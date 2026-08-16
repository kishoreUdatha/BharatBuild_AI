/**
 * BharatBuild CLI - Knowledge Tool
 * Persistent knowledge base the agent can read/write across sessions.
 */

import fs from "fs";
import path from "path";
import os from "os";

// ── Tool Definition ────────────────────────────────────────────────────────

export const knowledgeDefinition = {
  name: "knowledge",
  description:
    "Access and update a persistent knowledge base. Use this to:\n" +
    "  - 'add': Store a fact, pattern, or snippet for future reference\n" +
    "  - 'search': Find previously stored knowledge relevant to the current task\n" +
    "  - 'list': Show all stored knowledge entries\n" +
    "  - 'remove': Delete a knowledge entry by ID",
  input_schema: {
    type: "object",
    properties: {
      command: {
        type: "string",
        enum: ["add", "search", "list", "remove"],
        description: "Operation to perform.",
      },
      name: {
        type: "string",
        description: "Name/title for the knowledge entry (required for add).",
      },
      content: {
        type: "string",
        description: "Content to store (required for add).",
      },
      tags: {
        type: "array",
        items: { type: "string" },
        description: "Tags for categorisation (optional for add).",
      },
      query: {
        type: "string",
        description: "Search query (required for search).",
      },
      id: {
        type: "string",
        description: "Entry ID (required for remove).",
      },
    },
    required: ["command"],
  },
} as const;

// ── Storage ────────────────────────────────────────────────────────────────

export interface KnowledgeEntry {
  id: string;
  name: string;
  content: string;
  tags: string[];
  createdAt: string;
  filePath?: string;
}

function getKnowledgeDir(): string {
  return path.join(
    process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"),
    "knowledge"
  );
}

export function addKnowledge(name: string, content: string, tags: string[] = [], filePath?: string): KnowledgeEntry {
  const dir = getKnowledgeDir();
  fs.mkdirSync(dir, { recursive: true });
  const entry: KnowledgeEntry = {
    id: `kb-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    name,
    content,
    tags,
    createdAt: new Date().toISOString(),
    filePath,
  };
  fs.writeFileSync(path.join(dir, `${entry.id}.json`), JSON.stringify(entry, null, 2));
  return entry;
}

export function searchKnowledge(query: string): KnowledgeEntry[] {
  const dir = getKnowledgeDir();
  if (!fs.existsSync(dir)) return [];
  const q = query.toLowerCase();
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => { try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as KnowledgeEntry; } catch { return null; } })
    .filter((e): e is KnowledgeEntry => e !== null)
    .filter((e) =>
      e.name.toLowerCase().includes(q) ||
      e.content.toLowerCase().includes(q) ||
      e.tags.some((t) => t.toLowerCase().includes(q))
    );
}

export function listKnowledge(): KnowledgeEntry[] {
  const dir = getKnowledgeDir();
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => { try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as KnowledgeEntry; } catch { return null; } })
    .filter((e): e is KnowledgeEntry => e !== null)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
}

export function removeKnowledge(id: string): boolean {
  try {
    fs.unlinkSync(path.join(getKnowledgeDir(), `${id}.json`));
    return true;
  } catch {
    return false;
  }
}

// ── Tool executor ──────────────────────────────────────────────────────────

export interface KnowledgeInput {
  command: "add" | "search" | "list" | "remove";
  name?: string;
  content?: string;
  tags?: string[];
  query?: string;
  id?: string;
}

export function executeKnowledge(input: KnowledgeInput): { content: string; isError: boolean } {
  switch (input.command) {
    case "add": {
      if (!input.name) return { content: "Error: name is required for add", isError: true };
      if (!input.content) return { content: "Error: content is required for add", isError: true };
      const entry = addKnowledge(input.name, input.content, input.tags ?? []);
      return {
        content: JSON.stringify({ id: entry.id, name: entry.name, message: "Knowledge stored." }, null, 2),
        isError: false,
      };
    }
    case "search": {
      if (!input.query) return { content: "Error: query is required for search", isError: true };
      const results = searchKnowledge(input.query);
      if (results.length === 0) return { content: `No knowledge found for: "${input.query}"`, isError: false };
      return {
        content: JSON.stringify(results.map((e) => ({ id: e.id, name: e.name, tags: e.tags, content: e.content.slice(0, 200) })), null, 2),
        isError: false,
      };
    }
    case "list": {
      const all = listKnowledge();
      if (all.length === 0) return { content: "Knowledge base is empty.", isError: false };
      return {
        content: JSON.stringify(all.map((e) => ({ id: e.id, name: e.name, tags: e.tags, createdAt: e.createdAt })), null, 2),
        isError: false,
      };
    }
    case "remove": {
      if (!input.id) return { content: "Error: id is required for remove", isError: true };
      const ok = removeKnowledge(input.id);
      return ok
        ? { content: `Removed knowledge entry: ${input.id}`, isError: false }
        : { content: `Knowledge entry not found: ${input.id}`, isError: true };
    }
    default:
      return { content: `Unknown command: ${input.command}`, isError: true };
  }
}