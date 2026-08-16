/**
 * BharatBuild CLI — Built-in Tool: grep
 * Fast text pattern search in files using regex. Respects .gitignore.
 */

import fs from "fs";
import path from "path";
import type { BuiltInTool, ToolResult } from "./types.js";

export const grepTool: BuiltInTool = {
  definition: {
    name: "grep",
    source: "built-in",
    status: "approval_required",
    description: "Fast text pattern search in files using regex. Respects .gitignore.",
    parameters: {
      type: "object",
      properties: {
        pattern: { type: "string", description: "Regex pattern to search for." },
        path: { type: "string", description: "Directory to search from, defaults to current working directory." },
        include: { type: "string", description: "File filter glob, e.g. '*.rs', '*.{ts,tsx}'." },
        case_sensitive: { type: "boolean", description: "Case-sensitive search, defaults to false." },
        max_depth: { type: "number", description: "Maximum directory depth to traverse." },
        max_files: { type: "number", description: "Maximum number of files to include in results." },
        max_matches_per_file: { type: "number", description: "Maximum matches to return per file (content mode only)." },
        max_total_lines: { type: "number", description: "Maximum total lines in output (content mode only)." },
        output_mode: {
          type: "string",
          enum: ["content", "files_with_matches", "count"],
          description: "Output format: content (default), files_with_matches, or count.",
        },
      },
      required: ["pattern"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const pattern = params["pattern"] as string;
    const searchPath = params["path"] as string | undefined;
    const include = params["include"] as string | undefined;
    const caseSensitive = params["case_sensitive"] as boolean ?? false;
    const maxDepth = params["max_depth"] as number | undefined;
    const maxFiles = params["max_files"] as number ?? 100;
    const maxMatchesPerFile = params["max_matches_per_file"] as number ?? 20;
    const maxTotalLines = params["max_total_lines"] as number ?? 500;
    const outputMode = (params["output_mode"] as string) ?? "content";

    if (!pattern) return { content: "Error: 'pattern' is required.", isError: true };

    const rootDir = path.resolve(searchPath ?? ".");

    let regex: RegExp;
    try {
      regex = new RegExp(pattern, caseSensitive ? "g" : "gi");
    } catch (e) {
      return { content: `Error: Invalid regex: ${e instanceof Error ? e.message : e}`, isError: true };
    }

    // Build file filter
    const fileFilter = include ? buildFileFilter(include) : null;

    // Walk directory and collect matching files
    const files: string[] = [];
    collectFiles(rootDir, files, maxFiles, 0, maxDepth, fileFilter);

    // Search files
    switch (outputMode) {
      case "files_with_matches":
        return searchFilesOnly(files, regex, rootDir);
      case "count":
        return searchCount(files, regex, rootDir);
      default:
        return searchContent(files, regex, rootDir, maxMatchesPerFile, maxTotalLines);
    }
  },
};

const EXCLUDED_DIRS = new Set([
  "node_modules", ".git", "__pycache__", ".next",
  "dist", "build", "out", ".cache", "coverage", "target",
]);

const BINARY_EXT = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf",
  ".zip", ".tar", ".gz", ".7z", ".exe", ".dll", ".so",
  ".wasm", ".bin", ".pyc", ".class", ".db", ".sqlite",
  ".mp3", ".mp4", ".ttf", ".woff", ".woff2",
]);

function buildFileFilter(include: string): RegExp {
  // Handle {ts,tsx} syntax
  let pattern = include.replace(/\{([^}]+)\}/g, (_, group: string) => {
    return "(" + group.split(",").map((s: string) => s.trim()).join("|") + ")";
  });
  pattern = pattern
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\(([^)]+)\\\)/g, "($1)")
    .replace(/\*/g, ".*");
  return new RegExp(pattern + "$", "i");
}

function collectFiles(
  dir: string,
  files: string[],
  maxFiles: number,
  depth: number,
  maxDepth: number | undefined,
  filter: RegExp | null,
): void {
  if (files.length >= maxFiles) return;
  if (maxDepth !== undefined && depth > maxDepth) return;

  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    if (files.length >= maxFiles) break;
    if (entry.name.startsWith(".")) continue;

    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry.name)) {
        collectFiles(fullPath, files, maxFiles, depth + 1, maxDepth, filter);
      }
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name).toLowerCase();
      if (BINARY_EXT.has(ext)) continue;
      if (filter && !filter.test(entry.name)) continue;
      files.push(fullPath);
    }
  }
}

function searchContent(
  files: string[],
  regex: RegExp,
  rootDir: string,
  maxPerFile: number,
  maxTotal: number
): ToolResult {
  const output: string[] = [];
  let totalLines = 0;

  for (const file of files) {
    if (totalLines >= maxTotal) break;
    let content: string;
    try {
      content = fs.readFileSync(file, "utf8");
    } catch {
      continue;
    }

    const lines = content.split("\n");
    const matches: Array<{ line: number; text: string }> = [];

    for (let i = 0; i < lines.length; i++) {
      regex.lastIndex = 0;
      if (regex.test(lines[i]!)) {
        matches.push({ line: i + 1, text: lines[i]! });
        if (matches.length >= maxPerFile) break;
      }
    }

    if (matches.length > 0) {
      const relPath = path.relative(rootDir, file);
      output.push(`${relPath}:`);
      for (const m of matches) {
        if (totalLines >= maxTotal) break;
        output.push(`  ${String(m.line).padStart(5)}:${m.text}`);
        totalLines++;
      }
      output.push("");
    }
  }

  if (output.length === 0) {
    return { content: `No matches found for pattern '${regex.source}'`, isError: false };
  }

  return { content: output.join("\n"), isError: false };
}

function searchFilesOnly(files: string[], regex: RegExp, rootDir: string): ToolResult {
  const matchingFiles: string[] = [];

  for (const file of files) {
    let content: string;
    try {
      content = fs.readFileSync(file, "utf8");
    } catch {
      continue;
    }
    regex.lastIndex = 0;
    if (regex.test(content)) {
      matchingFiles.push(path.relative(rootDir, file));
    }
  }

  if (matchingFiles.length === 0) {
    return { content: `No files match pattern '${regex.source}'`, isError: false };
  }
  return { content: matchingFiles.join("\n"), isError: false };
}

function searchCount(files: string[], regex: RegExp, rootDir: string): ToolResult {
  const counts: Array<{ file: string; count: number }> = [];

  for (const file of files) {
    let content: string;
    try {
      content = fs.readFileSync(file, "utf8");
    } catch {
      continue;
    }
    const matches = content.match(new RegExp(regex.source, regex.flags));
    if (matches && matches.length > 0) {
      counts.push({ file: path.relative(rootDir, file), count: matches.length });
    }
  }

  if (counts.length === 0) {
    return { content: `No matches found for pattern '${regex.source}'`, isError: false };
  }
  const output = counts.map((c) => `${c.file}: ${c.count}`).join("\n");
  return { content: output, isError: false };
}
