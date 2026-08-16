import { runTests } from "../tools/testing/run-tests.js";
export interface TestValidation { passed:boolean; total:number; failed:number; output:string; }
export async function validateTests(cwd?: string, filter?: string): Promise<TestValidation> {
  const r=await runTests(filter,cwd); const failMatch=r.output.match(/(\d+)\s+fail/i); const totalMatch=r.output.match(/(\d+)\s+total/i);
  return {passed:r.passed,total:parseInt(totalMatch?.[1]??"0"),failed:parseInt(failMatch?.[1]??"0"),output:r.output};
}
