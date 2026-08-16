/**
 * BharatBuild CLI — Built-in Tool: knowledge
 * A tool for indexing and searching content across chat sessions using semantic search.
 * Persistent storage and retrieval for later use.
 */

import fs from "fs";
import path from "path";
import os from "os";
import type { BuiltInTool, ToolResult } from "./types.js";

export const knowledgeTool: BuiltInTool = {
  definition: {
    name: "knowledge",
    source: "built-in",
    status: "approval_required",
    description: "A tool for indexing and searching content across chat sessions using semantic search. Content remains available across sessions for later use.",
    parameters: {
      type: "object",
      properties: {
        command: {
          type: "string",
          enum: ["show", "add", "remove", "clear", "search", "update", "status", "cancel"],
          description: "The knowledge operation to perform.",
        },
        name: { type: "string", description: "A descriptive name for the knowledge context. Required for 'add'." },
        value: { type: "string", description: "The content to store. Required for 'add'. Can be text or a file/directory path." },
        query: { type: "string", description: "The search query string. Required for 'search'." },
        context_id: { type: "string", description: "Unique context identifier for targeted operations." },
        path: { type: "string", description: "File or directory path for 'remove' or 'update' operations." },
        limit: { type: "number", description: "Maximum number of search results to return." },
        offset: { type: "number", description: "Number of results to skip for pagination." },
        snippet_length: { type: "number", description: "Maximum character length for text snippets in results." },
        sort_by: {
          type: "string",
          enum: ["relevance", "path", "name"],
          description: "Sort order for search results.",
        },
        file_type: { type: "string", description: "Filter results by file type (e.g., 'Code', 'Markdown', 'Text')." },
      },
      required: ["command"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const command = params["command"] as string;

    switch (command) {
      case "show": return showKnowledge();
      case "add": return addKnowledge(params);
      case "remove": return removeKnowledge(params);
      case "clear": return clearKnowledge();
      case "search": return searchKnowledge(params);
      case "update": return updateKnowledge(params);
      case "status": return { content: "No background operations running.", isError: false };
      case "cancel": return { content: "No operations to cancel.", isError: false };
      default: return { content: `Unknown command: ${command}`, isError: true };
    }
  },
};

// ── Storage ────────────────────────────────────────────────────────────────

interface KnowledgeEntry {
  id: string;
  name: string;
  content: string;
  path?: string;
  fileType?: string;
  createdAt: string;
  updatedAt: string;
}

function getKnowledgeDir(): string {
  return path.join(
    process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"),
    "knowledge"
  );
}

function loadAllEntries(): KnowledgeEntry[] {
  const dir = getKnowledgeDir();
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as KnowledgeEntry; }
      catch { return null; }
    })
    .filter((e): e is KnowledgeEntry => e !== null)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

function showKnowledge(): ToolResult {
  const entries = loadAllEntries();
  if (entries.length === 0) return { content: "No knowledge bases indexed.", isError: false };

  const lines = entries.map((e) =>
    `  ${e.id.slice(0, 8)}  ${e.name.padEnd(30)}  ${e.fileType ?? "Text"}  ${e.createdAt.slice(0, 10)}`
  );
  return { content: `Knowledge bases (${entries.length}):\n\n${lines.join("\n")}`, isError: false };
}

function addKnowledge(params: Record<string, unknown>): ToolResult {
  const name = params["name"] as string;
  const value = params["value"] as string;

  if (!name) return { content: "Error: 'name' is required for add.", isError: true };
  if (!value) return { content: "Error: 'value' is required for add.", isError: true };

  const dir = getKnowledgeDir();
  fs.mkdirSync(dir, { recursive: true });

  // Check if value is a file path
  let content = value;
  let filePath: string | undefined;
  let fileType = "Text";
  try {
    const resolved = path.resolve(value);
    if (fs.existsSync(resolved)) {
      const stat = fs.statSync(resolved);
      if (stat.isFile()) {
        content = fs.readFileSync(resolved, "utf8");
        filePath = resolved;
        const ext = path.extname(resolved).toLowerCase();
        if ([".ts", ".js", ".py", ".rs", ".go", ".java", ".c", ".cpp"].includes(ext)) fileType = "Code";
        else if ([".md", ".mdx"].includes(ext)) fileType = "Markdown";
      } else if (stat.isDirectory()) {
        // Index directory
        content = indexDirectory(resolved);
        filePath = resolved;
        fileType = "Directory";
      }
    }
  } catch { /* treat as text */ }

  const entry: KnowledgeEntry = {
    id: `kb-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    name,
    content,
    path: filePath,
    fileType,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  fs.writeFileSync(path.join(dir, `${entry.id}.json`), JSON.stringify(entry, null, 2));
  return {
    content: JSON.stringify({ context_id: entry.id, name: entry.name, file_type: fileType, message: "Knowledge indexed successfully." }, null, 2),
    isError: false,
  };
}

function removeKnowledge(params: Record<string, unknown>): ToolResult {
  const contextId = params["context_id"] as string;
  const name = params["name"] as string;
  const filePath = params["path"] as string;

  const dir = getKnowledgeDir();
  const entries = loadAllEntries();

  let target: KnowledgeEntry | undefined;
  if (contextId) target = entries.find((e) => e.id === contextId);
  else if (name) target = entries.find((e) => e.name === name);
  else if (filePath) target = entries.find((e) => e.path === path.resolve(filePath));

  if (!target) return { content: "Knowledge context not found.", isError: true };

  try {
    fs.unlinkSync(path.join(dir, `${target.id}.json`));
    return { content: `Removed knowledge context: ${target.name}`, isError: false };
  } catch {
    return { content: `Error removing knowledge context.`, isError: true };
  }
}

function clearKnowledge(): ToolResult {
  const dir = getKnowledgeDir();
  if (!fs.existsSync(dir)) return { content: "Knowledge base already empty.", isError: false };

  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  for (const f of files) {
    try { fs.unlinkSync(path.join(dir, f)); } catch { /* skip */ }
  }
  return { content: `Cleared ${files.length} knowledge context(s).`, isError: false };
}

function searchKnowledge(params: Record<string, unknown>): ToolResult {
  const query = params["query"] as string;
  const contextId = params["context_id"] as string | undefined;
  const limit = (params["limit"] as number) ?? 10;
  const offset = (params["offset"] as number) ?? 0;
  const snippetLength = (params["snippet_length"] as number) ?? 200;

  if (!query) return { content: "Error: 'query' is required for search.", isError: true };

  let entries = loadAllEntries();
  if (contextId) entries = entries.filter((e) => e.id === contextId);

  // Simple keyword search (BM25-style scoring)
  const terms = query.toLowerCase().split(/\s+/);
  const scored = entries
    .map((entry) => {
      const text = (entry.name + " " + entry.content).toLowerCase();
      let score = 0;
      for (const term of terms) {
        const count = (text.match(new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g")) || []).length;
        score += count;
      }
      return { entry, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(offset, offset + limit);

  if (scored.length === 0) {
    return { content: `No results found for: "${query}"`, isError: false };
  }

  const results = scored.map((s) => ({
    context_id: s.entry.id,
    name: s.entry.name,
    score: s.score,
    snippet: s.entry.content.slice(0, snippetLength),
    file_type: s.entry.fileType,
  }));

  return { content: JSON.stringify(results, null, 2), isError: false };
}

function updateKnowledge(params: Record<string, unknown>): ToolResult {
  const contextId = params["context_id"] as string;
  const name = params["name"] as string;
  const filePath = params["path"] as string;

  if (!filePath) return { content: "Error: 'path' is required for update.", isError: true };
  if (!contextId && !name) return { content: "Error: 'context_id' or 'name' is required for update.", isError: true };

  const entries = loadAllEntries();
  let target: KnowledgeEntry | undefined;
  if (contextId) target = entries.find((e) => e.id === contextId);
  else if (name) target = entries.find((e) => e.name === name);

  if (!target) return { content: "Knowledge context not found.", isError: true };

  const resolved = path.resolve(filePath);
  try {
    const stat = fs.statSync(resolved);
    target.content = stat.isDirectory() ? indexDirectory(resolved) : fs.readFileSync(resolved, "utf8");
    target.path = resolved;
    target.updatedAt = new Date().toISOString();

    const dir = getKnowledgeDir();
    fs.writeFileSync(path.join(dir, `${target.id}.json`), JSON.stringify(target, null, 2));
    return { content: `Updated knowledge context: ${target.name}`, isError: false };
  } catch (err) {
    return { content: `Error updating: ${err instanceof Error ? err.message : err}`, isError: true };
  }
}

function indexDirectory(dir: string): string {
  const files: string[] = [];
  const walk = (d: string) => {
    let entries: fs.Dirent[];
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const entry of entries) {
      if (entry.name.startsWith(".") || entry.name === "node_modules") continue;
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile()) files.push(full);
    }
  };
  walk(dir);
  return `Directory: ${dir}\nFiles (${files.length}):\n${files.slice(0, 100).map((f) => path.relative(dir, f)).join("\n")}`;
}
