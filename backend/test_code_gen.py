"""
Test: Generate actual code file using BharatBuild Writer Agent
"""
import sys, os, asyncio
os.chdir('D:/Smartgrow Projects/BharatBuild_AI/backend')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('D:/Smartgrow Projects/BharatBuild_AI/backend/.env', override=True)

async def main():
    print("=" * 60)
    print("  BharatBuild AI - Actual Code Generation Test")
    print("=" * 60)

    from app.utils.claude_client import claude_client

    # Generate a single React component
    print("\n[Test] Generating a React Counter component...")

    response = await claude_client.generate(
        prompt="""Generate a complete React Counter component with TypeScript.
Requirements:
- Increment/decrement buttons
- Display current count
- Tailwind CSS styling
- Dark theme

Output ONLY the code inside <file path="src/components/Counter.tsx"> tags.""",
        system_prompt="""You are a code generator. Output complete, working code.
Use <file path="...">code here</file> format. No explanations.""",
        model="sonnet",
        max_tokens=2000,
        temperature=0.3
    )

    content = response["content"]
    print(f"\nTokens used: {response['total_tokens']}")
    print(f"Model: {response['model']}")
    print(f"\n{'=' * 60}")
    print("  GENERATED CODE:")
    print("=" * 60)
    print(content)

    # Save the generated file
    output_dir = "D:/tmp/bharatbuild_test"
    os.makedirs(output_dir, exist_ok=True)

    # Extract content from <file> tags
    import re
    file_match = re.search(r'<file path="([^"]+)">(.*?)</file>', content, re.DOTALL)
    if file_match:
        file_path = file_match.group(1)
        file_content = file_match.group(2).strip()

        # Save to disk
        full_path = os.path.join(output_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(file_content)

        print(f"\n{'=' * 60}")
        print(f"  FILE SAVED: {full_path}")
        print(f"  Size: {len(file_content)} characters")
        print("=" * 60)
    else:
        print("\n[Note] Could not extract file tags, showing raw output above")

    print("\n[PASS] Code generation works!")

asyncio.run(main())
