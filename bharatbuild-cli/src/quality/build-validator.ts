import { detectBuildSystem } from "../tools/build/detect-build-system.js"; import { executeCommand } from "../tools/shell/index.js";
export interface ValidationResult { passed:boolean; errors:string[]; warnings:string[]; output:string; }
export async function validateBuild(cwd?: string): Promise<ValidationResult> {
  const bs=detectBuildSystem(cwd??process.cwd()); const r=await executeCommand({command:bs.buildCommand,working_dir:cwd});
  const errors=r.content.split("\n").filter((l)=>/error/i.test(l)&&!/warning/i.test(l));
  const warnings=r.content.split("\n").filter((l)=>/warning/i.test(l));
  return {passed:!r.isError,errors,warnings,output:r.content};
}
