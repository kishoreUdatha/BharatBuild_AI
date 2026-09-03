/**
 * What kind of project this is.
 *
 * The result goes into the system prompt, so a wrong answer is worse than no
 * answer: it tells the model to reason about the wrong kind of codebase. This
 * repo was reported as `Framework: react` — it depends on react because Ink
 * renders a terminal UI with it — so the model was being told a command-line
 * tool was a web app.
 */

import fs from "fs";
import path from "path";

export interface TechStack {
  language: string;
  framework?: string;
  database?: string;
  packageManager?: string;
  testFramework?: string;
}

interface PackageJson {
  bin?: unknown;
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
}

/**
 * The framework, from the dependencies.
 *
 * Order is the whole point. `react` appears in a Next.js app, a web app and an
 * Ink CLI alike, so it can only be concluded once the more specific cases have
 * been ruled out — and `react-dom` is what separates a browser app from a
 * terminal one.
 */
function frameworkOf(pkg: PackageJson, deps: Record<string, string>): string | undefined {
  if (deps["next"]) return "next.js";
  // A command-line tool: it declares an executable and draws with Ink rather
  // than into a DOM.
  if (deps["ink"] && pkg.bin) return "cli (ink)";
  if (deps["ink"]) return "ink";
  if (pkg.bin && (deps["commander"] || deps["yargs"] || deps["cac"])) return "cli";
  // react-dom is the discriminator: react alone does not mean a web app.
  if (deps["react"] && deps["react-dom"]) return "react";
  if (deps["@nestjs/core"]) return "nestjs";
  if (deps["fastify"]) return "fastify";
  if (deps["express"]) return "express";
  if (deps["react"]) return "react (non-browser)";
  return undefined;
}

export function detectStack(dir: string): TechStack {
  const has = (f: string) => fs.existsSync(path.join(dir, f));
  let language = "unknown";
  let framework: string | undefined;
  let database: string | undefined;
  let packageManager: string | undefined;
  let testFramework: string | undefined;

  if (has("package.json")) {
    packageManager = has("pnpm-lock.yaml") ? "pnpm" : has("yarn.lock") ? "yarn" : "npm";
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(dir, "package.json"), "utf8")) as PackageJson;
      const deps = { ...pkg.dependencies, ...pkg.devDependencies };

      // Every package.json was reported as typescript, so a plain JS project
      // was told to write types it has no compiler for.
      language = has("tsconfig.json") || deps["typescript"] ? "typescript" : "javascript";

      framework = frameworkOf(pkg, deps);

      if (deps["vitest"]) testFramework = "vitest";
      else if (deps["jest"]) testFramework = "jest";
      else if (deps["mocha"]) testFramework = "mocha";

      if (deps["pg"] || deps["postgres"]) database = "postgresql";
      else if (deps["mongoose"]) database = "mongodb";
      else if (deps["prisma"] || deps["@prisma/client"]) database = "prisma";
    } catch {
      // Malformed package.json — the language guess stands, the rest is unknown.
      language = has("tsconfig.json") ? "typescript" : "javascript";
    }
  } else if (has("requirements.txt") || has("pyproject.toml")) {
    language = "python";
    try {
      const req = has("requirements.txt")
        ? fs.readFileSync(path.join(dir, "requirements.txt"), "utf8")
        : fs.readFileSync(path.join(dir, "pyproject.toml"), "utf8");
      if (req.includes("fastapi")) framework = "fastapi";
      else if (req.includes("django")) framework = "django";
      else if (req.includes("flask")) framework = "flask";
      if (/\bpytest\b/.test(req)) testFramework = "pytest";
      if (/psycopg|asyncpg/.test(req)) database = "postgresql";
    } catch {
      /* unreadable — language alone is still useful */
    }
  } else if (has("pom.xml") || has("build.gradle") || has("build.gradle.kts")) {
    language = "java";
    packageManager = has("pom.xml") ? "maven" : "gradle";
  } else if (has("go.mod")) {
    language = "go";
  } else if (has("Cargo.toml")) {
    language = "rust";
    packageManager = "cargo";
  }

  return { language, framework, database, packageManager, testFramework };
}
