# 🎯 Dynamic Orchestrator - Complete Integration Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backend Setup](#backend-setup)
4. [API Endpoints](#api-endpoints)
5. [Frontend Integration](#frontend-integration)
6. [Workflows](#workflows)
7. [Agent Configuration](#agent-configuration)
8. [Usage Examples](#usage-examples)
9. [Testing](#testing)

---

## 🎬 Overview

The **Dynamic Orchestrator** is a Bolt.new-style backend system that provides:

✅ **Multi-Agent Routing** - Intelligently routes work to specialized agents
✅ **Dynamic Prompts/Models** - Update agent behavior at runtime (no restart needed)
✅ **Configurable Workflows** - `plan → write → run → fix → docs` loop
✅ **File Patching** - Apply unified diffs for incremental updates
✅ **SSE Streaming** - Real-time event streaming to frontend
✅ **Retry Logic** - Automatic retries with exponential backoff
✅ **Progress Tracking** - 0-100% progress with step-by-step updates

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  StreamingClient.streamOrchestratorWorkflow()        │  │
│  │  - Connects to /orchestrator/execute                 │  │
│  │  - Receives SSE events                               │  │
│  │  - Updates Monaco editor in real-time                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ SSE Events
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  /api/v1/orchestrator/execute                        │  │
│  │  - POST endpoint with SSE streaming                  │  │
│  │  - Returns real-time workflow events                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  DynamicOrchestrator                                 │  │
│  │  - Executes workflows step-by-step                   │  │
│  │  - Manages agent execution with retries              │  │
│  │  - Streams events to frontend                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  WorkflowEngine                                      │  │
│  │  - Loads workflow definitions                        │  │
│  │  - Supports: bolt_standard, quick_iteration, debug   │  │
│  │  - Custom workflows via API                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  AgentRegistry                                       │  │
│  │  - Manages agent configurations                      │  │
│  │  - Dynamic prompt/model updates                      │  │
│  │  - Agents: Planner, Writer, Fixer, Runner, etc.     │  │
│  └──────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Individual Agents                                   │  │
│  │  - Planner Agent (creates execution plan)            │  │
│  │  - Writer Agent (generates code)                     │  │
│  │  - Fixer Agent (applies patches)                     │  │
│  │  - Runner Agent (executes commands)                  │  │
│  │  - Documenter Agent (creates docs)                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Backend Setup

### 1. Files Created

```
backend/
├── app/
│   ├── modules/
│   │   └── orchestrator/
│   │       └── dynamic_orchestrator.py  ✅ NEW (850+ lines)
│   └── api/
│       └── v1/
│           ├── endpoints/
│           │   └── orchestrator.py      ✅ NEW (590+ lines)
│           └── router.py                ✅ UPDATED
```

### 2. Dependencies

The Dynamic Orchestrator uses existing dependencies:
- `anthropic` - Claude API client
- `fastapi` - API framework
- `pydantic` - Data validation

No new dependencies needed!

### 3. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The orchestrator will be available at: `http://localhost:8000/api/v1/orchestrator`

---

## 🔌 API Endpoints

### **1. Execute Workflow (SSE Streaming)**

**Endpoint:** `POST /api/v1/orchestrator/execute`

**Description:** Execute a workflow with real-time SSE streaming.

**Request Body:**
```json
{
  "user_request": "Build a todo app with React",
  "project_id": "my-project-001",
  "workflow_name": "bolt_standard",
  "metadata": {
    "user_id": "user123",
    "session_id": "session456"
  }
}
```

**Response:** Server-Sent Events (SSE) stream

**Event Types:**
- `status` - Workflow status updates
- `thinking_step` - AI thinking progress
- `plan_created` - Plan generation complete
- `file_operation` - File creation/modification started
- `file_content` - File content chunk (streaming)
- `file_complete` - File completed
- `command_execute` - Command execution
- `error` - Error occurred
- `complete` - Workflow finished

**Example Event:**
```json
data: {
  "type": "file_content",
  "message": "Streaming code...",
  "data": {
    "path": "src/App.tsx",
    "chunk": "import React from 'react'\n"
  },
  "step": 2,
  "agent": "writer",
  "progress": 45
}
```

---

### **2. List Workflows**

**Endpoint:** `GET /api/v1/orchestrator/workflows`

**Response:**
```json
[
  {
    "name": "bolt_standard",
    "steps": [
      {
        "agent_type": "planner",
        "name": "Create Plan",
        "timeout": 120,
        "retry_count": 2,
        "stream_output": false
      },
      {
        "agent_type": "writer",
        "name": "Generate Code",
        "timeout": 300,
        "retry_count": 2,
        "stream_output": true
      },
      {
        "agent_type": "runner",
        "name": "Execute & Test",
        "timeout": 180,
        "retry_count": 1,
        "stream_output": false
      },
      {
        "agent_type": "fixer",
        "name": "Fix Errors",
        "timeout": 300,
        "retry_count": 2,
        "stream_output": true
      },
      {
        "agent_type": "documenter",
        "name": "Generate Docs",
        "timeout": 180,
        "retry_count": 1,
        "stream_output": false
      }
    ]
  }
]
```

---

### **3. Create Custom Workflow**

**Endpoint:** `POST /api/v1/orchestrator/workflows`

**Request Body:**
```json
{
  "name": "my_custom_workflow",
  "description": "Custom workflow for specific use case",
  "steps": [
    {
      "agent_type": "planner",
      "name": "Create Plan",
      "timeout": 120,
      "retry_count": 2
    },
    {
      "agent_type": "writer",
      "name": "Generate Code",
      "stream_output": true
    }
  ]
}
```

---

### **4. List Agents**

**Endpoint:** `GET /api/v1/orchestrator/agents`

**Response:**
```json
[
  {
    "name": "Planner Agent",
    "agent_type": "planner",
    "model": "sonnet",
    "temperature": 0.7,
    "max_tokens": 4096,
    "capabilities": ["planning", "task_breakdown"],
    "enabled": true,
    "has_custom_prompt": false
  },
  {
    "name": "Writer Agent",
    "agent_type": "writer",
    "model": "sonnet",
    "temperature": 0.3,
    "max_tokens": 8192,
    "capabilities": ["code_generation", "file_creation"],
    "enabled": true,
    "has_custom_prompt": false
  }
]
```

---

### **5. Update Agent Prompt (Dynamic)**

**Endpoint:** `PUT /api/v1/orchestrator/agents/{agent_type}/prompt`

**Request Body:**
```json
{
  "system_prompt": "You are an expert Python developer specializing in FastAPI and async programming. Always use type hints and follow PEP 8 conventions."
}
```

**Response:**
```json
{
  "message": "Agent 'writer' prompt updated successfully",
  "agent_type": "writer"
}
```

---

### **6. Update Agent Model (Dynamic)**

**Endpoint:** `PUT /api/v1/orchestrator/agents/{agent_type}/model`

**Request Body:**
```json
{
  "model": "opus"
}
```

**Valid Models:**
- `haiku` - Fast, cost-effective (Claude 3 Haiku)
- `sonnet` - Balanced performance (Claude 3.5 Sonnet) - **Default**
- `opus` - Most powerful (Claude 3 Opus)

---

### **7. Health Check**

**Endpoint:** `GET /api/v1/orchestrator/health`

**Response:**
```json
{
  "status": "healthy",
  "agents_count": 7,
  "workflows_count": 3,
  "default_workflow": "bolt_standard"
}
```

---

## 🎨 Frontend Integration

### 1. Update `useChat` Hook (Optional)

You can optionally add orchestrator support to the chat:

```typescript
// In frontend/src/hooks/useChat.ts

import { streamingClient } from '@/lib/streaming-client'

// Add new method
const sendOrchestratorMessage = useCallback(async (
  content: string,
  workflowName: string = 'bolt_standard'
) => {
  const aiMessageId = generateId()
  const aiMessage: AIMessage = {
    id: aiMessageId,
    type: 'assistant',
    content: '',
    timestamp: new Date(),
    isStreaming: true,
    status: 'thinking',
    fileOperations: [],
    thinkingSteps: []
  }
  addMessage(aiMessage)
  startStreaming(aiMessageId)

  try {
    await streamingClient.streamOrchestratorWorkflow(
      content,
      'demo-project-001',
      workflowName,
      {},
      (event) => {
        // Handle events (same as existing sendMessage)
        switch (event.type) {
          case 'file_start':
            // ... (same logic)
            break
          case 'file_content':
            // ... (same logic)
            break
          // etc.
        }
      },
      (error) => {
        console.error('Orchestrator error:', error)
        appendToMessage(aiMessageId, `\n\n⚠️ Error: ${error.message}`)
        stopStreaming()
      },
      () => {
        stopStreaming()
      }
    )
  } catch (error: any) {
    console.error('Failed to send orchestrator message:', error)
    appendToMessage(aiMessageId, `\n\n⚠️ Error: ${error.message}`)
    stopStreaming()
  }
}, [addMessage, startStreaming, stopStreaming, appendToMessage])
```

### 2. Direct Usage Example

```typescript
import { streamingClient } from '@/lib/streaming-client'

// Execute workflow
await streamingClient.streamOrchestratorWorkflow(
  'Build a todo app with React and TypeScript',
  'my-project-001',
  'bolt_standard',
  { user_id: 'user123' },
  (event) => {
    console.log('Event:', event.type, event.message)
  },
  (error) => {
    console.error('Error:', error)
  },
  () => {
    console.log('Workflow complete!')
  }
)
```

---

## ⚙️ Workflows

### **Built-in Workflows**

#### 1. **bolt_standard** (Default)
**Steps:** plan → write → run → fix → docs

**Use Case:** Full-featured project generation with testing and documentation

```
┌─────────────┐
│  Planner    │ - Analyzes requirements, creates execution plan
└──────┬──────┘
       ↓
┌─────────────┐
│  Writer     │ - Generates all code files with streaming
└──────┬──────┘
       ↓
┌─────────────┐
│  Runner     │ - Executes npm install, runs tests
└──────┬──────┘
       ↓
┌─────────────┐
│  Fixer      │ - Applies patches if tests fail
└──────┬──────┘
       ↓
┌─────────────┐
│ Documenter  │ - Generates README.md
└─────────────┘
```

#### 2. **quick_iteration**
**Steps:** plan → write → test

**Use Case:** Rapid prototyping without full documentation

#### 3. **debug**
**Steps:** analyze → fix → verify

**Use Case:** Debugging existing code

---

### **Creating Custom Workflows**

**Via API:**

```bash
curl -X POST http://localhost:8000/api/v1/orchestrator/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "frontend_only",
    "description": "Generate frontend code only",
    "steps": [
      {
        "agent_type": "planner",
        "name": "Plan UI Components",
        "timeout": 60
      },
      {
        "agent_type": "writer",
        "name": "Generate React Components",
        "stream_output": true
      }
    ]
  }'
```

**Via Code:**

```python
from app.modules.orchestrator.dynamic_orchestrator import (
    orchestrator, WorkflowStep, AgentType
)

# Create custom workflow
custom_steps = [
    WorkflowStep(
        agent_type=AgentType.PLANNER,
        name="Analyze Backend Requirements",
        timeout=90
    ),
    WorkflowStep(
        agent_type=AgentType.WRITER,
        name="Generate FastAPI Endpoints",
        stream_output=True,
        retry_count=3
    ),
    WorkflowStep(
        agent_type=AgentType.TESTER,
        name="Run pytest",
        timeout=120
    )
]

orchestrator.workflow_engine.register_workflow("backend_api", custom_steps)
```

---

## 🤖 Agent Configuration

### **Available Agents**

| Agent | Purpose | Default Model | Capabilities |
|-------|---------|---------------|-------------|
| **Planner** | Create execution plans | Sonnet | planning, task_breakdown |
| **Writer** | Generate code | Sonnet | code_generation, file_creation |
| **Fixer** | Apply patches, fix bugs | Sonnet | patching, debugging |
| **Runner** | Execute commands | Haiku | command_execution, testing |
| **Tester** | Run tests | Haiku | testing, validation |
| **Documenter** | Generate documentation | Haiku | documentation, README |
| **Enhancer** | Code enhancement | Sonnet | refactoring, optimization |
| **Analyzer** | Code analysis | Sonnet | analysis, code_review |

### **Dynamic Agent Updates**

**Update Prompt:**
```bash
curl -X PUT http://localhost:8000/api/v1/orchestrator/agents/writer/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "system_prompt": "You are an expert React developer. Always use functional components with hooks. Follow Airbnb style guide."
  }'
```

**Update Model:**
```bash
curl -X PUT http://localhost:8000/api/v1/orchestrator/agents/writer/model \
  -H "Content-Type: application/json" \
  -d '{"model": "opus"}'
```

**Enable/Disable Agent:**
```bash
# Disable
curl -X PUT http://localhost:8000/api/v1/orchestrator/agents/documenter/disable

# Enable
curl -X PUT http://localhost:8000/api/v1/orchestrator/agents/documenter/enable
```

---

## 📚 Usage Examples

### **Example 1: Basic Workflow Execution**

```python
import asyncio
from app.modules.orchestrator.dynamic_orchestrator import orchestrator

async def main():
    async for event in orchestrator.execute_workflow(
        user_request="Build a calculator app with React",
        project_id="calc-001",
        workflow_name="bolt_standard"
    ):
        print(f"[{event.agent}] {event.type}: {event.message}")

asyncio.run(main())
```

**Output:**
```
[planner] status: Creating execution plan...
[planner] plan_created: Plan ready with 5 files
[writer] file_operation: Creating src/App.tsx...
[writer] file_content: import React from 'react'
[writer] file_complete: src/App.tsx complete
[runner] command_execute: npm install
[fixer] status: No errors found
[documenter] file_operation: Creating README.md...
[documenter] complete: Workflow finished!
```

---

### **Example 2: Frontend Integration**

```typescript
// In a React component
import { streamingClient } from '@/lib/streaming-client'
import { useState } from 'react'

function CodeGenerator() {
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')

  const generateProject = async () => {
    await streamingClient.streamOrchestratorWorkflow(
      'Build a blog with Next.js',
      'blog-project',
      'bolt_standard',
      {},
      (event) => {
        setProgress(event.progress || 0)
        setStatus(event.message || '')

        if (event.type === 'file_content') {
          // Update Monaco editor in real-time
          console.log('Streaming:', event.content)
        }
      },
      (error) => {
        console.error('Error:', error)
      },
      () => {
        console.log('Complete!')
      }
    )
  }

  return (
    <div>
      <button onClick={generateProject}>Generate Project</button>
      <div>Progress: {progress}%</div>
      <div>Status: {status}</div>
    </div>
  )
}
```

---

### **Example 3: Custom Workflow with Conditional Steps**

```python
from app.modules.orchestrator.dynamic_orchestrator import (
    WorkflowStep, AgentType, ExecutionContext
)

def should_run_tests(context: ExecutionContext) -> bool:
    """Only run tests if code was generated"""
    return len(context.files_created) > 0

custom_workflow = [
    WorkflowStep(
        agent_type=AgentType.PLANNER,
        name="Create Plan"
    ),
    WorkflowStep(
        agent_type=AgentType.WRITER,
        name="Generate Code",
        stream_output=True
    ),
    WorkflowStep(
        agent_type=AgentType.TESTER,
        name="Run Tests",
        condition=should_run_tests  # Conditional execution
    )
]

orchestrator.workflow_engine.register_workflow("conditional_test", custom_workflow)
```

---

## 🧪 Testing

### **1. Test Health Endpoint**

```bash
curl http://localhost:8000/api/v1/orchestrator/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "agents_count": 7,
  "workflows_count": 3,
  "default_workflow": "bolt_standard"
}
```

---

### **2. Test Workflow Execution**

```bash
curl -X POST http://localhost:8000/api/v1/orchestrator/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_request": "Create a simple counter component",
    "project_id": "test-001",
    "workflow_name": "quick_iteration"
  }'
```

**Expected SSE Stream:**
```
data: {"type":"status","message":"Starting workflow...","progress":0}

data: {"type":"thinking_step","message":"Analyzing requirements","progress":10}

data: {"type":"plan_created","message":"Plan ready","progress":20}

data: {"type":"file_operation","data":{"path":"Counter.tsx","status":"started"},"progress":30}

data: {"type":"file_content","data":{"path":"Counter.tsx","chunk":"import React"},"progress":35}

data: {"type":"complete","message":"Workflow complete!","progress":100}
```

---

### **3. Test Agent Configuration**

```bash
# Get agent details
curl http://localhost:8000/api/v1/orchestrator/agents/writer

# Update model
curl -X PUT http://localhost:8000/api/v1/orchestrator/agents/writer/model \
  -H "Content-Type: application/json" \
  -d '{"model": "opus"}'

# Verify update
curl http://localhost:8000/api/v1/orchestrator/agents/writer
```

---

## 🎯 Benefits Over Previous System

| Feature | Old System | Dynamic Orchestrator |
|---------|-----------|---------------------|
| **Prompts** | Hardcoded in agent files | Configurable via API |
| **Models** | Fixed (sonnet) | Switchable (haiku/sonnet/opus) |
| **Workflows** | Single BoltOrchestrator | Multiple workflows |
| **Agent Management** | Code changes required | Runtime configuration |
| **Error Recovery** | Basic | Exponential backoff retries |
| **Progress Tracking** | Limited | 0-100% with step details |
| **Event Streaming** | Basic SSE | Rich event types |
| **File Patching** | Not supported | Unified diff support |

---

## 🚀 Next Steps

1. **Test the API:**
   ```bash
   # Start backend
   cd backend
   uvicorn app.main:app --reload

   # Test health
   curl http://localhost:8000/api/v1/orchestrator/health
   ```

2. **Try a workflow:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/orchestrator/execute \
     -H "Content-Type: application/json" \
     -d '{
       "user_request": "Build a todo app",
       "project_id": "test-001",
       "workflow_name": "bolt_standard"
     }'
   ```

3. **Integrate with frontend:**
   - Use `streamingClient.streamOrchestratorWorkflow()` in your components
   - Handle events in `useChat` hook
   - Update Monaco editor in real-time

4. **Customize agents:**
   - Update writer agent to use Opus model for better quality
   - Customize planner prompt for specific domains
   - Create custom workflows for your use cases

---

## 📖 API Documentation

Full API documentation is available at: `http://localhost:8000/docs`

This includes:
- Interactive API testing
- Request/response schemas
- Authentication details
- Example requests

---

## 🎉 Summary

The Dynamic Orchestrator provides a **production-ready, Bolt.new-style backend** with:

✅ **Flexible Architecture** - Easily add new agents and workflows
✅ **Runtime Configuration** - Update prompts/models without restarts
✅ **Real-time Streaming** - SSE events for live UI updates
✅ **Robust Error Handling** - Retries, timeouts, and fallbacks
✅ **Comprehensive API** - Full CRUD for agents and workflows
✅ **Frontend Integration** - Ready-to-use streaming client

**You now have a complete, configurable orchestration system! 🚀**
