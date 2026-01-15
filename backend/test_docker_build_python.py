"""
Docker Build Test - Python FastAPI

This test:
1. Generates a complete FastAPI project
2. Runs syntax check and import validation in Docker
3. Reports any errors

Run: python test_docker_build_python.py
"""

import asyncio
import os
import re
import shutil
import subprocess
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
OUTPUT_DIR = Path(__file__).parent / "test_docker_python_project"


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


async def generate_project():
    """Generate a complete FastAPI project."""
    print("=" * 70)
    print("DOCKER BUILD TEST - Python FastAPI")
    print("=" * 70)

    client = AsyncAnthropic()
    generated_files: Dict[str, str] = {}

    # Load prompts
    core = load_prompt("writer_core.txt")
    python = load_prompt("writer_python.txt")
    system_prompt = core + "\n\n" + python

    entity_specs = """
ENTITY_SPECS:
ENTITY: Task
TABLE: tasks
FIELDS:
  - id: int (primary key)
  - title: str
  - description: str (optional)
  - status: TaskStatus (enum)
  - priority: int
  - due_date: date (optional)
  - created_at: datetime
  - updated_at: datetime
API_PATH: /api/tasks

ENUM: TaskStatus
VALUES: TODO, IN_PROGRESS, DONE, CANCELLED
"""

    # Files to generate in dependency order
    files = [
        ("app/core/config.py", "Settings configuration with Pydantic"),
        ("app/core/database.py", "SQLAlchemy async database setup"),
        ("app/models/enums.py", "TaskStatus enum"),
        ("app/models/task.py", "Task SQLAlchemy model"),
        ("app/schemas/task.py", "Pydantic schemas: TaskCreate, TaskUpdate, TaskResponse"),
        ("app/services/task_service.py", "Task service with async CRUD"),
        ("app/api/routes/tasks.py", "FastAPI router for /api/tasks"),
        ("app/main.py", "FastAPI application entry point"),
    ]

    print(f"\n[PHASE 1] Generating {len(files)} Python files...")

    for i, (file_path, description) in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {file_path.split('/')[-1]}")

        # Build context
        context = [f"- {p}" for p in generated_files.keys()]
        dependency_context = ""

        # For database.py: include config code
        if 'database.py' in file_path:
            for path, code in generated_files.items():
                if 'config.py' in path:
                    dependency_context = f"""
CONFIG CLASS (use EXACT attribute names):
```python
{code}
```

CRITICAL: Use the EXACT field names from Settings class above.
If config has 'database_url', use 'settings.database_url' NOT 'settings.DATABASE_URL'
"""

        # For routes: include service AND schema code
        if 'routes/' in file_path:
            schema_context = ""
            service_context = ""
            for path, code in generated_files.items():
                if 'schemas/' in path and 'task' in path.lower():
                    schema_context = f"""
SCHEMA CLASSES (import ONLY these exact class names):
```python
{code}
```

CRITICAL: Only import schema classes that are DEFINED above.
- Do NOT import 'PaginatedTaskResponse' unless it exists in the schema file
- Use List[TaskResponse] for list endpoints instead of inventing pagination schemas
"""
                if 'service' in path and 'task' in path.lower():
                    service_context = f"""
SERVICE CLASS (use ONLY these methods with EXACT signatures):
```python
{code}
```

CRITICAL: Match Service method signatures exactly:
- Use the exact method names from the service
- Match return types (if service returns Optional, handle it)
- Only call methods that exist in the service
"""
            dependency_context = schema_context + "\n" + service_context

        # For main.py: include database.py code
        if 'main.py' in file_path:
            for path, code in generated_files.items():
                if 'database.py' in path:
                    dependency_context = f"""
DATABASE MODULE (use EXACT function names from this file):
```python
{code}
```

CRITICAL: Import and use the EXACT function names defined in database.py above.
- If database.py has 'init_db', import and call 'init_db' NOT 'create_tables'
- If database.py has 'create_tables', import and call 'create_tables' NOT 'init_db'
- Match function names EXACTLY as they appear in the database module
"""

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{entity_specs}
{dependency_context}
FILES ALREADY CREATED:
{chr(10).join(context) if context else "None"}

Requirements:
- Use async/await for database operations
- Type hints on all functions
- Pydantic v2 syntax
- SQLAlchemy 2.0 async style
- Output: <file path="{file_path}">CODE</file>"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code

    return generated_files


def save_project(generated_files: Dict[str, str]):
    """Save generated files and add build files."""
    print(f"\n[PHASE 2] Saving project to {OUTPUT_DIR}...")

    # Clean and create output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Save generated Python files
    for path, content in generated_files.items():
        full_path = OUTPUT_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        print(f"  Saved: {path}")

    # Add __init__.py files
    init_dirs = [
        "app",
        "app/core",
        "app/models",
        "app/schemas",
        "app/services",
        "app/api",
        "app/api/routes",
    ]
    for dir_path in init_dirs:
        init_file = OUTPUT_DIR / dir_path / "__init__.py"
        init_file.parent.mkdir(parents=True, exist_ok=True)
        init_file.write_text("", encoding="utf-8")
    print("  Added: __init__.py files")

    # Add requirements.txt
    requirements = """fastapi
uvicorn
sqlalchemy
aiosqlite
pydantic
pydantic-settings
python-multipart
"""
    (OUTPUT_DIR / "requirements.txt").write_text(requirements, encoding="utf-8")
    print("  Saved: requirements.txt")

    # Add Dockerfile
    dockerfile = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Syntax check all Python files
RUN python -m py_compile app/main.py && \\
    python -m py_compile app/core/config.py && \\
    python -m py_compile app/core/database.py && \\
    python -m py_compile app/models/enums.py && \\
    python -m py_compile app/models/task.py && \\
    python -m py_compile app/schemas/task.py && \\
    python -m py_compile app/services/task_service.py && \\
    python -m py_compile app/api/routes/tasks.py

# Try importing to check for import errors
RUN python -c "from app.main import app; print('Import check passed!')"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    (OUTPUT_DIR / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    print("  Saved: Dockerfile")


def run_docker_build() -> tuple:
    """Run Docker build to validate Python code."""
    print(f"\n[PHASE 3] Running Docker build (syntax + import check)...")

    # Convert path for Docker
    project_path = str(OUTPUT_DIR.absolute()).replace("\\", "/")
    if project_path[1] == ":":
        project_path = "/" + project_path[0].lower() + project_path[2:]

    print(f"  Project path: {project_path}")
    print("  Building Docker image with syntax and import validation...")

    # Build Docker image (this will run syntax checks)
    cmd = [
        "docker", "build",
        "-t", "fastapi-test:latest",
        str(OUTPUT_DIR.absolute())
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout or "", result.stderr or ""

    except subprocess.TimeoutExpired:
        return -1, "", "Build timed out after 5 minutes"
    except Exception as e:
        return -1, "", str(e)


def analyze_build_output(returncode: int, stdout: str, stderr: str) -> List[str]:
    """Analyze build output for errors."""
    errors = []
    output = stdout + stderr

    if returncode == 0:
        return errors

    # Extract Python errors
    error_patterns = [
        r'SyntaxError:.*',
        r'IndentationError:.*',
        r'ImportError:.*',
        r'ModuleNotFoundError:.*',
        r'NameError:.*',
        r'TypeError:.*',
        r'AttributeError:.*',
        r'File ".*", line \d+.*',
        r'Error:.*',
    ]

    for pattern in error_patterns:
        for match in re.finditer(pattern, output):
            error = match.group(0).strip()
            if error and error not in errors:
                errors.append(error)

    return errors


async def main():
    """Run the full Docker build test."""

    # Phase 1: Generate project
    generated_files = await generate_project()
    print(f"\n  Generated {len(generated_files)} files")

    # Phase 2: Save project
    save_project(generated_files)

    # Phase 3: Run Docker build
    returncode, stdout, stderr = run_docker_build()

    # Phase 4: Analyze results
    print("\n" + "=" * 70)
    print("BUILD RESULTS")
    print("=" * 70)

    if returncode == 0:
        print("\n[SUCCESS] Docker build completed successfully!")
        print("\nAll Python files passed:")
        print("  - Syntax validation (py_compile)")
        print("  - Import validation (import check)")

        # Show last few lines of output
        print("\nBuild output (last 15 lines):")
        print("-" * 50)
        lines = (stdout + stderr).strip().split('\n')
        for line in lines[-15:]:
            print(line)
        print("-" * 50)

        print("\n" + "=" * 70)
        print("[SUCCESS] All Python files validated without errors!")
        print("=" * 70)
        return True

    else:
        print("\n[FAILED] Docker build failed!")

        errors = analyze_build_output(returncode, stdout, stderr)

        if errors:
            print(f"\n[Errors Found: {len(errors)}]")
            print("-" * 50)
            for i, error in enumerate(errors[:20], 1):
                print(f"  {i}. {error}")
            print("-" * 50)

        print("\n[Full Build Output]")
        print("-" * 50)
        output = stdout + stderr
        lines = output.strip().split('\n')
        for line in lines[-50:]:
            print(line)
        print("-" * 50)

        print("\n" + "=" * 70)
        print(f"[FAILED] Build failed with {len(errors)} errors")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
