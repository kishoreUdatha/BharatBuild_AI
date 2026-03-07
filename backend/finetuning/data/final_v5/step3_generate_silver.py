#!/usr/bin/env python3
"""
STEP 3: Generate Silver Data

Use Model v1 to generate answers for new prompts.
Auto-check quality, human review only failures.

Target: 2k-5k silver samples
"""

import json
import re
import random
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import torch

SCRIPT_DIR = Path(__file__).parent
MODEL_DIR = SCRIPT_DIR / "models" / "sft_v1"
SILVER_OUTPUT = SCRIPT_DIR / "silver_data"

# ============================================================================
# PROMPT TEMPLATES FOR SILVER DATA
# ============================================================================

# Domains
DOMAINS = [
    "e-commerce", "healthcare", "fintech", "social media", "logistics",
    "education", "real estate", "travel", "food delivery", "fitness",
    "HR management", "CRM", "inventory", "booking", "subscription"
]

# Entities
ENTITIES = [
    "User", "Product", "Order", "Payment", "Invoice", "Customer",
    "Booking", "Appointment", "Review", "Comment", "Message", "Notification",
    "Task", "Project", "Document", "Report", "Transaction", "Subscription",
    "Category", "Tag", "Event", "Ticket", "Coupon", "Discount"
]

# Frameworks
FRAMEWORKS = ["FastAPI", "Django", "Flask", "Express", "NestJS"]

# Database operations
DB_OPS = [
    "CRUD operations", "pagination", "search", "filtering", "sorting",
    "aggregation", "joins", "transactions", "migrations", "indexing"
]

# Features
FEATURES = [
    "authentication", "authorization", "file upload", "email sending",
    "SMS notifications", "webhooks", "caching", "rate limiting",
    "logging", "monitoring", "background jobs", "scheduled tasks",
    "real-time updates", "search", "export to CSV/PDF"
]

# Bug types
BUG_TYPES = [
    ("memory leak", "Objects not garbage collected"),
    ("race condition", "Concurrent access without locking"),
    ("N+1 query", "Lazy loading in loops"),
    ("deadlock", "Circular lock dependencies"),
    ("connection pool exhaustion", "Connections not released"),
    ("timezone issue", "Naive datetime handling"),
    ("encoding error", "UTF-8 not handled properly"),
    ("null pointer", "Missing null checks"),
    ("off-by-one", "Incorrect loop bounds"),
    ("SQL injection", "User input in queries"),
]

# ============================================================================
# PROMPT GENERATORS
# ============================================================================

def generate_api_prompts(count: int) -> List[str]:
    """Generate API implementation prompts."""
    prompts = []
    for _ in range(count):
        entity = random.choice(ENTITIES)
        framework = random.choice(FRAMEWORKS)
        db_op = random.choice(DB_OPS)
        feature = random.choice(FEATURES)
        domain = random.choice(DOMAINS)

        templates = [
            f"Implement a REST API for {entity} management in a {domain} app using {framework} with {db_op}.",
            f"Create {entity} endpoints with {feature} using {framework}.",
            f"Build a {entity} service for {domain} with {db_op} and {feature}.",
            f"Implement {entity} CRUD with validation, error handling, and {feature} in {framework}.",
        ]
        prompts.append(random.choice(templates))
    return prompts


def generate_bug_fix_prompts(count: int) -> List[str]:
    """Generate bug fix prompts."""
    prompts = []
    for _ in range(count):
        bug_type, cause = random.choice(BUG_TYPES)
        entity = random.choice(ENTITIES)
        framework = random.choice(FRAMEWORKS)

        templates = [
            f"Fix the {bug_type} in the {entity} service. Error: {cause}",
            f"Debug and fix: {bug_type} occurring in {entity} API. Root cause: {cause}",
            f"Production error: {bug_type} in {framework} {entity} endpoint. Details: {cause}",
        ]
        prompts.append(random.choice(templates))
    return prompts


def generate_test_prompts(count: int) -> List[str]:
    """Generate test writing prompts."""
    prompts = []
    test_types = ["unit", "integration", "e2e", "performance", "security"]

    for _ in range(count):
        entity = random.choice(ENTITIES)
        test_type = random.choice(test_types)
        feature = random.choice(FEATURES)

        templates = [
            f"Write {test_type} tests for the {entity} service.",
            f"Create comprehensive {test_type} tests for {feature} in {entity} API.",
            f"Implement {test_type} tests covering edge cases for {entity} operations.",
        ]
        prompts.append(random.choice(templates))
    return prompts


def generate_refactor_prompts(count: int) -> List[str]:
    """Generate refactoring prompts."""
    patterns = [
        "Repository Pattern", "Service Layer", "Factory Pattern",
        "Strategy Pattern", "SOLID principles", "Clean Architecture",
        "Dependency Injection", "CQRS", "Event Sourcing"
    ]
    prompts = []

    for _ in range(count):
        entity = random.choice(ENTITIES)
        pattern = random.choice(patterns)

        templates = [
            f"Refactor the {entity} code to follow {pattern}.",
            f"Apply {pattern} to improve testability of {entity} service.",
            f"Restructure {entity} module using {pattern}.",
        ]
        prompts.append(random.choice(templates))
    return prompts


def generate_security_prompts(count: int) -> List[str]:
    """Generate security implementation prompts."""
    security_features = [
        "JWT authentication", "OAuth2", "RBAC", "API key auth",
        "input validation", "rate limiting", "CORS", "CSRF protection",
        "password hashing", "encryption", "audit logging"
    ]
    prompts = []

    for _ in range(count):
        feature = random.choice(security_features)
        entity = random.choice(ENTITIES)

        templates = [
            f"Implement {feature} for the {entity} API.",
            f"Add {feature} to secure {entity} endpoints.",
            f"Create a secure {entity} service with {feature}.",
        ]
        prompts.append(random.choice(templates))
    return prompts


# ============================================================================
# QUALITY CHECKS
# ============================================================================

def check_format(response: str) -> bool:
    """Quick format check."""
    required = ["PLAN:", "FILES:", "PATCH:", "COMMANDS:", "NOTES:"]
    return all(s in response for s in required)


def check_patch_valid(response: str) -> bool:
    """Check if patch format is valid."""
    if "*** Begin Patch" not in response:
        return False
    if "*** End Patch" not in response:
        return False
    if "---" not in response or "+++" not in response:
        return False
    return True


def check_syntax(response: str) -> bool:
    """Check Python syntax in patch."""
    patch_match = re.search(
        r"\*\*\* Begin Patch\n(.*?)\*\*\* End Patch",
        response,
        re.DOTALL
    )
    if not patch_match:
        return True

    added_lines = []
    for line in patch_match.group(1).split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:])

    if not added_lines:
        return True

    try:
        compile('\n'.join(added_lines), "<string>", "exec")
        return True
    except SyntaxError:
        return False


def check_security(response: str) -> bool:
    """Check for security issues."""
    bad_patterns = [
        r"eval\(", r"exec\(", r"shell\s*=\s*True",
        r"verify\s*=\s*False", r'password\s*=\s*["\'][^"\']+["\']'
    ]
    for pattern in bad_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            return False
    return True


def validate_sample(prompt: str, response: str) -> Tuple[bool, str]:
    """Validate a generated sample."""
    if not check_format(response):
        return False, "format_invalid"
    if not check_patch_valid(response):
        return False, "patch_invalid"
    if not check_syntax(response):
        return False, "syntax_error"
    if not check_security(response):
        return False, "security_issue"
    return True, "ok"


# ============================================================================
# MAIN GENERATOR
# ============================================================================

SYSTEM_PROMPT = """You are an expert software engineer. Respond with this exact structure:

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


def generate_silver_data(target_count: int = 3000):
    """Generate silver data using Model v1."""
    print("=" * 70)
    print("STEP 3: GENERATE SILVER DATA")
    print("=" * 70)

    # Check model
    if not MODEL_DIR.exists():
        print(f"ERROR: Model not found at {MODEL_DIR}")
        print("Run step1 and step2 first.")
        return

    # Generate prompts
    print("\nGenerating prompts...")
    all_prompts = []

    # Distribution: 40% API, 25% bugs, 15% tests, 10% refactor, 10% security
    all_prompts.extend(generate_api_prompts(int(target_count * 0.40)))
    all_prompts.extend(generate_bug_fix_prompts(int(target_count * 0.25)))
    all_prompts.extend(generate_test_prompts(int(target_count * 0.15)))
    all_prompts.extend(generate_refactor_prompts(int(target_count * 0.10)))
    all_prompts.extend(generate_security_prompts(int(target_count * 0.10)))

    random.shuffle(all_prompts)
    print(f"Generated {len(all_prompts)} prompts")

    # Load model
    print("\nLoading Model v1...")
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

    # Generate responses
    print("\nGenerating silver samples...")
    SILVER_OUTPUT.mkdir(parents=True, exist_ok=True)

    valid_samples = []
    invalid_samples = []
    stats = {"ok": 0, "format_invalid": 0, "patch_invalid": 0, "syntax_error": 0, "security_issue": 0}

    for i, prompt in enumerate(all_prompts):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(all_prompts)} | Valid: {len(valid_samples)}")

        # Generate
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=2048,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

        # Validate
        is_valid, reason = validate_sample(prompt, response)
        stats[reason] += 1

        sample = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ]
        }

        if is_valid:
            valid_samples.append(sample)
        else:
            sample["rejection_reason"] = reason
            invalid_samples.append(sample)

    # Save results
    print("\n" + "-" * 40)
    print("GENERATION COMPLETE")
    print("-" * 40)
    print(f"Valid samples: {len(valid_samples)}")
    print(f"Invalid samples: {len(invalid_samples)}")
    print(f"\nBreakdown:")
    for reason, count in stats.items():
        print(f"  {reason}: {count}")

    # Save valid samples
    silver_file = SILVER_OUTPUT / "silver_samples.jsonl"
    with open(silver_file, 'w', encoding='utf-8') as f:
        for sample in valid_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    print(f"\nSaved valid samples to: {silver_file}")

    # Save invalid for review
    invalid_file = SILVER_OUTPUT / "needs_review.jsonl"
    with open(invalid_file, 'w', encoding='utf-8') as f:
        for sample in invalid_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    print(f"Saved samples for review to: {invalid_file}")

    # Summary
    summary = {
        "total_generated": len(all_prompts),
        "valid_samples": len(valid_samples),
        "invalid_samples": len(invalid_samples),
        "validation_stats": stats
    }
    with open(SILVER_OUTPUT / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print("STEP 3 COMPLETE")
    print("=" * 70)
    print(f"Silver samples ready: {len(valid_samples)}")
    print("\nNext step:")
    print("  1. Review samples in needs_review.jsonl (optional)")
    print("  2. Run: python step4_train_sft_v2.py")
    print("=" * 70)


if __name__ == "__main__":
    generate_silver_data(target_count=3000)
