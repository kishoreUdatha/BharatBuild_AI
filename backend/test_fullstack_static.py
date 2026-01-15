"""
Fullstack Static Analysis Test - Java Spring Boot + React TypeScript

Tests complete fullstack code generation:
- Backend: Entity, DTO, Repository, Service, Controller
- Frontend: Types, API client, Components, Pages

Run: python test_fullstack_static.py
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Load API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
for env_file in [".env.test", ".env"]:
    if api_key:
        break
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                break

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found")
    exit(1)

from anthropic import AsyncAnthropic

PROMPTS_DIR = Path(__file__).parent / "app" / "config" / "prompts"


def load_prompt(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def extract_file_content(response: str) -> str:
    match = re.search(r'<file[^>]*>(.*?)</file>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response


class JavaAnalyzer:
    """Analyze Java code."""

    @staticmethod
    def check_lombok(code: str) -> bool:
        return '@Data' not in code and '@Getter' not in code and 'import lombok' not in code

    @staticmethod
    def check_jakarta(code: str) -> bool:
        return 'javax.persistence' not in code and 'javax.validation' not in code

    @staticmethod
    def has_getters_setters(code: str) -> bool:
        return 'getId()' in code and 'setId(' in code

    @staticmethod
    def has_constructor_injection(code: str, class_name: str) -> bool:
        return f'public {class_name}(' in code

    @staticmethod
    def extract_methods(code: str) -> List[str]:
        """Extract method names from interface/class."""
        methods = []
        pattern = r'(?:public\s+)?[\w<>,\s]+\s+(\w+)\s*\([^)]*\)'
        for match in re.finditer(pattern, code):
            name = match.group(1)
            if name not in ['if', 'for', 'while', 'class', 'interface', 'new']:
                methods.append(name)
        return methods


class ReactAnalyzer:
    """Analyze React/TypeScript code."""

    @staticmethod
    def check_no_import_react(code: str) -> bool:
        """React 17+ doesn't need 'import React from react'."""
        return 'import React from' not in code

    @staticmethod
    def has_typescript_types(code: str) -> bool:
        return 'interface ' in code or ': string' in code or ': number' in code or 'Props' in code

    @staticmethod
    def has_export_default(code: str) -> bool:
        return 'export default' in code

    @staticmethod
    def has_tailwind_classes(code: str) -> bool:
        return 'className=' in code

    @staticmethod
    def uses_hooks(code: str) -> bool:
        return 'useState' in code or 'useEffect' in code

    @staticmethod
    def has_proper_api_calls(code: str) -> bool:
        return 'fetch(' in code or 'axios' in code or 'api.' in code

    @staticmethod
    def check_field_names(code: str, expected_fields: List[str]) -> List[str]:
        """Check if code uses expected field names."""
        missing = []
        for field in expected_fields:
            if field not in code:
                missing.append(field)
        return missing


async def test_fullstack():
    """Generate and analyze fullstack application."""
    print("=" * 70)
    print("FULLSTACK STATIC ANALYSIS TEST")
    print("Java Spring Boot + React TypeScript")
    print("=" * 70)

    client = AsyncAnthropic()
    generated_files: Dict[str, str] = {}
    errors: List[str] = []
    warnings: List[str] = []

    # Entity specs - shared between backend and frontend
    entity_specs = """
ENTITY_SPECS:
ENTITY: Task
TABLE: tasks
FIELDS:
  - id: Long (primary key)
  - title: String
  - description: String
  - status: TaskStatus (enum)
  - priority: TaskPriority (enum)
  - dueDate: LocalDateTime
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/tasks

ENUM: TaskStatus
VALUES: TODO, IN_PROGRESS, DONE, CANCELLED

ENUM: TaskPriority
VALUES: LOW, MEDIUM, HIGH, URGENT
"""

    # =========================================================================
    # BACKEND FILES
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: BACKEND (Java Spring Boot)")
    print("=" * 70)

    java_core = load_prompt("writer_core.txt")
    java_prompt = load_prompt("writer_java.txt")
    java_system = java_core + "\n\n" + java_prompt

    backend_files = [
        ("backend/src/main/java/com/taskapp/model/enums/TaskStatus.java", "Task status enum"),
        ("backend/src/main/java/com/taskapp/model/enums/TaskPriority.java", "Task priority enum"),
        ("backend/src/main/java/com/taskapp/model/Task.java", "Task JPA entity with explicit getters/setters"),
        ("backend/src/main/java/com/taskapp/dto/TaskDto.java", "Task DTO with explicit getters/setters"),
        ("backend/src/main/java/com/taskapp/repository/TaskRepository.java", "Task repository with custom queries"),
        ("backend/src/main/java/com/taskapp/service/TaskService.java", "Task service with CRUD operations"),
        ("backend/src/main/java/com/taskapp/controller/TaskController.java", "Task REST controller"),
    ]

    for i, (file_path, description) in enumerate(backend_files, 1):
        print(f"\n[{i}/{len(backend_files)}] {file_path.split('/')[-1]}")

        # Build context
        context_parts = [f"- {p}" for p in generated_files.keys() if p.startswith("backend/")]
        repo_context = ""

        if 'Service.java' in file_path:
            for path, code in generated_files.items():
                if 'Repository.java' in path:
                    repo_context = f"""
🔗 REPOSITORY INTERFACE (use ONLY these methods):
```java
{code}
```
"""
                    break

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{entity_specs}
{repo_context}
FILES ALREADY CREATED:
{chr(10).join(context_parts) if context_parts else "None yet"}

Requirements:
- NO LOMBOK
- Use jakarta.* imports
- Constructor injection for services
- Output: <file path="{file_path}">CODE</file>"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=java_system,
            messages=[{"role": "user", "content": user_prompt}]
        )

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code
        print(f"    Generated: {len(code)} chars")

    # =========================================================================
    # FRONTEND FILES
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: FRONTEND (React + TypeScript + Tailwind)")
    print("=" * 70)

    react_core = load_prompt("writer_core.txt")
    react_prompt = load_prompt("writer_react.txt")
    react_system = react_core + "\n\n" + react_prompt

    frontend_files = [
        ("frontend/src/types/index.ts", "TypeScript interfaces for Task, TaskStatus, TaskPriority"),
        ("frontend/src/lib/api.ts", "API client with fetch for /api/tasks endpoints"),
        ("frontend/src/components/TaskCard.tsx", "Task card component with Tailwind styling"),
        ("frontend/src/components/TaskForm.tsx", "Task form component for create/edit"),
        ("frontend/src/components/TaskList.tsx", "Task list component with filtering"),
        ("frontend/src/pages/TasksPage.tsx", "Main tasks page with CRUD operations"),
    ]

    for i, (file_path, description) in enumerate(frontend_files, 1):
        print(f"\n[{i}/{len(frontend_files)}] {file_path.split('/')[-1]}")

        # Build context - include types for all components
        context_parts = [f"- {p}" for p in generated_files.keys() if p.startswith("frontend/")]
        types_context = ""

        if 'types/index.ts' in generated_files.get("frontend/src/types/index.ts", ""):
            types_context = f"""
TYPES (from types/index.ts):
```typescript
{generated_files.get("frontend/src/types/index.ts", "")}
```
"""
        elif "frontend/src/types/index.ts" in generated_files:
            types_context = f"""
TYPES (from types/index.ts):
```typescript
{generated_files["frontend/src/types/index.ts"]}
```
"""

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{entity_specs}
{types_context}
FILES ALREADY CREATED:
{chr(10).join(context_parts) if context_parts else "None yet"}

Requirements:
- TypeScript with proper types
- React functional components with hooks
- Tailwind CSS for styling (cyan/teal theme)
- NO 'import React from "react"' (React 17+)
- export default for components
- Output: <file path="{file_path}">CODE</file>"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=react_system,
            messages=[{"role": "user", "content": user_prompt}]
        )

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code
        print(f"    Generated: {len(code)} chars")

    # =========================================================================
    # ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: STATIC ANALYSIS")
    print("=" * 70)

    java_analyzer = JavaAnalyzer()
    react_analyzer = ReactAnalyzer()
    checks_passed = 0
    checks_failed = 0

    # Analyze Backend
    print("\n[BACKEND ANALYSIS]")
    for file_path, code in generated_files.items():
        if not file_path.startswith("backend/") or not file_path.endswith(".java"):
            continue

        file_name = file_path.split("/")[-1]
        print(f"\n  {file_name}:")

        checks = []

        # Common Java checks
        if java_analyzer.check_lombok(code):
            checks.append(("[OK]", "No Lombok"))
            checks_passed += 1
        else:
            checks.append(("[FAIL]", "Uses Lombok"))
            checks_failed += 1
            errors.append(f"{file_name}: Uses Lombok")

        if java_analyzer.check_jakarta(code):
            checks.append(("[OK]", "Jakarta imports"))
            checks_passed += 1
        else:
            checks.append(("[FAIL]", "Uses javax"))
            checks_failed += 1
            errors.append(f"{file_name}: Uses javax instead of jakarta")

        # Entity/DTO checks
        if '/model/' in file_path and 'enum' not in file_path.lower():
            if java_analyzer.has_getters_setters(code):
                checks.append(("[OK]", "Has getters/setters"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Missing getters/setters"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing getters/setters")

        # Service checks
        if 'Service.java' in file_path:
            class_name = file_name.replace(".java", "")
            if java_analyzer.has_constructor_injection(code, class_name):
                checks.append(("[OK]", "Constructor injection"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "No constructor injection"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing constructor injection")

            # Check repository calls
            repo_code = generated_files.get("backend/src/main/java/com/taskapp/repository/TaskRepository.java", "")
            repo_methods = set(java_analyzer.extract_methods(repo_code))
            repo_methods.update(['findAll', 'findById', 'save', 'delete', 'deleteById', 'existsById'])

            service_calls = set(re.findall(r'taskRepository\.(\w+)\s*\(', code))
            invalid_calls = service_calls - repo_methods
            if not invalid_calls:
                checks.append(("[OK]", "Valid repository calls"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", f"Invalid repo calls: {invalid_calls}"))
                checks_failed += 1
                errors.append(f"{file_name}: Calls non-existent repo methods: {invalid_calls}")

        for status, msg in checks:
            print(f"    {status} {msg}")

    # Analyze Frontend
    print("\n[FRONTEND ANALYSIS]")
    expected_fields = ['id', 'title', 'description', 'status', 'priority', 'dueDate']

    for file_path, code in generated_files.items():
        if not file_path.startswith("frontend/"):
            continue

        file_name = file_path.split("/")[-1]
        print(f"\n  {file_name}:")

        checks = []

        # TypeScript types file
        if file_path.endswith("types/index.ts"):
            if react_analyzer.has_typescript_types(code):
                checks.append(("[OK]", "Has TypeScript interfaces"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Missing TypeScript interfaces"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing TypeScript interfaces")

            # Check field names match entity_specs
            missing = react_analyzer.check_field_names(code, expected_fields)
            if not missing:
                checks.append(("[OK]", "All fields defined"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", f"May miss fields: {missing}"))
                warnings.append(f"{file_name}: May be missing fields: {missing}")

        # React components
        if file_path.endswith(".tsx"):
            if react_analyzer.check_no_import_react(code):
                checks.append(("[OK]", "No 'import React from'"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Has old React import"))
                checks_failed += 1
                errors.append(f"{file_name}: Uses old 'import React from' syntax")

            if react_analyzer.has_export_default(code):
                checks.append(("[OK]", "Has export default"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Missing export default"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing export default")

            if react_analyzer.has_tailwind_classes(code):
                checks.append(("[OK]", "Uses Tailwind CSS"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", "No Tailwind classes"))
                warnings.append(f"{file_name}: No Tailwind classes found")

            if react_analyzer.uses_hooks(code):
                checks.append(("[OK]", "Uses React hooks"))
                checks_passed += 1
            else:
                checks.append(("[OK]", "No hooks (may not need)"))
                checks_passed += 1

        # API client
        if file_path.endswith("api.ts"):
            if react_analyzer.has_proper_api_calls(code):
                checks.append(("[OK]", "Has API calls"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "No API calls"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing API calls")

            if '/api/tasks' in code:
                checks.append(("[OK]", "Correct API endpoint"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", "API endpoint may be wrong"))
                warnings.append(f"{file_name}: API endpoint may not match")

        for status, msg in checks:
            print(f"    {status} {msg}")

    # =========================================================================
    # CROSS-STACK CONSISTENCY
    # =========================================================================
    print("\n[CROSS-STACK CONSISTENCY]")

    # Check types match between Java DTO and TypeScript interface
    dto_code = generated_files.get("backend/src/main/java/com/taskapp/dto/TaskDto.java", "")
    types_code = generated_files.get("frontend/src/types/index.ts", "")

    # Extract Java fields
    java_fields = set(re.findall(r'private\s+\w+\s+(\w+);', dto_code))
    # Extract TypeScript fields
    ts_fields = set(re.findall(r'(\w+)\s*[?]?\s*:\s*\w+', types_code))

    # Common expected fields
    common_fields = {'id', 'title', 'description', 'status', 'priority'}
    java_has = common_fields & java_fields
    ts_has = common_fields & ts_fields

    if java_has == ts_has:
        print(f"  [OK] DTO and TypeScript types have matching fields")
        checks_passed += 1
    else:
        missing_in_ts = java_has - ts_has
        missing_in_java = ts_has - java_has
        if missing_in_ts:
            print(f"  [WARN] TypeScript missing: {missing_in_ts}")
            warnings.append(f"TypeScript types missing fields: {missing_in_ts}")
        if missing_in_java:
            print(f"  [WARN] Java DTO missing: {missing_in_java}")
            warnings.append(f"Java DTO missing fields: {missing_in_java}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Files Generated: {len(generated_files)}")
    print(f"  - Backend: {len([f for f in generated_files if f.startswith('backend/')])}")
    print(f"  - Frontend: {len([f for f in generated_files if f.startswith('frontend/')])}")
    print(f"\nChecks Passed: {checks_passed}")
    print(f"Checks Failed: {checks_failed}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    if errors:
        print("\n[ERRORS]")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("\n[WARNINGS]")
        for warning in warnings[:10]:
            print(f"  - {warning}")

    # Show sample frontend code
    print("\n" + "=" * 70)
    print("SAMPLE: TaskCard.tsx")
    print("=" * 70)
    task_card = generated_files.get("frontend/src/components/TaskCard.tsx", "")
    for i, line in enumerate(task_card.split('\n')[:40], 1):
        print(f"{i:3}: {line}")

    print("\n" + "=" * 70)
    if checks_failed == 0 and len(errors) == 0:
        print("[SUCCESS] All fullstack checks PASSED!")
        return True
    else:
        print(f"[FAILED] {checks_failed} checks failed, {len(errors)} errors")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_fullstack())
    exit(0 if success else 1)
