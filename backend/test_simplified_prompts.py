"""
Test Simplified Prompts - Verify they load correctly and generate valid output.

Run: python test_simplified_prompts.py
"""

import asyncio
import os
from pathlib import Path

# Load API key - try multiple sources
api_key = os.environ.get("ANTHROPIC_API_KEY")

# Try .env.test first, then .env
for env_file in [".env.test", ".env"]:
    if api_key:
        break
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                print(f"[OK] Loaded API key from {env_file}")
                break

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found")
    print("Set it with: set ANTHROPIC_API_KEY=your-key")
    exit(1)

print(f"[OK] API key: {api_key[:20]}...{api_key[-10:]}")

from anthropic import AsyncAnthropic

# Load the simplified prompts
PROMPTS_DIR = Path(__file__).parent / "app" / "config" / "prompts"


def load_prompt(filename: str) -> str:
    """Load a prompt file."""
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        content = filepath.read_text(encoding="utf-8")
        print(f"[OK] Loaded {filename}: {len(content)} chars")
        return content
    print(f"[ERROR] Not found: {filepath}")
    return ""


async def test_planner_prompt():
    """Test that planner generates valid plan with entity_specs."""
    print("\n" + "=" * 60)
    print("TEST 1: Planner Prompt - Java Backend")
    print("=" * 60)

    # Load prompts
    core_prompt = load_prompt("planner_core.txt")
    java_prompt = load_prompt("planner_java.txt")

    if not core_prompt or not java_prompt:
        print("[FAILED] Could not load prompts")
        return False

    system_prompt = core_prompt + "\n\n" + java_prompt
    print(f"[OK] Combined prompt: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)")

    client = AsyncAnthropic()

    user_prompt = """Create a simple e-commerce backend with:
- Product entity (name, price, description, stock)
- Order entity (customer name, total, status)
Use Spring Boot with Java."""

    print(f"\n[Calling Claude with simplified prompt...]")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    output = response.content[0].text
    print(f"[OK] Response received: {len(output)} chars")
    print(f"[OK] Tokens used: {response.usage.input_tokens + response.usage.output_tokens}")

    # Check for required elements
    checks = {
        "<plan>": "<plan>" in output,
        "</plan>": "</plan>" in output,
        "<entity_specs>": "<entity_specs>" in output,
        "ENTITY:": "ENTITY:" in output,
        "FIELDS:": "FIELDS:" in output,
        "<files>": "<files>" in output,
        "jakarta": "jakarta" in output.lower() or "no lombok" in output.lower(),
    }

    print("\n[Checking output...]")
    all_passed = True
    for check, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} Contains {check}")
        if not passed:
            all_passed = False

    # Show entity_specs section
    if "<entity_specs>" in output:
        start = output.find("<entity_specs>")
        end = output.find("</entity_specs>") + len("</entity_specs>")
        if start >= 0 and end > start:
            print("\n[Entity Specs Generated:]")
            print("-" * 40)
            print(output[start:end][:1000])
            print("-" * 40)

    return all_passed


async def test_writer_prompt():
    """Test that writer generates valid code."""
    print("\n" + "=" * 60)
    print("TEST 2: Writer Prompt - Java Entity")
    print("=" * 60)

    # Load prompts
    core_prompt = load_prompt("writer_core.txt")
    java_prompt = load_prompt("writer_java.txt")

    if not core_prompt or not java_prompt:
        print("[FAILED] Could not load prompts")
        return False

    system_prompt = core_prompt + "\n\n" + java_prompt
    print(f"[OK] Combined prompt: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)")

    client = AsyncAnthropic()

    user_prompt = """Generate this file:

FILE TO GENERATE: backend/src/main/java/com/ecommerce/model/Product.java

ENTITY_SPECS:
ENTITY: Product
TABLE: products
FIELDS:
  - id: Long (primary key)
  - name: String
  - price: BigDecimal
  - description: String
  - stockQuantity: Integer
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/products

Generate the complete JPA entity with explicit getters and setters (NO LOMBOK)."""

    print(f"\n[Calling Claude with simplified prompt...]")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    output = response.content[0].text
    print(f"[OK] Response received: {len(output)} chars")
    print(f"[OK] Tokens used: {response.usage.input_tokens + response.usage.output_tokens}")

    # Check for required elements
    checks = {
        "<file path=": "<file path=" in output,
        "jakarta.persistence": "jakarta.persistence" in output,
        "NO @Data/@Getter": "@Data" not in output and "@Getter" not in output,
        "NO lombok import": "import lombok" not in output,
        "Has getId()": "getId()" in output,
        "Has setId()": "setId(" in output,
        "Has getName()": "getName()" in output,
        "Has getPrice()": "getPrice()" in output,
        "Has BigDecimal": "BigDecimal" in output,
        "Has LocalDateTime": "LocalDateTime" in output,
    }

    print("\n[Checking generated code...]")
    all_passed = True
    for check, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    # Show generated code
    if "<file" in output:
        print("\n[Generated Code:]")
        print("-" * 40)
        # Extract file content
        start = output.find("<file")
        end = output.find("</file>") + len("</file>")
        if start >= 0 and end > start:
            print(output[start:end][:2000])
        print("-" * 40)

    return all_passed


async def test_react_writer_prompt():
    """Test React writer prompt."""
    print("\n" + "=" * 60)
    print("TEST 3: Writer Prompt - React Component")
    print("=" * 60)

    core_prompt = load_prompt("writer_core.txt")
    react_prompt = load_prompt("writer_react.txt")

    if not core_prompt or not react_prompt:
        print("[FAILED] Could not load prompts")
        return False

    system_prompt = core_prompt + "\n\n" + react_prompt
    print(f"[OK] Combined prompt: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)")

    client = AsyncAnthropic()

    user_prompt = """Generate this file:

FILE TO GENERATE: frontend/src/components/ProductCard.tsx

TYPES (from types/index.ts):
interface Product {
  id: number;
  name: string;
  price: number;
  imageUrl: string;
  stockQuantity: number;
}

Create a ProductCard component that displays product info with Tailwind styling."""

    print(f"\n[Calling Claude with simplified prompt...]")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    output = response.content[0].text
    print(f"[OK] Response received: {len(output)} chars")
    print(f"[OK] Tokens used: {response.usage.input_tokens + response.usage.output_tokens}")

    checks = {
        "<file path=": "<file path=" in output,
        "NO 'import React'": "import React from" not in output,
        "Uses hooks correctly": "useState" in output or "from 'react'" in output or "interface" in output,
        "Has export default": "export default" in output,
        "Uses camelCase (imageUrl)": "imageUrl" in output,
        "Uses camelCase (stockQuantity)": "stockQuantity" in output,
        "Has Tailwind classes": "className=" in output,
    }

    print("\n[Checking generated code...]")
    all_passed = True
    for check, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    return all_passed


async def main():
    print("=" * 60)
    print("SIMPLIFIED PROMPTS TEST SUITE")
    print("=" * 60)

    # Check prompt files exist and show sizes
    print("\n[Prompt File Sizes]")
    prompt_files = [
        "planner_core.txt", "planner_java.txt", "planner_python.txt", "planner_react.txt",
        "writer_core.txt", "writer_java.txt", "writer_python.txt", "writer_react.txt"
    ]

    total_lines = 0
    for filename in prompt_files:
        filepath = PROMPTS_DIR / filename
        if filepath.exists():
            lines = len(filepath.read_text(encoding="utf-8").split("\n"))
            total_lines += lines
            print(f"  {filename}: {lines} lines")
        else:
            print(f"  {filename}: NOT FOUND")

    print(f"\n  TOTAL: {total_lines} lines (target: <700)")

    # Run tests
    results = {}

    results["Planner (Java)"] = await test_planner_prompt()
    results["Writer (Java Entity)"] = await test_writer_prompt()
    results["Writer (React Component)"] = await test_react_writer_prompt()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed! Simplified prompts work correctly.")
    else:
        print("[WARNING] Some tests failed. Review the output above.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
