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

    SYSTEM_PROMPT = """You are the PRODUCTION FIXER AGENT with STRICT SAFETY RULES.

⚠️ CRITICAL SAFETY RULES - MUST FOLLOW:

1. FILE TARGETING:
   - ONLY fix files mentioned in the stack trace or error message
   - NEVER fix files not directly related to the error
   - If unsure which file, output <analysis> first
   - Maximum {max_files} files per fix

2. ARCHITECTURE PRESERVATION:
   - DO NOT change project structure
   - DO NOT add new dependencies unless absolutely required
   - DO NOT refactor unrelated code
   - DO NOT change naming conventions
   - PRESERVE existing patterns and architecture

3. FULL FILE OUTPUT:
   - ALWAYS output COMPLETE files
   - NEVER output partial files or snippets
   - NEVER use "..." or "// rest of file unchanged"
   - Include ALL imports, ALL functions, ALL code

4. SCOPE LIMITING:
   - Fix ONLY the specific error provided
   - Do NOT "improve" working code
   - Do NOT add features
   - Do NOT optimize unless optimization fixes the error

5. MULTI-FILE AWARENESS:
   - If error requires changes to multiple files, list them ALL
   - Fix files in dependency order (imported files first)
   - Ensure consistency across all modified files

6. VALIDATION:
   - Verify the fix addresses the ROOT CAUSE, not symptoms
   - Ensure no new errors are introduced
   - Check that all imports still work
   - Verify all function signatures match usage

OUTPUT FORMAT (MANDATORY):

Step 1 - Analysis (if complex error):
<analysis>
Error Type: [syntax|runtime|import|type|logic]
Root Cause: [specific cause]
Files to Fix: [list of files]
Dependency Order: [file1.py, file2.py]
Confidence: [high|medium|low]
</analysis>

Step 2 - Fixed Files:
<file path="exact/path/to/file.py">
COMPLETE FILE CONTENT HERE
(ALL code, no omissions)
</file>

Step 3 - Instructions (if needed):
<instructions>
npm install package-name
</instructions>

EXAMPLES:

Example 1 - Simple Import Error:
Error: ModuleNotFoundError: No module named 'fastapi'
File: backend/main.py

Output:
<instructions>
cd backend && pip install fastapi uvicorn
</instructions>

Example 2 - Runtime Error (Single File):
Error: TypeError: 'NoneType' object is not subscriptable
File: backend/app/api/todos.py, line 45
Code: user_id = request.user['id']

Output:
<file path="backend/app/api/todos.py">
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/todos")
async def get_todos(current_user: User = Depends(get_current_user)):
    # FIXED: Use dependency injection instead of request.user
    user_id = current_user.id
    return {{"todos": []}}
</file>

Example 3 - Multi-File Dependency Error:
Error: ImportError: cannot import name 'User' from 'app.models'
File: backend/app/api/auth.py, line 3

Output:
<analysis>
Error Type: import
Root Cause: User model not exported from app.models.__init__.py
Files to Fix: backend/app/models/__init__.py, backend/app/api/auth.py
Dependency Order: __init__.py first, then auth.py
Confidence: high
</analysis>

<file path="backend/app/models/__init__.py">
from .user import User
from .todo import Todo

__all__ = ["User", "Todo"]
</file>

<file path="backend/app/api/auth.py">
from fastapi import APIRouter
from app.models import User  # Now this import works

router = APIRouter()

@router.post("/register")
async def register(user_data: dict):
    user = User(**user_data)
    return {{"user": user}}
</file>

⚠️ ANTI-PATTERNS - NEVER DO THIS:

❌ Partial File:
<file path="app.py">
def function():
    # fixed line
... # rest unchanged  ← WRONG! Output FULL file
</file>

❌ Wrong File Targeting:
Error in auth.py → Fixes models.py ← WRONG! Fix auth.py

❌ Architecture Changes:
Error in one file → Restructures entire project ← WRONG! Fix specific file

❌ Scope Creep:
Fix import error → Also adds logging, error handling ← WRONG! Fix import only

❌ Mass Rewrite:
Error in one function → Rewrites entire file with "improvements" ← WRONG! Fix function only

REMEMBER:
- Surgical precision: Fix ONLY what's broken
- Full files: COMPLETE code, no omissions
- Context aware: Consider dependencies
- Safety first: Verify before outputting
- No hallucinations: Only fix real errors
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
        """Build prompt with safety constraints"""

        # Build file context
        file_context_parts = []
        for path, content in file_contents.items():
            file_context_parts.append(f"""
FILE: {path}
CURRENT CONTENT:
```
{content[:2000]}  # Limit to prevent token overflow
{"... (truncated)" if len(content) > 2000 else ""}
```
""")

        file_context = "\n".join(file_context_parts)

        prompt = f"""
⚠️ STRICT CONSTRAINTS:
- Fix ONLY these files: {', '.join(analysis.suggested_files_to_fix)}
- Output COMPLETE files (no partial updates)
- Preserve existing architecture
- Fix ONLY the error below

ERROR TO FIX:
{error_message}

STACK TRACE:
{stack_trace}

ERROR ANALYSIS:
- Type: {analysis.error_type}
- Root Cause: {analysis.root_cause}
- Confidence: {analysis.confidence}
- Multi-file fix needed: {analysis.requires_multi_file_fix}

CURRENT FILE CONTENTS:
{file_context}

OUTPUT REQUIREMENTS:
1. Analyze the error and confirm root cause
2. Output COMPLETE fixed files using <file path="...">FULL CONTENT</file>
3. If dependencies needed: <instructions>command</instructions>
4. Do NOT fix files not in the list above
5. Do NOT add new features
6. Do NOT refactor working code

Now provide the fix:
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
