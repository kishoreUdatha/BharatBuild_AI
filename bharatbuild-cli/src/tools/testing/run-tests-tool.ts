/**
 * run_tests — model-facing test runner.
 *
 * The agent could already shell out to `execute_command("npm test")`, but that
 * hands the model a raw log and makes it infer whether anything failed. On a
 * large suite the log is mostly noise and can crowd out the rest of the
 * context. This returns a verdict first, then the failing test names, then a
 * bounded slice of output — which is what the verify→fix loop actually needs.
 */

import type { ToolDefinition, ToolResult } from "../filesystem/index.js";
import { detectBuildSystem } from "../build/detect-build-system.js";
import { executeCommand } from "../shell/index.js";
import { parseJestOutput } from "./jest-parser.js";
import { parsePytestOutput } from "./pytest-parser.js";
import { parseVitestOutput } from "./vitest-parser.js";

export const runTestsDefinition: ToolDefinition = {
  name: "run_tests",
  description:
    "Run the project's test suite and return a structured pass/fail summary with the names of failing tests. " +
    "Prefer this over running the test command through the shell: it reports the verdict directly and trims " +
    "passing noise out of the output. Use it to verify a change before reporting it as done.",
  input_schema: {
    type: "object",
    properties: {
      filter: {
        type: "string",
        description:
          "Optional pattern to narrow the run to matching tests or files (passed through to the runner).",
      },
      working_dir: {
        type: "string",
        description: "Directory to run in (default: current working directory).",
      },
    },
    required: [],
  },
};

export interface RunTestsInput {
  filter?: string;
  working_dir?: string;
}

interface Counts {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  failedTests: string[];
}

/** How many lines of raw output to keep when tests fail. */
const FAILURE_TAIL_LINES = 40;
const MAX_FAILED_NAMES = 20;

/**
 * Pick a parser from the runner's own output rather than the project type —
 * a Node project can drive pytest, and vitest prints jest-shaped summaries.
 */
function parseCounts(output: string): Counts | null {
  // Order matters, and each check must be specific to its runner. A loose
  // `\d+ passed` test let the pytest parser claim vitest output and report the
  // file count as the test count.
  const v = parseVitestOutput(output);
  if (v) {
    return {
      total: v.totalTests,
      passed: v.passed,
      failed: v.failed,
      skipped: v.skipped,
      failedTests: v.failedTests,
    };
  }

  if (/Tests:\s+.*\d+ total/.test(output)) {
    const j = parseJestOutput(output);
    if (j.totalTests > 0 || j.failed > 0) {
      return {
        total: j.totalTests,
        passed: j.passed,
        failed: j.failed,
        skipped: j.skipped,
        failedTests: j.failedTests,
      };
    }
  }

  // pytest's own summary line, e.g. "3 failed, 529 passed in 391.92s".
  if (/^=+.*\b\d+ (passed|failed|error)/m.test(output) || /\d+ (passed|failed).*\bin [\d.]+s/.test(output)) {
    const p = parsePytestOutput(output);
    if (p.totalTests > 0 || p.failed > 0) {
      return {
        total: p.totalTests,
        passed: p.passed,
        failed: p.failed + p.errors,
        skipped: p.skipped,
        failedTests: p.failedTests,
      };
    }
  }

  return null;
}

function tail(output: string, lines: number): string {
  const all = output.split("\n");
  if (all.length <= lines) return output.trim();
  return `… ${all.length - lines} earlier lines omitted\n${all.slice(-lines).join("\n").trim()}`;
}

export async function executeRunTests(input: RunTestsInput): Promise<ToolResult> {
  const cwd = input.working_dir ?? process.cwd();
  const build = detectBuildSystem(cwd);

  if (!build.testCommand) {
    return {
      content:
        `No test command detected for this project (${build.name}, ${build.language}).\n` +
        `Run a specific command with execute_command if you know it.`,
      isError: true,
    };
  }

  const command = input.filter ? `${build.testCommand} ${input.filter}` : build.testCommand;
  const started = Date.now();
  // Test suites are the slowest thing a shell tool runs; the 120s default is
  // shorter than this project's own suite, so the runner was being killed
  // mid-flight. 300s is executeCommand's ceiling.
  const run = await executeCommand({ command, working_dir: cwd, timeout_ms: 300_000 });
  const durationMs = Date.now() - started;
  const output = run.content ?? "";

  // A killed runner produced no summary and a non-zero exit, which the logic
  // below reads as "the tests failed". The agent then goes looking for failing
  // tests that do not exist. Say what actually happened instead.
  if (/Command timed out after \d+ms/.test(output)) {
    return {
      content:
        `TESTS DID NOT COMPLETE  (${command}, ${(durationMs / 1000).toFixed(1)}s)\n` +
        `The runner was still going when the timeout was reached, so nothing is known ` +
        `about pass or fail. Narrow the run with the 'filter' argument, or run a ` +
        `specific command with execute_command.`,
      isError: true,
    };
  }

  const counts = parseCounts(output);

  // The exit code is the authority on pass/fail. Scanning stdout for the word
  // "failed" — which is what the old helper did — calls a suite red whenever a
  // test *name* contains it.
  const failedByExit = run.isError;
  const failed = counts ? counts.failed > 0 || failedByExit : failedByExit;

  const header = failed ? "TESTS FAILED" : "TESTS PASSED";
  const lines: string[] = [`${header}  (${command}, ${(durationMs / 1000).toFixed(1)}s)`];

  if (counts) {
    lines.push(
      `${counts.passed} passed, ${counts.failed} failed` +
        (counts.skipped ? `, ${counts.skipped} skipped` : "") +
        `, ${counts.total} total`,
    );
    if (counts.failedTests.length > 0) {
      lines.push("", "Failing tests:");
      for (const name of counts.failedTests.slice(0, MAX_FAILED_NAMES)) {
        lines.push(`  ${name}`);
      }
      const extra = counts.failedTests.length - MAX_FAILED_NAMES;
      if (extra > 0) lines.push(`  … and ${extra} more`);
    }
  } else {
    // Unrecognised runner — say so instead of implying a parsed result.
    lines.push("(could not parse a summary from this runner's output)");
  }

  // Passing runs need no log; failing ones need enough to diagnose.
  if (failed) {
    lines.push("", tail(output, FAILURE_TAIL_LINES));
  }

  return { content: lines.join("\n"), isError: failed };
}
