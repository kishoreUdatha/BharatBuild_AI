/**
 * BharatBuild CLI — Built-in Tool: web_search
 * WebSearch looks up information outside the model's training data.
 * Uses DuckDuckGo API (no key required) with Brave Search API fallback.
 */

import https from "https";
import http from "http";
import { URL } from "url";
import type { BuiltInTool, ToolResult } from "./types.js";

export const webSearchTool: BuiltInTool = {
  definition: {
    name: "web_search",
    source: "built-in",
    status: "approval_required",
    description: "WebSearch looks up information that is outside the model's training data or cannot be reliably inferred from the current codebase/context.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query (max 200 chars) — use concise keywords, not full sentences.",
        },
      },
      required: ["query"],
    },
  },

  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const query = params["query"] as string;
    if (!query?.trim()) return { content: "Error: 'query' is required.", isError: true };

    const limit = 5;

    // Strategy 1: DuckDuckGo Instant Answer API
    try {
      const ddgUrl = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_redirect=1&no_html=1&skip_disambig=1`;
      const ddgJson = await fetchUrl(ddgUrl, 8000);
      const data = JSON.parse(ddgJson) as Record<string, unknown>;
      const results: Array<{ title: string; url: string; snippet: string }> = [];

      if (data["AbstractText"] && data["AbstractURL"]) {
        results.push({
          title: (data["AbstractSource"] as string) ?? "Answer",
          url: data["AbstractURL"] as string,
          snippet: (data["AbstractText"] as string).slice(0, 300),
        });
      }

      const relatedTopics = data["RelatedTopics"] as Array<Record<string, unknown>> ?? [];
      for (const topic of relatedTopics) {
        if (results.length >= limit) break;
        if (topic["FirstURL"] && topic["Text"]) {
          results.push({
            title: (topic["Text"] as string).slice(0, 80),
            url: topic["FirstURL"] as string,
            snippet: (topic["Text"] as string).slice(0, 200),
          });
        }
        // Nested topics
        const subTopics = topic["Topics"] as Array<Record<string, unknown>> | undefined;
        if (subTopics) {
          for (const sub of subTopics) {
            if (results.length >= limit) break;
            if (sub["FirstURL"] && sub["Text"]) {
              results.push({
                title: (sub["Text"] as string).slice(0, 80),
                url: sub["FirstURL"] as string,
                snippet: (sub["Text"] as string).slice(0, 200),
              });
            }
          }
        }
      }

      if (results.length > 0) {
        return { content: formatResults(query, results), isError: false };
      }
    } catch { /* fall through */ }

    // Strategy 2: DuckDuckGo HTML scrape
    try {
      const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
      const html = await fetchUrl(searchUrl, 12000);
      const results = parseHtmlResults(html, limit);
      if (results.length > 0) {
        return { content: formatResults(query, results), isError: false };
      }
    } catch { /* fall through */ }

    // Strategy 3: Brave Search API (if key set)
    const braveKey = process.env["BRAVE_SEARCH_API_KEY"];
    if (braveKey) {
      try {
        const braveUrl = `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=${limit}`;
        const raw = await fetchUrl(braveUrl + `&key=${braveKey}`, 10000);
        const data = JSON.parse(raw) as { web?: { results?: Array<{ title?: string; url?: string; description?: string }> } };
        const items = data.web?.results ?? [];
        if (items.length > 0) {
          const results = items.map((r) => ({ title: r.title ?? "", url: r.url ?? "", snippet: r.description ?? "" }));
          return { content: formatResults(query, results), isError: false };
        }
      } catch { /* fall through */ }
    }

    return {
      content: `No search results found for: "${query}"\n\nTip: Try using web_fetch with a direct URL, or set BRAVE_SEARCH_API_KEY for reliable results.`,
      isError: false,
    };
  },
};

function formatResults(query: string, results: Array<{ title: string; url: string; snippet: string }>): string {
  const formatted = results
    .map((r, i) => `${i + 1}. **${r.title}**\n   URL: ${r.url}\n   ${r.snippet}`)
    .join("\n\n");
  return `Search results for: "${query}"\n\n${formatted}`;
}

function parseHtmlResults(html: string, limit: number): Array<{ title: string; url: string; snippet: string }> {
  const results: Array<{ title: string; url: string; snippet: string }> = [];
  const resultPattern = /<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
  const snippetPattern = /<a[^>]+class="result__snippet"[^>]*>([\s\S]*?)<\/a>/gi;

  const urls: string[] = [];
  const titles: string[] = [];
  const snippets: string[] = [];

  let match: RegExpExecArray | null;
  while ((match = resultPattern.exec(html)) !== null && urls.length < limit) {
    const rawUrl = match[1] ?? "";
    const title = stripHtml(match[2] ?? "").trim();
    const uddg = rawUrl.match(/uddg=([^&]+)/);
    const actualUrl = uddg ? decodeURIComponent(uddg[1] ?? rawUrl) : rawUrl;
    if (actualUrl.startsWith("http")) { urls.push(actualUrl); titles.push(title); }
  }
  while ((match = snippetPattern.exec(html)) !== null && snippets.length < limit) {
    snippets.push(stripHtml(match[1] ?? "").trim());
  }
  for (let i = 0; i < Math.min(urls.length, limit); i++) {
    results.push({ title: titles[i] ?? "", url: urls[i] ?? "", snippet: snippets[i] ?? "" });
  }
  return results;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
}

function fetchUrl(url: string, timeoutMs = 10000): Promise<string> {
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
