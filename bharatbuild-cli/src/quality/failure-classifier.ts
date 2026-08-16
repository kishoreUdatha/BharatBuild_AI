export type FailureCategory = "build_error"|"test_failure"|"type_error"|"import_error"|"runtime_error"|"network_error"|"unknown";
export interface ClassifiedFailure { category:FailureCategory; summary:string; files:string[]; fixable:boolean; }
export function classifyFailure(output: string): ClassifiedFailure {
  const low=output.toLowerCase(); const files=[...output.matchAll(/(?:src|app|lib)\/[\w/.-]+\.(ts|js|py|java)/g)].map((m)=>m[0]);
  if (/TS\d{4}|type error|typescript/.test(low)) return {category:"type_error",summary:"TypeScript type error",files,fixable:true};
  if (/cannot find module|module not found|importerror/.test(low)) return {category:"import_error",summary:"Import not found",files,fixable:true};
  if (/compilation failed|build failed/.test(low)) return {category:"build_error",summary:"Build failed",files,fixable:true};
  if (/assertionerror|expect|assert|test.*fail/i.test(output)) return {category:"test_failure",summary:"Test assertion failed",files,fixable:true};
  if (/econnrefused|enotfound|network|timeout/.test(low)) return {category:"network_error",summary:"Network error",files:[],fixable:false};
  return {category:"unknown",summary:"Unknown error",files,fixable:false};
}
