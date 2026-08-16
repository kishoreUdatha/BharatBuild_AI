import readline from "readline";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { getTheme } from "./theme.js";

export interface SessionEntry {
  id: string;
  title: string;
  timestamp: string;
  messageCount: number;
}

export function loadSessions(dir?: string): SessionEntry[] {
  const sessionsDir = path.join(dir ?? process.cwd(), ".bharatbuild", "sessions");
  if (!fs.existsSync(sessionsDir)) return [];
  try {
    return fs.readdirSync(sessionsDir)
      .filter((f) => f.endsWith(".json"))
      .map((f) => {
        try {
          const data = JSON.parse(fs.readFileSync(path.join(sessionsDir, f), "utf8")) as Partial<SessionEntry>;
          return {
            id: data.id ?? f.replace(".json", ""),
            title: data.title ?? "Untitled session",
            timestamp: data.timestamp ?? new Date().toISOString(),
            messageCount: data.messageCount ?? 0,
          };
        } catch { return null; }
      })
      .filter(Boolean) as SessionEntry[];
  } catch { return []; }
}

export function saveSession(session: SessionEntry, dir?: string): void {
  const sessionsDir = path.join(dir ?? process.cwd(), ".bharatbuild", "sessions");
  fs.mkdirSync(sessionsDir, { recursive: true });
  fs.writeFileSync(path.join(sessionsDir, `${session.id}.json`), JSON.stringify(session, null, 2));
}

export async function pickSession(sessions: SessionEntry[]): Promise<SessionEntry | null> {
  const t = getTheme();
  if (sessions.length === 0) {
    console.log(t.dim("\n  No previous sessions found.\n"));
    return null;
  }
  console.log(t.heading("\n  💬 Previous Sessions (fuzzy search):\n"));
  sessions.slice(0, 10).forEach((s, i) => {
    const ts = new Date(s.timestamp).toLocaleString();
    console.log(`  ${t.info((i + 1).toString().padStart(2))}. ${t.heading(s.title.padEnd(40))} ${t.dim(ts)}`);
  });
  console.log();
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(t.prompt("  Enter number (or press Enter to start new): "), (answer) => {
      rl.close();
      const n = parseInt(answer.trim());
      if (n > 0 && n <= sessions.length) resolve(sessions[n - 1] ?? null);
      else resolve(null);
    });
  });
}
