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

/**
 * Called when the API rejects a request with 401. Should mint a new access
 * token (e.g. via the refresh token) and return it, or null to give up.
 */
export type TokenRefresher = () => Promise<string | null>;

export interface ClientConfig {
  apiBaseUrl: string;
  authToken?: string;
  timeout?: number;
  onUnauthorized?: TokenRefresher;
}

export class BharatBuildClient {
  private baseUrl: string;
  private authToken: string | undefined;
  private timeout: number;
  private onUnauthorized: TokenRefresher | undefined;
  /** In-flight refresh, shared so concurrent 401s trigger only one refresh. */
  private refreshInFlight: Promise<string | null> | null = null;

  constructor(config: ClientConfig) {
    this.baseUrl = config.apiBaseUrl.replace(/\/$/, "");
    this.authToken = config.authToken;
    this.timeout = config.timeout ?? 60_000;
    this.onUnauthorized = config.onUnauthorized;
  }

  setToken(token: string): void {
    this.authToken = token;
  }

  setUnauthorizedHandler(handler: TokenRefresher): void {
    this.onUnauthorized = handler;
  }

  /**
   * Run the refresh handler at most once at a time. Returns the new access
   * token, or null when the session cannot be recovered.
   */
  private async refreshAuth(): Promise<string | null> {
    if (!this.onUnauthorized) return null;
    if (!this.refreshInFlight) {
      this.refreshInFlight = this.onUnauthorized()
        .catch(() => null)
        .finally(() => {
          this.refreshInFlight = null;
        });
    }
    const token = await this.refreshInFlight;
    if (token) this.authToken = token;
    return token;
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
    body?: unknown,
    allowRetry = true
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

      // Access tokens are short-lived — swap in a fresh one and retry once.
      if (res.status === 401 && allowRetry && this.onUnauthorized) {
        const token = await this.refreshAuth();
        if (token) return this.request<T>(method, path, body, false);
      }

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const err = (await res.json()) as { detail?: string; message?: string };
          detail = err.detail ?? err.message ?? detail;
        } catch {
          // ignore parse error
        }
        // The session is genuinely dead — tell the user what to do about it
        // instead of surfacing the backend's internal wording.
        if (res.status === 401 && this.authToken) {
          detail = "Session expired. Run: bharatbuild login";
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

    const connect = async (): Promise<Response> => {
      try {
        return await fetch(url, {
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
    };

    let res = await connect();

    // Nothing has been streamed yet, so a 401 here is safe to retry.
    if (res.status === 401 && this.onUnauthorized) {
      const token = await this.refreshAuth();
      if (token) res = await connect();
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
