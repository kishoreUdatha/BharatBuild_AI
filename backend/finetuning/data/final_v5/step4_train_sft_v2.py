#!/usr/bin/env python3
"""
STEP 4: SFT v2 - Gold + Silver Training

Train on combined dataset:
- 30-40% gold samples (503)
- 60-70% silver samples (2k-5k)

Goal: Better generalization and coverage.
"""

import os
import json
import torch
from pathlib import Path
from datasets import load_dataset, concatenate_datasets
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
GOLD_FILE = SCRIPT_DIR.parent / "gold_samples" / "gold_samples.jsonl"
SILVER_FILE = SCRIPT_DIR / "silver_data" / "silver_samples.jsonl"
OUTPUT_DIR = SCRIPT_DIR / "models" / "sft_v2"

# Model
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"

# Training
EPOCHS = 2
BATCH_SIZE = 4
GRADIENT_ACCUMULATION = 8  # Effective batch = 32
LEARNING_RATE = 1e-4  # Lower LR for larger dataset
MAX_SEQ_LENGTH = 4096

# LoRA
LORA_R = 64
LORA_ALPHA = 128
LORA_DROPOUT = 0.05

# ============================================================================
# SETUP
# ============================================================================

print("=" * 70)
print("STEP 4: SFT v2 - GOLD + SILVER TRAINING")
print("=" * 70)

# Check files
if not GOLD_FILE.exists():
    print(f"ERROR: Gold file not found: {GOLD_FILE}")
    exit(1)

if not SILVER_FILE.exists():
    print(f"ERROR: Silver file not found: {SILVER_FILE}")
    print("Run step3_generate_silver.py first.")
    exit(1)

# Count samples
with open(GOLD_FILE, 'r', encoding='utf-8') as f:
    gold_count = sum(1 for _ in f)

with open(SILVER_FILE, 'r', encoding='utf-8') as f:
    silver_count = sum(1 for _ in f)

total_count = gold_count + silver_count
gold_pct = gold_count / total_count * 100
silver_pct = silver_count / total_count * 100

print(f"\nDataset composition:")
print(f"  Gold samples:   {gold_count:,} ({gold_pct:.1f}%)")
print(f"  Silver samples: {silver_count:,} ({silver_pct:.1f}%)")
print(f"  Total:          {total_count:,}")
print(f"\nModel: {MODEL_NAME}")
print(f"Epochs: {EPOCHS}")
print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION}")
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
# LOAD AND MERGE DATASETS
# ============================================================================

print("\nLoading and merging datasets...")

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

# Load datasets
gold_dataset = load_dataset("json", data_files={"train": str(GOLD_FILE)})["train"]
silver_dataset = load_dataset("json", data_files={"train": str(SILVER_FILE)})["train"]

# Merge
combined = concatenate_datasets([gold_dataset, silver_dataset])
combined = combined.shuffle(seed=42)

# Split 95/5 for train/eval
split = combined.train_test_split(test_size=0.05, seed=42)
train_dataset = split["train"]
eval_dataset = split["test"]

print(f"Train: {len(train_dataset):,} examples")
print(f"Eval: {len(eval_dataset):,} examples")

# ============================================================================
# TRAINING
# ============================================================================

print("\nStarting SFT v2 training...")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

training_args = TrainingArguments(
    output_dir=str(OUTPUT_DIR),
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.05,
    lr_scheduler_type="cosine",
    logging_steps=50,
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
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    formatting_func=formatting_func,
    max_seq_length=MAX_SEQ_LENGTH,
    tokenizer=tokenizer,
    args=training_args,
    packing=True,  # Enable packing for larger dataset
)

# Train
trainer.train()

# Save
print("\nSaving Model v2...")
trainer.save_model(str(OUTPUT_DIR))
tokenizer.save_pretrained(str(OUTPUT_DIR))

# Save training info
info = {
    "step": "SFT v2",
    "gold_samples": gold_count,
    "silver_samples": silver_count,
    "total_samples": total_count,
    "epochs": EPOCHS,
    "base_model": MODEL_NAME,
    "output_format": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"]
}
with open(OUTPUT_DIR / "training_info.json", 'w') as f:
    json.dump(info, f, indent=2)

print("\n" + "=" * 70)
print("STEP 4 COMPLETE: SFT v2")
print("=" * 70)
print(f"Model saved to: {OUTPUT_DIR}")
print(f"\nTraining summary:")
print(f"  Gold samples: {gold_count}")
print(f"  Silver samples: {silver_count}")
print(f"  Total: {total_count}")
print("\nNext step:")
print("  python step5_train_dpo.py")
print("=" * 70)
