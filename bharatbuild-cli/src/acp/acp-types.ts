export interface ACPMessage {
  jsonrpc: "2.0";
  id?: string | number;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}
export interface ACPTask { id: string; title: string; description: string; agent?: string; status: "pending"|"running"|"complete"|"failed"; result?: string; }
export interface ACPCapabilities { streaming: boolean; tools: string[]; agents: string[]; models: string[]; }
export interface ACPSession { id: string; createdAt: string; capabilities: ACPCapabilities; }
