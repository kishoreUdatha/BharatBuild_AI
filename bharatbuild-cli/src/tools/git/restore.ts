import { executeCommand } from "../shell/index.js";
export async function restoreCheckpoint(hash: string, cwd?: string) {
  const r = await executeCommand({ command: `git checkout ${hash}`, working_dir: cwd });
  return { success: !r.isError, error: r.isError ? r.content : undefined };
}
export async function restoreFile(filePath: string, cwd?: string) {
  const r = await executeCommand({ command: `git checkout HEAD -- ${filePath}`, working_dir: cwd });
  return { success: !r.isError };
}
