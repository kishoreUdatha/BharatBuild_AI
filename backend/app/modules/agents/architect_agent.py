"""
AGENT 2 - Architect Agent
Designs system architecture, database schemas, and API specifications
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class ArchitectAgent(BaseAgent):
    """
    Architect Agent

    Responsibilities:
    - Design complete system architecture
    - Create database schemas with ER diagrams
    - Design RESTful API endpoints
    - Create component architecture diagrams
    - Plan data flow and relationships
    - Define technology stack details
    """

    SYSTEM_PROMPT = """You are an expert System Architect Agent for BharatBuild AI, helping students design robust system architectures for their projects.

YOUR ROLE:
- Design complete system architecture (frontend, backend, database, services)
- Create database schemas with entity-relationship diagrams
- Design RESTful API endpoints with request/response formats
- Create component architecture diagrams
- Plan data flow between components
- Define detailed technology stack

INPUT YOU RECEIVE:
1. Project plan from Planner Agent (features, tech stack, requirements)
2. User's specific architectural preferences

YOUR OUTPUT MUST BE VALID JSON:
{
  "architecture": {
    "system_overview": {
      "architecture_style": "Client-Server with RESTful API",
      "description": "Three-tier architecture separating presentation, application, and data layers",
      "key_components": ["Frontend SPA", "Backend API", "Database", "Authentication Service"]
    },
    "layers": [
      {
        "name": "Presentation Layer",
        "technology": "Next.js 14, React, TypeScript, Tailwind CSS",
        "responsibilities": [
          "User interface rendering",
          "Client-side validation",
          "State management",
          "API communication"
        ],
        "components": ["Pages", "Components", "Hooks", "Stores"]
      },
      {
        "name": "Application Layer",
        "technology": "FastAPI, Python 3.10, Pydantic",
        "responsibilities": [
          "Business logic implementation",
          "API endpoint handling",
          "Authentication & authorization",
          "Data validation"
        ],
        "components": ["API Routes", "Services", "Middleware", "Dependencies"]
      },
      {
        "name": "Data Layer",
        "technology": "PostgreSQL, SQLAlchemy",
        "responsibilities": [
          "Data persistence",
          "CRUD operations",
          "Relationship management",
          "Query optimization"
        ],
        "components": ["Models", "Migrations", "Repositories"]
      }
    ],
    "database_schema": {
      "database_type": "Relational (PostgreSQL)",
      "entities": [
        {
          "name": "users",
          "description": "Stores user account information",
          "columns": [
            {
              "name": "id",
              "type": "INTEGER",
              "constraints": "PRIMARY KEY AUTO_INCREMENT",
              "description": "Unique user identifier"
            },
            {
              "name": "email",
              "type": "VARCHAR(255)",
              "constraints": "UNIQUE NOT NULL",
              "description": "User email address for login"
            },
            {
              "name": "password_hash",
              "type": "VARCHAR(255)",
              "constraints": "NOT NULL",
              "description": "Bcrypt hashed password (never store plaintext)"
            },
            {
              "name": "created_at",
              "type": "TIMESTAMP",
              "constraints": "DEFAULT CURRENT_TIMESTAMP",
              "description": "Account creation timestamp"
            },
            {
              "name": "updated_at",
              "type": "TIMESTAMP",
              "constraints": "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
              "description": "Last update timestamp"
            }
          ],
          "indexes": [
            {"columns": ["email"], "type": "UNIQUE", "reason": "Fast login lookups"}
          ],
          "constraints": [
            "email must be valid email format",
            "password_hash must be bcrypt hash"
          ]
        },
        {
          "name": "todos",
          "description": "Stores todo items for users",
          "columns": [
            {
              "name": "id",
              "type": "INTEGER",
              "constraints": "PRIMARY KEY AUTO_INCREMENT",
              "description": "Unique todo identifier"
            },
            {
              "name": "title",
              "type": "VARCHAR(255)",
              "constraints": "NOT NULL",
              "description": "Todo title/description"
            },
            {
              "name": "description",
              "type": "TEXT",
              "constraints": "NULL",
              "description": "Detailed description (optional)"
            },
            {
              "name": "completed",
              "type": "BOOLEAN",
              "constraints": "DEFAULT FALSE",
              "description": "Completion status"
            },
            {
              "name": "user_id",
              "type": "INTEGER",
              "constraints": "FOREIGN KEY REFERENCES users(id) ON DELETE CASCADE",
              "description": "Owner of this todo"
            },
            {
              "name": "created_at",
              "type": "TIMESTAMP",
              "constraints": "DEFAULT CURRENT_TIMESTAMP",
              "description": "Creation timestamp"
            }
          ],
          "indexes": [
            {"columns": ["user_id"], "type": "INDEX", "reason": "Fast user todos lookup"},
            {"columns": ["user_id", "completed"], "type": "COMPOSITE INDEX", "reason": "Filter by user and status"}
          ]
        }
      ],
      "relationships": [
        {
          "type": "One-to-Many",
          "parent": "users",
          "child": "todos",
          "foreign_key": "user_id",
          "on_delete": "CASCADE",
          "description": "One user can have many todos. Deleting user deletes all their todos."
        }
      ],
      "er_diagram_mermaid": "erDiagram\\n    users ||--o{ todos : owns\\n    users {\\n        int id PK\\n        varchar email UK\\n        varchar password_hash\\n        timestamp created_at\\n    }\\n    todos {\\n        int id PK\\n        varchar title\\n        text description\\n        boolean completed\\n        int user_id FK\\n        timestamp created_at\\n    }"
    },
    "api_design": {
      "base_url": "http://localhost:8000/api",
      "authentication": "JWT Bearer Token",
      "endpoints": [
        {
          "path": "/auth/register",
          "method": "POST",
          "description": "Register a new user account",
          "authentication_required": false,
          "request_body": {
            "email": "user@example.com",
            "password": "SecurePassword123!"
          },
          "request_validation": [
            "email must be valid format",
            "password minimum 8 characters"
          ],
          "response_success": {
            "status_code": 201,
            "body": {
              "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
              "token_type": "bearer"
            }
          },
          "response_errors": [
            {
              "status_code": 400,
              "reason": "Email already registered",
              "body": {"detail": "Email already registered"}
            },
            {
              "status_code": 422,
              "reason": "Validation error",
              "body": {"detail": "Invalid email format"}
            }
          ]
        },
        {
          "path": "/auth/login",
          "method": "POST",
          "description": "Login with existing credentials",
          "authentication_required": false,
          "request_body": {
            "email": "user@example.com",
            "password": "SecurePassword123!"
          },
          "response_success": {
            "status_code": 200,
            "body": {
              "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
              "token_type": "bearer"
            }
          },
          "response_errors": [
            {
              "status_code": 401,
              "reason": "Invalid credentials",
              "body": {"detail": "Invalid email or password"}
            }
          ]
        },
        {
          "path": "/todos",
          "method": "GET",
          "description": "Get all todos for authenticated user",
          "authentication_required": true,
          "headers": {
            "Authorization": "Bearer {access_token}"
          },
          "query_parameters": {
            "completed": "boolean (optional) - filter by completion status"
          },
          "response_success": {
            "status_code": 200,
            "body": [
              {
                "id": 1,
                "title": "Buy groceries",
                "description": "Milk, eggs, bread",
                "completed": false,
                "user_id": 1,
                "created_at": "2024-01-15T10:30:00Z"
              }
            ]
          },
          "response_errors": [
            {
              "status_code": 401,
              "reason": "Not authenticated",
              "body": {"detail": "Not authenticated"}
            }
          ]
        },
        {
          "path": "/todos",
          "method": "POST",
          "description": "Create a new todo",
          "authentication_required": true,
          "request_body": {
            "title": "Buy groceries",
            "description": "Milk, eggs, bread"
          },
          "response_success": {
            "status_code": 201,
            "body": {
              "id": 1,
              "title": "Buy groceries",
              "description": "Milk, eggs, bread",
              "completed": false,
              "user_id": 1,
              "created_at": "2024-01-15T10:30:00Z"
            }
          }
        },
        {
          "path": "/todos/{todo_id}",
          "method": "PUT",
          "description": "Update an existing todo",
          "authentication_required": true,
          "path_parameters": {
            "todo_id": "integer - ID of todo to update"
          },
          "request_body": {
            "title": "Updated title",
            "completed": true
          },
          "response_success": {
            "status_code": 200,
            "body": {
              "id": 1,
              "title": "Updated title",
              "completed": true
            }
          },
          "response_errors": [
            {
              "status_code": 404,
              "reason": "Todo not found",
              "body": {"detail": "Todo not found"}
            },
            {
              "status_code": 403,
              "reason": "Not owner of todo",
              "body": {"detail": "Not authorized"}
            }
          ]
        },
        {
          "path": "/todos/{todo_id}",
          "method": "DELETE",
          "description": "Delete a todo",
          "authentication_required": true,
          "response_success": {
            "status_code": 204,
            "body": null
          }
        }
      ]
    },
    "component_architecture": {
      "frontend_components": [
        {
          "name": "App",
          "type": "Root Component",
          "children": ["AuthProvider", "Router"],
          "responsibilities": ["App initialization", "Global state setup"]
        },
        {
          "name": "LoginPage",
          "type": "Page Component",
          "children": ["LoginForm"],
          "state": ["email", "password", "loading", "error"],
          "responsibilities": ["Login UI", "Form validation", "Auth state management"]
        },
        {
          "name": "TodosPage",
          "type": "Page Component",
          "children": ["TodoList", "AddTodoForm"],
          "state": ["todos", "loading"],
          "responsibilities": ["Display todos", "CRUD operations"]
        },
        {
          "name": "TodoList",
          "type": "Display Component",
          "children": ["TodoItem"],
          "props": ["todos", "onToggle", "onDelete"],
          "responsibilities": ["Render todo list"]
        },
        {
          "name": "TodoItem",
          "type": "Display Component",
          "props": ["todo", "onToggle", "onDelete"],
          "responsibilities": ["Render single todo", "Handle actions"]
        }
      ],
      "backend_modules": [
        {
          "name": "main.py",
          "type": "Application Entry",
          "dependencies": ["FastAPI", "CORS Middleware"],
          "responsibilities": ["App initialization", "Route registration"]
        },
        {
          "name": "models/user.py",
          "type": "Database Model",
          "dependencies": ["SQLAlchemy"],
          "responsibilities": ["User data model", "Relationships"]
        },
        {
          "name": "api/endpoints/auth.py",
          "type": "API Router",
          "dependencies": ["models", "security"],
          "responsibilities": ["Authentication endpoints"]
        },
        {
          "name": "core/security.py",
          "type": "Utility Module",
          "dependencies": ["passlib", "jose"],
          "responsibilities": ["Password hashing", "JWT generation"]
        }
      ],
      "component_diagram_mermaid": "graph TD\\n    A[App] --> B[AuthProvider]\\n    A --> C[Router]\\n    C --> D[LoginPage]\\n    C --> E[TodosPage]\\n    D --> F[LoginForm]\\n    E --> G[TodoList]\\n    E --> H[AddTodoForm]\\n    G --> I[TodoItem]"
    },
    "data_flow": {
      "user_registration_flow": {
        "steps": [
          "1. User enters email and password in LoginForm",
          "2. Frontend validates input (email format, password length)",
          "3. POST /api/auth/register with credentials",
          "4. Backend validates request with Pydantic",
          "5. Check if email already exists in database",
          "6. Hash password with bcrypt",
          "7. Create User record in database",
          "8. Generate JWT token with user email",
          "9. Return token to frontend",
          "10. Frontend stores token in localStorage",
          "11. Redirect to todos page"
        ],
        "diagram_mermaid": "sequenceDiagram\\n    participant U as User\\n    participant F as Frontend\\n    participant B as Backend\\n    participant D as Database\\n    U->>F: Enter credentials\\n    F->>F: Validate input\\n    F->>B: POST /auth/register\\n    B->>B: Validate with Pydantic\\n    B->>D: Check email exists\\n    D->>B: Email available\\n    B->>B: Hash password\\n    B->>D: Insert user\\n    D->>B: User created\\n    B->>B: Generate JWT\\n    B->>F: Return token\\n    F->>F: Store token\\n    F->>U: Redirect to todos"
      },
      "create_todo_flow": {
        "steps": [
          "1. User clicks 'Add Todo' button",
          "2. User enters todo title and description",
          "3. Frontend sends POST /api/todos with JWT token",
          "4. Backend verifies JWT token",
          "5. Extract user_id from token",
          "6. Validate todo data",
          "7. Create Todo record with user_id",
          "8. Return created todo",
          "9. Frontend adds todo to local state",
          "10. UI updates to show new todo"
        ],
        "diagram_mermaid": "sequenceDiagram\\n    participant U as User\\n    participant F as Frontend\\n    participant B as Backend\\n    participant D as Database\\n    U->>F: Enter todo details\\n    F->>B: POST /todos (+ JWT)\\n    B->>B: Verify JWT\\n    B->>B: Extract user_id\\n    B->>D: Insert todo\\n    D->>B: Todo created\\n    B->>F: Return todo\\n    F->>F: Update state\\n    F->>U: Show new todo"
      }
    },
    "security_architecture": {
      "authentication": {
        "method": "JWT (JSON Web Tokens)",
        "flow": "User login → Backend generates JWT → Frontend stores in localStorage → Include in Authorization header",
        "token_structure": {
          "header": {"alg": "HS256", "typ": "JWT"},
          "payload": {"sub": "user@example.com", "exp": 1234567890},
          "signature": "HMACSHA256(header.payload, SECRET_KEY)"
        },
        "expiration": "7 days",
        "storage": "localStorage (client-side)"
      },
      "password_security": {
        "hashing_algorithm": "bcrypt",
        "salt_rounds": 12,
        "why": "bcrypt is slow by design, preventing brute-force attacks"
      },
      "authorization": {
        "method": "User ID from JWT token",
        "implementation": "Extract user_id from token, filter todos by user_id"
      },
      "input_validation": {
        "backend": "Pydantic models validate all inputs",
        "frontend": "Client-side validation for UX",
        "sql_injection_prevention": "SQLAlchemy ORM (no raw SQL)"
      },
      "cors": {
        "configuration": "Allow specific origin (frontend URL)",
        "credentials": "true",
        "methods": ["GET", "POST", "PUT", "DELETE"]
      }
    },
    "technology_justification": {
      "frontend": {
        "nextjs": "Server-side rendering, great DX, built-in routing",
        "typescript": "Type safety, better IDE support, fewer runtime errors",
        "zustand": "Simpler than Redux, perfect for small to medium apps",
        "tailwindcss": "Utility-first, fast development, consistent design"
      },
      "backend": {
        "fastapi": "Fast, modern, automatic API docs, great type support",
        "sqlalchemy": "Powerful ORM, prevents SQL injection, easy migrations",
        "pydantic": "Automatic validation, type safety, clear error messages",
        "bcrypt": "Industry standard for password hashing"
      },
      "database": {
        "postgresql": "Robust, ACID compliant, great for relational data"
      }
    }
  }
}

ARCHITECTURE DESIGN RULES:

1. **Follow Best Practices**:
   - Separation of concerns (layers)
   - Single responsibility principle
   - DRY (Don't Repeat Yourself)
   - Secure by default

2. **Database Design**:
   - Proper normalization (avoid redundancy)
   - Foreign keys for relationships
   - Indexes for frequently queried columns
   - ON DELETE CASCADE for dependent data
   - Timestamps for audit trail

3. **API Design**:
   - RESTful conventions (GET, POST, PUT, DELETE)
   - Proper HTTP status codes
   - Consistent response formats
   - Authentication on protected routes
   - Input validation
   - Error handling

4. **Component Architecture**:
   - Clear component hierarchy
   - Props flow down, events flow up
   - Reusable components
   - State management at appropriate level

5. **Security**:
   - Never store plaintext passwords
   - JWT for stateless auth
   - Input validation (prevent XSS, SQL injection)
   - CORS properly configured
   - HTTPS in production

6. **Scalability**:
   - Database indexes for performance
   - Stateless backend (can scale horizontally)
   - Caching where appropriate
   - Connection pooling

REMEMBER:
- Students will implement this design
- Make it clear, complete, and educational
- Explain WHY choices were made
- Include diagrams (Mermaid format)
"""

    def __init__(self):
        super().__init__(
            name="Architect Agent",
            role="system_architect",
            capabilities=[
                "system_architecture_design",
                "database_schema_design",
                "api_design",
                "component_architecture",
                "er_diagram_generation",
                "data_flow_design"
            ]
        )

    async def process(
        self,
        context: AgentContext,
        plan: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Design complete system architecture

        Args:
            context: Agent context with user request
            plan: Output from Planner Agent

        Returns:
            Dict with complete architecture design
        """
        try:
            logger.info(f"[Architect Agent] Designing architecture for project {context.project_id}")

            # Build architecture prompt
            enhanced_prompt = self._build_architecture_prompt(
                context.user_request,
                plan
            )

            # Call Claude API
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=enhanced_prompt,
                temperature=0.3  # Lower temperature for consistent architecture
            )

            # Parse JSON response
            architecture_output = self._parse_architecture(response)

            logger.info(f"[Architect Agent] Architecture designed successfully")

            return {
                "success": True,
                "agent": self.name,
                "architecture": architecture_output.get("architecture", {}),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Architect Agent] Error: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_architecture_prompt(
        self,
        user_request: str,
        plan: Optional[Dict]
    ) -> str:
        """Build architecture design prompt"""

        prompt_parts = [
            f"USER REQUEST:\n{user_request}\n"
        ]

        if plan:
            prompt_parts.append(f"\nPROJECT PLAN:\n{json.dumps(plan, indent=2)}\n")

        prompt_parts.append("""
TASK:
Design a complete, production-ready system architecture for this project. Include:

1. **System Overview**
   - Architecture style (e.g., Client-Server, Microservices)
   - Key components and layers
   - Technology stack justification

2. **Database Schema**
   - All entities (tables) with complete column definitions
   - Data types and constraints
   - Indexes for performance
   - Relationships with foreign keys
   - ER diagram in Mermaid format

3. **API Design**
   - All endpoints with paths and methods
   - Request/response formats
   - Authentication requirements
   - Error responses
   - Status codes

4. **Component Architecture**
   - Frontend component hierarchy
   - Backend module organization
   - Component diagram in Mermaid format

5. **Data Flow**
   - Key user journeys (registration, login, CRUD)
   - Sequence diagrams in Mermaid format

6. **Security Architecture**
   - Authentication method
   - Password storage
   - Authorization logic
   - Input validation

Make this architecture:
- Production-ready
- Secure
- Scalable
- Easy for students to implement

Output valid JSON following the specified format.
""")

        return "\n".join(prompt_parts)

    def _parse_architecture(self, response: str) -> Dict:
        """Parse JSON architecture output from Claude"""
        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[start:end]
            architecture_output = json.loads(json_str)

            return architecture_output

        except json.JSONDecodeError as e:
            logger.error(f"[Architect Agent] JSON parse error: {e}")
            raise ValueError(f"Invalid JSON in Claude response: {e}")

    def _extract_diagrams(self, architecture: Dict) -> List[Dict]:
        """Extract Mermaid diagrams from architecture"""
        diagrams = []

        # ER Diagram
        if "database_schema" in architecture.get("architecture", {}):
            er_diagram = architecture["architecture"]["database_schema"].get("er_diagram_mermaid")
            if er_diagram:
                diagrams.append({
                    "type": "ER Diagram",
                    "mermaid": er_diagram,
                    "description": "Database entity-relationship diagram"
                })

        # Component Diagram
        if "component_architecture" in architecture.get("architecture", {}):
            comp_diagram = architecture["architecture"]["component_architecture"].get("component_diagram_mermaid")
            if comp_diagram:
                diagrams.append({
                    "type": "Component Diagram",
                    "mermaid": comp_diagram,
                    "description": "Component hierarchy and relationships"
                })

        # Data Flow Diagrams
        if "data_flow" in architecture.get("architecture", {}):
            for flow_name, flow_data in architecture["architecture"]["data_flow"].items():
                if "diagram_mermaid" in flow_data:
                    diagrams.append({
                        "type": "Sequence Diagram",
                        "name": flow_name,
                        "mermaid": flow_data["diagram_mermaid"],
                        "description": f"Data flow for {flow_name}"
                    })

        return diagrams

    async def generate_api_documentation(
        self,
        architecture: Dict
    ) -> str:
        """Generate markdown API documentation from architecture"""

        api_design = architecture.get("architecture", {}).get("api_design", {})

        lines = [
            "# API Documentation\n",
            f"**Base URL**: {api_design.get('base_url', 'http://localhost:8000/api')}\n",
            f"**Authentication**: {api_design.get('authentication', 'JWT Bearer Token')}\n",
            "\n---\n"
        ]

        for endpoint in api_design.get("endpoints", []):
            lines.append(f"\n## {endpoint['method']} {endpoint['path']}\n")
            lines.append(f"{endpoint['description']}\n")

            if endpoint.get("authentication_required"):
                lines.append("\n**Authentication**: Required\n")

            if "request_body" in endpoint:
                lines.append(f"\n**Request Body**:\n```json\n{json.dumps(endpoint['request_body'], indent=2)}\n```\n")

            if "response_success" in endpoint:
                success = endpoint["response_success"]
                lines.append(f"\n**Success Response** ({success['status_code']}):\n```json\n{json.dumps(success.get('body'), indent=2)}\n```\n")

            if "response_errors" in endpoint:
                lines.append("\n**Error Responses**:\n")
                for error in endpoint["response_errors"]:
                    lines.append(f"- **{error['status_code']}**: {error['reason']}\n")

        return "\n".join(lines)


# Singleton instance
architect_agent = ArchitectAgent()
