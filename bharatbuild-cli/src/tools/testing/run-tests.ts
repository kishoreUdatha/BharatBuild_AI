import { detectBuildSystem } from "../build/detect-build-system.js";
import { executeCommand } from "../shell/index.js";
export interface TestRunResult { passed: boolean; output: string; exitCode: number; }
export async function runTests(filter?: string, cwd?: string): Promise<TestRunResult> {
  const bs = detectBuildSystem(cwd ?? process.cwd());
  const cmd = filter ? `${bs.testCommand ?? "npm test"} ${filter}` : (bs.testCommand ?? "npm test");
  const r = await executeCommand({ command:cmd, working_dir:cwd });
  const passed = !r.isError && !r.content.includes("FAILED") && !r.content.includes("ERROR") && !r.content.includes("failed");
  return { passed, output:r.content, exitCode: r.isError ? 1 : 0 };
}
