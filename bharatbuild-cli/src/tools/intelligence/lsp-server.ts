import { executeCommand } from "../shell/index.js";
import { EventEmitter } from "events";

export interface LSPMessage {
  jsonrpc: "2.0";
  id?: number;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: { code: number; message: string };
}

export interface LSPPosition { line: number; character: number; }
export interface LSPRange { start: LSPPosition; end: LSPPosition; }
export interface LSPLocation { uri: string; range: LSPRange; }
export interface LSPDiagnostic { range: LSPRange; severity: 1 | 2 | 3 | 4; message: string; source?: string; }
export interface LSPHover { contents: string | { kind: string; value: string }; range?: LSPRange; }

export class LSPServer extends EventEmitter {
  private msgId = 1;
  private pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>();
  private initialized = false;

  async checkInstalled(serverCmd: string): Promise<boolean> {
    const r = await executeCommand({ command: `${serverCmd} --version` });
    return !r.isError;
  }

  private nextId() { return this.msgId++; }

  buildInitialize(rootUri: string): LSPMessage {
    return {
      jsonrpc: "2.0", id: this.nextId(), method: "initialize",
      params: {
        processId: process.pid,
        rootUri,
        capabilities: {
          textDocument: {
            hover: { contentFormat: ["markdown", "plaintext"] },
            definition: { linkSupport: false },
            references: {},
            publishDiagnostics: { relatedInformation: true },
          },
          workspace: { workspaceFolders: true },
        },
      },
    };
  }

  buildHoverRequest(uri: string, line: number, character: number): LSPMessage {
    return { jsonrpc: "2.0", id: this.nextId(), method: "textDocument/hover", params: { textDocument: { uri }, position: { line, character } } };
  }

  buildDefinitionRequest(uri: string, line: number, character: number): LSPMessage {
    return { jsonrpc: "2.0", id: this.nextId(), method: "textDocument/definition", params: { textDocument: { uri }, position: { line, character } } };
  }

  buildReferencesRequest(uri: string, line: number, character: number): LSPMessage {
    return { jsonrpc: "2.0", id: this.nextId(), method: "textDocument/references", params: { textDocument: { uri }, position: { line, character }, context: { includeDeclaration: true } } };
  }

  formatMessage(msg: LSPMessage): Buffer {
    const body = JSON.stringify(msg);
    return Buffer.from(`Content-Length: ${Buffer.byteLength(body)}\r\n\r\n${body}`);
  }

  parseMessage(data: string): LSPMessage | null {
    try {
      const bodyStart = data.indexOf("\r\n\r\n");
      if (bodyStart === -1) return null;
      return JSON.parse(data.slice(bodyStart + 4)) as LSPMessage;
    } catch { return null; }
  }
}

export function getLanguageServer(language: string): string | null {
  const servers: Record<string, string> = {
    typescript: "typescript-language-server --stdio",
    javascript: "typescript-language-server --stdio",
    python: "pyright-langserver --stdio",
    go: "gopls",
    rust: "rust-analyzer",
    java: "jdtls",
    ruby: "solargraph stdio",
    php: "intelephense --stdio",
    "c++": "clangd",
    c: "clangd",
  };
  return servers[language] ?? null;
}
