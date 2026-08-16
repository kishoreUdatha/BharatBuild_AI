/**
 * BharatBuild CLI — Built-in Tool: web_fetch
 * Fetch and extract content from a specific URL.
 * Supports selective, truncated, and full modes.
 */

import https from "https";
import http from "http";
import { URL } from "url";
import type { BuiltInTool, ToolResult } from "./types.js";

export const webFetchTool: BuiltInTool = {
  definition: {
    name: "web_fetch",
    source: "built-in",
    status: "approval_required",
    description: "Fetch and extract content from a specific URL. Supports selective (smart extraction), truncated (first 8000 chars), and full modes.",
    parameters: {
      type: "object",
      properties: {
        url: { type: "string", description: "URL to fetch content from." },
        mode: {
          type: "string",
          enum: ["selective", "truncated", "full"],
          description: "Extraction mode: 'selective' (default), 'truncated' for first 8000 chars, 'full' for complete content.",
        },
        search_terms: {
          type: "string",
          description: "Keywords to find in selective mode. Returns ~10 lines before and after matches.",
        },
      },
      required: ["url"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const url = params["url"] as string;
    const mode = (params["mode"] as string) ?? "selective";
    const searchTerms = params["search_terms"] as string | undefined;

    if (!url?.trim()) return { content: "Error: 'url' is required.", isError: true };

    try {
      new URL(url);
    } catch {
      return { content: `Error: Invalid URL: ${url}`, isError: true };
    }

    try {
      const raw = await fetchUrl(url);
      const isHtml = raw.trimStart().startsWith("<!") || raw.includes("<html");
      const text = isHtml ? stripHtml(raw) : raw;

      switch (mode) {
        case "full":
          return { content: `URL: ${url}\n\n${text}`, isError: false };

        case "truncated":
          return {
            content: `URL: ${url}\n\n${text.slice(0, 8000)}${text.length > 8000 ? "\n\n[truncated]" : ""}`,
            isError: false,
          };

        case "selective":
        default:
          if (!searchTerms) {
            // No search terms — return first 8000 chars
            return {
              content: `URL: ${url}\n\n${text.slice(0, 8000)}${text.length > 8000 ? "\n\n[truncated — use search_terms for focused extraction]" : ""}`,
              isError: false,
            };
          }
          const extracted = selectiveExtract(text, searchTerms);
          return { content: `URL: ${url}\n\n${extracted}`, isError: false };
      }
    } catch (err) {
      return {
        content: `Failed to fetch ${url}: ${err instanceof Error ? err.message : String(err)}`,
        isError: true,
      };
    }
  },
};

function selectiveExtract(text: string, searchTerms: string): string {
  const lines = text.split("\n");
  const terms = searchTerms.toLowerCase().split(/\s+/);
  const contextLines = 10;
  const matchedSections: string[] = [];
  const matchedIndices = new Set<number>();

  for (let i = 0; i < lines.length; i++) {
    const lower = lines[i]!.toLowerCase();
    if (terms.some((t) => lower.includes(t))) {
      const start = Math.max(0, i - contextLines);
      const end = Math.min(lines.length, i + contextLines + 1);
      for (let j = start; j < end; j++) matchedIndices.add(j);
    }
  }

  if (matchedIndices.size === 0) {
    return text.slice(0, 4000) + "\n\n[No matches for search terms — showing beginning of content]";
  }

  const sorted = [...matchedIndices].sort((a, b) => a - b);
  let prevIdx = -2;
  for (const idx of sorted) {
    if (idx - prevIdx > 1 && matchedSections.length > 0) {
      matchedSections.push("\n...\n");
    }
    matchedSections.push(lines[idx]!);
    prevIdx = idx;
  }

  return matchedSections.join("\n");
}

function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s{3,}/g, "\n\n")
    .trim();
}

function fetchUrl(url: string, timeoutMs = 15000): Promise<string> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === "https:" ? https : http;
    const req = lib.get(url, { headers: { "User-Agent": "BharatBuild-CLI/1.0" } }, (res) => {
      if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        fetchUrl(res.headers.location, timeoutMs).then(resolve).catch(reject);
        return;
      }
      if (res.statusCode && res.statusCode >= 400) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }
      const chunks: Buffer[] = [];
      res.on("data", (chunk: Buffer) => chunks.push(chunk));
      res.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      res.on("error", reject);
    });
    req.setTimeout(timeoutMs, () => { req.destroy(); reject(new Error("Request timed out")); });
    req.on("error", reject);
  });
}
