"""
Full Project Generation Test — Saves complete project to local disk
"""
import sys, os, asyncio, re, time
os.chdir('D:/Smartgrow Projects/BharatBuild_AI/backend')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('D:/Smartgrow Projects/BharatBuild_AI/backend/.env', override=True)

OUTPUT_DIR = "D:/tmp/bharatbuild_generated"

async def main():
    print("=" * 60)
    print("  BharatBuild AI - Full Project Generation")
    print("=" * 60)

    from app.utils.claude_client import claude_client
    from app.modules.agents.planner_agent import PlannerAgent
    from app.modules.agents.base_agent import AgentContext

    # Step 1: Plan
    print("\n[1/3] Planning project...")
    planner = PlannerAgent()
    context = AgentContext(
        user_request="Build a Todo App with React frontend and FastAPI backend. Features: add/delete/complete todos, filter by status, dark theme with Tailwind CSS.",
        project_id="fullstack-todo-test",
    )

    plan_result = await planner.process(context)
    if not plan_result.get("success"):
        print(f"  FAILED: {plan_result.get('error')}")
        return

    plan = plan_result["plan"]
    files = plan.get("files", [])
    print(f"  Project: {plan.get('project_name', 'Todo App')}")
    print(f"  Tech: {plan.get('tech_stack', 'React + FastAPI')}")
    print(f"  Files to generate: {len(files)}")

    # Limit to 15 files to save credits
    files = files[:15]
    print(f"  Generating first {len(files)} files (to save credits)...")

    # Step 2: Generate each file
    print(f"\n[2/3] Generating code...")
    start = time.time()
    generated_files = {}
    errors = []

    for i, file_info in enumerate(files):
        file_path = file_info.get("path", "") if isinstance(file_info, dict) else str(file_info)
        description = file_info.get("description", "") if isinstance(file_info, dict) else ""

        if not file_path:
            continue

        print(f"  [{i+1}/{len(files)}] {file_path}...", end=" ", flush=True)

        # Context of already-generated files (last 3 only to save tokens)
        existing_context = ""
        if generated_files:
            existing_context = "\nFILES ALREADY CREATED:\n"
            for p, c in list(generated_files.items())[-3:]:
                existing_context += f"--- {p} (first 150 chars) ---\n{c[:150]}\n\n"

        prompt = f"""Generate COMPLETE file: {file_path}
Description: {description}
Project: Todo App (React + Vite + Tailwind frontend, FastAPI backend)
{existing_context}
Output ONLY code inside <file path="{file_path}"> tags. No explanations. Complete and runnable."""

        try:
            response = await claude_client.generate(
                prompt=prompt,
                system_prompt="You are a code generator. Output complete code in <file path=\"...\">code</file> format only. No markdown, no explanations.",
                model="sonnet",
                max_tokens=4096,
                temperature=0.2
            )

            content = response["content"]
            match = re.search(r'<file path="[^"]*">(.*?)</file>', content, re.DOTALL)
            if match:
                file_content = match.group(1).strip()
            else:
                file_content = content.strip()

            generated_files[file_path] = file_content
            print(f"OK ({len(file_content)} chars)")

        except Exception as e:
            print(f"FAILED ({e})")
            errors.append(file_path)

    elapsed = time.time() - start

    # Step 3: Save to disk
    print(f"\n[3/3] Saving to {OUTPUT_DIR}...")

    if os.path.exists(OUTPUT_DIR):
        import shutil
        shutil.rmtree(OUTPUT_DIR)

    for file_path, content in generated_files.items():
        full_path = os.path.join(OUTPUT_DIR, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  DONE!")
    print(f"{'=' * 60}")
    print(f"  Files: {len(generated_files)} generated, {len(errors)} failed")
    print(f"  Time: {elapsed:.1f} seconds")
    print(f"  Location: {OUTPUT_DIR}")
    print(f"\n  Files:")
    for path in sorted(generated_files.keys()):
        print(f"    {path} ({len(generated_files[path])} chars)")

asyncio.run(main())
