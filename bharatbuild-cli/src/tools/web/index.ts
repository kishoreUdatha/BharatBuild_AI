/**
 * BharatBuild CLI - Web Tools
 * web_fetch and web_search tools matching Kiro CLI's built-in tools.
 */

import https from "https";
import http from "http";
import { URL } from "url";

// ── Tool Definitions ───────────────────────────────────────────────────────

export const webFetchDefinition = {
  name: "web_fetch",
  description:
    "Fetch the content of a URL and return it as text. " +
    "Use this to read documentation, API references, GitHub files, or any web resource. " +
    "HTML is converted to readable plain text. Respects robots.txt is not checked — use responsibly.",
  input_schema: {
    type: "object",
    properties: {
      url: {
        type: "string",
        description: "The URL to fetch.",
      },
      max_length: {
        type: "number",
        description: "Maximum characters to return (default: 10000).",
      },
    },
    required: ["url"],
  },
} as const;

export const webSearchDefinition = {
  name: "web_search",
  description:
    "Search the web for information. Returns a list of relevant results with titles, " +
    "URLs, and snippets. Use this to find documentation, examples, package info, " +
    "error solutions, or any information not available in the codebase.",
  input_schema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "The search query.",
      },
      num_results: {
        type: "number",
        description: "Number of results to return (default: 5, max: 10).",
      },
    },
    required: ["query"],
  },
} as const;

// ── Helpers ────────────────────────────────────────────────────────────────

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
    .replace(/\s{3,}/g, "\n\n")
    .trim();
}

function fetchUrl(url: string, timeoutMs = 10000): Promise<string> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const lib = parsed.protocol === "https:" ? https : http;
    const req = lib.get(url, { headers: { "User-Agent": "BharatBuild-CLI/1.0" } }, (res) => {
      // Follow redirect
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

// ── Tool executors ─────────────────────────────────────────────────────────

export interface WebFetchInput {
  url: string;
  max_length?: number;
}

export async function executeWebFetch(input: WebFetchInput): Promise<{ content: string; isError: boolean }> {
  const { url, max_length = 10000 } = input;

  if (!url?.trim()) return { content: "Error: url is required", isError: true };

  // Basic URL validation
  try { new URL(url); } catch {
    return { content: `Error: invalid URL: ${url}`, isError: true };
  }

  try {
    const raw = await fetchUrl(url);
    const isHtml = raw.trimStart().startsWith("<!") || raw.includes("<html");
    const text = isHtml ? stripHtml(raw) : raw;
    const truncated = text.length > max_length ? text.slice(0, max_length) + `\n\n[truncated — ${text.length} total chars]` : text;
    return { content: `URL: ${url}\n\n${truncated}`, isError: false };
  } catch (err) {
    return { content: `Failed to fetch ${url}: ${err instanceof Error ? err.message : String(err)}`, isError: true };
  }
}

export interface WebSearchInput {
  query: string;
  num_results?: number;
}

export async function executeWebSearch(input: WebSearchInput): Promise<{ content: string; isError: boolean }> {
  const { query, num_results = 5 } = input;

  if (!query?.trim()) return { content: "Error: query is required", isError: true };

  const limit = Math.min(num_results, 10);

  // Strategy 1: DuckDuckGo Instant Answer API (JSON, no key needed, stable)
  try {
    const ddgJson = await fetchUrl(
      `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_redirect=1&no_html=1&skip_disambig=1`,
      8000
    );
    const data = JSON.parse(ddgJson) as {
      AbstractText?: string;
      AbstractURL?: string;
      AbstractSource?: string;
      RelatedTopics?: Array<{ Text?: string; FirstURL?: string; Topics?: Array<{ Text?: string; FirstURL?: string }> }>;
      Results?: Array<{ Text?: string; FirstURL?: string }>;
    };

    const results: Array<{ title: string; url: string; snippet: string }> = [];

    // Direct answer / abstract
    if (data.AbstractText && data.AbstractURL) {
      results.push({
        title:   data.AbstractSource ?? "Answer",
        url:     data.AbstractURL,
        snippet: data.AbstractText.slice(0, 300),
      });
    }

    // Instant results
    for (const r of data.Results ?? []) {
      if (results.length >= limit) break;
      if (r.FirstURL && r.Text) {
        results.push({ title: r.Text.slice(0, 80), url: r.FirstURL, snippet: r.Text.slice(0, 200) });
      }
    }

    // Related topics
    for (const t of data.RelatedTopics ?? []) {
      if (results.length >= limit) break;
      // Topics can be nested
      const items = t.Topics ?? [t];
      for (const item of items) {
        if (results.length >= limit) break;
        if (item.FirstURL && item.Text) {
          results.push({ title: item.Text.slice(0, 80), url: item.FirstURL, snippet: item.Text.slice(0, 200) });
        }
      }
    }

    if (results.length > 0) {
      const formatted = results
        .map((r, i) => `${i + 1}. **${r.title}**\n   URL: ${r.url}\n   ${r.snippet}`)
        .join("\n\n");
      return { content: `Search results for: "${query}"\n\n${formatted}`, isError: false };
    }
    // No results from JSON API — fall through to strategy 2
  } catch {
    // JSON API failed — fall through
  }

  // Strategy 2: DuckDuckGo HTML scrape (fallback)
  try {
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    const html = await fetchUrl(searchUrl, 12000);

    const results: Array<{ title: string; url: string; snippet: string }> = [];
    const resultPattern = /<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
    const snippetPattern = /<a[^>]+class="result__snippet"[^>]*>([\s\S]*?)<\/a>/gi;

    let match: RegExpExecArray | null;
    const urls: string[] = [];
    const titles: string[] = [];
    const snippets: string[] = [];

    while ((match = resultPattern.exec(html)) !== null && urls.length < limit) {
      const rawUrl = match[1] ?? "";
      const title  = stripHtml(match[2] ?? "").trim();
      const uddg   = rawUrl.match(/uddg=([^&]+)/);
      const actualUrl = uddg ? decodeURIComponent(uddg[1] ?? rawUrl) : rawUrl;
      if (actualUrl.startsWith("http")) { urls.push(actualUrl); titles.push(title); }
    }

    while ((match = snippetPattern.exec(html)) !== null && snippets.length < limit) {
      snippets.push(stripHtml(match[1] ?? "").trim());
    }

    for (let i = 0; i < Math.min(urls.length, limit); i++) {
      results.push({ title: titles[i] ?? "", url: urls[i] ?? "", snippet: snippets[i] ?? "" });
    }

    if (results.length > 0) {
      const formatted = results
        .map((r, i) => `${i + 1}. **${r.title}**\n   URL: ${r.url}\n   ${r.snippet}`)
        .join("\n\n");
      return { content: `Search results for: "${query}"\n\n${formatted}`, isError: false };
    }
  } catch {
    // HTML scrape failed — fall through
  }

  // Strategy 3: Brave Search API (if key is set)
  const braveKey = process.env["BRAVE_SEARCH_API_KEY"];
  if (braveKey) {
    try {
      const braveUrl = `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(query)}&count=${limit}`;
      const raw = await fetchUrl(braveUrl + `&key=${braveKey}`, 10000);
      const data = JSON.parse(raw) as {
        web?: { results?: Array<{ title?: string; url?: string; description?: string }> };
      };
      const items = data.web?.results ?? [];
      if (items.length > 0) {
        const formatted = items
          .map((r, i) => `${i + 1}. **${r.title ?? ""}**\n   URL: ${r.url ?? ""}\n   ${r.description ?? ""}`)
          .join("\n\n");
        return { content: `Search results for: "${query}"\n\n${formatted}`, isError: false };
      }
    } catch {
      // Brave failed — fall through
    }
  }

  // All strategies exhausted
  return {
    content:
      `No search results found for: "${query}"\n\n` +
      `Tip: Use web_fetch with a direct URL (e.g. web_fetch with url="https://docs.example.com/...") ` +
      `or set BRAVE_SEARCH_API_KEY for reliable search results.`,
    isError: false,
  };
}