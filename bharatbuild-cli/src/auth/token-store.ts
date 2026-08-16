/**
 * BharatBuild CLI — Token Store
 * Manages API token lifecycle (refresh, validation)
 */
import { loadCredentials, saveCredentials, clearCredentials, isExpired, type Credentials } from "./credentials.js";
import { BharatBuildClient } from "../api/client.js";

export class TokenStore {
  private _client: BharatBuildClient;

  constructor(client: BharatBuildClient) {
    this._client = client;
  }

  get(): Credentials | null {
    return loadCredentials();
  }

  save(creds: Credentials): void {
    saveCredentials(creds);
    this._client.setToken(creds.token);
  }

  clear(): void {
    clearCredentials();
    this._client.clearToken();
  }

  async getValid(): Promise<Credentials | null> {
    const creds = loadCredentials();
    if (!creds) return null;
    if (!isExpired(creds)) {
      this._client.setToken(creds.token);
      return creds;
    }
    // Try refresh
    if (creds.refreshToken) {
      try {
        const res = await this._client.post<{ access_token: string; refresh_token?: string }>(
          "/api/v1/auth/refresh",
          { refresh_token: creds.refreshToken }
        );
        const updated: Credentials = {
          ...creds,
          token: res.access_token,
          refreshToken: res.refresh_token ?? creds.refreshToken,
          expiresAt: Date.now() + 24 * 60 * 60 * 1000,
        };
        this.save(updated);
        return updated;
      } catch {
        this.clear();
        return null;
      }
    }
    return null;
  }
}
