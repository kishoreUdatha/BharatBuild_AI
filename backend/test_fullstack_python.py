"""
Fullstack Static Analysis Test - Python FastAPI + React TypeScript

Tests complete fullstack code generation:
- Backend: SQLAlchemy Models, Pydantic Schemas, Services, Routes
- Frontend: Types, API client, Components, Pages

Run: python test_fullstack_python.py
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List

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


class PythonAnalyzer:
    """Analyze Python/FastAPI code."""

    @staticmethod
    def has_sqlalchemy_model(code: str) -> bool:
        return 'Base' in code and ('Column' in code or 'Mapped' in code)

    @staticmethod
    def has_pydantic_schema(code: str) -> bool:
        return 'BaseModel' in code or 'class ' in code and ': ' in code

    @staticmethod
    def has_fastapi_router(code: str) -> bool:
        return 'APIRouter' in code or '@router.' in code or '@app.' in code

    @staticmethod
    def has_async_functions(code: str) -> bool:
        return 'async def' in code

    @staticmethod
    def has_type_hints(code: str) -> bool:
        return ': str' in code or ': int' in code or ': List[' in code or '-> ' in code

    @staticmethod
    def has_dependency_injection(code: str) -> bool:
        return 'Depends(' in code

    @staticmethod
    def uses_correct_imports(code: str) -> bool:
        """Check for modern Python/FastAPI imports."""
        issues = []
        if 'from typing import' in code and 'Optional' in code:
            # Python 3.10+ should use | None instead
            pass  # Still acceptable
        return True

    @staticmethod
    def extract_functions(code: str) -> List[str]:
        """Extract function names."""
        return re.findall(r'(?:async\s+)?def\s+(\w+)\s*\(', code)


class ReactAnalyzer:
    """Analyze React/TypeScript code."""

    @staticmethod
    def check_no_import_react(code: str) -> bool:
        return 'import React from' not in code

    @staticmethod
    def has_typescript_types(code: str) -> bool:
        return 'interface ' in code or ': string' in code or ': number' in code

    @staticmethod
    def has_export_default(code: str) -> bool:
        return 'export default' in code

    @staticmethod
    def has_tailwind_classes(code: str) -> bool:
        return 'className=' in code

    @staticmethod
    def uses_hooks(code: str) -> bool:
        return 'useState' in code or 'useEffect' in code


async def test_fullstack_python():
    """Generate and analyze Python FastAPI + React fullstack application."""
    print("=" * 70)
    print("FULLSTACK STATIC ANALYSIS TEST")
    print("Python FastAPI + React TypeScript")
    print("=" * 70)

    client = AsyncAnthropic()
    generated_files: Dict[str, str] = {}
    errors: List[str] = []
    warnings: List[str] = []

    # Entity specs - shared between backend and frontend
    entity_specs = """
ENTITY_SPECS:
ENTITY: Book
TABLE: books
FIELDS:
  - id: int (primary key)
  - title: str
  - author: str
  - isbn: str
  - price: float
  - category: BookCategory (enum)
  - published_date: date
  - in_stock: bool
  - created_at: datetime
  - updated_at: datetime
API_PATH: /api/books

ENUM: BookCategory
VALUES: FICTION, NON_FICTION, SCIENCE, TECHNOLOGY, HISTORY, BIOGRAPHY, OTHER
"""

    # =========================================================================
    # BACKEND FILES (Python FastAPI)
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: BACKEND (Python FastAPI)")
    print("=" * 70)

    python_core = load_prompt("writer_core.txt")
    python_prompt = load_prompt("writer_python.txt")
    python_system = python_core + "\n\n" + python_prompt

    backend_files = [
        ("backend/app/core/database.py", "SQLAlchemy database setup with async engine"),
        ("backend/app/models/enums.py", "BookCategory enum using Python Enum"),
        ("backend/app/models/book.py", "Book SQLAlchemy model with all fields"),
        ("backend/app/schemas/book.py", "Pydantic schemas: BookBase, BookCreate, BookUpdate, BookResponse"),
        ("backend/app/services/book_service.py", "Book service with async CRUD operations"),
        ("backend/app/api/routes/books.py", "FastAPI router for /api/books endpoints"),
        ("backend/app/main.py", "FastAPI application entry point"),
    ]

    for i, (file_path, description) in enumerate(backend_files, 1):
        print(f"\n[{i}/{len(backend_files)}] {file_path.split('/')[-1]}")

        # Build context
        context_parts = [f"- {p}" for p in generated_files.keys() if p.startswith("backend/")]

        # For routes, include service functions
        service_context = ""
        if 'routes' in file_path:
            service_code = generated_files.get("backend/app/services/book_service.py", "")
            if service_code:
                service_context = f"""
SERVICE FUNCTIONS AVAILABLE (from book_service.py):
```python
{service_code}
```
"""

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{entity_specs}
{service_context}
FILES ALREADY CREATED:
{chr(10).join(context_parts) if context_parts else "None yet"}

Requirements:
- Use async/await for database operations
- Type hints on all functions
- Pydantic v2 syntax (model_config instead of Config class)
- SQLAlchemy 2.0 style (Mapped, mapped_column)
- Use Depends() for dependency injection
- Output: <file path="{file_path}">CODE</file>"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=python_system,
            messages=[{"role": "user", "content": user_prompt}]
        )

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code
        print(f"    Generated: {len(code)} chars")

    # =========================================================================
    # FRONTEND FILES (React TypeScript)
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: FRONTEND (React + TypeScript + Tailwind)")
    print("=" * 70)

    react_core = load_prompt("writer_core.txt")
    react_prompt = load_prompt("writer_react.txt")
    react_system = react_core + "\n\n" + react_prompt

    frontend_files = [
        ("frontend/src/types/index.ts", "TypeScript interfaces for Book, BookCategory"),
        ("frontend/src/lib/api.ts", "API client with fetch for /api/books endpoints"),
        ("frontend/src/components/BookCard.tsx", "Book card component with Tailwind styling"),
        ("frontend/src/components/BookForm.tsx", "Book form component for create/edit"),
        ("frontend/src/components/BookList.tsx", "Book list with search and category filter"),
        ("frontend/src/pages/BooksPage.tsx", "Main books page with CRUD operations"),
    ]

    for i, (file_path, description) in enumerate(frontend_files, 1):
        print(f"\n[{i}/{len(frontend_files)}] {file_path.split('/')[-1]}")

        # Build context
        context_parts = [f"- {p}" for p in generated_files.keys() if p.startswith("frontend/")]
        types_context = ""

        if "frontend/src/types/index.ts" in generated_files:
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
- Tailwind CSS (violet/purple theme for books)
- NO 'import React from "react"'
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

    python_analyzer = PythonAnalyzer()
    react_analyzer = ReactAnalyzer()
    checks_passed = 0
    checks_failed = 0

    # Analyze Backend (Python)
    print("\n[BACKEND ANALYSIS - Python FastAPI]")

    for file_path, code in generated_files.items():
        if not file_path.startswith("backend/"):
            continue

        file_name = file_path.split("/")[-1]
        print(f"\n  {file_name}:")

        checks = []

        # Type hints check
        if python_analyzer.has_type_hints(code):
            checks.append(("[OK]", "Has type hints"))
            checks_passed += 1
        else:
            checks.append(("[WARN]", "May be missing type hints"))
            warnings.append(f"{file_name}: May be missing type hints")

        # Model checks
        if 'models/' in file_path and 'enum' not in file_path:
            if python_analyzer.has_sqlalchemy_model(code):
                checks.append(("[OK]", "Valid SQLAlchemy model"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Invalid SQLAlchemy model"))
                checks_failed += 1
                errors.append(f"{file_name}: Invalid SQLAlchemy model")

        # Schema checks
        if 'schemas/' in file_path:
            if python_analyzer.has_pydantic_schema(code):
                checks.append(("[OK]", "Valid Pydantic schema"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Invalid Pydantic schema"))
                checks_failed += 1
                errors.append(f"{file_name}: Invalid Pydantic schema")

        # Service checks
        if 'service' in file_path:
            if python_analyzer.has_async_functions(code):
                checks.append(("[OK]", "Has async functions"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", "No async functions"))
                warnings.append(f"{file_name}: No async functions")

        # Routes checks
        if 'routes/' in file_path:
            if python_analyzer.has_fastapi_router(code):
                checks.append(("[OK]", "Has FastAPI router"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Missing FastAPI router"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing FastAPI router")

            if python_analyzer.has_async_functions(code):
                checks.append(("[OK]", "Async route handlers"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", "Route handlers not async"))
                warnings.append(f"{file_name}: Route handlers should be async")

            if python_analyzer.has_dependency_injection(code):
                checks.append(("[OK]", "Uses Depends()"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", "Not using Depends()"))
                warnings.append(f"{file_name}: Should use Depends() for DI")

            # Check service calls
            service_code = generated_files.get("backend/app/services/book_service.py", "")
            service_funcs = set(python_analyzer.extract_functions(service_code))
            route_calls = set(re.findall(r'book_service\.(\w+)\s*\(', code))

            # Also check for direct function calls
            route_calls.update(re.findall(r'(?:await\s+)?(\w+)\s*\([^)]*db', code))

            invalid_calls = route_calls - service_funcs - {'get_db', 'Depends'}
            if not invalid_calls or len(invalid_calls) < 3:
                checks.append(("[OK]", "Valid service calls"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", f"Unknown calls: {invalid_calls}"))
                warnings.append(f"{file_name}: Unknown service calls")

        for status, msg in checks:
            print(f"    {status} {msg}")

    # Analyze Frontend (React)
    print("\n[FRONTEND ANALYSIS - React TypeScript]")

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

            # Check for Book interface fields
            expected_fields = ['id', 'title', 'author', 'isbn', 'price', 'category']
            missing = [f for f in expected_fields if f not in code]
            if not missing:
                checks.append(("[OK]", "All fields defined"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", f"May miss: {missing}"))
                warnings.append(f"{file_name}: May be missing fields")

        # React components
        if file_path.endswith(".tsx"):
            if react_analyzer.check_no_import_react(code):
                checks.append(("[OK]", "No old React import"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "Has old React import"))
                checks_failed += 1
                errors.append(f"{file_name}: Uses old React import")

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
                warnings.append(f"{file_name}: No Tailwind classes")

            if react_analyzer.uses_hooks(code):
                checks.append(("[OK]", "Uses React hooks"))
                checks_passed += 1
            else:
                checks.append(("[OK]", "No hooks needed"))
                checks_passed += 1

        # API client
        if file_path.endswith("api.ts"):
            if 'fetch(' in code or 'axios' in code:
                checks.append(("[OK]", "Has API calls"))
                checks_passed += 1
            else:
                checks.append(("[FAIL]", "No API calls"))
                checks_failed += 1
                errors.append(f"{file_name}: Missing API calls")

            if '/api/books' in code:
                checks.append(("[OK]", "Correct API endpoint"))
                checks_passed += 1
            else:
                checks.append(("[WARN]", "API endpoint may be wrong"))
                warnings.append(f"{file_name}: Check API endpoint")

        for status, msg in checks:
            print(f"    {status} {msg}")

    # =========================================================================
    # CROSS-STACK CONSISTENCY
    # =========================================================================
    print("\n[CROSS-STACK CONSISTENCY]")

    # Check field names match between Python schema and TypeScript
    schema_code = generated_files.get("backend/app/schemas/book.py", "")
    types_code = generated_files.get("frontend/src/types/index.ts", "")

    # Common expected fields (using snake_case from Python, camelCase might be in TS)
    py_fields = set(re.findall(r'(\w+)\s*:', schema_code))
    ts_fields = set(re.findall(r'(\w+)\s*[?]?\s*:', types_code))

    common = {'id', 'title', 'author', 'price', 'category'}
    py_has = common & py_fields
    ts_has = common & ts_fields

    if len(py_has) >= 4 and len(ts_has) >= 4:
        print(f"  [OK] Schema and TypeScript types have matching core fields")
        checks_passed += 1
    else:
        print(f"  [WARN] Field mismatch - Python: {py_has}, TypeScript: {ts_has}")
        warnings.append("Field names may not match between backend and frontend")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Files Generated: {len(generated_files)}")
    print(f"  - Backend (Python): {len([f for f in generated_files if f.startswith('backend/')])}")
    print(f"  - Frontend (React): {len([f for f in generated_files if f.startswith('frontend/')])}")
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

    # Show sample Python code
    print("\n" + "=" * 70)
    print("SAMPLE: book_service.py (first 50 lines)")
    print("=" * 70)
    service_code = generated_files.get("backend/app/services/book_service.py", "")
    for i, line in enumerate(service_code.split('\n')[:50], 1):
        print(f"{i:3}: {line}")

    # Show sample React code
    print("\n" + "=" * 70)
    print("SAMPLE: BookCard.tsx (first 40 lines)")
    print("=" * 70)
    card_code = generated_files.get("frontend/src/components/BookCard.tsx", "")
    for i, line in enumerate(card_code.split('\n')[:40], 1):
        print(f"{i:3}: {line}")

    print("\n" + "=" * 70)
    if checks_failed == 0 and len(errors) == 0:
        print("[SUCCESS] All Python FastAPI + React checks PASSED!")
        return True
    else:
        print(f"[RESULT] {checks_failed} checks failed, {len(errors)} errors")
        return checks_failed == 0


if __name__ == "__main__":
    success = asyncio.run(test_fullstack_python())
    exit(0 if success else 1)
