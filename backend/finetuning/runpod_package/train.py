"""
Fine-tuning Script for Qwen2.5-Coder using QLoRA
Optimized for BharatBuild AI code generation
"""
import os
import sys
import json
import torch
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Hugging Face imports
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    DataCollatorForSeq2Seq,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset, Dataset

# Local imports
from config import (
    DEFAULT_MODEL_CONFIG,
    DEFAULT_QUANT_CONFIG,
    DEFAULT_LORA_CONFIG,
    DEFAULT_TRAINING_CONFIG,
    DEFAULT_DATA_CONFIG,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QwenCoderFineTuner:
    """Fine-tune Qwen2.5-Coder for code generation"""

    def __init__(
        self,
        model_config=DEFAULT_MODEL_CONFIG,
        quant_config=DEFAULT_QUANT_CONFIG,
        lora_config=DEFAULT_LORA_CONFIG,
        training_config=DEFAULT_TRAINING_CONFIG,
    ):
        self.model_config = model_config
        self.quant_config = quant_config
        self.lora_config = lora_config
        self.training_config = training_config

        self.model = None
        self.tokenizer = None
        self.trainer = None

    def setup_quantization(self) -> BitsAndBytesConfig:
        """Configure 4-bit quantization for QLoRA"""
        compute_dtype = getattr(torch, self.quant_config.bnb_4bit_compute_dtype)

        return BitsAndBytesConfig(
            load_in_4bit=self.quant_config.load_in_4bit,
            bnb_4bit_quant_type=self.quant_config.bnb_4bit_quant_type,
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=self.quant_config.bnb_4bit_use_double_quant,
        )

    def load_model(self):
        """Load model with quantization"""
        logger.info(f"Loading model: {self.model_config.model_name}")

        # Quantization config
        bnb_config = self.setup_quantization()

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_config.model_name,
            trust_remote_code=self.model_config.trust_remote_code,
            padding_side="right",
        )

        # Set pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model
        model_kwargs = {
            "quantization_config": bnb_config,
            "device_map": "auto",
            "trust_remote_code": self.model_config.trust_remote_code,
        }

        # Add flash attention if available
        if self.model_config.use_flash_attention:
            try:
                model_kwargs["attn_implementation"] = "flash_attention_2"
                logger.info("Using Flash Attention 2")
            except Exception as e:
                logger.warning(f"Flash Attention not available: {e}")

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_config.model_name,
            **model_kwargs
        )

        # Prepare for k-bit training
        self.model = prepare_model_for_kbit_training(
            self.model,
            use_gradient_checkpointing=self.training_config.gradient_checkpointing
        )

        logger.info("Model loaded successfully")

    def setup_lora(self):
        """Configure LoRA adapters"""
        logger.info("Setting up LoRA adapters")

        lora_config = LoraConfig(
            r=self.lora_config.r,
            lora_alpha=self.lora_config.lora_alpha,
            lora_dropout=self.lora_config.lora_dropout,
            target_modules=self.lora_config.target_modules,
            bias=self.lora_config.bias,
            task_type=TaskType.CAUSAL_LM,
        )

        self.model = get_peft_model(self.model, lora_config)

        # Print trainable parameters
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in self.model.parameters())
        logger.info(f"Trainable params: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")

    def load_dataset(self, train_path: str, eval_path: Optional[str] = None):
        """Load and prepare dataset"""
        logger.info(f"Loading dataset from {train_path}")

        # Load JSONL files
        train_data = load_dataset("json", data_files=train_path, split="train")

        if eval_path and Path(eval_path).exists():
            eval_data = load_dataset("json", data_files=eval_path, split="train")
        else:
            # Split train for eval
            split = train_data.train_test_split(test_size=0.1, seed=42)
            train_data = split["train"]
            eval_data = split["test"]

        logger.info(f"Train samples: {len(train_data)}, Eval samples: {len(eval_data)}")

        return train_data, eval_data

    def format_chat_template(self, example):
        """Format example using chat template"""
        if "messages" in example:
            # Already in chat format
            messages = example["messages"]
        else:
            # Convert Alpaca format to chat
            messages = [
                {"role": "system", "content": "You are an expert full-stack developer specializing in React, Next.js, TypeScript, FastAPI, and Python. Generate clean, production-ready code."},
                {"role": "user", "content": example["instruction"] + ("\n" + example["input"] if example.get("input") else "")},
                {"role": "assistant", "content": example["output"]}
            ]

        # Apply chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )

        return {"text": text}

    def train(
        self,
        train_path: str,
        eval_path: Optional[str] = None,
        resume_from_checkpoint: Optional[str] = None
    ):
        """Run training"""
        # Load dataset
        train_data, eval_data = self.load_dataset(train_path, eval_path)

        # Format with chat template
        logger.info("Formatting dataset with chat template...")
        train_data = train_data.map(self.format_chat_template, remove_columns=train_data.column_names)
        eval_data = eval_data.map(self.format_chat_template, remove_columns=eval_data.column_names)

        # Training arguments
        training_args = SFTConfig(
            output_dir=self.training_config.output_dir,
            num_train_epochs=self.training_config.num_train_epochs,
            per_device_train_batch_size=self.training_config.per_device_train_batch_size,
            per_device_eval_batch_size=self.training_config.per_device_eval_batch_size,
            gradient_accumulation_steps=self.training_config.gradient_accumulation_steps,
            gradient_checkpointing=self.training_config.gradient_checkpointing,
            learning_rate=self.training_config.learning_rate,
            weight_decay=self.training_config.weight_decay,
            warmup_ratio=self.training_config.warmup_ratio,
            lr_scheduler_type=self.training_config.lr_scheduler_type,
            optim=self.training_config.optim,
            fp16=self.training_config.fp16,
            bf16=self.training_config.bf16,
            logging_steps=self.training_config.logging_steps,
            save_steps=self.training_config.save_steps,
            eval_steps=self.training_config.eval_steps,
            eval_strategy="steps",
            save_total_limit=self.training_config.save_total_limit,
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            greater_is_better=False,
            report_to=self.training_config.report_to,
            run_name=self.training_config.run_name,
            seed=self.training_config.seed,
            max_seq_length=self.training_config.max_seq_length,
            packing=self.training_config.packing,
            dataset_text_field="text",
        )

        # Initialize trainer
        self.trainer = SFTTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_data,
            eval_dataset=eval_data,
            tokenizer=self.tokenizer,
        )

        # Train
        logger.info("Starting training...")
        self.trainer.train(resume_from_checkpoint=resume_from_checkpoint)

        # Save final model
        logger.info("Saving final model...")
        self.save_model()

        return self.trainer.state.log_history

    def save_model(self, output_dir: Optional[str] = None):
        """Save the fine-tuned model"""
        output_dir = output_dir or self.training_config.output_dir
        final_dir = Path(output_dir) / "final"
        final_dir.mkdir(parents=True, exist_ok=True)

        # Save LoRA adapter
        self.model.save_pretrained(final_dir)
        self.tokenizer.save_pretrained(final_dir)

        # Save config
        config = {
            "base_model": self.model_config.model_name,
            "lora_r": self.lora_config.r,
            "lora_alpha": self.lora_config.lora_alpha,
            "training_date": datetime.now().isoformat(),
        }
        with open(final_dir / "training_config.json", "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Model saved to {final_dir}")

    def merge_and_export(self, output_dir: str):
        """Merge LoRA weights and export full model"""
        logger.info("Merging LoRA weights with base model...")

        # Merge
        merged_model = self.model.merge_and_unload()

        # Save
        output_path = Path(output_dir) / "merged"
        output_path.mkdir(parents=True, exist_ok=True)

        merged_model.save_pretrained(output_path)
        self.tokenizer.save_pretrained(output_path)

        logger.info(f"Merged model saved to {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fine-tune Qwen2.5-Coder")
    parser.add_argument("--train-file", type=str, required=True, help="Training data JSONL")
    parser.add_argument("--eval-file", type=str, help="Evaluation data JSONL")
    parser.add_argument("--output-dir", type=str, default="./finetuned_models/qwen-coder")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=64)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--resume", type=str, help="Resume from checkpoint")
    parser.add_argument("--merge", action="store_true", help="Merge LoRA after training")
    parser.add_argument("--wandb-project", type=str, default="bharatbuild-finetuning")
    args = parser.parse_args()

    # Set wandb project
    os.environ["WANDB_PROJECT"] = args.wandb_project

    # Update configs
    from config import ModelConfig, LoraConfig as LC, TrainingConfig

    model_config = ModelConfig(model_name=args.model)
    lora_config = LC(r=args.lora_r)
    training_config = TrainingConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_seq_length=args.max_seq_length,
    )

    # Initialize fine-tuner
    fine_tuner = QwenCoderFineTuner(
        model_config=model_config,
        lora_config=lora_config,
        training_config=training_config,
    )

    # Load model
    fine_tuner.load_model()
    fine_tuner.setup_lora()

    # Train
    history = fine_tuner.train(
        train_path=args.train_file,
        eval_path=args.eval_file,
        resume_from_checkpoint=args.resume,
    )

    # Optionally merge
    if args.merge:
        fine_tuner.merge_and_export(args.output_dir)

    print("\nTraining complete!")
    print(f"Model saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
