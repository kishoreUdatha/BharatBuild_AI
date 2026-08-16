export interface JUnitResult { totalTests:number; passed:number; failed:number; errors:number; skipped:number; failedTests:string[]; }
export function parseJUnitOutput(output: string): JUnitResult {
  const tests = parseInt(output.match(/Tests run: (\d+)/)?.[1] ?? "0");
  const failed = parseInt(output.match(/Failures: (\d+)/)?.[1] ?? "0");
  const errors = parseInt(output.match(/Errors: (\d+)/)?.[1] ?? "0");
  const skipped = parseInt(output.match(/Skipped: (\d+)/)?.[1] ?? "0");
  const failedTests: string[] = [];
  const failRegex = /FAILED: (.+)/g; let m;
  while ((m = failRegex.exec(output)) !== null) failedTests.push(m[1] ?? "");
  return { totalTests:tests, passed:tests-failed-errors-skipped, failed, errors, skipped, failedTests };
}
