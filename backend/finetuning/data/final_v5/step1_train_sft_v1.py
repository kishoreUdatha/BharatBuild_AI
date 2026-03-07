#!/usr/bin/env python3
"""
STEP 1: SFT v1 - Baseline Alignment Training

Train Qwen on 503 gold samples ONLY.
Goal: Make model follow Claude-style structure reliably.

Run on GPU with >= 24GB VRAM
"""

import os
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
GOLD_FILE = SCRIPT_DIR.parent / "gold_samples" / "gold_samples.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "models" / "sft_v1"

# Model
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"

# Training - conservative for 503 samples
EPOCHS = 2  # Don't overtrain on small dataset
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 4  # Effective batch = 16
LEARNING_RATE = 2e-4
MAX_SEQ_LENGTH = 4096

# LoRA
LORA_R = 64
LORA_ALPHA = 128
LORA_DROPOUT = 0.05

# ============================================================================
# SETUP
# ============================================================================

print("=" * 70)
print("STEP 1: SFT v1 - BASELINE ALIGNMENT")
print("=" * 70)
print(f"Model: {MODEL_NAME}")
print(f"Gold samples: {GOLD_FILE}")
print(f"Epochs: {EPOCHS}")
print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION}")
print("=" * 70)

# Count samples
with open(GOLD_FILE, 'r', encoding='utf-8') as f:
    sample_count = sum(1 for _ in f)
print(f"Training on {sample_count} gold samples ONLY")
print("=" * 70)

# ============================================================================
# LOAD MODEL
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

print("\nLoading gold samples...")

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

dataset = load_dataset("json", data_files={"train": str(GOLD_FILE)})

# Split 90/10 for train/eval
dataset = dataset["train"].train_test_split(test_size=0.1, seed=42)
print(f"Train: {len(dataset['train'])} examples")
print(f"Eval: {len(dataset['test'])} examples")

# ============================================================================
# TRAINING
# ============================================================================

print("\nStarting SFT v1 training...")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

training_args = TrainingArguments(
    output_dir=str(OUTPUT_DIR),
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.1,  # Higher warmup for small dataset
    lr_scheduler_type="cosine",
    logging_steps=10,
    save_steps=100,
    eval_steps=100,
    evaluation_strategy="steps",
    save_total_limit=2,
    load_best_model_at_end=True,
    report_to="none",
    bf16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
    formatting_func=formatting_func,
    max_seq_length=MAX_SEQ_LENGTH,
    tokenizer=tokenizer,
    args=training_args,
    packing=False,  # Don't pack for small dataset
)

# Train
trainer.train()

# Save
print("\nSaving Model v1...")
trainer.save_model(str(OUTPUT_DIR))
tokenizer.save_pretrained(str(OUTPUT_DIR))

# Save training info
info = {
    "step": "SFT v1",
    "gold_samples": sample_count,
    "epochs": EPOCHS,
    "base_model": MODEL_NAME,
    "output_format": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"]
}
with open(OUTPUT_DIR / "training_info.json", 'w') as f:
    json.dump(info, f, indent=2)

print("\n" + "=" * 70)
print("STEP 1 COMPLETE: SFT v1")
print("=" * 70)
print(f"Model saved to: {OUTPUT_DIR}")
print("\nNext step:")
print("  python step2_evaluate_v1.py")
print("=" * 70)
