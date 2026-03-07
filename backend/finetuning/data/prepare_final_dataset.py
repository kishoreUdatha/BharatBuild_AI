"""
Prepare Final Training Dataset for Qwen Fine-tuning

Combines:
1. Public datasets (75K examples) - CodeAlpaca, Magicoder, Evol-Instruct, etc.
2. Multi-file project examples (170 examples) - Full-stack projects
3. Complex task examples (30 examples) - Debugging, explanation, refactoring

Output:
- final/train.jsonl - Ready for training
- final/eval.jsonl - Ready for evaluation
- final/config.json - Training configuration
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime


def load_jsonl(file_path: Path) -> List[Dict]:
    """Load JSONL file"""
    if not file_path.exists():
        print(f"  Warning: File not found: {file_path}")
        return []

    examples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return examples


def save_jsonl(examples: List[Dict], file_path: Path):
    """Save examples to JSONL file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')


def get_response_length(example: Dict) -> int:
    """Get assistant response length"""
    for msg in example.get("messages", []):
        if msg.get("role") == "assistant":
            return len(msg.get("content", ""))
    return 0


def categorize_example(example: Dict) -> str:
    """Categorize example by type"""
    assistant_content = ""
    for msg in example.get("messages", []):
        if msg.get("role") == "assistant":
            assistant_content = msg.get("content", "")
            break

    if "## Project Structure" in assistant_content or "docker-compose" in assistant_content.lower():
        return "multifile"
    elif "## Error Analysis" in assistant_content or "## Root Cause" in assistant_content:
        return "debugging"
    elif "## Code Review" in assistant_content or "### Refactored" in assistant_content:
        return "refactoring"
    elif "## What It Does" in assistant_content or "## Key Concepts" in assistant_content:
        return "explanation"
    elif "```" in assistant_content and len(assistant_content) > 500:
        return "code_generation"
    else:
        return "simple"


def deduplicate_by_prompt(examples: List[Dict]) -> List[Dict]:
    """Remove duplicates based on user prompt"""
    seen: Set[str] = set()
    unique = []

    for example in examples:
        user_prompt = ""
        for msg in example.get("messages", []):
            if msg.get("role") == "user":
                user_prompt = msg.get("content", "")[:300].lower().strip()
                break

        if user_prompt and user_prompt not in seen:
            seen.add(user_prompt)
            unique.append(example)

    return unique


def prepare_final_dataset():
    """Prepare final combined dataset"""

    data_dir = Path(__file__).parent
    output_dir = data_dir / "final_v3"
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("PREPARING FINAL TRAINING DATASET")
    print("=" * 70)

    # Load all datasets
    print("\n[1/5] Loading datasets...")

    datasets = {
        "public_train": data_dir / "public_datasets" / "merged_train.jsonl",
        "public_eval": data_dir / "public_datasets" / "merged_eval.jsonl",
        "multifile_train": data_dir / "multifile" / "train.jsonl",
        "multifile_eval": data_dir / "multifile" / "eval.jsonl",
        "complex_train": data_dir / "complex_tasks" / "train.jsonl",
        "complex_eval": data_dir / "complex_tasks" / "eval.jsonl",
    }

    all_train = []
    all_eval = []

    for name, path in datasets.items():
        examples = load_jsonl(path)
        print(f"  {name}: {len(examples):,} examples")

        if "eval" in name:
            all_eval.extend(examples)
        else:
            all_train.extend(examples)

    print(f"\n  Total loaded: {len(all_train):,} train, {len(all_eval):,} eval")

    # Deduplicate
    print("\n[2/5] Deduplicating...")
    before_train = len(all_train)
    before_eval = len(all_eval)

    all_train = deduplicate_by_prompt(all_train)
    all_eval = deduplicate_by_prompt(all_eval)

    print(f"  Train: {before_train:,} -> {len(all_train):,} (removed {before_train - len(all_train):,})")
    print(f"  Eval: {before_eval:,} -> {len(all_eval):,} (removed {before_eval - len(all_eval):,})")

    # Categorize and count
    print("\n[3/5] Analyzing dataset composition...")
    categories = {"multifile": 0, "debugging": 0, "refactoring": 0, "explanation": 0, "code_generation": 0, "simple": 0}

    for example in all_train:
        cat = categorize_example(example)
        categories[cat] += 1

    print("  Dataset composition:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        pct = count / len(all_train) * 100
        print(f"    {cat}: {count:,} ({pct:.1f}%)")

    # Shuffle
    print("\n[4/5] Shuffling...")
    random.seed(42)  # Reproducible
    random.shuffle(all_train)
    random.shuffle(all_eval)

    # Save final datasets
    print("\n[5/5] Saving final datasets...")

    train_file = output_dir / "train.jsonl"
    eval_file = output_dir / "eval.jsonl"

    save_jsonl(all_train, train_file)
    save_jsonl(all_eval, eval_file)

    # Calculate statistics
    train_tokens_estimate = sum(get_response_length(e) for e in all_train) // 4
    eval_tokens_estimate = sum(get_response_length(e) for e in all_eval) // 4

    # Create config file
    config = {
        "dataset_version": "v3_final",
        "created_at": datetime.now().isoformat(),
        "statistics": {
            "train_examples": len(all_train),
            "eval_examples": len(all_eval),
            "estimated_train_tokens": train_tokens_estimate,
            "estimated_eval_tokens": eval_tokens_estimate,
        },
        "composition": categories,
        "sources": [
            "CodeAlpaca-20k (Hugging Face)",
            "Magicoder-OSS-Instruct-75K (Hugging Face)",
            "Evol-Instruct-Code-80k (Hugging Face)",
            "Python-Codes-25k (Hugging Face)",
            "Python-Instructions-18k (Hugging Face)",
            "Custom Multi-file Projects (Generated)",
            "Custom Complex Tasks (Generated)",
        ],
        "training_config": {
            "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
            "method": "LoRA",
            "lora_r": 64,
            "lora_alpha": 128,
            "lora_dropout": 0.05,
            "learning_rate": 2e-4,
            "batch_size": 4,
            "gradient_accumulation_steps": 4,
            "epochs": 3,
            "max_seq_length": 4096,
            "warmup_ratio": 0.03,
        },
        "files": {
            "train": str(train_file),
            "eval": str(eval_file),
        }
    }

    config_file = output_dir / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("FINAL DATASET READY FOR TRAINING")
    print("=" * 70)
    print(f"""
Files created:
  - {train_file}
  - {eval_file}
  - {config_file}

Statistics:
  Training examples:   {len(all_train):,}
  Evaluation examples: {len(all_eval):,}
  Est. training tokens: {train_tokens_estimate:,}

Dataset composition:
  - Multi-file projects: {categories['multifile']:,}
  - Code generation:     {categories['code_generation']:,}
  - Debugging:           {categories['debugging']:,}
  - Explanation:         {categories['explanation']:,}
  - Refactoring:         {categories['refactoring']:,}
  - Simple tasks:        {categories['simple']:,}

Recommended training command:
  python train_qwen.py \\
    --model Qwen/Qwen2.5-Coder-7B-Instruct \\
    --train_data {train_file} \\
    --eval_data {eval_file} \\
    --output_dir ./qwen-finetuned-v3 \\
    --epochs 3 \\
    --batch_size 4 \\
    --learning_rate 2e-4
""")

    # Create training script
    create_training_script(output_dir)

    return train_file, eval_file, config_file


def create_training_script(output_dir: Path):
    """Create ready-to-use training script"""

    script_content = '''#!/usr/bin/env python3
"""
Qwen Fine-tuning Script for BharatBuild AI
Run on RunPod or any GPU server with >= 24GB VRAM

Usage:
  python train_qwen.py

Requirements:
  pip install transformers datasets peft accelerate bitsandbytes trl
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
from trl import SFTTrainer
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

MODEL_NAME = config["training_config"]["base_model"]
TRAIN_FILE = "train.jsonl"
EVAL_FILE = "eval.jsonl"
OUTPUT_DIR = "./qwen-bharatbuild-v3"

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

print("=" * 60)
print("QWEN FINE-TUNING FOR BHARATBUILD AI")
print("=" * 60)
print(f"Model: {MODEL_NAME}")
print(f"Train examples: {config['statistics']['train_examples']:,}")
print(f"Eval examples: {config['statistics']['eval_examples']:,}")
print(f"Epochs: {EPOCHS}")
print(f"Batch size: {BATCH_SIZE} x {GRADIENT_ACCUMULATION} = {BATCH_SIZE * GRADIENT_ACCUMULATION}")
print("=" * 60)

# ============================================================================
# LOAD MODEL WITH QUANTIZATION
# ============================================================================

print("\\nLoading model with 4-bit quantization...")

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

print("\\nLoading dataset...")

def formatting_func(example):
    """Format example for training"""
    messages = example["messages"]
    text = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            text += f"<|im_start|>system\\n{content}<|im_end|>\\n"
        elif role == "user":
            text += f"<|im_start|>user\\n{content}<|im_end|>\\n"
        elif role == "assistant":
            text += f"<|im_start|>assistant\\n{content}<|im_end|>\\n"
    return text

dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "eval": EVAL_FILE})
print(f"Train: {len(dataset['train']):,} examples")
print(f"Eval: {len(dataset['eval']):,} examples")

# ============================================================================
# TRAINING
# ============================================================================

print("\\nStarting training...")

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
print("\\nSaving model...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\\n" + "=" * 60)
print("TRAINING COMPLETE!")
print("=" * 60)
print(f"Model saved to: {OUTPUT_DIR}")
print("\\nTo merge LoRA weights and upload:")
print("  python merge_and_upload.py")
'''

    script_file = output_dir / "train_qwen.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)

    print(f"  Created training script: {script_file}")

    # Create merge script
    merge_script = '''#!/usr/bin/env python3
"""
Merge LoRA weights and prepare for deployment
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import json

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

BASE_MODEL = config["training_config"]["base_model"]
LORA_MODEL = "./qwen-bharatbuild-v3"
OUTPUT_DIR = "./qwen-bharatbuild-v3-merged"

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

print("Loading LoRA weights...")
model = PeftModel.from_pretrained(model, LORA_MODEL)

print("Merging weights...")
model = model.merge_and_unload()

print(f"Saving merged model to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.save_pretrained(OUTPUT_DIR)

print("Done! Model ready for deployment.")
'''

    merge_file = output_dir / "merge_and_upload.py"
    with open(merge_file, 'w', encoding='utf-8') as f:
        f.write(merge_script)

    print(f"  Created merge script: {merge_file}")

    # Create requirements file
    requirements = '''# Requirements for Qwen fine-tuning
torch>=2.0.0
transformers>=4.36.0
datasets>=2.14.0
peft>=0.7.0
accelerate>=0.25.0
bitsandbytes>=0.41.0
trl>=0.7.0
scipy
'''

    req_file = output_dir / "requirements.txt"
    with open(req_file, 'w') as f:
        f.write(requirements)

    print(f"  Created requirements: {req_file}")


if __name__ == "__main__":
    prepare_final_dataset()
