#!/usr/bin/env python3
"""
STEP 5: DPO Training

Generate DPO pairs by:
1. Generate 2-4 candidates per prompt
2. Apply patches + run syntax checks
3. chosen = passes checks
4. rejected = fails / insecure

Target: 500-2k DPO pairs
This creates Model v3 with dramatically increased reliability.
"""

import json
import re
import random
import torch
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass

SCRIPT_DIR = Path(__file__).parent
MODEL_DIR = SCRIPT_DIR / "models" / "sft_v2"
DPO_OUTPUT = SCRIPT_DIR / "dpo_data"
DPO_MODEL_DIR = SCRIPT_DIR / "models" / "dpo_v3"

# ============================================================================
# DPO PAIR GENERATION
# ============================================================================

# Prompts for DPO pair generation
DPO_PROMPTS = [
    # Security-sensitive prompts
    "Implement user login with password verification",
    "Create an API endpoint that accepts user input and queries the database",
    "Build a file download endpoint",
    "Implement password reset functionality",
    "Create a payment processing endpoint",

    # Error-prone prompts
    "Implement concurrent order processing",
    "Create a caching layer for user sessions",
    "Build a WebSocket connection manager",
    "Implement database connection pooling",
    "Create a background job processor",

    # Complex implementations
    "Build a rate limiter with sliding window",
    "Implement JWT token refresh",
    "Create audit logging for sensitive operations",
    "Build a file upload with chunking",
    "Implement optimistic locking for updates",
]


def check_quality(response: str) -> Tuple[float, List[str]]:
    """
    Score a response for quality.
    Returns (score 0-1, list of issues)
    """
    score = 1.0
    issues = []

    # Format check (-0.3 per missing section)
    required = ["PLAN:", "FILES:", "PATCH:", "COMMANDS:", "NOTES:"]
    for section in required:
        if section not in response:
            score -= 0.3
            issues.append(f"Missing {section}")

    # Patch format check (-0.2 per issue)
    if "PATCH:" in response:
        if "*** Begin Patch" not in response:
            score -= 0.2
            issues.append("Missing patch start marker")
        if "*** End Patch" not in response:
            score -= 0.2
            issues.append("Missing patch end marker")

    # Security checks (-0.4 per issue)
    security_issues = [
        (r"eval\(", "Uses eval()"),
        (r"exec\(", "Uses exec()"),
        (r"shell\s*=\s*True", "Uses shell=True"),
        (r"verify\s*=\s*False", "Disables SSL verification"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r"SELECT.*\+.*user", "SQL injection risk"),
        (r'f"SELECT', "SQL injection via f-string"),
    ]

    for pattern, msg in security_issues:
        if re.search(pattern, response, re.IGNORECASE):
            score -= 0.4
            issues.append(msg)

    # Syntax check (-0.3 if fails)
    patch_match = re.search(
        r"\*\*\* Begin Patch\n(.*?)\*\*\* End Patch",
        response,
        re.DOTALL
    )
    if patch_match:
        added_lines = []
        for line in patch_match.group(1).split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])

        if added_lines:
            try:
                compile('\n'.join(added_lines), "<string>", "exec")
            except SyntaxError as e:
                score -= 0.3
                issues.append(f"Syntax error: {e.msg}")

    # Best practices checks (+0.1 per practice)
    best_practices = [
        (r"async def", "Uses async"),
        (r"try:", "Has error handling"),
        (r"raise\s+\w+Error", "Raises proper exceptions"),
        (r"logging\.", "Uses logging"),
        (r"@pytest", "Includes tests"),
    ]

    for pattern, _ in best_practices:
        if re.search(pattern, response):
            score += 0.1

    return max(0, min(1, score)), issues


def generate_candidate(prompt: str, model, tokenizer, temperature: float) -> str:
    """Generate a single candidate response."""
    system_prompt = """You are an expert software engineer. Respond with this exact structure:

PLAN:
1) First step
2) Second step
...

FILES:
- path/to/file.py
...

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed
+added
*** End Patch

COMMANDS:
- command to run
...

NOTES:
- Important notes
...

Use unified diff format. Be precise."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            temperature=temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    return response


def create_dpo_pair(prompt: str, model, tokenizer) -> Dict:
    """
    Generate candidates and create a DPO pair.
    Returns None if no valid pair can be created.
    """
    # Generate 4 candidates with varying temperatures
    candidates = []
    temperatures = [0.3, 0.5, 0.7, 0.9]

    for temp in temperatures:
        response = generate_candidate(prompt, model, tokenizer, temp)
        score, issues = check_quality(response)
        candidates.append({
            "response": response,
            "score": score,
            "issues": issues,
            "temperature": temp
        })

    # Sort by score
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # We need at least one good and one bad candidate
    best = candidates[0]
    worst = candidates[-1]

    # Only create pair if there's a meaningful difference
    if best["score"] - worst["score"] < 0.2:
        return None

    if best["score"] < 0.5:  # Best isn't good enough
        return None

    return {
        "prompt": prompt,
        "chosen": best["response"],
        "rejected": worst["response"],
        "chosen_score": best["score"],
        "rejected_score": worst["score"],
        "chosen_issues": best["issues"],
        "rejected_issues": worst["issues"]
    }


def generate_dpo_pairs(target_count: int = 500):
    """Generate DPO training pairs."""
    print("=" * 70)
    print("STEP 5A: GENERATE DPO PAIRS")
    print("=" * 70)

    if not MODEL_DIR.exists():
        print(f"ERROR: Model not found at {MODEL_DIR}")
        print("Run step4_train_sft_v2.py first.")
        return

    # Load model
    print(f"\nLoading Model v2 from {MODEL_DIR}...")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    base_model = "Qwen/Qwen2.5-Coder-7B-Instruct"

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, str(MODEL_DIR))
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    # Extend prompts to reach target
    all_prompts = DPO_PROMPTS * (target_count // len(DPO_PROMPTS) + 1)
    random.shuffle(all_prompts)
    all_prompts = all_prompts[:target_count * 2]  # Generate more to account for failures

    print(f"Generating DPO pairs from {len(all_prompts)} prompts...")

    DPO_OUTPUT.mkdir(parents=True, exist_ok=True)
    dpo_pairs = []

    for i, prompt in enumerate(all_prompts):
        if len(dpo_pairs) >= target_count:
            break

        if i % 10 == 0:
            print(f"Progress: {i}/{len(all_prompts)} | Valid pairs: {len(dpo_pairs)}")

        pair = create_dpo_pair(prompt, model, tokenizer)
        if pair:
            dpo_pairs.append(pair)

    # Save pairs
    dpo_file = DPO_OUTPUT / "dpo_pairs.jsonl"
    with open(dpo_file, 'w', encoding='utf-8') as f:
        for pair in dpo_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')

    print(f"\nGenerated {len(dpo_pairs)} DPO pairs")
    print(f"Saved to: {dpo_file}")

    # Stats
    avg_chosen = sum(p["chosen_score"] for p in dpo_pairs) / len(dpo_pairs)
    avg_rejected = sum(p["rejected_score"] for p in dpo_pairs) / len(dpo_pairs)
    print(f"\nQuality scores:")
    print(f"  Average chosen score: {avg_chosen:.2f}")
    print(f"  Average rejected score: {avg_rejected:.2f}")
    print(f"  Average gap: {avg_chosen - avg_rejected:.2f}")

    return dpo_pairs


def train_dpo():
    """Train DPO on generated pairs."""
    print("\n" + "=" * 70)
    print("STEP 5B: DPO TRAINING")
    print("=" * 70)

    dpo_file = DPO_OUTPUT / "dpo_pairs.jsonl"
    if not dpo_file.exists():
        print("ERROR: DPO pairs not found. Generate them first.")
        return

    # Count pairs
    with open(dpo_file, 'r') as f:
        pair_count = sum(1 for _ in f)
    print(f"Training on {pair_count} DPO pairs")

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model
    from trl import DPOTrainer, DPOConfig
    from datasets import load_dataset

    # Load model (start from SFT v2)
    print("\nLoading SFT v2 model...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    base_model = "Qwen/Qwen2.5-Coder-7B-Instruct"

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Load SFT v2 weights
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, str(MODEL_DIR))
    model = model.merge_and_unload()

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    # Add new LoRA for DPO
    lora_config = LoraConfig(
        r=32,
        lora_alpha=64,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)

    # Load dataset
    dataset = load_dataset("json", data_files={"train": str(dpo_file)})["train"]

    # DPO config
    DPO_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    dpo_config = DPOConfig(
        output_dir=str(DPO_MODEL_DIR),
        num_train_epochs=1,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=5e-5,
        beta=0.1,
        warmup_ratio=0.1,
        logging_steps=10,
        save_steps=100,
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
    )

    # Train
    print("\nStarting DPO training...")

    trainer = DPOTrainer(
        model=model,
        args=dpo_config,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )

    trainer.train()

    # Save
    print("\nSaving Model v3...")
    trainer.save_model(str(DPO_MODEL_DIR))
    tokenizer.save_pretrained(str(DPO_MODEL_DIR))

    info = {
        "step": "DPO v3",
        "dpo_pairs": pair_count,
        "base": "SFT v2",
        "output_format": ["PLAN", "FILES", "PATCH", "COMMANDS", "NOTES"]
    }
    with open(DPO_MODEL_DIR / "training_info.json", 'w') as f:
        json.dump(info, f, indent=2)

    print("\n" + "=" * 70)
    print("STEP 5 COMPLETE: DPO v3")
    print("=" * 70)
    print(f"Model saved to: {DPO_MODEL_DIR}")
    print("\nNext step:")
    print("  Integrate with coding agent (step6)")
    print("=" * 70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--train-only":
        train_dpo()
    else:
        # Full pipeline: generate pairs then train
        generate_dpo_pairs(target_count=500)
        train_dpo()
