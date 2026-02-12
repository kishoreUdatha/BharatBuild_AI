#!/usr/bin/env python3
"""
Complete Fine-tuning Pipeline Runner
Orchestrates data extraction, processing, training, and evaluation
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrate the complete fine-tuning pipeline"""

    def __init__(self, config: dict):
        self.config = config
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / "data"
        self.models_dir = self.base_dir / "finetuned_models"
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)

    def run_step(self, name: str, command: list) -> bool:
        """Run a pipeline step"""
        logger.info(f"{'='*60}")
        logger.info(f"STEP: {name}")
        logger.info(f"{'='*60}")

        try:
            result = subprocess.run(
                command,
                cwd=str(self.base_dir),
                check=True,
                capture_output=False
            )
            logger.info(f"Step '{name}' completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Step '{name}' failed with error: {e}")
            return False

    def step_1_extract_data(self) -> bool:
        """Extract training data from database"""
        logger.info("Extracting training data from BharatBuild AI database...")

        cmd = [
            sys.executable, "data_extractor.py",
            "--output-dir", str(self.data_dir / "raw"),
            "--format", "chatml",
        ]

        if self.config.get("limit_samples"):
            cmd.extend(["--limit", str(self.config["limit_samples"])])

        return self.run_step("Data Extraction", cmd)

    def step_2_process_data(self) -> bool:
        """Process and prepare training data"""
        logger.info("Processing training data...")

        cmd = [
            sys.executable, "data_processor.py",
            "--input", str(self.data_dir / "raw" / "train_chatml.jsonl"),
            "--output-dir", str(self.data_dir / "processed"),
            "--train-split", str(self.config.get("train_split", 0.9)),
        ]

        if not self.config.get("augment", True):
            cmd.append("--no-augment")

        return self.run_step("Data Processing", cmd)

    def step_3_train(self) -> bool:
        """Run fine-tuning"""
        logger.info("Starting fine-tuning...")

        output_dir = self.models_dir / f"qwen-coder-{self.run_id}"

        cmd = [
            sys.executable, "train.py",
            "--train-file", str(self.data_dir / "processed" / "train.jsonl"),
            "--eval-file", str(self.data_dir / "processed" / "eval.jsonl"),
            "--output-dir", str(output_dir),
            "--model", self.config.get("model", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            "--epochs", str(self.config.get("epochs", 3)),
            "--batch-size", str(self.config.get("batch_size", 2)),
            "--learning-rate", str(self.config.get("learning_rate", 2e-4)),
            "--lora-r", str(self.config.get("lora_r", 64)),
            "--max-seq-length", str(self.config.get("max_seq_length", 4096)),
        ]

        if self.config.get("merge_model", False):
            cmd.append("--merge")

        return self.run_step("Training", cmd)

    def step_4_evaluate(self) -> bool:
        """Evaluate the fine-tuned model"""
        logger.info("Evaluating model...")

        # Find latest model
        model_dirs = sorted(self.models_dir.glob("qwen-coder-*"))
        if not model_dirs:
            logger.error("No trained model found")
            return False

        latest_model = model_dirs[-1] / "final"

        cmd = [
            sys.executable, "evaluate.py",
            "--model-path", str(latest_model),
            "--eval-file", str(self.data_dir / "processed" / "eval.jsonl"),
        ]

        return self.run_step("Evaluation", cmd)

    def run_full_pipeline(self, skip_steps: list = None):
        """Run the complete pipeline"""
        skip_steps = skip_steps or []

        steps = [
            ("extract", self.step_1_extract_data),
            ("process", self.step_2_process_data),
            ("train", self.step_3_train),
            ("evaluate", self.step_4_evaluate),
        ]

        results = {}
        for step_name, step_func in steps:
            if step_name in skip_steps:
                logger.info(f"Skipping step: {step_name}")
                results[step_name] = "skipped"
                continue

            success = step_func()
            results[step_name] = "success" if success else "failed"

            if not success and not self.config.get("continue_on_error", False):
                logger.error(f"Pipeline stopped at step: {step_name}")
                break

        # Summary
        logger.info("\n" + "="*60)
        logger.info("PIPELINE SUMMARY")
        logger.info("="*60)
        for step, status in results.items():
            emoji = "✓" if status == "success" else ("⏭" if status == "skipped" else "✗")
            logger.info(f"  {emoji} {step}: {status}")

        return all(s in ["success", "skipped"] for s in results.values())


def main():
    parser = argparse.ArgumentParser(description="Run fine-tuning pipeline")

    # Pipeline options
    parser.add_argument("--skip", nargs="+", choices=["extract", "process", "train", "evaluate"],
                        help="Steps to skip")
    parser.add_argument("--only", choices=["extract", "process", "train", "evaluate"],
                        help="Run only this step")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Continue pipeline even if a step fails")

    # Data options
    parser.add_argument("--limit-samples", type=int, help="Limit training samples")
    parser.add_argument("--train-split", type=float, default=0.9)
    parser.add_argument("--no-augment", action="store_true")

    # Model options
    parser.add_argument("--model", type=str, default="Qwen/Qwen2.5-Coder-7B-Instruct",
                        choices=[
                            "Qwen/Qwen2.5-Coder-7B-Instruct",
                            "Qwen/Qwen2.5-Coder-14B-Instruct",
                            "Qwen/Qwen2.5-Coder-32B-Instruct",
                        ])
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=64)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--merge-model", action="store_true",
                        help="Merge LoRA weights after training")

    args = parser.parse_args()

    # Build config
    config = {
        "model": args.model,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "lora_r": args.lora_r,
        "max_seq_length": args.max_seq_length,
        "train_split": args.train_split,
        "augment": not args.no_augment,
        "merge_model": args.merge_model,
        "continue_on_error": args.continue_on_error,
    }

    if args.limit_samples:
        config["limit_samples"] = args.limit_samples

    # Run pipeline
    runner = PipelineRunner(config)

    if args.only:
        # Run single step
        step_map = {
            "extract": runner.step_1_extract_data,
            "process": runner.step_2_process_data,
            "train": runner.step_3_train,
            "evaluate": runner.step_4_evaluate,
        }
        success = step_map[args.only]()
    else:
        # Run full pipeline
        success = runner.run_full_pipeline(skip_steps=args.skip or [])

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
