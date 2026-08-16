import fs from "fs";
import path from "path";
import os from "os";

export interface CloudSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Array<{ role: string; content: string }>;
  directory: string;
}

function getSessionsDir(): string {
  const home = process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild");
  return path.join(home, "sessions");
}

export function saveCloudSession(session: CloudSession): void {
  const dir = getSessionsDir();
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${session.id}.json`), JSON.stringify(session, null, 2));
}

export function loadCloudSession(id: string): CloudSession | null {
  try {
    const f = path.join(getSessionsDir(), `${id}.json`);
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as CloudSession;
  } catch {}
  return null;
}

export function listCloudSessions(directory?: string): CloudSession[] {
  const dir = getSessionsDir();
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => { try { return JSON.parse(fs.readFileSync(path.join(dir, f), "utf8")) as CloudSession; } catch { return null; } })
    .filter(Boolean)
    .filter((s) => !directory || (s as CloudSession).directory === directory)
    .sort((a, b) => new Date((b as CloudSession).updatedAt).getTime() - new Date((a as CloudSession).updatedAt).getTime()) as CloudSession[];
}

export function deleteCloudSession(id: string): boolean {
  try { fs.unlinkSync(path.join(getSessionsDir(), `${id}.json`)); return true; } catch { return false; }
}
