import path from "path";
const PROTECTED=["/etc","/sys","/proc","/boot","C:\\Windows","C:\\System32"];
export function isProtectedPath(filePath: string): boolean { const r=path.resolve(filePath); return PROTECTED.some((p)=>r.startsWith(p)); }
export function isOutsideProject(filePath: string, projectDir: string): boolean { return !path.resolve(filePath).startsWith(path.resolve(projectDir)); }
