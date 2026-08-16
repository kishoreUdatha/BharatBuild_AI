export interface PytestResult { totalTests:number; passed:number; failed:number; errors:number; skipped:number; duration:number; failedTests:string[]; }
export function parsePytestOutput(output: string): PytestResult {
  const summary = output.match(/(\d+) passed(?:, (\d+) failed)?(?:, (\d+) error)?(?:, (\d+) skipped)?/);
  const durationMatch = output.match(/([\d.]+)s/);
  const failedTests: string[] = [];
  const failRegex = /FAILED (.+?) -/g; let m;
  while ((m = failRegex.exec(output)) !== null) failedTests.push(m[1] ?? "");
  return {
    totalTests: summary ? (parseInt(summary[1]??'0') + parseInt(summary[2]??'0') + parseInt(summary[3]??'0')) : 0,
    passed: summary ? parseInt(summary[1]??'0') : 0,
    failed: summary ? parseInt(summary[2]??'0') : 0,
    errors: summary ? parseInt(summary[3]??'0') : 0,
    skipped: summary ? parseInt(summary[4]??'0') : 0,
    duration: durationMatch ? parseFloat(durationMatch[1]??'0') : 0,
    failedTests,
  };
}
