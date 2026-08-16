import type { ACPMessage, ACPTask, ACPSession } from "./acp-types.js";

export class ACPClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  private msgId = 1;

  constructor(baseUrl: string) { this.baseUrl = baseUrl.replace(/\/$/, ""); }

  private async send(method: string, params?: unknown): Promise<unknown> {
    const msg: ACPMessage = { jsonrpc: "2.0", id: this.msgId++, method, ...(params ? { params } : {}) };
    const res = await fetch(this.baseUrl, { method: "POST", headers: { "Content-Type": "application/json", ...(this.sessionId ? { "X-Session-Id": this.sessionId } : {}) }, body: JSON.stringify(msg) });
    const data = await res.json() as ACPMessage;
    if (data.error) throw new Error(data.error.message);
    return data.result;
  }

  async initialize(): Promise<ACPSession> { const r = await this.send("initialize") as ACPSession; this.sessionId = r.id; return r; }
  async createTask(title: string, description: string, agent?: string): Promise<ACPTask> { return this.send("tasks/create", { title, description, agent }) as Promise<ACPTask>; }
  async getCapabilities() { return this.send("capabilities"); }
}
