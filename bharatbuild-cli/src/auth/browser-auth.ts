/**
 * BharatBuild CLI — Browser Login (Self-Contained)
 *
 * Complete browser-based login flow:
 *   1. CLI starts local HTTP server on 127.0.0.1:<random port>
 *   2. CLI opens browser to http://127.0.0.1:<port>/login
 *   3. Browser shows a login form (served by the CLI itself)
 *   4. User enters email + password → form POSTs to CLI server
 *   5. CLI server calls BharatBuild API to verify credentials
 *   6. On success: stores token, shows success page, returns to terminal
 *   7. On failure: shows error in browser, user can retry
 *
 * This works immediately without needing any frontend/backend changes.
 * When the production login page supports cli_port handoff, the existing
 * browser-login.ts will be used instead.
 */

import http from "http";
import crypto from "crypto";
import { spawn } from "child_process";
import { AddressInfo } from "net";
import { DEFAULT_API_BASE_URL } from "../config/constants.js";

export interface BrowserLoginResult {
  token: string;
  refreshToken?: string;
  email: string;
  name: string;
  tier: string;
  userId: string;
}

export interface BrowserLoginOptions {
  apiBaseUrl?: string;
  timeoutMs?: number;
  noBrowser?: boolean;
  onUrl?: (url: string) => void;
  onSuccess?: (result: BrowserLoginResult) => void;
}

const DEFAULT_TIMEOUT_MS = 300_000; // 5 minutes

/** Open a URL in the user's default browser */
function openBrowser(url: string): void {
  const cmd =
    process.platform === "win32" ? { file: "cmd", args: ["/c", "start", "", url.replace(/&/g, "^&")] }
    : process.platform === "darwin" ? { file: "open", args: [url] }
    : { file: "xdg-open", args: [url] };
  try {
    spawn(cmd.file, cmd.args, { stdio: "ignore", detached: true }).unref();
  } catch { /* fall back to printed URL */ }
}

/** The HTML login page served by the CLI's local server */
function loginPage(port: number, csrfToken: string, error?: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BharatBuild CLI — Sign In</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    color: #e2e8f0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .card {
    background: rgba(30, 41, 59, 0.8);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 16px;
    padding: 2.5rem;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  }
  .logo {
    text-align: center;
    margin-bottom: 1.5rem;
  }
  .logo h1 {
    font-size: 1.5rem;
    font-weight: 700;
    background: linear-gradient(to right, #818cf8, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.25rem;
  }
  .logo p {
    color: #94a3b8;
    font-size: 0.875rem;
  }
  .form-group {
    margin-bottom: 1.25rem;
  }
  label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: #94a3b8;
    margin-bottom: 0.5rem;
  }
  input[type="email"], input[type="password"] {
    width: 100%;
    padding: 0.75rem 1rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 1rem;
    transition: border-color 0.2s;
  }
  input:focus {
    outline: none;
    border-color: #818cf8;
    box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.1);
  }
  .btn {
    width: 100%;
    padding: 0.75rem;
    background: linear-gradient(to right, #6366f1, #4f46e5);
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.1s, box-shadow 0.2s;
    margin-top: 0.5rem;
  }
  .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4); }
  .btn:active { transform: translateY(0); }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
  .error {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #fca5a5;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.875rem;
    margin-bottom: 1rem;
    display: ${error ? 'block' : 'none'};
  }
  .footer {
    text-align: center;
    margin-top: 1.5rem;
    color: #64748b;
    font-size: 0.75rem;
  }
  .spinner {
    display: none;
    width: 20px;
    height: 20px;
    border: 2px solid #ffffff40;
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <h1>⚡ BharatBuild</h1>
    <p>Sign in to your CLI</p>
  </div>

  <div class="error" id="error">${error || ''}</div>

  <form id="loginForm" action="/auth" method="POST">
    <input type="hidden" name="_csrf" value="${csrfToken}">
    <div class="form-group">
      <label for="email">Email</label>
      <input type="email" id="email" name="email" placeholder="you@example.com" required autofocus>
    </div>
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" placeholder="••••••••" required minlength="6">
    </div>
    <button type="submit" class="btn" id="submitBtn">
      <span id="btnText">Sign In</span>
      <div class="spinner" id="spinner"></div>
    </button>
  </form>

  <div class="footer">
    Authentication is verified by BharatBuild server.<br>
    Your credentials are never stored in the browser.
  </div>
</div>

<script>
document.getElementById('loginForm').addEventListener('submit', function(e) {
  e.preventDefault();
  const btn = document.getElementById('submitBtn');
  const spinner = document.getElementById('spinner');
  const btnText = document.getElementById('btnText');
  const errorEl = document.getElementById('error');

  btn.disabled = true;
  btnText.style.display = 'none';
  spinner.style.display = 'inline-block';
  errorEl.style.display = 'none';

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const csrf = document.querySelector('[name=_csrf]').value;

  fetch('/auth', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, _csrf: csrf })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      document.querySelector('.card').innerHTML = \`
        <div style="text-align:center;padding:2rem 0">
          <div style="font-size:3rem;margin-bottom:1rem">✅</div>
          <h2 style="color:#34d399;margin-bottom:0.5rem">Login Successful!</h2>
          <p style="color:#94a3b8">Welcome, \${data.name}!</p>
          <p style="color:#64748b;margin-top:1rem;font-size:0.875rem">
            You can close this tab and return to your terminal.
          </p>
        </div>
      \`;
      setTimeout(() => window.close(), 2000);
    } else {
      errorEl.textContent = data.error || 'Login failed. Please check your credentials.';
      errorEl.style.display = 'block';
      btn.disabled = false;
      btnText.style.display = 'inline';
      spinner.style.display = 'none';
    }
  })
  .catch(err => {
    errorEl.textContent = 'Connection error. Please try again.';
    errorEl.style.display = 'block';
    btn.disabled = false;
    btnText.style.display = 'inline';
    spinner.style.display = 'none';
  });
});
</script>
</body>
</html>`;
}

/** Success page shown after login */
function successPage(name: string): string {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>BharatBuild — Signed In</title>
<style>
  body{font-family:system-ui;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
  .c{text-align:center}
  .i{font-size:4rem;margin-bottom:1rem}
  h1{color:#34d399;font-size:1.5rem;margin-bottom:0.5rem}
  p{color:#94a3b8}
</style></head>
<body><div class="c">
  <div class="i">✅</div>
  <h1>Welcome, ${name}!</h1>
  <p>Authentication complete — return to your terminal.</p>
  <p style="margin-top:1rem;color:#64748b;font-size:0.875rem">This tab will close automatically.</p>
</div>
<script>setTimeout(function(){window.close()},3000)</script>
</body></html>`;
}

/**
 * Start the browser login flow.
 *
 * Opens a browser to a locally-served login form.
 * The form sends credentials to the CLI server, which verifies them
 * with the BharatBuild API and returns the token.
 */
export async function startBrowserLogin(opts: BrowserLoginOptions = {}): Promise<BrowserLoginResult> {
  const apiBaseUrl = opts.apiBaseUrl ?? DEFAULT_API_BASE_URL;
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const csrfToken = crypto.randomBytes(32).toString("hex");

  return new Promise<BrowserLoginResult>((resolve, reject) => {
    let settled = false;
    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      setTimeout(() => server.close(), 500);
      fn();
    };

    const server = http.createServer(async (req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");

      // ── Serve the login page ──
      if (req.method === "GET" && (url.pathname === "/" || url.pathname === "/login")) {
        const { port } = server.address() as AddressInfo;
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(loginPage(port, csrfToken));
        return;
      }

      // ── Handle login form submission ──
      if (req.method === "POST" && url.pathname === "/auth") {
        let body = "";
        req.on("data", (chunk) => {
          body += chunk;
          if (body.length > 10_000) { req.destroy(); return; }
        });
        req.on("end", async () => {
          try {
            const data = JSON.parse(body) as { email?: string; password?: string; _csrf?: string };

            // Verify CSRF
            if (data._csrf !== csrfToken) {
              res.writeHead(403, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ success: false, error: "Invalid session. Please refresh and try again." }));
              return;
            }

            const email = data.email?.trim();
            const password = data.password;

            if (!email || !password) {
              res.writeHead(400, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ success: false, error: "Email and password are required." }));
              return;
            }

            // Call BharatBuild API to authenticate
            const loginRes = await callLoginAPI(apiBaseUrl, email, password);

            if (loginRes.success) {
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({
                success: true,
                name: loginRes.name,
                message: "Login successful!",
              }));

              // Signal the CLI
              finish(() => resolve({
                token: loginRes.token!,
                refreshToken: loginRes.refreshToken,
                email: loginRes.email!,
                name: loginRes.name!,
                tier: loginRes.tier!,
                userId: loginRes.userId!,
              }));
            } else {
              res.writeHead(401, { "Content-Type": "application/json" });
              res.end(JSON.stringify({
                success: false,
                error: loginRes.error || "Invalid email or password.",
              }));
            }
          } catch (err) {
            res.writeHead(500, { "Content-Type": "application/json" });
            res.end(JSON.stringify({
              success: false,
              error: "Server error. Please try again.",
            }));
          }
        });
        return;
      }

      // ── 404 for everything else ──
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not found");
    });

    const timer = setTimeout(() => {
      finish(() => reject(new Error(
        `Login timed out after ${Math.round(timeoutMs / 1000)}s. ` +
        `Use: bharatbuild login --email for terminal-based login.`
      )));
    }, timeoutMs);

    server.on("error", (err) => finish(() => reject(err)));

    // Listen on random port, localhost only
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address() as AddressInfo;
      const loginUrl = `http://127.0.0.1:${port}/login`;

      opts.onUrl?.(loginUrl);
      if (!opts.noBrowser) openBrowser(loginUrl);
    });
  });
}

// ── API Call Helper ───────────────────────────────────────────────────────────

interface LoginAPIResult {
  success: boolean;
  token?: string;
  refreshToken?: string;
  email?: string;
  name?: string;
  tier?: string;
  userId?: string;
  error?: string;
}

async function callLoginAPI(baseUrl: string, email: string, password: string): Promise<LoginAPIResult> {
  const url = `${baseUrl}/api/v1/auth/login`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      signal: AbortSignal.timeout(15_000),
    });

    if (res.ok) {
      const data = await res.json() as {
        access_token: string;
        refresh_token?: string;
        user?: { id?: string; email?: string; name?: string; full_name?: string; role?: string; tier?: string; subscription_plan?: string };
      };

      return {
        success: true,
        token: data.access_token,
        refreshToken: data.refresh_token,
        email: data.user?.email ?? email,
        name: data.user?.full_name ?? data.user?.name ?? email,
        tier: data.user?.subscription_plan ?? data.user?.tier ?? data.user?.role ?? "free",
        userId: String(data.user?.id ?? ""),
      };
    }

    // API returned error
    let errorMsg = "Invalid email or password.";
    try {
      const errData = await res.json() as { detail?: string; message?: string; error?: string };
      errorMsg = errData.detail ?? errData.message ?? errData.error ?? errorMsg;
    } catch { /* ignore parse error */ }

    return { success: false, error: errorMsg };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("timeout") || msg.includes("ETIMEDOUT")) {
      return { success: false, error: "Server not reachable. Check your internet connection." };
    }
    if (msg.includes("ECONNREFUSED")) {
      return { success: false, error: "Cannot reach BharatBuild server. Try again later." };
    }
    return { success: false, error: `Connection error: ${msg}` };
  }
}
