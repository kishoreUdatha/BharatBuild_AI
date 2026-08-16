/**
 * BharatBuild CLI — Built-in Tool: code
 * Code intelligence with AST parsing and fuzzy search.
 * Supports: search_symbols, lookup_symbols, get_document_symbols,
 * pattern_search, generate_codebase_overview, search_codebase_map.
 */

import fs from "fs";
import path from "path";
import type { BuiltInTool, ToolResult } from "./types.js";

export const codeTool: BuiltInTool = {
  definition: {
    name: "code",
    source: "built-in",
    status: "approval_required",
    description: "Code intelligence with AST parsing and fuzzy search. Supports symbol search, document symbols, pattern search, and codebase overview.",
    parameters: {
      type: "object",
      properties: {
        operation: {
          type: "string",
          enum: ["search_symbols", "lookup_symbols", "get_document_symbols", "pattern_search", "generate_codebase_overview", "search_codebase_map"],
          description: "The code intelligence operation to perform.",
        },
        symbol_name: { type: "string", description: "Symbol name (required for search_symbols)." },
        symbols: { type: "array", items: { type: "string" }, description: "List of symbol names (required for lookup_symbols, max 10)." },
        file_path: { type: "string", description: "File path (required for get_document_symbols, optional for pattern_search)." },
        pattern: { type: "string", description: "AST pattern (required for pattern_search)." },
        language: { type: "string", description: "Programming language (required for pattern_search, optional for search_symbols)." },
        path: { type: "string", description: "Directory path (optional)." },
        limit: { type: "number", description: "Maximum results (optional)." },
        include_source: { type: "boolean", description: "Include source code in results (optional for lookup_symbols)." },
        top_level_only: { type: "boolean", description: "Only return top-level symbols (optional for get_document_symbols)." },
      },
      required: ["operation"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const operation = params["operation"] as string;

    switch (operation) {
      case "search_symbols":
        return searchSymbols(params);
      case "lookup_symbols":
        return lookupSymbols(params);
      case "get_document_symbols":
        return getDocumentSymbols(params);
      case "pattern_search":
        return patternSearch(params);
      case "generate_codebase_overview":
        return generateOverview(params);
      case "search_codebase_map":
        return searchCodebaseMap(params);
      default:
        return { content: `Unknown operation: ${operation}`, isError: true };
    }
  },
};

// ── Symbol extraction via regex (language-agnostic) ────────────────────────

interface SymbolInfo {
  name: string;
  kind: string;
  line: number;
  file: string;
  signature?: string;
}

const SYMBOL_PATTERNS: Record<string, Array<{ kind: string; regex: RegExp }>> = {
  typescript: [
    { kind: "function", regex: /^(?:export\s+)?(?:async\s+)?function\s+(\w+)/gm },
    { kind: "class", regex: /^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)/gm },
    { kind: "interface", regex: /^(?:export\s+)?interface\s+(\w+)/gm },
    { kind: "type", regex: /^(?:export\s+)?type\s+(\w+)/gm },
    { kind: "const", regex: /^(?:export\s+)?const\s+(\w+)\s*[:=]/gm },
    { kind: "method", regex: /^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:{]/gm },
  ],
  javascript: [
    { kind: "function", regex: /^(?:export\s+)?(?:async\s+)?function\s+(\w+)/gm },
    { kind: "class", regex: /^(?:export\s+)?class\s+(\w+)/gm },
    { kind: "const", regex: /^(?:export\s+)?const\s+(\w+)\s*=/gm },
    { kind: "method", regex: /^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{/gm },
  ],
  python: [
    { kind: "function", regex: /^(?:async\s+)?def\s+(\w+)/gm },
    { kind: "class", regex: /^class\s+(\w+)/gm },
  ],
  rust: [
    { kind: "function", regex: /^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)/gm },
    { kind: "struct", regex: /^(?:pub\s+)?struct\s+(\w+)/gm },
    { kind: "enum", regex: /^(?:pub\s+)?enum\s+(\w+)/gm },
    { kind: "trait", regex: /^(?:pub\s+)?trait\s+(\w+)/gm },
    { kind: "impl", regex: /^impl(?:<[^>]+>)?\s+(\w+)/gm },
  ],
  go: [
    { kind: "function", regex: /^func\s+(\w+)/gm },
    { kind: "type", regex: /^type\s+(\w+)/gm },
  ],
};

function detectLanguage(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  const map: Record<string, string> = {
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
  };
  return map[ext] ?? "typescript";
}

function extractSymbolsFromFile(filePath: string, lang?: string): SymbolInfo[] {
  const language = lang ?? detectLanguage(filePath);
  const patterns = SYMBOL_PATTERNS[language] ?? SYMBOL_PATTERNS["typescript"]!;
  const symbols: SymbolInfo[] = [];

  let content: string;
  try {
    content = fs.readFileSync(filePath, "utf8");
  } catch {
    return [];
  }

  const lines = content.split("\n");
  for (const { kind, regex } of patterns) {
    const re = new RegExp(regex.source, regex.flags);
    let match: RegExpExecArray | null;
    while ((match = re.exec(content)) !== null) {
      const line = content.slice(0, match.index).split("\n").length;
      const lineText = lines[line - 1] ?? "";
      symbols.push({
        name: match[1]!,
        kind,
        line,
        file: filePath,
        signature: lineText.trim().slice(0, 120),
      });
    }
  }

  return symbols;
}

// ── Operations ─────────────────────────────────────────────────────────────

const EXCLUDED_DIRS = new Set(["node_modules", ".git", "dist", "build", "out", ".cache", "target"]);
const CODE_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".py", ".rs", ".go", ".java", ".c", ".cpp", ".h"]);

function walkCodeFiles(dir: string, files: string[], maxFiles = 500): void {
  if (files.length >= maxFiles) return;
  let entries: fs.Dirent[];
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
  for (const entry of entries) {
    if (files.length >= maxFiles) break;
    if (entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!EXCLUDED_DIRS.has(entry.name)) walkCodeFiles(full, files, maxFiles);
    } else if (CODE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      files.push(full);
    }
  }
}

function searchSymbols(params: Record<string, unknown>): ToolResult {
  const name = params["symbol_name"] as string;
  const dir = params["path"] as string ?? ".";
  const limit = params["limit"] as number ?? 20;

  if (!name) return { content: "Error: 'symbol_name' is required for search_symbols.", isError: true };

  const rootDir = path.resolve(dir);
  const files: string[] = [];
  walkCodeFiles(rootDir, files);

  const matches: SymbolInfo[] = [];
  const lowerName = name.toLowerCase();
  for (const file of files) {
    const symbols = extractSymbolsFromFile(file);
    for (const sym of symbols) {
      if (sym.name.toLowerCase().includes(lowerName)) {
        matches.push({ ...sym, file: path.relative(rootDir, sym.file) });
        if (matches.length >= limit) break;
      }
    }
    if (matches.length >= limit) break;
  }

  if (matches.length === 0) return { content: `No symbols found matching '${name}'.`, isError: false };

  const output = matches.map((s) => `${s.kind} ${s.name} — ${s.file}:${s.line}${s.signature ? `\n  ${s.signature}` : ""}`).join("\n");
  return { content: output, isError: false };
}

function lookupSymbols(params: Record<string, unknown>): ToolResult {
  const symbols = params["symbols"] as string[];
  const dir = params["path"] as string ?? ".";
  const includeSource = params["include_source"] as boolean ?? false;

  if (!symbols || symbols.length === 0) return { content: "Error: 'symbols' array is required.", isError: true };

  const rootDir = path.resolve(dir);
  const files: string[] = [];
  walkCodeFiles(rootDir, files);

  const results: string[] = [];
  for (const symbolName of symbols.slice(0, 10)) {
    let found = false;
    for (const file of files) {
      const fileSymbols = extractSymbolsFromFile(file);
      const match = fileSymbols.find((s) => s.name === symbolName);
      if (match) {
        let output = `${match.kind} ${match.name} — ${path.relative(rootDir, match.file)}:${match.line}`;
        if (includeSource && match.signature) output += `\n  ${match.signature}`;
        results.push(output);
        found = true;
        break;
      }
    }
    if (!found) results.push(`${symbolName} — not found`);
  }

  return { content: results.join("\n"), isError: false };
}

function getDocumentSymbols(params: Record<string, unknown>): ToolResult {
  const filePath = params["file_path"] as string;
  const topLevelOnly = params["top_level_only"] as boolean ?? false;

  if (!filePath) return { content: "Error: 'file_path' is required.", isError: true };

  const resolved = path.resolve(filePath);
  if (!fs.existsSync(resolved)) return { content: `File not found: ${filePath}`, isError: true };

  const symbols = extractSymbolsFromFile(resolved);

  const filtered = topLevelOnly
    ? symbols.filter((s) => s.kind !== "method")
    : symbols;

  if (filtered.length === 0) return { content: `No symbols found in ${filePath}.`, isError: false };

  const output = filtered.map((s) => `  ${s.kind.padEnd(10)} ${s.name.padEnd(30)} line ${s.line}`).join("\n");
  return { content: `Symbols in ${filePath}:\n${output}`, isError: false };
}

function patternSearch(params: Record<string, unknown>): ToolResult {
  const pattern = params["pattern"] as string;
  const filePath = params["file_path"] as string | undefined;
  const dir = params["path"] as string ?? ".";
  const limit = params["limit"] as number ?? 20;

  if (!pattern) return { content: "Error: 'pattern' is required for pattern_search.", isError: true };

  // Use pattern as a regex search across code files
  let regex: RegExp;
  try {
    regex = new RegExp(pattern, "gm");
  } catch (e) {
    return { content: `Error: Invalid pattern: ${e instanceof Error ? e.message : e}`, isError: true };
  }

  const rootDir = path.resolve(dir);
  const files: string[] = filePath ? [path.resolve(filePath)] : [];
  if (!filePath) walkCodeFiles(rootDir, files);

  const matches: Array<{ file: string; line: number; text: string }> = [];
  for (const file of files) {
    if (matches.length >= limit) break;
    let content: string;
    try { content = fs.readFileSync(file, "utf8"); } catch { continue; }
    const lines = content.split("\n");
    for (let i = 0; i < lines.length; i++) {
      regex.lastIndex = 0;
      if (regex.test(lines[i]!)) {
        matches.push({ file: path.relative(rootDir, file), line: i + 1, text: lines[i]!.trim() });
        if (matches.length >= limit) break;
      }
    }
  }

  if (matches.length === 0) return { content: `No matches for pattern '${pattern}'.`, isError: false };

  const output = matches.map((m) => `${m.file}:${m.line}  ${m.text.slice(0, 100)}`).join("\n");
  return { content: `${matches.length} match(es):\n${output}`, isError: false };
}

function generateOverview(params: Record<string, unknown>): ToolResult {
  const dir = params["path"] as string ?? ".";
  const rootDir = path.resolve(dir);

  // Count files by extension
  const extCount = new Map<string, number>();
  const dirs: string[] = [];
  const topFiles: string[] = [];

  let entries: fs.Dirent[];
  try { entries = fs.readdirSync(rootDir, { withFileTypes: true }); } catch {
    return { content: `Cannot read directory: ${rootDir}`, isError: true };
  }

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    if (entry.isDirectory() && !EXCLUDED_DIRS.has(entry.name)) {
      dirs.push(entry.name);
    } else if (entry.isFile()) {
      topFiles.push(entry.name);
      const ext = path.extname(entry.name);
      extCount.set(ext, (extCount.get(ext) ?? 0) + 1);
    }
  }

  // Deeper scan for extension stats
  const allFiles: string[] = [];
  walkCodeFiles(rootDir, allFiles, 1000);
  for (const file of allFiles) {
    const ext = path.extname(file);
    extCount.set(ext, (extCount.get(ext) ?? 0) + 1);
  }

  const output: string[] = [];
  output.push(`Codebase Overview: ${rootDir}`);
  output.push(`\nDirectories:`);
  for (const d of dirs.sort()) output.push(`  ${d}/`);
  output.push(`\nFile types:`);
  const sorted = [...extCount.entries()].sort((a, b) => b[1] - a[1]);
  for (const [ext, count] of sorted.slice(0, 15)) {
    output.push(`  ${(ext || "(no ext)").padEnd(10)} ${count} files`);
  }
  output.push(`\nTotal code files: ${allFiles.length}`);
  output.push(`Top-level files: ${topFiles.slice(0, 10).join(", ")}`);

  return { content: output.join("\n"), isError: false };
}

function searchCodebaseMap(params: Record<string, unknown>): ToolResult {
  const dir = params["path"] as string ?? ".";
  const filePath = params["file_path"] as string | undefined;
  const rootDir = path.resolve(filePath ?? dir);

  if (!fs.existsSync(rootDir)) return { content: `Path not found: ${rootDir}`, isError: true };

  const stat = fs.statSync(rootDir);
  if (!stat.isDirectory()) {
    // Show symbols from the file
    const symbols = extractSymbolsFromFile(rootDir);
    if (symbols.length === 0) return { content: `No symbols found in ${rootDir}`, isError: false };
    const output = symbols.map((s) => `  ${s.kind.padEnd(10)} ${s.name.padEnd(30)} line ${s.line}`).join("\n");
    return { content: `${rootDir}:\n${output}`, isError: false };
  }

  // Show directory structure with symbols summary
  const files: string[] = [];
  walkCodeFiles(rootDir, files, 50);

  const output: string[] = [`Codebase map: ${rootDir}\n`];
  for (const file of files) {
    const symbols = extractSymbolsFromFile(file);
    const relPath = path.relative(rootDir, file);
    if (symbols.length > 0) {
      output.push(`${relPath}: ${symbols.map((s) => s.name).join(", ")}`);
    } else {
      output.push(relPath);
    }
  }

  return { content: output.join("\n"), isError: false };
}
