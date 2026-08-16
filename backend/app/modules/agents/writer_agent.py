"""
Writer Agent - Step-by-Step File Writing Agent (Bolt.new Architecture)

This agent processes ONE step at a time from the plan, writes files incrementally,
executes terminal commands, and provides real-time progress updates.

⚠️ ARCHITECTURE NOTE:
This class is currently NOT used by the Dynamic Orchestrator in production.
The Dynamic Orchestrator implements its own writer logic in:
  - DynamicOrchestrator._execute_writer() (loops through tasks)
  - DynamicOrchestrator._execute_writer_for_task() (executes single task)

This WriterAgent class is maintained for:
  1. Direct usage via Bolt Orchestrator (legacy workflow)
  2. Testing writer logic in isolation
  3. Future refactoring to consolidate writer implementations

For production bolt.new-style workflows, the Dynamic Orchestrator's embedded
writer logic is used as it supports real-time SSE streaming to the frontend.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import asyncio
import subprocess
import os

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.utils.response_parser import PlainTextParser
from app.modules.automation import file_manager


class WriterAgent(BaseAgent):
    """
    Writer Agent - Bolt.new Style Step-by-Step Execution

    Responsibilities:
    - Execute ONE step from the plan at a time
    - Parse <file> tags and write files to disk
    - Parse <terminal> tags and execute commands
    - Parse <explain> tags for UI updates
    - Mark steps as complete in real-time
    - Provide incremental progress updates

    Optimization:
    - Detects technology from file path and context
    - Loads only relevant prompt sections
    - Reduces API costs and improves response quality
    """

    # Prompt directory
    PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"

    # Technology detection keywords
    TECH_KEYWORDS = {
        "react": ["react", "vite", "tsx", "jsx", "frontend", "tailwind", "next.js", "nextjs"],
        "python": ["fastapi", "django", "flask", "python", "uvicorn", "sqlalchemy", ".py"],
        "java": ["spring", "java", "maven", "gradle", "spring boot", "springboot", ".java", "pom.xml"],
        "node": ["express", "node", "nestjs", "prisma"],
        "3d": ["three", "r3f", "@react-three", "fiber", "drei", "canvas", "webgl", "3d", "gsap", "useframe"],
    }

    @classmethod
    def _load_prompt_file(cls, filename: str) -> str:
        """Load a prompt file from the prompts directory"""
        filepath = cls.PROMPTS_DIR / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        logger.warning(f"[WriterAgent] Prompt file not found: {filepath}")
        return ""

    @classmethod
    def _detect_technologies(cls, file_path: str, context: str = "") -> List[str]:
        """Detect technologies from file path and context"""
        combined = (file_path + " " + context).lower()
        detected = []

        for tech, keywords in cls.TECH_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                detected.append(tech)

        # Default to react if nothing detected
        if not detected:
            detected = ["react"]

        logger.info(f"[WriterAgent] Detected technologies: {detected}")
        return detected

    @classmethod
    def _build_dynamic_prompt(cls, file_path: str = "", context: str = "") -> str:
        """Build prompt dynamically based on detected technologies"""
        # Always load core prompt
        core_prompt = cls._load_prompt_file("writer_core.txt")

        if not core_prompt:
            logger.warning("[WriterAgent] Core prompt not found! Using SYSTEM_PROMPT fallback.")
            return cls.SYSTEM_PROMPT  # Fall back to the hardcoded prompt

        # Detect technologies and load relevant prompts
        detected_techs = cls._detect_technologies(file_path, context)

        tech_prompts = []
        prompt_mapping = {
            "react": "writer_react.txt",
            "python": "writer_python.txt",
            "java": "writer_java.txt",
            "3d": "writer_3d.txt",
        }

        for tech in detected_techs:
            if tech in prompt_mapping:
                tech_prompt = cls._load_prompt_file(prompt_mapping[tech])
                if tech_prompt:
                    tech_prompts.append(f"\n{'='*60}\n{tech.upper()} SPECIFIC RULES:\n{'='*60}\n{tech_prompt}")

        # Combine prompts
        full_prompt = core_prompt
        if tech_prompts:
            full_prompt += "\n" + "\n".join(tech_prompts)

        # Add fullstack integration prompt when frontend + backend detected
        is_fullstack = ("react" in detected_techs and ("java" in detected_techs or "python" in detected_techs))
        if is_fullstack:
            fullstack_prompt = cls._load_prompt_file("writer_fullstack.txt")
            if fullstack_prompt:
                full_prompt += f"\n{'='*60}\nFULLSTACK INTEGRATION RULES:\n{'='*60}\n{fullstack_prompt}"
                logger.info("[WriterAgent] Added fullstack integration rules")

        # Log prompt size for debugging
        token_estimate = len(full_prompt) // 4
        logger.info(f"[WriterAgent] Dynamic prompt size: ~{token_estimate} tokens")

        return full_prompt

    # FALLBACK: Keep the original SYSTEM_PROMPT for backwards compatibility
    # FALLBACK: Lean system prompt (dynamic loading preferred via _build_dynamic_prompt)
    SYSTEM_PROMPT = """You are the WRITER AGENT - Code Generator for BharatBuild AI.

YOUR JOB: Generate ONE complete file at a time as instructed by the step.

RULES:
1. Output ONLY the file content wrapped in <file path="...">...</file> tags
2. NEVER truncate code - every file must be COMPLETE and runnable
3. Include ALL imports, types, error handling
4. Match the project's existing code style and tech stack
5. Use secure coding practices (parameterized queries, input validation, proper error handling)
6. MAX 300 lines per file - split if larger

OUTPUT FORMAT:
<file path="path/to/file.ext">
complete file content here
</file>

CRITICAL:
- Zero syntax errors
- All imports must be valid
- Handle edge cases
- Use TypeScript strict mode for .ts/.tsx files
- Include proper error boundaries in React components
- For Python: use type hints, async/await where appropriate
- For Java: use proper Spring Boot annotations, jakarta.* not javax.*
"""

    def __init__(self):
        super().__init__(
            name="Writer Agent",
            role="step_by_step_file_writer",
            capabilities=[
                "incremental_file_writing",
                "terminal_command_execution",
                "real_time_progress",
                "step_by_step_execution",
                "bolt_new_architecture"
            ],
            model="sonnet"  # Sonnet for better code quality
        )

    async def process(
        self,
        context: AgentContext,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a single step from the plan

        Args:
            context: Agent context with project info.
                Expected metadata keys:
                - step_number (int): Current step number (1-indexed)
                - step_data (Dict): Step information from plan
                - previous_context (Dict, optional): Context from previous steps

        Returns:
            Dict with execution results
        """
        # Backward compatibility: accept kwargs and populate metadata
        if kwargs:
            import warnings
            warnings.warn(
                "Passing step_number, step_data, previous_context as keyword arguments to "
                "WriterAgent.process() is deprecated. Pass them in context.metadata instead.",
                DeprecationWarning,
                stacklevel=2
            )
            for key in ("step_number", "step_data", "previous_context"):
                if key in kwargs and key not in (context.metadata or {}):
                    context.metadata[key] = kwargs[key]

        # Extract parameters from context.metadata
        step_number: int = context.metadata.get("step_number", 0)
        step_data: Dict[str, Any] = context.metadata.get("step_data", {})
        previous_context: Optional[Dict[str, Any]] = context.metadata.get("previous_context")

        try:
            logger.info(f"[Writer Agent] Executing Step {step_number}: {step_data.get('name', 'Unnamed Step')}")

            # Build prompt for this specific step
            step_prompt = self._build_step_prompt(
                step_number=step_number,
                step_data=step_data,
                previous_context=previous_context,
                context=context
            )

            # Build dynamic system prompt based on detected technology
            # Pass step_prompt for tech detection (contains file paths, descriptions)
            dynamic_system_prompt = self._build_dynamic_prompt(
                file_path=str(step_data.get("deliverables", [""])[0]) if step_data.get("deliverables") else "",
                context=step_prompt
            )

            # Call Claude with Bolt.new format
            # Use higher max_tokens to prevent file truncation
            response = await self._call_claude(
                system_prompt=dynamic_system_prompt,
                user_prompt=step_prompt,
                max_tokens=16384,  # Increased from 4096 to prevent truncation
                temperature=0.3  # Lower temperature for consistent code
            )

            # Parse Bolt.new response
            parsed = PlainTextParser.parse_bolt_response(response)

            # Execute the parsed actions
            execution_result = await self._execute_actions(
                parsed=parsed,
                project_id=context.project_id,
                step_number=step_number
            )

            logger.info(f"[Writer Agent] Step {step_number} completed successfully")

            return {
                "success": True,
                "agent": self.name,
                "step_number": step_number,
                "step_name": step_data.get("name"),
                "thinking": parsed.get("thinking"),
                "explanation": parsed.get("explain"),
                "files_created": execution_result["files_created"],
                "commands_executed": execution_result["commands_executed"],
                "errors": execution_result.get("errors", []),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Writer Agent] Step {step_number} failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "step_number": step_number,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_step_prompt(
        self,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for the current step"""

        prompt_parts = [
            f"CURRENT STEP: Step {step_number}",
            f"STEP NAME: {step_data.get('name', 'Unnamed Step')}",
            f"STEP DESCRIPTION: {step_data.get('description', 'No description')}",
            ""
        ]

        # Add tasks if available
        if "tasks" in step_data and step_data["tasks"]:
            prompt_parts.append("TASKS TO COMPLETE:")
            for i, task in enumerate(step_data["tasks"], 1):
                prompt_parts.append(f"{i}. {task}")
            prompt_parts.append("")

        # Add deliverables if available
        if "deliverables" in step_data and step_data["deliverables"]:
            prompt_parts.append("DELIVERABLES:")
            for deliverable in step_data["deliverables"]:
                prompt_parts.append(f"- {deliverable}")
            prompt_parts.append("")

        # Add context from previous steps
        if previous_context:
            prompt_parts.append("CONTEXT FROM PREVIOUS STEPS:")
            if "files_created" in previous_context:
                prompt_parts.append(f"Files created so far: {len(previous_context['files_created'])} files")
            if "last_explanation" in previous_context:
                prompt_parts.append(f"Previous step: {previous_context['last_explanation']}")
            prompt_parts.append("")

        # Add project metadata
        metadata = context.metadata or {}
        if "tech_stack" in metadata:
            prompt_parts.append(f"TECH STACK: {metadata['tech_stack']}")
        if "features" in metadata:
            prompt_parts.append(f"FEATURES: {', '.join(metadata.get('features', []))}")

        prompt_parts.append("")
        prompt_parts.append("TASK:")
        prompt_parts.append(f"Execute Step {step_number} completely. Generate files, commands, and explanations using Bolt.new XML tags.")
        prompt_parts.append("Focus ONLY on this step. Do not generate files for future steps.")
        prompt_parts.append("")
        prompt_parts.append("Output format: <thinking>, <explain>, <file>, <terminal> tags")

        return "\n".join(prompt_parts)

    async def _execute_actions(
        self,
        parsed: Dict[str, Any],
        project_id: str,
        step_number: int
    ) -> Dict[str, Any]:
        """
        Execute parsed actions from Bolt.new response

        Args:
            parsed: Parsed response with files, commands, etc.
            project_id: Project identifier
            step_number: Current step number

        Returns:
            Dict with execution results
        """
        result = {
            "files_created": [],
            "commands_executed": [],
            "errors": []
        }

        # 1. Write files
        if "files" in parsed and parsed["files"]:
            for file_info in parsed["files"]:
                try:
                    file_path = file_info.get("path")
                    content = file_info.get("content")

                    if not file_path or not content:
                        logger.warning(f"[Writer Agent] Skipping file with missing path or content")
                        continue

                    # FILE SIZE CHECK: Warn if file exceeds 300 lines (may cause truncation)
                    line_count = content.count('\n') + 1
                    if line_count > 300:
                        logger.warning(
                            f"[Writer Agent] ⚠️ LARGE FILE WARNING: {file_path} has {line_count} lines "
                            f"(exceeds 300 line limit). This may cause truncation issues!"
                        )
                        result["warnings"] = result.get("warnings", [])
                        result["warnings"].append(
                            f"File {file_path} has {line_count} lines - may cause build issues. "
                            f"Consider splitting into smaller files."
                        )

                    # TRUNCATION DETECTION: Check if file appears truncated
                    truncation_error = self._detect_truncation(file_path, content)
                    if truncation_error:
                        logger.error(
                            f"[Writer Agent] 🚨 TRUNCATED FILE DETECTED: {file_path} - {truncation_error}"
                        )
                        result["errors"].append(
                            f"File {file_path} appears truncated: {truncation_error}. "
                            f"The file has {line_count} lines - please regenerate with smaller components."
                        )
                        # Still write the file but mark as error so auto-fixer can handle it
                        result["truncated_files"] = result.get("truncated_files", [])
                        result["truncated_files"].append({
                            "path": file_path,
                            "line_count": line_count,
                            "error": truncation_error
                        })

                    # Write file using file_manager
                    write_result = await file_manager.create_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content
                    )

                    if write_result["success"]:
                        result["files_created"].append({
                            "path": file_path,
                            "size": len(content),
                            "step": step_number
                        })
                        logger.info(f"[Writer Agent] Created file: {file_path}")
                    else:
                        result["errors"].append(f"Failed to create {file_path}: {write_result.get('error')}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error writing file: {e}")
                    result["errors"].append(f"File write error: {str(e)}")

        # 1.5. VALIDATE: Ensure package.json has all required dependencies
        # This catches cases where AI adds plugins to tailwind.config.js but forgets package.json
        await self._validate_and_fix_dependencies(project_id, result["files_created"])

        # 2. Execute terminal commands
        if "terminal" in parsed:
            commands = parsed["terminal"]
            # Handle both single command (string) and multiple commands (list)
            if isinstance(commands, str):
                commands = [commands]

            for command in commands:
                try:
                    # Execute command safely
                    exec_result = await self._execute_terminal_command(
                        command=command,
                        project_id=project_id
                    )

                    result["commands_executed"].append({
                        "command": command,
                        "success": exec_result["success"],
                        "output": exec_result.get("output", ""),
                        "step": step_number
                    })

                    if not exec_result["success"]:
                        result["errors"].append(f"Command failed: {command}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error executing command: {e}")
                    result["errors"].append(f"Command error: {str(e)}")

        return result

    def _detect_truncation(self, file_path: str, content: str) -> Optional[str]:
        """
        Detect if a file appears to be truncated (incomplete).

        Returns error message if truncated, None if OK.
        """
        if not content or not content.strip():
            return "Empty file"

        # Get file extension
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''

        # Count brackets/braces
        if ext in ['tsx', 'ts', 'jsx', 'js', 'java', 'go', 'rs', 'c', 'cpp', 'cs']:
            open_braces = content.count('{')
            close_braces = content.count('}')
            open_parens = content.count('(')
            close_parens = content.count(')')
            open_brackets = content.count('[')
            close_brackets = content.count(']')

            # Check for significant imbalance (allowing for string literals)
            if open_braces > close_braces + 2:
                return f"Missing {open_braces - close_braces} closing braces '}}'"
            if open_parens > close_parens + 3:
                return f"Missing {open_parens - close_parens} closing parentheses ')'"
            if open_brackets > close_brackets + 2:
                return f"Missing {open_brackets - close_brackets} closing brackets ']'"

        # Check for TSX/JSX specific patterns
        if ext in ['tsx', 'jsx']:
            # Check for unclosed JSX tags (simplified check)
            if content.count('<') > content.count('>') + 5:
                return "Possible unclosed JSX tags"

            # Check if file ends mid-component (no closing export or return)
            lines = content.strip().split('\n')
            last_line = lines[-1].strip() if lines else ''

            # Suspicious endings for TSX/JSX
            suspicious_endings = [
                'className=',
                'onClick=',
                'onChange=',
                'value=',
                '<div',
                '<span',
                '<button',
                '<input',
                'return (',
                'return <',
            ]
            for ending in suspicious_endings:
                if last_line.startswith(ending) or last_line.endswith(ending):
                    return f"File ends with incomplete code: '{last_line[:50]}...'"

        # Check for Python
        if ext == 'py':
            # Check for incomplete function/class
            lines = content.strip().split('\n')
            last_line = lines[-1].strip() if lines else ''

            if last_line.endswith(':') and not last_line.startswith('#'):
                return f"File ends with incomplete block: '{last_line}'"

            # Check indentation suggests truncation
            if len(lines) > 10:
                last_lines = lines[-5:]
                if all(line.startswith('    ') or line.startswith('\t') for line in last_lines if line.strip()):
                    # All last lines are indented - might be truncated mid-function
                    if not any(keyword in last_line for keyword in ['return', 'pass', 'raise', 'break', 'continue']):
                        if last_line and not last_line.startswith('#'):
                            return "File may be truncated mid-function"

        # Check for Java
        if ext == 'java':
            # Must end with closing brace for class
            content_stripped = content.strip()
            if not content_stripped.endswith('}'):
                return "Java file must end with closing brace"

        # General check: file ends mid-line with obvious truncation
        if content and not content.endswith('\n'):
            last_line = content.split('\n')[-1]
            if len(last_line) > 100 and not any(last_line.rstrip().endswith(c) for c in [';', '}', ')', ']', ',', ':', '"', "'"]):
                return f"File appears cut off mid-line"

        return None

    async def _validate_and_fix_dependencies(
        self,
        project_id: str,
        files_created: List[Dict[str, Any]]
    ) -> None:
        """
        COMPREHENSIVE validation and auto-fix for ALL common AI code generation mistakes.

        Fixes:
        1. tsconfig.node.json - Create if tsconfig.json references it
        2. Tailwind plugins - ALL packages (not just @scoped)
        3. Python __init__.py - Create for all Python packages
        4. Path aliases - Ensure @/ is configured in tsconfig.json
        5. Missing dependencies - Add to package.json
        """
        import json
        import re
        from pathlib import Path

        # Known packages and their versions
        KNOWN_PACKAGES = {
            # Tailwind CSS plugins (scoped)
            '@tailwindcss/forms': '^0.5.7',
            '@tailwindcss/typography': '^0.5.10',
            '@tailwindcss/aspect-ratio': '^0.4.2',
            '@tailwindcss/container-queries': '^0.1.1',
            '@tailwindcss/line-clamp': '^0.4.4',
            # Tailwind CSS plugins (non-scoped) - CRITICAL: These were missing!
            'daisyui': '^4.6.0',
            'flowbite': '^2.3.0',
            'tailwindcss-animate': '^1.0.7',
            'tailwind-scrollbar': '^3.0.5',
            'tailwind-scrollbar-hide': '^1.1.7',
            # Common UI packages
            'clsx': '^2.1.0',
            'class-variance-authority': '^0.7.0',
            'tailwind-merge': '^2.2.0',
            'lucide-react': '^0.314.0',
            '@headlessui/react': '^1.7.18',
            '@radix-ui/react-dialog': '^1.0.5',
            '@radix-ui/react-dropdown-menu': '^2.0.6',
            '@radix-ui/react-slot': '^1.0.2',
            # Animation
            'framer-motion': '^11.0.3',
            # Forms
            'react-hook-form': '^7.50.0',
            '@hookform/resolvers': '^3.3.4',
            'zod': '^3.22.4',
            # State management
            'zustand': '^4.5.0',
            '@tanstack/react-query': '^5.17.19',
            # Utilities
            'date-fns': '^3.3.1',
            'lodash': '^4.17.21',
            'axios': '^1.6.7',
            # Icons - CRITICAL: Commonly used but often missing!
            'react-icons': '^5.0.1',
            '@heroicons/react': '^2.1.1',
            # Charts - CRITICAL: LLMs often use these
            'recharts': '^2.12.0',
            'chart.js': '^4.4.1',
            'react-chartjs-2': '^5.2.0',
            # Routing - CRITICAL: Almost every React app needs this
            'react-router-dom': '^6.22.0',
            # Notifications/Toasts
            'react-toastify': '^10.0.4',
            'sonner': '^1.4.0',
            'react-hot-toast': '^2.4.1',
            # Tables and Data
            '@tanstack/react-table': '^8.11.0',
            # File handling
            'react-dropzone': '^14.2.3',
            # Form inputs
            'react-select': '^5.8.0',
            # Date pickers
            'react-datepicker': '^6.1.0',
            '@types/react-datepicker': '^4.19.0',
        }

        try:
            # Get project path
            project_path = await file_manager.get_project_path(project_id)
            if not project_path:
                return

            fixes_applied = []

            # ================================================================
            # FIX 1: tsconfig.node.json - Create if referenced but missing
            # ================================================================
            await self._fix_tsconfig_references(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 2: Tailwind plugins - Add ALL missing packages to package.json
            # ================================================================
            await self._fix_tailwind_dependencies(project_id, project_path, KNOWN_PACKAGES, fixes_applied)

            # ================================================================
            # FIX 3: Python __init__.py - Create for all Python packages
            # ================================================================
            await self._fix_python_init_files(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 4: Path aliases - Ensure @/ is configured in tsconfig.json
            # ================================================================
            await self._fix_path_aliases(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 5: Next.js route files - Add NextRequest/NextResponse imports
            # ================================================================
            await self._fix_nextjs_routes(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 6: Vite config - Ensure vite.config.ts exists for Vite projects
            # ================================================================
            await self._fix_vite_config(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 7: Index.html - Ensure entry point exists for Vite
            # ================================================================
            await self._fix_index_html(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 11: Python requirements.txt - Add missing packages
            # ================================================================
            await self._fix_python_requirements(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 12: Java pom.xml - Add missing dependencies
            # ================================================================
            await self._fix_java_dependencies(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 13: Go go.mod - Add missing dependencies
            # ================================================================
            await self._fix_go_dependencies(project_id, project_path, fixes_applied)

            # ================================================================
            # FIX 14: Next.js config - Create next.config.js and globals.css
            # ================================================================
            await self._fix_nextjs_config(project_id, project_path, fixes_applied)

            if fixes_applied:
                logger.info(f"[Writer Agent] Applied {len(fixes_applied)} auto-fixes: {fixes_applied}")

        except Exception as e:
            logger.warning(f"[Writer Agent] Dependency validation failed (non-fatal): {e}")

    async def _fix_tsconfig_references(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 1: Create tsconfig.node.json if tsconfig.json references it"""
        import json

        tsconfig_path = project_path / "tsconfig.json"
        if not tsconfig_path.exists():
            return

        try:
            content = tsconfig_path.read_text(encoding='utf-8')
            tsconfig_data = json.loads(content)

            # Check for references
            references = tsconfig_data.get("references", [])
            for ref in references:
                ref_path = ref.get("path", "")
                if "tsconfig.node.json" in ref_path:
                    node_config_path = project_path / "tsconfig.node.json"
                    if not node_config_path.exists():
                        # Create tsconfig.node.json
                        node_config = {
                            "compilerOptions": {
                                "composite": True,
                                "skipLibCheck": True,
                                "module": "ESNext",
                                "moduleResolution": "bundler",
                                "allowSyntheticDefaultImports": True,
                                "strict": True,
                                "noEmit": True
                            },
                            "include": ["vite.config.ts", "vite.config.js"]
                        }
                        node_config_content = json.dumps(node_config, indent=2) + "\n"
                        node_config_path.write_text(node_config_content, encoding='utf-8')

                        await file_manager.create_file(
                            project_id=project_id,
                            file_path="tsconfig.node.json",
                            content=node_config_content
                        )
                        fixes_applied.append("tsconfig.node.json")
                        logger.info(f"[Writer Agent] Created missing tsconfig.node.json")

                elif "tsconfig.app.json" in ref_path:
                    app_config_path = project_path / "tsconfig.app.json"
                    if not app_config_path.exists():
                        # Create tsconfig.app.json
                        app_config = {
                            "compilerOptions": {
                                "composite": True,
                                "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
                                "target": "ES2020",
                                "useDefineForClassFields": True,
                                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                                "module": "ESNext",
                                "skipLibCheck": True,
                                "moduleResolution": "bundler",
                                "allowImportingTsExtensions": True,
                                "resolveJsonModule": True,
                                "isolatedModules": True,
                                "moduleDetection": "force",
                                "noEmit": True,
                                "jsx": "react-jsx",
                                "strict": True,
                                "noUnusedLocals": True,
                                "noUnusedParameters": True,
                                "noFallthroughCasesInSwitch": True
                            },
                            "include": ["src"]
                        }
                        app_config_content = json.dumps(app_config, indent=2) + "\n"
                        app_config_path.write_text(app_config_content, encoding='utf-8')

                        await file_manager.create_file(
                            project_id=project_id,
                            file_path="tsconfig.app.json",
                            content=app_config_content
                        )
                        fixes_applied.append("tsconfig.app.json")
                        logger.info(f"[Writer Agent] Created missing tsconfig.app.json")

        except Exception as e:
            logger.warning(f"[Writer Agent] tsconfig reference fix failed: {e}")

    async def _fix_tailwind_dependencies(
        self,
        project_id: str,
        project_path: Path,
        known_packages: Dict[str, str],
        fixes_applied: List[str]
    ) -> None:
        """Fix 2: Add ALL missing Tailwind plugin packages to package.json"""
        import json
        import re

        tailwind_config_path = project_path / "tailwind.config.js"
        package_json_path = project_path / "package.json"

        if not tailwind_config_path.exists() or not package_json_path.exists():
            return

        try:
            tailwind_content = tailwind_config_path.read_text(encoding='utf-8')

            # FIXED: Match ALL require() calls, not just @scoped packages
            # This catches: require('@tailwindcss/forms'), require('daisyui'), etc.
            require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]"
            required_packages = set(re.findall(require_pattern, tailwind_content))

            # Filter out relative paths like './myPlugin'
            required_packages = {p for p in required_packages if not p.startswith('.')}

            if not required_packages:
                return

            logger.info(f"[Writer Agent] Found required packages in tailwind.config.js: {required_packages}")

            # Read package.json
            package_content = package_json_path.read_text(encoding='utf-8')
            package_data = json.loads(package_content)

            # Get all existing dependencies
            all_deps = set()
            for dep_key in ['dependencies', 'devDependencies', 'peerDependencies']:
                if dep_key in package_data:
                    all_deps.update(package_data[dep_key].keys())

            # Find missing packages
            missing_packages = required_packages - all_deps

            if not missing_packages:
                return

            logger.warning(f"[Writer Agent] FIXING: Missing packages in package.json: {missing_packages}")

            # Add missing packages to devDependencies
            if 'devDependencies' not in package_data:
                package_data['devDependencies'] = {}

            for pkg in missing_packages:
                version = known_packages.get(pkg, 'latest')
                package_data['devDependencies'][pkg] = version
                logger.info(f"[Writer Agent] Added {pkg}@{version} to devDependencies")

            # Sort devDependencies
            package_data['devDependencies'] = dict(sorted(package_data['devDependencies'].items()))

            # Write back
            new_content = json.dumps(package_data, indent=2) + "\n"
            package_json_path.write_text(new_content, encoding='utf-8')

            await file_manager.create_file(
                project_id=project_id,
                file_path="package.json",
                content=new_content
            )

            fixes_applied.append(f"package.json (+{len(missing_packages)} deps)")
            logger.info(f"[Writer Agent] Fixed package.json - added {len(missing_packages)} missing packages")

        except Exception as e:
            logger.warning(f"[Writer Agent] Tailwind dependency fix failed: {e}")

    async def _fix_python_init_files(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 3: Create __init__.py for all Python packages"""
        import os

        # Check if this is a Python project
        has_python = any([
            (project_path / "requirements.txt").exists(),
            (project_path / "pyproject.toml").exists(),
            (project_path / "setup.py").exists(),
            (project_path / "main.py").exists(),
            (project_path / "app").is_dir(),
        ])

        if not has_python:
            return

        try:
            init_files_created = []

            # Walk through all directories
            for root, dirs, files in os.walk(project_path):
                root_path = Path(root)

                # Skip non-Python directories
                if any(skip in str(root_path) for skip in ['node_modules', '.git', '__pycache__', 'venv', '.venv']):
                    continue

                # Check if this directory has .py files
                has_py_files = any(f.endswith('.py') and f != '__init__.py' for f in files)

                if has_py_files:
                    init_path = root_path / "__init__.py"
                    if not init_path.exists():
                        # Create __init__.py
                        init_path.write_text("", encoding='utf-8')

                        rel_path = init_path.relative_to(project_path)
                        await file_manager.create_file(
                            project_id=project_id,
                            file_path=str(rel_path),
                            content=""
                        )
                        init_files_created.append(str(rel_path))

            if init_files_created:
                fixes_applied.append(f"__init__.py ({len(init_files_created)} files)")
                logger.info(f"[Writer Agent] Created {len(init_files_created)} missing __init__.py files")

        except Exception as e:
            logger.warning(f"[Writer Agent] Python __init__.py fix failed: {e}")

    async def _fix_python_requirements(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 11: Scan Python imports and add missing packages to requirements.txt"""
        import re

        # Check if this is a Python project
        requirements_path = project_path / "requirements.txt"
        if not requirements_path.exists():
            return

        # Known Python packages and their pip names
        PYTHON_PACKAGES = {
            # Web frameworks
            'fastapi': 'fastapi',
            'flask': 'Flask',
            'django': 'Django',
            'uvicorn': 'uvicorn',
            'gunicorn': 'gunicorn',
            # Database
            'sqlalchemy': 'SQLAlchemy',
            'databases': 'databases',
            'asyncpg': 'asyncpg',
            'psycopg2': 'psycopg2-binary',
            'pymongo': 'pymongo',
            'redis': 'redis',
            # Auth & Security
            'passlib': 'passlib[bcrypt]',
            'python_jose': 'python-jose[cryptography]',
            'jose': 'python-jose[cryptography]',
            'bcrypt': 'bcrypt',
            # HTTP & APIs
            'httpx': 'httpx',
            'aiohttp': 'aiohttp',
            'requests': 'requests',
            # Validation
            'pydantic': 'pydantic',
            'pydantic_settings': 'pydantic-settings',
            # Utils
            'dotenv': 'python-dotenv',
            'python_multipart': 'python-multipart',
            'jinja2': 'Jinja2',
            'boto3': 'boto3',
            'pillow': 'Pillow',
            'PIL': 'Pillow',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'celery': 'celery',
            # Testing
            'pytest': 'pytest',
            'pytest_asyncio': 'pytest-asyncio',
        }

        try:
            # Read existing requirements
            existing_reqs = requirements_path.read_text(encoding='utf-8').lower()

            # Scan all Python files for imports
            imports_found = set()
            for py_file in project_path.rglob("*.py"):
                if 'venv' in str(py_file) or 'site-packages' in str(py_file):
                    continue
                try:
                    content = py_file.read_text(encoding='utf-8')
                    # Find imports
                    for match in re.finditer(r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)', content, re.MULTILINE):
                        imports_found.add(match.group(1).lower())
                except:
                    continue

            # Find missing packages
            missing_packages = []
            for imp in imports_found:
                if imp in PYTHON_PACKAGES:
                    pip_name = PYTHON_PACKAGES[imp]
                    # Check if already in requirements (case-insensitive)
                    if pip_name.lower().split('[')[0] not in existing_reqs:
                        missing_packages.append(pip_name)

            if missing_packages:
                # Add missing packages to requirements.txt
                current_content = requirements_path.read_text(encoding='utf-8')
                new_content = current_content.rstrip() + '\n'
                new_content += '\n# Auto-added by Writer Agent\n'
                for pkg in missing_packages:
                    new_content += f'{pkg}\n'

                requirements_path.write_text(new_content, encoding='utf-8')

                await file_manager.create_file(
                    project_id=project_id,
                    file_path="requirements.txt",
                    content=new_content
                )

                fixes_applied.append(f"requirements.txt (+{len(missing_packages)} packages)")
                logger.info(f"[Writer Agent] Added {len(missing_packages)} missing packages to requirements.txt: {missing_packages}")

        except Exception as e:
            logger.warning(f"[Writer Agent] Python requirements fix failed: {e}")

    async def _fix_java_dependencies(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 12: Check Java pom.xml for missing dependencies"""
        import re

        pom_path = project_path / "pom.xml"
        if not pom_path.exists():
            return

        # Known Java/Spring dependencies (NO LOMBOK - it breaks builds)
        JAVA_PACKAGES = {
            # 'lombok' removed - we never want to add Lombok
            'jakarta.validation': '<dependency>\n            <groupId>org.springframework.boot</groupId>\n            <artifactId>spring-boot-starter-validation</artifactId>\n        </dependency>',
            'springframework.web': '<dependency>\n            <groupId>org.springframework.boot</groupId>\n            <artifactId>spring-boot-starter-web</artifactId>\n        </dependency>',
            'springframework.data.jpa': '<dependency>\n            <groupId>org.springframework.boot</groupId>\n            <artifactId>spring-boot-starter-data-jpa</artifactId>\n        </dependency>',
            'springframework.security': '<dependency>\n            <groupId>org.springframework.boot</groupId>\n            <artifactId>spring-boot-starter-security</artifactId>\n        </dependency>',
        }

        try:
            pom_content = pom_path.read_text(encoding='utf-8')

            # Scan Java files for imports
            imports_found = set()
            for java_file in project_path.rglob("*.java"):
                try:
                    content = java_file.read_text(encoding='utf-8')
                    for match in re.finditer(r'^import\s+([\w.]+);', content, re.MULTILINE):
                        imports_found.add(match.group(1))
                except:
                    continue

            # Check for missing dependencies
            missing_deps = []
            for imp in imports_found:
                for pkg_key, dep_xml in JAVA_PACKAGES.items():
                    if pkg_key in imp and dep_xml not in pom_content:
                        if dep_xml not in missing_deps:
                            missing_deps.append(dep_xml)

            if missing_deps:
                # Add before </dependencies>
                if '</dependencies>' in pom_content:
                    insert_point = pom_content.find('</dependencies>')
                    new_deps = '\n        '.join(missing_deps)
                    new_content = pom_content[:insert_point] + '\n        ' + new_deps + '\n    ' + pom_content[insert_point:]

                    pom_path.write_text(new_content, encoding='utf-8')

                    await file_manager.create_file(
                        project_id=project_id,
                        file_path="pom.xml",
                        content=new_content
                    )

                    fixes_applied.append(f"pom.xml (+{len(missing_deps)} dependencies)")
                    logger.info(f"[Writer Agent] Added {len(missing_deps)} missing dependencies to pom.xml")

        except Exception as e:
            logger.warning(f"[Writer Agent] Java dependencies fix failed: {e}")

    async def _fix_go_dependencies(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 13: Check Go go.mod for missing dependencies"""
        import re

        go_mod_path = project_path / "go.mod"
        if not go_mod_path.exists():
            return

        # Known Go packages
        GO_PACKAGES = {
            'gin-gonic/gin': 'github.com/gin-gonic/gin v1.9.1',
            'gorilla/mux': 'github.com/gorilla/mux v1.8.1',
            'gorm.io/gorm': 'gorm.io/gorm v1.25.5',
            'gorm.io/driver/postgres': 'gorm.io/driver/postgres v1.5.4',
            'gorm.io/driver/mysql': 'gorm.io/driver/mysql v1.5.2',
            'godotenv': 'github.com/joho/godotenv v1.5.1',
            'jwt-go': 'github.com/golang-jwt/jwt/v5 v5.2.0',
            'uuid': 'github.com/google/uuid v1.5.0',
            'validator': 'github.com/go-playground/validator/v10 v10.16.0',
            'cors': 'github.com/rs/cors v1.10.1',
        }

        try:
            go_mod_content = go_mod_path.read_text(encoding='utf-8')

            # Scan Go files for imports
            imports_found = set()
            for go_file in project_path.rglob("*.go"):
                try:
                    content = go_file.read_text(encoding='utf-8')
                    for match in re.finditer(r'"(github\.com/[^"]+|gorm\.io/[^"]+)"', content):
                        imports_found.add(match.group(1))
                except:
                    continue

            # Check for missing dependencies
            missing_deps = []
            for imp in imports_found:
                for pkg_key, dep_line in GO_PACKAGES.items():
                    if pkg_key in imp and dep_line.split()[0] not in go_mod_content:
                        if dep_line not in missing_deps:
                            missing_deps.append(dep_line)

            if missing_deps:
                # Add after require (
                if 'require (' in go_mod_content:
                    insert_point = go_mod_content.find('require (') + len('require (')
                    new_deps = '\n\t'.join(missing_deps)
                    new_content = go_mod_content[:insert_point] + '\n\t' + new_deps + go_mod_content[insert_point:]

                    go_mod_path.write_text(new_content, encoding='utf-8')

                    await file_manager.create_file(
                        project_id=project_id,
                        file_path="go.mod",
                        content=new_content
                    )

                    fixes_applied.append(f"go.mod (+{len(missing_deps)} dependencies)")
                    logger.info(f"[Writer Agent] Added {len(missing_deps)} missing dependencies to go.mod")

        except Exception as e:
            logger.warning(f"[Writer Agent] Go dependencies fix failed: {e}")

    async def _fix_nextjs_config(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 14: Ensure Next.js projects have proper configuration"""

        # Check if this is a Next.js project
        package_json = project_path / "package.json"
        if not package_json.exists():
            return

        try:
            import json
            pkg_content = package_json.read_text(encoding='utf-8')
            pkg_data = json.loads(pkg_content)

            all_deps = {}
            for key in ['dependencies', 'devDependencies']:
                if key in pkg_data:
                    all_deps.update(pkg_data[key])

            if 'next' not in all_deps:
                return

            # Check for next.config.js/mjs
            next_config_js = project_path / "next.config.js"
            next_config_mjs = project_path / "next.config.mjs"
            next_config_ts = project_path / "next.config.ts"

            if not any([next_config_js.exists(), next_config_mjs.exists(), next_config_ts.exists()]):
                # Create next.config.js
                config_content = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
}

module.exports = nextConfig
"""
                next_config_js.write_text(config_content, encoding='utf-8')

                await file_manager.create_file(
                    project_id=project_id,
                    file_path="next.config.js",
                    content=config_content
                )

                fixes_applied.append("next.config.js")
                logger.info(f"[Writer Agent] Created missing next.config.js")

            # Check for globals.css in app directory
            app_dir = project_path / "app"
            if app_dir.exists():
                globals_css = app_dir / "globals.css"
                if not globals_css.exists():
                    # Check for tailwind
                    if 'tailwindcss' in all_deps:
                        css_content = """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-rgb: 255, 255, 255;
}

body {
  color: rgb(var(--foreground-rgb));
  background: rgb(var(--background-rgb));
}
"""
                        globals_css.write_text(css_content, encoding='utf-8')

                        await file_manager.create_file(
                            project_id=project_id,
                            file_path="app/globals.css",
                            content=css_content
                        )

                        fixes_applied.append("app/globals.css")
                        logger.info(f"[Writer Agent] Created missing app/globals.css with Tailwind")

        except Exception as e:
            logger.warning(f"[Writer Agent] Next.js config fix failed: {e}")

    async def _fix_path_aliases(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 4: Ensure @/ path alias is configured in tsconfig.json"""
        import json
        import re

        # Check if any file uses @/ imports
        uses_alias = False
        for ext in ['*.tsx', '*.ts', '*.jsx', '*.js']:
            for file_path in project_path.rglob(ext):
                if 'node_modules' in str(file_path):
                    continue
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if re.search(r"from\s+['\"]@/", content) or re.search(r"import\s+['\"]@/", content):
                        uses_alias = True
                        break
                except:
                    continue
            if uses_alias:
                break

        if not uses_alias:
            return

        tsconfig_path = project_path / "tsconfig.json"
        if not tsconfig_path.exists():
            return

        try:
            content = tsconfig_path.read_text(encoding='utf-8')
            tsconfig_data = json.loads(content)

            compiler_options = tsconfig_data.get("compilerOptions", {})

            # Check if paths is already configured
            if "paths" in compiler_options and "@/*" in compiler_options["paths"]:
                return

            # Add path alias configuration
            if "compilerOptions" not in tsconfig_data:
                tsconfig_data["compilerOptions"] = {}

            tsconfig_data["compilerOptions"]["baseUrl"] = "."
            tsconfig_data["compilerOptions"]["paths"] = {
                "@/*": ["./src/*"]
            }

            new_content = json.dumps(tsconfig_data, indent=2) + "\n"
            tsconfig_path.write_text(new_content, encoding='utf-8')

            await file_manager.create_file(
                project_id=project_id,
                file_path="tsconfig.json",
                content=new_content
            )

            fixes_applied.append("tsconfig.json (@/ alias)")
            logger.info(f"[Writer Agent] Added @/ path alias to tsconfig.json")

        except Exception as e:
            logger.warning(f"[Writer Agent] Path alias fix failed: {e}")

    async def _fix_nextjs_routes(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 5: Add NextRequest/NextResponse imports to Next.js route files"""
        import re

        # Check if this is a Next.js project
        app_dir = project_path / "app"
        if not app_dir.exists():
            return

        try:
            fixed_files = []

            # Find all route.ts files
            for route_file in app_dir.rglob("route.ts"):
                content = route_file.read_text(encoding='utf-8')

                # Check if file has GET/POST/PUT/DELETE exports
                has_route_handlers = bool(re.search(r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)', content))

                if not has_route_handlers:
                    continue

                # Check if NextRequest/NextResponse are imported
                has_next_imports = 'NextRequest' in content or 'NextResponse' in content
                has_import_statement = bool(re.search(r"from\s+['\"]next/server['\"]", content))

                if not has_import_statement and has_route_handlers:
                    # Add import at the top
                    import_line = "import { NextRequest, NextResponse } from 'next/server';\n"

                    # Check if there's a 'use server' directive
                    if content.startswith("'use server'") or content.startswith('"use server"'):
                        # Insert after directive
                        lines = content.split('\n', 1)
                        new_content = lines[0] + '\n' + import_line + (lines[1] if len(lines) > 1 else '')
                    else:
                        new_content = import_line + content

                    route_file.write_text(new_content, encoding='utf-8')

                    rel_path = route_file.relative_to(project_path)
                    await file_manager.create_file(
                        project_id=project_id,
                        file_path=str(rel_path),
                        content=new_content
                    )
                    fixed_files.append(str(rel_path))

            if fixed_files:
                fixes_applied.append(f"Next.js routes ({len(fixed_files)} files)")
                logger.info(f"[Writer Agent] Added NextRequest/NextResponse imports to {len(fixed_files)} route files")

        except Exception as e:
            logger.warning(f"[Writer Agent] Next.js route fix failed: {e}")

    async def _fix_vite_config(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 6: Ensure vite.config.ts exists for Vite projects"""

        # Check if this is a Vite project (has vite in package.json)
        package_json_path = project_path / "package.json"
        if not package_json_path.exists():
            return

        try:
            import json
            package_content = package_json_path.read_text(encoding='utf-8')
            package_data = json.loads(package_content)

            # Check if vite is a dependency
            all_deps = {}
            for dep_key in ['dependencies', 'devDependencies']:
                if dep_key in package_data:
                    all_deps.update(package_data[dep_key])

            if 'vite' not in all_deps:
                return

            # Check if vite.config exists
            vite_config_ts = project_path / "vite.config.ts"
            vite_config_js = project_path / "vite.config.js"

            if vite_config_ts.exists() or vite_config_js.exists():
                return

            # Determine if React or Vue
            is_react = '@vitejs/plugin-react' in all_deps or 'react' in all_deps
            is_vue = '@vitejs/plugin-vue' in all_deps or 'vue' in all_deps

            if is_react:
                vite_config = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',  // CRITICAL: Required for path-based preview URLs
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
})
'''
            elif is_vue:
                vite_config = '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: './',  // CRITICAL: Required for path-based preview URLs
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
})
'''
            else:
                vite_config = '''import { defineConfig } from 'vite'

export default defineConfig({
  base: './',  // CRITICAL: Required for path-based preview URLs
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
})
'''

            vite_config_ts.write_text(vite_config, encoding='utf-8')

            await file_manager.create_file(
                project_id=project_id,
                file_path="vite.config.ts",
                content=vite_config
            )

            fixes_applied.append("vite.config.ts")
            logger.info(f"[Writer Agent] Created missing vite.config.ts")

        except Exception as e:
            logger.warning(f"[Writer Agent] Vite config fix failed: {e}")

    async def _fix_index_html(
        self,
        project_id: str,
        project_path: Path,
        fixes_applied: List[str]
    ) -> None:
        """Fix 7: Ensure index.html exists for Vite projects"""

        # Check if this is a Vite project
        vite_config_ts = project_path / "vite.config.ts"
        vite_config_js = project_path / "vite.config.js"

        if not (vite_config_ts.exists() or vite_config_js.exists()):
            return

        index_html_path = project_path / "index.html"
        if index_html_path.exists():
            return

        try:
            # Check what entry point exists
            main_tsx = project_path / "src" / "main.tsx"
            main_ts = project_path / "src" / "main.ts"
            main_jsx = project_path / "src" / "main.jsx"
            main_js = project_path / "src" / "main.js"

            if main_tsx.exists():
                entry = "/src/main.tsx"
            elif main_ts.exists():
                entry = "/src/main.ts"
            elif main_jsx.exists():
                entry = "/src/main.jsx"
            elif main_js.exists():
                entry = "/src/main.js"
            else:
                entry = "/src/main.tsx"  # Default

            index_html = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="{entry}"></script>
  </body>
</html>
'''

            index_html_path.write_text(index_html, encoding='utf-8')

            await file_manager.create_file(
                project_id=project_id,
                file_path="index.html",
                content=index_html
            )

            fixes_applied.append("index.html")
            logger.info(f"[Writer Agent] Created missing index.html")

        except Exception as e:
            logger.warning(f"[Writer Agent] index.html fix failed: {e}")

        # =====================================================================
        # Fix 8: Create postcss.config.js for Tailwind projects
        # =====================================================================
        try:
            tailwind_config = project_path / "tailwind.config.js"
            tailwind_config_ts = project_path / "tailwind.config.ts"
            postcss_config = project_path / "postcss.config.js"
            postcss_config_cjs = project_path / "postcss.config.cjs"
            postcss_config_mjs = project_path / "postcss.config.mjs"

            has_tailwind = tailwind_config.exists() or tailwind_config_ts.exists()
            has_postcss = postcss_config.exists() or postcss_config_cjs.exists() or postcss_config_mjs.exists()

            if has_tailwind and not has_postcss:
                logger.info(f"[Writer Agent] Creating missing postcss.config.js for Tailwind project")

                postcss_content = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""
                # Write file
                postcss_config.write_text(postcss_content, encoding='utf-8')

                if file_manager:
                    await file_manager.create_file(
                        project_id=project_id,
                        file_path="postcss.config.js",
                        content=postcss_content
                    )

                fixes_applied.append("postcss.config.js")
                logger.info(f"[Writer Agent] Created missing postcss.config.js")

        except Exception as e:
            logger.warning(f"[Writer Agent] postcss.config.js fix failed: {e}")

        # =====================================================================
        # Fix 9: Create index.css with @tailwind directives for Tailwind projects
        # =====================================================================
        try:
            tailwind_config = project_path / "tailwind.config.js"
            tailwind_config_ts = project_path / "tailwind.config.ts"

            has_tailwind = tailwind_config.exists() or tailwind_config_ts.exists()

            if has_tailwind:
                # Check for index.css in various locations
                src_dir = project_path / "src"
                index_css = src_dir / "index.css"
                globals_css = src_dir / "globals.css"
                styles_css = src_dir / "styles.css"
                app_css = src_dir / "App.css"

                # Check if any CSS file with @tailwind exists
                has_tailwind_css = False
                for css_file in [index_css, globals_css, styles_css, app_css]:
                    if css_file.exists():
                        content = css_file.read_text(encoding='utf-8')
                        if '@tailwind' in content:
                            has_tailwind_css = True
                            break

                if not has_tailwind_css:
                    # Create src directory if it doesn't exist
                    src_dir.mkdir(parents=True, exist_ok=True)

                    logger.info(f"[Writer Agent] Creating index.css with @tailwind directives")

                    css_content = """@tailwind base;
@tailwind components;
@tailwind utilities;

/* Global styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
"""
                    index_css.write_text(css_content, encoding='utf-8')

                    if file_manager:
                        await file_manager.create_file(
                            project_id=project_id,
                            file_path="src/index.css",
                            content=css_content
                        )

                    fixes_applied.append("src/index.css")
                    logger.info(f"[Writer Agent] Created index.css with @tailwind directives")

        except Exception as e:
            logger.warning(f"[Writer Agent] index.css fix failed: {e}")

        # =====================================================================
        # Fix 10: Ensure main.tsx imports index.css for Tailwind to work
        # =====================================================================
        try:
            src_dir = project_path / "src"
            main_tsx = src_dir / "main.tsx"
            main_ts = src_dir / "main.ts"
            main_jsx = src_dir / "main.jsx"
            main_js = src_dir / "main.js"

            # Find the main entry file
            main_file = None
            for mf in [main_tsx, main_ts, main_jsx, main_js]:
                if mf.exists():
                    main_file = mf
                    break

            if main_file:
                content = main_file.read_text(encoding='utf-8')

                # Check if CSS is imported
                has_css_import = any(imp in content for imp in [
                    "import './index.css'",
                    'import "./index.css"',
                    "import './globals.css'",
                    'import "./globals.css"',
                    "import './styles.css'",
                    'import "./styles.css"',
                    "import './App.css'",
                    'import "./App.css"',
                ])

                if not has_css_import:
                    # Check if index.css exists
                    index_css = src_dir / "index.css"
                    if index_css.exists():
                        logger.info(f"[Writer Agent] Adding CSS import to {main_file.name}")

                        # Add import after first line (typically 'use client' or import)
                        lines = content.split('\n')
                        insert_index = 0

                        # Find good position to insert (after 'use client' or first imports)
                        for i, line in enumerate(lines):
                            if line.strip().startswith("import ") or line.strip() == "'use client'" or line.strip() == '"use client"':
                                insert_index = i + 1
                                break

                        # Insert CSS import
                        lines.insert(insert_index, "import './index.css'")
                        new_content = '\n'.join(lines)

                        main_file.write_text(new_content, encoding='utf-8')

                        if file_manager:
                            relative_path = str(main_file.relative_to(project_path))
                            await file_manager.update_file(
                                project_id=project_id,
                                file_path=relative_path,
                                content=new_content
                            )

                        fixes_applied.append(f"{main_file.name} CSS import")
                        logger.info(f"[Writer Agent] Added CSS import to {main_file.name}")

        except Exception as e:
            logger.warning(f"[Writer Agent] main.tsx CSS import fix failed: {e}")

    async def _execute_terminal_command(
        self,
        command: str,
        project_id: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute a terminal command safely

        Args:
            command: Command to execute
            project_id: Project identifier
            timeout: Command timeout in seconds

        Returns:
            Dict with execution result
        """
        try:
            logger.info(f"[Writer Agent] Executing command: {command}")

            # Get project directory
            project_dir = os.path.join("generated", project_id)

            # Security: Validate command is safe
            dangerous_commands = ["rm -rf", "sudo", "chmod 777", "dd if=", "> /dev/"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                logger.warning(f"[Writer Agent] Blocked dangerous command: {command}")
                return {
                    "success": False,
                    "error": "Command blocked for security reasons"
                }

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "output": stdout.decode() if stdout else "",
                    "error": stderr.decode() if stderr else ""
                }

            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s"
                }

        except Exception as e:
            logger.error(f"[Writer Agent] Command execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_plan_steps(
        self,
        context: AgentContext,
        plan: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute all steps from a plan sequentially

        Args:
            context: Agent context
            plan: Complete plan with steps
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with all execution results
        """
        results = {
            "steps_completed": [],
            "total_files_created": 0,
            "total_commands_executed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat()
        }

        # Extract steps from plan
        steps = self._extract_steps_from_plan(plan)
        total_steps = len(steps)

        logger.info(f"[Writer Agent] Starting execution of {total_steps} steps")

        previous_context = None

        for i, step_data in enumerate(steps, 1):
            # Update progress
            if progress_callback:
                progress_percent = int((i / total_steps) * 100)
                await progress_callback(
                    progress_percent,
                    f"Step {i}/{total_steps}: {step_data.get('name', 'Processing...')}"
                )

            # Execute step
            step_result = await self.process(
                context=context,
                step_number=i,
                step_data=step_data,
                previous_context=previous_context
            )

            results["steps_completed"].append(step_result)

            if step_result["success"]:
                results["total_files_created"] += len(step_result.get("files_created", []))
                results["total_commands_executed"] += len(step_result.get("commands_executed", []))

                # Update context for next step
                previous_context = {
                    "files_created": step_result.get("files_created", []),
                    "last_explanation": step_result.get("explanation")
                }
            else:
                results["errors"].append(f"Step {i} failed: {step_result.get('error')}")
                # Continue with next step even if current fails
                logger.warning(f"[Writer Agent] Step {i} failed, continuing with next step")

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"[Writer Agent] Completed all steps. Files: {results['total_files_created']}, Commands: {results['total_commands_executed']}")

        return results

    def _extract_steps_from_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract steps from plan structure"""
        steps = []

        # Check for implementation_steps or phases
        if "implementation_steps" in plan:
            for phase_key, phase_data in plan["implementation_steps"].items():
                if isinstance(phase_data, dict):
                    steps.append({
                        "name": phase_data.get("name", phase_key),
                        "description": phase_data.get("description", ""),
                        "tasks": phase_data.get("tasks", []),
                        "deliverables": phase_data.get("deliverables", []),
                        "duration": phase_data.get("duration", "")
                    })

        # Fallback: if no steps found, create a single step
        if not steps:
            steps.append({
                "name": "Project Implementation",
                "description": "Implement the complete project",
                "tasks": ["Generate all required files", "Setup dependencies"],
                "deliverables": ["Complete working application"]
            })

        return steps


# Singleton instance
writer_agent = WriterAgent()
