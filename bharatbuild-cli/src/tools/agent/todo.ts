/**
 * BharatBuild CLI - Todo Tool
 * In-session task list management. The agent uses this to track
 * multi-step work and show progress.
 */

// ── Tool Definition ────────────────────────────────────────────────────────

export const todoDefinition = {
  name: "todo_list",
  description:
    "Manage a task list for tracking multi-step work. Use this to:\n" +
    "  - 'create': Start a new task list for a goal\n" +
    "  - 'add': Add a task to an existing list\n" +
    "  - 'complete': Mark a task as done\n" +
    "  - 'list': Show current task list with status\n" +
    "Create a task list at the start of complex multi-step tasks, then mark items complete as you finish them.",
  input_schema: {
    type: "object",
    properties: {
      command: {
        type: "string",
        enum: ["create", "add", "complete", "list"],
        description: "Operation to perform.",
      },
      title: {
        type: "string",
        description: "Title for the task list (required for create).",
      },
      list_id: {
        type: "string",
        description: "Task list ID (required for add, complete). Use the ID returned by create.",
      },
      description: {
        type: "string",
        description: "Task description (required for add).",
      },
      item_id: {
        type: "string",
        description: "Task item ID to complete (required for complete).",
      },
    },
    required: ["command"],
  },
} as const;

// ── State ──────────────────────────────────────────────────────────────────

export interface TodoItem {
  id: string;
  description: string;
  completed: boolean;
  createdAt: string;
  completedAt?: string;
}

export interface TodoList {
  id: string;
  title: string;
  items: TodoItem[];
  createdAt: string;
}

const lists = new Map<string, TodoList>();

export function createTodoList(title: string): TodoList {
  const list: TodoList = {
    id: `todo-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    title,
    items: [],
    createdAt: new Date().toISOString(),
  };
  lists.set(list.id, list);
  return list;
}

export function addTodoItem(listId: string, description: string): TodoItem | null {
  const list = lists.get(listId);
  if (!list) return null;
  const item: TodoItem = {
    id: `item-${Date.now()}-${Math.random().toString(36).slice(2, 4)}`,
    description,
    completed: false,
    createdAt: new Date().toISOString(),
  };
  list.items.push(item);
  return item;
}

export function completeTodoItem(listId: string, itemId: string): boolean {
  const list = lists.get(listId);
  if (!list) return false;
  const item = list.items.find((i) => i.id === itemId);
  if (!item) return false;
  item.completed = true;
  item.completedAt = new Date().toISOString();
  return true;
}

export function getTodoList(listId: string) { return lists.get(listId); }
export function getAllLists() { return Array.from(lists.values()); }

// ── Tool executor ──────────────────────────────────────────────────────────

export interface TodoInput {
  command: "create" | "add" | "complete" | "list";
  title?: string;
  list_id?: string;
  description?: string;
  item_id?: string;
}

export function executeTodo(input: TodoInput): { content: string; isError: boolean } {
  switch (input.command) {
    case "create": {
      if (!input.title) return { content: "Error: title is required for create", isError: true };
      const list = createTodoList(input.title);
      return {
        content: JSON.stringify({ list_id: list.id, title: list.title, message: "Task list created." }, null, 2),
        isError: false,
      };
    }
    case "add": {
      if (!input.list_id) return { content: "Error: list_id is required for add", isError: true };
      if (!input.description) return { content: "Error: description is required for add", isError: true };
      const item = addTodoItem(input.list_id, input.description);
      if (!item) return { content: `Task list not found: ${input.list_id}`, isError: true };
      return {
        content: JSON.stringify({ item_id: item.id, description: item.description, message: "Task added." }, null, 2),
        isError: false,
      };
    }
    case "complete": {
      if (!input.list_id) return { content: "Error: list_id is required for complete", isError: true };
      if (!input.item_id) return { content: "Error: item_id is required for complete", isError: true };
      const ok = completeTodoItem(input.list_id, input.item_id);
      if (!ok) return { content: `Task or list not found: ${input.list_id}/${input.item_id}`, isError: true };
      const list = getTodoList(input.list_id)!;
      const done = list.items.filter((i) => i.completed).length;
      const total = list.items.length;
      return {
        content: JSON.stringify({
          message: `Task completed (${done}/${total} done)`,
          progress: `${Math.round((done / total) * 100)}%`,
          remaining: list.items.filter((i) => !i.completed).map((i) => i.description),
        }, null, 2),
        isError: false,
      };
    }
    case "list": {
      if (input.list_id) {
        const list = getTodoList(input.list_id);
        if (!list) return { content: `Task list not found: ${input.list_id}`, isError: true };
        return {
          content: JSON.stringify({
            id: list.id,
            title: list.title,
            items: list.items.map((i) => ({ id: i.id, description: i.description, completed: i.completed })),
          }, null, 2),
          isError: false,
        };
      }
      const all = getAllLists();
      if (all.length === 0) return { content: "No task lists.", isError: false };
      return {
        content: JSON.stringify(all.map((l) => ({
          id: l.id,
          title: l.title,
          total: l.items.length,
          completed: l.items.filter((i) => i.completed).length,
        })), null, 2),
        isError: false,
      };
    }
    default:
      return { content: `Unknown command: ${input.command}`, isError: true };
  }
}