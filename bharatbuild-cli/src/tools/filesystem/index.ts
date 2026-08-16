/**
 * BharatBuild CLI — Filesystem Tools
 * read_file, write_file, list_files, find_files
 */

import fs from "fs";
import path from "path";
import { MAX_FILE_READ_BYTES } from "../../config/constants.js";

export interface ToolDefinition {
  name: string;
  description: string;
  input_schema: {
    type: "object";
    properties: Record<string, unknown>;
    required: string[];
  };
}

export interface ToolResult {
  content: string;
  isError: boolean;
}

// ── read_file ─────────────────────────────────────────────────────────────────

export const readFileDefinition: ToolDefinition = {
  name: "read_file",
  description:
    "Read the contents of a file. Returns the file content with line numbers. " +
    "Supports optional line range (start_line, end_line).",
  input_schema: {
    type: "object",
    properties: {
      path: { type: "string", description: "Path to the file (absolute or relative to working directory)" },
      start_line: { type: "number", description: "First line to read (1-indexed). Optional." },
      end_line: { type: "number", description: "Last line to read (1-indexed). Optional." },
    },
    required: ["path"],
  },
};

export async function readFile(input: {
  path: string;
  start_line?: number;
  end_line?: number;
}): Promise<ToolResult> {
  const filePath = path.resolve(input.path);
  try {
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) {
      return { content: `'${input.path}' is a directory. Use list_files instead.`, isError: true };
    }
    if (stat.size > MAX_FILE_READ_BYTES) {
      return { content: `File too large (${Math.round(stat.size / 1024)}KB). Max is ${Math.round(MAX_FILE_READ_BYTES / 1024)}KB.`, isError: true };
    }
    const raw = fs.readFileSync(filePath, "utf8");
    const lines = raw.split("\n");
    const start = Math.max(1, input.start_line ?? 1) - 1;
    const end = Math.min(lines.length, input.end_line ?? lines.length);
    const sliced = (input.start_line !== undefined || input.end_line !== undefined)
      ? lines.slice(start, end) : lines;
    const numbered = sliced.map((line, i) => `${String(start + i + 1).padStart(4)} | ${line}`);
    return { content: numbered.join("\n"), isError: false };
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      return { content: `File not found: '${input.path}'`, isError: true };
    }
    return { content: `Error reading file: ${err instanceof Error ? err.message : err}`, isError: true };
  }
}

// ── write_file ────────────────────────────────────────────────────────────────

export const writeFileDefinition: ToolDefinition = {
  name: "write_file",
  description:
    "Write content to a file. Creates the file (and parent directories) if it doesn't exist. " +
    "Overwrites by default. Set append=true to append.",
  input_schema: {
    type: "object",
    properties: {
      path: { type: "string", description: "Path to the file" },
      content: { type: "string", description: "Content to write" },
      append: { type: "boolean", description: "Append instead of overwrite (default: false)" },
    },
    required: ["path", "content"],
  },
};

export async function writeFile(input: {
  path: string;
  content: string;
  append?: boolean;
}): Promise<ToolResult> {
  const filePath = path.resolve(input.path);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    if (input.append) {
      fs.appendFileSync(filePath, input.content, "utf8");
      return { content: `Appended ${input.content.length} chars to '${input.path}'`, isError: false };
    }
    fs.writeFileSync(filePath, input.content, "utf8");
    return { content: `Written ${input.content.length} chars to '${input.path}'`, isError: false };
  } catch (err) {
    return { content: `Error writing file: ${err instanceof Error ? err.message : err}`, isError: true };
  }
}

// ── list_files ────────────────────────────────────────────────────────────────

export const listFilesDefinition: ToolDefinition = {
  name: "list_files",
  description: "List files and directories in a directory. Use recursive=true for subdirectories.",
  input_schema: {
    type: "object",
    properties: {
      path: { type: "string", description: "Directory path (default: current working directory)" },
      recursive: { type: "boolean", description: "List files recursively (default: false)" },
      max_depth: { type: "number", description: "Max recursion depth (default: 3)" },
      show_hidden: { type: "boolean", description: "Include hidden files (default: false)" },
    },
    required: [],
  },
};

const IGNORED_DIRS = new Set([
  "node_modules", ".git", ".svn", "__pycache__", ".next",
  "dist", "build", "out", ".cache", "coverage", "venv", ".venv",
]);

function listDir(
  dirPath: string,
  opts: { recursive: boolean; maxDepth: number; showHidden: boolean; depth?: number }
): string[] {
  const depth = opts.depth ?? 0;
  if (depth > opts.maxDepth) return [];
  let entries: fs.Dirent[];
  try { entries = fs.readdirSync(dirPath, { withFileTypes: true }); } catch { return []; }
  const pad = "  ".repeat(depth);
  const lines: string[] = [];
  entries.sort((a, b) => {
    if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const e of entries) {
    if (!opts.showHidden && e.name.startsWith(".")) continue;
    if (e.isDirectory() && IGNORED_DIRS.has(e.name)) {
      lines.push(`${pad}[dir] ${e.name}/ [skipped]`);
      continue;
    }
    if (e.isDirectory()) {
      lines.push(`${pad}[dir] ${e.name}/`);
      if (opts.recursive) {
        lines.push(...listDir(path.join(dirPath, e.name), { ...opts, depth: depth + 1 }));
      }
    } else {
      try {
        const sz = fs.statSync(path.join(dirPath, e.name)).size;
        const s = sz < 1024 ? `${sz}B` : sz < 1048576 ? `${Math.round(sz / 1024)}KB` : `${(sz / 1048576).toFixed(1)}MB`;
        lines.push(`${pad}[file] ${e.name}  (${s})`);
      } catch { lines.push(`${pad}[file] ${e.name}`); }
    }
  }
  return lines;
}

export async function listFiles(input: {
  path?: string; recursive?: boolean; max_depth?: number; show_hidden?: boolean;
}): Promise<ToolResult> {
  const dirPath = path.resolve(input.path ?? ".");
  try {
    if (!fs.statSync(dirPath).isDirectory()) {
      return { content: `'${input.path}' is not a directory.`, isError: true };
    }
  } catch { return { content: `Directory not found: '${input.path}'`, isError: true }; }
  const lines = listDir(dirPath, {
    recursive: input.recursive ?? false,
    maxDepth: input.max_depth ?? 3,
    showHidden: input.show_hidden ?? false,
  });
  if (!lines.length) return { content: `Directory '${dirPath}' is empty.`, isError: false };
  return { content: `${dirPath}:\n${lines.join("\n")}`, isError: false };
}

// ── find_files ────────────────────────────────────────────────────────────────

export const findFilesDefinition: ToolDefinition = {
  name: "find_files",
  description: "Find files matching a pattern (glob or substring). Returns matching file paths.",
  input_schema: {
    type: "object",
    properties: {
      pattern: { type: "string", description: "Filename pattern (e.g. '*.ts', 'config', 'README*')" },
      directory: { type: "string", description: "Directory to search (default: cwd)" },
      max_results: { type: "number", description: "Maximum results (default: 50)" },
      include_hidden: { type: "boolean", description: "Include hidden files (default: false)" },
    },
    required: ["pattern"],
  },
};

function matchPattern(name: string, pattern: string): boolean {
  if (!pattern.includes("*") && !pattern.includes("?")) {
    return name.toLowerCase().includes(pattern.toLowerCase());
  }
  const re = new RegExp(
    "^" + pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".") + "$",
    "i"
  );
  return re.test(name);
}

function findInDir(
  dir: string,
  pattern: string,
  opts: { maxResults: number; includeHidden: boolean },
  results: string[]
): void {
  if (results.length >= opts.maxResults) return;
  let entries: fs.Dirent[];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    if (results.length >= opts.maxResults) break;
    if (!opts.includeHidden && e.name.startsWith(".")) continue;
    if (e.isDirectory() && IGNORED_DIRS.has(e.name)) continue;
    const full = path.join(dir, e.name);
    if (e.isFile() && matchPattern(e.name, pattern)) results.push(full);
    if (e.isDirectory()) findInDir(full, pattern, opts, results);
  }
}

export async function findFiles(input: {
  pattern: string; directory?: string; max_results?: number; include_hidden?: boolean;
}): Promise<ToolResult> {
  const rootDir = path.resolve(input.directory ?? ".");
  try { fs.statSync(rootDir); } catch {
    return { content: `Directory not found: '${input.directory}'`, isError: true };
  }
  const results: string[] = [];
  findInDir(rootDir, input.pattern, {
    maxResults: input.max_results ?? 50,
    includeHidden: input.include_hidden ?? false,
  }, results);
  if (!results.length) {
    return { content: `No files found matching '${input.pattern}' in '${rootDir}'`, isError: false };
  }
  const note = results.length >= (input.max_results ?? 50)
    ? `\n(first ${input.max_results ?? 50} results shown)` : "";
  return { content: `Found ${results.length} file(s):\n\n${results.join("\n")}${note}`, isError: false };
}
