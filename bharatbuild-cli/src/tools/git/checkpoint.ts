import { gitAdd, gitCommit } from "./index.js";
export async function createCheckpoint(message: string, cwd?: string): Promise<{ hash: string | null; error?: string }> {
  const add = await gitAdd({ paths: ["."], working_dir: cwd });
  if (add.isError) return { hash: null, error: add.content };
  const commit = await gitCommit({ message: `[checkpoint] ${message}`, working_dir: cwd });
  if (commit.isError) return { hash: null, error: commit.content };
  return { hash: commit.content.match(/\[([a-f0-9]+)\]/)?.[1] ?? null };
}
