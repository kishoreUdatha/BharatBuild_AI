"""
Download Comprehensive Datasets for All Technologies

Covers:
1. Languages: Python, JavaScript, TypeScript, Java, Go, Rust, C#, Ruby, PHP, Kotlin, Swift, Dart
2. Frontend: React, Vue, Angular, Svelte, Next.js
3. Backend: FastAPI, Django, Flask, Express, NestJS, Spring Boot, .NET, Go, Rails, Laravel
4. Mobile: Flutter, React Native, Swift, Kotlin
5. DevOps: Docker, Kubernetes, Terraform, CI/CD
6. Databases: SQL, MongoDB, Redis, GraphQL
"""

import json
import os
import random
from pathlib import Path
from typing import List, Dict, Any


def check_dependencies():
    """Install required packages"""
    try:
        from datasets import load_dataset
        return True
    except ImportError:
        os.system("pip install datasets huggingface_hub -q")
        return True


def convert_to_training_format(example: Dict, dataset_type: str) -> Dict:
    """Convert to training format"""
    messages = []

    # System prompts based on type
    system_prompts = {
        "general": "You are an expert software developer. Generate clean, production-ready code with proper error handling and best practices.",
        "java": "You are an expert Java developer specializing in Spring Boot, Maven, and enterprise applications. Generate production-ready Java code.",
        "go": "You are an expert Go developer. Generate idiomatic, efficient Go code with proper error handling.",
        "rust": "You are an expert Rust developer. Generate safe, efficient Rust code following best practices.",
        "csharp": "You are an expert C# developer specializing in .NET Core and ASP.NET. Generate production-ready C# code.",
        "ruby": "You are an expert Ruby developer specializing in Ruby on Rails. Generate clean, idiomatic Ruby code.",
        "php": "You are an expert PHP developer specializing in Laravel. Generate modern, secure PHP code.",
        "mobile": "You are an expert mobile developer. Generate production-ready mobile app code with proper architecture.",
        "devops": "You are an expert DevOps engineer. Generate production-ready infrastructure code and configurations.",
        "frontend": "You are an expert frontend developer specializing in modern JavaScript frameworks. Generate clean, responsive UI code.",
        "fullstack": "You are an expert full-stack developer. Generate complete, production-ready applications with frontend, backend, and database.",
    }

    system_prompt = system_prompts.get(dataset_type, system_prompts["general"])
    messages.append({"role": "system", "content": system_prompt})

    # Handle different dataset formats
    instruction = ""
    response = ""

    # Common field names
    instruction_fields = ["instruction", "prompt", "question", "input", "problem", "query", "text"]
    response_fields = ["output", "response", "answer", "solution", "completion", "code"]

    for field in instruction_fields:
        if field in example and example[field]:
            instruction = str(example[field])
            break

    for field in response_fields:
        if field in example and example[field]:
            response = str(example[field])
            break

    # Handle conversations format
    if "conversations" in example:
        for conv in example["conversations"]:
            role = "user" if conv.get("from") in ["human", "user"] else "assistant"
            content = conv.get("value", "") or conv.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
        return {"messages": messages}

    # Handle messages format
    if "messages" in example:
        for msg in example["messages"]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
        return {"messages": messages}

    if instruction and response:
        messages.append({"role": "user", "content": instruction})
        messages.append({"role": "assistant", "content": response})

    return {"messages": messages}


def filter_quality(example: Dict, min_response_len: int = 50) -> bool:
    """Filter low-quality examples"""
    messages = example.get("messages", [])
    if len(messages) < 2:
        return False

    user_content = ""
    assistant_content = ""

    for msg in messages:
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
        elif msg.get("role") == "assistant":
            assistant_content = msg.get("content", "")

    if len(user_content) < 10 or len(assistant_content) < min_response_len:
        return False

    # Filter harmful content
    harmful = ["hack", "crack", "exploit", "malware", "steal password", "ddos"]
    combined = (user_content + assistant_content).lower()
    if any(h in combined for h in harmful):
        return False

    return True


def download_dataset(name: str, path: str, output_dir: Path, dataset_type: str, max_examples: int = 10000, config: str = None):
    """Download and process a single dataset"""
    from datasets import load_dataset

    print(f"\n  Downloading {name}...")
    print(f"    Source: {path}")

    try:
        # Load dataset
        if config:
            dataset = load_dataset(path, config, split="train", trust_remote_code=True)
        else:
            dataset = load_dataset(path, split="train", trust_remote_code=True)

        print(f"    Loaded: {len(dataset):,} examples")

        # Convert and filter
        processed = []
        for example in dataset:
            converted = convert_to_training_format(dict(example), dataset_type)
            if filter_quality(converted):
                processed.append(converted)
            if len(processed) >= max_examples:
                break

        print(f"    After filter: {len(processed):,} examples")

        # Save
        output_file = output_dir / f"{name}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for ex in processed:
                f.write(json.dumps(ex, ensure_ascii=False) + '\n')

        return len(processed)

    except Exception as e:
        print(f"    Error: {e}")
        return 0


def download_all_comprehensive():
    """Download all comprehensive datasets"""

    check_dependencies()

    output_dir = Path(__file__).parent / "comprehensive_datasets"
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("DOWNLOADING COMPREHENSIVE DATASETS FOR ALL TECHNOLOGIES")
    print("=" * 70)

    # All datasets organized by category
    datasets = {
        # ==================== MULTI-LANGUAGE CODE ====================
        "Multi-Language": {
            "starcoder_data": ("bigcode/starcoderdata", "python", "general", 15000),
            "code_alpaca": ("sahil2801/CodeAlpaca-20k", None, "general", 15000),
            "code_instructions": ("iamtarun/python_code_instructions_18k_alpaca", None, "general", 15000),
        },

        # ==================== JAVA ====================
        "Java": {
            "java_code": ("flytech/java-codes-25k", None, "java", 10000),
            "java_exercises": ("Nan-Do/java-code-exercises", None, "java", 5000),
        },

        # ==================== GO ====================
        "Go": {
            "go_code": ("flytech/go-codes-30k", None, "go", 10000),
        },

        # ==================== RUST ====================
        "Rust": {
            "rust_code": ("flytech/rust-codes-10k", None, "rust", 8000),
        },

        # ==================== JAVASCRIPT/TYPESCRIPT ====================
        "JavaScript": {
            "js_code": ("flytech/javascript-codes-40k", None, "frontend", 15000),
            "typescript_code": ("flytech/typescript-codes-25k", None, "frontend", 10000),
        },

        # ==================== HIGH QUALITY INSTRUCTION DATASETS ====================
        "Instructions": {
            "magicoder": ("ise-uiuc/Magicoder-OSS-Instruct-75K", None, "fullstack", 20000),
            "evol_instruct": ("nickrosh/Evol-Instruct-Code-80k-v1", None, "fullstack", 20000),
            "glaive_code": ("glaiveai/glaive-code-assistant", None, "fullstack", 15000),
            "code_feedback": ("m-a-p/Code-Feedback", None, "fullstack", 10000),
        },

        # ==================== SQL & DATABASES ====================
        "SQL": {
            "sql_create": ("b-mc2/sql-create-context", None, "general", 8000),
            "spider_sql": ("spider", None, "general", 5000),
        },

        # ==================== SHELL/DEVOPS ====================
        "DevOps": {
            "shell_code": ("flytech/shell-codes-10k", None, "devops", 8000),
        },
    }

    total_examples = 0
    category_stats = {}

    for category, category_datasets in datasets.items():
        print(f"\n{'='*70}")
        print(f"CATEGORY: {category}")
        print(f"{'='*70}")

        category_count = 0

        for name, (path, config, dtype, max_ex) in category_datasets.items():
            count = download_dataset(name, path, output_dir, dtype, max_ex, config)
            category_count += count
            total_examples += count

        category_stats[category] = category_count

    # Print summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)

    for category, count in category_stats.items():
        print(f"  {category}: {count:,} examples")

    print(f"\n  TOTAL: {total_examples:,} examples")
    print(f"  Location: {output_dir}")

    return output_dir, total_examples


if __name__ == "__main__":
    download_all_comprehensive()
