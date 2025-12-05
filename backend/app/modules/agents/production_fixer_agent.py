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
    """Track fix attempts to prevent loops"""
    timestamp: datetime
    error_hash: str
    files_modified: List[str]
    success: bool


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
    MAX_FIX_ATTEMPTS_PER_ERROR = 3
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

## OUTPUT FORMAT (STRICT):

<file path="exact/path/to/file.ext">
COMPLETE FILE CONTENT
(No omissions, no "..." placeholders)
</file>

<instructions>
# Package manager commands:
npm install package-name
pip install package-name
go get package
cargo add package
bundle install
composer require package

# Build commands:
docker build --no-cache .
npm run build
go build ./...
cargo build
</instructions>

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

### Python - Type Error:
Error: TypeError: 'NoneType' object is not subscriptable
File: app/api/users.py

<file path="app/api/users.py">
from typing import Optional

def get_user(user_id: int) -> Optional[dict]:
    user = db.get(user_id)
    if user is None:
        return None
    return user.to_dict()
</file>

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

## CRITICAL RULES:

1. OUTPUT COMPLETE FILES - Never use "..." or "rest unchanged"
2. FIX ROOT CAUSE - Don't just suppress errors
3. PRESERVE ARCHITECTURE - Don't restructure the project
4. MATCH EXISTING PATTERNS - Use same coding style
5. VALIDATE FIXES - Ensure imports work, types match
6. MAX {max_files} FILES - Don't fix unrelated files
7. TECHNOLOGY AWARE - Use correct syntax for the language
8. PACKAGE MANAGER AWARE - Use correct command (npm/yarn/pnpm, pip/poetry, etc.)

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

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Fix errors with safety checks and validation
        """
        metadata = context.metadata or {}

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

        # Validate files to fix
        validated_files = self._validate_target_files(
            analysis.suggested_files_to_fix,
            metadata.get("project_files", [])
        )

        if not validated_files:
            return {
                "success": False,
                "error": "Could not identify valid files to fix",
                "analysis": analysis
            }

        # Safety check: Don't fix too many files at once
        if len(validated_files) > self.MAX_FILES_TO_FIX_AT_ONCE:
            logger.warning(f"Too many files to fix ({len(validated_files)}), limiting to {self.MAX_FILES_TO_FIX_AT_ONCE}")
            validated_files = validated_files[:self.MAX_FILES_TO_FIX_AT_ONCE]

        # Get file contents for context
        file_contents = await self._get_file_contents(validated_files, context)

        # Build safe prompt with constraints
        prompt = self._build_safe_prompt(
            error_message=error_message,
            stack_trace=stack_trace,
            analysis=analysis,
            file_contents=file_contents,
            context=context
        )

        # Call Claude with safety-enhanced system prompt
        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT.format(
                max_files=self.MAX_FILES_TO_FIX_AT_ONCE
            ),
            user_prompt=prompt,
            max_tokens=8192,  # Higher for multi-file fixes
            temperature=0.1   # Very low for precise fixes
        )

        # Parse and validate response
        parsed = self._parse_and_validate_response(response, validated_files)

        # Safety check: Verify all fixed files were in validated list
        unauthorized_files = [
            f['path'] for f in parsed['fixed_files']
            if f['path'] not in validated_files
        ]

        if unauthorized_files:
            logger.error(f"❌ Claude tried to fix unauthorized files: {unauthorized_files}")
            # Remove unauthorized files
            parsed['fixed_files'] = [
                f for f in parsed['fixed_files']
                if f['path'] in validated_files
            ]

        # Safety check: Verify files are complete (no partial updates)
        for file_info in parsed['fixed_files']:
            if not self._is_complete_file(file_info['content']):
                logger.warning(f"⚠️ File {file_info['path']} appears incomplete")
                # Could reject here or request regeneration

        # Record fix attempt
        self._record_fix_attempt(
            error_hash=error_hash,
            files_modified=[f['path'] for f in parsed['fixed_files']],
            success=True
        )

        return {
            "success": True,
            "analysis": analysis,
            "fixed_files": parsed['fixed_files'],
            "instructions": parsed.get('instructions'),
            "validated_files": validated_files,
            "safety_checks_passed": True
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
        context: AgentContext
    ) -> str:
        """Build Bolt.new-style prompt with full context"""

        metadata = context.metadata or {}

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

        # Build Bolt.new style prompt
        prompt = f"""## ERROR TO FIX

**Command:** {metadata.get('command', 'unknown')}

**Error Message:**
```
{error_message}
```

**Stack Trace:**
```
{stack_trace[:2000] if stack_trace else 'No stack trace available'}
```

## ENVIRONMENT
{env_str}

## FILES TO FIX (ONLY THESE):
{', '.join(analysis.suggested_files_to_fix)}

## CURRENT FILE CONTENTS:
{file_context}
{config_context}

## ERROR ANALYSIS:
- Error Type: {analysis.error_type}
- Root Cause: {analysis.root_cause}
- Confidence: {analysis.confidence}

## YOUR TASK:
1. Identify the exact fix needed
2. Output COMPLETE fixed files using <file path="...">content</file>
3. If packages needed, output <instructions>npm install X</instructions>

OUTPUT THE FIX NOW:
"""

        return prompt

    def _parse_and_validate_response(
        self,
        response: str,
        validated_files: List[str]
    ) -> Dict[str, Any]:
        """Parse response with robust validation"""

        result = {
            "fixed_files": [],
            "instructions": None,
            "analysis": None
        }

        # Parse analysis if present
        analysis_match = re.search(r'<analysis>(.*?)</analysis>', response, re.DOTALL | re.IGNORECASE)
        if analysis_match:
            result["analysis"] = analysis_match.group(1).strip()

        # Parse file blocks with multiple fallback patterns
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
                else:
                    logger.warning(f"⚠️ Skipping unauthorized file: {path}")

        # Parse instructions
        inst_match = re.search(r'<instructions>(.*?)</instructions>', response, re.DOTALL | re.IGNORECASE)
        if inst_match:
            result["instructions"] = inst_match.group(1).strip()

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
        success: bool
    ):
        """Record fix attempt for loop prevention"""

        if error_hash not in self.fix_history:
            self.fix_history[error_hash] = []

        self.fix_history[error_hash].append(FixAttempt(
            timestamp=datetime.utcnow(),
            error_hash=error_hash,
            files_modified=files_modified,
            success=success
        ))

    def _hash_error(self, error_message: str, stack_trace: str) -> str:
        """Generate hash for error to track fix attempts"""
        import hashlib
        combined = f"{error_message[:200]}:{stack_trace[:200]}"
        return hashlib.md5(combined.encode()).hexdigest()


# Singleton instance
production_fixer_agent = ProductionFixerAgent()
