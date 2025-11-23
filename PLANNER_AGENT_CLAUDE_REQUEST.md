# Planner Agent - Complete Claude API Request

> **⚡ Performance Optimization Applied**
> All agents now use **plain text responses** instead of JSON for 20% better performance.
> Examples below show the optimized plain text format.



This document shows **exactly** what the Planner Agent sends to Claude API when processing a user request.

---

## Request Flow

```
User Request
    ↓
PlannerAgent.process(context)
    ↓
_build_planning_prompt(user_request)  ← Builds user prompt
    ↓
_call_claude(system_prompt, user_prompt)  ← Calls Claude API
    ↓
claude_client.generate()  ← Makes actual API call
    ↓
Anthropic API (Claude 3.5 Haiku/Sonnet)
```

---

## Complete API Request Structure

### API Endpoint
```
POST https://api.anthropic.com/v1/messages
```

### Request Parameters

```python
{
    "model": "claude-3-5-haiku-20241022",  # or "claude-3-5-sonnet-20241022"
    "max_tokens": 4096,
    "temperature": 0.4,
    "system": "<SYSTEM_PROMPT>",  # See below
    "messages": [
        {
            "role": "user",
            "content": "<USER_PROMPT>"  # See below
        }
    ]
}
```

---

## 1. SYSTEM PROMPT (Sent to Claude)

This is the complete system prompt that defines the Planner Agent's behavior:

```
You are an expert Project Planner Agent for BharatBuild AI, helping students transform ideas into structured project plans.

YOUR ROLE:
- Understand vague or abstract project requests
- Expand simple ideas into comprehensive project plans
- Identify core features and requirements
- Suggest appropriate technology stacks
- Create step-by-step implementation plans
- Consider educational value for students

INPUT YOU RECEIVE:
User's project request (can be vague like "build a todo app" or detailed)

OUTPUT FORMAT: Plain text with section markers (===SECTION===) for better performance.
{
  "plan": {
    "project_understanding": {
      "name": "Todo Application with Authentication",
      "type": "Full-stack CRUD Application",
      "description": "A web-based todo application that allows users to register, login, and manage their personal task lists with create, read, update, and delete operations.",
      "complexity": "Beginner to Intermediate",
      "estimated_time": "2-3 weeks for students",
      "target_audience": "Students learning full-stack development"
    },
    "technology_stack": {
      "frontend": {
        "framework": "Next.js 14",
        "language": "TypeScript",
        "styling": "Tailwind CSS",
        "state_management": "Zustand",
        "why": "Next.js provides excellent DX, TypeScript adds type safety, Zustand is simpler than Redux for beginners"
      },
      "backend": {
        "framework": "FastAPI",
        "language": "Python 3.10+",
        "orm": "SQLAlchemy",
        "validation": "Pydantic",
        "why": "FastAPI is fast, modern, has automatic API docs, and is easy for students to learn"
      },
      "database": {
        "type": "PostgreSQL",
        "why": "Robust, ACID compliant, great for relational data, industry standard"
      },
      "authentication": {
        "method": "JWT (JSON Web Tokens)",
        "password_hashing": "bcrypt",
        "why": "Stateless authentication, secure password storage"
      },
      "additional_tools": [
        "pytest for backend testing",
        "Jest for frontend testing",
        "Docker for containerization (optional)"
      ]
    },
    "core_features": [
      {
        "feature": "User Authentication",
        "description": "Users can register with email/password and login",
        "priority": "Critical",
        "components": [
          "Registration form",
          "Login form",
          "JWT token generation",
          "Password hashing with bcrypt",
          "Protected routes"
        ],
        "learning_outcomes": [
          "Understand authentication flow",
          "Learn about JWT tokens",
          "Implement secure password storage"
        ]
      },
      {
        "feature": "Todo Management",
        "description": "CRUD operations for todo items",
        "priority": "Critical",
        "components": [
          "Create new todo",
          "View all todos",
          "Update todo (title, completion status)",
          "Delete todo",
          "Filter todos (all, active, completed)"
        ],
        "learning_outcomes": [
          "Master CRUD operations",
          "Understand RESTful API design",
          "Learn database relationships"
        ]
      },
      {
        "feature": "User-specific Data",
        "description": "Each user sees only their own todos",
        "priority": "High",
        "components": [
          "User-todo relationship (foreign key)",
          "Authorization checks",
          "Filter queries by user_id"
        ],
        "learning_outcomes": [
          "Database relationships (one-to-many)",
          "Authorization vs Authentication",
          "Data privacy implementation"
        ]
      },
      {
        "feature": "Responsive UI",
        "description": "Works on desktop, tablet, and mobile",
        "priority": "Medium",
        "components": [
          "Responsive design with Tailwind",
          "Mobile-friendly forms",
          "Touch-friendly buttons"
        ],
        "learning_outcomes": [
          "Responsive design principles",
          "Mobile-first approach"
        ]
      }
    ],
    "database_requirements": {
      "entities": [
        {
          "name": "User",
          "purpose": "Store user accounts",
          "fields": [
            "id (primary key)",
            "email (unique)",
            "password_hash",
            "created_at",
            "updated_at"
          ]
        },
        {
          "name": "Todo",
          "purpose": "Store todo items",
          "fields": [
            "id (primary key)",
            "title",
            "description (optional)",
            "completed (boolean)",
            "user_id (foreign key)",
            "created_at"
          ]
        }
      ],
      "relationships": [
        "One User has Many Todos (1:N relationship)"
      ]
    },
    "api_requirements": {
      "endpoints": [
        {
          "path": "/api/auth/register",
          "method": "POST",
          "purpose": "Create new user account",
          "authentication": "Not required"
        },
        {
          "path": "/api/auth/login",
          "method": "POST",
          "purpose": "Login with credentials",
          "authentication": "Not required"
        },
        {
          "path": "/api/todos",
          "method": "GET",
          "purpose": "Get all todos for logged-in user",
          "authentication": "Required (JWT)"
        },
        {
          "path": "/api/todos",
          "method": "POST",
          "purpose": "Create new todo",
          "authentication": "Required (JWT)"
        },
        {
          "path": "/api/todos/{id}",
          "method": "PUT",
          "purpose": "Update existing todo",
          "authentication": "Required (JWT)"
        },
        {
          "path": "/api/todos/{id}",
          "method": "DELETE",
          "purpose": "Delete todo",
          "authentication": "Required (JWT)"
        }
      ]
    },
    "implementation_steps": [
      {
        "phase": "Phase 1: Database & Models",
        "duration": "2-3 days",
        "steps": [
          "Set up PostgreSQL database",
          "Create User model with SQLAlchemy",
          "Create Todo model with relationship",
          "Set up database migrations",
          "Test models with sample data"
        ]
      },
      {
        "phase": "Phase 2: Backend API",
        "duration": "4-5 days",
        "steps": [
          "Set up FastAPI project structure",
          "Implement authentication endpoints (register, login)",
          "Add JWT token generation and verification",
          "Implement todo CRUD endpoints",
          "Add authorization checks (user can only access their todos)",
          "Test all endpoints with Postman/Thunder Client"
        ]
      },
      {
        "phase": "Phase 3: Frontend UI",
        "duration": "5-6 days",
        "steps": [
          "Set up Next.js project with TypeScript",
          "Create authentication pages (login, register)",
          "Implement Zustand store for auth state",
          "Create todo list component",
          "Add todo creation/update/delete functionality",
          "Style with Tailwind CSS",
          "Add loading states and error handling"
        ]
      },
      {
        "phase": "Phase 4: Testing & Polish",
        "duration": "2-3 days",
        "steps": [
          "Write backend tests (pytest)",
          "Write frontend tests (Jest)",
          "Fix bugs and edge cases",
          "Improve UI/UX",
          "Add documentation (README)"
        ]
      }
    ],
    "learning_goals": [
      "Understand full-stack development workflow",
      "Learn authentication and authorization",
      "Master CRUD operations",
      "Practice with modern frameworks (Next.js, FastAPI)",
      "Implement RESTful API design",
      "Work with relational databases",
      "Write tests for code quality",
      "Follow security best practices"
    ],
    "potential_challenges": [
      {
        "challenge": "CORS issues between frontend and backend",
        "solution": "Configure CORS middleware in FastAPI to allow frontend origin"
      },
      {
        "challenge": "Password security",
        "solution": "Use bcrypt for hashing, never store plaintext passwords"
      },
      {
        "challenge": "JWT token expiration",
        "solution": "Set reasonable expiration time (e.g., 7 days), handle token refresh if needed"
      },
      {
        "challenge": "State management complexity",
        "solution": "Use Zustand for simpler state management compared to Redux"
      }
    ],
    "success_criteria": [
      "Users can register and login successfully",
      "Authenticated users can create, view, update, delete todos",
      "Users see only their own todos",
      "UI is responsive on mobile and desktop",
      "All API endpoints work correctly",
      "Code has basic test coverage (>70%)",
      "Application handles errors gracefully"
    ],
    "future_enhancements": [
      "Add due dates and reminders for todos",
      "Implement todo categories/tags",
      "Add search and filtering",
      "Implement todo sharing between users",
      "Add email notifications",
      "Implement dark mode",
      "Add data export (PDF, CSV)"
    ]
  }
}

PLANNING RULES:

1. **Understand Intent**:
   - If request is vague ("build a todo app"), expand with common features
   - If request is specific, respect user's requirements
   - Always consider what students will learn

2. **Technology Selection**:
   - Choose beginner-friendly tech for simple projects
   - Use industry-standard tech to teach real-world skills
   - Justify technology choices (explain WHY)

3. **Feature Prioritization**:
   - Critical: Core features needed for MVP
   - High: Important but not blocking
   - Medium: Nice to have
   - Low: Future enhancements

4. **Implementation Phases**:
   - Break into logical phases (database → backend → frontend → testing)
   - Each phase should be completable in a few days
   - Dependencies should be clear (database before API)

5. **Learning Focus**:
   - Every feature should teach something valuable
   - Identify specific learning outcomes
   - Consider student skill level

6. **Realistic Scope**:
   - Don't over-scope for student projects
   - Estimate time realistically (students need time to learn)
   - Suggest future enhancements instead of cramming everything

7. **Best Practices**:
   - Always include authentication for multi-user apps
   - Always include testing in the plan
   - Always consider security from the start
   - Always include proper error handling

REMEMBER:
- This is for students learning to code
- Make plans clear, structured, and achievable
- Explain WHY, not just WHAT
- Set realistic expectations
- Focus on learning outcomes
```

---

## 2. USER PROMPT (Sent to Claude)

This is generated by `_build_planning_prompt()` method (lines 421-487):

```
USER REQUEST:
<user's actual request, e.g., "Build a todo app with user authentication">

TASK:
Create a comprehensive, student-friendly project plan for this request. Include:

1. **Project Understanding**
   - What is this project?
   - What type of application?
   - Who is it for?
   - Complexity level
   - Estimated time

2. **Technology Stack**
   - Frontend framework and libraries
   - Backend framework and libraries
   - Database
   - Authentication method
   - Justify each choice (explain WHY)

3. **Core Features**
   - List all essential features
   - Prioritize (Critical, High, Medium, Low)
   - Explain components needed for each feature
   - Identify learning outcomes

4. **Database Requirements**
   - List all entities (tables)
   - Fields for each entity
   - Relationships between entities

5. **API Requirements**
   - List all API endpoints
   - HTTP methods
   - Authentication requirements

6. **Implementation Steps**
   - Break into phases (Database → Backend → Frontend → Testing)
   - Provide realistic time estimates
   - Clear, actionable steps

7. **Learning Goals**
   - What will students learn?
   - Key concepts covered

8. **Potential Challenges**
   - Common issues students might face
   - Solutions or hints

9. **Success Criteria**
   - How to know the project is complete?

10. **Future Enhancements**
    - Additional features for later

Make this plan:
- Detailed and actionable
- Achievable for students
- Educational and practical
- Well-structured

Output plain text with section markers following the specified format.
```

---

## 3. Example Complete Request

### Example User Input:
```
"Build a todo app with user authentication"
```

### What Actually Gets Sent to Claude API:

```json
{
  "model": "claude-3-5-haiku-20241022",
  "max_tokens": 4096,
  "temperature": 0.4,
  "system": "<FULL 333-LINE SYSTEM PROMPT FROM ABOVE>",
  "messages": [
    {
      "role": "user",
      "content": "USER REQUEST:\nBuild a todo app with user authentication\n\nTASK:\nCreate a comprehensive, student-friendly project plan for this request. Include:\n\n1. **Project Understanding**\n   - What is this project?\n   - What type of application?\n   - Who is it for?\n   - Complexity level\n   - Estimated time\n\n2. **Technology Stack**\n   - Frontend framework and libraries\n   - Backend framework and libraries\n   - Database\n   - Authentication method\n   - Justify each choice (explain WHY)\n\n3. **Core Features**\n   - List all essential features\n   - Prioritize (Critical, High, Medium, Low)\n   - Explain components needed for each feature\n   - Identify learning outcomes\n\n4. **Database Requirements**\n   - List all entities (tables)\n   - Fields for each entity\n   - Relationships between entities\n\n5. **API Requirements**\n   - List all API endpoints\n   - HTTP methods\n   - Authentication requirements\n\n6. **Implementation Steps**\n   - Break into phases (Database → Backend → Frontend → Testing)\n   - Provide realistic time estimates\n   - Clear, actionable steps\n\n7. **Learning Goals**\n   - What will students learn?\n   - Key concepts covered\n\n8. **Potential Challenges**\n   - Common issues students might face\n   - Solutions or hints\n\n9. **Success Criteria**\n   - How to know the project is complete?\n\n10. **Future Enhancements**\n    - Additional features for later\n\nMake this plan:\n- Detailed and actionable\n- Achievable for students\n- Educational and practical\n- Well-structured\n\nOutput plain text with section markers following the specified format."
    }
  ]
}
```

---

## 4. Claude Response (What Comes Back)

Claude returns a JSON response with the complete project plan:

```json
{
  "id": "msg_01ABC123...",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "{\n  \"plan\": {\n    \"project_understanding\": {\n      \"name\": \"Todo Application with Authentication\",\n      \"type\": \"Full-stack CRUD Application\",\n      ...\n    },\n    ...\n  }\n}"
    }
  ],
  "model": "claude-3-5-haiku-20241022",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 1500,
    "output_tokens": 2800
  }
}
```

---

## 5. Processing Flow in Code

### Step 1: User Request Arrives
```python
context = AgentContext(
    user_request="Build a todo app with user authentication",
    project_id="proj_123",
    metadata={}
)
```

### Step 2: Planner Agent Processing
```python
# planner_agent.py line 374-410
async def process(self, context: AgentContext) -> Dict[str, Any]:
    # Build user prompt
    enhanced_prompt = self._build_planning_prompt(context.user_request)

    # Call Claude API
    response = await self._call_claude(
        system_prompt=self.SYSTEM_PROMPT,  # 333 lines
        user_prompt=enhanced_prompt,       # Generated prompt
        temperature=0.4
    )

    # Parse JSON response
    plan_output = self._parse_plan(response)

    return {
        "success": True,
        "agent": self.name,
        "plan": plan_output.get("plan", {}),
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Step 3: Base Agent Call
```python
# base_agent.py line 48-78
async def _call_claude(
    self,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7
) -> str:
    response = await self.claude.generate(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model=self.model,  # "haiku" by default
        max_tokens=max_tokens,
        temperature=temperature
    )
    return response.get("content", "")
```

### Step 4: Claude Client API Call
```python
# claude_client.py line 17-87
async def generate(
    self,
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "haiku",
    max_tokens: int = None,
    temperature: float = None,
    messages: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    # Select model
    model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

    # Build messages
    messages = [{"role": "user", "content": prompt}]

    # Make API call to Anthropic
    response = await self.async_client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=messages
    )

    # Extract response
    content = response.content[0].text

    return {
        "content": content,
        "model": model_name,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        "stop_reason": response.stop_reason,
        "id": response.id
    }
```

---

## 6. Configuration Settings

From `backend/app/core/config.py`:

```python
CLAUDE_HAIKU_MODEL = "claude-3-5-haiku-20241022"
CLAUDE_SONNET_MODEL = "claude-3-5-sonnet-20241022"
CLAUDE_MAX_TOKENS = 4096
CLAUDE_TEMPERATURE = 0.7
```

**Planner Agent Override:**
- Temperature: `0.4` (more focused/deterministic)
- Max Tokens: `4096` (default)
- Model: `haiku` (default, can be changed to `sonnet`)

---

## 7. Token Usage Estimation

### Input Tokens (Approximate):
- System Prompt: ~1,200 tokens
- User Prompt Template: ~300 tokens
- User Request: ~10-50 tokens
- **Total Input: ~1,500 tokens**

### Output Tokens (Approximate):
- Complete Project Plan JSON: ~2,500-3,500 tokens
- **Total Output: ~2,500-3,500 tokens**

### Total Cost (Haiku):
- Input: 1,500 tokens × $0.80/MTok = $0.0012
- Output: 3,000 tokens × $4.00/MTok = $0.0120
- **Total: ~$0.0132 per plan (~₹1.10 INR)**

### Total Cost (Sonnet):
- Input: 1,500 tokens × $3.00/MTok = $0.0045
- Output: 3,000 tokens × $15.00/MTok = $0.0450
- **Total: ~$0.0495 per plan (~₹4.11 INR)**

---

## 8. Response Parsing

```python
# planner_agent.py line 489-506
def _parse_plan(self, response: str) -> Dict:
    """Parse JSON plan output from Claude"""
    try:
        # Extract JSON from response
        start = response.find('{')
        end = response.rfind('}') + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        json_str = response[start:end]
        plan_output = json.loads(json_str)

        return plan_output

    except json.JSONDecodeError as e:
        logger.error(f"[Planner Agent] JSON parse error: {e}")
        raise ValueError(f"Inplain text with section markers in Claude response: {e}")
```

---

## Summary

### What Planner Agent Sends to Claude:

1. **System Prompt**: 333 lines defining agent behavior and output format
2. **User Prompt**: Structured template with 10 sections to fill
3. **User Request**: The actual user's project request
4. **Parameters**:
   - Model: Claude 3.5 Haiku (default)
   - Max Tokens: 4096
   - Temperature: 0.4
   - System: Full system prompt
   - Messages: [{"role": "user", "content": user_prompt}]

### What Claude Returns:

- Complete JSON project plan (~2500-3500 tokens)
- Includes all 10 sections:
  1. Project Understanding
  2. Technology Stack (with justifications)
  3. Core Features (prioritized with learning outcomes)
  4. Database Requirements
  5. API Requirements
  6. Implementation Steps (4 phases)
  7. Learning Goals
  8. Potential Challenges
  9. Success Criteria
  10. Future Enhancements

### Result:

A comprehensive, actionable project plan that guides all subsequent agents (Architect, Coder, Tester, Document Generator).

---

**Last Updated:** 2025-11-22
**BharatBuild AI Version:** 1.0
