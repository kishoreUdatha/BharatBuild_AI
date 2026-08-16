import { scanRepository, type RepoSummary } from "./repository-scanner.js"; import { detectStack } from "./stack-detector.js";
export interface ProjectContext { projectDir:string; summary:RepoSummary; systemPromptAddition:string; }
export function buildProjectContext(projectDir: string): ProjectContext {
  const summary=scanRepository(projectDir); const stack=detectStack(projectDir);
  const systemPromptAddition=[`Working directory: ${projectDir}`,`Language: ${stack.language}`,stack.framework?`Framework: ${stack.framework}`:"",stack.database?`Database: ${stack.database}`:"",`Total files: ${summary.totalFiles}`].filter(Boolean).join("\n");
  return { projectDir, summary, systemPromptAddition };
}
