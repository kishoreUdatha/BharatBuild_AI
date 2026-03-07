#!/usr/bin/env python3
"""
Qwen Fine-tuning Script for BharatBuild AI V5
Claude-Style Output Training with 500+ Gold Samples

Run on RunPod or any GPU server with >= 24GB VRAM

Usage:
  python train_qwen.py

Requirements:
  pip install -r requirements.txt
"""

import os
import sys
import torch
from pathlib import Path
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

MODEL_NAME = config["training_config"]["base_model"]
TRAIN_FILE = str(SCRIPT_DIR / "train.jsonl")
EVAL_FILE = str(SCRIPT_DIR / "eval.jsonl")
OUTPUT_DIR = str(SCRIPT_DIR / "qwen-bharatbuild-v5")

# Training hyperparameters
EPOCHS = config["training_config"]["epochs"]
BATCH_SIZE = config["training_config"]["batch_size"]
GRADIENT_ACCUMULATION = config["training_config"]["gradient_accumulation_steps"]
LEARNING_RATE = config["training_config"]["learning_rate"]
MAX_SEQ_LENGTH = config["training_config"]["max_seq_length"]

# LoRA configuration
LORA_R = config["training_config"]["lora_r"]
LORA_ALPHA = config["training_config"]["lora_alpha"]
LORA_DROPOUT = config["training_config"]["lora_dropout"]

# ============================================================================
# SETUP
# ============================================================================

print("=" * 70)
print("QWEN FINE-TUNING FOR BHARATBUILD AI - V5 CLAUDE-STYLE")
print("=" * 70)
print(f"Model: {MODEL_NAME}")
print(f"Train examples: {config['statistics']['train_examples']:,}")
print(f"Eval examples: {config['statistics']['eval_examples']:,}")
print(f"DPO pairs: {config['statistics'].get('dpo_pairs', 0)}")
print(f"Epochs: {EPOCHS}")
print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION}")
print("=" * 70)

# Print gold samples info
if "gold_samples" in config:
    print("\nGold Samples (Claude-Style):")
    gs = config["gold_samples"]
    print(f"  Total: {gs['total_samples']}")
    for cat, count in gs["categories"].items():
        print(f"    {cat}: {count}")
    print(f"  Output format: {', '.join(gs['output_format'])}")

# Print microservices coverage
if "microservices_coverage" in config:
    print("\nMicroservices Coverage:")
    for tech, count in sorted(config["microservices_coverage"].items(), key=lambda x: -x[1])[:5]:
        print(f"  {tech}: {count}")

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
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

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
# LOAD DATASET
# ============================================================================

print("\nLoading dataset...")

def formatting_func(example):
    """Format example for training using ChatML format"""
    messages = example["messages"]
    text = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            text += f"<|im_start|>system\n{content}<|im_end|>\n"
        elif role == "user":
            text += f"<|im_start|>user\n{content}<|im_end|>\n"
        elif role == "assistant":
            text += f"<|im_start|>assistant\n{content}<|im_end|>\n"
    return text

dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "eval": EVAL_FILE})
print(f"Train: {len(dataset['train']):,} examples")
print(f"Eval: {len(dataset['eval']):,} examples")

# ============================================================================
# TRAINING
# ============================================================================

print("\nStarting training...")

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=10,
    save_steps=500,
    eval_steps=500,
    evaluation_strategy="steps",
    save_total_limit=3,
    load_best_model_at_end=True,
    report_to="none",
    bf16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    eval_dataset=dataset["eval"],
    formatting_func=formatting_func,
    max_seq_length=MAX_SEQ_LENGTH,
    tokenizer=tokenizer,
    args=training_args,
    packing=True,
)

# Train
trainer.train()

# Save final model
print("\nSaving model...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n" + "=" * 70)
print("SFT TRAINING COMPLETE!")
print("=" * 70)
print(f"Model saved to: {OUTPUT_DIR}")
print("\nNext steps:")
print("  1. Run DPO training: python train_dpo.py")
print("  2. Run: python merge_and_upload.py")
print("  3. Upload to Hugging Face or deploy locally")
print("\nClaude-Style Output Format:")
print("  PLAN -> FILES -> PATCH -> COMMANDS -> NOTES")
