import { EventEmitter } from "events";
import type { CrewAgent, CrewSession } from "./crew-types.js";

export class CrewManager extends EventEmitter {
  private sessions = new Map<string, CrewSession>();

  createSession(title: string, agentRoles: Array<{ name: string; role: string; model?: string }>): CrewSession {
    const session: CrewSession = {
      id: `crew-${Date.now()}`, title,
      agents: agentRoles.map((r, i) => ({ id: `agent-${i}-${Date.now()}`, name: r.name, role: r.role, model: r.model, status: "idle" as const })),
      createdAt: new Date().toISOString(), status: "active",
    };
    this.sessions.set(session.id, session);
    this.emit("session:created", session);
    return session;
  }

  assignTask(sessionId: string, agentId: string, task: string, handler: (task: string) => Promise<string>): void {
    const session = this.sessions.get(sessionId);
    if (!session) return;
    const agent = session.agents.find((a) => a.id === agentId);
    if (!agent) return;
    agent.status = "running"; agent.task = task; agent.startedAt = new Date().toISOString();
    this.emit("agent:started", { session, agent });
    handler(task).then((result) => {
      agent.status = "complete"; agent.result = result; agent.completedAt = new Date().toISOString();
      this.emit("agent:complete", { session, agent });
      if (session.agents.every((a) => a.status === "complete")) { session.status = "complete"; this.emit("session:complete", session); }
    }).catch((err: Error) => {
      agent.status = "failed"; agent.result = err.message; agent.completedAt = new Date().toISOString();
      this.emit("agent:failed", { session, agent });
    });
  }

  getSession(id: string) { return this.sessions.get(id); }
  listSessions() { return Array.from(this.sessions.values()); }

  renderMonitor(sessionId: string): string {
    const session = this.sessions.get(sessionId);
    if (!session) return "  Session not found.";
    const icons: Record<string, string> = { idle: "○", running: "⠋", complete: "✓", failed: "✗" };
    return [`  📋 Crew: ${session.title}  [${session.status}]\n`,
      ...session.agents.map((a) => `  ${icons[a.status] ?? "○"} [${a.role}] ${a.name}${a.task ? "  " + a.task.slice(0, 40) : ""}`)
    ].join("\n");
  }
}

export const crewManager = new CrewManager();
