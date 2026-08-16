import { EventStream } from "../runtime/event-stream.js";
export class WebSocketClient {
  private ws: WebSocket | null = null;
  readonly events = new EventStream();
  connect(url: string, token?: string) {
    const wsUrl = token ? `${url}?token=${token}` : url;
    this.ws = new (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket(wsUrl);
    this.ws.onmessage = (e: MessageEvent) => {
      try {
        const d = JSON.parse(typeof e.data === "string" ? e.data : "") as Record<string, unknown>;
        if (d["type"]) void this.events.emit(d as unknown as Parameters<typeof this.events.emit>[0]);
      } catch {}
    };
  }
  disconnect() { this.ws?.close(); this.ws = null; }
  send(d: unknown) { this.ws?.send(JSON.stringify(d)); }
}
