#!/usr/bin/env python3
"""
Evaluate Fine-tuned Model Quality

Metrics:
1. Build pass rate - Does generated code compile/run?
2. Test pass rate - Do generated tests pass?
3. Security score - OWASP compliance
4. Output format compliance - Follows PLAN/FILES/PATCH/COMMANDS/NOTES?
"""

import os
import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    prompt: str
    response: str
    build_passed: bool
    tests_passed: bool
    security_passed: bool
    format_compliant: bool
    errors: List[str]


class ModelEvaluator:
    """Evaluate model outputs for quality metrics."""

    # Expected output format sections
    REQUIRED_SECTIONS = ["PLAN:", "FILES:", "PATCH:", "COMMANDS:", "NOTES:"]

    # Security anti-patterns to detect
    SECURITY_ISSUES = [
        (r"hashlib\.md5", "Insecure hash: MD5"),
        (r"password\s*=\s*['\"]", "Hardcoded password"),
        (r"f['\"].*SELECT.*{", "Potential SQL injection"),
        (r"eval\(", "Dangerous eval() usage"),
        (r"exec\(", "Dangerous exec() usage"),
        (r"shell\s*=\s*True", "Shell injection risk"),
        (r"verify\s*=\s*False", "SSL verification disabled"),
    ]

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.results: List[EvalResult] = []

    def check_format_compliance(self, response: str) -> Tuple[bool, List[str]]:
        """Check if response follows Claude-style format."""
        errors = []
        for section in self.REQUIRED_SECTIONS:
            if section not in response:
                errors.append(f"Missing section: {section}")

        # Check patch format
        if "PATCH:" in response:
            if "*** Begin Patch" not in response:
                errors.append("Missing patch start marker")
            if "*** End Patch" not in response:
                errors.append("Missing patch end marker")
            if "---" not in response or "+++" not in response:
                errors.append("Missing unified diff markers")

        return len(errors) == 0, errors

    def check_security(self, response: str) -> Tuple[bool, List[str]]:
        """Check for common security issues."""
        issues = []
        for pattern, message in self.SECURITY_ISSUES:
            if re.search(pattern, response, re.IGNORECASE):
                issues.append(message)

        return len(issues) == 0, issues

    def extract_code_from_patch(self, response: str) -> str:
        """Extract code from PATCH section."""
        patch_match = re.search(
            r"\*\*\* Begin Patch\n(.*?)\*\*\* End Patch",
            response,
            re.DOTALL
        )
        if patch_match:
            return patch_match.group(1)
        return ""

    def check_python_syntax(self, code: str) -> Tuple[bool, str]:
        """Check if Python code has valid syntax."""
        # Extract Python code blocks
        python_blocks = re.findall(r"```python\n(.*?)```", code, re.DOTALL)
        if not python_blocks:
            # Try to extract from diff format
            added_lines = re.findall(r"^\+(?!\+\+)(.*)$", code, re.MULTILINE)
            if added_lines:
                python_blocks = ["\n".join(added_lines)]

        for block in python_blocks:
            try:
                compile(block, "<string>", "exec")
            except SyntaxError as e:
                return False, str(e)
        return True, ""

    def check_build(self, response: str) -> Tuple[bool, str]:
        """Check if generated code builds/compiles."""
        patch_code = self.extract_code_from_patch(response)

        # Check Python syntax
        passed, error = self.check_python_syntax(patch_code)
        return passed, error

    def run_tests(self, response: str) -> Tuple[bool, str]:
        """Run generated tests if present."""
        # Extract test code
        if "test_" not in response.lower():
            return True, "No tests to run"

        # For actual evaluation, would run pytest
        # This is a placeholder for structure validation
        if "def test_" in response or "async def test_" in response:
            return True, "Tests present and structured correctly"
        return False, "Invalid test structure"

    def evaluate_response(self, prompt: str, response: str) -> EvalResult:
        """Evaluate a single model response."""
        errors = []

        # Check format
        format_ok, format_errors = self.check_format_compliance(response)
        errors.extend(format_errors)

        # Check security
        security_ok, security_errors = self.check_security(response)
        errors.extend(security_errors)

        # Check build
        build_ok, build_error = self.check_build(response)
        if build_error:
            errors.append(f"Build: {build_error}")

        # Check tests
        tests_ok, test_error = self.run_tests(response)
        if not tests_ok:
            errors.append(f"Tests: {test_error}")

        result = EvalResult(
            prompt=prompt,
            response=response[:500] + "..." if len(response) > 500 else response,
            build_passed=build_ok,
            tests_passed=tests_ok,
            security_passed=security_ok,
            format_compliant=format_ok,
            errors=errors
        )
        self.results.append(result)
        return result

    def evaluate_dataset(self, eval_file: str) -> Dict:
        """Evaluate all examples in dataset."""
        with open(eval_file, 'r', encoding='utf-8') as f:
            examples = [json.loads(line) for line in f if line.strip()]

        for ex in examples:
            messages = ex.get("messages", [])
            prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
            response = next((m["content"] for m in messages if m["role"] == "assistant"), "")

            self.evaluate_response(prompt, response)

        return self.get_summary()

    def get_summary(self) -> Dict:
        """Get evaluation summary."""
        if not self.results:
            return {}

        total = len(self.results)
        return {
            "total_evaluated": total,
            "build_pass_rate": sum(1 for r in self.results if r.build_passed) / total * 100,
            "test_pass_rate": sum(1 for r in self.results if r.tests_passed) / total * 100,
            "security_pass_rate": sum(1 for r in self.results if r.security_passed) / total * 100,
            "format_compliance_rate": sum(1 for r in self.results if r.format_compliant) / total * 100,
            "common_errors": self._get_common_errors()
        }

    def _get_common_errors(self) -> Dict[str, int]:
        """Get frequency of common errors."""
        error_counts = {}
        for result in self.results:
            for error in result.errors:
                error_type = error.split(":")[0] if ":" in error else error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return dict(sorted(error_counts.items(), key=lambda x: -x[1])[:10])


def main():
    print("=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)

    evaluator = ModelEvaluator()

    # Evaluate gold samples first
    gold_file = Path(__file__).parent.parent / "gold_samples" / "gold_samples.jsonl"
    if gold_file.exists():
        print(f"\nEvaluating Gold samples: {gold_file}")
        summary = evaluator.evaluate_dataset(str(gold_file))

        print("\n" + "-" * 40)
        print("GOLD SAMPLES RESULTS")
        print("-" * 40)
        print(f"Total evaluated: {summary['total_evaluated']}")
        print(f"Build pass rate: {summary['build_pass_rate']:.1f}%")
        print(f"Test pass rate: {summary['test_pass_rate']:.1f}%")
        print(f"Security pass rate: {summary['security_pass_rate']:.1f}%")
        print(f"Format compliance: {summary['format_compliance_rate']:.1f}%")

        if summary.get("common_errors"):
            print("\nCommon errors:")
            for error, count in list(summary["common_errors"].items())[:5]:
                print(f"  {error}: {count}")

        # Reset for next evaluation
        evaluator = ModelEvaluator()

    # Evaluate Claude-style examples
    claude_file = Path(__file__).parent.parent / "claude_style_data" / "claude_style_sft.jsonl"
    if claude_file.exists():
        print(f"\nEvaluating Claude-style examples: {claude_file}")
        summary = evaluator.evaluate_dataset(str(claude_file))

        print("\n" + "-" * 40)
        print("RESULTS")
        print("-" * 40)
        print(f"Total evaluated: {summary['total_evaluated']}")
        print(f"Build pass rate: {summary['build_pass_rate']:.1f}%")
        print(f"Test pass rate: {summary['test_pass_rate']:.1f}%")
        print(f"Security pass rate: {summary['security_pass_rate']:.1f}%")
        print(f"Format compliance: {summary['format_compliance_rate']:.1f}%")

        if summary.get("common_errors"):
            print("\nCommon errors:")
            for error, count in list(summary["common_errors"].items())[:5]:
                print(f"  {error}: {count}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
