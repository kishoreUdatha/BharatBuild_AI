# Multi-Agent System for BharatBuild AI

Complete multi-agent architecture for intelligent code generation, testing, debugging, and documentation.

## Overview

BharatBuild AI uses a specialized multi-agent system where each agent focuses on a specific aspect of software development. This approach provides:

- **Higher Quality**: Each agent is an expert in its domain
- **Better Learning**: Students see the complete development process
- **Flexibility**: Can run full workflow or individual agents
- **Maintainability**: Easy to improve or add agents

## Architecture

```
User Request
     ↓
Orchestrator (Routes to agents)
     ↓
┌────────────────────────────────────────────────┐
│  AGENT 1: Planner                              │
│  • Understands vague requests                  │
│  • Creates detailed project plans              │
│  • Identifies tech stack and requirements      │
└────────────────────────────────────────────────┘
     ↓ (plan)
┌────────────────────────────────────────────────┐
│  AGENT 2: Architect                            │
│  • Designs system architecture                 │
│  • Creates database schemas (ER diagrams)      │
│  • Defines API endpoints                       │
│  • Generates UML diagrams                      │
└────────────────────────────────────────────────┘
     ↓ (architecture)
┌────────────────────────────────────────────────┐
│  AGENT 3: Coder                                │
│  • Generates production-ready code             │
│  • Creates complete file structure             │
│  • Writes backend + frontend                   │
│  • Adds security & best practices              │
└────────────────────────────────────────────────┘
     ↓ (code files)
┌────────────────────────────────────────────────┐
│  AGENT 4: Tester                               │
│  • Generates comprehensive test suites         │
│  • Unit, integration, E2E tests                │
│  • Runs tests and reports coverage             │
│  • Aims for 80%+ coverage                      │
└────────────────────────────────────────────────┘
     ↓ (test results)
┌────────────────────────────────────────────────┐
│  AGENT 5: Debugger                             │
│  • Analyzes errors and exceptions              │
│  • Identifies root causes                      │
│  • Provides complete fixes                     │
│  • Teaches debugging techniques                │
└────────────────────────────────────────────────┘
     ↓ (if errors)
┌────────────────────────────────────────────────┐
│  AGENT 6: Explainer                            │
│  • Explains code in simple terms               │
│  • Generates comprehensive docs                │
│  • Creates README, API docs, tutorials         │
│  • Helps students understand concepts          │
└────────────────────────────────────────────────┘
     ↓
Complete Project with Code, Tests, and Documentation
```

## Agents

### 1. Planner Agent (Understanding)
**File**: `planner_agent.py`

**Role**: Turns vague user requests into detailed project plans

**Capabilities**:
- Understands abstract requests
- Identifies tech stack requirements
- Creates detailed feature lists
- Plans implementation steps
- Considers learning goals for students

**Input**: "Build a todo app"
**Output**:
```json
{
  "project_understanding": {
    "name": "Todo App",
    "type": "Full-stack CRUD application"
  },
  "technology_stack": {
    "frontend": "Next.js + TypeScript",
    "backend": "FastAPI + Python",
    "database": "PostgreSQL"
  },
  "features": [
    "User registration and authentication",
    "CRUD operations for todos",
    "Mark todos as complete"
  ],
  "implementation_steps": [...]
}
```

---

### 2. Architect Agent (Design)
**File**: `architect_agent.py`

**Role**: Designs system architecture and data models

**Capabilities**:
- Creates database schemas with ER diagrams
- Designs RESTful API endpoints
- Generates UML diagrams (component, sequence)
- Plans data flow
- Defines system components

**Input**: Plan from Planner Agent
**Output**:
```json
{
  "database_schema": {
    "entities": [
      {"name": "User", "fields": ["id", "email", "password_hash"]},
      {"name": "Todo", "fields": ["id", "title", "completed", "user_id"]}
    ],
    "er_diagram_mermaid": "erDiagram..."
  },
  "api_design": {
    "endpoints": [
      {"path": "/api/auth/register", "method": "POST"},
      {"path": "/api/todos", "method": "GET"}
    ]
  }
}
```

---

### 3. Coder Agent (Implementation)
**File**: `coder_agent.py`

**Role**: Generates complete, production-ready code

**Capabilities**:
- Generates full backend code (FastAPI, Express, Spring, Django)
- Generates full frontend code (React, Next.js, Vue)
- Creates complete folder structures
- Writes all configuration files
- Adds security best practices
- Includes educational comments

**Input**: Plan + Architecture
**Output**: 20+ complete files including:
- Backend models, API routes, authentication
- Frontend components, pages, state management
- Configuration (package.json, requirements.txt, .env)
- Setup instructions

**Example Files Generated**:
```
backend/
  app/
    models/user.py
    models/todo.py
    api/endpoints/auth.py
    api/endpoints/todos.py
    core/security.py
  requirements.txt

frontend/
  src/
    app/page.tsx
    components/TodoList.tsx
    store/authStore.ts
  package.json
```

---

### 4. Tester Agent (Quality Assurance)
**File**: `tester_agent.py`

**Role**: Generates comprehensive test suites

**Capabilities**:
- Generates unit tests for all functions
- Creates integration tests for APIs
- Writes E2E tests for user flows
- Runs tests and reports coverage
- Aims for 80%+ code coverage
- Tests edge cases and errors

**Input**: Generated code files
**Output**:
```json
{
  "test_files": [
    {
      "path": "backend/tests/test_auth.py",
      "tests_count": 8,
      "coverage_areas": ["register", "login", "token validation"]
    }
  ],
  "test_results": {
    "total_tests": 45,
    "passed": 45,
    "coverage": "87%"
  }
}
```

**Example Test**:
```python
def test_user_registration():
    # ARRANGE
    user_data = {"email": "test@example.com", "password": "Test123!"}

    # ACT
    response = client.post("/api/auth/register", json=user_data)

    # ASSERT
    assert response.status_code == 201
    assert "access_token" in response.json()
```

---

### 5. Debugger Agent (Error Resolution)
**File**: `debugger_agent.py`

**Role**: Analyzes and fixes errors

**Capabilities**:
- Analyzes runtime errors and exceptions
- Identifies root causes
- Provides complete fixes (not just patches)
- Explains errors in student-friendly terms
- Fixes syntax, type, logic, and build errors
- Teaches debugging strategies

**Input**: Error message + stack trace + code
**Output**:
```json
{
  "error_analysis": {
    "error_type": "TypeError",
    "root_cause": "SQLAlchemy filter() requires == not keyword args",
    "educational_explanation": "Think of it like SQL WHERE clause..."
  },
  "fixes": [
    {
      "file": "backend/app/api/todos.py",
      "original_code": "filter(user_id=user_id)",
      "fixed_code": "filter(Todo.user_id == user_id).all()",
      "explanation": "Changed to use == comparison...",
      "learning_points": [...]
    }
  ],
  "fixed": true
}
```

---

### 6. Explainer Agent (Documentation & Education)
**File**: `explainer_agent.py`

**Role**: Explains code and creates documentation

**Capabilities**:
- Explains code in simple, clear language
- Generates comprehensive README files
- Creates API documentation
- Writes architecture guides
- Uses analogies and examples
- Creates learning resources

**Input**: Code files + architecture
**Output**:
```json
{
  "documentation": {
    "key_concepts": [
      {
        "concept": "JWT Authentication",
        "simple_explanation": "JWT is like a ticket you show to prove who you are",
        "technical_explanation": "Stateless tokens containing signed user data...",
        "code_example": {...}
      }
    ],
    "code_walkthroughs": [...],
    "best_practices_used": [...],
    "learning_resources": [...]
  }
}
```

**Generated Files**:
- README.md - Project overview and setup
- API.md - API endpoint documentation
- ARCHITECTURE.md - System design explanation

---

## Orchestrator

**File**: `orchestrator.py`

The orchestrator coordinates agent workflows and manages dependencies.

### Workflow Modes

1. **FULL** (Default) - Complete workflow:
   ```
   Planner → Architect → Coder → Tester → Explainer
   ```

2. **CODE_ONLY** - Quick code generation:
   ```
   Coder → Tester
   ```

3. **DEBUG_ONLY** - Error fixing:
   ```
   Debugger
   ```

4. **EXPLAIN_ONLY** - Documentation:
   ```
   Explainer
   ```

5. **CUSTOM** - User-specified agents

### Usage Examples

#### Generate Complete Project
```python
from app.modules.agents import orchestrator

# Full workflow
async for event in orchestrator.generate_project(
    project_id="project-123",
    user_request="Build a todo app with authentication",
    include_tests=True,
    include_docs=True
):
    print(event)  # Progress events
```

#### Debug an Error
```python
result = await orchestrator.debug_error(
    project_id="project-123",
    error_message="TypeError: Cannot read property 'map' of undefined",
    stack_trace="at TodoList.tsx:42...",
    file_context=[...]
)
```

#### Explain Code
```python
result = await orchestrator.explain_code(
    project_id="project-123",
    code_files=[...],
    specific_request="Explain how JWT authentication works"
)
```

## Integration with Automation Engine

The multi-agent system integrates with the existing automation engine:

```python
# In automation_engine.py

from app.modules.agents import orchestrator, WorkflowMode

async def process_user_request(project_id, user_prompt, ...):
    # Option 1: Use multi-agent workflow
    async for event in orchestrator.execute_workflow(
        project_id=project_id,
        user_request=user_prompt,
        mode=WorkflowMode.FULL
    ):
        # Map agent events to automation events
        yield convert_agent_event_to_automation_event(event)

    # Option 2: Use single automation (existing)
    # ... existing code ...
```

## Benefits of Multi-Agent Architecture

### 1. **Separation of Concerns**
Each agent focuses on one task, making it:
- Easier to improve individual agents
- Easier to debug issues
- Easier to add new agents

### 2. **Educational Value**
Students see the complete development process:
- Planning → Design → Implementation → Testing → Documentation

### 3. **Higher Quality**
Specialized agents produce better results:
- Planner creates thorough project plans
- Architect designs proper data models
- Coder writes production-ready code
- Tester ensures high coverage
- Debugger teaches error resolution
- Explainer helps understanding

### 4. **Flexibility**
Can run:
- Full workflow for new projects
- Partial workflow for specific tasks
- Single agents for quick operations

### 5. **Scalability**
Easy to:
- Add new agents (e.g., DeploymentAgent, SecurityAuditor)
- Improve existing agents
- Run agents in parallel (where possible)

## Cost Considerations

**Full Workflow (6 agents)**:
- Higher token usage
- Better quality
- Complete automation

**Estimated Costs**:
- Simple project (todo app): ~$0.50 - $1.00
- Medium project (blog): ~$2.00 - $4.00
- Large project (e-commerce): ~$5.00 - $10.00

**Optimization Strategies**:
1. Use selective workflows (not always full)
2. Cache agent outputs
3. Use smaller models for simple tasks (haiku)
4. Batch similar operations

## File Structure

```
backend/app/modules/agents/
├── __init__.py                  # Exports all agents
├── base_agent.py                # Base class for all agents
├── planner_agent.py             # AGENT 1: Planning
├── architect_agent.py           # AGENT 2: Architecture
├── coder_agent.py               # AGENT 3: Code Generation
├── tester_agent.py              # AGENT 4: Testing
├── debugger_agent.py            # AGENT 5: Debugging
├── explainer_agent.py           # AGENT 6: Documentation
├── orchestrator.py              # Multi-agent coordinator
├── README.md                    # This file
└── CODER_AGENT_EXAMPLE.md       # Example output
```

## Future Enhancements

### Additional Agents
1. **DeploymentAgent**: Deploy to Vercel, Railway, AWS
2. **SecurityAuditorAgent**: Security vulnerability scanning
3. **PerformanceOptimizerAgent**: Performance analysis and optimization
4. **RefactorAgent**: Code refactoring suggestions
5. **MigrationAgent**: Upgrade dependencies, migrate to new frameworks

### Enhanced Orchestrator
1. Parallel agent execution (where possible)
2. Agent result caching
3. Workflow templates for common patterns
4. User-defined custom workflows
5. A/B testing different agent approaches

### Integration
1. Real-time collaboration (multiple users)
2. Version control integration (auto-commit)
3. CI/CD pipeline generation
4. Cloud deployment automation

## Contributing

To add a new agent:

1. Create new file: `backend/app/modules/agents/your_agent.py`
2. Inherit from `BaseAgent`
3. Implement `process()` method
4. Add comprehensive system prompt
5. Export in `__init__.py`
6. Update orchestrator if needed

Example:
```python
from app.modules.agents.base_agent import BaseAgent, AgentContext

class YourAgent(BaseAgent):
    SYSTEM_PROMPT = """Your agent instructions..."""

    def __init__(self):
        super().__init__(
            name="Your Agent",
            role="your_role",
            capabilities=["capability1", "capability2"]
        )

    async def process(self, context: AgentContext, **kwargs):
        # Your agent logic
        result = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3
        )
        return result

your_agent = YourAgent()
```

## License

MIT License - BharatBuild AI

## Support

For questions or issues, please open an issue on GitHub or contact the maintainers.

---

**Built with ❤️ for students learning to code**
