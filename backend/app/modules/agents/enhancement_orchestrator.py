"""
Enhancement Orchestrator - Coordinates Enhancer, Writer, and Fixer agents

Workflow:
1. User requests enhancement (e.g., "Add Admin Panel")
2. Enhancer Agent creates enhancement plan
3. Orchestrator executes tasks using Writer/Fixer agents
4. Results are saved to project
"""

from typing import Dict, Any, List
from app.modules.agents.enhancer_agent import EnhancerAgent
from app.utils.claude_client import ClaudeClient
import asyncio
import os
from pathlib import Path


class EnhancementOrchestrator:
    """
    Orchestrates the enhancement workflow using multiple agents.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.enhancer = EnhancerAgent()
        self.claude_client = ClaudeClient()

    async def execute_enhancement(
        self,
        project_analysis: Dict[str, Any],
        enhancement_request: str,
        stream_callback=None
    ) -> Dict[str, Any]:
        """
        Execute complete enhancement workflow.

        Args:
            project_analysis: Current project structure
            enhancement_request: What user wants to add
            stream_callback: Function to call with progress updates

        Returns:
            Dict with created/modified files and status
        """

        results = {
            "status": "in_progress",
            "plan": {},
            "tasks_completed": 0,
            "tasks_total": 0,
            "files_created": [],
            "files_modified": [],
            "errors": []
        }

        try:
            # Step 1: Create enhancement plan
            if stream_callback:
                await stream_callback("📋 Creating enhancement plan...")

            plan = await self.enhancer.create_enhancement_plan(
                project_analysis,
                enhancement_request
            )

            results["plan"] = plan

            # Generate task list
            tasks = self.enhancer.generate_task_list(plan)
            results["tasks_total"] = len(tasks)

            if stream_callback:
                await stream_callback(f"✅ Plan created: {len(tasks)} tasks identified")
                await stream_callback(f"Summary: {plan['summary']}")

            # Step 2: Execute tasks in order
            for i, task in enumerate(tasks, 1):
                if stream_callback:
                    await stream_callback(f"\n[{i}/{len(tasks)}] {task['description']}")

                try:
                    if task["agent"] == "writer":
                        # Create new file
                        result = await self._execute_writer_task(task)
                        results["files_created"].append(result["file"])

                    elif task["agent"] == "fixer":
                        # Modify existing file
                        result = await self._execute_fixer_task(task)
                        results["files_modified"].append(result["file"])

                    elif task["agent"] == "tester":
                        # Generate tests
                        result = await self._execute_tester_task(task)
                        results["files_created"].append(result["file"])

                    results["tasks_completed"] += 1

                    if stream_callback:
                        await stream_callback(f"  ✅ Completed: {result['file']}")

                except Exception as e:
                    error_msg = f"Error in task {i}: {str(e)}"
                    results["errors"].append(error_msg)

                    if stream_callback:
                        await stream_callback(f"  ❌ Error: {str(e)}")

            # Step 3: Final status
            results["status"] = "completed" if not results["errors"] else "completed_with_errors"

            if stream_callback:
                await stream_callback(f"\n🎉 Enhancement complete!")
                await stream_callback(f"   Files created: {len(results['files_created'])}")
                await stream_callback(f"   Files modified: {len(results['files_modified'])}")
                if results["errors"]:
                    await stream_callback(f"   ⚠️  Errors: {len(results['errors'])}")

        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(str(e))

            if stream_callback:
                await stream_callback(f"❌ Enhancement failed: {str(e)}")

        return results

    async def _execute_writer_task(self, task: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a Writer agent task (create new file).

        Args:
            task: Task specification

        Returns:
            Result with file path and content
        """

        # Determine what type of file to generate
        file_path = task["file"]
        is_backend = "backend" in file_path
        is_model = "models" in file_path
        is_api = "api" in file_path or "endpoints" in file_path
        is_frontend = "frontend" in file_path or "src" in file_path

        # Create appropriate prompt based on file type
        if is_model:
            prompt = self._create_model_prompt(task)
        elif is_api:
            prompt = self._create_api_prompt(task)
        elif is_frontend:
            prompt = self._create_frontend_prompt(task)
        else:
            prompt = self._create_generic_prompt(task)

        # Call Claude to generate code
        response = await self.claude_client.generate(
            prompt=prompt,
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.7
        )

        code = response['content'][0]['text']

        # Extract code from markdown if present
        if "```" in code:
            code = self._extract_code_from_markdown(code)

        # Save file
        full_path = self.project_root / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(code)

        return {
            "file": file_path,
            "content": code,
            "status": "created"
        }

    async def _execute_fixer_task(self, task: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a Fixer agent task (modify existing file).

        Args:
            task: Task specification

        Returns:
            Result with file path and modifications
        """

        file_path = self.project_root / task["file"]

        # Read existing file
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {task['file']}")

        with open(file_path, 'r', encoding='utf-8') as f:
            existing_code = f.read()

        # Create modification prompt
        prompt = f"""Modify the following code based on these specifications:

# CURRENT CODE
```
{existing_code}
```

# MODIFICATION REQUIRED
{task['description']}

# SPECIFICATIONS
{task['specifications']}

# INSTRUCTIONS
- Maintain existing functionality
- Add the new features as specified
- Keep code style consistent
- Add comments for new sections
- Ensure backward compatibility

Output the COMPLETE modified file (not just changes).
"""

        # Call Claude
        response = await self.claude_client.generate(
            prompt=prompt,
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000
        )

        modified_code = response['content'][0]['text']

        # Extract code
        if "```" in modified_code:
            modified_code = self._extract_code_from_markdown(modified_code)

        # Save modified file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_code)

        return {
            "file": task["file"],
            "content": modified_code,
            "status": "modified"
        }

    async def _execute_tester_task(self, task: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a Tester agent task (generate tests).

        Args:
            task: Task specification

        Returns:
            Result with test file path
        """

        # Generate test file path
        test_file = f"backend/tests/test_{task['description'].lower().replace(' ', '_')}.py"

        prompt = f"""Generate comprehensive pytest tests for:

# REQUIREMENT
{task['description']}

# SPECIFICATIONS
{task['specifications']}

# INSTRUCTIONS
- Use pytest framework
- Include fixtures if needed
- Test happy path and edge cases
- Add docstrings
- Use proper assertions

Generate COMPLETE test file.
"""

        response = await self.claude_client.generate(
            prompt=prompt,
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000
        )

        test_code = response['content'][0]['text']

        if "```" in test_code:
            test_code = self._extract_code_from_markdown(test_code)

        # Save test file
        test_path = self.project_root / test_file
        test_path.parent.mkdir(parents=True, exist_ok=True)

        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_code)

        return {
            "file": test_file,
            "content": test_code,
            "status": "created"
        }

    def _create_model_prompt(self, task: Dict[str, str]) -> str:
        """Create prompt for database model generation"""

        return f"""Generate a SQLAlchemy database model based on these specifications:

# MODEL SPECIFICATIONS
{task['specifications']}

# DESCRIPTION
{task['description']}

# REQUIREMENTS
- Use SQLAlchemy 2.0 async syntax
- Include proper type hints
- Add relationships if specified
- Include timestamps (created_at, updated_at)
- Add __repr__ method
- Use UUID for primary keys

# EXAMPLE FORMAT
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime

class ModelName(Base):
    __tablename__ = "table_name"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ... fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ModelName(id={{self.id}})>"
```

Generate the complete model file.
"""

    def _create_api_prompt(self, task: Dict[str, str]) -> str:
        """Create prompt for API endpoint generation"""

        return f"""Generate FastAPI endpoint(s) based on these specifications:

# ENDPOINT SPECIFICATIONS
{task['specifications']}

# DESCRIPTION
{task['description']}

# REQUIREMENTS
- Use FastAPI router
- Include proper Pydantic schemas for request/response
- Add authentication dependency if needed
- Include error handling
- Add OpenAPI documentation (docstrings)
- Follow REST principles

# EXAMPLE FORMAT
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.your_schema import YourSchema
from typing import List

router = APIRouter()

@router.get("/items", response_model=List[YourSchema])
async def get_items(db: AsyncSession = Depends(get_db)):
    \"\"\"Get all items\"\"\"
    # Implementation
    pass
```

Generate the complete API file.
"""

    def _create_frontend_prompt(self, task: Dict[str, str]) -> str:
        """Create prompt for frontend component generation"""

        return f"""Generate a React/Next.js component based on these specifications:

# COMPONENT SPECIFICATIONS
{task['specifications']}

# DESCRIPTION
{task['description']}

# REQUIREMENTS
- Use TypeScript
- Use React hooks (useState, useEffect, etc.)
- Include proper TypeScript types
- Add comments for complex logic
- Use Tailwind CSS for styling
- Include error handling

# EXAMPLE FORMAT
```typescript
'use client';

import {{ useState, useEffect }} from 'react';

interface ComponentProps {{
  // props
}}

export function ComponentName({{ prop1, prop2 }}: ComponentProps) {{
  const [state, setState] = useState<Type>(initialValue);

  return (
    <div className="...">
      {{/* Component JSX */}}
    </div>
  );
}}
```

Generate the complete component file.
"""

    def _create_generic_prompt(self, task: Dict[str, str]) -> str:
        """Create generic prompt for other file types"""

        return f"""Generate code based on these specifications:

# FILE: {task['file']}

# DESCRIPTION
{task['description']}

# SPECIFICATIONS
{task['specifications']}

Generate clean, well-commented, production-ready code.
"""

    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract code from markdown code blocks"""

        import re
        pattern = r'```(?:\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            return matches[0].strip()
        return text


# CLI usage example
async def main():
    """
    CLI example for enhancement
    """
    from app.modules.agents.project_analyzer import ProjectAnalyzer

    print("=" * 60)
    print("🔧 ENHANCEMENT ORCHESTRATOR")
    print("=" * 60)
    print()

    # Analyze project
    project_root = r"C:\Users\KishoreUdatha\IdeaProjects\BharatBuild_AI"
    analyzer = ProjectAnalyzer(project_root)
    analysis = analyzer.analyze()

    print(f"📁 Project: {analysis['project_name']}")
    print()

    # Get user input
    print("What would you like to add to the project?")
    print()
    print("Examples:")
    print("  1. Add Admin Panel")
    print("  2. Add OTP authentication")
    print("  3. Add analytics dashboard with charts")
    print("  4. Add ML model integration")
    print()

    enhancement_request = input("Enter your request: ")

    # Create orchestrator
    orchestrator = EnhancementOrchestrator(project_root)

    # Stream callback
    async def progress_callback(message: str):
        print(message)

    # Execute enhancement
    results = await orchestrator.execute_enhancement(
        analysis,
        enhancement_request,
        progress_callback
    )

    # Summary
    print("\n" + "=" * 60)
    print("✅ ENHANCEMENT COMPLETE")
    print("=" * 60)
    print(f"\nStatus: {results['status']}")
    print(f"Tasks completed: {results['tasks_completed']}/{results['tasks_total']}")
    print(f"\nFiles created: {len(results['files_created'])}")
    for file in results['files_created']:
        print(f"  ✅ {file}")

    if results['files_modified']:
        print(f"\nFiles modified: {len(results['files_modified'])}")
        for file in results['files_modified']:
            print(f"  📝 {file}")

    if results['errors']:
        print(f"\n⚠️  Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  ❌ {error}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
