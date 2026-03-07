"""
Coding Agent - Anthropic-Style Autonomous Code Generation

Architecture (following Anthropic's approach):
1. Single strong model (NOT per-stack LoRA adapters)
2. Smart prompting/routing based on task type
3. Agent loop: Read repo -> Generate -> Apply patch -> Test -> Retry
4. Claude-style structured output (PLAN/FILES/PATCH/COMMANDS/NOTES)

This is simpler and more effective than per-stack adapters.
"""

import os
import re
import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# TASK TYPES & SMART PROMPTING (Instead of per-stack adapters)
# ============================================================================

class TaskType(Enum):
    """Task types for smart routing - uses different system prompts."""
    API_IMPLEMENTATION = "api"
    BUG_FIX = "bug"
    ADD_TESTS = "test"
    REFACTOR = "refactor"
    SECURITY = "security"
    AI_ML = "aiml"
    FRONTEND = "frontend"
    DATABASE = "database"
    DEVOPS = "devops"
    GENERAL = "general"


# Task detection keywords for routing
TASK_KEYWORDS = {
    TaskType.API_IMPLEMENTATION: [
        "api", "endpoint", "rest", "crud", "route", "controller",
        "fastapi", "django", "flask", "express", "handler"
    ],
    TaskType.BUG_FIX: [
        "fix", "bug", "error", "issue", "broken", "crash", "fail",
        "not working", "debug", "problem", "exception"
    ],
    TaskType.ADD_TESTS: [
        "test", "pytest", "unittest", "coverage", "spec", "jest",
        "mocha", "testing", "assert", "mock"
    ],
    TaskType.REFACTOR: [
        "refactor", "clean", "improve", "restructure", "solid",
        "optimize", "simplify", "reorganize", "extract"
    ],
    TaskType.SECURITY: [
        "security", "auth", "jwt", "oauth", "password", "encrypt",
        "xss", "sql injection", "csrf", "token", "bcrypt", "hash"
    ],
    TaskType.AI_ML: [
        "pytorch", "tensorflow", "model", "train", "neural", "ml", "ai",
        "sklearn", "pandas", "numpy", "keras", "transformer", "bert"
    ],
    TaskType.FRONTEND: [
        "react", "vue", "angular", "frontend", "component", "ui",
        "css", "html", "jsx", "tsx", "tailwind", "nextjs"
    ],
    TaskType.DATABASE: [
        "database", "sql", "query", "migration", "orm", "postgresql",
        "mongodb", "redis", "mysql", "prisma", "sqlalchemy"
    ],
    TaskType.DEVOPS: [
        "docker", "kubernetes", "deploy", "ci/cd", "pipeline", "nginx",
        "terraform", "aws", "gcp", "azure", "k8s"
    ],
}


def detect_task_type(prompt: str) -> TaskType:
    """
    Detect task type from prompt for smart routing.

    This enables task-specific system prompts without needing
    separate LoRA adapters for each stack.

    Uses weighted keyword matching with priority for domain-specific terms.
    """
    prompt_lower = prompt.lower()
    # Add spaces for word boundary matching
    prompt_spaced = f" {prompt_lower} "
    scores = {task: 0 for task in TaskType}

    # Priority keywords (worth 3 points) - domain-specific terms
    # Use word boundaries to avoid false matches (e.g., "orm" in "form")
    PRIORITY_KEYWORDS = {
        TaskType.SECURITY: ["sql injection", "xss", "csrf", "vulnerability", "owasp", "injection"],
        TaskType.DATABASE: ["n+1", "query optimization", "database migration", " orm "],
        TaskType.AI_ML: ["neural network", "machine learning", "deep learning", "training loop"],
        TaskType.DEVOPS: ["ci/cd", "kubernetes", "docker compose", "infrastructure"],
    }

    # Check priority keywords first (worth 3 points each)
    for task_type, keywords in PRIORITY_KEYWORDS.items():
        for keyword in keywords:
            # Use spaced version for single words to ensure word boundaries
            search_in = prompt_spaced if len(keyword.split()) == 1 else prompt_lower
            if keyword in search_in:
                scores[task_type] += 3

    # Regular keyword matching (worth 1 point each)
    for task_type, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                scores[task_type] += 1

    best_task = max(scores, key=scores.get)
    return best_task if scores[best_task] > 0 else TaskType.GENERAL


# ============================================================================
# TASK-SPECIFIC SYSTEM PROMPTS (Smart routing)
# ============================================================================

BASE_SYSTEM_PROMPT = """You are an expert software engineer. Respond with this exact structure:

PLAN:
1) First step
2) Second step
...

FILES:
- path/to/file.py
...

PATCH:
*** Begin Patch
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -line,count +line,count @@
 context
-removed
+added
*** End Patch

COMMANDS:
- command to run
...

NOTES:
- Important notes
...

Use unified diff format. Be precise and production-ready."""


TASK_SPECIFIC_ADDITIONS = {
    TaskType.API_IMPLEMENTATION: """
Focus on:
- RESTful conventions (proper HTTP methods, status codes)
- Input validation with Pydantic
- Proper error handling (HTTPException)
- Pagination for list endpoints
- OpenAPI documentation""",

    TaskType.BUG_FIX: """
Focus on:
- Root cause analysis first
- Minimal change to fix the issue
- Add test to prevent regression
- Check for similar issues elsewhere""",

    TaskType.ADD_TESTS: """
Focus on:
- Arrange-Act-Assert pattern
- Test edge cases and error paths
- Use fixtures for setup
- Mock external dependencies
- Aim for high coverage of critical paths""",

    TaskType.REFACTOR: """
Focus on:
- SOLID principles
- Don't change external behavior
- Small, incremental changes
- Keep tests passing
- Improve readability""",

    TaskType.SECURITY: """
Focus on:
- OWASP Top 10 prevention
- Input validation and sanitization
- Secure password handling (bcrypt)
- JWT best practices
- No hardcoded secrets
- Parameterized queries (no SQL injection)""",

    TaskType.AI_ML: """
Focus on:
- Reproducibility (set random seeds)
- Proper train/val/test splits
- Avoid data leakage
- Use appropriate metrics
- Save model checkpoints
- Log experiments (wandb/mlflow)""",

    TaskType.FRONTEND: """
Focus on:
- Component reusability
- Proper state management
- Accessibility (a11y)
- Responsive design
- Error boundaries""",

    TaskType.DATABASE: """
Focus on:
- Proper indexing
- N+1 query prevention
- Transaction handling
- Migration safety
- Connection pooling""",

    TaskType.DEVOPS: """
Focus on:
- Infrastructure as code
- Health checks
- Proper logging
- Secret management
- Graceful shutdown""",

    TaskType.GENERAL: ""
}


def get_system_prompt(task_type: TaskType) -> str:
    """Get task-specific system prompt for smart routing."""
    addition = TASK_SPECIFIC_ADDITIONS.get(task_type, "")
    if addition:
        return BASE_SYSTEM_PROMPT + "\n" + addition
    return BASE_SYSTEM_PROMPT


class AgentAction(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    RUN_COMMAND = "run_command"
    RUN_TESTS = "run_tests"
    SEARCH_CODE = "search_code"
    LIST_FILES = "list_files"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentState:
    """Track agent execution state."""
    task: str
    working_dir: Path
    files_read: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    commands_run: List[Dict] = field(default_factory=list)
    test_results: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    retries: int = 0
    max_retries: int = 3
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of an agent action."""
    success: bool
    action: AgentAction
    data: Any = None
    error: Optional[str] = None


@dataclass
class ClaudeStyleOutput:
    """Structured output in Claude Code format."""
    plan: List[str]
    files: List[str]
    patch: str
    commands: List[str]
    notes: List[str]

    def to_string(self) -> str:
        """Convert to Claude-style format string."""
        sections = []

        # PLAN
        sections.append("PLAN:")
        for i, step in enumerate(self.plan, 1):
            sections.append(f"{i}) {step}")

        # FILES
        sections.append("\nFILES:")
        for file in self.files:
            sections.append(f"- {file}")

        # PATCH
        sections.append("\nPATCH:")
        sections.append("*** Begin Patch")
        sections.append(self.patch)
        sections.append("*** End Patch")

        # COMMANDS
        sections.append("\nCOMMANDS:")
        for cmd in self.commands:
            sections.append(f"- {cmd}")

        # NOTES
        sections.append("\nNOTES:")
        for note in self.notes:
            sections.append(f"- {note}")

        return "\n".join(sections)

    @classmethod
    def from_string(cls, text: str) -> "ClaudeStyleOutput":
        """Parse Claude-style format string."""
        plan = []
        files = []
        patch = ""
        commands = []
        notes = []

        current_section = None
        patch_lines = []
        in_patch = False

        for line in text.split("\n"):
            line_stripped = line.strip()

            # Detect section headers
            if line_stripped.startswith("PLAN:"):
                current_section = "plan"
                continue
            elif line_stripped.startswith("FILES:"):
                current_section = "files"
                continue
            elif line_stripped.startswith("PATCH:"):
                current_section = "patch"
                continue
            elif line_stripped.startswith("COMMANDS:"):
                current_section = "commands"
                continue
            elif line_stripped.startswith("NOTES:"):
                current_section = "notes"
                continue

            # Handle patch markers
            if "*** Begin Patch" in line:
                in_patch = True
                continue
            elif "*** End Patch" in line:
                in_patch = False
                patch = "\n".join(patch_lines)
                continue

            # Parse content based on section
            if in_patch:
                patch_lines.append(line)
            elif current_section == "plan" and line_stripped:
                # Remove numbering
                step = re.sub(r"^\d+\)\s*", "", line_stripped)
                if step:
                    plan.append(step)
            elif current_section == "files" and line_stripped.startswith("-"):
                files.append(line_stripped[1:].strip())
            elif current_section == "commands" and line_stripped.startswith("-"):
                commands.append(line_stripped[1:].strip())
            elif current_section == "notes" and line_stripped.startswith("-"):
                notes.append(line_stripped[1:].strip())

        return cls(plan=plan, files=files, patch=patch, commands=commands, notes=notes)


class RepoRAG:
    """Local RAG for repository context injection."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.file_index: Dict[str, str] = {}
        self.code_snippets: List[Dict] = []

    def index_repository(self, extensions: List[str] = None):
        """Index all relevant files in the repository."""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs']

        for root, dirs, files in os.walk(self.repo_path):
            # Skip common non-code directories
            dirs[:] = [d for d in dirs if d not in [
                'node_modules', '.git', '__pycache__', 'venv', '.venv',
                'dist', 'build', '.next', 'coverage'
            ]]

            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.repo_path)
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        self.file_index[str(rel_path)] = content
                        self._extract_snippets(str(rel_path), content)
                    except Exception as e:
                        logger.warning(f"Could not index {file_path}: {e}")

        logger.info(f"Indexed {len(self.file_index)} files")

    def _extract_snippets(self, file_path: str, content: str):
        """Extract code snippets (functions, classes) for context."""
        # Extract Python functions and classes
        if file_path.endswith('.py'):
            patterns = [
                (r'(class\s+\w+.*?(?=\nclass|\ndef|\Z))', 'class'),
                (r'(def\s+\w+.*?(?=\ndef|\nclass|\Z))', 'function'),
            ]
        # Extract JS/TS functions
        elif file_path.endswith(('.js', '.ts', '.tsx', '.jsx')):
            patterns = [
                (r'((?:export\s+)?(?:async\s+)?function\s+\w+.*?(?=\n(?:export|function|class)|\Z))', 'function'),
                (r'((?:export\s+)?class\s+\w+.*?(?=\nclass|\nexport|\Z))', 'class'),
            ]
        else:
            return

        for pattern, snippet_type in patterns:
            for match in re.finditer(pattern, content, re.DOTALL):
                self.code_snippets.append({
                    'file': file_path,
                    'type': snippet_type,
                    'content': match.group(1)[:500],  # Limit size
                })

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for relevant code snippets."""
        results = []
        query_lower = query.lower()
        query_terms = query_lower.split()

        for file_path, content in self.file_index.items():
            content_lower = content.lower()
            score = sum(1 for term in query_terms if term in content_lower)
            if score > 0:
                results.append({
                    'file': file_path,
                    'score': score,
                    'preview': content[:500]
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    def get_file_context(self, file_path: str) -> Optional[str]:
        """Get content of a specific file."""
        return self.file_index.get(file_path)

    def get_related_files(self, file_path: str, limit: int = 5) -> List[str]:
        """Find files related to a given file (imports, similar names)."""
        related = []

        if file_path in self.file_index:
            content = self.file_index[file_path]

            # Find imports
            import_patterns = [
                r'from\s+[\'"]?(\S+)[\'"]?\s+import',
                r'import\s+[\'"](\S+)[\'"]',
                r'require\([\'"](\S+)[\'"]\)',
            ]

            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    imported = match.group(1)
                    # Find matching files
                    for indexed_file in self.file_index:
                        if imported.replace('.', '/') in indexed_file:
                            related.append(indexed_file)

        return list(set(related))[:limit]


class CodingAgent:
    """
    Anthropic-Style Autonomous Coding Agent

    Architecture (following Anthropic's approach):
    1. Single model (NOT per-stack LoRA adapters)
    2. Smart prompting based on task type
    3. Read repository context
    4. Agent loop: Generate -> Apply -> Test -> Retry

    This is simpler and more effective than per-stack adapters.
    """

    def __init__(
        self,
        llm_client,  # Your Qwen or Claude client (single model)
        working_dir: Path,
        max_retries: int = 3
    ):
        self.llm = llm_client
        self.working_dir = Path(working_dir)
        self.max_retries = max_retries
        self.rag = RepoRAG(self.working_dir)
        self.state: Optional[AgentState] = None
        self.current_task_type: Optional[TaskType] = None

    async def initialize(self):
        """Initialize the agent and index the repository."""
        self.rag.index_repository()
        logger.info(f"Agent initialized for {self.working_dir}")

    async def execute_task(self, task: str) -> Dict[str, Any]:
        """
        Execute a coding task with Anthropic-style agent loop.

        Agent loop:
        1. Detect task type for smart prompting
        2. Read repository context
        3. Generate code with task-specific system prompt
        4. Apply patch
        5. Run tests
        6. Retry on failure (up to max_retries)

        Args:
            task: Natural language description of the task

        Returns:
            Result dictionary with success status and details
        """
        # Detect task type for smart prompting (NOT adapter switching)
        self.current_task_type = detect_task_type(task)
        logger.info(f"Task type detected: {self.current_task_type.value}")

        self.state = AgentState(
            task=task,
            working_dir=self.working_dir,
            max_retries=self.max_retries
        )

        # Gather initial context (read repo)
        context = await self._gather_context(task)
        context["task_type"] = self.current_task_type.value
        self.state.context = context

        for attempt in range(self.max_retries):
            self.state.retries = attempt

            try:
                # Plan the approach
                plan = await self._plan_task(task, context)
                logger.info(f"Attempt {attempt + 1}: Plan created with {len(plan)} steps")

                # Execute the plan
                for step in plan:
                    result = await self._execute_step(step)
                    if not result.success:
                        raise Exception(f"Step failed: {result.error}")

                # Run tests to verify
                test_result = await self._run_tests()

                if test_result.success:
                    return {
                        "success": True,
                        "files_modified": self.state.files_modified,
                        "test_results": self.state.test_results,
                        "attempts": attempt + 1
                    }
                else:
                    # Tests failed, will retry
                    error = f"Tests failed: {test_result.error}"
                    self.state.errors.append(error)
                    logger.warning(f"Attempt {attempt + 1} failed: {error}")

                    # Update context with error for next attempt
                    context["last_error"] = error
                    context["test_output"] = test_result.data

            except Exception as e:
                self.state.errors.append(str(e))
                logger.error(f"Attempt {attempt + 1} error: {e}")
                context["last_error"] = str(e)

        # All retries failed
        return {
            "success": False,
            "errors": self.state.errors,
            "files_modified": self.state.files_modified,
            "attempts": self.max_retries
        }

    async def _gather_context(self, task: str) -> Dict[str, Any]:
        """Gather relevant context from the repository."""
        # Search for relevant files
        relevant_files = self.rag.search(task, limit=10)

        # Get project structure
        structure = self._get_project_structure()

        # Detect project type
        project_type = self._detect_project_type()

        return {
            "relevant_files": relevant_files,
            "project_structure": structure,
            "project_type": project_type,
            "total_files": len(self.rag.file_index)
        }

    def _get_project_structure(self, max_depth: int = 3) -> str:
        """Get project directory structure."""
        structure = []

        def walk(path: Path, depth: int = 0):
            if depth > max_depth:
                return

            indent = "  " * depth
            for item in sorted(path.iterdir()):
                if item.name.startswith('.'):
                    continue
                if item.name in ['node_modules', '__pycache__', 'venv', '.venv', 'dist']:
                    continue

                if item.is_dir():
                    structure.append(f"{indent}{item.name}/")
                    walk(item, depth + 1)
                else:
                    structure.append(f"{indent}{item.name}")

        walk(self.working_dir)
        return "\n".join(structure[:100])  # Limit output

    def _detect_project_type(self) -> Dict[str, Any]:
        """Detect the project type and configuration."""
        project_type = {
            "language": "unknown",
            "framework": "unknown",
            "test_command": "echo 'No tests configured'"
        }

        # Check for Python
        if (self.working_dir / "requirements.txt").exists() or \
           (self.working_dir / "pyproject.toml").exists():
            project_type["language"] = "python"
            project_type["test_command"] = "pytest -v"

            if (self.working_dir / "pyproject.toml").exists():
                content = (self.working_dir / "pyproject.toml").read_text()
                if "fastapi" in content.lower():
                    project_type["framework"] = "fastapi"
                elif "django" in content.lower():
                    project_type["framework"] = "django"
                elif "flask" in content.lower():
                    project_type["framework"] = "flask"

        # Check for Node.js
        elif (self.working_dir / "package.json").exists():
            project_type["language"] = "javascript"
            project_type["test_command"] = "npm test"

            content = (self.working_dir / "package.json").read_text()
            if "next" in content:
                project_type["framework"] = "nextjs"
            elif "react" in content:
                project_type["framework"] = "react"
            elif "vue" in content:
                project_type["framework"] = "vue"
            elif "express" in content:
                project_type["framework"] = "express"

        # Check for Go
        elif (self.working_dir / "go.mod").exists():
            project_type["language"] = "go"
            project_type["test_command"] = "go test ./..."

        # Check for Rust
        elif (self.working_dir / "Cargo.toml").exists():
            project_type["language"] = "rust"
            project_type["test_command"] = "cargo test"

        return project_type

    async def _plan_task(self, task: str, context: Dict) -> List[Dict]:
        """
        Use LLM to plan the task execution with smart prompting.

        Uses task-specific system prompt based on detected task type
        (smart prompting instead of per-stack adapters).
        """
        # Get task-specific system prompt (smart routing)
        task_type = self.current_task_type or TaskType.GENERAL
        system_prompt = get_system_prompt(task_type)

        # Build the planning prompt
        error_section = ""
        if context.get('last_error'):
            error_section = f"\n## Previous Error (fix this)\n{context.get('last_error')}"

        prompt = f"""{system_prompt}

## Task
{task}

## Task Type Detected
{task_type.value} (using {task_type.value}-specific guidance)

## Project Context
- Language: {context['project_type']['language']}
- Framework: {context['project_type']['framework']}
- Files: {context['total_files']}

## Relevant Files
{json.dumps([f['file'] for f in context['relevant_files'][:5]], indent=2)}

## Project Structure
{context['project_structure'][:1000]}
{error_section}

## Instructions
Return a JSON array of steps. Each step should have:
- action: one of [read_file, write_file, edit_file, run_command]
- params: action-specific parameters

Example:
[
  {{"action": "read_file", "params": {{"path": "src/main.py"}}}},
  {{"action": "edit_file", "params": {{"path": "src/main.py", "changes": "description of changes"}}}},
  {{"action": "run_command", "params": {{"command": "pytest"}}}}
]

Return ONLY the JSON array, no explanation."""

        response = await self.llm.generate(prompt)

        # Parse the plan
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                return plan
        except json.JSONDecodeError:
            pass

        # Default plan if parsing fails
        return [
            {"action": "read_file", "params": {"path": context['relevant_files'][0]['file']}}
        ] if context['relevant_files'] else []

    async def _execute_step(self, step: Dict) -> ActionResult:
        """Execute a single step in the plan."""
        action = step.get("action")
        params = step.get("params", {})

        try:
            if action == "read_file":
                return await self._read_file(params.get("path"))

            elif action == "write_file":
                return await self._write_file(
                    params.get("path"),
                    params.get("content")
                )

            elif action == "edit_file":
                return await self._edit_file(
                    params.get("path"),
                    params.get("changes")
                )

            elif action == "run_command":
                return await self._run_command(params.get("command"))

            else:
                return ActionResult(
                    success=False,
                    action=AgentAction.ERROR,
                    error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ActionResult(
                success=False,
                action=AgentAction.ERROR,
                error=str(e)
            )

    async def _read_file(self, path: str) -> ActionResult:
        """Read a file from the repository."""
        full_path = self.working_dir / path

        if not full_path.exists():
            return ActionResult(
                success=False,
                action=AgentAction.READ_FILE,
                error=f"File not found: {path}"
            )

        try:
            content = full_path.read_text(encoding='utf-8')
            self.state.files_read.append(path)
            return ActionResult(
                success=True,
                action=AgentAction.READ_FILE,
                data={"path": path, "content": content}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action=AgentAction.READ_FILE,
                error=str(e)
            )

    async def _write_file(self, path: str, content: str) -> ActionResult:
        """Write content to a file."""
        full_path = self.working_dir / path

        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            full_path.write_text(content, encoding='utf-8')
            self.state.files_modified.append(path)

            return ActionResult(
                success=True,
                action=AgentAction.WRITE_FILE,
                data={"path": path}
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action=AgentAction.WRITE_FILE,
                error=str(e)
            )

    async def _edit_file(self, path: str, changes_description: str) -> ActionResult:
        """
        Edit a file based on description (uses LLM with smart prompting).

        Uses task-specific system prompt for better edits.
        """
        # First read the file
        read_result = await self._read_file(path)
        if not read_result.success:
            return read_result

        original_content = read_result.data["content"]

        # Get task-specific system prompt (smart routing)
        task_type = self.current_task_type or TaskType.GENERAL
        system_prompt = get_system_prompt(task_type)

        # Use LLM to generate the edit with task-specific guidance
        prompt = f"""{system_prompt}

## Task Type: {task_type.value}

Edit this file according to the instructions.

## File: {path}

## Current Content:
```
{original_content}
```

## Required Changes:
{changes_description}

## Instructions:
Return ONLY the complete new file content, no explanations.
Preserve the original structure and style.
Apply the {task_type.value}-specific best practices.
"""

        new_content = await self.llm.generate(prompt)

        # Clean up the response (remove markdown code blocks if present)
        if new_content.startswith("```"):
            lines = new_content.split("\n")
            new_content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return await self._write_file(path, new_content)

    async def _run_command(self, command: str) -> ActionResult:
        """Run a shell command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            self.state.commands_run.append({
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:5000]
            })

            return ActionResult(
                success=result.returncode == 0,
                action=AgentAction.RUN_COMMAND,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                },
                error=result.stderr if result.returncode != 0 else None
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                success=False,
                action=AgentAction.RUN_COMMAND,
                error="Command timed out after 5 minutes"
            )
        except Exception as e:
            return ActionResult(
                success=False,
                action=AgentAction.RUN_COMMAND,
                error=str(e)
            )

    async def _run_tests(self) -> ActionResult:
        """Run project tests."""
        test_command = self.state.context.get("project_type", {}).get(
            "test_command",
            "echo 'No tests'"
        )

        result = await self._run_command(test_command)

        self.state.test_results.append({
            "command": test_command,
            "success": result.success,
            "output": result.data
        })

        return result


# ============================================================================
# AGENT API ENDPOINT
# ============================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/agent", tags=["Coding Agent"])


class TaskRequest(BaseModel):
    task: str
    repo_path: str


class TaskResponse(BaseModel):
    success: bool
    files_modified: List[str]
    attempts: int
    errors: List[str] = []
    task_type: str = "general"  # Detected task type for smart prompting


@router.post("/execute", response_model=TaskResponse)
async def execute_coding_task(request: TaskRequest):
    """
    Execute a coding task using Anthropic-style autonomous agent.

    Architecture (following Anthropic's approach):
    1. Single model (NOT per-stack LoRA adapters)
    2. Smart prompting based on detected task type
    3. Agent loop: Read repo -> Generate -> Apply patch -> Test -> Retry

    The agent will:
    1. Detect task type (api, bug, test, refactor, security, aiml, etc.)
    2. Use task-specific system prompt (smart prompting)
    3. Analyze the repository
    4. Plan and implement
    5. Run tests
    6. Retry up to 3 times if tests fail
    """
    from app.utils.qwen_client import QwenClient

    repo_path = Path(request.repo_path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail="Repository path not found")

    # Initialize agent (single model, smart prompting)
    llm = QwenClient()
    agent = CodingAgent(llm, repo_path)
    await agent.initialize()

    # Execute task with Anthropic-style agent loop
    result = await agent.execute_task(request.task)

    return TaskResponse(
        success=result["success"],
        files_modified=result.get("files_modified", []),
        attempts=result.get("attempts", 0),
        errors=result.get("errors", []),
        task_type=agent.current_task_type.value if agent.current_task_type else "general"
    )


# ============================================================================
# USAGE EXAMPLE (Anthropic-style)
# ============================================================================

async def example_usage():
    """
    Example of using the Anthropic-style coding agent.

    Key differences from per-stack adapter approach:
    1. Single model (no adapter switching)
    2. Task type is detected automatically
    3. System prompt changes based on task type (smart prompting)
    4. Agent loop handles retries automatically
    """
    from app.utils.qwen_client import QwenClient

    # Initialize (single model, not per-stack adapters)
    llm = QwenClient()
    agent = CodingAgent(llm, Path("/path/to/repo"))
    await agent.initialize()

    # Example tasks with different types
    tasks = [
        "Add a new endpoint POST /api/users with email validation",  # -> API_IMPLEMENTATION
        "Fix the memory leak in the connection pool",                 # -> BUG_FIX
        "Add unit tests for the payment service",                     # -> ADD_TESTS
        "Train a CNN for image classification",                       # -> AI_ML
        "Add JWT authentication to the API",                          # -> SECURITY
    ]

    for task in tasks:
        # Task type is detected automatically
        task_type = detect_task_type(task)
        print(f"\nTask: {task}")
        print(f"Detected type: {task_type.value}")
        print(f"Using {task_type.value}-specific system prompt")

    # Execute a task (full agent loop)
    result = await agent.execute_task(
        "Add a new endpoint POST /api/users that creates a user with email and password validation"
    )

    if result["success"]:
        print(f"\nTask completed in {result['attempts']} attempt(s)")
        print(f"Task type used: {agent.current_task_type.value}")
        print(f"Modified files: {result['files_modified']}")
    else:
        print(f"\nTask failed after {result['attempts']} attempts")
        print(f"Errors: {result['errors']}")


# ============================================================================
# WHY ANTHROPIC-STYLE IS BETTER THAN PER-STACK ADAPTERS
# ============================================================================

"""
Per-stack LoRA adapters approach:
- Separate adapter for FastAPI, Django, React, etc.
- Need to load/switch adapters based on task
- More complex deployment
- Knowledge is siloed

Anthropic-style (what we use):
- Single strong model trained on ALL samples
- Smart prompting: different system prompts per task type
- Shared learning across all stacks
- Simpler deployment
- Agent loop handles errors automatically

The key insight: Claude Code doesn't use per-stack adapters.
It uses a single strong model with smart prompting and an agent loop.
"""
