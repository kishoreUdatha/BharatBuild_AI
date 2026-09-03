/**
 * BharatBuild CLI — Session auto-refresh
 *
 * Access tokens expire in as little as 30 minutes (ACCESS_TOKEN_EXPIRE_MINUTES),
 * while refresh tokens last days. Without this, every command started failing
 * with "Could not validate credentials" half an hour after login even though the
 * session was still recoverable.
 */
import type { BharatBuildClient } from "../api/client.js";
import { loadCredentials, saveCredentials, canRefresh } from "./credentials.js";

interface RefreshResponse {
  access_token: string;
  refresh_token?: string;
}

/**
 * Exchange the stored refresh token for a new access token and persist it.
 * Uses a bare fetch rather than the client so it can never recurse into the
 * 401 handler that calls it.
 */
export async function refreshSession(apiBaseUrl: string): Promise<string | null> {
  const creds = loadCredentials();
  if (!creds || !canRefresh(creds)) return null;

  try {
    const res = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh_token: creds.refreshToken }),
    });
    if (!res.ok) return null;

    const data = (await res.json()) as RefreshResponse;
    if (!data.access_token) return null;

    saveCredentials({
      ...creds,
      token: data.access_token,
      refreshToken: data.refresh_token ?? creds.refreshToken,
    });
    return data.access_token;
  } catch {
    return null;
  }
}

/** Give a client the ability to recover its own expired access token. */
export function attachAutoRefresh(client: BharatBuildClient, apiBaseUrl: string): BharatBuildClient {
  client.setUnauthorizedHandler(() => refreshSession(apiBaseUrl));
  return client;
}
