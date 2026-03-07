"""
Merge all training data into final dataset for Qwen fine-tuning

Combines:
1. Multi-file project examples (full-stack projects)
2. Complex task examples (debugging, explanation, refactoring)
3. Existing training data (CRUD, components, etc.)

Output:
- v2/train.jsonl - Combined training data
- v2/eval.jsonl - Combined evaluation data
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Set


def load_jsonl(file_path: Path) -> List[Dict]:
    """Load JSONL file"""
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}")
        return []

    examples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Error parsing line: {e}")
    return examples


def save_jsonl(examples: List[Dict], file_path: Path):
    """Save examples to JSONL file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')


def deduplicate_examples(examples: List[Dict]) -> List[Dict]:
    """Remove duplicate examples based on user prompt"""
    seen_prompts: Set[str] = set()
    unique_examples = []

    for example in examples:
        # Get user prompt for deduplication
        user_prompt = ""
        for msg in example.get("messages", []):
            if msg.get("role") == "user":
                user_prompt = msg.get("content", "")[:200]  # First 200 chars
                break

        if user_prompt and user_prompt not in seen_prompts:
            seen_prompts.add(user_prompt)
            unique_examples.append(example)

    return unique_examples


def filter_quality_examples(examples: List[Dict], min_response_length: int = 100) -> List[Dict]:
    """Filter out low-quality examples"""
    quality_examples = []

    for example in examples:
        # Get assistant response
        assistant_response = ""
        for msg in example.get("messages", []):
            if msg.get("role") == "assistant":
                assistant_response = msg.get("content", "")
                break

        # Filter criteria
        if len(assistant_response) < min_response_length:
            continue  # Too short

        # Check for placeholder patterns
        if "{username}" in assistant_response or "{password}" in assistant_response:
            continue  # Has unresolved placeholders

        # Check for repeated "please please" patterns
        user_prompt = ""
        for msg in example.get("messages", []):
            if msg.get("role") == "user":
                user_prompt = msg.get("content", "")
                break

        if "please please please" in user_prompt.lower():
            continue  # Low quality prompt

        quality_examples.append(example)

    return quality_examples


def merge_all_training_data():
    """Merge all training data sources"""

    data_dir = Path(__file__).parent

    print("Loading training data sources...")

    # Load all training data
    sources = {
        "multifile_train": data_dir / "multifile" / "train.jsonl",
        "multifile_eval": data_dir / "multifile" / "eval.jsonl",
        "complex_train": data_dir / "complex_tasks" / "train.jsonl",
        "complex_eval": data_dir / "complex_tasks" / "eval.jsonl",
        "existing_ultimate": data_dir / "ultimate" / "train.jsonl",
    }

    all_train = []
    all_eval = []

    for name, path in sources.items():
        examples = load_jsonl(path)
        print(f"  {name}: {len(examples)} examples")

        if "eval" in name:
            all_eval.extend(examples)
        else:
            all_train.extend(examples)

    print(f"\nTotal before processing: {len(all_train)} train, {len(all_eval)} eval")

    # Filter quality
    print("\nFiltering quality...")
    all_train = filter_quality_examples(all_train)
    all_eval = filter_quality_examples(all_eval)
    print(f"After quality filter: {len(all_train)} train, {len(all_eval)} eval")

    # Deduplicate
    print("\nDeduplicating...")
    all_train = deduplicate_examples(all_train)
    all_eval = deduplicate_examples(all_eval)
    print(f"After deduplication: {len(all_train)} train, {len(all_eval)} eval")

    # Shuffle
    random.shuffle(all_train)
    random.shuffle(all_eval)

    # Save to v2 folder
    output_dir = data_dir / "v2_multifile"
    output_dir.mkdir(exist_ok=True)

    train_file = output_dir / "train.jsonl"
    eval_file = output_dir / "eval.jsonl"

    save_jsonl(all_train, train_file)
    save_jsonl(all_eval, eval_file)

    print(f"\n{'='*60}")
    print("FINAL DATASET CREATED")
    print(f"{'='*60}")
    print(f"Training examples: {len(all_train)}")
    print(f"Evaluation examples: {len(all_eval)}")
    print(f"\nSaved to:")
    print(f"  {train_file}")
    print(f"  {eval_file}")

    # Print sample
    print(f"\n{'='*60}")
    print("SAMPLE TRAINING EXAMPLE")
    print(f"{'='*60}")
    if all_train:
        sample = all_train[0]
        for msg in sample.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content", "")[:200]
            print(f"\n[{role.upper()}]")
            print(content + "..." if len(msg.get("content", "")) > 200 else content)

    # Print statistics
    print(f"\n{'='*60}")
    print("DATASET STATISTICS")
    print(f"{'='*60}")

    # Count by type
    multifile_count = 0
    complex_count = 0
    simple_count = 0

    for example in all_train:
        assistant_response = ""
        for msg in example.get("messages", []):
            if msg.get("role") == "assistant":
                assistant_response = msg.get("content", "")
                break

        if "## Project Structure" in assistant_response or "docker-compose" in assistant_response:
            multifile_count += 1
        elif "## Error Analysis" in assistant_response or "## Code Review" in assistant_response:
            complex_count += 1
        else:
            simple_count += 1

    print(f"Multi-file project examples: {multifile_count}")
    print(f"Complex task examples: {complex_count}")
    print(f"Simple task examples: {simple_count}")

    return len(all_train), len(all_eval)


if __name__ == "__main__":
    merge_all_training_data()
