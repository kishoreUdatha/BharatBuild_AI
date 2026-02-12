"""
AWS SageMaker Training Script
Fine-tune Qwen2.5-Coder on SageMaker with managed infrastructure
"""
import os
import json
import boto3
import sagemaker
from sagemaker.huggingface import HuggingFace
from sagemaker.inputs import TrainingInput
from datetime import datetime


class SageMakerTrainer:
    """Train on AWS SageMaker"""

    def __init__(
        self,
        role: str = None,
        region: str = "us-east-1",
        bucket: str = None,
    ):
        self.region = region
        self.session = sagemaker.Session()
        self.role = role or sagemaker.get_execution_role()
        self.bucket = bucket or self.session.default_bucket()

    def upload_data(self, local_path: str, s3_prefix: str = "bharatbuild/training-data"):
        """Upload training data to S3"""
        s3_uri = self.session.upload_data(
            path=local_path,
            bucket=self.bucket,
            key_prefix=s3_prefix,
        )
        print(f"Uploaded to: {s3_uri}")
        return s3_uri

    def create_training_job(
        self,
        train_data_s3: str,
        eval_data_s3: str = None,
        model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
        instance_type: str = "ml.g5.2xlarge",  # 1x A10G 24GB
        epochs: int = 3,
        batch_size: int = 2,
        learning_rate: float = 2e-4,
        lora_r: int = 64,
        max_seq_length: int = 4096,
    ):
        """Create and start SageMaker training job"""

        # Hyperparameters
        hyperparameters = {
            "model_id": model_name,
            "epochs": epochs,
            "per_device_train_batch_size": batch_size,
            "learning_rate": learning_rate,
            "lora_r": lora_r,
            "lora_alpha": lora_r * 2,
            "max_seq_length": max_seq_length,
            "gradient_accumulation_steps": 8,
            "bf16": "true",
            "gradient_checkpointing": "true",
        }

        # Estimator
        estimator = HuggingFace(
            entry_point="train_sagemaker.py",
            source_dir="./",
            instance_type=instance_type,
            instance_count=1,
            role=self.role,
            transformers_version="4.37",
            pytorch_version="2.1",
            py_version="py310",
            hyperparameters=hyperparameters,
            disable_profiler=True,
            base_job_name="bharatbuild-qwen-coder",
            # Enable spot instances for cost savings (up to 70% off)
            use_spot_instances=True,
            max_wait=72000,  # 20 hours max wait
            max_run=36000,   # 10 hours max run
            # Checkpointing
            checkpoint_s3_uri=f"s3://{self.bucket}/bharatbuild/checkpoints/",
            checkpoint_local_path="/opt/ml/checkpoints",
        )

        # Input channels
        inputs = {
            "train": TrainingInput(s3_data=train_data_s3, content_type="application/jsonlines"),
        }
        if eval_data_s3:
            inputs["eval"] = TrainingInput(s3_data=eval_data_s3, content_type="application/jsonlines")

        # Start training
        print(f"Starting training job...")
        print(f"  Instance: {instance_type}")
        print(f"  Model: {model_name}")
        print(f"  Epochs: {epochs}")

        estimator.fit(inputs, wait=False)

        print(f"\nTraining job started: {estimator.latest_training_job.name}")
        print(f"Monitor at: https://{self.region}.console.aws.amazon.com/sagemaker/home?region={self.region}#/jobs")

        return estimator

    def download_model(self, training_job_name: str, local_path: str = "./finetuned_models/"):
        """Download trained model from S3"""
        client = boto3.client("sagemaker", region_name=self.region)

        # Get job details
        response = client.describe_training_job(TrainingJobName=training_job_name)
        model_artifacts = response["ModelArtifacts"]["S3ModelArtifacts"]

        print(f"Downloading model from: {model_artifacts}")

        # Download
        s3 = boto3.client("s3")
        # Parse S3 URI
        bucket = model_artifacts.split("/")[2]
        key = "/".join(model_artifacts.split("/")[3:])

        os.makedirs(local_path, exist_ok=True)
        s3.download_file(bucket, key, f"{local_path}/model.tar.gz")

        print(f"Model downloaded to: {local_path}/model.tar.gz")
        print(f"Extract with: tar -xzf {local_path}/model.tar.gz -C {local_path}/")


# SageMaker entry point script
TRAIN_SAGEMAKER_SCRIPT = '''
#!/usr/bin/env python3
"""
SageMaker Training Entry Point
This script is executed by SageMaker
"""
import os
import json
import argparse
import torch
from pathlib import Path

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset


def parse_args():
    parser = argparse.ArgumentParser()

    # Hyperparameters
    parser.add_argument("--model_id", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--per_device_train_batch_size", type=int, default=2)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=64)
    parser.add_argument("--lora_alpha", type=int, default=128)
    parser.add_argument("--max_seq_length", type=int, default=4096)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--bf16", type=str, default="true")
    parser.add_argument("--gradient_checkpointing", type=str, default="true")

    # SageMaker paths
    parser.add_argument("--model_dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--eval", type=str, default=os.environ.get("SM_CHANNEL_EVAL", ""))

    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Training model: {args.model_id}")
    print(f"Training data: {args.train}")

    # Quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Prepare for training
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=args.gradient_checkpointing == "true"
    )

    # LoRA config
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    # Load data
    train_files = list(Path(args.train).glob("*.jsonl"))
    train_data = load_dataset("json", data_files=[str(f) for f in train_files], split="train")

    eval_data = None
    if args.eval and Path(args.eval).exists():
        eval_files = list(Path(args.eval).glob("*.jsonl"))
        if eval_files:
            eval_data = load_dataset("json", data_files=[str(f) for f in eval_files], split="train")

    # Format function
    def format_chat(example):
        messages = example["messages"]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    train_data = train_data.map(format_chat, remove_columns=train_data.column_names)
    if eval_data:
        eval_data = eval_data.map(format_chat, remove_columns=eval_data.column_names)

    # Training config
    training_args = SFTConfig(
        output_dir=args.model_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        bf16=args.bf16 == "true",
        logging_steps=10,
        save_steps=500,
        eval_strategy="steps" if eval_data else "no",
        eval_steps=500 if eval_data else None,
        max_seq_length=args.max_seq_length,
        packing=True,
        dataset_text_field="text",
    )

    # Trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        tokenizer=tokenizer,
    )

    # Train
    trainer.train()

    # Save
    trainer.save_model()
    tokenizer.save_pretrained(args.model_dir)

    print(f"Model saved to {args.model_dir}")


if __name__ == "__main__":
    main()
'''


def create_sagemaker_script():
    """Create the SageMaker training script"""
    script_path = os.path.join(os.path.dirname(__file__), "train_sagemaker.py")
    with open(script_path, "w") as f:
        f.write(TRAIN_SAGEMAKER_SCRIPT)
    print(f"Created: {script_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Train on AWS SageMaker")
    parser.add_argument("--action", choices=["upload", "train", "download", "create-script"], required=True)
    parser.add_argument("--train-data", type=str, help="Local path to training data")
    parser.add_argument("--eval-data", type=str, help="Local path to eval data")
    parser.add_argument("--s3-train", type=str, help="S3 URI for training data")
    parser.add_argument("--s3-eval", type=str, help="S3 URI for eval data")
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--instance-type", type=str, default="ml.g5.2xlarge")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--job-name", type=str, help="Training job name (for download)")
    parser.add_argument("--output-dir", type=str, default="./finetuned_models")
    args = parser.parse_args()

    trainer = SageMakerTrainer()

    if args.action == "create-script":
        create_sagemaker_script()

    elif args.action == "upload":
        if not args.train_data:
            print("Error: --train-data required for upload")
            return
        trainer.upload_data(args.train_data)

    elif args.action == "train":
        if not args.s3_train:
            print("Error: --s3-train required for training")
            return
        trainer.create_training_job(
            train_data_s3=args.s3_train,
            eval_data_s3=args.s3_eval,
            model_name=args.model,
            instance_type=args.instance_type,
            epochs=args.epochs,
        )

    elif args.action == "download":
        if not args.job_name:
            print("Error: --job-name required for download")
            return
        trainer.download_model(args.job_name, args.output_dir)


if __name__ == "__main__":
    main()
