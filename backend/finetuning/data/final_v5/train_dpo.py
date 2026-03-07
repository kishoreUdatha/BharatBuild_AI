#!/usr/bin/env python3
"""
DPO (Direct Preference Optimization) Training Script for BharatBuild AI
Trains the model to prefer good solutions over bad solutions

Run on RunPod or any GPU server with >= 24GB VRAM

Usage:
  python train_dpo.py

Requirements:
  pip install -r requirements.txt
  pip install trl>=0.7.0  # Includes DPO trainer
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import DPOTrainer
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

with open("config.json", "r") as f:
    config = json.load(f)

# Use SFT fine-tuned model as base for DPO
BASE_MODEL = config["training_config"]["base_model"]
SFT_MODEL = "./qwen-bharatbuild-v4"  # Use SFT model if available
DPO_DATA = "dpo_pairs.jsonl"
OUTPUT_DIR = "./qwen-bharatbuild-v4-dpo"

# DPO hyperparameters
EPOCHS = 1
BATCH_SIZE = 2
GRADIENT_ACCUMULATION = 4
LEARNING_RATE = 5e-5
BETA = 0.1  # DPO temperature parameter
MAX_LENGTH = 2048

# LoRA configuration
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05

# ============================================================================
# SETUP
# ============================================================================

print("=" * 70)
print("DPO TRAINING FOR BHARATBUILD AI")
print("=" * 70)

# Check if SFT model exists, otherwise use base model
model_path = SFT_MODEL if os.path.exists(SFT_MODEL) else BASE_MODEL
print(f"Model: {model_path}")
print(f"DPO Beta: {BETA}")
print(f"Epochs: {EPOCHS}")
print("=" * 70)

# ============================================================================
# LOAD MODEL WITH QUANTIZATION
# ============================================================================

print("\nLoading model with 4-bit quantization...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

# Load reference model for DPO (frozen)
ref_model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"  # Important for DPO

# ============================================================================
# PREPARE FOR TRAINING
# ============================================================================

print("Preparing model for training...")

model = prepare_model_for_kbit_training(model)

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ============================================================================
# LOAD DPO DATASET
# ============================================================================

print("\nLoading DPO dataset...")

def load_dpo_data(file_path):
    """Load DPO pairs and format for training."""
    examples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                examples.append({
                    "prompt": data["prompt"],
                    "chosen": data["chosen"],
                    "rejected": data["rejected"]
                })
    return examples

dpo_data = load_dpo_data(DPO_DATA)
print(f"DPO pairs loaded: {len(dpo_data)}")

# Split into train/eval
train_size = int(len(dpo_data) * 0.9)
train_data = dpo_data[:train_size]
eval_data = dpo_data[train_size:]

print(f"Train pairs: {len(train_data)}")
print(f"Eval pairs: {len(eval_data)}")

# Convert to HuggingFace dataset
from datasets import Dataset

train_dataset = Dataset.from_list(train_data)
eval_dataset = Dataset.from_list(eval_data) if eval_data else None

# ============================================================================
# DPO TRAINING
# ============================================================================

print("\nStarting DPO training...")

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",
    logging_steps=1,
    save_steps=50,
    eval_steps=50 if eval_dataset else None,
    evaluation_strategy="steps" if eval_dataset else "no",
    save_total_limit=2,
    load_best_model_at_end=True if eval_dataset else False,
    report_to="none",
    bf16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
    remove_unused_columns=False,
)

# Initialize DPO trainer
dpo_trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,
    args=training_args,
    beta=BETA,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
    max_length=MAX_LENGTH,
    max_prompt_length=MAX_LENGTH // 2,
)

# Train
dpo_trainer.train()

# Save final model
print("\nSaving model...")
dpo_trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n" + "=" * 70)
print("DPO TRAINING COMPLETE!")
print("=" * 70)
print(f"Model saved to: {OUTPUT_DIR}")
print("\nTraining pipeline:")
print("  1. SFT (train_qwen.py) - Learn to generate code")
print("  2. DPO (train_dpo.py) - Learn to prefer good solutions")
print("\nNext: Merge weights with merge_and_upload.py")
