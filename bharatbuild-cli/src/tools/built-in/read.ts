/**
 * BharatBuild CLI — Built-in Tool: read
 * Tool for reading files, directories and images.
 * Matches Kiro CLI's read tool with Line, Directory, and Image modes.
 */

import fs from "fs";
import path from "path";
import type { BuiltInTool, ToolResult } from "./types.js";

const MAX_FILE_SIZE = 1_000_000; // 1 MB

const EXCLUDED_DIRS_DEFAULT = ["node_modules", ".git", "dist", "build", "out", ".cache", "target"];

interface ReadOperation {
  mode: "Line" | "Directory" | "Image";
  path?: string;
  offset?: number;
  limit?: number;
  depth?: number;
  exclude_patterns?: string[];
  image_paths?: string[];
}

export const readTool: BuiltInTool = {
  definition: {
    name: "read",
    source: "built-in",
    status: "approval_required",
    description: "Tool for reading files, directories and images. Always provide an 'operations' array.",
    parameters: {
      type: "object",
      properties: {
        operations: {
          type: "array",
          description: "Array of operations to execute. Provide one element for single operation, multiple for batch.",
          items: {
            type: "object",
            properties: {
              mode: {
                type: "string",
                enum: ["Line", "Directory", "Image"],
                description: "The operation mode: Line for text files, Directory for listing, Image for image files.",
              },
              path: { type: "string", description: "Path to the file or directory (required for Line, Directory)." },
              offset: { type: "number", description: "Line offset (0-indexed) to start reading from (optional, Line mode)." },
              limit: { type: "number", description: "Number of lines to read (optional, Line mode)." },
              depth: { type: "number", description: "Depth for recursive directory listing (optional, Directory mode). Default 0." },
              exclude_patterns: {
                type: "array",
                items: { type: "string" },
                description: "Glob patterns to exclude from directory listing (optional, Directory mode).",
              },
              image_paths: {
                type: "array",
                items: { type: "string" },
                description: "List of paths to images. Required for Image mode.",
              },
            },
            required: ["mode"],
          },
        },
      },
      required: ["operations"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const operations = params["operations"] as ReadOperation[];
    if (!operations || !Array.isArray(operations) || operations.length === 0) {
      return { content: "Error: 'operations' array is required with at least one element.", isError: true };
    }

    const results: string[] = [];

    for (const op of operations) {
      try {
        switch (op.mode) {
          case "Line":
            results.push(await readLine(op));
            break;
          case "Directory":
            results.push(await readDirectory(op));
            break;
          case "Image":
            results.push(readImage(op));
            break;
          default:
            results.push(`Error: Unknown mode '${op.mode}'. Use 'Line', 'Directory', or 'Image'.`);
        }
      } catch (err) {
        results.push(`Error: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    return { content: results.join("\n\n---\n\n"), isError: false };
  },
};

async function readLine(op: ReadOperation): Promise<string> {
  if (!op.path) return "Error: 'path' is required for Line mode.";

  const filePath = path.resolve(op.path);

  try {
    const stat = fs.statSync(filePath);
    if (stat.isDirectory()) return `'${op.path}' is a directory. Use Directory mode instead.`;
    if (stat.size > MAX_FILE_SIZE) {
      return `File too large (${Math.round(stat.size / 1024)}KB). Max is ${Math.round(MAX_FILE_SIZE / 1024)}KB.`;
    }

    const raw = fs.readFileSync(filePath, "utf8");
    const lines = raw.split("\n");

    const offset = op.offset ?? 0;
    const limit = op.limit ?? lines.length - offset;
    const sliced = lines.slice(offset, offset + limit);

    const numbered = sliced.map((line, i) => `${String(offset + i + 1).padStart(5)} | ${line}`);
    return numbered.join("\n");
  } catch (err) {
    const e = err as NodeJS.ErrnoException;
    if (e.code === "ENOENT") return `File not found: '${op.path}'`;
    return `Error reading file: ${e.message}`;
  }
}

async function readDirectory(op: ReadOperation): Promise<string> {
  if (!op.path) return "Error: 'path' is required for Directory mode.";

  const dirPath = path.resolve(op.path);
  const depth = op.depth ?? 0;
  const excludes = new Set(op.exclude_patterns ?? EXCLUDED_DIRS_DEFAULT);

  try {
    const stat = fs.statSync(dirPath);
    if (!stat.isDirectory()) return `'${op.path}' is not a directory.`;
  } catch {
    return `Directory not found: '${op.path}'`;
  }

  const lines = listDirRecursive(dirPath, excludes, 0, depth);
  return `${dirPath}\n${lines.join("\n")}`;
}

function listDirRecursive(dir: string, excludes: Set<string>, currentDepth: number, maxDepth: number): string[] {
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }

  const indent = "  ".repeat(currentDepth);
  const lines: string[] = [];

  entries.sort((a, b) => {
    if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;

    if (entry.isDirectory()) {
      if (excludes.has(entry.name)) {
        lines.push(`${indent}drw  ${entry.name}/ [excluded]`);
        continue;
      }
      const fullPath = path.join(dir, entry.name);
      try {
        const stat = fs.statSync(fullPath);
        const mtime = stat.mtime.toISOString().slice(0, 16).replace("T", " ");
        lines.push(`${indent}drw ${mtime} ${fullPath}`);
      } catch {
        lines.push(`${indent}drw  ${entry.name}/`);
      }

      if (currentDepth < maxDepth) {
        lines.push(...listDirRecursive(path.join(dir, entry.name), excludes, currentDepth + 1, maxDepth));
      }
    } else {
      const fullPath = path.join(dir, entry.name);
      try {
        const stat = fs.statSync(fullPath);
        const size = stat.size;
        const mtime = stat.mtime.toISOString().slice(0, 16).replace("T", " ");
        lines.push(`${indent}-rw ${size} ${mtime} ${fullPath}`);
      } catch {
        lines.push(`${indent}-rw  ${entry.name}`);
      }
    }
  }

  return lines;
}

function readImage(op: ReadOperation): string {
  if (!op.image_paths || op.image_paths.length === 0) {
    return "Error: 'image_paths' is required for Image mode.";
  }

  const results: string[] = [];
  for (const imgPath of op.image_paths) {
    const resolved = path.resolve(imgPath);
    try {
      const stat = fs.statSync(resolved);
      const ext = path.extname(resolved).toLowerCase();
      const mimeMap: Record<string, string> = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
      };
      const mime = mimeMap[ext] ?? "application/octet-stream";
      const sizeKB = Math.round(stat.size / 1024);
      results.push(`Image: ${resolved}\n  Type: ${mime}\n  Size: ${sizeKB}KB\n  (Image content available for multimodal processing)`);
    } catch {
      results.push(`Image not found: ${imgPath}`);
    }
  }
  return results.join("\n\n");
}
