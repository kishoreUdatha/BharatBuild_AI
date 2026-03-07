"""
Download Public Datasets for Qwen Fine-tuning

Sources:
1. Hugging Face - Code instruction datasets
2. GitHub - Real project examples
3. Public code generation datasets

Datasets:
- CodeAlpaca (20K instruction-following examples)
- Magicoder-OSS-Instruct (75K code instructions)
- Evol-Instruct-Code (110K evolved code instructions)
- glaive-code-assistant (136K code Q&A)
- Code-Feedback (64K code with feedback)
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import random


def check_dependencies():
    """Check and install required packages"""
    try:
        from datasets import load_dataset
        print("datasets library found")
    except ImportError:
        print("Installing datasets library...")
        os.system("pip install datasets")
        from datasets import load_dataset

    try:
        from huggingface_hub import login
        print("huggingface_hub library found")
    except ImportError:
        print("Installing huggingface_hub...")
        os.system("pip install huggingface_hub")

    return True


def convert_to_training_format(example: Dict, dataset_name: str) -> Dict:
    """Convert dataset example to our training format"""

    messages = []

    # Add system prompt
    system_prompt = "You are an expert full-stack developer. Generate clean, production-ready code with proper error handling, TypeScript types, and best practices."
    messages.append({"role": "system", "content": system_prompt})

    # Handle different dataset formats
    if dataset_name == "code_alpaca":
        # CodeAlpaca format: instruction, input, output
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output = example.get("output", "")

        user_content = instruction
        if input_text:
            user_content += f"\n\n{input_text}"

        messages.append({"role": "user", "content": user_content})
        messages.append({"role": "assistant", "content": output})

    elif dataset_name == "magicoder":
        # Magicoder format: problem, solution
        problem = example.get("problem", "") or example.get("instruction", "")
        solution = example.get("solution", "") or example.get("response", "")

        messages.append({"role": "user", "content": problem})
        messages.append({"role": "assistant", "content": solution})

    elif dataset_name == "evol_instruct":
        # Evol-Instruct format: instruction, output
        instruction = example.get("instruction", "")
        output = example.get("output", "")

        messages.append({"role": "user", "content": instruction})
        messages.append({"role": "assistant", "content": output})

    elif dataset_name == "glaive":
        # Glaive format: question, answer or conversations
        if "conversations" in example:
            for conv in example["conversations"]:
                role = "user" if conv.get("from") == "human" else "assistant"
                messages.append({"role": role, "content": conv.get("value", "")})
        else:
            question = example.get("question", "") or example.get("instruction", "")
            answer = example.get("answer", "") or example.get("response", "")
            messages.append({"role": "user", "content": question})
            messages.append({"role": "assistant", "content": answer})

    elif dataset_name == "code_feedback":
        # Code-Feedback format: query, response
        query = example.get("query", "") or example.get("instruction", "")
        response = example.get("response", "") or example.get("answer", "")

        messages.append({"role": "user", "content": query})
        messages.append({"role": "assistant", "content": response})

    else:
        # Generic format
        instruction = example.get("instruction", "") or example.get("prompt", "") or example.get("question", "")
        response = example.get("response", "") or example.get("output", "") or example.get("answer", "")

        messages.append({"role": "user", "content": instruction})
        messages.append({"role": "assistant", "content": response})

    return {"messages": messages}


def filter_quality(example: Dict) -> bool:
    """Filter low-quality examples"""
    messages = example.get("messages", [])

    if len(messages) < 2:
        return False

    # Get user and assistant content
    user_content = ""
    assistant_content = ""

    for msg in messages:
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
        elif msg.get("role") == "assistant":
            assistant_content = msg.get("content", "")

    # Filter criteria
    if len(user_content) < 10:
        return False
    if len(assistant_content) < 50:
        return False
    if not assistant_content.strip():
        return False

    # Filter harmful content
    harmful_keywords = ["hack", "crack", "exploit", "malware", "virus", "password steal"]
    content_lower = (user_content + assistant_content).lower()
    if any(kw in content_lower for kw in harmful_keywords):
        return False

    return True


def download_and_process_dataset(dataset_name: str, dataset_path: str, output_dir: Path, max_examples: int = 10000):
    """Download and process a single dataset"""
    from datasets import load_dataset

    print(f"\nDownloading {dataset_name}...")
    print(f"  Source: {dataset_path}")

    try:
        # Load dataset
        if ":" in dataset_path:
            repo, config = dataset_path.split(":")
            dataset = load_dataset(repo, config, split="train", trust_remote_code=True)
        else:
            dataset = load_dataset(dataset_path, split="train", trust_remote_code=True)

        print(f"  Loaded {len(dataset)} examples")

        # Convert and filter
        processed = []
        for example in dataset:
            converted = convert_to_training_format(example, dataset_name)
            if filter_quality(converted):
                processed.append(converted)

            if len(processed) >= max_examples:
                break

        print(f"  After filtering: {len(processed)} examples")

        # Save to file
        output_file = output_dir / f"{dataset_name}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for example in processed:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')

        print(f"  Saved to: {output_file}")
        return len(processed)

    except Exception as e:
        print(f"  Error: {e}")
        return 0


def download_all_datasets():
    """Download all public datasets"""

    check_dependencies()

    output_dir = Path(__file__).parent / "public_datasets"
    output_dir.mkdir(exist_ok=True)

    # List of public datasets for code generation
    datasets = {
        # High-quality code instruction datasets
        "code_alpaca": "sahil2801/CodeAlpaca-20k",
        "magicoder": "ise-uiuc/Magicoder-OSS-Instruct-75K",
        "evol_instruct": "nickrosh/Evol-Instruct-Code-80k-v1",
        "code_feedback": "m-a-p/Code-Feedback",

        # Additional datasets
        "python_code": "flytech/python-codes-25k",
        "code_instructions": "iamtarun/python_code_instructions_18k_alpaca",
    }

    total_examples = 0
    dataset_stats = {}

    print("=" * 60)
    print("DOWNLOADING PUBLIC DATASETS FOR CODE FINE-TUNING")
    print("=" * 60)

    for name, path in datasets.items():
        count = download_and_process_dataset(name, path, output_dir, max_examples=15000)
        dataset_stats[name] = count
        total_examples += count

    # Merge all datasets
    print("\n" + "=" * 60)
    print("MERGING ALL DATASETS")
    print("=" * 60)

    all_examples = []
    for name in datasets.keys():
        file_path = output_dir / f"{name}.jsonl"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        all_examples.append(json.loads(line))

    # Shuffle
    random.shuffle(all_examples)

    # Split train/eval (95/5)
    split_idx = int(len(all_examples) * 0.95)
    train_examples = all_examples[:split_idx]
    eval_examples = all_examples[split_idx:]

    # Save merged files
    train_file = output_dir / "merged_train.jsonl"
    eval_file = output_dir / "merged_eval.jsonl"

    with open(train_file, 'w', encoding='utf-8') as f:
        for example in train_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    with open(eval_file, 'w', encoding='utf-8') as f:
        for example in eval_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')

    print(f"\nTotal examples: {len(all_examples)}")
    print(f"Training: {len(train_examples)}")
    print(f"Evaluation: {len(eval_examples)}")
    print(f"\nSaved to:")
    print(f"  {train_file}")
    print(f"  {eval_file}")

    # Print statistics
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    for name, count in dataset_stats.items():
        print(f"  {name}: {count:,} examples")
    print(f"\n  TOTAL: {total_examples:,} examples")

    return train_file, eval_file


def download_single_dataset(dataset_name: str):
    """Download a single dataset by name"""

    check_dependencies()

    output_dir = Path(__file__).parent / "public_datasets"
    output_dir.mkdir(exist_ok=True)

    datasets = {
        "code_alpaca": "sahil2801/CodeAlpaca-20k",
        "magicoder": "ise-uiuc/Magicoder-OSS-Instruct-75K",
        "evol_instruct": "nickrosh/Evol-Instruct-Code-80k-v1",
        "code_feedback": "m-a-p/Code-Feedback",
        "python_code": "flytech/python-codes-25k",
        "code_instructions": "iamtarun/python_code_instructions_18k_alpaca",
    }

    if dataset_name not in datasets:
        print(f"Unknown dataset: {dataset_name}")
        print(f"Available: {list(datasets.keys())}")
        return

    download_and_process_dataset(dataset_name, datasets[dataset_name], output_dir)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Download specific dataset
        download_single_dataset(sys.argv[1])
    else:
        # Download all datasets
        download_all_datasets()
