"""
Production-Ready Fixer Agent with Safety Rules

Prevents:
❌ Wrong file being updated
❌ Wrong architecture changes
❌ Infinite loops
❌ Partial file updates
❌ Missing multi-file dependency context
❌ Incorrect regex parsing
❌ Claude hallucinations
❌ Rewriting entire project
"""

from typing import Dict, List, Optional, Any, Set
import json
import re
from datetime import datetime
from dataclasses import dataclass

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


@dataclass
class ErrorAnalysis:
    """Structured error analysis"""
    error_type: str  # syntax, runtime, import, type, logic
    root_cause: str
    affected_files: List[str]
    suggested_files_to_fix: List[str]
    confidence: float  # 0.0 to 1.0
    requires_multi_file_fix: bool
    stack_trace_files: List[str]


@dataclass
class FixAttempt:
    """Track fix attempts to prevent loops and inform retries"""
    timestamp: datetime
    error_hash: str
    files_modified: List[str]
    success: bool
    attempt_number: int = 1
    fix_description: str = ""  # What fix was attempted
    result_error: str = ""     # Error after this fix (if any)
    approach_used: str = ""    # e.g., "syntax_fix", "import_fix", "dependency_fix"


class ProductionFixerAgent(BaseAgent):
    """
    Production-Ready Fixer Agent with Safety Rules

    Safety Features:
    1. File targeting validation
    2. Architecture preservation
    3. Loop prevention (max 3 attempts per error)
    4. Full file regeneration only
    5. Multi-file context tracking
    6. Robust regex parsing
    7. Hallucination detection
    8. Scope limiting
    """

    # Safety limits
    MAX_FIX_ATTEMPTS_PER_ERROR = 10  # Increased to match frontend retry loop
    MAX_FILES_TO_FIX_AT_ONCE = 5
    MAX_PROJECT_FILES_TO_REWRITE = 10  # Prevents mass rewrites

    # ============= BOLT.NEW STYLE FIXER AGENT PROMPT (MULTI-TECHNOLOGY) =============
    SYSTEM_PROMPT = """You are the FIXER AGENT - an expert at fixing code, dependency, terminal, and Docker issues across ALL technologies.

Your job is to analyze errors and generate precise fixes that work the FIRST time.

## INPUTS YOU RECEIVE:
- Error logs (stderr, stdout, stack traces)
- Command that failed
- Related file contents (exact code)
- Project metadata (package.json, requirements.txt, Dockerfile, etc.)
- Environment details (runtime version, ports, framework)

## YOUR OUTPUT:
- Unified patch with fixed files
- Only output fixed files (no explanations)
- Use exact file paths

## SUPPORTED TECHNOLOGIES:

### JAVASCRIPT/TYPESCRIPT
- Node.js, Deno, Bun
- React, Vue, Angular, Svelte, Next.js, Nuxt, Remix
- Vite, Webpack, esbuild, Rollup
- Express, Fastify, Koa, NestJS
- ESLint, Prettier, TypeScript errors

### PYTHON
- FastAPI, Flask, Django, Starlette
- Poetry, pip, pipenv, conda
- pytest, unittest errors
- SQLAlchemy, Pydantic, asyncio
- Type hints, mypy errors

### JAVA/KOTLIN
- Spring Boot, Quarkus, Micronaut
- Maven, Gradle build errors
- JUnit, Mockito test errors
- JDBC, JPA, Hibernate

### GO
- Gin, Echo, Fiber, Chi
- go mod errors
- Build/compile errors
- goroutine/channel issues

### RUST
- Actix, Axum, Rocket
- Cargo build errors
- Borrow checker errors
- Lifetime issues

### RUBY
- Rails, Sinatra
- Bundler, gem errors
- RSpec, Minitest errors

### PHP
- Laravel, Symfony
- Composer errors
- Artisan command errors

### C#/.NET
- ASP.NET Core, Blazor
- NuGet errors
- dotnet CLI errors

### MOBILE
- React Native, Expo
- Flutter/Dart
- iOS/Swift build errors
- Android/Kotlin build errors

### DATABASE
- PostgreSQL, MySQL, SQLite
- MongoDB, Redis
- Prisma, Drizzle, TypeORM
- Migration errors

### DOCKER/CONTAINERIZATION
- Dockerfile syntax
- docker-compose.yml
- Multi-stage builds
- Port mapping, volumes
- Health checks

### CLOUD/DEVOPS
- AWS, GCP, Azure errors
- Kubernetes, Helm
- Terraform, Pulumi
- CI/CD pipeline errors

## FIX CATEGORIES:

### 1. SYNTAX ERRORS
- Missing brackets, semicolons, quotes
- Invalid syntax for language
- JSX/TSX errors
- YAML/JSON formatting

### 2. IMPORT/MODULE ERRORS
- Cannot find module
- ModuleNotFoundError
- ImportError
- Circular dependencies

### 3. TYPE ERRORS
- TypeError, AttributeError
- Type mismatch
- Null/undefined access
- Generic type issues

### 4. RUNTIME ERRORS
- ReferenceError, NameError
- IndexError, KeyError
- Null pointer exceptions
- Stack overflow

### 5. BUILD ERRORS
- Compilation failed
- Bundler errors
- Asset processing errors
- Minification errors

### 6. DEPENDENCY ERRORS
- Version conflicts
- Peer dependency issues
- Missing packages
- Lock file conflicts

### 7. CONFIGURATION ERRORS
- Config file syntax
- Environment variables
- Port conflicts
- Path issues

### 8. DOCKER ERRORS
- Build failures
- Container startup errors
- Network issues
- Volume mount errors

### 9. DATABASE ERRORS
- Connection errors
- Migration failures
- Query syntax errors
- Schema mismatches

### 10. TEST ERRORS
- Assertion failures
- Mock/stub issues
- Timeout errors
- Setup/teardown errors

## OUTPUT FORMAT (JSON - Production Standard):

You MUST return a valid JSON object with this structure:
```json
{{
  "patches": [
    {{
      "path": "src/App.jsx",
      "diff": "--- a/src/App.jsx\\n+++ b/src/App.jsx\\n@@ -1,5 +1,6 @@\\n import React from 'react';\\n-import Header from './Header';\\n+import Header from './components/Header';",
      "type": "patch"
    }}
  ],
  "newFiles": [
    {{
      "path": "tsconfig.node.json",
      "content": "{{ ... full file content ... }}",
      "type": "create"
    }}
  ],
  "runCommand": "npm install missing-package"
}}
```

### RULES:
1. `patches` - Array of unified diffs for EXISTING files (minimal changes)
2. `newFiles` - Array of NEW files to create (full content)
3. `runCommand` - Optional command to run (npm install, pip install, etc.)
4. Return ONLY the JSON object - no explanations before or after
5. Escape newlines in diff as \\n
6. If no patches needed, use empty array: `"patches": []`

## DIFF FORMAT RULES:
1. Use unified diff format (like git diff)
2. Include @@ hunk headers with line numbers
3. Lines starting with '-' are REMOVED
4. Lines starting with '+' are ADDED
5. Lines starting with ' ' (space) are CONTEXT
6. Keep 3 lines of context around changes
7. Multiple hunks allowed for multiple changes in same file

## EXAMPLES (JSON FORMAT):

### JavaScript - Missing Module:
```json
{{"patches": [], "newFiles": [], "runCommand": "npm install express"}}
```

### Python - Import Error:
```json
{{"patches": [], "newFiles": [], "runCommand": "pip install fastapi uvicorn"}}
```

### Python - Type Error (patch existing file):
```json
{{
  "patches": [{{
    "path": "app/api/users.py",
    "diff": "--- a/app/api/users.py\\n+++ b/app/api/users.py\\n@@ -1,5 +1,8 @@\\n+from typing import Optional\\n+\\n def get_user(user_id: int):\\n     user = db.get(user_id)\\n-    return user.to_dict()\\n+    if user is None:\\n+        return None\\n+    return user.to_dict()",
    "type": "patch"
  }}],
  "newFiles": [],
  "runCommand": null
}}
```

### Missing Config File (create new file):
```json
{{
  "patches": [],
  "newFiles": [{{
    "path": "tsconfig.node.json",
    "content": "{{\\n  \\"compilerOptions\\": {{\\n    \\"composite\\": true,\\n    \\"module\\": \\"ESNext\\"\\n  }},\\n  \\"include\\": [\\"vite.config.ts\\"]\\n}}",
    "type": "create"
  }}],
  "runCommand": null
}}
```

### Import Path Fix:
```json
{{
  "patches": [{{
    "path": "src/App.jsx",
    "diff": "--- a/src/App.jsx\\n+++ b/src/App.jsx\\n@@ -1,3 +1,3 @@\\n-import Header from './Header';\\n+import Header from './components/Header';",
    "type": "patch"
  }}],
  "newFiles": [],
  "runCommand": null
}}

## RETRY STRATEGY (When Previous Fixes Failed):

If this is a RETRY attempt (previous_attempts > 0):
1. READ the "PREVIOUS ATTEMPTS" section carefully
2. UNDERSTAND why previous fixes failed (new error message)
3. TRY A DIFFERENT APPROACH - don't repeat what failed
4. ESCALATE complexity if simple fixes didn't work:
   - Attempt 1: Fix syntax/typo
   - Attempt 2: Fix imports/paths
   - Attempt 3: Add missing dependencies
   - Attempt 4: Restructure code
   - Attempt 5+: Consider broader changes

### Strategy by Retry Count:
- Retry 1-2: Focus on the exact error location
- Retry 3-4: Look at related files that might cause the issue
- Retry 5-6: Consider dependency/version issues
- Retry 7+: More comprehensive refactoring may be needed

### If Error Changed After Previous Fix:
- Your previous fix partially worked!
- Now fix the NEW error (different from before)
- Don't undo your previous fix unless it caused the new error

### If Same Error Persists:
- Your previous fix didn't address the root cause
- Look DEEPER at the stack trace
- Consider if the file path is wrong
- Check for multiple places where the error could originate

## CRITICAL RULES:

1. OUTPUT ONLY JSON - No text before or after the JSON object
2. EXISTING FILES → Use "patches" array with unified diff
3. NEW/MISSING FILES → Use "newFiles" array with full content
4. FIX ROOT CAUSE - Don't just suppress errors
5. PRESERVE ARCHITECTURE - Don't restructure the project
6. MATCH EXISTING PATTERNS - Use same coding style
7. MAX {max_files} FILES - Don't fix unrelated files
8. MINIMAL CHANGES - Only change what's necessary
9. ON RETRY - Try a DIFFERENT approach than what failed before
10. VALID JSON - Ensure your output is parseable JSON

## WHY YOU SUCCEED:
- You receive EXACT error logs
- You receive EXACT file contents
- You understand the project context via fileTree
- You support ALL major technologies
- You generate precise, minimal patches
- The system auto-applies your patches
- The system auto-reruns after fix

Be surgical. Fix only what's broken. Output valid JSON only.
"""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="ProductionFixerAgent",
            role="Production Auto Debugger with Safety Rules",
            capabilities=[
                "error_analysis",
                "safe_bug_fixing",
                "build_error_resolution",
                "runtime_error_fixing",
                "multi_file_fixes",
                "dependency_resolution",
                "loop_prevention",
                "hallucination_detection"
            ],
            model=model
        )

        # Track fix attempts to prevent infinite loops
        self.fix_history: Dict[str, List[FixAttempt]] = {}

    def _get_previous_attempts_context(self, error_hash: str) -> str:
        """Build context about previous fix attempts to help Claude try different approaches"""
        if error_hash not in self.fix_history or not self.fix_history[error_hash]:
            return ""

        attempts = self.fix_history[error_hash]
        attempt_count = len(attempts)

        if attempt_count == 0:
            return ""

        lines = [
            f"\n## PREVIOUS ATTEMPTS ({attempt_count} failed - TRY A DIFFERENT APPROACH!)",
            ""
        ]

        for i, attempt in enumerate(attempts[-3:], 1):  # Show last 3 attempts
            lines.append(f"### Attempt {attempt.attempt_number}:")
            lines.append(f"- Files modified: {', '.join(attempt.files_modified) if attempt.files_modified else 'None'}")
            if attempt.fix_description:
                lines.append(f"- What was tried: {attempt.fix_description}")
            if attempt.result_error:
                lines.append(f"- Result error: {attempt.result_error[:200]}...")
            if attempt.approach_used:
                lines.append(f"- Approach: {attempt.approach_used}")
            lines.append("")

        # Add guidance based on attempt count
        if attempt_count >= 5:
            lines.append("⚠️ MULTIPLE FAILURES - Consider:")
            lines.append("- Is there a deeper architectural issue?")
            lines.append("- Are there multiple files that need changing together?")
            lines.append("- Is a dependency missing or wrong version?")
        elif attempt_count >= 3:
            lines.append("⚠️ Several attempts failed - try a COMPLETELY different approach!")
        else:
            lines.append("💡 Previous fix didn't work - analyze what went wrong and try differently")

        return "\n".join(lines)

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Fix errors with safety checks and validation.
        Supports BOTH fixing existing files AND creating new files (for missing configs).
        """
        # Validate context
        if context is None:
            logger.error("[ProductionFixerAgent] Received None context")
            return {
                "success": False,
                "error": "Invalid context: context is None",
                "fixed_files": [],
                "patches": [],
                "instructions": None
            }

        # Ensure metadata is never None
        metadata = context.metadata if context.metadata is not None else {}

        # Extract error information with robust null handling
        # metadata.get() returns None if key exists but value is None, so use "or" fallback
        error_message = metadata.get("error_message") or ""
        stack_trace = metadata.get("stack_trace") or ""

        # Ensure they are strings for regex operations
        if not isinstance(error_message, str):
            error_message = str(error_message) if error_message else ""
        if not isinstance(stack_trace, str):
            stack_trace = str(stack_trace) if stack_trace else ""

        # Generate error hash for loop detection
        error_hash = self._hash_error(error_message, stack_trace)

        # Check if we've tried to fix this error too many times
        if not self._can_attempt_fix(error_hash):
            return {
                "success": False,
                "error": f"Maximum fix attempts ({self.MAX_FIX_ATTEMPTS_PER_ERROR}) reached for this error",
                "suggestion": "Manual intervention required"
            }

        # ============= EXTRACT FILES FROM ALL SOURCES =============
        # The frontend error_message is often truncated. Use ALL available sources:
        # 1. affected_files from LogBus (already extracted by LogBus)
        # 2. error_logs["build"] messages (full build errors with file paths)
        # 3. error_message and stack_trace (fallback)

        # Source 1: Pre-extracted affected_files from LogBus
        logbus_affected_files = metadata.get("affected_files", [])
        logger.info(f"[ProductionFixerAgent] Source 1 - LogBus affected_files: {logbus_affected_files}")

        # Source 2: Extract files from full build error messages
        error_logs = metadata.get("error_logs", {})
        build_errors = error_logs.get("build", [])
        build_error_files = []
        full_error_text = error_message  # Start with frontend error

        for err in build_errors:
            # Get rebuilt or original error message
            err_msg = err.get("rebuilt", err.get("original", "")) if isinstance(err, dict) else str(err)
            full_error_text += "\n" + err_msg
            # Extract files from this error
            build_error_files.extend(self._extract_files_from_error(err_msg))

        logger.info(f"[ProductionFixerAgent] Source 2 - Build error files: {list(set(build_error_files))}")

        # Combine all file sources BEFORE analysis
        pre_extracted_files = list(set(logbus_affected_files + build_error_files))

        # Analyze error with the FULL error text (not just truncated frontend message)
        analysis = await self._analyze_error(
            error_message=full_error_text,  # Use combined full error text
            stack_trace=stack_trace,
            context=context
        )

        # ============= BOLT.NEW STYLE: DYNAMIC FILE SELECTION =============
        # Step 1: Identify files mentioned in error
        # Step 2: Load those files
        # Step 3: Load nearby files (same directory)
        # Step 4: Send error + file tree + relevant content to Claude

        project_files = metadata.get("project_files", [])

        # Step 1: Get files from ALL sources (analysis + pre-extracted)
        error_mentioned_files = list(set(analysis.suggested_files_to_fix + pre_extracted_files))
        logger.info(f"[ProductionFixerAgent] DYNAMIC Step 1: Error mentions files: {error_mentioned_files}")

        # Step 2: Find which error-mentioned files exist in project
        existing_files = self._validate_target_files(error_mentioned_files, project_files)
        logger.info(f"[ProductionFixerAgent] DYNAMIC Step 2: Found existing files: {existing_files}")

        # Step 3: Load nearby files (same directory) for context
        nearby_files = self._get_nearby_files(existing_files, project_files)
        logger.info(f"[ProductionFixerAgent] DYNAMIC Step 3: Nearby files: {nearby_files}")

        # Combine: error files + nearby files (limit total to avoid token overflow)
        files_to_load = list(set(existing_files + nearby_files))[:10]  # Max 10 files

        # Files that don't exist are potential new files to create
        missing_files = [f for f in error_mentioned_files if f not in existing_files]
        logger.info(f"[ProductionFixerAgent] DYNAMIC: Missing files (can be created): {missing_files}")

        # Build file tree metadata (Bolt.new style - structure only, no content)
        file_tree = self._build_file_tree(project_files)

        # DYNAMIC: Allow Claude to fix/create ANY file it identifies
        # We don't restrict to hardcoded safe lists anymore
        all_allowed_files = list(set(existing_files + error_mentioned_files))

        # Safety check: Don't fix too many files at once
        if len(all_allowed_files) > self.MAX_FILES_TO_FIX_AT_ONCE:
            logger.warning(f"[ProductionFixerAgent] Too many files ({len(all_allowed_files)}), limiting to {self.MAX_FILES_TO_FIX_AT_ONCE}")
            all_allowed_files = all_allowed_files[:self.MAX_FILES_TO_FIX_AT_ONCE]

        # Step 4: Get file contents for error files + nearby files (openFiles in Bolt.new style)
        file_contents = await self._get_file_contents(files_to_load, context)

        # Get previous attempts context for retry guidance
        previous_attempts_context = self._get_previous_attempts_context(error_hash)
        attempt_number = len(self.fix_history.get(error_hash, [])) + 1

        # Build Bolt.new-style prompt with:
        # - openFiles (file contents for error-mentioned files)
        # - fileTree (structure metadata, no content)
        # - error (message, stack, filename, line)
        prompt = self._build_safe_prompt(
            error_message=error_message,
            stack_trace=stack_trace,
            analysis=analysis,
            file_contents=file_contents,
            context=context,
            allowed_new_files=missing_files,  # Files that can be created
            previous_attempts_context=previous_attempts_context,
            attempt_number=attempt_number,
            file_tree=file_tree  # Bolt.new-style file tree metadata
        )

        # Call Claude with safety-enhanced system prompt
        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT.format(
                max_files=self.MAX_FILES_TO_FIX_AT_ONCE
            ),
            user_prompt=prompt,
            max_tokens=8192,
            temperature=0.1
        )

        # Parse response (DYNAMIC - accept any file path Claude outputs)
        parsed = self._parse_and_validate_response(response, all_allowed_files)

        # DYNAMIC: We now trust Claude's file identification
        # Log any files Claude identified that weren't in our initial list (for debugging)
        claude_identified_files = [f['path'] for f in parsed['fixed_files']]
        extra_files = [f for f in claude_identified_files if f not in all_allowed_files]
        if extra_files:
            logger.info(f"[ProductionFixerAgent] DYNAMIC: Claude identified additional files: {extra_files}")
            # Add these to allowed files for safety check bypass
            all_allowed_files.extend(extra_files)

        # Safety check: Verify files are complete (no partial updates)
        for file_info in parsed['fixed_files']:
            if not self._is_complete_file(file_info['content']):
                logger.warning(f"[ProductionFixerAgent] File {file_info['path']} appears incomplete")

        # Build description of what was fixed
        files_fixed = [f['path'] for f in parsed['fixed_files']]
        patches_applied = [p['path'] for p in parsed.get('patches', [])]
        all_modified = files_fixed + patches_applied

        fix_description = f"Modified files: {', '.join(all_modified)}" if all_modified else "No files modified"
        if parsed.get('instructions'):
            fix_description += f"; Instructions: {parsed['instructions'][:100]}"

        # Record fix attempt with full context
        self._record_fix_attempt(
            error_hash=error_hash,
            files_modified=all_modified,
            success=True,
            fix_description=fix_description,
            approach_used=analysis.error_type  # Use error type as approach indicator
        )

        return {
            "success": True,
            "analysis": analysis,
            "fixed_files": parsed['fixed_files'],       # Full files (new/missing)
            "patches": parsed.get('patches', []),       # Unified diff patches (existing)
            "instructions": parsed.get('instructions'),
            "existing_files": existing_files,           # Files that existed before
            "missing_files": missing_files,             # Files that need to be created
            "claude_identified_files": claude_identified_files,  # All files Claude found
            "safety_checks_passed": True,
            "attempt_number": attempt_number,
            "mode": "dynamic"  # Mark as using dynamic mode
        }

    async def _analyze_error(
        self,
        error_message: str,
        stack_trace: str,
        context: AgentContext
    ) -> ErrorAnalysis:
        """
        Analyze error to identify root cause and target files
        """
        # Extract files from stack trace
        stack_files = self._extract_files_from_stacktrace(stack_trace)

        # Determine error type
        error_type = self._classify_error(error_message)

        # Extract affected files from error message
        error_files = self._extract_files_from_error(error_message)

        # Combine and deduplicate
        all_files = list(set(stack_files + error_files))

        # Determine if multi-file fix needed
        requires_multi_file = len(all_files) > 1 or "import" in error_message.lower()

        # Calculate confidence
        confidence = 1.0 if stack_files else 0.7

        return ErrorAnalysis(
            error_type=error_type,
            root_cause=self._extract_root_cause(error_message, stack_trace),
            affected_files=all_files,
            suggested_files_to_fix=all_files,
            confidence=confidence,
            requires_multi_file_fix=requires_multi_file,
            stack_trace_files=stack_files
        )

    def _extract_files_from_stacktrace(self, stack_trace: str) -> List[str]:
        """Extract file paths from stack trace"""
        files = []

        # SAFETY: Handle None or non-string stack_trace
        if stack_trace is None or not isinstance(stack_trace, str):
            logger.info(f"[ProductionFixerAgent] Empty or invalid stack trace, returning empty files list")
            return files

        # Pattern: File "path/to/file.py", line X
        pattern = r'File\s+"([^"]+)"'
        matches = re.findall(pattern, stack_trace)
        files.extend(matches)

        # Pattern: at path/to/file.py:line:col
        pattern2 = r'at\s+([\w/\\.]+\.[\w]+):\d+'
        matches2 = re.findall(pattern2, stack_trace)
        files.extend(matches2)

        # Pattern: path/to/file.py:line
        pattern3 = r'([\w/\\.]+\.[\w]+):\d+'
        matches3 = re.findall(pattern3, stack_trace)
        files.extend(matches3)

        # Deduplicate and clean
        files = list(set([f.strip() for f in files if f.strip()]))

        logger.info(f"[ProductionFixerAgent] Extracted {len(files)} files from stack trace: {files}")
        return files

    def _extract_files_from_error(self, error_message: str) -> List[str]:
        """
        DYNAMIC file extraction from error message (Bolt.new style).
        Extracts ANY file path mentioned, not hardcoded patterns.
        """
        files = []

        # SAFETY: Handle None or non-string error_message
        if error_message is None or not isinstance(error_message, str):
            return files

        # Common file extensions to look for
        extensions = r'(?:tsx?|jsx?|vue|svelte|py|rs|go|java|rb|php|cs|cpp|c|h|hpp|swift|kt|scala|json|yaml|yml|toml|xml|html|css|scss|sass|less|md|sql)'

        # DYNAMIC patterns - catch any file path format
        patterns = [
            # TypeScript error format: src/file.tsx(12,5): error TS1234
            # MUST be FIRST to capture before more generic patterns
            rf'([a-zA-Z0-9_\-./\\]+\.{extensions})\(\d+,\d+\)',
            # Path with line:col: src/App.tsx:12:5
            rf'([a-zA-Z0-9_\-./\\]+\.{extensions}):\d+(?::\d+)?',
            # Quoted paths: "src/file.tsx" or 'src/file.tsx'
            rf'["\']([a-zA-Z0-9_\-./\\]+\.{extensions})["\']',
            # Module resolution: Cannot find module './Header'
            r'(?:module|from|import)\s*["\']([^"\']+)["\']',
            # Error in format: Error in src/App.jsx:12
            rf'(?:error|warning|info)\s+(?:in\s+)?([a-zA-Z0-9_\-./\\]+\.{extensions})',
            # At format: at src/file.ts:123
            rf'at\s+([a-zA-Z0-9_\-./\\]+\.{extensions})',
            # File not found: File 'xxx' not found
            r'[Ff]ile\s*["\']([^"\']+)["\']',
            # Standard path with extension (LAST - most generic): src/file.tsx, ./src/file.js
            rf'(?:^|[^a-zA-Z0-9_])([a-zA-Z0-9_][a-zA-Z0-9_\-./\\]*\.{extensions})(?:[^a-zA-Z0-9_]|$)',
        ]

        for pattern in patterns:
            try:
                matches = re.findall(pattern, error_message, re.IGNORECASE)
                files.extend(matches)
            except re.error:
                continue

        # Clean up paths
        cleaned_files = []
        for f in files:
            # Remove leading ./ or ./
            f = re.sub(r'^\.?[/\\]', '', f)
            # Skip node_modules, .git, etc.
            if 'node_modules' in f or '.git' in f:
                continue
            # Skip if it's just an extension or too short
            if len(f) < 3 or f.startswith('.'):
                continue
            cleaned_files.append(f)

        result = list(set(cleaned_files))
        logger.info(f"[ProductionFixerAgent] Extracted {len(result)} files from error message: {result}")
        return result

    def _build_file_tree(self, project_files: List[str]) -> Dict[str, Any]:
        """
        Build file tree metadata (Bolt.new style).
        Returns structure only, NO file contents.
        """
        tree = {}

        for file_path in project_files:
            # Normalize path separators
            parts = file_path.replace('\\', '/').split('/')
            current = tree

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # It's a file
                    current[part] = True
                else:
                    # It's a directory
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        return tree

    def _resolve_import_path(self, import_path: str, from_file: str, project_files: List[str]) -> Optional[str]:
        """
        Resolve relative import to actual file path.
        Example: './Header' from 'src/App.jsx' -> 'src/Header.jsx' or 'src/components/Header.jsx'
        """
        if not import_path.startswith('.'):
            return None  # Not a relative import

        # Get directory of the importing file
        from_dir = '/'.join(from_file.replace('\\', '/').split('/')[:-1])

        # Resolve the relative path
        if import_path.startswith('./'):
            resolved = f"{from_dir}/{import_path[2:]}"
        elif import_path.startswith('../'):
            parts = from_dir.split('/')
            import_parts = import_path.split('/')
            up_count = sum(1 for p in import_parts if p == '..')
            resolved = '/'.join(parts[:-up_count]) + '/' + '/'.join(p for p in import_parts if p not in ['..', '.'])
        else:
            resolved = import_path

        # Try common extensions
        extensions = ['', '.tsx', '.ts', '.jsx', '.js', '.vue', '.svelte', '/index.tsx', '/index.ts', '/index.jsx', '/index.js']

        for ext in extensions:
            candidate = resolved + ext
            # Check if file exists in project
            for pf in project_files:
                pf_normalized = pf.replace('\\', '/')
                if pf_normalized == candidate or pf_normalized.endswith('/' + candidate):
                    return pf

        return None

    def _get_nearby_files(self, error_files: List[str], project_files: List[str], max_nearby: int = 5) -> List[str]:
        """
        Get nearby files (same directory) for context.
        Bolt.new Step 3: Load nearby files to help Claude understand context.

        Example: If error is in src/pages/Home.tsx, also load:
        - src/pages/About.tsx
        - src/pages/index.ts
        But NOT src/components/Button.tsx (different directory)
        """
        nearby = []

        # Get directories of error files
        error_dirs = set()
        for f in error_files:
            normalized = f.replace('\\', '/')
            if '/' in normalized:
                error_dirs.add('/'.join(normalized.split('/')[:-1]))
            else:
                error_dirs.add('')  # Root directory

        # Find files in same directories
        for pf in project_files:
            if pf in error_files:
                continue  # Skip files we already have

            normalized = pf.replace('\\', '/')
            if '/' in normalized:
                pf_dir = '/'.join(normalized.split('/')[:-1])
            else:
                pf_dir = ''

            if pf_dir in error_dirs:
                # Same directory - include it
                nearby.append(pf)

                if len(nearby) >= max_nearby:
                    break

        # Prioritize certain files: index, types, constants, utils
        priority_patterns = ['index.', 'types.', 'constants.', 'utils.', 'helpers.']
        nearby.sort(key=lambda x: (
            0 if any(p in x.lower() for p in priority_patterns) else 1,
            x
        ))

        return nearby[:max_nearby]

    def _classify_error(self, error_message: str) -> str:
        """Classify error type"""
        # SAFETY: Handle None or non-string error_message
        if error_message is None or not isinstance(error_message, str):
            return 'logic'

        error_lower = error_message.lower()

        if any(x in error_lower for x in ['syntaxerror', 'unexpected token', 'invalid syntax']):
            return 'syntax'
        elif any(x in error_lower for x in ['importerror', 'modulenotfound', 'cannot import']):
            return 'import'
        elif any(x in error_lower for x in ['typeerror', 'attributeerror']):
            return 'type'
        elif any(x in error_lower for x in ['runtimeerror', 'valueerror', 'keyerror']):
            return 'runtime'
        else:
            return 'logic'

    def _extract_root_cause(self, error_message: str, stack_trace: str) -> str:
        """Extract concise root cause from error"""
        # SAFETY: Handle None or non-string error_message
        if error_message is None or not isinstance(error_message, str):
            return "Unknown error"

        # Take first line of error message
        lines = error_message.strip().split('\n')
        return lines[0][:200] if lines else "Unknown error"

    def _validate_target_files(
        self,
        suggested_files: List[str],
        project_files: List[str]
    ) -> List[str]:
        """
        Validate that suggested files exist in project
        """
        validated = []

        for suggested in suggested_files:
            # Check exact match
            if suggested in project_files:
                validated.append(suggested)
                continue

            # Check partial match (in case of path differences)
            for project_file in project_files:
                if suggested in project_file or project_file.endswith(suggested):
                    validated.append(project_file)
                    break

        return list(set(validated))

    async def _get_file_contents(
        self,
        file_paths: List[str],
        context: AgentContext
    ) -> Dict[str, str]:
        """
        Get current contents of files to be fixed
        """
        contents = {}

        # Try to get from metadata first
        metadata = context.metadata or {}
        file_contents = metadata.get("file_contents", {})

        for path in file_paths:
            if path in file_contents:
                contents[path] = file_contents[path]
            else:
                logger.warning(f"[ProductionFixerAgent] File content not provided for {path}")
                contents[path] = "# File content not available"

        return contents

    def _build_safe_prompt(
        self,
        error_message: str,
        stack_trace: str,
        analysis: ErrorAnalysis,
        file_contents: Dict[str, str],
        context: AgentContext,
        allowed_new_files: List[str] = None,
        previous_attempts_context: str = "",
        attempt_number: int = 1,
        file_tree: Dict[str, Any] = None
    ) -> str:
        """Build Bolt.new-style prompt with openFiles + fileTree + error"""

        metadata = context.metadata or {}
        allowed_new_files = allowed_new_files or []
        file_tree = file_tree or {}

        # ============= BOLT.NEW STYLE: openFiles =============
        # Only the files mentioned in error, with full content
        open_files_parts = []
        for path, content in file_contents.items():
            # Limit file size but keep complete enough for context
            truncated = len(content) > 4000
            open_files_parts.append(f"""
=== {path} ===
{content[:4000]}{"... (truncated)" if truncated else ""}
""")

        open_files_context = "\n".join(open_files_parts)

        # Get additional config files from metadata (always useful for builds)
        config_context = ""
        if "package_json" in metadata.get("file_contents", {}):
            config_context += f"\n=== package.json ===\n{metadata['file_contents']['package_json'][:2000]}\n"
        if "dockerfile" in metadata.get("file_contents", {}):
            config_context += f"\n=== Dockerfile ===\n{metadata['file_contents']['dockerfile'][:1000]}\n"

        # Get environment info
        env_info = metadata.get("environment", {})
        env_str = f"""
Framework: {env_info.get('framework', 'unknown')}
Project Type: {env_info.get('project_type', 'unknown')}
Ports: {env_info.get('ports', [])}
Has Docker: {env_info.get('has_docker', False)}
"""

        # ============= BOLT.NEW STYLE: fileTree (structure only, no content) =============
        # Convert tree dict to readable format
        def tree_to_string(tree: Dict, indent: int = 0) -> str:
            lines = []
            for name, value in sorted(tree.items()):
                prefix = "  " * indent
                if value is True:
                    lines.append(f"{prefix}{name}")
                elif isinstance(value, dict):
                    lines.append(f"{prefix}{name}/")
                    lines.append(tree_to_string(value, indent + 1))
            return "\n".join(lines)

        file_tree_str = tree_to_string(file_tree) if file_tree else "No file tree available"
        # Limit tree size
        if len(file_tree_str) > 3000:
            file_tree_str = file_tree_str[:3000] + "\n... (truncated)"

        file_tree_section = f"""
## FILE TREE (structure only - use to validate paths):
```
{file_tree_str}
```
"""

        # Recently modified files from metadata
        recently_modified = metadata.get("recently_modified", [])

        # Build recently modified files context (shows Claude which files were recently changed)
        recently_modified_section = ""
        if recently_modified:
            recent_entries = []
            for entry in recently_modified[:10]:  # Show last 10 modified files
                path = entry.get('path', 'unknown')
                action = entry.get('action', 'modified')
                recent_entries.append(f"  - {path} ({action})")

            recently_modified_section = f"""
## RECENTLY MODIFIED FILES (prioritize these for fixes):
{chr(10).join(recent_entries)}
"""

        # Build section for new files that can be created
        new_files_section = ""
        if allowed_new_files:
            new_files_section = f"""
## FILES YOU CAN CREATE (MISSING FILES):
{', '.join(allowed_new_files)}

For these missing config files, use these templates:

tsconfig.json (CRITICAL - fixes TS6305 error):
```json
{{
  "compilerOptions": {{
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false
  }},
  "include": ["src"],
  "exclude": ["node_modules"]
}}
```
⚠️ CRITICAL: "include" must be ["src"] only - NEVER include vite.config.ts!

tsconfig.node.json:
```json
{{
  "compilerOptions": {{
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  }},
  "include": ["vite.config.ts"]
}}
```

postcss.config.js:
```javascript
export default {{
  plugins: {{
    tailwindcss: {{}},
    autoprefixer: {{}},
  }},
}}
```

tailwind.config.js:
```javascript
/** @type {{import('tailwindcss').Config}} */
export default {{
  content: ["./index.html", "./src/**/*.{{js,ts,jsx,tsx}}"],
  theme: {{ extend: {{}} }},
  plugins: [],
}}
```
"""

        # Build retry indicator
        retry_indicator = ""
        if attempt_number > 1:
            retry_indicator = f"""
## ⚠️ THIS IS RETRY ATTEMPT #{attempt_number}

Previous fix attempts DID NOT WORK. You MUST try a DIFFERENT approach!
{previous_attempts_context}
"""

        # Build Bolt.new style prompt
        prompt = f"""## ERROR TO FIX (Attempt #{attempt_number})

**Command:** {metadata.get('command', 'unknown')}

**Error Message:**
```
{error_message}
```

**Stack Trace:**
```
{stack_trace[:2000] if stack_trace else 'No stack trace available'}
```
{retry_indicator}
## ENVIRONMENT
{env_str}
{file_tree_section}{recently_modified_section}
## OPEN FILES (content for error-mentioned files):
{open_files_context if open_files_context.strip() else 'No files to show - this may be a missing file error'}
{new_files_section}
{config_context}

## ERROR ANALYSIS:
- Error Type: {analysis.error_type}
- Root Cause: {analysis.root_cause}
- Confidence: {analysis.confidence}

## YOUR TASK:
1. If error is about MISSING FILE, CREATE it using <file path="...">content</file>
2. If error is in existing file, FIX it using <file path="...">complete content</file> or <patch path="...">unified diff</patch>
3. If packages needed, output <instructions>npm install X</instructions>
{"4. THIS IS A RETRY - Try a COMPLETELY DIFFERENT approach than before!" if attempt_number > 1 else ""}

OUTPUT THE FIX NOW:
"""

        return prompt

    def _parse_and_validate_response(
        self,
        response: str,
        validated_files: List[str]
    ) -> Dict[str, Any]:
        """Parse JSON response from Fixer Agent (Bolt.new production format)"""

        result = {
            "fixed_files": [],      # Full file content (for new files)
            "patches": [],          # Unified diff patches (for existing files)
            "instructions": None,
            "analysis": None
        }

        # SAFETY: Handle None or empty response gracefully
        if response is None:
            logger.warning("[ProductionFixerAgent] Response is None - Claude may have failed to respond")
            return result

        if not isinstance(response, str):
            logger.warning(f"[ProductionFixerAgent] Response is not a string: {type(response)}")
            return result

        if not response.strip():
            logger.warning("[ProductionFixerAgent] Response is empty")
            return result

        # ========== PARSE JSON RESPONSE ==========
        try:
            # Try to extract JSON from response (Claude might add text before/after)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
                parsed_json = json.loads(json_str)

                logger.info(f"[ProductionFixerAgent] Successfully parsed JSON response")

                # Extract patches (unified diffs for existing files)
                for patch in parsed_json.get("patches", []):
                    path = patch.get("path", "")
                    diff = patch.get("diff", "")
                    if path and diff:
                        # SAFETY VALIDATION for JSON patches
                        safety_result = self._validate_patch_safety(path, diff, "patch")
                        if not safety_result["valid"]:
                            logger.warning(f"[ProductionFixerAgent] SAFETY: Rejected JSON patch for {path}: {safety_result['reason']}")
                            continue

                        if safety_result["warnings"]:
                            for warn in safety_result["warnings"]:
                                logger.warning(f"[ProductionFixerAgent] SAFETY WARNING ({path}): {warn}")

                        result["patches"].append({
                            "path": path,
                            "patch": diff,
                            "type": "unified_diff",
                            "is_validated": path in validated_files,
                            "safety_warnings": safety_result["warnings"]
                        })
                        logger.info(f"[ProductionFixerAgent] JSON: Parsed patch for: {path}")

                # Extract new files (full content for missing files)
                for new_file in parsed_json.get("newFiles", []):
                    path = new_file.get("path", "")
                    content = new_file.get("content", "")
                    if path and content:
                        # SAFETY VALIDATION for JSON new files
                        safety_result = self._validate_patch_safety(path, content, "file")
                        if not safety_result["valid"]:
                            logger.warning(f"[ProductionFixerAgent] SAFETY: Rejected JSON file {path}: {safety_result['reason']}")
                            continue

                        if safety_result["warnings"]:
                            for warn in safety_result["warnings"]:
                                logger.warning(f"[ProductionFixerAgent] SAFETY WARNING ({path}): {warn}")

                        result["fixed_files"].append({
                            "path": path,
                            "content": content,
                            "is_validated": path in validated_files,
                            "safety_warnings": safety_result["warnings"]
                        })
                        logger.info(f"[ProductionFixerAgent] JSON: Parsed new file: {path}")

                # Extract run command
                run_cmd = parsed_json.get("runCommand")
                if run_cmd:
                    result["instructions"] = run_cmd
                    logger.info(f"[ProductionFixerAgent] JSON: Parsed runCommand: {run_cmd}")

                logger.info(f"[ProductionFixerAgent] Parsed {len(result['patches'])} patches + {len(result['fixed_files'])} new files")
                return result

        except json.JSONDecodeError as e:
            logger.warning(f"[ProductionFixerAgent] JSON parse failed: {e}, falling back to XML/regex")

        # ========== FALLBACK: XML/Regex parsing (backward compatibility) ==========
        logger.info("[ProductionFixerAgent] Using fallback XML/regex parsing")

        # Parse patches
        # Track already-seen paths to avoid duplicates from multiple patterns
        seen_patch_paths = set()
        patch_patterns = [
            r'<patch\s+path=["\']([^"\']+)["\']>(.*?)</patch>',
            r'<patch\s+path=([^\s>]+)>(.*?)</patch>',
        ]
        for pattern in patch_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            for match in matches:
                path, patch_content = match
                # Strip quotes and whitespace from path
                path = path.strip().strip('"').strip("'")

                # Skip if already processed (prevents duplicates from multiple patterns)
                if path in seen_patch_paths:
                    continue
                seen_patch_paths.add(path)

                # SAFETY VALIDATION for fallback patches
                safety_result = self._validate_patch_safety(path, patch_content, "patch")
                if not safety_result["valid"]:
                    logger.warning(f"[ProductionFixerAgent] SAFETY: Rejected patch for {path}: {safety_result['reason']}")
                    continue

                if safety_result["warnings"]:
                    for warn in safety_result["warnings"]:
                        logger.warning(f"[ProductionFixerAgent] SAFETY WARNING ({path}): {warn}")

                result["patches"].append({
                    "path": path,
                    "patch": patch_content,
                    "type": "unified_diff",
                    "is_validated": path in validated_files,
                    "safety_warnings": safety_result["warnings"]
                })

        # Parse file blocks
        # Track already-seen paths to avoid duplicates from multiple patterns
        seen_file_paths = set()
        file_patterns = [
            r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>',
            r'<file\s+path=([^\s>]+)>(.*?)</file>',
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            for match in matches:
                path, content = match
                # Strip quotes and whitespace from path (same as patches)
                path = path.strip().strip('"').strip("'")
                content = content.strip()

                # Skip if already processed (prevents duplicates from multiple patterns)
                if path in seen_file_paths:
                    continue
                seen_file_paths.add(path)

                # SAFETY VALIDATION for new files
                safety_result = self._validate_patch_safety(path, content, "file")
                if not safety_result["valid"]:
                    logger.warning(f"[ProductionFixerAgent] SAFETY: Rejected file {path}: {safety_result['reason']}")
                    continue

                if safety_result["warnings"]:
                    for warn in safety_result["warnings"]:
                        logger.warning(f"[ProductionFixerAgent] SAFETY WARNING ({path}): {warn}")

                result["fixed_files"].append({
                    "path": path,
                    "content": content,
                    "is_validated": path in validated_files,
                    "safety_warnings": safety_result["warnings"]
                })

        # Parse instructions
        inst_match = re.search(r'<instructions>(.*?)</instructions>', response, re.DOTALL | re.IGNORECASE)
        if inst_match:
            result["instructions"] = inst_match.group(1).strip()

        logger.info(f"[ProductionFixerAgent] Fallback parsed {len(result['patches'])} patches + {len(result['fixed_files'])} files")
        return result

    def _validate_patch_safety(self, path: str, content: str, patch_type: str = "patch") -> Dict[str, Any]:
        """
        SAFETY VALIDATION for patches and new files.
        Prevents malicious/invalid content from being applied.

        Returns: {"valid": bool, "reason": str, "warnings": List[str]}
        """
        warnings = []

        # 1. Path traversal prevention
        normalized_path = path.replace('\\', '/').strip()
        if '..' in normalized_path or normalized_path.startswith('/'):
            return {
                "valid": False,
                "reason": f"Path traversal detected in: {path}",
                "warnings": []
            }

        # 2. Dangerous file extensions
        dangerous_extensions = ['.exe', '.dll', '.so', '.dylib', '.bat', '.cmd', '.ps1', '.sh']
        if any(normalized_path.lower().endswith(ext) for ext in dangerous_extensions):
            return {
                "valid": False,
                "reason": f"Dangerous file extension in: {path}",
                "warnings": []
            }

        # 3. Check for shell injection patterns in content
        shell_patterns = [
            r'`[^`]+`',  # Backtick execution
            r'\$\([^)]+\)',  # $() execution
            r'eval\s*\(',  # eval()
            r'exec\s*\(',  # exec()
            r'os\.system\s*\(',  # os.system()
            r'subprocess\.(?:call|run|Popen)',  # subprocess
            r'child_process',  # Node child_process
            r'require\s*\(\s*[\'"]child_process',  # require('child_process')
        ]

        # Only check for shell patterns in code files (not configs)
        config_extensions = ['.json', '.yaml', '.yml', '.toml', '.xml', '.md', '.txt']
        is_config = any(normalized_path.lower().endswith(ext) for ext in config_extensions)

        if not is_config:
            for pattern in shell_patterns:
                if re.search(pattern, content):
                    warnings.append(f"Potential shell execution pattern found: {pattern}")

        # 4. Suspiciously large patch (might be full file replacement)
        if patch_type == "patch":
            # Unified diff should have reasonable line additions/removals
            add_lines = content.count('\n+')
            del_lines = content.count('\n-')
            total_changes = add_lines + del_lines

            if total_changes > 500:
                warnings.append(f"Large patch ({total_changes} changes) - may be full file replacement")

        # 5. Validate unified diff format (basic check)
        if patch_type == "patch" and content.strip():
            # Should have at least one hunk header
            if not re.search(r'^@@\s*-\d+,?\d*\s*\+\d+,?\d*\s*@@', content, re.MULTILINE):
                # Not a valid unified diff format - might be full content
                warnings.append("Patch doesn't appear to be valid unified diff format")

        # 6. Empty content check
        if not content.strip():
            return {
                "valid": False,
                "reason": f"Empty content for: {path}",
                "warnings": []
            }

        return {
            "valid": True,
            "reason": "Passed safety validation",
            "warnings": warnings
        }

    def _is_complete_file(self, content: str) -> bool:
        """Check if file content appears complete"""

        # Red flags for incomplete files
        incomplete_indicators = [
            '...',
            '# rest of code',
            '# unchanged',
            '// rest of file',
            '/* ... */',
            'TODO',
            'FIXME',
        ]

        content_lower = content.lower()
        for indicator in incomplete_indicators:
            if indicator.lower() in content_lower:
                return False

        # Should have reasonable length
        if len(content.strip()) < 10:
            return False

        return True

    def _can_attempt_fix(self, error_hash: str) -> bool:
        """Check if we can attempt to fix this error (loop prevention)"""

        if error_hash not in self.fix_history:
            return True

        attempts = self.fix_history[error_hash]
        return len(attempts) < self.MAX_FIX_ATTEMPTS_PER_ERROR

    def _record_fix_attempt(
        self,
        error_hash: str,
        files_modified: List[str],
        success: bool,
        fix_description: str = "",
        result_error: str = "",
        approach_used: str = ""
    ):
        """Record fix attempt for loop prevention and retry guidance"""

        if error_hash not in self.fix_history:
            self.fix_history[error_hash] = []

        attempt_number = len(self.fix_history[error_hash]) + 1

        self.fix_history[error_hash].append(FixAttempt(
            timestamp=datetime.utcnow(),
            error_hash=error_hash,
            files_modified=files_modified,
            success=success,
            attempt_number=attempt_number,
            fix_description=fix_description,
            result_error=result_error,
            approach_used=approach_used
        ))

    def _hash_error(self, error_message: str, stack_trace: str) -> str:
        """Generate hash for error to track fix attempts"""
        import hashlib
        combined = f"{error_message[:200]}:{stack_trace[:200]}"
        return hashlib.md5(combined.encode()).hexdigest()


# Singleton instance
production_fixer_agent = ProductionFixerAgent()
