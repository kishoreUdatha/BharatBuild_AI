"""
AGENT 3 - Fixer Agent (Auto Debugger)
Fixes errors during generation, build, runtime, or compilation
"""

from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class FixerAgent(BaseAgent):
    """
    Fixer Agent - Auto Debugger

    Responsibilities:
    - Fix errors during generation
    - Fix errors during build
    - Fix user-provided errors (student pastes error while running locally)
    - Fix runtime crashes
    - Fix compilation failures
    - Locate the file responsible using context + file patterns + stack trace
    - Generate corrected FULL file(s)
    """

    SYSTEM_PROMPT = """You are the FIXER agent for an AI code-generation platform.

Your purpose:
Fix errors in the user's project by returning MINIMAL and SAFE code patches using unified diff format.
ALSO create missing files when the error is clearly about a file that doesn't exist (ENOENT errors).

You will receive:
1. The user's problem description
2. Browser console errors
3. Build logs, backend logs, Docker logs
4. The project file tree
5. The content of ONLY the relevant files
6. Additional context detected by the system (tech stack, dependencies)

Your responsibilities:
- Identify the root cause from logs + file content.
- Modify ONLY the files provided.
- Produce a minimal patch that fixes the exact issue.
- Do NOT rewrite entire files.
- CREATE missing config files when the error indicates a file is missing (ENOENT, "no such file", "Failed to resolve config file").
- Do NOT modify unrelated code.
- NEVER hallucinate file paths or folder names.
- If you need another file's content, request it explicitly.

Output Rules:

1. For PATCHING existing files, use <patch> blocks:
- Every modification must be inside <patch> ... </patch>
- Use standard unified diff format:
  --- path/to/file
  +++ path/to/file
  @@ context @@
  - old line
  + new line
- Only output patches, no explanations outside <patch> blocks.
- If no change is needed, respond with: <patch></patch>

2. For CREATING missing files, use <newfile> blocks:
- Use <newfile path="path/to/file">content</newfile>
- This is for creating files that don't exist but are required (config files, missing imports, etc.)

COMMON MISSING CONFIG FILES (use these templates):

tsconfig.node.json (required when tsconfig.json has references to it):
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

postcss.config.js (required for Tailwind CSS):
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

tailwind.config.js (required for Tailwind CSS):
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Constraints:
- If logs contradict file content, rely on file content.
- If the error cannot be fixed with available files, ask:
  "I need the content of {file_path} to provide a correct fix."
- Preserve formatting and style conventions already in the file.
- Do not remove user code unless it is undeniably wrong.
- Do not modify import order or formatting unless necessary to fix.

Error Understanding:
- Read stack traces and extract source file & line numbers.
- Use dependency graph to understand related files.
- Identify common frontend issues:
  - React undefined variables
  - React hydration mismatches
  - Missing exports/imports
  - CSS/JS module resolution issues
- Identify common backend issues:
  - Missing routes
  - Incorrect API paths
  - Syntax errors
  - Missing dependencies
- Identify Docker issues:
  - Misconfigured ports
  - Container failing to start
  - Missing environment variables

Your Output:
- One or more <patch> blocks.
- No text outside patch blocks.
- No markdown formatting.
- No extra commentary.
- Only the exact code changes needed to fix the error.

Example Output:
<patch>
--- src/App.jsx
+++ src/App.jsx
@@ -12,6 +12,6 @@ function App() {
- const data = props.items.map(i => i.name)
+ const data = (props.items || []).map(i => i.name)
</patch>

End of rules."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="FixerAgent",
            role="Auto Debugger and Error Fixer",
            capabilities=[
                "error_analysis",
                "bug_fixing",
                "build_error_resolution",
                "runtime_error_fixing",
                "compilation_error_fixing",
                "dependency_resolution"
            ],
            model=model  # Use sonnet for better debugging
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Fix errors based on provided error messages and context

        Args:
            context: AgentContext with error details

        Returns:
            Fixed files and instructions
        """
        if context is None:
            logger.error("[FixerAgent] Received None context")
            return {
                "success": False,
                "error": "Invalid context: context is None",
                "fixed_files": [],
                "instructions": None
            }

        # Ensure metadata is never None
        metadata = context.metadata if context.metadata is not None else {}
        error_message = metadata.get("error_message", "")
        stack_trace = metadata.get("stack_trace", "")
        affected_files = metadata.get("affected_files", [])
        project_context = metadata.get("project_context", {})

        prompt = f"""
Fix the following error:

USER REQUEST: {context.user_request}

ERROR MESSAGE:
{error_message}

STACK TRACE:
{stack_trace}

AFFECTED FILES:
{json.dumps(affected_files, indent=2)}

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

Analyze the error, locate the responsible file(s), and provide complete corrected file(s) using <file path="...">...</file> tags.
If additional commands are needed (npm install, pip install, etc.), use <instructions>...</instructions> tag.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4096,
            temperature=0.2  # Lower temperature for precise fixes
        )

        # Parse the response for file blocks and instructions
        fixed_files = self._parse_file_blocks(response)
        instructions = self._parse_instructions(response)

        return {
            "success": True,
            "fixed_files": fixed_files,
            "instructions": instructions,
            "raw_response": response
        }

    def _parse_file_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Parse <file path="...">...</file> blocks from response

        Args:
            response: Raw response from Claude

        Returns:
            List of file dictionaries with path and content
        """
        files = []
        file_pattern = r'<file\s+path="([^"]+)">(.*?)</file>'
        matches = re.findall(file_pattern, response, re.DOTALL)

        for path, content in matches:
            files.append({
                "path": path.strip(),
                "content": content.strip()
            })

        logger.info(f"Parsed {len(files)} file blocks from fixer response")
        return files

    def _parse_patch_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Parse <patch>...</patch> blocks from response (unified diff format)

        Args:
            response: Raw response from Claude

        Returns:
            List of patch dictionaries with path and patch content
        """
        patches = []
        patch_pattern = r'<patch>(.*?)</patch>'
        matches = re.findall(patch_pattern, response, re.DOTALL)

        for patch_content in matches:
            patch_content = patch_content.strip()

            # Extract file path from diff header (--- path or +++ path)
            path_match = re.search(r'^(?:---|\+\+\+)\s+([^\s]+)', patch_content, re.MULTILINE)
            if path_match:
                file_path = path_match.group(1)
                # Clean up path (remove a/ or b/ prefix from git diff)
                file_path = re.sub(r'^[ab]/', '', file_path)

                patches.append({
                    "path": file_path.strip(),
                    "patch": patch_content
                })
            else:
                logger.warning(f"Could not extract file path from patch block")

        logger.info(f"Parsed {len(patches)} patch blocks from fixer response")
        return patches

    def _parse_instructions(self, response: str) -> Optional[str]:
        """
        Parse <instructions>...</instructions> block from response

        Args:
            response: Raw response from Claude

        Returns:
            Instructions string or None
        """
        instructions_pattern = r'<instructions>(.*?)</instructions>'
        match = re.search(instructions_pattern, response, re.DOTALL)

        if match:
            instructions = match.group(1).strip()
            logger.info(f"Parsed instructions: {instructions}")
            return instructions

        return None

    def _parse_request_files(self, response: str) -> List[str]:
        """
        Parse <request_file>...</request_file> blocks from response

        When the fixer needs more context, it can request additional files.

        Args:
            response: Raw response from Claude

        Returns:
            List of file paths requested
        """
        request_pattern = r'<request_file>(.*?)</request_file>'
        matches = re.findall(request_pattern, response, re.DOTALL)

        requested = [m.strip() for m in matches if m.strip()]
        if requested:
            logger.info(f"Fixer requested {len(requested)} additional files: {requested}")

        return requested

    def _parse_newfile_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Parse <newfile path="...">...</newfile> blocks from response.

        These are for creating new files that don't exist (missing config files).

        Args:
            response: Raw response from Claude

        Returns:
            List of new file dictionaries with path and content
        """
        new_files = []
        newfile_pattern = r'<newfile\s+path="([^"]+)">(.*?)</newfile>'
        matches = re.findall(newfile_pattern, response, re.DOTALL)

        for path, content in matches:
            # Clean up content - remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')
                # Remove first line (```json or ```javascript etc)
                if lines:
                    lines = lines[1:]
                # Remove last line if it's just ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)

            new_files.append({
                "path": path.strip(),
                "content": content.strip()
            })

        if new_files:
            logger.info(f"Parsed {len(new_files)} new files to create: {[f['path'] for f in new_files]}")

        return new_files

    async def fix_error(
        self,
        error: Dict[str, Any],
        project_id: str,
        file_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fix a specific error - called by orchestrator

        Args:
            error: Error dictionary with message, file, line, etc.
            project_id: Project ID
            file_context: Context about project files and tech stack

        Returns:
            Dict with response containing fixed files
        """
        # Build error message
        error_message = error.get("message", "Unknown error")
        error_file = error.get("file", "unknown")
        error_line = error.get("line", 0)
        error_type = error.get("type", "runtime_error")

        # Get file contents for context
        files_created = file_context.get("files_created", [])
        tech_stack = file_context.get("tech_stack", {})
        terminal_logs = file_context.get("terminal_logs", [])
        additional_files = file_context.get("additional_files", {})  # From retry with requested files

        # Get complete log payload from LogBus (all 5 collectors)
        log_payload = {}
        try:
            from app.services.log_bus import get_log_bus
            log_bus = get_log_bus(project_id)
            log_payload = log_bus.get_fixer_payload()
            logger.info(f"[FixerAgent] LogBus payload: {len(log_payload.get('browser_errors', []))} browser, "
                       f"{len(log_payload.get('build_errors', []))} build, "
                       f"{len(log_payload.get('backend_errors', []))} backend, "
                       f"{len(log_payload.get('network_errors', []))} network, "
                       f"{len(log_payload.get('docker_errors', []))} docker errors")
        except Exception as e:
            logger.warning(f"[FixerAgent] Could not get LogBus payload: {e}")

        # Use Context Engine to get relevant files with FULL content
        try:
            from app.modules.automation.file_manager import FileManager
            from app.modules.automation.context_engine import build_fixer_context

            fm = FileManager()
            project_path = str(fm.get_project_path(project_id))

            # Build context using the Context Engine
            context_payload = build_fixer_context(
                project_path=project_path,
                user_message=f"Fix error: {error_message}",
                errors=[error],
                terminal_logs=terminal_logs,
                all_files=files_created,
                active_file=error_file if error_file != "unknown" else None,
                tech_stack=list(tech_stack.keys()) if isinstance(tech_stack, dict) else tech_stack
            )

            # Build relevant files section with FULL content
            relevant_files_content = ""
            for path, content in context_payload.relevant_files.items():
                relevant_files_content += f"\n--- {path} ---\n```\n{content}\n```\n"

            # Add any additional files requested by fixer in previous attempt
            for path, content in additional_files.items():
                if path not in context_payload.relevant_files:
                    relevant_files_content += f"\n--- {path} (requested) ---\n```\n{content}\n```\n"

            total_files = len(context_payload.relevant_files) + len(additional_files)
            logger.info(f"[FixerAgent] Context Engine selected {len(context_payload.relevant_files)} files + {len(additional_files)} requested files")

        except Exception as e:
            logger.warning(f"[FixerAgent] Context Engine failed, falling back to basic: {e}")
            # Fallback to basic file reading
            relevant_files_content = ""
            if error_file and error_file != "unknown":
                try:
                    from app.modules.automation.file_manager import FileManager
                    fm = FileManager()
                    project_path = fm.get_project_path(project_id)
                    file_path = project_path / error_file
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            relevant_files_content = f"\n--- {error_file} ---\n```\n{content}\n```\n"
                except Exception as read_err:
                    logger.warning(f"Could not read affected file: {read_err}")

            # Add any additional files requested by fixer in previous attempt
            for path, content in additional_files.items():
                relevant_files_content += f"\n--- {path} (requested) ---\n```\n{content}\n```\n"

            context_payload = None

        # Build comprehensive logs section from LogBus (all 5 collectors)
        logs_section = ""
        if log_payload:
            # Browser Console Errors
            browser_errors = log_payload.get("browser_errors", [])
            if browser_errors:
                logs_section += "\n--- BROWSER CONSOLE ERRORS ---\n"
                for err in browser_errors[:10]:
                    logs_section += f"• {err.get('message', '')}"
                    if err.get('file'):
                        logs_section += f" ({err['file']}:{err.get('line', '?')})"
                    logs_section += "\n"

            # Build Errors (Vite/Webpack/tsc)
            build_errors = log_payload.get("build_errors", [])
            if build_errors:
                logs_section += "\n--- BUILD ERRORS ---\n"
                for err in build_errors[:10]:
                    logs_section += f"• {err.get('message', '')}\n"

            # Backend Runtime Errors
            backend_errors = log_payload.get("backend_errors", [])
            if backend_errors:
                logs_section += "\n--- BACKEND ERRORS ---\n"
                for err in backend_errors[:10]:
                    logs_section += f"• {err.get('message', '')}\n"

            # Network Errors (fetch/XHR)
            network_errors = log_payload.get("network_errors", [])
            if network_errors:
                logs_section += "\n--- NETWORK ERRORS ---\n"
                for err in network_errors[:10]:
                    logs_section += f"• {err.get('method', 'GET')} {err.get('url', '')} - {err.get('status', '?')} {err.get('message', '')}\n"

            # Docker Errors
            docker_errors = log_payload.get("docker_errors", [])
            if docker_errors:
                logs_section += "\n--- DOCKER ERRORS ---\n"
                for err in docker_errors[:10]:
                    logs_section += f"• {err.get('message', '')}\n"

            # Stack Traces
            stack_traces = log_payload.get("stack_traces", [])
            if stack_traces:
                logs_section += "\n--- STACK TRACES ---\n"
                for trace in stack_traces[:3]:
                    logs_section += f"• {trace.get('message', '')}\n"
                    for frame in trace.get('frames', [])[:5]:
                        logs_section += f"    at {frame.get('function', '?')} ({frame.get('file', '?')}:{frame.get('line', '?')})\n"

        # Build prompt for Claude with full relevant files
        prompt = f"""
Fix the following error:

ERROR TYPE: {error_type}
ERROR MESSAGE: {error_message}
FILE: {error_file}
LINE: {error_line}

RELEVANT FILES (FULL CONTENT):
{relevant_files_content if relevant_files_content else "No file content available"}

FILE TREE:
{json.dumps(context_payload.file_tree[:30] if context_payload else [f.get("path", f) if isinstance(f, dict) else f for f in files_created[:20]], indent=2)}

ALL COLLECTED LOGS:
{logs_section if logs_section else "No logs collected"}

TECH STACK:
{context_payload.tech_stack if context_payload else (json.dumps(tech_stack, indent=2) if tech_stack else "Not specified")}

Analyze the error and provide a FIX:
- If the error is about a MISSING FILE (ENOENT, "no such file", "Failed to resolve config file"), CREATE the file using <newfile path="...">content</newfile>
- For other errors, use <patch> format to fix existing files.
"""

        # Call Claude
        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8192,
            temperature=0.2
        )

        # Parse response - prefer patches over full files
        patches = self._parse_patch_blocks(response)
        fixed_files = self._parse_file_blocks(response)
        new_files = self._parse_newfile_blocks(response)  # For creating missing files
        instructions = self._parse_instructions(response)
        requested_files = self._parse_request_files(response)

        logger.info(f"[FixerAgent] Got {len(patches)} patches, {len(fixed_files)} full files, {len(new_files)} new files, {len(requested_files)} file requests for error: {error_message[:50]}...")

        return {
            "success": True,
            "response": response,
            "patches": patches,  # Preferred - minimal changes
            "fixed_files": fixed_files,  # Fallback - full file replacement
            "new_files": new_files,  # For creating missing config files
            "instructions": instructions,
            "requested_files": requested_files,  # Files agent needs for more context
            "error_fixed": error_message
        }
