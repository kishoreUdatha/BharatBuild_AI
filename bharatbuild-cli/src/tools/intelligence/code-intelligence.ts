import path from "path";
import { parseFile, type ASTNode } from "./treesitter.js";
import { findReferences } from "./references.js";
import { extractSymbols } from "./symbols.js";
import { getTypeScriptDiagnostics } from "./diagnostics.js";
import { LSPServer, getLanguageServer } from "./lsp-server.js";

export interface CodeIntelligenceResult {
  symbols: Array<{ name: string; kind: string; file: string; line: number }>;
  ast?: ASTNode[];
  parseMethod?: string;
  lspAvailable: boolean;
  lspServer?: string;
}

export async function analyzeFile(filePath: string): Promise<CodeIntelligenceResult> {
  const ext = path.extname(filePath).slice(1);
  const language = extToLang(ext);

  // Get symbols via regex
  const symbols = extractSymbols(filePath);

  // Try AST parsing
  let ast: ASTNode[] | undefined;
  let parseMethod: string | undefined;
  try {
    const result = parseFile(filePath);
    ast = result.nodes;
    parseMethod = result.parseMethod;
  } catch {}

  // Check LSP availability
  const lspServer = getLanguageServer(language);
  const lspAvailable = lspServer !== null;

  return { symbols, ast, parseMethod, lspAvailable, lspServer: lspServer ?? undefined };
}

export async function getProjectDiagnostics(cwd?: string) {
  return getTypeScriptDiagnostics(cwd);
}

export function searchReferences(symbolName: string, rootDir: string) {
  return findReferences(symbolName, rootDir);
}

function extToLang(ext: string): string {
  const map: Record<string, string> = { ts: "typescript", tsx: "typescript", js: "javascript", py: "python", rs: "rust", go: "go" };
  return map[ext] ?? "unknown";
}
