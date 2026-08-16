export interface JestResult { totalTests:number; passed:number; failed:number; skipped:number; duration:number; failedTests:string[]; }
export function parseJestOutput(output: string): JestResult {
  const totalMatch = output.match(/Tests:\s+(?:(\d+) skipped, )?(?:(\d+) failed, )?(\d+) passed, (\d+) total/);
  const durationMatch = output.match(/Time:\s+([\d.]+)\s*s/);
  const failedTests: string[] = [];
  const failRegex = /● (.+)/g; let m;
  while ((m = failRegex.exec(output)) !== null) failedTests.push(m[1]);
  return {
    totalTests: totalMatch ? parseInt(totalMatch[4] ?? "0") : 0,
    passed: totalMatch ? parseInt(totalMatch[3] ?? "0") : 0,
    failed: totalMatch ? parseInt(totalMatch[2] ?? "0") : 0,
    skipped: totalMatch ? parseInt(totalMatch[1] ?? "0") : 0,
    duration: durationMatch ? parseFloat(durationMatch[1] ?? "0") : 0,
    failedTests,
  };
}
