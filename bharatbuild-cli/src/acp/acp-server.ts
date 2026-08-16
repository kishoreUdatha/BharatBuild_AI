import http from "http";
import { EventEmitter } from "events";
import type { ACPMessage, ACPTask, ACPCapabilities } from "./acp-types.js";
import { MODEL_TIERS } from "../config/constants.js";

export interface ACPServerOptions { port?: number; host?: string; onTask: (task: ACPTask) => Promise<string>; }

export class ACPServer extends EventEmitter {
  private server: http.Server;
  private opts: ACPServerOptions;

  constructor(opts: ACPServerOptions) {
    super();
    this.opts = opts;
    this.server = http.createServer((req, res) => { void this._handle(req, res); });
  }

  private async _handle(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
    let body = "";
    req.on("data", (c) => { body += c.toString(); });
    req.on("end", async () => {
      try {
        const msg = JSON.parse(body) as ACPMessage;
        const result = await this._dispatch(msg);
        res.writeHead(200);
        res.end(JSON.stringify({ jsonrpc: "2.0", id: msg.id, result }));
      } catch (err) {
        res.writeHead(400);
        res.end(JSON.stringify({ jsonrpc: "2.0", error: { code: -32700, message: err instanceof Error ? err.message : "Error" } }));
      }
    });
  }

  private async _dispatch(msg: ACPMessage): Promise<unknown> {
    switch (msg.method) {
      case "initialize": {
        return { sessionId: `session-${Date.now()}`, createdAt: new Date().toISOString(), capabilities: { streaming: true, tools: ["read","write","shell","glob","grep"], agents: ["default","planner","coder","tester","fixer","reviewer"], models: [MODEL_TIERS.sonnet,"gpt-4o","gemini-1.5-pro"] } as ACPCapabilities };
      }
      case "tasks/create": {
        const p = msg.params as Partial<ACPTask>;
        const task: ACPTask = { id: `task-${Date.now()}`, title: p.title ?? "Task", description: p.description ?? "", agent: p.agent ?? "default", status: "running" };
        try { task.result = await this.opts.onTask(task); task.status = "complete"; } catch (err) { task.status = "failed"; task.result = err instanceof Error ? err.message : String(err); }
        return task;
      }
      case "capabilities":
        return { streaming: true, tools: ["read","write","shell","glob","grep"], agents: ["default","planner","coder","tester","fixer","reviewer"], models: [MODEL_TIERS.sonnet,"gpt-4o"] };
      default:
        throw new Error(`Unknown method: ${String(msg.method)}`);
    }
  }

  listen(port?: number, host?: string): Promise<void> {
    const p = port ?? this.opts.port ?? 3141;
    const h = host ?? this.opts.host ?? "127.0.0.1";
    return new Promise((resolve) => { this.server.listen(p, h, () => { this.emit("listening", { port: p, host: h }); resolve(); }); });
  }

  close(): Promise<void> { return new Promise((resolve, reject) => { this.server.close((err) => { if (err) reject(err); else resolve(); }); }); }
}
