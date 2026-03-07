#!/usr/bin/env python3
"""
STEP 2: Evaluate Model v1

Test on 50-100 UNSEEN prompts.
Decision gate before generating silver data.

Metrics:
- Format compliance (>95%)
- Code compiles (>85%)
- Tests pass (>70%)
- Security clean (>95%)
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import torch

SCRIPT_DIR = Path(__file__).parent
MODEL_DIR = SCRIPT_DIR / "models" / "sft_v1"
EVAL_OUTPUT = SCRIPT_DIR / "evaluation_results"

# ============================================================================
# TEST PROMPTS (NEVER IN TRAINING DATA)
# ============================================================================

TEST_PROMPTS = [
    # API Implementation
    "Create a REST API endpoint for managing shopping cart items with add, remove, update quantity, and checkout.",
    "Implement a rate-limited API endpoint that allows 100 requests per minute per user.",
    "Build a file versioning API that stores multiple versions of uploaded files.",
    "Create an API for managing user notifications with read/unread status and pagination.",
    "Implement a search API with filters, sorting, and full-text search using PostgreSQL.",

    # Bug Fixes
    "Fix this memory leak: the websocket connections are not being cleaned up when clients disconnect.",
    "Debug why this async function is causing a deadlock when called concurrently.",
    "Fix the N+1 query problem in this endpoint that fetches users with their orders.",
    "Resolve the race condition in the inventory update when multiple orders are placed simultaneously.",
    "Fix the timezone bug causing scheduled events to trigger at wrong times.",

    # Authentication & Security
    "Implement OAuth2 authorization code flow with PKCE for a mobile app.",
    "Add two-factor authentication using TOTP (Google Authenticator style).",
    "Implement API key rotation with graceful deprecation period.",
    "Create a password reset flow with secure token generation and expiry.",
    "Add CORS configuration that allows specific origins with credentials.",

    # Database Operations
    "Implement database migrations for adding a new 'subscriptions' table with foreign keys.",
    "Create a query that finds all users who haven't logged in for 30 days but have active subscriptions.",
    "Implement soft delete with automatic cleanup of records older than 90 days.",
    "Add database connection pooling with health checks and automatic reconnection.",
    "Create an audit log system that tracks all changes to sensitive tables.",

    # Testing
    "Write comprehensive unit tests for the payment processing service.",
    "Create integration tests for the user registration flow including email verification.",
    "Implement load tests for the API that simulates 1000 concurrent users.",
    "Write security tests to check for SQL injection and XSS vulnerabilities.",
    "Create end-to-end tests for the checkout process using pytest.",

    # Refactoring
    "Refactor this 500-line function into smaller, testable units following SOLID principles.",
    "Convert this synchronous API to async using FastAPI and asyncio.",
    "Extract the database logic into a repository pattern.",
    "Refactor the authentication middleware to support multiple auth strategies.",
    "Convert raw SQL queries to SQLAlchemy ORM with proper relationships.",

    # Infrastructure
    "Create a Docker Compose setup for the app with PostgreSQL, Redis, and the API.",
    "Implement health check endpoints for Kubernetes readiness and liveness probes.",
    "Add structured logging with correlation IDs for distributed tracing.",
    "Create a Celery task queue setup for background job processing.",
    "Implement circuit breaker pattern for external API calls.",

    # WebSocket & Real-time
    "Implement real-time notifications using WebSocket with room-based broadcasting.",
    "Create a live dashboard that updates metrics every 5 seconds.",
    "Build a collaborative document editing feature with conflict resolution.",
    "Implement typing indicators for a chat application.",
    "Create a real-time auction system with bid updates.",

    # File Processing
    "Implement chunked file upload for files larger than 100MB.",
    "Create an image processing pipeline that generates thumbnails and optimizes images.",
    "Build a CSV import feature that validates data and reports errors.",
    "Implement PDF generation for invoices with custom templates.",
    "Create a file encryption service for storing sensitive documents.",

    # Caching & Performance
    "Add Redis caching for frequently accessed user profiles with invalidation.",
    "Implement request deduplication to prevent duplicate form submissions.",
    "Create a query result cache with automatic invalidation on data changes.",
    "Add database query optimization with proper indexing strategy.",
    "Implement lazy loading for related objects to reduce initial query time.",
]

# ============================================================================
# EVALUATION FUNCTIONS
# ============================================================================

@dataclass
class EvalResult:
    prompt: str
    response: str
    format_ok: bool
    compiles: bool
    tests_present: bool
    security_ok: bool
    errors: List[str] = field(default_factory=list)


def check_format(response: str) -> Tuple[bool, List[str]]:
    """Check Claude-style format compliance."""
    errors = []
    required = ["PLAN:", "FILES:", "PATCH:", "COMMANDS:", "NOTES:"]

    for section in required:
        if section not in response:
            errors.append(f"Missing {section}")

    if "PATCH:" in response:
        if "*** Begin Patch" not in response:
            errors.append("Missing patch start marker")
        if "*** End Patch" not in response:
            errors.append("Missing patch end marker")
        if "---" not in response or "+++" not in response:
            errors.append("Missing diff markers")

    return len(errors) == 0, errors


def check_python_syntax(response: str) -> Tuple[bool, List[str]]:
    """Check if Python code has valid syntax."""
    errors = []

    # Extract code from patch
    patch_match = re.search(
        r"\*\*\* Begin Patch\n(.*?)\*\*\* End Patch",
        response,
        re.DOTALL
    )

    if not patch_match:
        return True, []  # No patch to check

    patch = patch_match.group(1)

    # Extract added lines (lines starting with +, not ++)
    added_lines = []
    for line in patch.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:])

    if not added_lines:
        return True, []

    code = '\n'.join(added_lines)

    try:
        compile(code, "<string>", "exec")
    except SyntaxError as e:
        errors.append(f"Syntax error: {e.msg} at line {e.lineno}")

    return len(errors) == 0, errors


def check_security(response: str) -> Tuple[bool, List[str]]:
    """Check for security anti-patterns."""
    issues = []
    patterns = [
        (r"eval\(", "Dangerous eval() usage"),
        (r"exec\(", "Dangerous exec() usage"),
        (r"shell\s*=\s*True", "Shell injection risk"),
        (r"verify\s*=\s*False", "SSL verification disabled"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r"md5\(", "Weak MD5 hash"),
    ]

    for pattern, message in patterns:
        if re.search(pattern, response, re.IGNORECASE):
            issues.append(message)

    return len(issues) == 0, issues


def check_tests_present(response: str) -> bool:
    """Check if tests are mentioned/included."""
    return "test_" in response.lower() or "pytest" in response.lower()


def generate_response(prompt: str, model, tokenizer) -> str:
    """Generate response from model."""
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

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

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
    return response


def evaluate_model():
    """Run full evaluation."""
    print("=" * 70)
    print("STEP 2: EVALUATE MODEL v1")
    print("=" * 70)

    # Check if model exists
    if not MODEL_DIR.exists():
        print(f"ERROR: Model not found at {MODEL_DIR}")
        print("Run step1_train_sft_v1.py first.")
        return

    # Load model
    print(f"\nLoading model from {MODEL_DIR}...")

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

    print(f"Testing on {len(TEST_PROMPTS)} unseen prompts...")

    results: List[EvalResult] = []

    for i, prompt in enumerate(TEST_PROMPTS):
        print(f"\n[{i+1}/{len(TEST_PROMPTS)}] {prompt[:60]}...")

        response = generate_response(prompt, model, tokenizer)

        format_ok, format_errors = check_format(response)
        compiles_ok, compile_errors = check_python_syntax(response)
        security_ok, security_errors = check_security(response)
        tests_present = check_tests_present(response)

        result = EvalResult(
            prompt=prompt,
            response=response,
            format_ok=format_ok,
            compiles=compiles_ok,
            tests_present=tests_present,
            security_ok=security_ok,
            errors=format_errors + compile_errors + security_errors
        )
        results.append(result)

        status = "OK" if (format_ok and compiles_ok and security_ok) else "ISSUES"
        print(f"  Status: {status}")

    # Calculate metrics
    total = len(results)
    format_rate = sum(1 for r in results if r.format_ok) / total * 100
    compile_rate = sum(1 for r in results if r.compiles) / total * 100
    security_rate = sum(1 for r in results if r.security_ok) / total * 100
    test_rate = sum(1 for r in results if r.tests_present) / total * 100

    # Print results
    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"Total prompts tested: {total}")
    print(f"\nMetrics:")
    print(f"  Format compliance: {format_rate:.1f}% (target: >95%)")
    print(f"  Code compiles:     {compile_rate:.1f}% (target: >85%)")
    print(f"  Security clean:    {security_rate:.1f}% (target: >95%)")
    print(f"  Tests present:     {test_rate:.1f}%")

    # Decision gate
    print("\n" + "-" * 40)
    print("DECISION GATE")
    print("-" * 40)

    passed = True
    if format_rate < 95:
        print("  [FAIL] Format compliance below 95%")
        print("         -> Fix dataset formatting")
        passed = False
    else:
        print("  [PASS] Format compliance OK")

    if compile_rate < 85:
        print("  [FAIL] Compile rate below 85%")
        print("         -> Add more gold samples with correct syntax")
        passed = False
    else:
        print("  [PASS] Compile rate OK")

    if security_rate < 95:
        print("  [FAIL] Security score below 95%")
        print("         -> Add security-focused gold samples")
        passed = False
    else:
        print("  [PASS] Security OK")

    print("\n" + "-" * 40)
    if passed:
        print("RESULT: PASSED - Proceed to Step 3 (Silver Data)")
        print("\nNext step:")
        print("  python step3_generate_silver.py")
    else:
        print("RESULT: FAILED - Fix issues before proceeding")
        print("\nRecommendations:")
        print("  1. Review failing samples")
        print("  2. Add targeted gold samples")
        print("  3. Retrain SFT v1")
    print("=" * 70)

    # Save results
    EVAL_OUTPUT.mkdir(parents=True, exist_ok=True)

    output_data = {
        "total_tested": total,
        "metrics": {
            "format_compliance": format_rate,
            "compile_rate": compile_rate,
            "security_rate": security_rate,
            "test_presence": test_rate
        },
        "passed": passed,
        "results": [
            {
                "prompt": r.prompt,
                "format_ok": r.format_ok,
                "compiles": r.compiles,
                "security_ok": r.security_ok,
                "errors": r.errors
            }
            for r in results
        ]
    }

    with open(EVAL_OUTPUT / "v1_evaluation.json", 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDetailed results saved to: {EVAL_OUTPUT / 'v1_evaluation.json'}")


if __name__ == "__main__":
    evaluate_model()
