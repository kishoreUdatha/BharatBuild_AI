"""
Incremental Generation Test — Generates project file-by-file with context
Each file gets the content of previous files, so imports/methods are correct.
"""
import sys, os, asyncio, re, time
os.chdir('D:/Smartgrow Projects/BharatBuild_AI/backend')
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv('D:/Smartgrow Projects/BharatBuild_AI/backend/.env', override=True)

OUTPUT_DIR = "D:/tmp/bharatbuild_incremental"

async def main():
    print("=" * 60)
    print("  BharatBuild AI - Incremental Generation (Kiro-style)")
    print("  Each file sees previous files = correct imports!")
    print("=" * 60)

    from app.utils.claude_client import claude_client
    from app.modules.agents.planner_agent import PlannerAgent
    from app.modules.agents.base_agent import AgentContext
    from app.modules.agents.incremental_orchestrator import InlineVerifier

    verifier = InlineVerifier()

    # Step 1: Plan
    print("\n[1/3] Planning project...")
    planner = PlannerAgent()
    context = AgentContext(
        user_request="Build a Todo App with React frontend and FastAPI backend. Features: add/delete/complete todos, filter by status, dark theme.",
        project_id="incremental-test",
    )

    plan_result = await planner.process(context)
    if not plan_result.get("success"):
        print(f"  FAILED: {plan_result.get('error')}")
        return

    plan = plan_result["plan"]
    files = plan.get("files", [])[:12]  # First 12 to save credits
    print(f"  Files to generate: {len(files)}")

    # Step 2: Generate file-by-file WITH context
    print(f"\n[2/3] Generating files incrementally (each sees previous)...")
    start = time.time()
    generated_files = {}  # path -> content (accumulates)
    errors_found = 0
    errors_fixed = 0

    for i, file_info in enumerate(files):
        file_path = file_info.get("path", "") if isinstance(file_info, dict) else str(file_info)
        description = file_info.get("description", "") if isinstance(file_info, dict) else ""

        if not file_path:
            continue

        print(f"\n  [{i+1}/{len(files)}] {file_path}")

        # KEY DIFFERENCE: Include FULL content of previous files
        context_str = ""
        if generated_files:
            context_str = "\n\n=== FILES ALREADY CREATED (use these EXACT imports and method names) ===\n"
            for prev_path, prev_content in generated_files.items():
                context_str += f"\n--- {prev_path} ---\n{prev_content}\n"
            context_str += "\n=== END OF EXISTING FILES ===\n"

        prompt = f"""Generate the COMPLETE file: {file_path}
Description: {description}

Project: Todo App
- Backend: FastAPI + SQLAlchemy + Pydantic (in backend/ folder)
- Frontend: React + TypeScript + Vite + Tailwind (in frontend/ folder)
- All backend imports use relative paths (e.g., from core.database import Base)
- NOT from backend.core.database (no 'backend.' prefix in imports)

{context_str}

CRITICAL RULES:
1. Use EXACT same class/function names as shown in existing files above
2. Import paths must be RELATIVE (from core.database, from models.todo, etc.)
3. If calling a service method, use the EXACT method name from the service file above
4. Output ONLY code inside <file path="{file_path}"> tags
5. Complete, runnable code - no TODOs or placeholders"""

        try:
            response = await claude_client.generate(
                prompt=prompt,
                system_prompt="You are a precise code generator. Match existing code exactly. Use <file path=\"...\">code</file> format only. No explanations.",
                model="sonnet",
                max_tokens=4096,
                temperature=0.1  # Low temp = more consistent
            )

            content = response["content"]
            match = re.search(r'<file path="[^"]*">(.*?)</file>', content, re.DOTALL)
            file_content = match.group(1).strip() if match else content.strip()

            # Verify the file
            issues = verifier.verify(file_path, file_content, generated_files)

            if issues:
                errors_found += len(issues)
                print(f"    Issues: {issues}")
                # For now just save anyway (in production, InlineFixer would fix these)
            else:
                print(f"    Verified OK ({len(file_content)} chars)")

            generated_files[file_path] = file_content

        except Exception as e:
            print(f"    FAILED: {e}")

    elapsed = time.time() - start

    # Step 3: Save
    print(f"\n[3/3] Saving to {OUTPUT_DIR}...")
    if os.path.exists(OUTPUT_DIR):
        import shutil
        shutil.rmtree(OUTPUT_DIR)

    for file_path, content in generated_files.items():
        full_path = os.path.join(OUTPUT_DIR, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # Step 4: Cross-file verification
    print(f"\n{'=' * 60}")
    print("  CROSS-FILE VERIFICATION")
    print("=" * 60)

    # Check import consistency
    import_errors = []
    for file_path, content in generated_files.items():
        if file_path.endswith('.py'):
            # Check for 'from backend.' imports (should be relative)
            if 'from backend.' in content:
                import_errors.append(f"  {file_path}: Uses 'from backend.' (should be relative)")

    # Check method name consistency between service and API
    service_content = generated_files.get("backend/services/todo_service.py", "")
    api_content = generated_files.get("backend/api/todos.py", "")

    if service_content and api_content:
        # Extract method names from service
        service_methods = re.findall(r'def (\w+)\(', service_content)
        # Check if API uses methods that exist in service
        api_calls = re.findall(r'service\.(\w+)\(', api_content) + re.findall(r'todo_service\.(\w+)\(', api_content)

        method_errors = []
        for call in api_calls:
            if call not in service_methods and call not in ['__init__']:
                method_errors.append(f"  API calls service.{call}() but service has: {service_methods}")

        if method_errors:
            print("  Method mismatches:")
            for e in method_errors:
                print(f"    {e}")
        else:
            print("  Service-API method names: MATCH!")

    if import_errors:
        print(f"  Import issues ({len(import_errors)}):")
        for e in import_errors:
            print(f"    {e}")
    else:
        print("  Import paths: ALL CORRECT!")

    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Files generated: {len(generated_files)}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Import errors: {len(import_errors)}")
    print(f"  Location: {OUTPUT_DIR}")

asyncio.run(main())
