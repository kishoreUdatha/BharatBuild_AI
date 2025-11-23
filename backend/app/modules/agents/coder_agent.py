"""
AGENT 3 - Code Generator Agent
Generates complete, production-ready code for full-stack applications
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.modules.automation import file_manager


class CoderAgent(BaseAgent):
    """
    Code Generator Agent

    Responsibilities:
    - Generate full backend code
    - Generate full frontend code
    - Create complete folder structures
    - Generate all project files
    - Support multiple tech stacks
    - Auto-correct syntax errors
    - Add educational comments for students
    """

    SYSTEM_PROMPT = """You are an expert Code Generator Agent for BharatBuild AI, a platform that helps students build full-stack projects.

YOUR ROLE:
- Generate complete, production-ready code for backend and frontend
- Create all necessary files with proper folder structure
- Support multiple tech stacks (React, Next.js, Python, Java, Go, Node.js, etc.)
- Write clean, well-commented code suitable for students to learn from
- Include error handling, validation, and security best practices
- Auto-correct any syntax or logical errors
- Generate small projects to large full-stack applications

INPUT YOU RECEIVE:
1. Project plan from Planner Agent (features, tech stack, requirements)
2. Architecture from Architect Agent (database schema, API design, components)
3. User's specific requirements and preferences

YOUR OUTPUT MUST BE VALID JSON:
{
  "project_metadata": {
    "name": "string",
    "tech_stack": {
      "frontend": "react/nextjs/vue/angular",
      "backend": "fastapi/express/spring/django",
      "database": "postgresql/mongodb/mysql",
      "other": ["typescript", "tailwindcss", "etc"]
    },
    "description": "string"
  },
  "folder_structure": {
    "root": "project-name",
    "directories": [
      "backend/",
      "backend/app/",
      "backend/app/models/",
      "backend/app/api/",
      "frontend/",
      "frontend/src/",
      "frontend/src/components/"
    ]
  },
  "files": [
    {
      "path": "relative/path/to/file.ext",
      "content": "complete file content with proper formatting",
      "language": "javascript/python/java/go/typescript",
      "description": "Brief explanation of what this file does",
      "dependencies": ["package1", "package2"],
      "educational_notes": "Key learning points for students"
    }
  ],
  "configuration_files": [
    {
      "path": "package.json",
      "content": "complete package.json content",
      "description": "Node.js dependencies and scripts"
    },
    {
      "path": "requirements.txt",
      "content": "fastapi\\npydantic\\nsqlalchemy",
      "description": "Python dependencies"
    },
    {
      "path": ".env.example",
      "content": "DATABASE_URL=postgresql://...",
      "description": "Environment variables template"
    }
  ],
  "setup_instructions": {
    "backend": [
      "cd backend",
      "pip install -r requirements.txt",
      "python -m uvicorn app.main:app --reload"
    ],
    "frontend": [
      "cd frontend",
      "npm install",
      "npm run dev"
    ],
    "database": [
      "Create PostgreSQL database",
      "Run migrations"
    ]
  },
  "implementation_notes": {
    "security": ["Password hashing with bcrypt", "JWT authentication", "Input validation"],
    "best_practices": ["Clean code", "Error handling", "Type safety"],
    "learning_points": ["RESTful API design", "React hooks", "Database relationships"]
  }
}

CODE GENERATION RULES:

1. **Code Quality**:
   - Write production-ready code, not just prototypes
   - Include proper error handling (try-catch, error boundaries)
   - Add input validation for all user inputs
   - Use TypeScript for type safety where applicable
   - Follow language-specific conventions (PEP 8 for Python, ESLint for JS)

2. **Security**:
   - Never hardcode secrets or API keys
   - Use environment variables for configuration
   - Hash passwords (bcrypt, argon2)
   - Validate and sanitize all inputs (prevent XSS, SQL injection)
   - Use HTTPS and secure headers
   - Implement proper CORS configuration

3. **Educational Comments**:
   - Add comments explaining complex logic
   - Include docstrings for functions/classes
   - Explain WHY, not just WHAT (e.g., "// Hash password to prevent plaintext storage" not "// Hash password")
   - Add TODO comments for future improvements
   - Include links to documentation for advanced topics

4. **File Structure**:
   - Follow framework conventions (Next.js App Router, FastAPI structure)
   - Separate concerns (models, views, controllers, services)
   - Use meaningful file and folder names
   - Keep files focused and single-purpose

5. **Dependencies**:
   - Use stable, well-maintained packages
   - Include version numbers in package.json/requirements.txt
   - Add only necessary dependencies
   - Document why each dependency is needed

6. **Testing Setup**:
   - Include basic test setup (Jest for React, pytest for Python)
   - Add example tests for core functionality
   - Include test scripts in package.json

7. **Tech Stack Specific Guidelines**:

   **React/Next.js:**
   - Use functional components with hooks
   - Implement proper state management (useState, useContext, Zustand)
   - Add loading states and error boundaries
   - Use Tailwind CSS for styling
   - Implement proper routing
   - Add SEO meta tags

   **FastAPI/Python:**
   - Use Pydantic models for validation
   - Implement proper async/await
   - Add API documentation (automatic with FastAPI)
   - Use SQLAlchemy for database
   - Implement dependency injection
   - Add proper logging

   **Node.js/Express:**
   - Use async/await, not callbacks
   - Implement middleware properly
   - Add request validation
   - Use proper error handling middleware
   - Implement rate limiting

   **Java/Spring Boot:**
   - Use proper annotations
   - Implement layered architecture
   - Add JPA entities and repositories
   - Use proper exception handling
   - Implement validation

8. **Error Correction**:
   - Validate syntax before output
   - Check for common errors (missing imports, undefined variables)
   - Ensure all file paths are correct
   - Verify dependency compatibility

9. **Responsive to Failures**:
   - If user reports error, analyze and fix immediately
   - Provide corrected file, not just explanation
   - Explain what was wrong and why fix works

EXAMPLE OUTPUT STRUCTURE:

For a "Todo App with Authentication" request:

{
  "project_metadata": {
    "name": "todo-app-fullstack",
    "tech_stack": {
      "frontend": "nextjs",
      "backend": "fastapi",
      "database": "postgresql",
      "other": ["typescript", "tailwindcss", "prisma"]
    }
  },
  "files": [
    {
      "path": "backend/app/main.py",
      "content": "from fastapi import FastAPI\\nfrom fastapi.middleware.cors import CORSMiddleware\\n\\napp = FastAPI(title=\\"Todo API\\")\\n\\n# CORS configuration for frontend access\\napp.add_middleware(\\n    CORSMiddleware,\\n    allow_origins=[\\"http://localhost:3000\\"],\\n    allow_credentials=True,\\n    allow_methods=[\\"*\\"],\\n    allow_headers=[\\"*\\"]\\n)...",
      "language": "python",
      "description": "FastAPI main application with CORS",
      "dependencies": ["fastapi", "uvicorn"],
      "educational_notes": "CORS middleware allows frontend to make API requests"
    },
    {
      "path": "frontend/src/app/page.tsx",
      "content": "'use client'\\n\\nimport { useState, useEffect } from 'react'\\n\\nexport default function Home() {\\n  const [todos, setTodos] = useState([])\\n  \\n  // Fetch todos on component mount\\n  useEffect(() => {\\n    fetchTodos()\\n  }, [])\\n  \\n  const fetchTodos = async () => {\\n    try {\\n      const res = await fetch('http://localhost:8000/api/todos')\\n      const data = await res.json()\\n      setTodos(data)\\n    } catch (error) {\\n      console.error('Error fetching todos:', error)\\n    }\\n  }...",
      "language": "typescript",
      "description": "Next.js home page with todo list",
      "dependencies": ["react", "next"],
      "educational_notes": "useEffect hook runs on mount to fetch data"
    }
  ]
}

REMEMBER:
- Students will read and learn from this code
- Code should work without modifications
- Include all necessary files (no placeholders)
- Generate complete implementations, not skeleton code
- Make it educational but production-ready
"""

    def __init__(self):
        super().__init__(
            name="Coder Agent",
            role="code_generator",
            capabilities=[
                "backend_code_generation",
                "frontend_code_generation",
                "file_structure_creation",
                "multi_language_support",
                "error_correction",
                "dependency_management",
                "security_best_practices"
            ]
        )

    async def process(
        self,
        context: AgentContext,
        plan: Optional[Dict] = None,
        architecture: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate complete code for the project

        Args:
            context: Agent context with user request and history
            plan: Output from Planner Agent
            architecture: Output from Architect Agent

        Returns:
            Dict with generated files, folder structure, and setup instructions
        """
        try:
            logger.info(f"[Coder Agent] Starting code generation for: {context.user_request[:100]}")

            # Build enhanced prompt with plan and architecture
            enhanced_prompt = self._build_code_generation_prompt(
                context.user_request,
                plan,
                architecture
            )

            # Call Claude API
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=enhanced_prompt,
                temperature=0.3  # Lower temperature for more consistent code
            )

            # Parse JSON response
            code_output = self._parse_code_output(response)

            # Validate generated code
            validation_result = await self._validate_code(code_output)

            if not validation_result["valid"]:
                logger.warning(f"[Coder Agent] Validation failed: {validation_result['errors']}")
                # Auto-correct and regenerate
                code_output = await self._auto_correct_code(code_output, validation_result["errors"])

            # Write files to disk
            files_created = await self._write_files_to_disk(
                context.project_id,
                code_output["files"] + code_output.get("configuration_files", [])
            )

            logger.info(f"[Coder Agent] Successfully generated {len(files_created)} files")

            return {
                "success": True,
                "agent": self.name,
                "project_metadata": code_output.get("project_metadata", {}),
                "folder_structure": code_output.get("folder_structure", {}),
                "files_created": files_created,
                "setup_instructions": code_output.get("setup_instructions", {}),
                "implementation_notes": code_output.get("implementation_notes", {}),
                "validation": validation_result,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Coder Agent] Error: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_code_generation_prompt(
        self,
        user_request: str,
        plan: Optional[Dict],
        architecture: Optional[Dict]
    ) -> str:
        """Build enhanced prompt with plan and architecture context"""

        prompt_parts = [
            f"USER REQUEST:\n{user_request}\n"
        ]

        if plan:
            prompt_parts.append(f"\nPROJECT PLAN:\n{json.dumps(plan, indent=2)}\n")

        if architecture:
            prompt_parts.append(f"\nSYSTEM ARCHITECTURE:\n{json.dumps(architecture, indent=2)}\n")

        prompt_parts.append("""
TASK:
Generate complete, production-ready code for this project. Include:
1. All backend files with complete implementations
2. All frontend files with complete implementations
3. Configuration files (package.json, requirements.txt, .env.example, etc.)
4. Database models and migrations if needed
5. API routes and endpoints
6. UI components and pages
7. Setup and installation instructions

Remember:
- This is for students - add educational comments
- Include security best practices
- Add proper error handling
- Make it production-ready
- No placeholders or TODOs in critical code
- Generate COMPLETE files, not skeleton code

Output valid JSON following the specified format.
""")

        return "\n".join(prompt_parts)

    def _parse_code_output(self, response: str) -> Dict:
        """Parse JSON output from Claude"""
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[start:end]
            code_output = json.loads(json_str)

            return code_output

        except json.JSONDecodeError as e:
            logger.error(f"[Coder Agent] JSON parse error: {e}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")

    async def _validate_code(self, code_output: Dict) -> Dict:
        """
        Validate generated code for common issues

        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []

        # Check required fields
        if "files" not in code_output or not code_output["files"]:
            errors.append("No files generated")

        # Validate each file
        for file_info in code_output.get("files", []):
            # Check required fields
            if "path" not in file_info:
                errors.append(f"File missing 'path' field")
                continue

            if "content" not in file_info or not file_info["content"]:
                errors.append(f"File {file_info['path']} has no content")

            # Check for placeholders/TODOs in critical files
            content = file_info.get("content", "")
            if "TODO" in content and not file_info["path"].endswith(".md"):
                warnings.append(f"TODO found in {file_info['path']}")

            if "PLACEHOLDER" in content.upper():
                errors.append(f"Placeholder code in {file_info['path']}")

            # Language-specific validation
            language = file_info.get("language", "")

            if language == "python":
                # Check for basic syntax issues
                if "import" not in content and "from" not in content:
                    warnings.append(f"No imports in Python file {file_info['path']}")

            elif language in ["javascript", "typescript"]:
                # Check for basic syntax
                if file_info["path"].endswith((".tsx", ".jsx")) and "export" not in content:
                    warnings.append(f"No exports in {file_info['path']}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    async def _auto_correct_code(self, code_output: Dict, errors: List[str]) -> Dict:
        """
        Attempt to auto-correct validation errors

        Args:
            code_output: Original code output
            errors: List of validation errors

        Returns:
            Corrected code output
        """
        logger.info(f"[Coder Agent] Auto-correcting {len(errors)} errors")

        correction_prompt = f"""
The generated code has the following errors:
{chr(10).join(f"- {error}" for error in errors)}

ORIGINAL OUTPUT:
{json.dumps(code_output, indent=2)}

Please fix these errors and return the corrected JSON output.
Make sure:
1. All files have content (no empty files)
2. No placeholder code in critical files
3. All required fields are present
4. Code is complete and functional
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=correction_prompt,
            temperature=0.2
        )

        return self._parse_code_output(response)

    async def _write_files_to_disk(
        self,
        project_id: str,
        files: List[Dict]
    ) -> List[Dict]:
        """
        Write generated files to disk using file_manager

        Args:
            project_id: Project identifier
            files: List of file dicts with path and content

        Returns:
            List of created file info
        """
        created_files = []

        for file_info in files:
            try:
                file_path = file_info["path"]
                content = file_info["content"]

                # Create file using file_manager
                result = await file_manager.create_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=content
                )

                if result["success"]:
                    created_files.append({
                        "path": file_path,
                        "size": len(content),
                        "language": file_info.get("language"),
                        "description": file_info.get("description")
                    })
                    logger.info(f"[Coder Agent] Created file: {file_path}")
                else:
                    logger.error(f"[Coder Agent] Failed to create {file_path}: {result.get('error')}")

            except Exception as e:
                logger.error(f"[Coder Agent] Error writing file {file_info.get('path')}: {e}")

        return created_files

    async def generate_file(
        self,
        file_path: str,
        description: str,
        tech_stack: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Generate a single file

        Args:
            file_path: Path for the file
            description: What the file should do
            tech_stack: Technology (python, typescript, etc.)
            context: Additional context (other files, requirements)

        Returns:
            Dict with file content and metadata
        """
        prompt = f"""
Generate a single file:

FILE PATH: {file_path}
DESCRIPTION: {description}
TECH STACK: {tech_stack}
{f"CONTEXT: {context}" if context else ""}

Generate ONLY this file with complete, production-ready code.
Include educational comments.
Return JSON:
{{
  "path": "{file_path}",
  "content": "complete file content",
  "language": "language name",
  "dependencies": ["package1", "package2"]
}}
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3
        )

        return self._parse_code_output(response)

    async def fix_error(
        self,
        file_path: str,
        error_message: str,
        current_code: str
    ) -> Dict:
        """
        Fix an error in existing code

        Args:
            file_path: Path to file with error
            error_message: Error message
            current_code: Current file content

        Returns:
            Dict with corrected code
        """
        prompt = f"""
Fix the following error:

FILE: {file_path}
ERROR: {error_message}

CURRENT CODE:
```
{current_code}
```

Return the CORRECTED code in JSON format:
{{
  "path": "{file_path}",
  "content": "corrected code",
  "fix_explanation": "what was wrong and how you fixed it"
}}
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2
        )

        return self._parse_code_output(response)


# Singleton instance
coder_agent = CoderAgent()
