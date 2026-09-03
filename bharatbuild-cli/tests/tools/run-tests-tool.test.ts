import { describe, it, expect } from "vitest";
import { parseVitestOutput } from "../../src/tools/testing/vitest-parser.js";
import { runTestsDefinition } from "../../src/tools/testing/run-tests-tool.js";
import { ToolDispatcher } from "../../src/runtime/tool-dispatcher.js";
import { EventStream } from "../../src/runtime/event-stream.js";

const VITEST_PASS = `
 RUN  v4.1.10 D:/project

 Test Files  1 passed (1)
      Tests  12 passed (12)
   Start at  12:00:00
   Duration  800ms
`;

const VITEST_FAIL = `
 ❯ tests/ui/thing.test.ts (2 tests | 1 failed) 120ms
     × fails on purpose 5ms

 FAIL  tests/ui/thing.test.ts > deliberately failing > fails on purpose
AssertionError: expected 1 to be 2

 Test Files  1 failed (1)
      Tests  1 failed | 1 passed (2)
`;

const VITEST_MIXED = `
 Test Files  1 failed | 15 passed (17)
      Tests  3 failed | 194 passed | 2 skipped (199)
`;

describe("vitest parser", () => {
  it("reads the Tests line, not the Test Files line", () => {
    // The pytest parser used to claim this output and report the *file* count,
    // so a 12-test file came back as "1 passed, 1 total".
    const r = parseVitestOutput(VITEST_PASS);
    expect(r).not.toBeNull();
    expect(r!.totalTests).toBe(12);
    expect(r!.passed).toBe(12);
    expect(r!.failed).toBe(0);
  });

  it("reads a failing run", () => {
    const r = parseVitestOutput(VITEST_FAIL)!;
    expect(r.failed).toBe(1);
    expect(r.passed).toBe(1);
    expect(r.totalTests).toBe(2);
  });

  it("names the failing tests", () => {
    const r = parseVitestOutput(VITEST_FAIL)!;
    expect(r.failedTests.join(" ")).toContain("fails on purpose");
  });

  it("handles failed | passed | skipped together", () => {
    const r = parseVitestOutput(VITEST_MIXED)!;
    expect(r).toMatchObject({ failed: 3, passed: 194, skipped: 2, totalTests: 199 });
  });

  it("returns null for output that is not vitest", () => {
    expect(parseVitestOutput("Tests: 1 failed, 4 passed, 5 total")).toBeNull();
    expect(parseVitestOutput("3 failed, 529 passed in 391.92s")).toBeNull();
    expect(parseVitestOutput("random text")).toBeNull();
  });
});

describe("run_tests tool registration", () => {
  it("is advertised to the model", () => {
    const names = (new ToolDispatcher(new EventStream()).getDefinitions() as Array<{ name: string }>)
      .map((d) => d.name);
    expect(names).toContain("run_tests");
  });

  it("declares an optional filter and working_dir", () => {
    const schema = runTestsDefinition.input_schema as {
      properties: Record<string, unknown>; required?: string[];
    };
    expect(schema.properties).toHaveProperty("filter");
    expect(schema.properties).toHaveProperty("working_dir");
    // Both optional: the common call is a bare run_tests().
    expect(schema.required ?? []).toEqual([]);
  });

  it("tells the model to prefer it over the shell", () => {
    expect(runTestsDefinition.description).toMatch(/shell/i);
  });
});
