#!/usr/bin/env python3
"""
Detailed Quality Analysis of Generated Gold Samples
"""

import json
import re
from pathlib import Path
from collections import Counter

GOLD_FILE = Path(__file__).parent.parent / "gold_samples" / "gold_samples.jsonl"

def analyze_samples():
    print("=" * 70)
    print("GOLD SAMPLES QUALITY ANALYSIS")
    print("=" * 70)

    samples = []
    with open(GOLD_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    print(f"\nTotal samples: {len(samples)}")

    # Category breakdown
    categories = Counter(s.get("category", "unknown") for s in samples)
    print("\n1. CATEGORY DISTRIBUTION")
    print("-" * 40)
    for cat, count in categories.most_common():
        pct = count / len(samples) * 100
        print(f"   {cat}: {count} ({pct:.1f}%)")

    # Format compliance check
    print("\n2. FORMAT COMPLIANCE")
    print("-" * 40)

    sections = ["PLAN:", "FILES:", "PATCH:", "COMMANDS:", "NOTES:"]
    section_counts = {s: 0 for s in sections}
    patch_markers = {"*** Begin Patch": 0, "*** End Patch": 0, "---": 0, "+++": 0}

    for sample in samples:
        response = sample["messages"][-1]["content"]
        for section in sections:
            if section in response:
                section_counts[section] += 1
        for marker in patch_markers:
            if marker in response:
                patch_markers[marker] += 1

    for section, count in section_counts.items():
        pct = count / len(samples) * 100
        status = "[OK]" if pct >= 95 else "[WARN]" if pct >= 80 else "[FAIL]"
        print(f"   {status} {section} {count}/{len(samples)} ({pct:.1f}%)")

    print("\n   Patch Format:")
    for marker, count in patch_markers.items():
        pct = count / len(samples) * 100
        print(f"     {marker}: {pct:.1f}%")

    # Code quality checks
    print("\n3. CODE QUALITY METRICS")
    print("-" * 40)

    # Security patterns
    security_issues = [
        (r"eval\(", "eval() usage"),
        (r"exec\(", "exec() usage"),
        (r"shell\s*=\s*True", "shell=True"),
        (r"verify\s*=\s*False", "SSL verify=False"),
        (r"password\s*=\s*['\"]", "Hardcoded password"),
        (r"md5\(", "MD5 hash"),
    ]

    security_found = Counter()
    for sample in samples:
        response = sample["messages"][-1]["content"]
        for pattern, name in security_issues:
            if re.search(pattern, response, re.IGNORECASE):
                security_found[name] += 1

    secure_count = len(samples) - sum(security_found.values())
    print(f"   Security-compliant samples: {secure_count}/{len(samples)} ({secure_count/len(samples)*100:.1f}%)")

    if security_found:
        print("   Issues found:")
        for issue, count in security_found.most_common():
            print(f"     - {issue}: {count}")

    # Best practices
    print("\n4. BEST PRACTICES")
    print("-" * 40)

    best_practices = {
        "Type hints": r"def \w+\([^)]*:\s*\w+",
        "Docstrings": r'"""[^"]+"""',
        "Error handling": r"try:|except|raise",
        "Async/await": r"async def|await",
        "Dependency injection": r"Depends\(",
        "Pydantic models": r"class \w+\(BaseModel\)",
        "SQLAlchemy models": r"class \w+\(Base\)",
        "pytest fixtures": r"@pytest\.fixture",
        "Type validation": r"Field\(|validator|@validator",
    }

    practice_counts = Counter()
    for sample in samples:
        response = sample["messages"][-1]["content"]
        for practice, pattern in best_practices.items():
            if re.search(pattern, response):
                practice_counts[practice] += 1

    for practice, count in sorted(practice_counts.items(), key=lambda x: -x[1]):
        pct = count / len(samples) * 100
        print(f"   {practice}: {count} samples ({pct:.1f}%)")

    # Response length analysis
    print("\n5. RESPONSE LENGTH")
    print("-" * 40)

    lengths = [len(s["messages"][-1]["content"]) for s in samples]
    avg_len = sum(lengths) / len(lengths)
    min_len = min(lengths)
    max_len = max(lengths)

    print(f"   Average: {avg_len:.0f} chars")
    print(f"   Min: {min_len} chars")
    print(f"   Max: {max_len} chars")

    # Token estimate (rough: 4 chars = 1 token)
    avg_tokens = avg_len / 4
    print(f"   Estimated avg tokens: ~{avg_tokens:.0f}")

    # Sample quality score
    print("\n6. OVERALL QUALITY SCORE")
    print("-" * 40)

    format_score = sum(section_counts.values()) / (len(sections) * len(samples)) * 100
    security_score = secure_count / len(samples) * 100
    practice_score = sum(practice_counts.values()) / (len(best_practices) * len(samples)) * 100

    overall = (format_score * 0.4 + security_score * 0.4 + practice_score * 0.2)

    print(f"   Format compliance: {format_score:.1f}%")
    print(f"   Security score: {security_score:.1f}%")
    print(f"   Best practices: {practice_score:.1f}%")
    print(f"   -------------------------")
    print(f"   OVERALL SCORE: {overall:.1f}%")

    # Show sample
    print("\n" + "=" * 70)
    print("SAMPLE OUTPUT (First spec_to_implementation)")
    print("=" * 70)

    for sample in samples:
        if sample.get("category") == "spec_to_implementation":
            response = sample["messages"][-1]["content"]
            # Show first 1500 chars
            print(response[:1500])
            if len(response) > 1500:
                print(f"\n... [{len(response) - 1500} more chars]")
            break

    print("\n" + "=" * 70)


if __name__ == "__main__":
    analyze_samples()
