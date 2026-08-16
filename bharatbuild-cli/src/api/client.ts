/**
 * BharatBuild CLI — HTTP + SSE API Client
 * Calls the BharatBuild FastAPI backend.
 */

export interface SSEEvent {
  type: string;
  data: unknown;
}

export class APIError extends Error {
  constructor(
    public statusCode: number,
    public detail: string
  ) {
    super(detail);
    this.name = "APIError";
  }
}

export interface ClientConfig {
  apiBaseUrl: string;
  authToken?: string;
  timeout?: number;
}

export class BharatBuildClient {
  private baseUrl: string;
  private authToken: string | undefined;
  private timeout: number;

  constructor(config: ClientConfig) {
    this.baseUrl = config.apiBaseUrl.replace(/\/$/, "");
    this.authToken = config.authToken;
    this.timeout = config.timeout ?? 60_000;
  }

  setToken(token: string): void {
    this.authToken = token;
  }

  clearToken(): void {
    this.authToken = undefined;
  }

  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    }
    return headers;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const res = await fetch(url, {
        method,
        headers: this.getAuthHeaders(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const err = (await res.json()) as { detail?: string; message?: string };
          detail = err.detail ?? err.message ?? detail;
        } catch {
          // ignore parse error
        }
        throw new APIError(res.status, detail);
      }

      // 204 No Content
      if (res.status === 204) return undefined as unknown as T;

      return (await res.json()) as T;
    } catch (err) {
      clearTimeout(timer);
      if (err instanceof APIError) throw err;
      const msg = err instanceof Error ? err.message : String(err);
      throw new APIError(0, `Network error: ${msg}`);
    }
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("POST", path, body);
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>("PUT", path, body);
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }

  /**
   * Server-Sent Events streaming — yields parsed SSEEvent objects.
   * Backend sends lines like: `data: {"type":"text","data":{...}}\n\n`
   */
  async *streamSSE(
    path: string,
    body: unknown
  ): AsyncGenerator<SSEEvent, void, unknown> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();

    let res: Response;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: {
          ...this.getAuthHeaders(),
          Accept: "text/event-stream",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      throw new APIError(0, `Stream connect error: ${msg}`);
    }

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = (await res.json()) as { detail?: string };
        detail = err.detail ?? detail;
      } catch {
        // ignore
      }
      throw new APIError(res.status, detail);
    }

    if (!res.body) {
      throw new APIError(0, "No response body for SSE stream");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double newline (SSE message boundary)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const lines = part.split("\n");
          let dataLine = "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              dataLine = line.slice(6).trim();
            }
          }

          if (!dataLine || dataLine === "[DONE]") {
            if (dataLine === "[DONE]") return;
            continue;
          }

          try {
            const parsed = JSON.parse(dataLine) as SSEEvent;
            yield parsed;
            if (parsed.type === "complete" || parsed.type === "done") return;
          } catch {
            // Skip malformed JSON lines
          }
        }
      }
    } finally {
      reader.releaseLock();
      controller.abort();
    }
  }
}
