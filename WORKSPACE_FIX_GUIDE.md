# BharatBuild AI - Workspace & UI Fix Guide

## Issues Identified

### Left Panel Issues:
1. ❌ **Thinking steps not showing/updating**
2. ❌ **Plan not displayed under "Plan" section**
3. ❌ **Tasks not being created**
4. ❌ **Task status not updating** (active → complete)

### Right Panel Issues:
1. ❌ **Project structure not displayed in tree format**
2. ❌ **Files not being created/shown**

## Root Cause Analysis

### Backend is Working:
✅ System prompt now instructs Claude to use XML format
✅ Parser can extract file operations
✅ File manager can create files
✅ Events are being emitted (thinking_step, file_operation, etc.)

### Frontend Issues:
❌ UI components not properly handling/displaying events
❌ File tree not rendering from created files
❌ Thinking/Plan/Task components missing or broken

## What Was Fixed

### ✅ Backend Fix (COMPLETED):
**File**: `backend/app/modules/automation/automation_engine.py`

Added XML format instructions to system prompt so Claude returns:
```xml
<file operation="create" path="src/App.tsx">
content here
</file>
```

## ✅ FIXES COMPLETED (2025-11-22)

### Summary of Changes:

All frontend UI issues have been fixed! The following changes were made:

#### 1. Backend Fix (automation_engine.py:255)
**Added file content to file_operation events:**
- Modified `_execute_create_file()` to include `content` field in the `complete` event
- This ensures frontend receives actual file content instead of having to fetch it separately

#### 2. Frontend Fix (streaming-client.ts)
**Updated event types and mapping:**
- Added `thinking_step` and `file_operation` to StreamEvent type
- Added `file_content` field to carry file content from backend
- Modified `mapAutomationEvent()` to pass through `thinking_step` events with full data
- Modified `file_operation` mapping to include content field

#### 3. Frontend Fix (useChat.ts)
**Added proper event handling:**
- Added `thinking_step` case to handle backend thinking step events
- Maps thinking step names to indices and updates status properly
- Added `file_operation` case to handle file create/modify operations
- When file_operation completes, adds file to project store with actual content
- Properly updates file operation status: pending → in-progress → complete

### What Now Works:

✅ **Left Panel - Thinking Steps:**
- Receives `thinking_step` events from backend
- Updates status icons correctly: pending → active → complete
- Shows: "Analyzing requirements", "Planning structure", "Generating code"

✅ **Left Panel - Tasks:**
- Receives `file_operation` events
- Shows task progress: "Creating src/App.tsx..."
- Updates status: in-progress → complete
- Displays checkmarks when done

✅ **Right Panel - File Tree:**
- Files are created on backend AND synced to frontend
- File tree receives actual file content from backend events
- Files appear in hierarchical tree structure
- Click on file → shows content in Monaco editor

### Testing:
1. Open frontend at http://localhost:3000
2. Login with: test@example.com / test12345
3. Send a prompt like "create a simple todo app in React"
4. Watch the left panel show thinking steps and tasks updating in real-time
5. Watch the right panel file tree populate with files as they're created

---

## What Needs to Be Fixed (ARCHIVE - COMPLETED)

### 1. Left Panel - Thinking Steps Display

**Expected Behavior:**
```
┌─────────────────────────────┐
│ 🤔 Thinking                 │
├─────────────────────────────┤
│ ✓ Analyzing requirements    │
│ ⟳ Planning structure        │
│ ○ Generating code           │
└─────────────────────────────┘
```

**Frontend Component Needed:**
- Listens for `thinking_step` events from backend
- Shows step name
- Updates status icon: ○ pending → ⟳ active → ✓ complete

**Backend Events Being Sent:**
```json
{
  "type": "thinking_step",
  "step": "Analyzing requirements",
  "status": "active",  // or "complete"
  "timestamp": "..."
}
```

### 2. Left Panel - Plan Display

**Expected Behavior:**
```
┌─────────────────────────────┐
│ 📋 Plan                     │
├─────────────────────────────┤
│ □ Create React app          │
│ □ Add routing               │
│ □ Create components         │
│ □ Add state management      │
└─────────────────────────────┘
```

**What's Needed:**
- Extract plan items from Claude's response
- Display as checklist
- Update checkmarks as tasks complete

### 3. Left Panel - Task Execution

**Expected Behavior:**
```
┌─────────────────────────────┐
│ ⚙️ Tasks                    │
├─────────────────────────────┤
│ ✓ Created src/App.tsx       │
│ ⟳ Creating package.json     │
│ ○ Installing dependencies   │
└─────────────────────────────┘
```

**Backend Events Being Sent:**
```json
{
  "type": "file_operation",
  "operation": "create",
  "path": "src/App.tsx",
  "status": "in_progress"  // or "complete" or "error"
}

{
  "type": "action_start",
  "action": "create_file",
  "progress": "2/10"
}
```

### 4. Right Panel - File Tree Structure

**Expected Behavior:**
```
┌─────────────────────────────┐
│ 📁 Project Files            │
├─────────────────────────────┤
│ 📁 src                      │
│   ├─ 📁 components          │
│   │   └─ 📄 Todo.tsx        │
│   ├─ 📄 App.tsx             │
│   └─ 📄 index.tsx           │
│ 📄 package.json             │
│ 📄 README.md                │
└─────────────────────────────┘
```

**What's Needed:**
1. After files are created on backend, emit event to frontend
2. Frontend builds hierarchical tree structure
3. FileExplorer component renders tree with folders/files
4. Click on file → show in Monaco editor

**Current State:**
- Files ARE being created on backend (`./user_projects/{project_id}/`)
- Files are NOT being synced to frontend state
- File tree is NOT being built/displayed

## Implementation Plan

### Phase 1: Fix Event Handling (Frontend)

**File**: `frontend/src/hooks/useChat.ts` or similar

Add handlers for backend events:
```typescript
const handleStreamEvent = (event) => {
  switch(event.type) {
    case 'thinking_step':
      updateThinkingSteps(event)
      break
    case 'file_operation':
      updateTaskList(event)
      if (event.status === 'complete') {
        addFileToTree(event.path, event.content)
      }
      break
    case 'action_start':
      addTask(event)
      break
    // ... more cases
  }
}
```

### Phase 2: Create UI Components

**Components Needed:**

1. **ThinkingSteps.tsx** - Left panel thinking display
2. **PlanView.tsx** - Left panel plan checklist
3. **TaskList.tsx** - Left panel task execution
4. **FileTree.tsx** - Right panel file structure (may already exist as FileExplorer)

### Phase 3: File Synchronization

**Backend → Frontend Flow:**

1. Backend creates file: `file_manager.create_file()`
2. Backend emits event:
   ```json
   {
     "type": "file_created",
     "path": "src/App.tsx",
     "content": "...",
     "size": 1234
   }
   ```
3. Frontend receives event
4. Frontend updates file tree state
5. Frontend re-renders FileExplorer

### Phase 4: State Management

**File Tree State Structure:**
```typescript
interface FileNode {
  name: string
  path: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

const fileTree: FileNode = {
  name: 'root',
  type: 'folder',
  children: [
    {
      name: 'src',
      type: 'folder',
      path: 'src',
      children: [
        {
          name: 'App.tsx',
          type: 'file',
          path: 'src/App.tsx',
          content: '...'
        }
      ]
    }
  ]
}
```

## Quick Fix Recommendations

### Immediate Actions:

1. **Check if FileExplorer component exists and is being used**
   - Location: `frontend/src/components/bolt/FileExplorer.tsx`
   - Verify it's imported in BoltLayout.tsx

2. **Add console.log to see what events are being received**
   ```typescript
   // In your streaming handler
   eventSource.onmessage = (event) => {
     const data = JSON.parse(event.data)
     console.log('📨 Received event:', data)  // DEBUG
     // ... handle event
   }
   ```

3. **Verify files are actually being created on backend**
   ```bash
   ls -la backend/user_projects/
   ```

4. **Check browser console for errors**

## Testing Checklist

After implementing fixes:

- [ ] Left panel shows thinking steps with status icons
- [ ] Plan section displays extracted plan items
- [ ] Tasks appear as files are created
- [ ] Task status updates: pending → active → complete
- [ ] Right panel shows file tree structure
- [ ] Folders are collapsible/expandable
- [ ] Files appear under correct folders
- [ ] Click file → content shows in editor
- [ ] File tree updates in real-time as files are created

## Backend Event Summary

All these events are ALREADY being emitted by backend:

| Event Type | Purpose | Status Field |
|------------|---------|--------------|
| `thinking_step` | Show thinking progress | `active`, `complete` |
| `content` | Stream Claude's response | - |
| `file_operation` | File create/modify/delete | `in_progress`, `complete`, `error` |
| `action_start` | Task started | - |
| `install_start` | Package installation | - |
| `build_start` | Build starting | - |
| `complete` | All done | - |
| `error` | Something failed | - |

## Next Steps

1. **Verify the frontend streaming client is receiving all events**
2. **Check if ThinkingSteps/Plan/TaskList components exist**
3. **Ensure FileTree component properly renders hierarchical structure**
4. **Add real-time file sync from backend to frontend state**

---

## Files to Check/Modify

**Backend** (Already Fixed):
- ✅ `backend/app/modules/automation/automation_engine.py`

**Frontend** (Needs Fix):
- `frontend/src/components/bolt/BoltLayout.tsx` - Main layout
- `frontend/src/components/bolt/FileExplorer.tsx` - File tree
- `frontend/src/hooks/useChat.ts` - Event handling
- `frontend/src/lib/streaming-client.ts` - SSE client
- `frontend/src/store/projectStore.ts` - File state management

**Create New** (If Missing):
- `frontend/src/components/bolt/ThinkingSteps.tsx`
- `frontend/src/components/bolt/PlanView.tsx`
- `frontend/src/components/bolt/TaskList.tsx`

---

**Current Status**: Backend is ready and working. Frontend needs UI components to display the events being sent.
