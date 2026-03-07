#!/usr/bin/env python3
"""
Merge 500+ Gold Samples into Final Training Dataset.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
GOLD_DIR = BASE_DIR / "gold_samples"
FINAL_DIR = BASE_DIR / "final_v5"

def main():
    print("=" * 60)
    print("MERGING GOLD SAMPLES INTO FINAL DATASET")
    print("=" * 60)

    # Load gold samples
    gold_file = GOLD_DIR / "gold_samples.jsonl"
    gold_samples = []
    if gold_file.exists():
        with open(gold_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    gold_samples.append(json.loads(line))
    print(f"\nGold samples: {len(gold_samples)}")

    # Load existing train data
    train_file = FINAL_DIR / "train.jsonl"
    train_data = []
    if train_file.exists():
        with open(train_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    train_data.append(json.loads(line))
    print(f"Existing train: {len(train_data)}")

    # Merge
    train_data.extend(gold_samples)
    print(f"Total train: {len(train_data)}")

    # Save merged train
    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_data:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    # Update config
    config_file = FINAL_DIR / "config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config["statistics"]["train_examples"] = len(train_data)

    # Load gold sample summary
    summary_file = GOLD_DIR / "summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            gold_summary = json.load(f)
        config["gold_samples"] = gold_summary

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    print(f"\nUpdated config: {config_file}")

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
