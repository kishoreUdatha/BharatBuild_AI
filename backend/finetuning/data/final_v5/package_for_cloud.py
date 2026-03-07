#!/usr/bin/env python3
"""
Package the training data for cloud upload.
Creates a zip file ready for RunPod/AWS/GCP.
"""

import zipfile
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_ZIP = SCRIPT_DIR / "bharatbuild_qwen_v5_training.zip"

FILES_TO_INCLUDE = [
    # Data files
    "config.json",
    "requirements.txt",
    "ROADMAP.md",
    "TRAINING_README.md",
    "CATASTROPHIC_FORGETTING_PREVENTION.md",

    # Step-by-step pipeline (CORRECT approach)
    "step1_train_sft_v1.py",
    "step2_evaluate_v1.py",
    "step3_generate_silver.py",
    "step4_train_sft_v2.py",
    "step5_train_dpo.py",
    "step6_agent_loop.py",
    "run_full_pipeline.sh",

    # Anthropic-style architecture
    "anthropic_style_pipeline.py",

    # Knowledge retention testing
    "test_knowledge_retention.py",

    # Legacy scripts
    "train_qwen.py",
    "train_dpo.py",
    "merge_and_upload.py",
    "evaluate_model.py",
    "analyze_quality.py",
]

# Also include gold samples from parent directory
GOLD_SAMPLES_DIR = SCRIPT_DIR.parent / "gold_samples"

def main():
    print("=" * 60)
    print("PACKAGING FOR CLOUD TRAINING")
    print("=" * 60)

    total_size = 0
    files_found = []

    # Main files
    for filename in FILES_TO_INCLUDE:
        filepath = SCRIPT_DIR / filename
        if filepath.exists():
            size = filepath.stat().st_size
            total_size += size
            files_found.append((filename, filepath, ""))
            print(f"  {filename}: {size / (1024*1024):.1f} MB")
        else:
            print(f"  {filename}: NOT FOUND")

    # Gold samples
    gold_file = GOLD_SAMPLES_DIR / "gold_samples.jsonl"
    if gold_file.exists():
        size = gold_file.stat().st_size
        total_size += size
        files_found.append(("gold_samples/gold_samples.jsonl", gold_file, "gold_samples/"))
        print(f"  gold_samples/gold_samples.jsonl: {size / (1024*1024):.1f} MB")

    gold_summary = GOLD_SAMPLES_DIR / "summary.json"
    if gold_summary.exists():
        files_found.append(("gold_samples/summary.json", gold_summary, "gold_samples/"))

    print(f"\nTotal size: {total_size / (1024*1024):.1f} MB")
    print(f"Files found: {len(files_found)}")

    print(f"\nCreating {OUTPUT_ZIP.name}...")

    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arc_name, filepath, prefix in files_found:
            zf.write(filepath, arc_name)
            print(f"  Added: {arc_name}")

    final_size = OUTPUT_ZIP.stat().st_size / (1024*1024)
    print(f"\nPackage created: {OUTPUT_ZIP}")
    print(f"Compressed size: {final_size:.1f} MB")

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Upload to cloud GPU instance (RunPod, AWS, GCP)")
    print("2. Unzip: unzip bharatbuild_qwen_v5_training.zip")
    print("3. Run: ./start_training.sh")
    print("=" * 60)


if __name__ == "__main__":
    main()
