"""
Qwen2.5-Coder-7B Fine-tuning Script for AWS
Optimized for g5.xlarge/g5.2xlarge (A10G 24GB GPU)

Usage:
    python train_aws.py

Cost estimate: ~$6 for full training
"""

import os
import torch
from datetime import datetime
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer

# ============================================
# Configuration
# ============================================
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"
OUTPUT_DIR = "./output/qwen-bharatbuild"
DATA_FILE = "./data/training_data.jsonl"

# Training hyperparameters (optimized for A10G 24GB)
BATCH_SIZE = 2
GRADIENT_ACCUMULATION = 8  # Effective batch size = 16
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
MAX_SEQ_LENGTH = 2048

# LoRA configuration
LORA_R = 64
LORA_ALPHA = 128
LORA_DROPOUT = 0.05

def print_gpu_info():
    """Print GPU information"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU: {gpu_name}")
        print(f"GPU Memory: {gpu_memory:.1f} GB")
    else:
        print("WARNING: No GPU detected!")

def format_training_sample(example):
    """Format training sample for chat template"""
    return {
        "text": f"<|im_start|>system\n{example.get('system', 'You are a helpful coding assistant.')}<|im_end|>\n"
                f"<|im_start|>user\n{example['instruction']}<|im_end|>\n"
                f"<|im_start|>assistant\n{example['output']}<|im_end|>"
    }

def main():
    print("=" * 60)
    print("BharatBuild Qwen Fine-tuning (AWS)")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    print_gpu_info()
    print()

    # Check for training data
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: Training data not found at {DATA_FILE}")
        print("Please upload training_data.jsonl to ./data/")
        return

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        padding_side="right"
    )
    tokenizer.pad_token = tokenizer.eos_token

    # 4-bit quantization config
    print("Configuring 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # Load model
    print(f"Loading model: {MODEL_NAME}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model.config.use_cache = False

    # Prepare model for training
    model = prepare_model_for_kbit_training(model)

    # LoRA configuration
    print("Applying LoRA...")
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Load dataset
    print(f"Loading dataset from {DATA_FILE}...")
    dataset = load_dataset("json", data_files=DATA_FILE, split="train")
    print(f"Dataset size: {len(dataset)} samples")

    # Format dataset
    dataset = dataset.map(format_training_sample, remove_columns=dataset.column_names)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION,
        learning_rate=LEARNING_RATE,
        weight_decay=0.01,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        logging_steps=10,
        save_steps=500,
        save_total_limit=3,
        bf16=True,
        gradient_checkpointing=True,
        max_grad_norm=0.3,
        optim="paged_adamw_32bit",
        report_to="none",  # Set to "wandb" for experiment tracking
    )

    # Initialize trainer
    print("Initializing trainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        packing=True,
    )

    # Train
    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60)
    trainer.train()

    # Save model
    print("\nSaving model...")
    trainer.save_model(f"{OUTPUT_DIR}/final")
    tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"Model saved to: {OUTPUT_DIR}/final")
    print(f"End time: {datetime.now()}")
    print("=" * 60)

    # Upload to S3 (optional)
    print("\nTo upload to S3, run:")
    print(f"  aws s3 cp {OUTPUT_DIR}/final s3://your-bucket/qwen-finetuned/ --recursive")

if __name__ == "__main__":
    main()
