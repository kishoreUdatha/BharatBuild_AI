/**
 * What the model is told about the repository before it does anything.
 *
 * This used to be four lines and a file count: "Total files: 337" tells the
 * model a codebase exists but nothing about what is in it, so its cheapest
 * opening move was to ask the user rather than to look. A layout it can read
 * makes the first search an informed one.
 */

import fs from "fs";
import path from "path";
import { scanRepository, type RepoSummary } from "./repository-scanner.js";
import { detectStack } from "./stack-detector.js";

export interface ProjectContext {
  projectDir: string;
  summary: RepoSummary;
  systemPromptAddition: string;
}

/** Directories never worth describing. */
const SKIP_DIRS = new Set([
  "node_modules", ".git", "dist", "build", "out", "coverage",
  ".next", ".cache", "target", "venv", ".venv", "__pycache__",
]);

/** Root files that say what a project is and how it is run. */
const NOTABLE = [
  "package.json", "tsconfig.json", "pyproject.toml", "requirements.txt",
  "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
  "Makefile", "Dockerfile", "docker-compose.yml",
  "README.md", "CLAUDE.md", "AGENTS.md",
];

/** How many files sit under each top-level directory. */
function countFiles(dir: string, depth = 0): number {
  if (depth > 6) return 0;
  let n = 0;
  try {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name.startsWith(".") || SKIP_DIRS.has(e.name)) continue;
      if (e.isDirectory()) n += countFiles(path.join(dir, e.name), depth + 1);
      else if (e.isFile()) n += 1;
    }
  } catch {
    /* unreadable directory contributes nothing */
  }
  return n;
}

/**
 * The top level of the tree, with a file count per directory.
 *
 * Deliberately one level deep. A full listing would dominate the prompt and go
 * stale within a turn; the point is only to tell the model where to start
 * looking, which the top level does.
 */
export function layoutSummary(projectDir: string): string {
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(projectDir, { withFileTypes: true });
  } catch {
    return "";
  }

  const dirs = entries
    .filter((e) => e.isDirectory() && !e.name.startsWith(".") && !SKIP_DIRS.has(e.name))
    .map((e) => ({ name: e.name, files: countFiles(path.join(projectDir, e.name)) }))
    .filter((d) => d.files > 0)
    .sort((a, b) => b.files - a.files)
    .slice(0, 12);

  const files = entries
    .filter((e) => e.isFile() && NOTABLE.includes(e.name))
    .map((e) => e.name);

  const lines: string[] = [];
  if (dirs.length) {
    lines.push("Top-level directories:");
    for (const d of dirs) lines.push(`  ${d.name}/  (${d.files} files)`);
  }
  if (files.length) lines.push(`Key files: ${files.join(", ")}`);
  return lines.join("\n");
}

/** The dominant source extensions, so the model knows what it is reading. */
function mainLanguages(summary: RepoSummary): string {
  const NOISE = new Set(["md", "json", "lock", "txt", "yml", "yaml", "map", "svg", "png", "ico"]);
  const top = Object.entries(summary.languages ?? {})
    .filter(([ext]) => !NOISE.has(ext))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([ext, n]) => `.${ext} (${n})`);
  return top.join(", ");
}

export function buildProjectContext(projectDir: string): ProjectContext {
  const summary = scanRepository(projectDir);
  const stack = detectStack(projectDir);

  const systemPromptAddition = [
    `Working directory: ${projectDir}`,
    `Language: ${stack.language}`,
    stack.framework ? `Framework: ${stack.framework}` : "",
    stack.database ? `Database: ${stack.database}` : "",
    // How to run things, which the model previously had to guess at.
    stack.packageManager ? `Package manager: ${stack.packageManager}` : "",
    stack.testFramework ? `Tests: ${stack.testFramework}` : "",
    `Total files: ${summary.totalFiles}`,
    mainLanguages(summary) ? `Mostly: ${mainLanguages(summary)}` : "",
    "",
    layoutSummary(projectDir),
  ]
    .filter((l) => l !== "")
    .join("\n");

  return { projectDir, summary, systemPromptAddition };
}
