/**
 * BharatBuild CLI — Credentials Store
 * Stores auth token in ~/.bharatbuild/auth.json
 */
import fs from "fs";
import os from "os";
import path from "path";

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
  fs.writeFileSync(AUTH_PATH, JSON.stringify(creds, null, 2), { mode: 0o600 });
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
  if (!creds.expiresAt) return false;
  return Date.now() >= creds.expiresAt - 60_000;
}
