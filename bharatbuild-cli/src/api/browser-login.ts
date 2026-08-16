/**
 * BharatBuild CLI - Browser login (loopback handoff)
 *
 * The standard CLI auth pattern used by `gh auth login`, `aws sso login`, and
 * `vercel login`:
 *
 *   1. CLI starts a one-shot HTTP server on 127.0.0.1:<random port>
 *   2. CLI opens the web login page with ?cli_port=<port>&cli_state=<nonce>
 *   3. You log in normally in the browser
 *   4. The page hands the token back to the loopback server
 *   5. CLI stores it, renders a "you can close this tab" page, and exits
 *
 * REQUIRES A FRONTEND CHANGE. The login page must read `cli_port` / `cli_state`
 * and POST the token back after a successful login. Until that ships, this flow
 * will time out — see docs/cli-browser-login.md for the exact patch.
 *
 * Security notes:
 *   - The listener binds to 127.0.0.1 only, never 0.0.0.0.
 *   - A random `state` nonce is required on the callback and compared with
 *     timingSafeEqual, so another local process cannot inject a token.
 *   - The server accepts exactly one successful callback, then closes.
 *   - The token never appears in a URL we log.
 */
import http from "http";
import crypto from "crypto";
import { spawn } from "child_process";
import { AddressInfo } from "net";

export interface BrowserLoginResult {
  token: string;
  refreshToken?: string;
  email?: string;
  name?: string;
  tier?: string;
  userId?: string;
}

export interface BrowserLoginOptions {
  /** Web login page, e.g. https://bharatbuild.ai/login */
  loginUrl: string;
  /** How long to wait for the browser handoff. */
  timeoutMs?: number;
  /** Print the URL instead of launching a browser. */
  noBrowser?: boolean;
  onUrl?: (url: string) => void;
}

const DEFAULT_TIMEOUT_MS = 180_000;

/** Constant-time compare so a wrong nonce leaks no timing information. */
function safeEqual(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

function page(title: string, message: string, ok: boolean): string {
  return `<!doctype html><meta charset="utf-8"><title>${title}</title>
<style>
  body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#0d1117;color:#e6edf3;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
  .c{text-align:center;max-width:28rem;padding:2rem}
  .i{font-size:3rem;line-height:1;margin-bottom:1rem}
  h1{font-size:1.25rem;margin:0 0 .5rem}
  p{color:#8b949e;margin:0;line-height:1.6}
</style>
<div class="c"><div class="i">${ok ? "✅" : "⚠️"}</div>
<h1>${title}</h1><p>${message}</p></div>
<script>setTimeout(function(){window.close()},2000)</script>`;
}

/** Open a URL in the user's default browser, cross-platform. */
function openBrowser(url: string): void {
  const cmd =
    process.platform === "win32" ? { file: "cmd", args: ["/c", "start", "", url] }
    : process.platform === "darwin" ? { file: "open", args: [url] }
    : { file: "xdg-open", args: [url] };
  try {
    // Detached so closing the browser never blocks or kills the CLI.
    spawn(cmd.file, cmd.args, { stdio: "ignore", detached: true }).unref();
  } catch {
    /* fall back to the printed URL */
  }
}

export async function browserLogin(opts: BrowserLoginOptions): Promise<BrowserLoginResult> {
  const state = crypto.randomBytes(24).toString("base64url");
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  return new Promise<BrowserLoginResult>((resolve, reject) => {
    let settled = false;
    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      // Give the response a moment to flush before tearing the socket down.
      setTimeout(() => server.close(), 100);
      fn();
    };

    const server = http.createServer((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");

      // The page is served from https://bharatbuild.ai, so the callback is
      // cross-origin and needs CORS (including the preflight).
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.setHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
      res.setHeader("Access-Control-Allow-Headers", "Content-Type");

      if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }

      if (!url.pathname.startsWith("/callback")) {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end("not found");
        return;
      }

      const handle = (payload: Record<string, unknown>, given: string | null) => {
        if (!given || !safeEqual(given, state)) {
          res.writeHead(403, { "Content-Type": "text/html" });
          res.end(page("Login rejected", "State mismatch — this request did not come from the CLI session you started.", false));
          return; // do not settle: a bad nonce must not end the wait
        }
        const token = String(payload["token"] ?? payload["access_token"] ?? "");
        if (!token) {
          res.writeHead(400, { "Content-Type": "text/html" });
          res.end(page("Login failed", "The login page did not send a token.", false));
          finish(() => reject(new Error("no token in callback")));
          return;
        }
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(page("You're signed in", "Authentication complete — you can close this tab and return to your terminal.", true));
        finish(() => resolve({
          token,
          refreshToken: (payload["refresh_token"] ?? payload["refreshToken"]) as string | undefined,
          email:  payload["email"]  as string | undefined,
          name:   payload["name"]   as string | undefined,
          tier:   payload["tier"]   as string | undefined,
          userId: (payload["user_id"] ?? payload["userId"]) as string | undefined,
        }));
      };

      if (req.method === "POST") {
        let body = "";
        req.on("data", (c) => {
          body += c;
          if (body.length > 64_000) req.destroy(); // don't buffer unbounded input
        });
        req.on("end", () => {
          let payload: Record<string, unknown> = {};
          try { payload = JSON.parse(body || "{}"); } catch { /* handled below */ }
          handle(payload, String(payload["state"] ?? url.searchParams.get("state") ?? ""));
        });
        return;
      }

      // GET fallback, for a page that can only redirect.
      handle(Object.fromEntries(url.searchParams.entries()), url.searchParams.get("state"));
    });

    const timer = setTimeout(() => {
      finish(() => reject(new Error(
        `timed out after ${Math.round(timeoutMs / 1000)}s waiting for the browser. ` +
        `If the login page does not yet support CLI handoff, use: bharatbuild login --token <token>`,
      )));
    }, timeoutMs);

    server.on("error", (err) => finish(() => reject(err)));

    // Port 0 = let the OS pick a free port. 127.0.0.1 keeps it off the network.
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address() as AddressInfo;
      const target = new URL(opts.loginUrl);
      target.searchParams.set("cli_port", String(port));
      target.searchParams.set("cli_state", state);
      const url = target.toString();

      opts.onUrl?.(url);
      if (!opts.noBrowser) openBrowser(url);
    });
  });
}
