/**
 * BharatBuild CLI — Built-in Tool: todo_list
 * A tool for creating a task list and keeping track of tasks.
 * Should be used for multi-step tasks to track progress.
 */

import type { BuiltInTool, ToolResult } from "./types.js";

export const todoListTool: BuiltInTool = {
  definition: {
    name: "todo_list",
    source: "built-in",
    status: "approval_required",
    description: "A tool for creating a task list and keeping track of tasks. This tool should be requested EVERY time the user gives a task that will take multiple steps.",
    parameters: {
      type: "object",
      properties: {
        command: {
          type: "string",
          enum: ["create", "complete", "add", "remove", "list"],
          description: "The command to run: create, complete, add, remove, or list.",
        },
        task_list_description: {
          type: "string",
          description: "Brief summary of the task list (required for 'create').",
        },
        tasks: {
          type: "array",
          description: "List of tasks to create (required for 'create').",
          items: {
            type: "object",
            properties: {
              task_description: { type: "string", description: "The main task description." },
              details: { type: "string", description: "Optional detailed information about the task." },
            },
            required: ["task_description"],
          },
        },
        new_tasks: {
          type: "array",
          description: "New tasks to add (required for 'add').",
          items: {
            type: "object",
            properties: {
              task_description: { type: "string", description: "The main task description." },
              details: { type: "string", description: "Optional detailed information." },
            },
            required: ["task_description"],
          },
        },
        completed_task_ids: {
          type: "array",
          items: { type: "string" },
          description: "IDs of completed tasks (required for 'complete').",
        },
        context_update: {
          type: "string",
          description: "Important context about completed tasks (required for 'complete').",
        },
        modified_files: {
          type: "array",
          items: { type: "string" },
          description: "Files modified during the task (optional for 'complete').",
        },
        remove_task_ids: {
          type: "array",
          items: { type: "string" },
          description: "IDs of tasks to remove (required for 'remove').",
        },
        new_description: {
          type: "string",
          description: "Updated task list description (optional for 'add'/'remove').",
        },
      },
      required: ["command"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const command = params["command"] as string;
    switch (command) {
      case "create": return createTaskList(params);
      case "complete": return completeTasks(params);
      case "add": return addTasks(params);
      case "remove": return removeTasks(params);
      case "list": return listTasks();
      default: return { content: `Unknown command: ${command}`, isError: true };
    }
  },
};

// ── State ──────────────────────────────────────────────────────────────────

interface TaskItem {
  id: string;
  description: string;
  details?: string;
  completed: boolean;
  context?: string;
  modifiedFiles?: string[];
}

interface TaskList {
  description: string;
  tasks: TaskItem[];
  createdAt: string;
}

let currentTaskList: TaskList | null = null;
let taskCounter = 0;

function createTaskList(params: Record<string, unknown>): ToolResult {
  const description = params["task_list_description"] as string;
  const tasks = params["tasks"] as Array<{ task_description: string; details?: string }>;

  if (!description) return { content: "Error: 'task_list_description' is required for create.", isError: true };
  if (!tasks || tasks.length === 0) return { content: "Error: 'tasks' array is required for create.", isError: true };

  taskCounter = 0;
  currentTaskList = {
    description,
    tasks: tasks.map((t) => ({
      id: String(++taskCounter),
      description: t.task_description,
      details: t.details,
      completed: false,
    })),
    createdAt: new Date().toISOString(),
  };

  return {
    content: JSON.stringify({
      description: currentTaskList.description,
      tasks: currentTaskList.tasks.map((t) => ({ id: t.id, description: t.description, completed: t.completed })),
      message: `Task list created with ${currentTaskList.tasks.length} tasks.`,
    }, null, 2),
    isError: false,
  };
}

function completeTasks(params: Record<string, unknown>): ToolResult {
  if (!currentTaskList) return { content: "Error: No task list exists. Create one first.", isError: true };

  const ids = params["completed_task_ids"] as string[];
  const context = params["context_update"] as string;
  const modifiedFiles = params["modified_files"] as string[] | undefined;

  if (!ids || ids.length === 0) return { content: "Error: 'completed_task_ids' is required.", isError: true };
  if (!context) return { content: "Error: 'context_update' is required for complete.", isError: true };

  for (const id of ids) {
    const task = currentTaskList.tasks.find((t) => t.id === id);
    if (task) {
      task.completed = true;
      task.context = context;
      task.modifiedFiles = modifiedFiles;
    }
  }

  const done = currentTaskList.tasks.filter((t) => t.completed).length;
  const total = currentTaskList.tasks.length;
  const next = currentTaskList.tasks.find((t) => !t.completed);

  return {
    content: JSON.stringify({
      context: context,
      modified_files: modifiedFiles,
      description: currentTaskList.description,
      tasks: currentTaskList.tasks.map((t) => ({
        id: t.id,
        description: t.description,
        completed: t.completed,
      })),
      progress: `${done}/${total}`,
      next_task: next ? { id: next.id, description: next.description } : null,
    }, null, 2),
    isError: false,
  };
}

function addTasks(params: Record<string, unknown>): ToolResult {
  if (!currentTaskList) return { content: "Error: No task list exists. Create one first.", isError: true };

  const newTasks = params["new_tasks"] as Array<{ task_description: string; details?: string }>;
  const newDescription = params["new_description"] as string | undefined;

  if (!newTasks || newTasks.length === 0) return { content: "Error: 'new_tasks' is required for add.", isError: true };

  if (newDescription) currentTaskList.description = newDescription;

  for (const t of newTasks) {
    currentTaskList.tasks.push({
      id: String(++taskCounter),
      description: t.task_description,
      details: t.details,
      completed: false,
    });
  }

  return {
    content: JSON.stringify({
      description: currentTaskList.description,
      tasks: currentTaskList.tasks.map((t) => ({ id: t.id, description: t.description, completed: t.completed })),
      message: `Added ${newTasks.length} task(s).`,
    }, null, 2),
    isError: false,
  };
}

function removeTasks(params: Record<string, unknown>): ToolResult {
  if (!currentTaskList) return { content: "Error: No task list exists.", isError: true };

  const ids = params["remove_task_ids"] as string[];
  const newDescription = params["new_description"] as string | undefined;

  if (!ids || ids.length === 0) return { content: "Error: 'remove_task_ids' is required for remove.", isError: true };

  if (newDescription) currentTaskList.description = newDescription;
  currentTaskList.tasks = currentTaskList.tasks.filter((t) => !ids.includes(t.id));

  return {
    content: JSON.stringify({
      description: currentTaskList.description,
      tasks: currentTaskList.tasks.map((t) => ({ id: t.id, description: t.description, completed: t.completed })),
      message: `Removed ${ids.length} task(s).`,
    }, null, 2),
    isError: false,
  };
}

function listTasks(): ToolResult {
  if (!currentTaskList) return { content: "No task list exists.", isError: false };

  const done = currentTaskList.tasks.filter((t) => t.completed).length;
  const total = currentTaskList.tasks.length;

  return {
    content: JSON.stringify({
      description: currentTaskList.description,
      progress: `${done}/${total} completed`,
      tasks: currentTaskList.tasks.map((t) => ({
        id: t.id,
        status: t.completed ? "✓" : "○",
        description: t.description,
      })),
    }, null, 2),
    isError: false,
  };
}
