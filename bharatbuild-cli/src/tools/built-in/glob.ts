/**
 * BharatBuild CLI — Built-in Tool: glob
 * Find files and directories whose paths match a glob pattern.
 * Respects .gitignore patterns.
 */

import fs from "fs";
import path from "path";
import type { BuiltInTool, ToolResult } from "./types.js";

export const globTool: BuiltInTool = {
  definition: {
    name: "glob",
    source: "built-in",
    status: "approval_required",
    description: "Find files and directories whose paths match a glob pattern. Respects .gitignore.",
    parameters: {
      type: "object",
      properties: {
        pattern: {
          type: "string",
          description: "Glob pattern, e.g. '**/*.rs', 'src/**/*.{ts,tsx}'",
        },
        path: {
          type: "string",
          description: "Root directory to search from. Defaults to current working directory.",
        },
        limit: {
          type: "number",
          description: "Maximum number of results to return.",
        },
        max_depth: {
          type: "number",
          description: "Maximum directory depth to traverse.",
        },
      },
      required: ["pattern"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const pattern = params["pattern"] as string;
    const rootPath = params["path"] as string | undefined;
    const limit = (params["limit"] as number) ?? 200;
    const maxDepth = params["max_depth"] as number | undefined;

    if (!pattern) return { content: "Error: 'pattern' is required.", isError: true };

    // A pattern may carry its own absolute root, which is how a model usually
    // writes one: `D:\proj\**\*.json` with no separate `path`. Matching is done
    // against paths relative to rootDir, so taking the root from `path` alone
    // searched the current directory for a pattern anchored somewhere else —
    // reporting "No files found matching 'D:\proj\**\*.json' in 'C:\Users\you'",
    // which is both wrong and a confusing thing to read.
    const split = splitAbsolutePattern(pattern);
    const rootDir = path.resolve(rootPath ?? split.root ?? ".");
    const matchPattern = split.pattern;

    try {
      const stat = fs.statSync(rootDir);
      if (!stat.isDirectory()) {
        return { content: `Error: '${rootDir}' is not a directory.`, isError: true };
      }
    } catch {
      return { content: `Error: Directory not found: '${rootDir}'`, isError: true };
    }

    // Load .gitignore patterns
    const ignorePatterns = loadGitignore(rootDir);

    // Convert glob pattern to regex
    const regex = globToRegex(matchPattern);

    // Walk and match
    const results: string[] = [];
    walkAndMatch(rootDir, rootDir, regex, ignorePatterns, results, limit, 0, maxDepth);

    if (results.length === 0) {
      return { content: `No files found matching '${matchPattern}' in '${rootDir}'`, isError: false };
    }

    const output = results.join("\n");
    const note = results.length >= limit ? `\n\n(showing first ${limit} results)` : "";
    return { content: output + note, isError: false };
  },
};

const EXCLUDED_DIRS = new Set([
  "node_modules", ".git", "__pycache__", ".next",
  "dist", "build", "out", ".cache", "coverage", "target",
  "venv", ".venv",
]);

function loadGitignore(rootDir: string): string[] {
  const gitignorePath = path.join(rootDir, ".gitignore");
  try {
    const content = fs.readFileSync(gitignorePath, "utf8");
    return content
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("#"));
  } catch {
    return [];
  }
}

function isIgnored(relPath: string, ignorePatterns: string[]): boolean {
  const parts = relPath.split(path.sep);
  for (const part of parts) {
    if (EXCLUDED_DIRS.has(part)) return true;
  }
  for (const pattern of ignorePatterns) {
    const clean = pattern.replace(/^\//, "");
    if (relPath.includes(clean) || matchSimple(relPath, clean)) return true;
  }
  return false;
}

function matchSimple(str: string, pattern: string): boolean {
  const re = new RegExp(
    "^" +
      pattern
        .replace(/[.+^${}()|[\]\\]/g, "\\$&")
        .replace(/\*\*/g, "§§")
        .replace(/\*/g, "[^/]*")
        .replace(/§§/g, ".*")
        .replace(/\?/g, ".") +
      "$"
  );
  return re.test(str);
}

/**
 * Separate an absolute pattern into the directory to search and the glob.
 *
 * A Windows pattern rooted at a drive becomes a root directory plus the
 * wildcard tail. The split is at the first segment containing a wildcard, so
 * everything before it is a real directory that can be walked.
 */
export function splitAbsolutePattern(pattern: string): { root?: string; pattern: string } {
  const normalised = pattern.replace(/\\/g, "/");
  if (!path.isAbsolute(normalised)) return { pattern: normalised };

  const parts = normalised.split("/");
  const wild = parts.findIndex((p) => /[*?[{]/.test(p));
  // Absolute with no wildcard at all: the whole thing names one file, so match
  // it by basename from its own directory.
  if (wild === -1) {
    return { root: path.dirname(normalised), pattern: path.basename(normalised) };
  }
  const root = parts.slice(0, wild).join("/");
  return { root: root || "/", pattern: parts.slice(wild).join("/") };
}

function globToRegex(pattern: string): RegExp {
  // Handle brace expansion {ts,tsx} -> (ts|tsx)
  let expanded = pattern.replace(/\{([^}]+)\}/g, (_, group: string) => {
    return "(" + group.split(",").map((s: string) => s.trim()).join("|") + ")";
  });

  // Escape regex special chars except glob chars
  expanded = expanded
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\(([^)]+)\\\)/g, "($1)") // restore brace groups
    .replace(/\*\*/g, "§§")
    .replace(/\*/g, "[^/\\\\]*")
    .replace(/§§/g, ".*")
    .replace(/\?/g, ".");

  return new RegExp("^" + expanded + "$", "i");
}

function walkAndMatch(
  rootDir: string,
  dir: string,
  regex: RegExp,
  ignorePatterns: string[],
  results: string[],
  limit: number,
  depth: number,
  maxDepth?: number
): void {
  if (results.length >= limit) return;
  if (maxDepth !== undefined && depth > maxDepth) return;

  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }

  for (const entry of entries) {
    if (results.length >= limit) break;
    if (entry.name.startsWith(".") && entry.name !== ".") continue;

    const fullPath = path.join(dir, entry.name);
    const relPath = path.relative(rootDir, fullPath).replace(/\\/g, "/");

    if (isIgnored(relPath, ignorePatterns)) continue;

    if (entry.isFile()) {
      if (regex.test(relPath) || regex.test(entry.name)) {
        results.push(fullPath);
      }
    } else if (entry.isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry.name)) {
        walkAndMatch(rootDir, fullPath, regex, ignorePatterns, results, limit, depth + 1, maxDepth);
      }
    }
  }
}
