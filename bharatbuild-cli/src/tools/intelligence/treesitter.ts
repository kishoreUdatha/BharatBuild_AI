import fs from "fs";
import path from "path";
// tree-sitter and its grammars are optional native deps resolved by name at
// runtime. This package is ESM, where bare require() is undefined, so use the
// ESM-native equivalent rather than a static import that would hard-fail when
// the optional dependency is absent.
import { createRequire } from "module";

export interface ASTNode {
  type: string;
  text: string;
  startLine: number;
  endLine: number;
  startCol: number;
  endCol: number;
  children?: ASTNode[];
}

export interface ParseResult {
  nodes: ASTNode[];
  language: string;
  parseMethod: "treesitter" | "regex-fallback";
}

/**
 * Try real tree-sitter first, fall back to regex-based parsing.
 * Install real tree-sitter: npm install tree-sitter tree-sitter-typescript tree-sitter-python
 */
export function parseFile(filePath: string): ParseResult {
  const ext = path.extname(filePath).slice(1);
  const language = extToLanguage(ext);
  const content = fs.readFileSync(filePath, "utf8");

  // Try real tree-sitter
  try {
    const require = createRequire(import.meta.url);
    const Parser = require("tree-sitter") as { new(): { setLanguage(l: unknown): void; parse(c: string): { rootNode: unknown } } };
    const langMap: Record<string, string> = { typescript: "tree-sitter-typescript/typescript", javascript: "tree-sitter-javascript", python: "tree-sitter-python", rust: "tree-sitter-rust", go: "tree-sitter-go" };
    const langPkg = langMap[language];
    if (langPkg) {
      const lang = require(langPkg) as unknown;
      const parser = new Parser();
      parser.setLanguage(lang);
      const tree = parser.parse(content);
      return { nodes: extractNodes(tree.rootNode as Record<string, unknown>), language, parseMethod: "treesitter" };
    }
  } catch {
    // tree-sitter not installed — fall back to regex
  }

  // Regex fallback
  return { nodes: regexParse(content, language), language, parseMethod: "regex-fallback" };
}

function extractNodes(node: Record<string, unknown>, depth = 0): ASTNode[] {
  if (depth > 5) return [];
  const result: ASTNode[] = [];
  const important = ["function_declaration", "class_declaration", "method_definition", "interface_declaration", "type_alias_declaration", "export_statement", "import_statement"];
  if (important.includes(String(node["type"] ?? ""))) {
    const sp = node["startPosition"] as Record<string, number> | undefined;
    const ep = node["endPosition"] as Record<string, number> | undefined;
    result.push({
      type: String(node["type"] ?? ""),
      text: String(node["text"] ?? "").slice(0, 100),
      startLine: sp?.["row"] ?? 0,
      endLine: ep?.["row"] ?? 0,
      startCol: sp?.["column"] ?? 0,
      endCol: ep?.["column"] ?? 0,
    });
  }
  const children = node["children"] as unknown[] | undefined;
  if (children) {
    for (const child of children) {
      result.push(...extractNodes(child as Record<string, unknown>, depth + 1));
    }
  }
  return result;
}

function regexParse(content: string, language: string): ASTNode[] {
  const nodes: ASTNode[] = [];
  const lines = content.split("\n");
  const patterns: Array<{ re: RegExp; type: string }> = language === "python"
    ? [{ re: /^(async\s+)?def\s+(\w+)/, type: "function" }, { re: /^class\s+(\w+)/, type: "class" }]
    : [
        { re: /^export\s+(async\s+)?function\s+(\w+)/, type: "function_declaration" },
        { re: /^export\s+class\s+(\w+)/, type: "class_declaration" },
        { re: /^export\s+interface\s+(\w+)/, type: "interface_declaration" },
        { re: /^export\s+type\s+(\w+)/, type: "type_alias_declaration" },
        { re: /^(async\s+)?function\s+(\w+)/, type: "function_declaration" },
        { re: /^class\s+(\w+)/, type: "class_declaration" },
      ];
  lines.forEach((line, i) => {
    for (const { re, type } of patterns) {
      if (re.test(line)) {
        nodes.push({ type, text: line.trim().slice(0, 80), startLine: i, endLine: i, startCol: 0, endCol: line.length });
        break;
      }
    }
  });
  return nodes;
}

function extToLanguage(ext: string): string {
  const map: Record<string, string> = { ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript", py: "python", rs: "rust", go: "go", java: "java", rb: "ruby", php: "php" };
  return map[ext] ?? "unknown";
}
