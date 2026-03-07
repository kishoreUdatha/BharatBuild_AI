#!/usr/bin/env python3
"""
Prepare Final V4 Dataset - Comprehensive All-Technologies Dataset

Merges all datasets:
1. comprehensive_datasets/ (103K examples) - Multi-language, Java, Go, Rust, SQL, DevOps
2. public_datasets/ (75K examples) - CodeAlpaca, Magicoder, Evol-Instruct, etc.
3. all_frameworks/ (80 examples) - Vue, Angular, Flutter, Spring Boot, Go multi-file
4. multifile/ (170 examples) - React+FastAPI full-stack projects
5. complex_tasks/ (30 examples) - Debugging, explanation, refactoring
"""

import json
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set
import random

# Configuration
OUTPUT_DIR = Path(__file__).parent / "final_v4"
EVAL_RATIO = 0.05  # 5% for evaluation


def load_jsonl(file_path: Path) -> List[Dict]:
    """Load examples from JSONL file"""
    examples = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        examples.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"    Error loading {file_path}: {e}")
    return examples


def get_content_hash(example: Dict) -> str:
    """Generate hash for deduplication"""
    messages = example.get("messages", [])
    content_parts = []
    for msg in messages:
        if msg.get("role") in ["user", "assistant"]:
            content_parts.append(msg.get("content", "")[:500])
    combined = "|||".join(content_parts)
    return hashlib.md5(combined.encode()).hexdigest()


def filter_quality(example: Dict) -> bool:
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

    # Minimum length requirements
    if len(user_content) < 10 or len(assistant_content) < 50:
        return False

    # Filter harmful content
    harmful = ["hack into", "crack password", "malware", "steal data", "ddos attack"]
    combined = (user_content + assistant_content).lower()
    if any(h in combined for h in harmful):
        return False

    return True


def categorize_example(example: Dict) -> str:
    """Categorize example by technology"""
    messages = example.get("messages", [])
    combined = ""
    for msg in messages:
        combined += msg.get("content", "").lower() + " "

    # Check categories
    categories = {
        "frontend": ["react", "vue", "angular", "svelte", "next.js", "nuxt", "jsx", "tsx", "component"],
        "backend_python": ["fastapi", "django", "flask", "python", "pydantic", "uvicorn"],
        "backend_js": ["express", "nestjs", "node.js", "nodejs", "koa"],
        "backend_java": ["spring boot", "spring", "java", "maven", "gradle", "@restcontroller"],
        "backend_go": ["golang", "go ", "gin", "fiber", "goroutine"],
        "backend_rust": ["rust", "cargo", "actix", "tokio", "async fn"],
        "backend_csharp": [".net", "c#", "asp.net", "entity framework", "blazor"],
        "backend_ruby": ["rails", "ruby", "activerecord", "sinatra"],
        "backend_php": ["laravel", "php", "eloquent", "symfony"],
        "mobile_flutter": ["flutter", "dart", "widget", "scaffold", "stateful"],
        "mobile_react_native": ["react native", "expo", "native module"],
        "mobile_swift": ["swift", "swiftui", "ios", "uikit", "xcode"],
        "mobile_kotlin": ["kotlin", "android", "jetpack", "viewmodel"],
        "database": ["sql", "mysql", "postgresql", "mongodb", "redis", "graphql"],
        "devops": ["docker", "kubernetes", "terraform", "ci/cd", "jenkins", "github actions"],
        "general": []
    }

    for category, keywords in categories.items():
        if any(kw in combined for kw in keywords):
            return category

    return "general"


def collect_all_datasets() -> Dict[str, List[Dict]]:
    """Collect all datasets from different sources"""
    base_dir = Path(__file__).parent
    all_datasets = {}

    # 1. Comprehensive datasets (103K)
    print("\n1. Loading comprehensive datasets...")
    comprehensive_dir = base_dir / "comprehensive_datasets"
    if comprehensive_dir.exists():
        for file in comprehensive_dir.glob("*.jsonl"):
            name = f"comprehensive_{file.stem}"
            examples = load_jsonl(file)
            if examples:
                all_datasets[name] = examples
                print(f"   {name}: {len(examples):,} examples")

    # 2. Public datasets (75K)
    print("\n2. Loading public datasets...")
    public_dir = base_dir / "public_datasets"
    if public_dir.exists():
        for file in public_dir.glob("*.jsonl"):
            name = f"public_{file.stem}"
            examples = load_jsonl(file)
            if examples:
                all_datasets[name] = examples
                print(f"   {name}: {len(examples):,} examples")

    # 3. All frameworks (80)
    print("\n3. Loading framework datasets...")
    frameworks_dir = base_dir / "all_frameworks"
    if frameworks_dir.exists():
        for file in frameworks_dir.glob("*.jsonl"):
            name = f"framework_{file.stem}"
            examples = load_jsonl(file)
            if examples:
                all_datasets[name] = examples
                print(f"   {name}: {len(examples):,} examples")

    # 4. Multi-file projects (170)
    print("\n4. Loading multi-file project datasets...")
    multifile_dir = base_dir / "multifile"
    if multifile_dir.exists():
        for file in multifile_dir.glob("*.jsonl"):
            name = f"multifile_{file.stem}"
            examples = load_jsonl(file)
            if examples:
                all_datasets[name] = examples
                print(f"   {name}: {len(examples):,} examples")

    # 5. Complex tasks (30)
    print("\n5. Loading complex task datasets...")
    complex_dir = base_dir / "complex_tasks"
    if complex_dir.exists():
        for file in complex_dir.glob("*.jsonl"):
            name = f"complex_{file.stem}"
            examples = load_jsonl(file)
            if examples:
                all_datasets[name] = examples
                print(f"   {name}: {len(examples):,} examples")

    # 6. Previous final_v3 if exists (to ensure we don't lose anything)
    print("\n6. Loading previous final_v3 dataset...")
    v3_train = base_dir / "final_v3" / "train.jsonl"
    if v3_train.exists():
        examples = load_jsonl(v3_train)
        if examples:
            all_datasets["final_v3_train"] = examples
            print(f"   final_v3_train: {len(examples):,} examples")

    return all_datasets


def merge_and_deduplicate(all_datasets: Dict[str, List[Dict]]) -> List[Dict]:
    """Merge all datasets and remove duplicates"""
    print("\n" + "=" * 60)
    print("MERGING AND DEDUPLICATING")
    print("=" * 60)

    seen_hashes: Set[str] = set()
    merged = []

    # Priority order - custom examples first (to ensure they're included)
    priority_order = [
        # Custom generated examples (highest priority)
        "multifile_", "complex_", "framework_",
        # Then public high-quality datasets
        "public_magicoder", "public_evol",
        # Then comprehensive
        "comprehensive_",
        # Then v3 (to fill gaps)
        "final_v3",
        # Everything else
        ""
    ]

    # Sort datasets by priority
    sorted_datasets = []
    for prefix in priority_order:
        for name, examples in all_datasets.items():
            if prefix and name.startswith(prefix):
                sorted_datasets.append((name, examples))
            elif not prefix and not any(name.startswith(p) for p in priority_order[:-1] if p):
                sorted_datasets.append((name, examples))

    # Add remaining
    added_names = {name for name, _ in sorted_datasets}
    for name, examples in all_datasets.items():
        if name not in added_names:
            sorted_datasets.append((name, examples))

    # Merge with deduplication
    for name, examples in sorted_datasets:
        added = 0
        for ex in examples:
            if not filter_quality(ex):
                continue

            content_hash = get_content_hash(ex)
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                merged.append(ex)
                added += 1

        if added > 0:
            print(f"  Added {added:,} from {name}")

    print(f"\n  Total after deduplication: {len(merged):,}")
    return merged


def analyze_coverage(examples: List[Dict]) -> Dict[str, int]:
    """Analyze technology coverage"""
    coverage = {}
    for ex in examples:
        category = categorize_example(ex)
        coverage[category] = coverage.get(category, 0) + 1
    return coverage


def create_training_files(examples: List[Dict]):
    """Create train.jsonl and eval.jsonl"""
    print("\n" + "=" * 60)
    print("CREATING TRAINING FILES")
    print("=" * 60)

    # Shuffle
    random.shuffle(examples)

    # Split
    eval_size = int(len(examples) * EVAL_RATIO)
    eval_examples = examples[:eval_size]
    train_examples = examples[eval_size:]

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Write train.jsonl
    train_file = OUTPUT_DIR / "train.jsonl"
    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    # Write eval.jsonl
    eval_file = OUTPUT_DIR / "eval.jsonl"
    with open(eval_file, 'w', encoding='utf-8') as f:
        for ex in eval_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"  Train: {len(train_examples):,} examples ({train_file})")
    print(f"  Eval: {len(eval_examples):,} examples ({eval_file})")

    return train_examples, eval_examples


def create_config(train_examples: List[Dict], eval_examples: List[Dict], coverage: Dict[str, int]):
    """Create config.json with training parameters"""
    config = {
        "version": "v4",
        "description": "Comprehensive all-technologies dataset for BharatBuild AI",
        "statistics": {
            "train_examples": len(train_examples),
            "eval_examples": len(eval_examples),
            "total_examples": len(train_examples) + len(eval_examples),
            "technology_coverage": coverage,
        },
        "data_sources": [
            "comprehensive_datasets - Multi-language code from Hugging Face",
            "public_datasets - CodeAlpaca, Magicoder, Evol-Instruct",
            "all_frameworks - Vue, Angular, Flutter, Spring Boot, Go multi-file projects",
            "multifile - React+FastAPI full-stack projects",
            "complex_tasks - Debugging, explanation, refactoring examples",
        ],
        "technologies_covered": {
            "frontend": ["React", "Vue", "Angular", "Svelte", "Next.js", "Nuxt"],
            "backend_python": ["FastAPI", "Django", "Flask"],
            "backend_js": ["Express", "NestJS", "Node.js"],
            "backend_java": ["Spring Boot", "Spring"],
            "backend_go": ["Go", "Gin", "Fiber"],
            "backend_rust": ["Rust", "Actix", "Tokio"],
            "backend_csharp": [".NET", "ASP.NET", "Blazor"],
            "backend_ruby": ["Rails", "Ruby"],
            "backend_php": ["Laravel", "PHP"],
            "mobile": ["Flutter", "React Native", "Swift", "Kotlin"],
            "database": ["SQL", "MongoDB", "Redis", "GraphQL"],
            "devops": ["Docker", "Kubernetes", "Terraform", "CI/CD"],
        },
        "training_config": {
            "base_model": "Qwen/Qwen2.5-Coder-7B-Instruct",
            "max_seq_length": 4096,
            "epochs": 3,
            "batch_size": 4,
            "gradient_accumulation_steps": 8,
            "learning_rate": 2e-4,
            "lora_r": 64,
            "lora_alpha": 128,
            "lora_dropout": 0.05,
        }
    }

    config_file = OUTPUT_DIR / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    print(f"\n  Config saved to: {config_file}")
    return config


def create_training_script():
    """Create the training script"""
    script = '''#!/usr/bin/env python3
"""
Qwen Fine-tuning Script for BharatBuild AI V4
Comprehensive All-Technologies Training

Run on RunPod or any GPU server with >= 24GB VRAM

Usage:
  python train_qwen.py

Requirements:
  pip install -r requirements.txt
"""

import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

with open("config.json", "r") as f:
    config = json.load(f)

MODEL_NAME = config["training_config"]["base_model"]
TRAIN_FILE = "train.jsonl"
EVAL_FILE = "eval.jsonl"
OUTPUT_DIR = "./qwen-bharatbuild-v4"

# Training hyperparameters
EPOCHS = config["training_config"]["epochs"]
BATCH_SIZE = config["training_config"]["batch_size"]
GRADIENT_ACCUMULATION = config["training_config"]["gradient_accumulation_steps"]
LEARNING_RATE = config["training_config"]["learning_rate"]
MAX_SEQ_LENGTH = config["training_config"]["max_seq_length"]

# LoRA configuration
LORA_R = config["training_config"]["lora_r"]
LORA_ALPHA = config["training_config"]["lora_alpha"]
LORA_DROPOUT = config["training_config"]["lora_dropout"]

# ============================================================================
# SETUP
# ============================================================================

print("=" * 70)
print("QWEN FINE-TUNING FOR BHARATBUILD AI - V4 ALL TECHNOLOGIES")
print("=" * 70)
print(f"Model: {MODEL_NAME}")
print(f"Train examples: {config['statistics']['train_examples']:,}")
print(f"Eval examples: {config['statistics']['eval_examples']:,}")
print(f"Epochs: {EPOCHS}")
print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION}")
print("=" * 70)

print("\\nTechnology Coverage:")
for tech, count in sorted(config["statistics"]["technology_coverage"].items(), key=lambda x: -x[1]):
    print(f"  {tech}: {count:,}")
print("=" * 70)

# ============================================================================
# LOAD MODEL WITH QUANTIZATION
# ============================================================================

print("\\nLoading model with 4-bit quantization...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

# ============================================================================
# PREPARE FOR TRAINING
# ============================================================================

print("Preparing model for training...")

model = prepare_model_for_kbit_training(model)

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ============================================================================
# LOAD DATASET
# ============================================================================

print("\\nLoading dataset...")

def formatting_func(example):
    """Format example for training using ChatML format"""
    messages = example["messages"]
    text = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            text += f"<|im_start|>system\\n{content}<|im_end|>\\n"
        elif role == "user":
            text += f"<|im_start|>user\\n{content}<|im_end|>\\n"
        elif role == "assistant":
            text += f"<|im_start|>assistant\\n{content}<|im_end|>\\n"
    return text

dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "eval": EVAL_FILE})
print(f"Train: {len(dataset['train']):,} examples")
print(f"Eval: {len(dataset['eval']):,} examples")

# ============================================================================
# TRAINING
# ============================================================================

print("\\nStarting training...")

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    logging_steps=10,
    save_steps=500,
    eval_steps=500,
    evaluation_strategy="steps",
    save_total_limit=3,
    load_best_model_at_end=True,
    report_to="none",
    bf16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset["train"],
    eval_dataset=dataset["eval"],
    formatting_func=formatting_func,
    max_seq_length=MAX_SEQ_LENGTH,
    tokenizer=tokenizer,
    args=training_args,
    packing=True,
)

# Train
trainer.train()

# Save final model
print("\\nSaving model...")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\\n" + "=" * 70)
print("TRAINING COMPLETE!")
print("=" * 70)
print(f"Model saved to: {OUTPUT_DIR}")
print("\\nNext steps:")
print("  1. Run: python merge_and_upload.py")
print("  2. Upload to Hugging Face or deploy locally")
'''

    script_file = OUTPUT_DIR / "train_qwen.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script)

    print(f"  Training script saved to: {script_file}")


def create_merge_script():
    """Create the merge and upload script"""
    script = '''#!/usr/bin/env python3
"""
Merge LoRA weights and prepare for deployment
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import json

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

BASE_MODEL = config["training_config"]["base_model"]
LORA_MODEL = "./qwen-bharatbuild-v4"
OUTPUT_DIR = "./qwen-bharatbuild-v4-merged"

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

print("Loading LoRA weights...")
model = PeftModel.from_pretrained(model, LORA_MODEL)

print("Merging weights...")
model = model.merge_and_unload()

print(f"Saving merged model to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.save_pretrained(OUTPUT_DIR)

print("Done! Model ready for deployment.")
print("\\nTo upload to Hugging Face:")
print("  huggingface-cli login")
print("  huggingface-cli upload your-username/qwen-bharatbuild-v4 ./qwen-bharatbuild-v4-merged")
'''

    script_file = OUTPUT_DIR / "merge_and_upload.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script)

    print(f"  Merge script saved to: {script_file}")


def create_requirements():
    """Create requirements.txt"""
    requirements = """# Requirements for Qwen fine-tuning V4
torch>=2.0.0
transformers>=4.36.0
datasets>=2.14.0
peft>=0.7.0
accelerate>=0.25.0
bitsandbytes>=0.41.0
trl>=0.7.0
scipy
huggingface_hub
"""

    req_file = OUTPUT_DIR / "requirements.txt"
    with open(req_file, 'w', encoding='utf-8') as f:
        f.write(requirements)

    print(f"  Requirements saved to: {req_file}")


def main():
    print("=" * 70)
    print("PREPARING FINAL V4 DATASET - ALL TECHNOLOGIES")
    print("=" * 70)

    # Collect all datasets
    all_datasets = collect_all_datasets()

    total_raw = sum(len(examples) for examples in all_datasets.values())
    print(f"\nTotal raw examples: {total_raw:,}")

    # Merge and deduplicate
    merged = merge_and_deduplicate(all_datasets)

    # Analyze coverage
    coverage = analyze_coverage(merged)
    print("\nTechnology Coverage:")
    for tech, count in sorted(coverage.items(), key=lambda x: -x[1]):
        print(f"  {tech}: {count:,}")

    # Create training files
    train_examples, eval_examples = create_training_files(merged)

    # Create config
    create_config(train_examples, eval_examples, coverage)

    # Create scripts
    create_training_script()
    create_merge_script()
    create_requirements()

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL V4 DATASET READY!")
    print("=" * 70)
    print(f"  Total examples: {len(train_examples) + len(eval_examples):,}")
    print(f"  Train: {len(train_examples):,}")
    print(f"  Eval: {len(eval_examples):,}")
    print(f"  Location: {OUTPUT_DIR}")
    print("\nTo train:")
    print(f"  cd {OUTPUT_DIR}")
    print("  pip install -r requirements.txt")
    print("  python train_qwen.py")

    return OUTPUT_DIR


if __name__ == "__main__":
    main()
