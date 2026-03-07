#!/usr/bin/env python3
"""
Merge coding agent training data into final_v5 dataset
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
CODING_AGENT_DIR = BASE_DIR / "coding_agent_data"
FINAL_DIR = BASE_DIR / "final_v5"

def main():
    print("=" * 70)
    print("MERGING CODING AGENT DATA INTO FINAL DATASET")
    print("=" * 70)

    # Read coding agent SFT data
    sft_file = CODING_AGENT_DIR / "sft_train.jsonl"
    coding_agent_examples = []
    if sft_file.exists():
        with open(sft_file, 'r', encoding='utf-8') as f:
            coding_agent_examples = [json.loads(line) for line in f if line.strip()]

    print(f"\nCoding Agent SFT Examples: {len(coding_agent_examples)}")

    # Read existing train data
    train_file = FINAL_DIR / "train.jsonl"
    train_data = []
    with open(train_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                train_data.append(json.loads(line))

    print(f"Existing Train Examples: {len(train_data)}")

    # Add coding agent examples
    train_data.extend(coding_agent_examples)

    # Save updated train data
    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_data:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"New Total Train Examples: {len(train_data)}")

    # Update config
    config_file = FINAL_DIR / "config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config["statistics"]["train_examples"] = len(train_data)
    config["statistics"]["total_examples"] = len(train_data) + config["statistics"]["eval_examples"]
    config["coding_agent_data"] = {
        "sft_examples": len(coding_agent_examples),
        "categories": ["spec_to_implementation", "bug_to_fix", "tdd"]
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    # Read DPO data
    dpo_file = CODING_AGENT_DIR / "dpo_pairs.jsonl"
    dpo_pairs = []
    if dpo_file.exists():
        with open(dpo_file, 'r', encoding='utf-8') as f:
            dpo_pairs = [json.loads(line) for line in f if line.strip()]

    # Save DPO data to final directory
    dpo_output = FINAL_DIR / "dpo_pairs.jsonl"
    with open(dpo_output, 'w', encoding='utf-8') as f:
        for pair in dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"\nDPO Pairs saved: {len(dpo_pairs)}")

    print("\n" + "=" * 70)
    print("MERGE COMPLETE")
    print("=" * 70)
    print(f"Train file: {train_file}")
    print(f"DPO file: {dpo_output}")


if __name__ == "__main__":
    main()
