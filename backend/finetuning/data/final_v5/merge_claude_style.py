#!/usr/bin/env python3
"""
Merge Claude-style training data into final dataset.
Creates the complete training package with:
1. SFT data (spec->impl, bug->fix, tests, security)
2. DPO preference pairs
3. Updated training configuration
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CLAUDE_DIR = BASE_DIR / "claude_style_data"
FINAL_DIR = Path(__file__).parent

def main():
    print("=" * 60)
    print("MERGING CLAUDE-STYLE DATA INTO FINAL DATASET")
    print("=" * 60)

    # Load Claude-style SFT data
    claude_sft = []
    sft_file = CLAUDE_DIR / "claude_style_sft.jsonl"
    if sft_file.exists():
        with open(sft_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    claude_sft.append(json.loads(line))
    print(f"\nClaude-style SFT: {len(claude_sft)}")

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
    train_data.extend(claude_sft)
    print(f"Total train: {len(train_data)}")

    # Save merged train
    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_data:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    # Load and merge DPO data
    existing_dpo = []
    dpo_file = FINAL_DIR / "dpo_pairs.jsonl"
    if dpo_file.exists():
        with open(dpo_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    existing_dpo.append(json.loads(line))

    claude_dpo = []
    claude_dpo_file = CLAUDE_DIR / "claude_style_dpo.jsonl"
    if claude_dpo_file.exists():
        with open(claude_dpo_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    claude_dpo.append(json.loads(line))

    all_dpo = existing_dpo + claude_dpo
    print(f"\nTotal DPO pairs: {len(all_dpo)}")

    with open(dpo_file, 'w', encoding='utf-8') as f:
        for pair in all_dpo:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    # Update config
    config_file = FINAL_DIR / "config.json"
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config["statistics"]["train_examples"] = len(train_data)
    config["statistics"]["dpo_pairs"] = len(all_dpo)
    config["claude_style_format"] = {
        "output_sections": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"],
        "patch_format": "unified_diff",
        "examples_added": len(claude_sft)
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
