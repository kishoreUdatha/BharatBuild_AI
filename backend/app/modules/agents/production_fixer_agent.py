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

## OUTPUT FORMAT (HYBRID - Bolt.new Style):

### FOR EXISTING FILES - Use UNIFIED DIFF (minimal, fast):
<patch path="exact/path/to/file.ext">
--- a/exact/path/to/file.ext
+++ b/exact/path/to/file.ext
@@ -5,7 +5,8 @@
 import React from 'react';
-import { Button } from './Button';
+import { Button } from './components/Button';
+import { Header } from './components/Header';

 function App() {
</patch>

### FOR NEW/MISSING FILES - Use FULL FILE:
<file path="config/newfile.json">
COMPLETE FILE CONTENT
</file>

### FOR PACKAGE COMMANDS:
<instructions>
npm install package-name
pip install package-name
go get package
</instructions>

## DIFF FORMAT RULES:
1. Use unified diff format (like git diff)
2. Include @@ hunk headers with line numbers
3. Lines starting with '-' are REMOVED
4. Lines starting with '+' are ADDED
5. Lines starting with ' ' (space) are CONTEXT
6. Keep 3 lines of context around changes
7. Multiple hunks allowed for multiple changes in same file

## EXAMPLES BY TECHNOLOGY:

### JavaScript - Missing Module:
Error: Cannot find module 'express'

<instructions>
npm install express
</instructions>

### Python - Import Error:
Error: ModuleNotFoundError: No module named 'fastapi'

<instructions>
pip install fastapi uvicorn
</instructions>

### Python - Type Error (UNIFIED DIFF for existing file):
Error: TypeError: 'NoneType' object is not subscriptable
File: app/api/users.py

<patch path="app/api/users.py">
--- a/app/api/users.py
+++ b/app/api/users.py
@@ -1,8 +1,12 @@
+from typing import Optional
+
 def get_user(user_id: int):
     user = db.get(user_id)
-    return user.to_dict()
+    if user is None:
+        return None
+    return user.to_dict()
</patch>

### Go - Import Error:
Error: cannot find package "github.com/gin-gonic/gin"

<instructions>
go get github.com/gin-gonic/gin
go mod tidy
</instructions>

### Rust - Borrow Error:
Error: cannot borrow `x` as mutable because it is also borrowed as immutable

<file path="src/main.rs">
fn main() {{
    let mut x = vec![1, 2, 3];
    // Fixed: Use clone or reorganize borrows
    let y = x.clone();
    x.push(4);
    println!("{{:?}} {{:?}}", x, y);
}}
</file>

### Docker - Build Error:
Error: npm ERR! could not determine executable to run

<file path="Dockerfile">
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host"]
</file>

### Docker Compose - Port Conflict:
Error: Port 3000 already in use

<file path="docker-compose.yml">
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5173:5173"
    environment:
      - PORT=5173
</file>

### Django - Migration Error:
Error: django.db.utils.OperationalError: no such table

<instructions>
python manage.py makemigrations
python manage.py migrate
</instructions>

### Rails - Gem Error:
Error: Could not find gem 'rails'

<instructions>
bundle install
</instructions>

### Java/Spring - Build Error:
Error: package org.springframework.boot does not exist

<file path="pom.xml">
<!-- Add Spring Boot parent and dependencies -->
</file>

<instructions>
mvn clean install
</instructions>

### Flutter - Build Error:
Error: Cannot run with sound null safety

<file path="pubspec.yaml">
environment:
  sdk: ">=2.12.0 <3.0.0"
</file>

<instructions>
flutter pub get
</instructions>

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

1. EXISTING FILES → Use <patch> with unified diff (minimal changes)
2. NEW/MISSING FILES → Use <file> with complete content
3. FIX ROOT CAUSE - Don't just suppress errors
4. PRESERVE ARCHITECTURE - Don't restructure the project
5. MATCH EXISTING PATTERNS - Use same coding style
6. VALIDATE FIXES - Ensure imports work, types match
7. MAX {max_files} FILES - Don't fix unrelated files
8. TECHNOLOGY AWARE - Use correct syntax for the language
9. PACKAGE MANAGER AWARE - Use correct command (npm/yarn/pnpm, pip/poetry, etc.)
10. MINIMAL CHANGES - Only change what's necessary to fix the error
11. ON RETRY - Try a DIFFERENT approach than what failed before

## WHY YOU SUCCEED:
- You receive EXACT error logs
- You receive EXACT file contents
- You understand the project context
- You support ALL major technologies
- You generate precise, complete fixes
- The system auto-applies your patches
- The system auto-reruns after fix

Be surgical. Fix only what's broken. Output complete files.
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

        # Extract error information
        error_message = metadata.get("error_message", "")
        stack_trace = metadata.get("stack_trace", "")

        # Generate error hash for loop detection
        error_hash = self._hash_error(error_message, stack_trace)

        # Check if we've tried to fix this error too many times
        if not self._can_attempt_fix(error_hash):
            return {
                "success": False,
                "error": f"Maximum fix attempts ({self.MAX_FIX_ATTEMPTS_PER_ERROR}) reached for this error",
                "suggestion": "Manual intervention required"
            }

        # Analyze error first
        analysis = await self._analyze_error(
            error_message=error_message,
            stack_trace=stack_trace,
            context=context
        )

        # Check if this is a MISSING FILE error (ENOENT, "no such file", etc.)
        missing_file_patterns = [
            r'ENOENT.*?["\']([^"\']+)["\']',
            r'Failed to resolve config file.*?["\']([^"\']+)["\']',
            r'no such file.*?["\']([^"\']+)["\']',
            r"Cannot find.*?'([^']+)'",
            r'Module not found.*?["\']([^"\']+)["\']',
        ]

        missing_files = []
        for pattern in missing_file_patterns:
            matches = re.findall(pattern, error_message, re.IGNORECASE)
            missing_files.extend(matches)

        # Also check stack trace for missing files
        for pattern in missing_file_patterns:
            matches = re.findall(pattern, stack_trace, re.IGNORECASE)
            missing_files.extend(matches)

        missing_files = list(set(missing_files))
        is_missing_file_error = len(missing_files) > 0

        if is_missing_file_error:
            logger.info(f"🔍 Detected MISSING FILE error: {missing_files}")

        # Validate files to fix (existing files)
        validated_files = self._validate_target_files(
            analysis.suggested_files_to_fix,
            metadata.get("project_files", [])
        )

        # For missing file errors, allow creating new files even if they don't exist
        allowed_new_files = []
        if is_missing_file_error:
            # Common config files that are safe to create
            safe_new_files = [
                'tsconfig.node.json', 'tsconfig.json', 'tsconfig.app.json',
                'postcss.config.js', 'postcss.config.cjs', 'postcss.config.mjs',
                'tailwind.config.js', 'tailwind.config.cjs', 'tailwind.config.ts',
                'vite.config.ts', 'vite.config.js',
                '.env', '.env.local', '.env.example',
                'next.config.js', 'next.config.mjs',
                'eslint.config.js', '.eslintrc.js', '.eslintrc.json',
                'jest.config.js', 'vitest.config.ts',
            ]

            for missing in missing_files:
                # Extract just the filename
                filename = missing.split('/')[-1].split('\\')[-1]
                if filename in safe_new_files or missing.endswith(('.json', '.js', '.ts', '.mjs', '.cjs')):
                    allowed_new_files.append(missing)
                    logger.info(f"✅ Allowing creation of missing file: {missing}")

        if not validated_files and not allowed_new_files:
            return {
                "success": False,
                "error": "Could not identify valid files to fix or create",
                "analysis": analysis
            }

        # Safety check: Don't fix too many files at once
        all_allowed_files = list(set(validated_files + allowed_new_files))
        if len(all_allowed_files) > self.MAX_FILES_TO_FIX_AT_ONCE:
            logger.warning(f"Too many files ({len(all_allowed_files)}), limiting to {self.MAX_FILES_TO_FIX_AT_ONCE}")
            all_allowed_files = all_allowed_files[:self.MAX_FILES_TO_FIX_AT_ONCE]

        # Get file contents for context (existing files only)
        file_contents = await self._get_file_contents(validated_files, context)

        # Get previous attempts context for retry guidance
        previous_attempts_context = self._get_previous_attempts_context(error_hash)
        attempt_number = len(self.fix_history.get(error_hash, [])) + 1

        # Build safe prompt with constraints
        prompt = self._build_safe_prompt(
            error_message=error_message,
            stack_trace=stack_trace,
            analysis=analysis,
            file_contents=file_contents,
            context=context,
            allowed_new_files=allowed_new_files,  # Pass allowed new files
            previous_attempts_context=previous_attempts_context,  # Pass retry context
            attempt_number=attempt_number
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

        # Parse and validate response (allow new files too)
        parsed = self._parse_and_validate_response(response, all_allowed_files)

        # Safety check: Verify all fixed files were in validated or allowed list
        unauthorized_files = [
            f['path'] for f in parsed['fixed_files']
            if f['path'] not in all_allowed_files
        ]

        if unauthorized_files:
            logger.error(f"❌ Claude tried to fix unauthorized files: {unauthorized_files}")
            parsed['fixed_files'] = [
                f for f in parsed['fixed_files']
                if f['path'] in all_allowed_files
            ]

        # Safety check: Verify files are complete (no partial updates)
        for file_info in parsed['fixed_files']:
            if not self._is_complete_file(file_info['content']):
                logger.warning(f"⚠️ File {file_info['path']} appears incomplete")

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
            "validated_files": validated_files,
            "new_files_created": [f for f in parsed['fixed_files'] if f['path'] in allowed_new_files],
            "safety_checks_passed": True,
            "attempt_number": attempt_number  # Include attempt number in response
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

        logger.info(f"📁 Extracted {len(files)} files from stack trace: {files}")
        return files

    def _extract_files_from_error(self, error_message: str) -> List[str]:
        """Extract file paths mentioned in error message"""
        files = []

        # Common patterns in error messages
        patterns = [
            r'in\s+([\w/\\.]+\.[\w]+)',
            r'from\s+([\w/\\.]+\.[\w]+)',
            r'module\s+["\']?([\w/\\.]+)["\']?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, error_message)
            files.extend(matches)

        return list(set(files))

    def _classify_error(self, error_message: str) -> str:
        """Classify error type"""
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
                logger.warning(f"⚠️ File content not provided for {path}")
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
        attempt_number: int = 1
    ) -> str:
        """Build Bolt.new-style prompt with full context and retry info"""

        metadata = context.metadata or {}
        allowed_new_files = allowed_new_files or []

        # Build file context section (Bolt.new style)
        file_context_parts = []
        for path, content in file_contents.items():
            # Limit file size but keep complete enough for context
            truncated = len(content) > 3000
            file_context_parts.append(f"""
=== {path} ===
{content[:3000]}{"... (truncated)" if truncated else ""}
""")

        file_context = "\n".join(file_context_parts)

        # Get additional config files from metadata
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

        # Build section for new files that can be created
        new_files_section = ""
        if allowed_new_files:
            new_files_section = f"""
## FILES YOU CAN CREATE (MISSING FILES):
{', '.join(allowed_new_files)}

For these missing config files, use these templates:

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

## FILES TO FIX (EXISTING):
{', '.join(analysis.suggested_files_to_fix) if analysis.suggested_files_to_fix else 'None identified'}
{new_files_section}

## CURRENT FILE CONTENTS:
{file_context if file_context.strip() else 'No existing files to show'}
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
        """Parse response with robust validation - supports HYBRID format"""

        result = {
            "fixed_files": [],      # Full file content (for new files)
            "patches": [],          # Unified diff patches (for existing files)
            "instructions": None,
            "analysis": None
        }

        # Parse analysis if present
        analysis_match = re.search(r'<analysis>(.*?)</analysis>', response, re.DOTALL | re.IGNORECASE)
        if analysis_match:
            result["analysis"] = analysis_match.group(1).strip()

        # ========== PARSE PATCHES (unified diff for existing files) ==========
        patch_patterns = [
            r'<patch\s+path=["\']([^"\']+)["\']>(.*?)</patch>',  # Standard
            r'<patch\s+path=([^\s>]+)>(.*?)</patch>',             # Unquoted
        ]

        for pattern in patch_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            for match in matches:
                path, patch_content = match
                path = path.strip()
                patch_content = patch_content.strip()

                # Only add if path is in validated files
                if path in validated_files:
                    result["patches"].append({
                        "path": path,
                        "patch": patch_content,
                        "type": "unified_diff"
                    })
                    logger.info(f"📝 Parsed unified diff patch for: {path}")
                else:
                    logger.warning(f"⚠️ Skipping unauthorized patch: {path}")

        # ========== PARSE FILE BLOCKS (full content for new files) ==========
        file_patterns = [
            r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>',  # Standard
            r'<file\s+path=([^\s>]+)>(.*?)</file>',             # Unquoted
            r'```(\w+)\s+([\w/\\.]+)\s*\n(.*?)\n```',           # Markdown fallback
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if len(match) == 2:  # file path pattern
                    path, content = match
                elif len(match) == 3:  # markdown pattern
                    _, path, content = match
                else:
                    continue

                path = path.strip()
                content = content.strip()

                # Only add if path is in validated files
                if path in validated_files:
                    result["fixed_files"].append({
                        "path": path,
                        "content": content
                    })
                    logger.info(f"📄 Parsed full file content for: {path}")
                else:
                    logger.warning(f"⚠️ Skipping unauthorized file: {path}")

        # Parse instructions
        inst_match = re.search(r'<instructions>(.*?)</instructions>', response, re.DOTALL | re.IGNORECASE)
        if inst_match:
            result["instructions"] = inst_match.group(1).strip()

        logger.info(f"📊 Parsed {len(result['patches'])} patches + {len(result['fixed_files'])} full files")
        return result

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
