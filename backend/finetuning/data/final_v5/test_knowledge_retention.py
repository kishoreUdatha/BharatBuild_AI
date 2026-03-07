#!/usr/bin/env python3
"""
KNOWLEDGE RETENTION TEST

Run this BEFORE and AFTER fine-tuning to ensure the model
doesn't lose its original capabilities (catastrophic forgetting).

Tests:
1. General coding ability (non-Claude format)
2. Multiple programming languages
3. Reasoning and explanation
4. Edge cases and error handling
"""

import torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import json

SCRIPT_DIR = Path(__file__).parent

# ============================================================================
# TEST CASES - Things the model should STILL be able to do
# ============================================================================

RETENTION_TESTS = [
    # Test 1: General Python (not Claude format)
    {
        "name": "General Python Function",
        "prompt": "Write a Python function to check if a number is prime.",
        "expected_contains": ["def", "prime", "return"],
        "should_not_contain": ["PLAN:", "PATCH:"],  # Should work WITHOUT Claude format too
    },

    # Test 2: JavaScript (different language)
    {
        "name": "JavaScript Array Methods",
        "prompt": "Write a JavaScript function to find the maximum value in an array.",
        "expected_contains": ["function", "Math.max", "return"],
    },

    # Test 3: Go language
    {
        "name": "Go HTTP Handler",
        "prompt": "Write a simple Go HTTP handler that returns 'Hello World'.",
        "expected_contains": ["func", "http", "ResponseWriter"],
    },

    # Test 4: Rust basics
    {
        "name": "Rust Struct",
        "prompt": "Define a Rust struct for a User with name and email fields.",
        "expected_contains": ["struct", "String"],
    },

    # Test 5: SQL query
    {
        "name": "SQL Query",
        "prompt": "Write a SQL query to find all users who registered in the last 30 days.",
        "expected_contains": ["SELECT", "FROM", "WHERE"],
    },

    # Test 6: Algorithm explanation
    {
        "name": "Algorithm Reasoning",
        "prompt": "Explain how binary search works and its time complexity.",
        "expected_contains": ["O(log", "middle", "half"],
    },

    # Test 7: Error handling
    {
        "name": "Error Handling",
        "prompt": "How do you handle exceptions in Python? Give an example.",
        "expected_contains": ["try", "except", "Exception"],
    },

    # Test 8: Data structures
    {
        "name": "Data Structures",
        "prompt": "Implement a simple stack in Python with push and pop methods.",
        "expected_contains": ["class", "push", "pop", "append"],
    },

    # Test 9: TypeScript
    {
        "name": "TypeScript Interface",
        "prompt": "Define a TypeScript interface for a Product with id, name, and price.",
        "expected_contains": ["interface", "number", "string"],
    },

    # Test 10: Docker
    {
        "name": "Dockerfile",
        "prompt": "Write a Dockerfile for a Python Flask application.",
        "expected_contains": ["FROM", "COPY", "RUN", "pip"],
    },
]


def load_model(model_path: str = None, base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"):
    """Load base model or fine-tuned model."""
    print(f"Loading model: {base_model}")

    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )

    if model_path and Path(model_path).exists():
        print(f"Loading LoRA adapter from: {model_path}")
        model = PeftModel.from_pretrained(model, model_path)

    return model, tokenizer


def generate_response(model, tokenizer, prompt: str, max_tokens: int = 512) -> str:
    """Generate a response from the model."""
    messages = [{"role": "user", "content": prompt}]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1]:],
        skip_special_tokens=True
    )
    return response


def run_retention_test(model, tokenizer) -> dict:
    """Run all retention tests."""
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }

    print("\n" + "=" * 70)
    print("KNOWLEDGE RETENTION TEST")
    print("=" * 70)

    for test in RETENTION_TESTS:
        print(f"\nTest: {test['name']}")
        print(f"Prompt: {test['prompt'][:50]}...")

        response = generate_response(model, tokenizer, test["prompt"])
        response_lower = response.lower()

        # Check expected content
        found_expected = []
        missing_expected = []
        for keyword in test.get("expected_contains", []):
            if keyword.lower() in response_lower:
                found_expected.append(keyword)
            else:
                missing_expected.append(keyword)

        # Check content that should NOT appear
        found_forbidden = []
        for keyword in test.get("should_not_contain", []):
            if keyword.lower() in response_lower:
                found_forbidden.append(keyword)

        # Determine pass/fail
        passed = len(missing_expected) == 0 and len(found_forbidden) == 0

        if passed:
            results["passed"] += 1
            print(f"  Status: [PASS]")
        else:
            results["failed"] += 1
            print(f"  Status: [FAIL]")
            if missing_expected:
                print(f"  Missing: {missing_expected}")
            if found_forbidden:
                print(f"  Forbidden found: {found_forbidden}")

        results["tests"].append({
            "name": test["name"],
            "passed": passed,
            "response_preview": response[:200],
        })

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test knowledge retention")
    parser.add_argument("--model-path", type=str, default=None,
                        help="Path to fine-tuned LoRA adapter (optional)")
    parser.add_argument("--save-results", type=str, default=None,
                        help="Save results to JSON file")
    args = parser.parse_args()

    # Load model
    model, tokenizer = load_model(args.model_path)

    # Run tests
    results = run_retention_test(model, tokenizer)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Passed: {results['passed']}/{len(RETENTION_TESTS)}")
    print(f"Failed: {results['failed']}/{len(RETENTION_TESTS)}")

    retention_rate = results['passed'] / len(RETENTION_TESTS) * 100
    print(f"Retention Rate: {retention_rate:.1f}%")

    if retention_rate >= 90:
        print("\n[OK] Model retains original capabilities!")
    elif retention_rate >= 70:
        print("\n[WARN] Some knowledge loss detected. Consider adjusting training.")
    else:
        print("\n[FAIL] Significant knowledge loss! Reduce epochs or learning rate.")

    # Save results
    if args.save_results:
        with open(args.save_results, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.save_results}")

    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
