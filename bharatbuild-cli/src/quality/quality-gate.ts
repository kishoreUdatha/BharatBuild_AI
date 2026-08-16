import chalk from "chalk"; import { validateBuild } from "./build-validator.js"; import { validateTests } from "./test-validator.js";
export interface QualityGateResult { passed:boolean; buildPassed:boolean; testsPassed:boolean; errors:string[]; }
export async function runQualityGate(cwd?: string): Promise<QualityGateResult> {
  console.log(chalk.bold("\n?? Quality Gate\n"));
  const build=await validateBuild(cwd); console.log(build.passed?chalk.green("  ? Build"):chalk.red("  ? Build"));
  const tests=await validateTests(cwd); console.log(tests.passed?chalk.green("  ? Tests"):chalk.red("  ? Tests"));
  const passed=build.passed&&tests.passed; console.log(passed?chalk.bold.green("\n? Quality gate passed\n"):chalk.bold.red("\n? Quality gate failed\n"));
  return {passed,buildPassed:build.passed,testsPassed:tests.passed,errors:[...build.errors]};
}
