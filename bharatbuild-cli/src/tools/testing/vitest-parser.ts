/**
 * Vitest summary parser.
 *
 * Vitest prints a two-line summary with no colons:
 *
 *     Test Files  1 failed | 15 passed (17)
 *          Tests  3 failed | 194 passed (197)
 *
 * The jest parser needs `Tests:` with a colon, so it never matched. The pytest
 * parser then matched on the bare `\d+ passed` and reported the *file* count as
 * the test count — a 12-test file came back as "1 passed, 1 total". Counts the
 * model is told have to be right, so vitest gets its own parser.
 */

export interface VitestResult {
  totalTests: number;
  passed: number;
  failed: number;
  skipped: number;
  failedTests: string[];
}

/** `3 failed | 194 passed (197)` → counts. */
function parseSummaryLine(segment: string, total: number): Omit<VitestResult, "failedTests"> {
  const read = (label: string): number => {
    const m = segment.match(new RegExp(`(\\d+)\\s+${label}`));
    return m ? parseInt(m[1]!, 10) : 0;
  };
  return {
    totalTests: total,
    passed: read("passed"),
    failed: read("failed"),
    skipped: read("skipped") + read("todo"),
  };
}

export function parseVitestOutput(output: string): VitestResult | null {
  // Anchor on the "Tests" line specifically — "Test Files" counts files, and
  // conflating the two is exactly the bug this parser exists to avoid.
  const testsLine = output.match(/^[^\S\n]*Tests[^\S\n]+(.+?)\((\d+)\)[^\S\n]*$/m);
  if (!testsLine) return null;

  const counts = parseSummaryLine(testsLine[1]!, parseInt(testsLine[2]!, 10));

  // Failing test names: "FAIL  path > suite > case", or the "×" rows.
  const failedTests: string[] = [];
  for (const m of output.matchAll(/^\s*FAIL\s+(.+?)\s*$/gm)) {
    const name = m[1]!.trim();
    if (name && !failedTests.includes(name)) failedTests.push(name);
  }
  if (failedTests.length === 0) {
    for (const m of output.matchAll(/^\s*×\s+(.+?)(?:\s+\d+ms)?\s*$/gm)) {
      const name = m[1]!.trim();
      if (name && !failedTests.includes(name)) failedTests.push(name);
    }
  }

  return { ...counts, failedTests };
}
