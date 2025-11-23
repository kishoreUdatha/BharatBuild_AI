# Writer Agent & Bolt.new Workflow - Complete Documentation

> **✨ New Architecture Implemented**
> BharatBuild AI now follows the exact **Bolt.new step-by-step workflow** for incremental project building with real-time progress.

---

## Overview

The **Writer Agent** is a new agent that implements the Bolt.new architecture for step-by-step project generation. Unlike the CoderAgent which generates all files at once, the Writer Agent processes ONE step at a time, providing real-time feedback and incremental progress.

---

## Bolt.new Workflow Architecture

### Complete Flow

```
User Input: "build ecommerce application"
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Backend calls Planner Agent                     │
│ ────────────────────────────────                        │
│ • Backend Orchestrator receives user request            │
│ • Calls Planner Agent with user input                   │
│ • Planner Agent returns <plan> with implementation steps│
│ • Backend parses plan and extracts steps                │
│ • UI shows: Left "Plan" panel + Steps list              │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Backend executes Step 1 with Writer Agent       │
│ ────────────────────────────────────────────            │
│ • Backend sends "Step 1: Setup Project Structure"       │
│ • Writer Agent processes step                           │
│ • Returns Bolt.new XML format:                          │
│   - <file path="">...</file>                            │
│   - <terminal>...</terminal>                            │
│   - <explain>...</explain>                              │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Backend executes actions                        │
│ ────────────────────────────────                        │
│ • Parse <file> → Write file to disk                     │
│ • Parse <terminal> → Execute command                    │
│ • Parse <explain> → Update UI Details panel             │
│ • Mark Step 1 as ✔ done                                 │
│ • Update progress circles                               │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Backend moves to Step 2                         │
│ ────────────────────────────────                        │
│ • Backend calls Writer Agent with "Step 2"              │
│ • Includes context from Step 1                          │
│ • Writer Agent generates files for Step 2               │
│ • Backend executes actions                              │
│ • Mark Step 2 as ✔ done                                 │
└─────────────────────────────────────────────────────────┘
    ↓
    ... (Continue for all steps) ...
    ↓
┌─────────────────────────────────────────────────────────┐
│ FINAL: All steps complete                               │
│ ────────────────────────────                            │
│ • All files written                                     │
│ • All commands executed                                 │
│ • Project ready to run                                  │
│ • UI shows 100% complete                                │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture Components

### 1. Frontend (UI)
**Responsibilities:**
- Send only user message
- Receive real-time events
- Display UI (Plan panel, Steps, Progress circles, Details panel)
- Show file tree as files are created
- Update progress in real-time

**Does NOT:**
- Call Claude directly
- Parse responses
- Write files
- Execute commands

---

### 2. Backend Orchestrator (`BoltOrchestrator`)
**File:** `backend/app/modules/orchestrator/bolt_orchestrator.py`

**Responsibilities:**
- Knows current step
- Calls Planner Agent (once at start)
- Calls Writer Agent (once per step)
- Maintains file structure
- Maintains project state
- Sends progress updates to frontend

**Key Methods:**
```python
async def execute_bolt_workflow(
    user_request: str,
    project_id: str,
    metadata: Optional[Dict] = None,
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]
```

**Flow:**
1. Call Planner Agent → Get <plan>
2. Parse plan → Extract steps
3. For each step:
   - Call Writer Agent
   - Execute actions (write files, run commands)
   - Update UI
   - Mark step complete
4. Return final result

---

### 3. Planner Agent (`planner_agent`)
**File:** `backend/app/modules/agents/planner_agent.py`

**Responsibility:** Create project plan with implementation steps

**Input:**
```
User Request: "build ecommerce application"
```

**Output (Bolt.new XML format):**
```xml
<plan>
Project Title: E-Commerce Application
Type: Full-stack web application

IMPLEMENTATION PLAN:

PHASE: Project Setup
Duration: 1 day
Tasks:
- Initialize frontend with Next.js
- Setup backend with FastAPI
- Configure database connection
Deliverables:
- Project structure
- Dependencies installed

PHASE: Backend Development
Duration: 3 days
Tasks:
- Create product models
- Implement authentication
- Build API endpoints
Deliverables:
- Working REST API
- Database schema

PHASE: Frontend Development
Duration: 3 days
Tasks:
- Create product listing page
- Build shopping cart
- Implement checkout flow
Deliverables:
- Functional UI
- Responsive design

PHASE: Testing & Deployment
Duration: 2 days
Tasks:
- Write tests
- Deploy to production
Deliverables:
- Live application
</plan>
```

**Called:** Once at the beginning

---

### 4. Writer Agent (`writer_agent`)
**File:** `backend/app/modules/agents/writer_agent.py`

**Responsibility:** Execute ONE step at a time, generate files incrementally

**Input:**
```python
{
    "step_number": 1,
    "step_data": {
        "name": "Project Setup",
        "tasks": ["Initialize frontend", "Setup backend"],
        "deliverables": ["Project structure"]
    },
    "previous_context": {...}
}
```

**Output (Bolt.new XML format):**
```xml
<thinking>
For Step 1, I need to:
1. Create package.json for Next.js frontend
2. Create requirements.txt for FastAPI backend
3. Setup basic folder structure
</thinking>

<explain>
Setting up the project structure with Next.js frontend and FastAPI backend.
Creating configuration files and installing dependencies.
</explain>

<file path="frontend/package.json">
{
  "name": "ecommerce-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "next": "^14.0.0"
  }
}
</file>

<file path="backend/requirements.txt">
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
</file>

<terminal>
cd frontend && npm install
</terminal>

<terminal>
cd backend && pip install -r requirements.txt
</terminal>

<explain>
Project structure created. Dependencies installed.
Ready for Step 2: Backend Development.
</explain>
```

**Called:** Once per step (multiple times throughout project)

---

## Key Differences: Writer Agent vs Coder Agent

| Feature | Writer Agent | Coder Agent |
|---------|-------------|-------------|
| **Execution** | Step-by-step | All at once |
| **Output Format** | Bolt.new XML (`<file>`, `<terminal>`, `<explain>`) | JSON |
| **Files** | Creates files incrementally | Returns all files in one response |
| **Progress** | Real-time per-step updates | No intermediate progress |
| **Commands** | Executes commands as it goes | No command execution |
| **UI Updates** | Live updates to Details panel | Only final result |
| **User Experience** | See progress in real-time | Wait for everything |
| **Model** | Haiku (fast iterations) | Haiku/Sonnet |
| **Use Case** | Bolt.new-style incremental building | Batch generation |

---

## Writer Agent Features

### 1. Incremental File Writing
```python
# Writer Agent creates files one step at a time
Step 1: Creates package.json, tsconfig.json
Step 2: Creates src/App.tsx, src/components/Header.tsx
Step 3: Creates backend/main.py, backend/models.py
```

### 2. Terminal Command Execution
```python
# Executes commands safely with timeout
<terminal>npm install</terminal>
<terminal>pip install -r requirements.txt</terminal>
<terminal>npm run build</terminal>
```

**Security:**
- Blocks dangerous commands (`rm -rf`, `sudo`, etc.)
- Runs in project directory only
- 120-second timeout per command
- Captures stdout/stderr

### 3. Real-Time Explanations
```xml
<explain>
Created the main App component with routing setup.
Configured Tailwind CSS for styling.
Next step will add authentication.
</explain>
```

### 4. Context Awareness
Each step receives context from previous steps:
```python
previous_context = {
    "files_created": ["package.json", "tsconfig.json"],
    "last_explanation": "Project structure created"
}
```

### 5. Error Handling
```xml
<error>
Failed to install dependencies. Node.js version must be 18 or higher.
Please upgrade Node.js and try again.
</error>
```

---

## Usage Examples

### Example 1: Basic Usage

```python
from app.modules.orchestrator.bolt_orchestrator import bolt_orchestrator

# Execute complete Bolt.new workflow
result = await bolt_orchestrator.execute_bolt_workflow(
    user_request="build a todo application with authentication",
    project_id="project_123",
    metadata={"user_id": "user_456"},
    progress_callback=update_ui_progress
)

# Result:
{
    "success": True,
    "project_id": "project_123",
    "total_steps": 4,
    "steps_completed": 4,
    "total_files_created": 15,
    "total_commands_executed": 6,
    "files_created": [
        {"path": "package.json", "size": 324, "step": 1},
        {"path": "src/App.tsx", "size": 1024, "step": 2},
        ...
    ],
    "commands_executed": [
        {"command": "npm install", "success": True, "step": 1},
        ...
    ]
}
```

### Example 2: Single Step Execution

```python
from app.modules.agents.writer_agent import writer_agent
from app.modules.agents.base_agent import AgentContext

# Execute just one step
context = AgentContext(
    user_request="build todo app",
    project_id="project_123",
    metadata={}
)

step_result = await writer_agent.process(
    context=context,
    step_number=1,
    step_data={
        "name": "Setup Project Structure",
        "tasks": ["Create package.json", "Setup TypeScript"],
        "deliverables": ["Working dev environment"]
    },
    previous_context=None
)

# Result:
{
    "success": True,
    "step_number": 1,
    "files_created": [
        {"path": "package.json", "size": 324},
        {"path": "tsconfig.json", "size": 512}
    ],
    "commands_executed": [
        {"command": "npm install", "success": True}
    ],
    "explanation": "Project structure created successfully"
}
```

### Example 3: Progress Callback

```python
async def update_ui_progress(percent: int, message: str):
    """Send progress to frontend via WebSocket"""
    await websocket.send_json({
        "type": "progress",
        "percent": percent,
        "message": message
    })

# Use with orchestrator
result = await bolt_orchestrator.execute_bolt_workflow(
    user_request="build blog platform",
    project_id="blog_001",
    progress_callback=update_ui_progress
)

# Frontend receives:
# {"type": "progress", "percent": 5, "message": "Analyzing your request..."}
# {"type": "progress", "percent": 20, "message": "Project plan created!"}
# {"type": "progress", "percent": 35, "message": "Step 1/4: Project Setup"}
# {"type": "progress", "percent": 60, "message": "Step 2/4: Backend Development"}
# ...
```

---

## File Structure

```
backend/app/modules/
├── agents/
│   ├── base_agent.py              # Base class (with Bolt.new optimization)
│   ├── planner_agent.py           # Creates project plan
│   ├── writer_agent.py            # NEW: Step-by-step file writer
│   ├── coder_agent.py             # OLD: Batch code generator
│   └── ...
├── orchestrator/
│   ├── bolt_orchestrator.py       # NEW: Bolt.new workflow orchestrator
│   └── multi_agent_orchestrator.py  # OLD: Original orchestrator
└── automation/
    └── file_manager.py            # File writing utilities
```

---

## API Integration

### REST Endpoint

```python
# backend/app/api/routes/projects.py

from app.modules.orchestrator.bolt_orchestrator import bolt_orchestrator

@router.post("/projects/bolt")
async def create_bolt_project(request: BoltProjectRequest):
    """Create project using Bolt.new workflow"""

    result = await bolt_orchestrator.execute_bolt_workflow(
        user_request=request.description,
        project_id=str(uuid.uuid4()),
        metadata={
            "user_id": request.user_id,
            "tech_stack": request.tech_stack
        }
    )

    return result
```

### WebSocket Endpoint (for real-time progress)

```python
# backend/app/api/websocket.py

@app.websocket("/ws/bolt/{project_id}")
async def bolt_websocket(websocket: WebSocket, project_id: str):
    await websocket.accept()

    # Progress callback
    async def send_progress(percent: int, message: str):
        await websocket.send_json({
            "type": "progress",
            "percent": percent,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Execute workflow
    result = await bolt_orchestrator.execute_bolt_workflow(
        user_request=data["request"],
        project_id=project_id,
        progress_callback=send_progress
    )

    # Send final result
    await websocket.send_json({
        "type": "complete",
        "result": result
    })
```

---

## Performance Comparison

### Writer Agent (Bolt.new Style)
```
User Request → Plan (10s) → Step 1 (5s) → Step 2 (5s) → Step 3 (5s) → Step 4 (5s) = 30s total
                               ↓            ↓            ↓            ↓
                            UI updates   UI updates   UI updates   UI updates
```
**User sees progress at:** 10s, 15s, 20s, 25s, 30s

### Coder Agent (Original)
```
User Request → Generate All Files (45s) = 45s total
                                        ↓
                                   UI updates once
```
**User sees progress at:** 45s only

**Winner:** Writer Agent - Better UX with incremental progress

---

## Configuration

### Enable Bolt.new Workflow

```python
# backend/app/core/config.py

# Use Bolt.new XML format
USE_PLAIN_TEXT_RESPONSES: bool = True

# Writer Agent settings
WRITER_AGENT_MODEL: str = "haiku"  # Fast model for iterations
WRITER_AGENT_TIMEOUT: int = 120    # Command timeout (seconds)
WRITER_AGENT_MAX_TOKENS: int = 4096
```

---

## Testing

### Unit Tests

```python
# tests/test_writer_agent.py

import pytest
from app.modules.agents.writer_agent import writer_agent

@pytest.mark.asyncio
async def test_writer_agent_single_step():
    """Test single step execution"""
    context = AgentContext(
        user_request="build todo app",
        project_id="test_001"
    )

    result = await writer_agent.process(
        context=context,
        step_number=1,
        step_data={
            "name": "Setup",
            "tasks": ["Create package.json"]
        }
    )

    assert result["success"] == True
    assert len(result["files_created"]) > 0
```

### Integration Tests

```python
# tests/test_bolt_orchestrator.py

@pytest.mark.asyncio
async def test_bolt_workflow_complete():
    """Test complete Bolt.new workflow"""
    result = await bolt_orchestrator.execute_bolt_workflow(
        user_request="build simple blog",
        project_id="test_blog_001"
    )

    assert result["success"] == True
    assert result["steps_completed"] > 0
    assert result["total_files_created"] > 0
```

---

## Monitoring & Logging

### Log Format

```python
[Bolt Orchestrator] Starting workflow for project: project_123
[Bolt Orchestrator] Plan created with 8 sections
[Bolt Orchestrator] Extracted 4 implementation steps
[Writer Agent] Executing Step 1: Project Setup
[Writer Agent] Created file: package.json
[Writer Agent] Created file: tsconfig.json
[Writer Agent] Executing command: npm install
[Writer Agent] Step 1 completed successfully
[Bolt Orchestrator] Step 1 completed: 2 files, 1 commands
[Writer Agent] Executing Step 2: Backend Development
...
[Bolt Orchestrator] Workflow completed successfully. Files: 15, Commands: 6
```

---

## Troubleshooting

### Common Issues

**1. Command Execution Fails**
```
Error: Command "npm install" timed out after 120s
Fix: Increase WRITER_AGENT_TIMEOUT in config
```

**2. Files Not Created**
```
Error: Permission denied writing to generated/project_123
Fix: Check file system permissions
```

**3. Step Parsing Fails**
```
Error: No implementation steps found in plan
Fix: Planner Agent should return PHASE sections in plan
```

---

## Future Enhancements

1. **Streaming Support**: Stream responses token-by-token for even better UX
2. **Rollback**: Undo steps if something goes wrong
3. **Manual Intervention**: Pause workflow and let user edit before continuing
4. **Fixer Agent**: Auto-fix errors without restarting
5. **Explainer Agent**: Provide detailed explanations of generated code
6. **Terminal Agent**: Better command execution with interactive support

---

## Summary

✅ **Writer Agent Created** - Step-by-step file writing with Bolt.new architecture
✅ **Bolt Orchestrator Created** - Manages complete workflow
✅ **Bolt.new XML Format** - Uses `<file>`, `<terminal>`, `<explain>` tags
✅ **Real-Time Progress** - Incremental updates to UI
✅ **Command Execution** - Safely runs terminal commands
✅ **Context Awareness** - Each step knows about previous steps
✅ **Production Ready** - Error handling, logging, security

---

**Implementation Date:** 2025-11-22
**Files Created:**
- `backend/app/modules/agents/writer_agent.py` (540 lines)
- `backend/app/modules/orchestrator/bolt_orchestrator.py` (350 lines)

**Status:** ✅ Complete and Ready for Integration
