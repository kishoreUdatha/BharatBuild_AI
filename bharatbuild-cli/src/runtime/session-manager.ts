// BharatBuild CLI — Session Manager
// Persists conversation state to disk for resume

import fs from "fs";
import path from "path";
import os from "os";
import { ContextManager } from "./context-manager.js";

export interface SessionMeta {
  id:          string;
  title:       string;
  model:       string;
  createdAt:   number;
  updatedAt:   number;
  messageCount: number;
  projectId?:  string;
  workingDir:  string;
}

export interface Session extends SessionMeta {
  context: ReturnType<ContextManager["toJSON"]>;
}

const SESSIONS_DIR = path.join(os.homedir(), ".bharatbuild", "sessions");

function ensureDir(): void {
  if (!fs.existsSync(SESSIONS_DIR)) {
    fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  }
}

function sessionPath(id: string): string {
  return path.join(SESSIONS_DIR, `${id}.json`);
}

export class SessionManager {
  save(id: string, meta: Omit<SessionMeta, "id">, context: ContextManager): void {
    ensureDir();
    const session: Session = {
      id,
      ...meta,
      updatedAt: Date.now(),
      context:   context.toJSON() as any,
    };
    fs.writeFileSync(sessionPath(id), JSON.stringify(session, null, 2));
  }

  load(id: string): { meta: SessionMeta; context: ContextManager } | null {
    const p = sessionPath(id);
    if (!fs.existsSync(p)) return null;
    try {
      const session: Session = JSON.parse(fs.readFileSync(p, "utf8"));
      const { context: ctxData, ...meta } = session;
      return { meta, context: ContextManager.fromJSON(ctxData) };
    } catch {
      return null;
    }
  }

  list(): SessionMeta[] {
    ensureDir();
    return fs.readdirSync(SESSIONS_DIR)
      .filter(f => f.endsWith(".json"))
      .map(f => {
        try {
          const data = JSON.parse(fs.readFileSync(path.join(SESSIONS_DIR, f), "utf8"));
          const { context: _, ...meta } = data;
          return meta as SessionMeta;
        } catch {
          return null;
        }
      })
      .filter(Boolean) as SessionMeta[];
  }

  delete(id: string): boolean {
    const p = sessionPath(id);
    if (!fs.existsSync(p)) return false;
    fs.unlinkSync(p);
    return true;
  }

  generateId(): string {
    return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
}

export const sessionManager = new SessionManager();
