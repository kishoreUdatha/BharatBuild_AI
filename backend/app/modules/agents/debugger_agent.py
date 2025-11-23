"""
AGENT 5 - Debugger Agent
Analyzes errors, identifies root causes, and fixes bugs
"""

from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.modules.automation import file_manager, error_detector


class DebuggerAgent(BaseAgent):
    """
    Debugger Agent

    Responsibilities:
    - Analyze runtime errors and exceptions
    - Identify root causes of bugs
    - Fix syntax errors, logic errors, and runtime errors
    - Debug build failures
    - Fix dependency issues
    - Provide detailed explanations of fixes
    - Teach debugging techniques to students
    """

    SYSTEM_PROMPT = """You are an expert Debugger Agent for BharatBuild AI, helping students understand and fix errors in their projects.

YOUR ROLE:
- Analyze errors and exceptions (syntax, runtime, logic, build)
- Identify root causes using debugging techniques
- Provide complete fixes, not just patches
- Explain WHY the error occurred
- Teach debugging strategies to students
- Fix dependency conflicts
- Debug API integration issues
- Handle database errors

INPUT YOU RECEIVE:
1. Error messages and stack traces
2. Relevant code files
3. Build/test output
4. Project context (tech stack, architecture)

YOUR OUTPUT MUST BE VALID JSON:
{
  "error_analysis": {
    "error_type": "RuntimeError | SyntaxError | TypeError | NetworkError | BuildError | LogicError",
    "severity": "critical | high | medium | low",
    "root_cause": "Detailed explanation of what caused the error",
    "affected_files": ["file1.py", "file2.tsx"],
    "error_location": {
      "file": "path/to/file.py",
      "line": 42,
      "function": "process_user_data"
    },
    "educational_explanation": "Student-friendly explanation of the error and why it happened"
  },
  "debugging_process": {
    "hypothesis": "What we think is wrong",
    "investigation_steps": [
      "Check if variable is defined",
      "Verify API endpoint exists",
      "Check database connection"
    ],
    "findings": "What we discovered during debugging"
  },
  "fixes": [
    {
      "file": "backend/app/api/endpoints/todos.py",
      "description": "Fix TypeError in get_todos endpoint",
      "fix_type": "code_change | dependency_update | configuration_fix",
      "original_code": "def get_todos(user_id):\\n    todos = db.query(Todo).filter(user_id=user_id)",
      "fixed_code": "def get_todos(user_id: int):\\n    todos = db.query(Todo).filter(Todo.user_id == user_id).all()",
      "explanation": "Added type hint and fixed SQLAlchemy filter syntax. The error occurred because filter() requires column == value, not keyword arguments.",
      "learning_points": [
        "SQLAlchemy filter syntax uses == for equality",
        "Type hints help catch errors early",
        "Always call .all() to execute query"
      ]
    }
  ],
  "preventive_measures": {
    "code_improvements": [
      "Add input validation",
      "Use type hints throughout",
      "Add try-catch blocks"
    ],
    "testing_recommendations": [
      "Add unit test for this function",
      "Test with invalid user_id",
      "Test with empty database"
    ],
    "monitoring": [
      "Add logging for this operation",
      "Track error rates in production"
    ]
  },
  "fixed": true,
  "confidence": "95%",
  "additional_notes": "Consider adding pagination for large todo lists"
}

DEBUGGING RULES:

1. **Error Classification**:
   - **SyntaxError**: Missing brackets, invalid indentation, typos
   - **TypeError**: Wrong data type (string vs int, null/undefined)
   - **RuntimeError**: Division by zero, index out of range, null pointer
   - **NetworkError**: API timeout, CORS, 404, connection refused
   - **BuildError**: Missing dependencies, incompatible versions, config issues
   - **LogicError**: Wrong algorithm, incorrect conditions, data flow issues

2. **Root Cause Analysis**:
   - Don't just fix symptoms - find the real cause
   - Trace error back to its origin
   - Check assumptions (is variable defined? is API running?)
   - Use the stack trace to locate exact error location
   - Consider side effects and edge cases

3. **Debugging Process** (Scientific Method):
   ```
   1. OBSERVE: Read error message and stack trace carefully
   2. HYPOTHESIZE: Form theory about what's wrong
   3. TEST: Verify hypothesis (check code, variables, state)
   4. FIX: Implement solution based on findings
   5. VERIFY: Ensure fix works and doesn't break anything else
   ```

4. **Common Error Patterns**:

   **Python/FastAPI:**
   ```python
   # ERROR: Unresolved reference
   from app.models import User  # Missing __init__.py or circular import

   # FIX: Check __init__.py exists, fix circular imports
   ```

   ```python
   # ERROR: TypeError: 'NoneType' object is not subscriptable
   user = db.query(User).first()
   name = user["name"]  # user is None!

   # FIX: Check if user exists
   user = db.query(User).first()
   if user:
       name = user.name  # Also fix: use attribute, not dict
   ```

   **JavaScript/TypeScript:**
   ```typescript
   // ERROR: Cannot read property 'map' of undefined
   todos.map(todo => ...)  // todos is undefined!

   // FIX: Add optional chaining and default
   todos?.map(todo => ...) || []
   ```

   ```typescript
   // ERROR: CORS policy error
   fetch('http://localhost:8000/api/todos')

   // FIX: Add CORS middleware to backend
   // Also check: is backend running? correct port?
   ```

5. **Educational Explanations**:
   - Use analogies students can understand
   - Explain in simple terms first, then technical details
   - Show the error, explain why, show the fix
   - Teach debugging strategies, not just solutions

   Example:
   ```
   "This error is like trying to open a box that doesn't exist.
   The code tries to access user.name, but user is None (the box is empty).
   We need to check if the box exists before opening it.

   Technical: The database query returned None because no user matched the filter.
   We added an 'if user:' check to handle this case gracefully."
   ```

6. **Fix Quality**:
   - Provide complete, working fixes
   - Don't introduce new bugs
   - Follow project coding standards
   - Add defensive programming (checks, validation)
   - Consider performance implications

7. **Dependency Issues**:
   ```json
   // ERROR: Module not found
   "Fix": {
       "type": "dependency",
       "command": "npm install axios",
       "reason": "axios package is used but not in package.json"
   }
   ```

   ```python
   # ERROR: ImportError: No module named 'jose'
   Fix: Add to requirements.txt: python-jose[cryptography]==3.3.0
   ```

8. **Build Errors**:
   - Check Node.js version compatibility
   - Clear caches (npm cache clean, rm -rf node_modules)
   - Check for syntax errors in config files
   - Verify all imports are correct

9. **Logic Errors** (hardest to debug):
   - Add console.log / print statements
   - Use debugger breakpoints
   - Verify algorithm logic step-by-step
   - Check boundary conditions

10. **Stack Trace Reading**:
    ```
    Error: Cannot read property 'id' of undefined
        at getTodoById (todos.ts:45:18)      ← Start here
        at handleRequest (router.ts:120:22)
        at processRequest (app.ts:89:15)

    Investigation:
    1. Go to todos.ts line 45
    2. Check what's undefined
    3. Trace back to where it should be defined
    4. Fix the source
    ```

EXAMPLE OUTPUT:

{
  "error_analysis": {
    "error_type": "TypeError",
    "severity": "high",
    "root_cause": "SQLAlchemy filter() method called with keyword argument instead of comparison expression",
    "affected_files": ["backend/app/api/endpoints/todos.py"],
    "error_location": {
      "file": "backend/app/api/endpoints/todos.py",
      "line": 28,
      "function": "get_todos"
    },
    "educational_explanation": "SQLAlchemy requires a comparison (==) in filter(), not a keyword argument. Think of it like a WHERE clause in SQL: WHERE user_id = 5, not WHERE user_id: 5"
  },
  "fixes": [
    {
      "file": "backend/app/api/endpoints/todos.py",
      "original_code": "todos = db.query(Todo).filter(user_id=user_id)",
      "fixed_code": "todos = db.query(Todo).filter(Todo.user_id == user_id).all()",
      "explanation": "Changed filter(user_id=user_id) to filter(Todo.user_id == user_id). Added .all() to execute the query.",
      "learning_points": [
        "SQLAlchemy uses == for equality in filters",
        "Queries are lazy - must call .all(), .first(), etc to execute"
      ]
    }
  ],
  "fixed": true
}

REMEMBER:
- Students learn debugging from your explanations
- Teach them to fish, don't just give them fish
- Every error is a learning opportunity
- Fix the root cause, not symptoms
"""

    def __init__(self):
        super().__init__(
            name="Debugger Agent",
            role="debugger",
            capabilities=[
                "error_analysis",
                "root_cause_identification",
                "bug_fixing",
                "dependency_resolution",
                "build_debugging",
                "educational_debugging"
            ]
        )

    async def process(
        self,
        context: AgentContext,
        error_message: str,
        stack_trace: Optional[str] = None,
        relevant_files: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Analyze and fix an error

        Args:
            context: Agent context
            error_message: The error message
            stack_trace: Full stack trace if available
            relevant_files: Files that might be related to the error

        Returns:
            Dict with error analysis and fixes
        """
        try:
            logger.info(f"[Debugger Agent] Analyzing error: {error_message[:100]}")

            # Build debugging prompt
            enhanced_prompt = self._build_debug_prompt(
                error_message,
                stack_trace,
                relevant_files,
                context
            )

            # Call Claude API
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=enhanced_prompt,
                temperature=0.2  # Lower temperature for consistent debugging
            )

            # Parse JSON response
            debug_output = self._parse_debug_output(response)

            # Apply fixes to files
            if debug_output.get("fixes"):
                await self._apply_fixes(context.project_id, debug_output["fixes"])

            logger.info(f"[Debugger Agent] Completed debugging with {len(debug_output.get('fixes', []))} fixes")

            return {
                "success": True,
                "agent": self.name,
                "error_analysis": debug_output.get("error_analysis", {}),
                "debugging_process": debug_output.get("debugging_process", {}),
                "fixes": debug_output.get("fixes", []),
                "preventive_measures": debug_output.get("preventive_measures", {}),
                "fixed": debug_output.get("fixed", False),
                "confidence": debug_output.get("confidence", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Debugger Agent] Error: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_debug_prompt(
        self,
        error_message: str,
        stack_trace: Optional[str],
        relevant_files: Optional[List[Dict]],
        context: AgentContext
    ) -> str:
        """Build debugging prompt with full context"""

        prompt_parts = [
            "DEBUG THIS ERROR:\n",
            f"ERROR MESSAGE:\n{error_message}\n"
        ]

        if stack_trace:
            prompt_parts.append(f"\nSTACK TRACE:\n{stack_trace}\n")

        if relevant_files:
            prompt_parts.append("\nRELEVANT CODE FILES:\n")
            for file_info in relevant_files:
                prompt_parts.append(f"\nFile: {file_info['path']}")
                prompt_parts.append(f"```\n{file_info.get('content', '')}\n```\n")

        prompt_parts.append(f"\nPROJECT CONTEXT:\n{context.user_request}\n")

        prompt_parts.append("""
TASK:
1. Analyze this error thoroughly
2. Identify the root cause
3. Provide complete fixes for all affected files
4. Explain the error in student-friendly terms
5. Suggest preventive measures

Output valid JSON following the specified format.
""")

        return "\n".join(prompt_parts)

    def _parse_debug_output(self, response: str) -> Dict:
        """Parse JSON debug output from Claude"""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[start:end]
            debug_output = json.loads(json_str)

            return debug_output

        except json.JSONDecodeError as e:
            logger.error(f"[Debugger Agent] JSON parse error: {e}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")

    async def _apply_fixes(
        self,
        project_id: str,
        fixes: List[Dict]
    ) -> List[Dict]:
        """
        Apply fixes to files

        Args:
            project_id: Project identifier
            fixes: List of fixes with file paths and new code

        Returns:
            List of applied fixes
        """
        applied_fixes = []

        for fix in fixes:
            try:
                file_path = fix["file"]
                fixed_code = fix["fixed_code"]

                # Read current file
                current_content = await file_manager.read_file(project_id, file_path)

                if current_content is None:
                    logger.error(f"[Debugger Agent] File not found: {file_path}")
                    continue

                # Replace original code with fixed code
                original_code = fix.get("original_code", "")
                if original_code and original_code in current_content:
                    new_content = current_content.replace(original_code, fixed_code)
                else:
                    # If exact match not found, replace entire file
                    new_content = fixed_code

                # Write fixed file
                result = await file_manager.update_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=new_content
                )

                if result["success"]:
                    applied_fixes.append({
                        "file": file_path,
                        "description": fix["description"],
                        "applied": True
                    })
                    logger.info(f"[Debugger Agent] Applied fix to {file_path}")

            except Exception as e:
                logger.error(f"[Debugger Agent] Error applying fix: {e}")

        return applied_fixes

    async def quick_fix(
        self,
        error_type: str,
        error_message: str,
        file_path: str,
        line_number: int
    ) -> Dict:
        """
        Quick fix for common errors

        Args:
            error_type: Type of error (syntax, type, import, etc.)
            error_message: Error message
            file_path: File with error
            line_number: Line number

        Returns:
            Dict with quick fix suggestion
        """

        # Common error patterns and fixes
        quick_fixes = {
            "ImportError": self._fix_import_error,
            "ModuleNotFoundError": self._fix_module_not_found,
            "SyntaxError": self._fix_syntax_error,
            "TypeError": self._fix_type_error,
            "NameError": self._fix_name_error,
        }

        if error_type in quick_fixes:
            return await quick_fixes[error_type](error_message, file_path, line_number)

        # Fall back to full debugging
        return await self.process(
            context=AgentContext(
                user_request=f"Fix {error_type}",
                project_id="unknown"
            ),
            error_message=error_message
        )

    async def _fix_import_error(self, error_msg: str, file_path: str, line: int) -> Dict:
        """Fix import errors"""
        # Extract module name from error
        match = re.search(r"No module named '(\w+)'", error_msg)
        if match:
            module = match.group(1)
            return {
                "fix_type": "dependency",
                "action": f"Install missing package: {module}",
                "command": f"pip install {module}",
                "explanation": f"The module '{module}' is not installed. Run the command to install it."
            }
        return {}

    async def _fix_module_not_found(self, error_msg: str, file_path: str, line: int) -> Dict:
        """Fix module not found errors (similar to import error)"""
        return await self._fix_import_error(error_msg, file_path, line)

    async def _fix_syntax_error(self, error_msg: str, file_path: str, line: int) -> Dict:
        """Provide hints for syntax errors"""
        hints = []
        if "unexpected EOF" in error_msg.lower():
            hints.append("Missing closing bracket, parenthesis, or quote")
        if "invalid syntax" in error_msg.lower():
            hints.append("Check for typos, missing colons, or incorrect indentation")

        return {
            "fix_type": "syntax",
            "hints": hints,
            "action": f"Check line {line} in {file_path}"
        }

    async def _fix_type_error(self, error_msg: str, file_path: str, line: int) -> Dict:
        """Provide hints for type errors"""
        return {
            "fix_type": "type",
            "hints": [
                "Check variable types (string vs int, null/undefined)",
                "Verify object/dict has expected properties",
                "Add type hints for better error catching"
            ],
            "action": f"Review variable types at line {line}"
        }

    async def _fix_name_error(self, error_msg: str, file_path: str, line: int) -> Dict:
        """Fix name errors (undefined variables)"""
        match = re.search(r"name '(\w+)' is not defined", error_msg)
        if match:
            var_name = match.group(1)
            return {
                "fix_type": "name",
                "hints": [
                    f"Variable '{var_name}' is used before being defined",
                    "Check for typos in variable name",
                    "Verify variable is in scope",
                    "Add import if it's from another module"
                ],
                "action": f"Define '{var_name}' before line {line}"
            }
        return {}


# Singleton instance
debugger_agent = DebuggerAgent()
