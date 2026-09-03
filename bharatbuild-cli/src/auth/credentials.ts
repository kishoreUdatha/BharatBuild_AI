/**
 * BharatBuild CLI — Credentials Store
 * Stores auth token in ~/.bharatbuild/auth.json
 */
import fs from "fs";
import os from "os";
import path from "path";
import { jwtExpiresAt, jwtIsExpired } from "./jwt.js";

export interface Credentials {
  token: string;
  refreshToken?: string;
  userId: string;
  email: string;
  name: string;
  tier: string;
  expiresAt?: number;
}

const AUTH_PATH = path.join(os.homedir(), ".bharatbuild", "auth.json");

function ensureDir(): void {
  fs.mkdirSync(path.dirname(AUTH_PATH), { recursive: true });
}

export function saveCredentials(creds: Credentials): void {
  ensureDir();
  // Always record the token's real expiry so later runs can tell a stale
  // access token from a live one without a round-trip.
  const withExpiry: Credentials = {
    ...creds,
    expiresAt: jwtExpiresAt(creds.token) ?? creds.expiresAt,
  };
  fs.writeFileSync(AUTH_PATH, JSON.stringify(withExpiry, null, 2), { mode: 0o600 });
}

export function loadCredentials(): Credentials | null {
  try {
    if (fs.existsSync(AUTH_PATH)) return JSON.parse(fs.readFileSync(AUTH_PATH, "utf8")) as Credentials;
  } catch { /* ignore */ }
  return null;
}

export function clearCredentials(): void {
  try { if (fs.existsSync(AUTH_PATH)) fs.unlinkSync(AUTH_PATH); } catch { /* ignore */ }
}

export function isExpired(creds: Credentials): boolean {
  // Prefer the token's own `exp` claim — `expiresAt` may be absent (browser
  // login) or a stale guess from an older CLI version.
  if (jwtExpiresAt(creds.token) !== null) return jwtIsExpired(creds.token);
  if (!creds.expiresAt) return false;
  return Date.now() >= creds.expiresAt - 60_000;
}

/** Can we still mint a fresh access token without the user logging in again? */
export function canRefresh(creds: Credentials): boolean {
  if (!creds.refreshToken) return false;
  return !jwtIsExpired(creds.refreshToken, 0);
}
