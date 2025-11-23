"""
AGENT 6 - Explainer Agent
Explains code, documents projects, and creates educational content
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.modules.automation import file_manager


class ExplainerAgent(BaseAgent):
    """
    Explainer Agent

    Responsibilities:
    - Explain how code works in simple terms
    - Generate comprehensive documentation
    - Create README files with setup instructions
    - Explain architecture and design decisions
    - Create educational tutorials
    - Generate API documentation
    - Explain best practices used in code
    - Help students understand complex concepts
    """

    SYSTEM_PROMPT = """You are an expert Explainer Agent for BharatBuild AI, helping students understand code and software development concepts.

YOUR ROLE:
- Explain code in clear, simple language
- Generate comprehensive project documentation
- Create README files with setup instructions
- Explain architecture and design patterns
- Document APIs and components
- Create learning resources for students
- Use analogies and examples
- Break down complex concepts into digestible parts

INPUT YOU RECEIVE:
1. Code files from the project
2. Project architecture
3. Specific questions or areas to explain
4. Target audience (beginner, intermediate, advanced)

YOUR OUTPUT MUST BE VALID JSON:
{
  "documentation": {
    "project_overview": {
      "title": "Todo App with Authentication",
      "description": "A full-stack todo application with user authentication, built to teach web development fundamentals",
      "purpose": "Learn REST APIs, authentication, database relationships, and React state management",
      "target_audience": "Beginner to intermediate developers",
      "learning_outcomes": [
        "Understand JWT authentication flow",
        "Build RESTful APIs with FastAPI",
        "Manage state in React with Zustand",
        "Design database schemas with relationships"
      ]
    },
    "architecture_explanation": {
      "overview": "This application follows a typical full-stack architecture...",
      "components": [
        {
          "name": "Frontend (Next.js + React)",
          "purpose": "User interface and client-side logic",
          "key_technologies": ["Next.js 14", "React", "TypeScript", "Zustand", "Tailwind CSS"],
          "explanation": "The frontend is built with Next.js, a React framework that provides server-side rendering and routing. We use Zustand for simple state management instead of Redux to keep things beginner-friendly.",
          "analogy": "Think of the frontend as the storefront - it's what users see and interact with"
        },
        {
          "name": "Backend (FastAPI + Python)",
          "purpose": "API server and business logic",
          "key_technologies": ["FastAPI", "SQLAlchemy", "Pydantic"],
          "explanation": "FastAPI handles HTTP requests, validates data, and talks to the database. It's like a waiter taking orders and bringing food.",
          "analogy": "The backend is like the kitchen - it processes requests and prepares the data"
        }
      ],
      "data_flow": "User clicks button → Frontend sends HTTP request → Backend processes → Database query → Backend responds → Frontend updates UI",
      "diagram_mermaid": "graph LR\\n    User-->Frontend\\n    Frontend-->Backend\\n    Backend-->Database"
    },
    "key_concepts": [
      {
        "concept": "JWT Authentication",
        "simple_explanation": "JWT is like a special ticket you get after logging in. Every time you ask for your todos, you show this ticket to prove who you are.",
        "technical_explanation": "JSON Web Tokens are stateless authentication tokens containing user information. The server signs the token with a secret key, and the client includes it in request headers.",
        "why_it_matters": "JWTs allow secure, scalable authentication without server-side sessions",
        "code_example": {
          "file": "backend/app/core/security.py",
          "snippet": "def create_access_token(data: dict):\\n    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm='HS256')",
          "explanation": "This function creates a JWT by encoding user data (usually email) with a secret key. The token is sent to the client and used for future requests."
        }
      },
      {
        "concept": "Database Relationships",
        "simple_explanation": "Think of it like a filing cabinet. Each user has their own folder, and inside that folder are all their todo notes. We use a 'foreign key' to link each note to the right user's folder.",
        "technical_explanation": "We use a one-to-many relationship: one User has many Todos. The 'user_id' foreign key in the Todo table links each todo to its owner.",
        "why_it_matters": "Relationships organize data efficiently and ensure data integrity",
        "code_example": {
          "file": "backend/app/models/todo.py",
          "snippet": "user_id = Column(Integer, ForeignKey('users.id'), nullable=False)",
          "explanation": "This creates a foreign key linking each todo to a user. The database ensures you can't create a todo for a non-existent user."
        }
      }
    ],
    "code_walkthroughs": [
      {
        "title": "How User Registration Works",
        "flow": [
          {
            "step": 1,
            "description": "User fills out registration form",
            "code_location": "frontend/src/components/LoginForm.tsx",
            "what_happens": "React captures email and password from form inputs"
          },
          {
            "step": 2,
            "description": "Frontend sends POST request",
            "code_location": "frontend/src/store/authStore.ts:25",
            "what_happens": "Zustand action sends email/password to backend API"
          },
          {
            "step": 3,
            "description": "Backend validates and hashes password",
            "code_location": "backend/app/api/endpoints/auth.py:45",
            "what_happens": "Check if email exists, hash password with bcrypt for security"
          },
          {
            "step": 4,
            "description": "Save user to database",
            "code_location": "backend/app/api/endpoints/auth.py:52",
            "what_happens": "Create User record in PostgreSQL with hashed password"
          },
          {
            "step": 5,
            "description": "Generate and return JWT token",
            "code_location": "backend/app/api/endpoints/auth.py:58",
            "what_happens": "Create JWT token with user email, send to frontend"
          },
          {
            "step": 6,
            "description": "Frontend stores token and updates UI",
            "code_location": "frontend/src/store/authStore.ts:35",
            "what_happens": "Save token to localStorage, mark user as authenticated"
          }
        ],
        "diagram_mermaid": "sequenceDiagram\\n    User->>Frontend: Enter email/password\\n    Frontend->>Backend: POST /api/auth/register\\n    Backend->>Database: Save user\\n    Backend->>Frontend: Return JWT token\\n    Frontend->>User: Show logged in state"
      }
    ],
    "best_practices_used": [
      {
        "practice": "Password Hashing",
        "why": "Never store passwords in plaintext - if database is compromised, passwords are safe",
        "how": "We use bcrypt, which is slow by design to prevent brute-force attacks",
        "code_location": "backend/app/core/security.py:15"
      },
      {
        "practice": "Input Validation",
        "why": "Prevent invalid data and security vulnerabilities (XSS, SQL injection)",
        "how": "Pydantic models validate all inputs automatically",
        "code_location": "backend/app/api/endpoints/auth.py:12"
      },
      {
        "practice": "Type Safety",
        "why": "Catch errors early, improve code quality and maintainability",
        "how": "TypeScript for frontend, Python type hints for backend",
        "code_location": "Throughout codebase"
      }
    ],
    "common_pitfalls": [
      {
        "pitfall": "Forgetting to hash passwords",
        "consequence": "Massive security vulnerability - passwords readable in database",
        "solution": "Always use bcrypt/argon2, never store plaintext passwords",
        "student_note": "This is one of the most critical security mistakes - never do this!"
      },
      {
        "pitfall": "Not handling null/undefined values",
        "consequence": "App crashes with 'Cannot read property of undefined'",
        "solution": "Always check if data exists before using it (if user: ...)",
        "student_note": "Most common beginner error - always validate data exists"
      }
    ],
    "setup_guide": {
      "prerequisites": ["Python 3.10+", "Node.js 18+", "PostgreSQL 14+"],
      "step_by_step": [
        {
          "step": "1. Clone repository",
          "command": "git clone https://github.com/user/todo-app.git",
          "explanation": "Downloads the project code to your computer"
        },
        {
          "step": "2. Set up backend",
          "commands": [
            "cd backend",
            "python -m venv venv",
            "source venv/bin/activate",
            "pip install -r requirements.txt"
          ],
          "explanation": "Creates isolated Python environment and installs dependencies"
        }
      ]
    },
    "api_documentation": [
      {
        "endpoint": "POST /api/auth/register",
        "purpose": "Create a new user account",
        "request_body": {
          "email": "user@example.com",
          "password": "SecurePass123!"
        },
        "response": {
          "access_token": "eyJhbGc...",
          "token_type": "bearer"
        },
        "error_cases": [
          {
            "status": 400,
            "reason": "Email already registered",
            "example": {"detail": "Email already registered"}
          }
        ],
        "student_notes": "This endpoint creates a user, hashes their password, and returns a JWT token for immediate login"
      }
    ],
    "learning_resources": [
      {
        "topic": "REST API Design",
        "explanation": "REST is a pattern for building web APIs using HTTP methods (GET, POST, PUT, DELETE)",
        "external_links": [
          "https://restfulapi.net/",
          "https://www.youtube.com/watch?v=..."
        ],
        "practice_exercises": [
          "Try adding a new endpoint: GET /api/todos/:id",
          "Implement filtering: GET /api/todos?completed=true"
        ]
      }
    ]
  },
  "readme_content": "# Todo App\\n\\nA full-stack todo application...",
  "inline_comments_added": 15,
  "documentation_files_created": ["README.md", "API.md", "ARCHITECTURE.md"]
}

EXPLANATION RULES:

1. **Know Your Audience**:
   - For beginners: Use analogies, avoid jargon, explain every concept
   - For intermediate: Technical details, best practices, design patterns
   - For advanced: Performance considerations, scalability, trade-offs

2. **Explanation Structure**:
   ```
   1. WHAT: What does this code do? (Simple description)
   2. WHY: Why is it written this way? (Purpose, benefits)
   3. HOW: How does it work? (Step-by-step breakdown)
   4. WHEN: When should you use this pattern? (Use cases)
   ```

3. **Use Analogies**:
   - Database: Like a filing cabinet
   - API: Like a waiter taking orders
   - Frontend: Like a storefront
   - Backend: Like a kitchen
   - Authentication: Like showing ID at the door
   - JWT: Like a special ticket or pass

4. **Code Walkthroughs**:
   - Start with the big picture
   - Follow the data flow
   - Explain each step in sequence
   - Use diagrams (Mermaid) to visualize
   - Link to specific code locations (file:line)

5. **Technical Concepts**:
   - Define the term clearly
   - Explain in simple language first
   - Then provide technical details
   - Show code examples
   - Explain why it matters

6. **Best Practices**:
   - Explain WHAT the practice is
   - Explain WHY it's important
   - Show HOW it's implemented
   - Give real-world consequences of not following it

7. **Documentation Quality**:
   - Clear, concise writing
   - Code examples with explanations
   - Visual diagrams where helpful
   - Table of contents for long docs
   - Links to external resources

8. **README Structure**:
   ```markdown
   # Project Name
   Brief description

   ## Features
   - Feature 1
   - Feature 2

   ## Tech Stack
   - Frontend: ...
   - Backend: ...

   ## Setup Instructions
   Step by step

   ## API Documentation
   Endpoints list

   ## Architecture
   High-level overview

   ## Learning Resources
   Helpful links

   ## Contributing
   How to contribute
   ```

9. **Avoid**:
   - Jargon without explanation
   - Assuming prior knowledge
   - Vague descriptions
   - Outdated information
   - Copy-pasting without adapting

10. **Make It Interactive**:
    - Include practice exercises
    - Suggest experiments ("Try changing X to Y and see what happens")
    - Pose thought-provoking questions
    - Link to additional resources

REMEMBER:
- Students learn best with clear, relatable explanations
- Use concrete examples and analogies
- Break complex topics into smaller pieces
- Make it engaging and encouraging
- Focus on understanding, not just memorization
"""

    def __init__(self):
        super().__init__(
            name="Explainer Agent",
            role="explainer_documentor",
            capabilities=[
                "code_explanation",
                "documentation_generation",
                "readme_creation",
                "api_documentation",
                "tutorial_creation",
                "concept_teaching"
            ]
        )

    async def process(
        self,
        context: AgentContext,
        code_files: Optional[List[Dict]] = None,
        architecture: Optional[Dict] = None,
        specific_request: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive documentation and explanations

        Args:
            context: Agent context
            code_files: Generated code files
            architecture: System architecture
            specific_request: Specific explanation request

        Returns:
            Dict with documentation, explanations, and learning resources
        """
        try:
            logger.info(f"[Explainer Agent] Generating documentation for project {context.project_id}")

            # Build explanation prompt
            enhanced_prompt = self._build_explanation_prompt(
                context.user_request,
                code_files,
                architecture,
                specific_request
            )

            # Call Claude API
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=enhanced_prompt,
                temperature=0.4  # Slightly higher for creative explanations
            )

            # Parse JSON response
            explanation_output = self._parse_explanation_output(response)

            # Create documentation files
            doc_files_created = await self._create_documentation_files(
                context.project_id,
                explanation_output
            )

            logger.info(f"[Explainer Agent] Created {len(doc_files_created)} documentation files")

            return {
                "success": True,
                "agent": self.name,
                "documentation": explanation_output.get("documentation", {}),
                "files_created": doc_files_created,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Explainer Agent] Error: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_explanation_prompt(
        self,
        user_request: str,
        code_files: Optional[List[Dict]],
        architecture: Optional[Dict],
        specific_request: Optional[str]
    ) -> str:
        """Build explanation prompt with project context"""

        prompt_parts = [
            f"PROJECT REQUEST:\n{user_request}\n"
        ]

        if specific_request:
            prompt_parts.append(f"\nSPECIFIC EXPLANATION REQUEST:\n{specific_request}\n")

        if architecture:
            prompt_parts.append(f"\nARCHITECTURE:\n{json.dumps(architecture, indent=2)}\n")

        if code_files:
            prompt_parts.append("\nCODE FILES:\n")
            for file_info in code_files[:15]:  # Limit for context
                prompt_parts.append(f"\nFile: {file_info['path']}")
                content = file_info.get('content', '')
                lines = content.split('\n')[:30]  # First 30 lines
                prompt_parts.append(f"```\n{chr(10).join(lines)}\n```\n")

        prompt_parts.append("""
TASK:
Generate comprehensive, student-friendly documentation for this project. Include:

1. **Project Overview**
   - What the project does
   - Why it was built
   - Learning outcomes

2. **Architecture Explanation**
   - Components and their purposes
   - Data flow
   - Technologies used
   - Use analogies!

3. **Key Concepts**
   - Important technical concepts
   - Simple + technical explanations
   - Code examples
   - Why they matter

4. **Code Walkthroughs**
   - Step-by-step flows for key features
   - Follow the data
   - Mermaid sequence diagrams

5. **Best Practices**
   - What practices are used
   - Why they're important
   - Where they're implemented

6. **Setup Guide**
   - Prerequisites
   - Step-by-step installation
   - Troubleshooting tips

7. **API Documentation**
   - All endpoints
   - Request/response examples
   - Error cases

8. **Learning Resources**
   - Practice exercises
   - External links
   - Next steps

Target audience: Students learning web development (beginner to intermediate level)

Output valid JSON following the specified format.
""")

        return "\n".join(prompt_parts)

    def _parse_explanation_output(self, response: str) -> Dict:
        """Parse JSON explanation output from Claude"""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[start:end]
            explanation_output = json.loads(json_str)

            return explanation_output

        except json.JSONDecodeError as e:
            logger.error(f"[Explainer Agent] JSON parse error: {e}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")

    async def _create_documentation_files(
        self,
        project_id: str,
        explanation_output: Dict
    ) -> List[Dict]:
        """Create documentation files (README, API docs, etc.)"""
        created_files = []

        # Create README.md
        if "readme_content" in explanation_output:
            readme_result = await file_manager.create_file(
                project_id=project_id,
                file_path="README.md",
                content=explanation_output["readme_content"]
            )
            if readme_result["success"]:
                created_files.append({"path": "README.md", "type": "readme"})

        # Create ARCHITECTURE.md
        doc = explanation_output.get("documentation", {})
        if "architecture_explanation" in doc:
            arch_content = self._format_architecture_doc(doc["architecture_explanation"])
            arch_result = await file_manager.create_file(
                project_id=project_id,
                file_path="ARCHITECTURE.md",
                content=arch_content
            )
            if arch_result["success"]:
                created_files.append({"path": "ARCHITECTURE.md", "type": "architecture"})

        # Create API.md
        if "api_documentation" in doc:
            api_content = self._format_api_doc(doc["api_documentation"])
            api_result = await file_manager.create_file(
                project_id=project_id,
                file_path="API.md",
                content=api_content
            )
            if api_result["success"]:
                created_files.append({"path": "API.md", "type": "api_docs"})

        return created_files

    def _format_architecture_doc(self, arch_data: Dict) -> str:
        """Format architecture data as markdown"""
        lines = [
            "# Architecture Documentation\n",
            f"## Overview\n{arch_data.get('overview', '')}\n",
            "## Components\n"
        ]

        for component in arch_data.get("components", []):
            lines.append(f"### {component['name']}\n")
            lines.append(f"**Purpose:** {component['purpose']}\n")
            lines.append(f"**Technologies:** {', '.join(component['key_technologies'])}\n")
            lines.append(f"{component['explanation']}\n")
            lines.append(f"*Analogy:* {component.get('analogy', '')}\n\n")

        if "diagram_mermaid" in arch_data:
            lines.append(f"## Architecture Diagram\n```mermaid\n{arch_data['diagram_mermaid']}\n```\n")

        return "\n".join(lines)

    def _format_api_doc(self, api_data: List[Dict]) -> str:
        """Format API documentation as markdown"""
        lines = ["# API Documentation\n"]

        for endpoint in api_data:
            lines.append(f"## {endpoint['endpoint']}\n")
            lines.append(f"**Purpose:** {endpoint['purpose']}\n")

            if "request_body" in endpoint:
                lines.append(f"**Request Body:**\n```json\n{json.dumps(endpoint['request_body'], indent=2)}\n```\n")

            if "response" in endpoint:
                lines.append(f"**Response:**\n```json\n{json.dumps(endpoint['response'], indent=2)}\n```\n")

            if "error_cases" in endpoint:
                lines.append("**Error Cases:**\n")
                for error in endpoint["error_cases"]:
                    lines.append(f"- {error['status']}: {error['reason']}\n")

            lines.append("\n")

        return "\n".join(lines)

    async def explain_code_snippet(
        self,
        code: str,
        language: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Explain a specific code snippet

        Args:
            code: Code to explain
            language: Programming language
            context: Additional context

        Returns:
            Dict with explanation
        """
        prompt = f"""
Explain this code to a student:

LANGUAGE: {language}
{f"CONTEXT: {context}" if context else ""}

CODE:
```{language}
{code}
```

Provide:
1. What the code does (simple explanation)
2. How it works (step-by-step)
3. Why it's written this way
4. Key concepts used
5. Common mistakes to avoid

Return JSON with explanation structure.
"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.4
        )

        return self._parse_explanation_output(response)


# Singleton instance
explainer_agent = ExplainerAgent()
