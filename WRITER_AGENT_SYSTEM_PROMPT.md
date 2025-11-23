# Writer Agent - Complete System Prompt Documentation

> **✅ Updated with Comprehensive System Prompt**
> The Writer Agent now has its own detailed system prompt that guides it to process ONE TASK AT A TIME following the Bolt.new architecture.

---

## Overview

The **Writer Agent** has a comprehensive, standalone system prompt that instructs it to:
1. Process **ONE specific task** from the plan
2. Create **ONLY the files needed for that task**
3. **NOT** create files for future tasks
4. Build projects **incrementally**, task by task
5. Use **Bolt.new XML format** (`<file>`, `<terminal>`, `<explain>`)

---

## How It Works

### Workflow

```
┌─────────────────────────────────────────────────────┐
│ 1️⃣ Planner Agent                                     │
│    - Creates step-by-step plan with tasks           │
│    - Example: 4 phases, each with specific tasks    │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 2️⃣ Orchestrator                                      │
│    - Receives plan from Planner                      │
│    - Extracts individual tasks                       │
│    - Sends ONE task at a time to Writer Agent       │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 3️⃣ Writer Agent (Task 1: "Setup Project Structure") │
│    - Reads its SYSTEM PROMPT                         │
│    - Sees: "Process ONLY THIS TASK"                  │
│    - Creates: package.json, tsconfig.json           │
│    - Does NOT create: components, models, etc.      │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 4️⃣ Orchestrator                                      │
│    - Receives files from Writer Agent                │
│    - Writes files to disk                            │
│    - Executes commands                               │
│    - Marks Task 1 as ✔ complete                     │
│    - Sends Task 2 to Writer Agent                   │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│ 5️⃣ Writer Agent (Task 2: "Create Database Models")  │
│    - Reads SYSTEM PROMPT again                       │
│    - Sees previous context (package.json exists)     │
│    - Creates: models/user.py, models/todo.py        │
│    - Does NOT create: API endpoints, frontend       │
└─────────────────────────────────────────────────────┘
                    ↓
                  (Continue for all tasks...)
```

---

## System Prompt Structure

The Writer Agent's system prompt is structured in these sections:

### 1. Role Definition
```
You are an expert Writer Agent specialized in writing files
ONE TASK AT A TIME following the Bolt.new architecture.
```

### 2. Important Principles
- **One Task at a Time**: Most critical rule
- **Complete Implementation**: No placeholders
- **Incremental Building**: Build on previous tasks
- **Production Quality**: Clean, commented code
- **Educational Value**: Help students learn

### 3. Input Specification
What the agent receives:
- Current task name and description
- Task requirements
- Previous context (files created, commands run)
- Project metadata (tech stack, features)

### 4. Output Format
```xml
<thinking>Reasoning and decisions</thinking>
<explain>What this task accomplishes</explain>
<file path="...">Complete file content</file>
<terminal>Commands to run</terminal>
```

### 5. Critical Rules (11 Rules)
1. **One Task at a Time** - Only create files for THIS task
2. **Task Scope** - Stay within exact scope
3. **File Creation** - Complete, production-ready code
4. **Code Quality** - Follow best practices
5. **Educational Comments** - Explain WHY, not just WHAT
6. **Terminal Commands** - Safe commands only
7. **Explanations** - Describe what was accomplished
8. **Thinking Process** - Show reasoning
9. **Context Awareness** - Build on existing files
10. **Error Handling** - Clear error messages
11. **Technology Stack Specific** - Follow framework conventions

### 6. Examples
- ✅ CORRECT: Task-focused file creation
- ❌ WRONG: Creating files for multiple tasks

---

## Key Differences from Other Agents

| Feature | Writer Agent | Coder Agent | Planner Agent |
|---------|-------------|-------------|---------------|
| **Calls** | Multiple (once per task) | Once | Once |
| **Scope** | ONE task | Entire project | Entire plan |
| **Files** | 2-5 files per call | 10-50 files | No files |
| **Output** | `<file>` XML tags | JSON | `<plan>` XML tag |
| **Context** | Builds incrementally | No context | Creates context |
| **Model** | Haiku (fast) | Haiku/Sonnet | Sonnet |

---

## System Prompt Highlights

### Most Important Rule

```
1. **One Task at a Time - MOST IMPORTANT**:
   - You are processing EXACTLY ONE TASK from the plan
   - ONLY create files needed for THIS SPECIFIC TASK
   - DO NOT create files for other tasks
   - The orchestrator will call you again for the next task
   - Example: If task is "Create database models",
     ONLY create model files, nothing else
```

### Task Scope Enforcement

```
2. **Task Scope**:
   - Read the task name and description carefully
   - Create ONLY files explicitly needed for this task
   - If task says "Create authentication endpoints",
     don't also create frontend components
   - If task says "Setup project structure",
     don't also create feature implementations
   - Stay focused on the exact scope of the current task
```

### Educational Comments

```
5. **Educational Comments**:
   - Explain WHY, not just WHAT
   - Good: "// Hash password before storage to prevent plaintext leaks"
   - Bad: "// Hash password"
   - Add links to documentation for complex concepts
   - Help students learn from the code
```

---

## Example Scenarios

### Scenario 1: Task "Setup Backend Structure"

**What Writer Agent SHOULD do:**
```xml
<file path="backend/app/main.py">
from fastapi import FastAPI
app = FastAPI()
# ... backend initialization only
</file>

<file path="backend/requirements.txt">
fastapi==0.104.1
uvicorn==0.24.0
</file>

<terminal>pip install -r backend/requirements.txt</terminal>
```

**What Writer Agent should NOT do:**
- ❌ Create database models (that's a different task)
- ❌ Create API endpoints (that's a different task)
- ❌ Create frontend files (that's a different task)

---

### Scenario 2: Task "Create Database Models"

**What Writer Agent SHOULD do:**
```xml
<file path="backend/app/models/user.py">
# Complete User model implementation
</file>

<file path="backend/app/models/todo.py">
# Complete Todo model implementation
</file>

<file path="backend/app/models/__init__.py">
# Export models
</file>
```

**What Writer Agent should NOT do:**
- ❌ Create API routes (that's a different task)
- ❌ Create authentication logic (that's a different task)
- ❌ Create frontend components (that's a different task)

---

### Scenario 3: Task "Create Authentication Endpoints"

**What Writer Agent SHOULD do:**
```xml
<file path="backend/app/api/auth.py">
# ONLY authentication endpoints: register, login, logout
</file>

<file path="backend/app/schemas/auth.py">
# ONLY auth-related Pydantic schemas
</file>
```

**What Writer Agent should NOT do:**
- ❌ Create user management endpoints (different task)
- ❌ Create todo endpoints (different task)
- ❌ Create frontend login page (different task)

---

## Context Awareness

The Writer Agent receives context from previous tasks:

```python
previous_context = {
    "files_created": [
        {"path": "backend/app/main.py", "size": 512, "step": 1},
        {"path": "backend/requirements.txt", "size": 128, "step": 1}
    ],
    "commands_executed": [
        {"command": "pip install -r requirements.txt", "success": True, "step": 1}
    ],
    "last_explanation": "Backend structure created successfully"
}
```

This helps the Writer Agent:
1. **Avoid recreating files** that already exist
2. **Reference existing code** when needed
3. **Build incrementally** on previous work
4. **Maintain consistency** across tasks

---

## Code Quality Standards

### Python/FastAPI
```python
# ✅ GOOD - Production-ready with comments
async def create_user(user_data: UserCreate, db: Session):
    """
    Create new user account with hashed password

    Security: Passwords are hashed using bcrypt before storage
    to prevent plaintext password leaks in case of database breach.
    """
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    return user

# ❌ BAD - No comments, unclear
def create_user(data, db):
    user = User(email=data.email, pwd=hash(data.pwd))
    db.add(user)
    db.commit()
    return user
```

### React/TypeScript
```typescript
// ✅ GOOD - Typed, commented, production-ready
interface TodoItemProps {
  id: number;
  title: string;
  completed: boolean;
  onToggle: (id: number) => void;
}

/**
 * TodoItem component displays a single todo with checkbox
 *
 * Props:
 * - id: Unique todo identifier
 * - title: Todo text
 * - completed: Whether todo is marked done
 * - onToggle: Callback when checkbox is clicked
 */
export const TodoItem: React.FC<TodoItemProps> = ({
  id,
  title,
  completed,
  onToggle
}) => {
  return (
    <div className="todo-item">
      <input
        type="checkbox"
        checked={completed}
        onChange={() => onToggle(id)}
      />
      <span className={completed ? 'line-through' : ''}>{title}</span>
    </div>
  );
};

// ❌ BAD - No types, no comments
export const TodoItem = (props) => {
  return <div>...</div>;
};
```

---

## Security & Safety

### Command Execution
Writer Agent blocks dangerous commands:
```bash
# ❌ BLOCKED
rm -rf /
sudo apt-get install
chmod 777 file.txt
dd if=/dev/zero of=/dev/sda

# ✅ ALLOWED
npm install
pip install -r requirements.txt
npm run build
python manage.py migrate
```

### Timeout Protection
- All commands have 120-second timeout
- Prevents infinite loops or hanging processes
- Captures stdout/stderr for debugging

---

## Performance Characteristics

### Writer Agent (Task-by-Task)
```
Task 1: 5 seconds → 2 files created
Task 2: 5 seconds → 3 files created
Task 3: 5 seconds → 4 files created
Task 4: 5 seconds → 3 files created
Total: 20 seconds, 12 files

User sees progress at: 5s, 10s, 15s, 20s ✅
```

### Coder Agent (All at Once)
```
Single call: 30 seconds → 12 files created
Total: 30 seconds, 12 files

User sees progress at: 30s only ❌
```

**Winner**: Writer Agent - Better UX despite similar total time

---

## Error Handling

### When Task Cannot Be Completed

```xml
<error>
Cannot create authentication endpoints because User model does not exist.
Please run "Create Database Models" task first.
</error>
```

### When Command Fails

```xml
<terminal>npm install express</terminal>

<error>
npm install failed with error: package.json not found
Ensure "Setup Project Structure" task was completed first.
</error>
```

---

## Testing the System Prompt

### Test 1: Scope Adherence
```python
# Give Writer Agent task: "Create database models"
# Expected: ONLY model files
# Not Expected: API routes, frontend components

result = await writer_agent.process(
    context=context,
    step_number=1,
    step_data={"name": "Create Database Models", ...}
)

assert all('models/' in f['path'] for f in result['files_created'])
assert not any('api/' in f['path'] for f in result['files_created'])
```

### Test 2: Context Awareness
```python
# Give Writer Agent context showing package.json exists
# Expected: Does NOT recreate package.json
# Expected: References existing dependencies

previous_context = {
    "files_created": [{"path": "package.json"}]
}

result = await writer_agent.process(
    context=context,
    step_number=2,
    step_data={"name": "Create Components", ...},
    previous_context=previous_context
)

assert not any(f['path'] == 'package.json' for f in result['files_created'])
```

---

## Summary

✅ **Comprehensive System Prompt** - 442 lines of detailed instructions
✅ **Task-Focused** - Emphasizes ONE task at a time
✅ **Clear Examples** - Shows correct and incorrect approaches
✅ **Production Quality** - Requires complete, working code
✅ **Educational** - Encourages meaningful comments
✅ **Security-Aware** - Blocks dangerous commands
✅ **Context-Aware** - Builds on previous work
✅ **Bolt.new Compatible** - Uses XML tag format

The Writer Agent now has a standalone, comprehensive system prompt that guides it to build projects incrementally, one task at a time, following the Bolt.new architecture perfectly!

---

**File:** `backend/app/modules/agents/writer_agent.py`
**System Prompt Length:** 442 lines
**Last Updated:** 2025-11-22
**Status:** ✅ Production Ready
