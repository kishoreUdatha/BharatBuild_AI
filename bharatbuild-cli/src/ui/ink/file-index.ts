/**
 * The list of files `@` completes against.
 *
 * Walking the tree on every keystroke would stall the input box on any real
 * repo, so the result is cached. The cache is short-lived rather than
 * permanent: the agent creates files during a session, and a picker that
 * cannot see the file that was just written is worse than a slow one.
 */

import fs from "node:fs";
import path from "node:path";

/** Directories never worth offering. Mirrors the glob tool's exclusions. */
const EXCLUDED_DIRS = new Set([
  "node_modules", ".git", "__pycache__", ".next",
  "dist", "build", "out", ".cache", "coverage", "target",
  "venv", ".venv",
]);

/** Enough to cover a large repo without holding a pathological tree in memory. */
const MAX_FILES = 20_000;
const MAX_DEPTH = 12;

/** How long a walk stays fresh. Long enough to type, short enough to notice. */
const CACHE_MS = 5_000;

interface Cached {
  files: string[];
  at: number;
}
const cache = new Map<string, Cached>();

function walk(root: string, dir: string, out: string[], depth: number): void {
  if (out.length >= MAX_FILES || depth > MAX_DEPTH) return;

  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;                     // unreadable directory is not a failure here
  }

  for (const entry of entries) {
    if (out.length >= MAX_FILES) return;
    // Dotfiles are skipped, but a dot-directory the user is working in would
    // still be reachable by typing the path out.
    if (entry.name.startsWith(".")) continue;
    if (entry.isDirectory() && EXCLUDED_DIRS.has(entry.name)) continue;

    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(root, full, out, depth + 1);
    } else if (entry.isFile()) {
      out.push(path.relative(root, full).split(path.sep).join("/"));
    }
  }
}

/** Project files, relative to `cwd`, with forward slashes on every platform. */
export function listProjectFiles(cwd: string = process.cwd(), now: number = Date.now()): string[] {
  const key = path.resolve(cwd);
  const hit = cache.get(key);
  if (hit && now - hit.at < CACHE_MS) return hit.files;

  const files: string[] = [];
  walk(key, key, files, 0);
  files.sort();
  cache.set(key, { files, at: now });
  return files;
}

/** Drop the cache — for tests, and for anything that knows the tree changed. */
export function clearFileIndex(): void {
  cache.clear();
}
