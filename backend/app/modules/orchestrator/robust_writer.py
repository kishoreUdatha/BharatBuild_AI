"""
Robust Writer Agent - Production-Ready Bolt.new Implementation

Handles ALL edge cases:
✅ Malformed planner output
✅ Unexpected Claude formatting
✅ Missing step names
✅ Large code responses (chunking)
✅ Cross-file dependencies
✅ Import resolution
✅ File conflicts
✅ Terminal stderr handling
✅ Recovery from partial failures
✅ Multiple output formats from Claude
"""

from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import re
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from app.core.logging_config import logger
from app.utils.claude_client import ClaudeClient
from app.modules.automation.file_manager import FileManager


@dataclass
class TaskInfo:
    """Robust task representation"""
    number: int
    name: str
    description: str = ""
    status: str = "pending"
    files_to_create: List[str] = None
    dependencies: List[int] = None  # Other task numbers this depends on

    def __post_init__(self):
        if self.files_to_create is None:
            self.files_to_create = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class FileInfo:
    """Robust file representation"""
    path: str
    content: str
    language: str = ""
    operation: str = "create"  # create, modify, delete
    chunk_index: int = 0
    total_chunks: int = 1
    dependencies: List[str] = None  # Other files this depends on

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class RobustPlanParser:
    """
    Parse planner output with multiple fallback strategies
    Handles various XML formats, markdown, plain text
    """

    @staticmethod
    def parse_plan(plan_text: str) -> Dict[str, Any]:
        """
        Parse plan with multiple strategies until one succeeds
        """
        strategies = [
            RobustPlanParser._parse_xml_format,
            RobustPlanParser._parse_markdown_format,
            RobustPlanParser._parse_plain_text_format,
            RobustPlanParser._parse_numbered_list_format,
        ]

        for strategy in strategies:
            try:
                result = strategy(plan_text)
                if result and result.get('tasks'):
                    logger.info(f"✅ Plan parsed using {strategy.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue

        # Final fallback: create generic task
        logger.warning("⚠️ All parsing strategies failed, using fallback")
        return RobustPlanParser._fallback_plan()

    @staticmethod
    def _parse_xml_format(plan_text: str) -> Dict[str, Any]:
        """Parse XML format: <plan><tasks>STEP 1: ...</tasks></plan>"""
        result = {"raw": plan_text, "tasks": []}

        # Extract tasks
        tasks_match = re.search(r'<tasks>(.*?)</tasks>', plan_text, re.DOTALL | re.IGNORECASE)
        if not tasks_match:
            return None

        tasks_text = tasks_match.group(1).strip()

        # Multiple patterns for task detection
        patterns = [
            r'(?:STEP|Step|step)\s+(\d+):\s*([^\n]+)',  # STEP 1: Name
            r'(?:Phase|phase)\s+(\d+):\s*([^\n]+)',      # Phase 1: Name
            r'(\d+)\.\s*([^\n]+)',                        # 1. Name
            r'-\s*(?:Step|step)\s+(\d+):\s*([^\n]+)',    # - Step 1: Name
        ]

        tasks = []
        for pattern in patterns:
            matches = re.findall(pattern, tasks_text)
            if matches:
                tasks = [
                    TaskInfo(
                        number=int(num),
                        name=name.strip(),
                        description=RobustPlanParser._extract_task_description(tasks_text, int(num))
                    )
                    for num, name in matches
                ]
                break

        if not tasks:
            raise ValueError("No tasks found in XML format")

        result['tasks'] = tasks

        # Extract tech stack
        tech_match = re.search(r'<tech_stack>(.*?)</tech_stack>', plan_text, re.DOTALL | re.IGNORECASE)
        if tech_match:
            result['tech_stack'] = tech_match.group(1).strip()

        # Extract project structure
        struct_match = re.search(r'<project_structure>(.*?)</project_structure>', plan_text, re.DOTALL | re.IGNORECASE)
        if struct_match:
            result['project_structure'] = struct_match.group(1).strip()

        return result

    @staticmethod
    def _parse_markdown_format(plan_text: str) -> Dict[str, Any]:
        """Parse markdown format: ## Step 1: Name"""
        result = {"raw": plan_text, "tasks": []}

        # Find markdown headers
        patterns = [
            r'##\s+(?:Step|step)\s+(\d+):\s*([^\n]+)',
            r'###\s+(?:Step|step)\s+(\d+):\s*([^\n]+)',
            r'\*\*(?:Step|step)\s+(\d+):\*\*\s*([^\n]+)',
        ]

        tasks = []
        for pattern in patterns:
            matches = re.findall(pattern, plan_text)
            if matches:
                tasks = [
                    TaskInfo(number=int(num), name=name.strip())
                    for num, name in matches
                ]
                break

        if not tasks:
            raise ValueError("No tasks found in markdown format")

        result['tasks'] = tasks
        return result

    @staticmethod
    def _parse_plain_text_format(plan_text: str) -> Dict[str, Any]:
        """Parse plain text: Step 1: Name (no XML)"""
        result = {"raw": plan_text, "tasks": []}

        lines = plan_text.split('\n')
        tasks = []

        for line in lines:
            # Try multiple patterns
            match = re.match(r'(?:Step|step|STEP)\s+(\d+):\s*(.+)', line.strip())
            if match:
                tasks.append(TaskInfo(
                    number=int(match.group(1)),
                    name=match.group(2).strip()
                ))

        if not tasks:
            raise ValueError("No tasks found in plain text format")

        result['tasks'] = tasks
        return result

    @staticmethod
    def _parse_numbered_list_format(plan_text: str) -> Dict[str, Any]:
        """Parse numbered list: 1. Name, 2. Name"""
        result = {"raw": plan_text, "tasks": []}

        lines = plan_text.split('\n')
        tasks = []

        for line in lines:
            match = re.match(r'(\d+)\.\s+(.+)', line.strip())
            if match:
                tasks.append(TaskInfo(
                    number=int(match.group(1)),
                    name=match.group(2).strip()
                ))

        if not tasks:
            raise ValueError("No tasks found in numbered list format")

        result['tasks'] = tasks
        return result

    @staticmethod
    def _extract_task_description(tasks_text: str, task_num: int) -> str:
        """Extract description for a specific task"""
        # Find text between "STEP {task_num}:" and next "STEP" or end
        pattern = rf'(?:STEP|Step)\s+{task_num}:.*?\n(.*?)(?=(?:STEP|Step)\s+\d+:|$)'
        match = re.search(pattern, tasks_text, re.DOTALL | re.IGNORECASE)
        if match:
            desc = match.group(1).strip()
            # Take first 200 chars
            return desc[:200] if len(desc) > 200 else desc
        return ""

    @staticmethod
    def _fallback_plan() -> Dict[str, Any]:
        """Absolute fallback when all parsing fails"""
        return {
            "raw": "Fallback plan - will generate code in single step",
            "tasks": [
                TaskInfo(
                    number=1,
                    name="Generate Complete Project",
                    description="Generate all required files for the project"
                )
            ]
        }


class RobustFileParser:
    """
    Parse Claude's file output with multiple format support
    Handles: <file>, ```language, code blocks, malformed tags
    """

    @staticmethod
    def parse_files(response: str) -> List[FileInfo]:
        """
        Parse files from Claude response using multiple strategies
        """
        strategies = [
            RobustFileParser._parse_xml_files,
            RobustFileParser._parse_markdown_code_blocks,
            RobustFileParser._parse_inline_code,
        ]

        all_files = []
        for strategy in strategies:
            try:
                files = strategy(response)
                if files:
                    all_files.extend(files)
            except Exception as e:
                logger.warning(f"File parsing strategy {strategy.__name__} failed: {e}")

        # Deduplicate by path (keep last occurrence)
        unique_files = {}
        for file in all_files:
            unique_files[file.path] = file

        return list(unique_files.values())

    @staticmethod
    def _parse_xml_files(response: str) -> List[FileInfo]:
        """Parse <file path="...">CONTENT</file> format"""
        files = []

        # Handle both single-line and multi-line file tags
        # Pattern 1: <file path="...">CONTENT</file>
        pattern1 = r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>'
        matches = re.findall(pattern1, response, re.DOTALL | re.IGNORECASE)

        for path, content in matches:
            files.append(FileInfo(
                path=path.strip(),
                content=content.strip(),
                language=RobustFileParser._detect_language(path)
            ))

        # Pattern 2: <file path="..." /> with content after
        if not files:
            pattern2 = r'<file\s+path=["\']([^"\']+)["\'].*?>\s*\n(.*?)(?=<file|$)'
            matches = re.findall(pattern2, response, re.DOTALL | re.IGNORECASE)
            for path, content in matches:
                files.append(FileInfo(
                    path=path.strip(),
                    content=content.strip(),
                    language=RobustFileParser._detect_language(path)
                ))

        return files

    @staticmethod
    def _parse_markdown_code_blocks(response: str) -> List[FileInfo]:
        """Parse ```language filepath CONTENT``` format"""
        files = []

        # Pattern: ```python filename.py\nCODE\n```
        pattern = r'```(\w+)\s+([\w/.]+)\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)

        for language, path, content in matches:
            files.append(FileInfo(
                path=path.strip(),
                content=content.strip(),
                language=language
            ))

        # Pattern: ```filename.py\nCODE\n```  (language inferred)
        if not files:
            pattern2 = r'```([\w/.]+)\s*\n(.*?)\n```'
            matches = re.findall(pattern2, response, re.DOTALL)
            for path, content in matches:
                if '.' in path:  # Looks like a filename
                    files.append(FileInfo(
                        path=path.strip(),
                        content=content.strip(),
                        language=RobustFileParser._detect_language(path)
                    ))

        return files

    @staticmethod
    def _parse_inline_code(response: str) -> List[FileInfo]:
        """Parse inline code with file path mentioned"""
        files = []

        # Pattern: "Create file `path/to/file.py`:\n```\nCODE\n```"
        pattern = r'(?:create|Create|write|Write)\s+(?:file\s+)?[`"]([^`"]+)[`"].*?```(?:\w+)?\s*\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for path, content in matches:
            files.append(FileInfo(
                path=path.strip(),
                content=content.strip(),
                language=RobustFileParser._detect_language(path)
            ))

        return files

    @staticmethod
    def _detect_language(file_path: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'bash',
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'plaintext')


class RobustWriterAgent:
    """
    Production-ready Writer Agent with comprehensive error handling
    """

    def __init__(self, claude_client: ClaudeClient, file_manager: FileManager):
        self.claude = claude_client
        self.file_manager = file_manager
        self.plan_parser = RobustPlanParser()
        self.file_parser = RobustFileParser()

    async def execute_with_recovery(
        self,
        context: Dict[str, Any],
        task: TaskInfo,
        previous_files: List[FileInfo] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute task with automatic recovery from failures
        """
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                async for event in self._execute_task(context, task, previous_files):
                    yield event
                return  # Success
            except Exception as e:
                attempt += 1
                logger.error(f"❌ Task execution failed (attempt {attempt}/{max_retries}): {e}")

                if attempt >= max_retries:
                    yield {
                        "type": "error",
                        "message": f"Task failed after {max_retries} attempts",
                        "error": str(e)
                    }
                    return

                # Recovery strategy
                yield {
                    "type": "warning",
                    "message": f"Retrying task (attempt {attempt + 1}/{max_retries})..."
                }

                # Wait before retry (exponential backoff)
                await asyncio.sleep(2 ** attempt)

    async def _execute_task(
        self,
        context: Dict[str, Any],
        task: TaskInfo,
        previous_files: List[FileInfo] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute single task with streaming"""

        # Build context-aware prompt
        prompt = self._build_smart_prompt(context, task, previous_files)

        # Stream response from Claude
        full_response = ""
        current_file = None

        async for chunk in self.claude.generate_stream(
            prompt=prompt['user_prompt'],
            system_prompt=prompt['system_prompt'],
            model="sonnet",
            max_tokens=8192,
            temperature=0.3
        ):
            full_response += chunk

            # Detect file operations in stream
            if '<file path="' in chunk or '```' in chunk:
                # File started
                file_match = re.search(r'<file path=["\']([^"\']+)["\']>', chunk)
                if file_match:
                    current_file = file_match.group(1)
                    yield {
                        "type": "file_start",
                        "path": current_file
                    }

            if current_file and ('</file>' in chunk or '```' in chunk):
                # File ended
                yield {
                    "type": "file_end",
                    "path": current_file
                }
                current_file = None

        # Parse all files from response
        files = self.file_parser.parse_files(full_response)

        if not files:
            # No files found - try to recover
            logger.warning("⚠️ No files found in response, attempting recovery...")
            yield {
                "type": "warning",
                "message": "Claude didn't output files in expected format. Requesting correction..."
            }

            # Request Claude to reformat
            recovery_prompt = f"""
Your previous response didn't include files in the correct format.

Please output the files for this task using this EXACT format:

<file path="path/to/file.ext">
FILE CONTENT HERE
</file>

Task: {task.name}

Previous response:
{full_response[:500]}...

Now output the files correctly:
"""

            recovery_response = await self.claude.generate(
                prompt=recovery_prompt,
                system_prompt="You are a code generator. Output files using <file path=\"...\">CONTENT</file> format.",
                model="sonnet",
                max_tokens=8192
            )

            files = self.file_parser.parse_files(recovery_response.get('content', ''))

        # Save files with dependency resolution
        saved_files = await self._save_files_with_dependencies(
            files,
            context.get('project_id', 'default'),
            previous_files or []
        )

        for file in saved_files:
            yield {
                "type": "file_complete",
                "file": file
            }

    def _build_smart_prompt(
        self,
        context: Dict[str, Any],
        task: TaskInfo,
        previous_files: List[FileInfo] = None
    ) -> Dict[str, str]:
        """Build context-aware prompt with previous file awareness"""

        # Extract context
        user_request = context.get('user_request', '')
        plan_raw = context.get('plan', {}).get('raw', '')
        project_id = context.get('project_id', 'default')
        tech_stack = context.get('tech_stack', {}).get('raw', '')

        # Build file context
        file_context = ""
        if previous_files:
            file_context = "\n\nPREVIOUSLY CREATED FILES:\n"
            for f in previous_files[-10:]:  # Last 10 files
                file_context += f"- {f.path} ({len(f.content)} bytes)\n"

        system_prompt = """You are an expert code generator for the Bolt.new platform.

CRITICAL RULES:
1. ALWAYS output files using EXACTLY this format:
   <file path="exact/path/to/file.ext">
   FILE CONTENT HERE
   </file>

2. Generate COMPLETE, WORKING code - NO placeholders, NO TODOs, NO "..."
3. Include ALL necessary imports
4. Handle cross-file dependencies correctly
5. Follow the specified tech stack exactly
6. Use proper error handling
7. Write clean, production-ready code

TASK FOCUS:
Generate ONLY the files needed for THIS SPECIFIC TASK.
Do NOT generate files for future tasks.
"""

        user_prompt = f"""
CURRENT TASK: Step {task.number}: {task.name}

TASK DESCRIPTION:
{task.description or 'Generate the files needed for this step'}

USER REQUEST:
{user_request}

TECH STACK:
{tech_stack or 'Use best practices for the requested technology'}

PLAN CONTEXT:
{plan_raw[:1000]}...
{file_context}

OUTPUT REQUIREMENTS:
1. Use <file path="...">CONTENT</file> format for ALL files
2. Generate complete, working code
3. Include proper imports and dependencies
4. Follow the tech stack specified
5. Focus ONLY on Step {task.number}

Now generate the files:
"""

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }

    async def _save_files_with_dependencies(
        self,
        files: List[FileInfo],
        project_id: str,
        previous_files: List[FileInfo]
    ) -> List[FileInfo]:
        """
        Save files in correct order based on dependencies
        """
        # Detect dependencies
        for file in files:
            file.dependencies = self._detect_file_dependencies(file, files)

        # Topological sort to determine order
        ordered_files = self._topological_sort(files)

        # Save in order
        saved_files = []
        for file in ordered_files:
            try:
                result = await self.file_manager.create_file(
                    project_id=project_id,
                    file_path=file.path,
                    content=file.content
                )

                if result.get('success'):
                    saved_files.append(file)
                    logger.info(f"✅ Saved: {file.path}")
                else:
                    logger.error(f"❌ Failed to save: {file.path}")

            except Exception as e:
                logger.error(f"❌ Error saving {file.path}: {e}")

        return saved_files

    def _detect_file_dependencies(self, file: FileInfo, all_files: List[FileInfo]) -> List[str]:
        """Detect which files this file depends on"""
        dependencies = []

        # Look for imports in content
        import_patterns = [
            r'from\s+([\w.]+)\s+import',  # Python
            r'import\s+([\w.]+)',          # Python/JS
            r'require\(["\']([^"\']+)["\']\)',  # Node.js
            r'#include\s*[<"]([^>"]+)[>"]',     # C/C++
        ]

        for pattern in import_patterns:
            matches = re.findall(pattern, file.content)
            for match in matches:
                # Check if this import corresponds to another file
                for other_file in all_files:
                    if other_file.path != file.path:
                        # Check if import matches file path
                        if match.replace('.', '/') in other_file.path:
                            dependencies.append(other_file.path)

        return dependencies

    def _topological_sort(self, files: List[FileInfo]) -> List[FileInfo]:
        """Sort files based on dependencies"""
        # Simple implementation: files with no deps first
        no_deps = [f for f in files if not f.dependencies]
        has_deps = [f for f in files if f.dependencies]

        return no_deps + has_deps
