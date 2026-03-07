#!/usr/bin/env python3
"""Test project generation with fine-tuned Qwen model."""

import asyncio
import sys
sys.path.insert(0, '.')

from app.utils.hybrid_client import hybrid_client

async def test_project_generation():
    print('=' * 70)
    print('TESTING PROJECT GENERATION WITH FINE-TUNED QWEN')
    print('=' * 70)

    prompt = """Create a simple Todo List application with:
- React frontend with Tailwind CSS
- Add, delete, and mark complete functionality
- Local storage persistence
- Clean modern UI"""

    system_prompt = """You are an expert software engineer. Generate complete, production-ready code.
Use this structure:
PLAN:
1) Step by step plan

FILES:
- List of files to create

Then provide the complete code for each file."""

    print(f'Prompt: {prompt[:100]}...')
    print()
    print('Generating...')

    result = await hybrid_client.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=2048
    )

    print()
    print(f'Model: {result.get("model")}')
    print(f'Tokens: {result.get("total_tokens")}')
    print()

    content = result.get('content', '')

    # Check format
    has_plan = 'PLAN' in content.upper()
    has_files = 'FILE' in content.upper()
    has_code = 'function' in content or 'const' in content or 'import' in content

    print(f'Has Plan: {has_plan}')
    print(f'Has Files: {has_files}')
    print(f'Has Code: {has_code}')
    print()
    print('Response Preview:')
    print('=' * 70)
    print(content[:2500])
    print('=' * 70)

    if len(content) > 2500:
        print(f'... ({len(content)} total chars)')

if __name__ == "__main__":
    asyncio.run(test_project_generation())
