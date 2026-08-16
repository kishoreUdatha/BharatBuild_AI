/**
 * BharatBuild CLI — Search Tools
 * search_code (grep-style), search_files (by name/content)
 */

import fs from "fs";
import path from "path";
import { MAX_SEARCH_RESULTS } from "../../config/constants.js";
import type { ToolDefinition, ToolResult } from "../filesystem/index.js";

const IGNORED_DIRS = new Set([
  "node_modules", ".git", "__pycache__", ".next",
  "dist", "build", "out", ".cache", "coverage", "venv", ".venv",
]);
const BINARY_EXT = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
  ".zip", ".tar", ".gz", ".7z", ".exe", ".dll", ".so",
  ".wasm", ".bin", ".pyc", ".class", ".db", ".sqlite",
  ".mp3", ".mp4", ".ttf", ".woff", ".woff2",
]);

function isBinary(file: string): boolean {
  return BINARY_EXT.has(path.extname(file).toLowerCase());
}

function walkDir(dir: string, extensions: Set<string> | null, results: string[]): void {
  let entries: fs.Dirent[];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (!IGNORED_DIRS.has(e.name) && !e.name.startsWith(".")) walkDir(full, extensions, results);
    } else if (e.isFile() && !isBinary(e.name)) {
      if (!extensions || extensions.has(path.extname(e.name).toLowerCase())) results.push(full);
    }
  }
}

// ── search_code ───────────────────────────────────────────────────────────────

export const searchCodeDefinition: ToolDefinition = {
  name: "search_code",
  description:
    "Search for a pattern (text or regex) across all source files. " +
    "Returns matching lines with file path and line numbers. Like grep.",
  input_schema: {
    type: "object",
    properties: {
      pattern: { type: "string", description: "Text or regex pattern to search" },
      directory: { type: "string", description: "Directory to search (default: cwd)" },
      file_extensions: { type: "array", items: { type: "string" }, description: "Filter by extensions (e.g. ['.ts', '.js'])" },
      case_sensitive: { type: "boolean", description: "Case-sensitive search (default: false)" },
      max_results: { type: "number", description: `Max matches (default: ${MAX_SEARCH_RESULTS})` },
      context_lines: { type: "number", description: "Context lines before/after match (default: 0)" },
      is_regex: { type: "boolean", description: "Treat pattern as regex (default: false)" },
    },
    required: ["pattern"],
  },
};

interface Match {
  file: string;
  line: number;
  content: string;
  before?: string[];
  after?: string[];
}

export async function searchCode(input: {
  pattern: string;
  directory?: string;
  file_extensions?: string[];
  case_sensitive?: boolean;
  max_results?: number;
  context_lines?: number;
  is_regex?: boolean;
}): Promise<ToolResult> {
  const rootDir = path.resolve(input.directory ?? ".");
  try { fs.statSync(rootDir); } catch {
    return { content: `Directory not found: '${input.directory}'`, isError: true };
  }

  const maxResults = input.max_results ?? MAX_SEARCH_RESULTS;
  const ctx = input.context_lines ?? 0;
  const flags = input.case_sensitive ? "" : "i";

  let regex: RegExp;
  try {
    const pat = input.is_regex
      ? input.pattern
      : input.pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    regex = new RegExp(pat, flags);
  } catch (e) {
    return { content: `Invalid regex: ${e instanceof Error ? e.message : e}`, isError: true };
  }

  const extensions = input.file_extensions?.length
    ? new Set(input.file_extensions.map((e) => (e.startsWith(".") ? e : `.${e}`).toLowerCase()))
    : null;

  const allFiles: string[] = [];
  walkDir(rootDir, extensions, allFiles);

  const allMatches: Match[] = [];
  for (const file of allFiles) {
    if (allMatches.length >= maxResults) break;
    let content: string;
    try { content = fs.readFileSync(file, "utf8"); } catch { continue; }
    const lines = content.split("\n");
    for (let i = 0; i < lines.length && allMatches.length < maxResults; i++) {
      if (regex.test(lines[i])) {
        allMatches.push({
          file,
          line: i + 1,
          content: lines[i],
          before: ctx > 0 ? lines.slice(Math.max(0, i - ctx), i) : undefined,
          after: ctx > 0 ? lines.slice(i + 1, Math.min(lines.length, i + 1 + ctx)) : undefined,
        });
      }
    }
  }

  if (!allMatches.length) {
    return { content: `No matches for '${input.pattern}' in '${rootDir}'`, isError: false };
  }

  const out: string[] = [];
  let curFile = "";
  for (const m of allMatches) {
    const rel = path.relative(rootDir, m.file);
    if (rel !== curFile) {
      if (curFile) out.push("");
      out.push(rel);
      curFile = rel;
    }
    if (m.before) {
      m.before.forEach((l, i) => out.push(`  ${String(m.line - m.before!.length + i).padStart(5)} | ${l}`));
    }
    out.push(`  ${String(m.line).padStart(5)} > ${m.content}`);
    if (m.after) {
      m.after.forEach((l, i) => out.push(`  ${String(m.line + 1 + i).padStart(5)} | ${l}`));
    }
  }

  const note = allMatches.length >= maxResults
    ? `\n(showing first ${maxResults} matches — use max_results to increase)` : "";
  return {
    content: `${allMatches.length} match(es) for '${input.pattern}':\n\n${out.join("\n")}${note}`,
    isError: false,
  };
}

// ── search_files ──────────────────────────────────────────────────────────────

export const searchFilesDefinition: ToolDefinition = {
  name: "search_files",
  description: "Search for files by name pattern and/or content.",
  input_schema: {
    type: "object",
    properties: {
      name_pattern: { type: "string", description: "Filename pattern (substring or glob, e.g. '*.config.ts')" },
      content_pattern: { type: "string", description: "Content to search for inside files" },
      directory: { type: "string", description: "Directory to search (default: cwd)" },
      max_results: { type: "number", description: "Max results (default: 50)" },
    },
    required: [],
  },
};

function nameMatches(name: string, pattern: string): boolean {
  if (!pattern.includes("*") && !pattern.includes("?")) {
    return name.toLowerCase().includes(pattern.toLowerCase());
  }
  const re = new RegExp(
    "^" + pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\?/g, ".") + "$",
    "i"
  );
  return re.test(name);
}

export async function searchFiles(input: {
  name_pattern?: string;
  content_pattern?: string;
  directory?: string;
  max_results?: number;
}): Promise<ToolResult> {
  if (!input.name_pattern && !input.content_pattern) {
    return { content: "Provide at least name_pattern or content_pattern.", isError: true };
  }
  const rootDir = path.resolve(input.directory ?? ".");
  const maxResults = input.max_results ?? 50;
  const contentRegex = input.content_pattern
    ? new RegExp(input.content_pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i")
    : null;

  const results: Array<{ file: string; line?: number; snippet?: string }> = [];

  function walk(dir: string): void {
    if (results.length >= maxResults) return;
    let entries: fs.Dirent[];
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (results.length >= maxResults) break;
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (!IGNORED_DIRS.has(e.name) && !e.name.startsWith(".")) walk(full);
      } else if (e.isFile() && !isBinary(e.name)) {
        if (input.name_pattern && !nameMatches(e.name, input.name_pattern)) continue;
        if (contentRegex) {
          let fc: string;
          try { fc = fs.readFileSync(full, "utf8"); } catch { continue; }
          const ls = fc.split("\n");
          for (let i = 0; i < ls.length && results.length < maxResults; i++) {
            if (contentRegex.test(ls[i])) {
              results.push({
                file: path.relative(rootDir, full),
                line: i + 1,
                snippet: ls[i].trim().slice(0, 100),
              });
            }
          }
        } else {
          results.push({ file: path.relative(rootDir, full) });
        }
      }
    }
  }

  walk(rootDir);
  if (!results.length) return { content: `No files found in '${rootDir}'`, isError: false };
  const lines = results.map((r) =>
    r.line !== undefined ? `  ${r.file}:${r.line}  ${r.snippet ?? ""}` : `  ${r.file}`
  );
  const note = results.length >= maxResults ? `\n(first ${maxResults} results)` : "";
  return { content: `Found ${results.length} result(s):\n\n${lines.join("\n")}${note}`, isError: false };
}
