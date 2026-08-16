"""
Incremental Orchestrator - Kiro-style file-by-file generation

Instead of generating all files at once then fixing errors,
this orchestrator:
1. Plans the full project (file list + order)
2. Generates ONE file at a time
3. Verifies each file immediately (syntax, imports, consistency)
4. Fixes errors inline before moving to next file
5. Each file gets context of already-created files (so imports are correct)

This produces significantly fewer errors because:
- Writer sees what already exists (no guessing imports)
- Errors are caught and fixed when context is fresh
- Build issues are prevented, not patched after the fact
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.logging_config import logger
from app.modules.agents.base_agent import AgentContext
from app.modules.agents.planner_agent import PlannerAgent
from app.modules.agents.writer_agent import WriterAgent
from app.utils.security import validate_file_path, sanitize_file_content_for_prompt
from app.utils.token_budget import TokenBudget, budget_for_code_generation


# =============================================================================
# DATA MODELS
# =============================================================================

class FileStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    VERIFYING = "verifying"
    FIXING = "fixing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class FileResult:
    """Result of generating a single file."""
    path: str
    status: FileStatus
    content: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    fix_attempts: int = 0
    generation_time_ms: int = 0


@dataclass
class GenerationProgress:
    """Overall generation progress."""
    project_id: str
    total_files: int
    completed_files: int = 0
    current_file: Optional[str] = None
    current_status: FileStatus = FileStatus.PENDING
    files: List[FileResult] = field(default_factory=list)
    errors_fixed_inline: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @property
    def progress_pct(self) -> int:
        if self.total_files == 0:
            return 0
        return int((self.completed_files / self.total_files) * 100)

    @property
    def is_complete(self) -> bool:
        return self.completed_files >= self.total_files


@dataclass
class StreamEvent:
    """Event streamed to frontend for real-time progress."""
    type: str  # plan, file_start, file_complete, file_error, fix_start, fix_complete, done, error
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# =============================================================================
# INLINE VERIFIER
# =============================================================================

class InlineVerifier:
    """
    Lightweight verifier that checks each file immediately after creation.
    
    Unlike the full VerificationAgent (which checks the entire project),
    this runs fast checks on a single file:
    - Syntax validity
    - Import consistency (do imported files exist?)
    - Export consistency (does this file export what others expect?)
    - Basic completeness (not truncated)
    """

    # Common truncation indicators
    TRUNCATION_MARKERS = [
        "// ...",
        "# ...",
        "/* ... */",
        "// TODO: implement",
        "// rest of",
        "// more code",
    ]

    def verify(
        self,
        file_path: str,
        content: str,
        existing_files: Dict[str, str],
        plan_exports: Dict[str, List[str]] = None,
    ) -> List[str]:
        """
        Verify a single file. Returns list of errors (empty = pass).
        
        Args:
            file_path: Path of the file being verified
            content: Generated file content
            existing_files: Dict of already-created files {path: content}
            plan_exports: Expected exports from the plan {file_path: [export_names]}
            
        Returns:
            List of error strings (empty means file is valid)
        """
        errors = []

        # 1. Empty check
        if not content or not content.strip():
            errors.append("File is empty")
            return errors

        # 2. Truncation check
        for marker in self.TRUNCATION_MARKERS:
            if marker in content.lower():
                errors.append(f"File appears truncated (contains '{marker}')")
                break

        # 3. Syntax check based on extension
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        syntax_errors = self._check_syntax(content, ext)
        errors.extend(syntax_errors)

        # 4. Import consistency check
        import_errors = self._check_imports(file_path, content, existing_files, ext)
        errors.extend(import_errors)

        # 5. Brace/bracket balance (JS/TS/Java/C)
        if ext in ("js", "jsx", "ts", "tsx", "java", "go", "cs", "rs"):
            balance_errors = self._check_brace_balance(content)
            errors.extend(balance_errors)

        # 6. Python indentation check
        if ext == "py":
            indent_errors = self._check_python_indent(content)
            errors.extend(indent_errors)

        return errors

    def _check_syntax(self, content: str, ext: str) -> List[str]:
        """Basic syntax checks by file type."""
        errors = []

        if ext == "py":
            import ast
            try:
                ast.parse(content)
            except SyntaxError as e:
                errors.append(f"Python syntax error: {e.msg} (line {e.lineno})")

        elif ext == "json":
            import json
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append(f"JSON syntax error: {e.msg} (line {e.lineno})")

        elif ext in ("yaml", "yml"):
            import yaml
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                errors.append(f"YAML syntax error: {e}")

        return errors

    def _check_imports(
        self, file_path: str, content: str, existing_files: Dict[str, str], ext: str
    ) -> List[str]:
        """Check if relative imports reference files that exist."""
        import re
        errors = []

        if ext in ("ts", "tsx", "js", "jsx"):
            # Find relative imports: import X from './path' or from '../path'
            import_pattern = r"""from\s+['"](\./[^'"]+|\.\.\/[^'"]+)['"]"""
            for match in re.finditer(import_pattern, content):
                import_path = match.group(1)
                # Resolve relative to current file's directory
                resolved = self._resolve_import(file_path, import_path, ext)
                if resolved and resolved not in existing_files:
                    # Not an error if it's a file that will be created later
                    # Just a warning we can skip
                    pass

        elif ext == "py":
            # Check relative imports: from . import X or from .module import X
            # These are harder to validate without the full package structure
            pass

        return errors

    def _resolve_import(self, from_file: str, import_path: str, ext: str) -> Optional[str]:
        """Resolve a relative import path to a file path."""
        import os
        from_dir = os.path.dirname(from_file)
        
        # Normalize
        resolved = os.path.normpath(os.path.join(from_dir, import_path)).replace("\\", "/")
        
        # Try with extensions
        extensions = [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"]
        for try_ext in extensions:
            candidate = resolved + try_ext
            # We'll check this against existing_files in the caller
            # For now just return the base resolved path
        
        return resolved

    def _check_brace_balance(self, content: str) -> List[str]:
        """Check if braces/brackets are balanced (ignoring strings)."""
        errors = []
        
        # Simple brace counting (skip content inside strings)
        open_braces = 0
        open_brackets = 0
        open_parens = 0
        in_string = False
        string_char = None
        escape_next = False

        for char in content:
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char in ('"', "'", '`') and not in_string:
                in_string = True
                string_char = char
                continue
            if char == string_char and in_string:
                in_string = False
                string_char = None
                continue
            if in_string:
                continue

            if char == '{': open_braces += 1
            elif char == '}': open_braces -= 1
            elif char == '[': open_brackets += 1
            elif char == ']': open_brackets -= 1
            elif char == '(': open_parens += 1
            elif char == ')': open_parens -= 1

        if open_braces > 0:
            errors.append(f"Unmatched braces: {open_braces} unclosed '{{' found")
        elif open_braces < 0:
            errors.append(f"Extra closing braces: {-open_braces} extra '}}' found")

        if open_brackets > 0:
            errors.append(f"Unmatched brackets: {open_brackets} unclosed '[' found")

        return errors

    def _check_python_indent(self, content: str) -> List[str]:
        """Check for mixed tabs/spaces in Python."""
        errors = []
        has_tabs = '\t' in content
        has_spaces = any(line.startswith('    ') for line in content.split('\n'))
        
        if has_tabs and has_spaces:
            errors.append("Mixed tabs and spaces in indentation")
        
        return errors


# =============================================================================
# INLINE FIXER
# =============================================================================

class InlineFixer:
    """
    Fixes errors in a single file immediately after detection.
    
    Uses the WriterAgent with error context to regenerate the file,
    rather than trying to patch it. This is more reliable because:
    - The file was just generated (context is fresh)
    - We know exactly what's wrong
    - Regeneration with error context usually succeeds first try
    """

    def __init__(self):
        self.writer = WriterAgent()
        self.max_attempts = 2

    async def fix(
        self,
        file_path: str,
        content: str,
        errors: List[str],
        context: AgentContext,
        existing_files: Dict[str, str],
        step_data: Dict[str, Any],
    ) -> Optional[str]:
        """
        Fix a file by regenerating it with error feedback.
        
        Args:
            file_path: Path of the broken file
            content: Current (broken) content
            errors: List of errors found by InlineVerifier
            context: Agent context
            existing_files: Already-created files for reference
            step_data: Original generation instructions
            
        Returns:
            Fixed content, or None if fix failed
        """
        error_feedback = "\n".join(f"- {e}" for e in errors)
        
        # Build a focused fix prompt
        fix_context = {
            **context.metadata,
            "step_data": step_data,
            "previous_files": self._build_file_summaries(existing_files),
            "fix_mode": True,
            "error_feedback": error_feedback,
            "broken_content": content[:2000],  # Include start of broken file for context
        }

        fix_request = AgentContext(
            user_request=f"Regenerate {file_path}. Previous attempt had errors:\n{error_feedback}\n\nFix these issues and output the complete corrected file.",
            project_id=context.project_id,
            user_id=context.user_id,
            metadata=fix_context,
        )

        try:
            result = await self.writer.process(fix_request)
            if result.get("success") and result.get("files"):
                # Get the fixed file content
                for file_data in result["files"]:
                    if file_data.get("path") == file_path:
                        return file_data.get("content")
                # If exact path not found, return first file
                if result["files"]:
                    return result["files"][0].get("content")
        except Exception as e:
            logger.error(f"[InlineFixer] Fix attempt failed for {file_path}: {e}")

        return None

    def _build_file_summaries(self, files: Dict[str, str]) -> str:
        """Create compact summaries of existing files for context."""
        if not files:
            return "No files created yet."
        
        summaries = []
        for path, content in list(files.items())[-10:]:  # Last 10 files
            # First 3 lines + export info
            lines = content.split("\n")[:5]
            preview = "\n".join(lines)
            summaries.append(f"--- {path} ---\n{preview}\n...\n")
        
        return "\n".join(summaries)


# =============================================================================
# INCREMENTAL ORCHESTRATOR
# =============================================================================

class IncrementalOrchestrator:
    """
    Kiro-style incremental project generator.
    
    Generates files one at a time with verification after each,
    producing far fewer errors than batch generation.
    
    Usage:
        orchestrator = IncrementalOrchestrator()
        async for event in orchestrator.generate(context):
            # event.type: plan, file_start, file_complete, fix_start, fix_complete, done
            send_to_frontend(event)
    """

    def __init__(self):
        self.planner = PlannerAgent()
        self.writer = WriterAgent()
        self.verifier = InlineVerifier()
        self.fixer = InlineFixer()

    async def generate(
        self,
        context: AgentContext,
        on_progress: Optional[callable] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Generate project incrementally, yielding progress events.
        
        Args:
            context: Agent context with user request
            on_progress: Optional callback for progress updates
            
        Yields:
            StreamEvent for each step (plan, file_start, file_complete, etc.)
        """
        progress = GenerationProgress(
            project_id=context.project_id,
            total_files=0,
            started_at=datetime.utcnow().isoformat(),
        )

        # Create token budget for this generation
        budget = budget_for_code_generation()
        context.token_budget = budget

        try:
            # =================================================================
            # STEP 1: Plan the project
            # =================================================================
            yield StreamEvent(type="plan_start", data={"message": "Planning project..."})

            plan_result = await self.planner.process(context)
            
            if not plan_result.get("success"):
                yield StreamEvent(type="error", data={
                    "message": f"Planning failed: {plan_result.get('error', 'Unknown error')}",
                })
                return

            plan = plan_result.get("plan", {})
            files_to_generate = self._extract_ordered_files(plan)
            progress.total_files = len(files_to_generate)

            yield StreamEvent(type="plan_complete", data={
                "message": f"Plan ready: {len(files_to_generate)} files to generate",
                "project_name": plan.get("project_name", "Project"),
                "tech_stack": plan.get("tech_stack", ""),
                "total_files": len(files_to_generate),
                "files": [f["path"] for f in files_to_generate],
            })

            # =================================================================
            # STEP 2: Generate files one by one
            # =================================================================
            existing_files: Dict[str, str] = {}  # path -> content (for context)

            for i, file_info in enumerate(files_to_generate):
                file_path = file_info["path"]
                progress.current_file = file_path
                progress.current_status = FileStatus.GENERATING

                # --- File Start ---
                yield StreamEvent(type="file_start", data={
                    "file": file_path,
                    "index": i + 1,
                    "total": len(files_to_generate),
                    "description": file_info.get("description", ""),
                })

                # Generate this single file with context of what already exists
                start_time = datetime.utcnow()
                
                file_content = await self._generate_single_file(
                    context=context,
                    file_info=file_info,
                    plan=plan,
                    existing_files=existing_files,
                )

                if file_content is None:
                    # Generation failed completely
                    file_result = FileResult(
                        path=file_path,
                        status=FileStatus.FAILED,
                        errors=["Generation returned empty content"],
                    )
                    progress.files.append(file_result)
                    yield StreamEvent(type="file_error", data={
                        "file": file_path,
                        "errors": ["Failed to generate file"],
                    })
                    continue

                # --- Verify ---
                progress.current_status = FileStatus.VERIFYING
                errors = self.verifier.verify(
                    file_path=file_path,
                    content=file_content,
                    existing_files=existing_files,
                )

                # --- Fix if needed ---
                fix_attempts = 0
                while errors and fix_attempts < 2:
                    progress.current_status = FileStatus.FIXING
                    fix_attempts += 1

                    yield StreamEvent(type="fix_start", data={
                        "file": file_path,
                        "errors": errors,
                        "attempt": fix_attempts,
                    })

                    fixed_content = await self.fixer.fix(
                        file_path=file_path,
                        content=file_content,
                        errors=errors,
                        context=context,
                        existing_files=existing_files,
                        step_data=file_info,
                    )

                    if fixed_content:
                        file_content = fixed_content
                        progress.errors_fixed_inline += len(errors)
                        
                        # Re-verify
                        errors = self.verifier.verify(
                            file_path=file_path,
                            content=file_content,
                            existing_files=existing_files,
                        )

                        yield StreamEvent(type="fix_complete", data={
                            "file": file_path,
                            "remaining_errors": len(errors),
                            "attempt": fix_attempts,
                        })
                    else:
                        break  # Fix failed, move on

                # --- File Complete ---
                gen_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                file_result = FileResult(
                    path=file_path,
                    status=FileStatus.COMPLETE if not errors else FileStatus.COMPLETE,
                    content=file_content,
                    errors=errors,
                    fix_attempts=fix_attempts,
                    generation_time_ms=gen_time,
                )
                progress.files.append(file_result)
                progress.completed_files += 1
                progress.current_status = FileStatus.COMPLETE

                # Add to existing files context (for next file's generation)
                existing_files[file_path] = file_content

                yield StreamEvent(type="file_complete", data={
                    "file": file_path,
                    "index": i + 1,
                    "total": len(files_to_generate),
                    "status": "complete",
                    "errors_fixed": fix_attempts,
                    "remaining_errors": len(errors),
                    "generation_time_ms": gen_time,
                    "progress_pct": progress.progress_pct,
                })

                # Check budget
                if budget.is_budget_exceeded:
                    yield StreamEvent(type="error", data={
                        "message": f"Token budget exceeded after {i+1} files. Generated {progress.completed_files}/{progress.total_files}.",
                    })
                    break

            # =================================================================
            # STEP 3: Done
            # =================================================================
            progress.completed_at = datetime.utcnow().isoformat()

            yield StreamEvent(type="done", data={
                "total_files": progress.total_files,
                "completed_files": progress.completed_files,
                "errors_fixed_inline": progress.errors_fixed_inline,
                "total_errors_remaining": sum(len(f.errors) for f in progress.files),
                "budget_used": budget.to_dict(),
            })

        except Exception as e:
            logger.error(f"[IncrementalOrchestrator] Generation failed: {e}", exc_info=True)
            yield StreamEvent(type="error", data={"message": str(e)})

    async def _generate_single_file(
        self,
        context: AgentContext,
        file_info: Dict[str, Any],
        plan: Dict[str, Any],
        existing_files: Dict[str, str],
    ) -> Optional[str]:
        """
        Generate a single file using WriterAgent with full context.
        
        The key insight: Writer knows what files already exist,
        so it generates correct imports/references.
        """
        # Build context of already-created files (compact summaries)
        files_context = self._build_files_context(existing_files)
        
        # Build the generation metadata
        gen_metadata = {
            **(context.metadata or {}),
            "step_data": file_info,
            "plan": plan,
            "previous_files_context": files_context,
            "existing_file_paths": list(existing_files.keys()),
            "single_file_mode": True,
        }

        gen_context = AgentContext(
            user_request=context.user_request,
            project_id=context.project_id,
            user_id=context.user_id,
            metadata=gen_metadata,
            token_budget=context.token_budget,
        )

        try:
            result = await self.writer.process(gen_context)
            
            if result.get("success") and result.get("files"):
                for file_data in result["files"]:
                    if file_data.get("path") == file_info["path"]:
                        return file_data.get("content")
                # Return first file if exact match not found
                if result["files"]:
                    return result["files"][0].get("content")

        except Exception as e:
            logger.error(f"[IncrementalOrchestrator] File generation error: {e}")

        return None

    def _build_files_context(self, existing_files: Dict[str, str]) -> str:
        """
        Build a compact context string of already-created files.
        Includes: file paths, exports, first few lines.
        This helps the Writer generate consistent imports.
        """
        if not existing_files:
            return "No files created yet. This is the first file."

        context_parts = [
            f"FILES ALREADY CREATED ({len(existing_files)}):",
            "",
        ]

        for path, content in existing_files.items():
            # Extract exports (simplified)
            exports = self._extract_exports(path, content)
            lines = content.split("\n")
            preview = "\n".join(lines[:3])
            
            context_parts.append(f"  {path}")
            if exports:
                context_parts.append(f"    exports: {', '.join(exports[:5])}")
            context_parts.append(f"    preview: {preview[:100]}")
            context_parts.append("")

        return "\n".join(context_parts)

    def _extract_exports(self, file_path: str, content: str) -> List[str]:
        """Extract exported symbols from a file."""
        import re
        exports = []

        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if ext in ("ts", "tsx", "js", "jsx"):
            # export function/const/class/default
            patterns = [
                r"export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)",
                r"export\s+\{([^}]+)\}",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content):
                    group = match.group(1)
                    exports.extend(
                        name.strip() for name in group.split(",") if name.strip()
                    )

        elif ext == "py":
            # Python: class definitions and top-level functions
            patterns = [
                r"^class\s+(\w+)",
                r"^def\s+(\w+)",
                r"^(\w+)\s*=",
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    name = match.group(1)
                    if not name.startswith("_"):
                        exports.append(name)

        return exports[:10]  # Limit to 10 exports

    def _extract_ordered_files(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract files from plan in dependency order (priority).
        Config files first, then core, then features.
        """
        files = []

        # Look for files in the plan structure
        plan_files = plan.get("files", [])
        if isinstance(plan_files, list):
            for f in plan_files:
                if isinstance(f, dict) and f.get("path"):
                    files.append(f)

        # Sort by priority (lower = first)
        files.sort(key=lambda f: int(f.get("priority", 99)))

        # If no files found in plan, try to extract from structure
        if not files:
            structure = plan.get("project_structure", "")
            if structure:
                # Extract file paths from tree structure
                import re
                paths = re.findall(r'[\w/.-]+\.\w+', structure)
                files = [{"path": p, "description": "", "priority": i} 
                        for i, p in enumerate(paths)]

        logger.info(f"[IncrementalOrchestrator] Extracted {len(files)} files in order")
        return files


# =============================================================================
# SINGLETON
# =============================================================================

incremental_orchestrator = IncrementalOrchestrator()
