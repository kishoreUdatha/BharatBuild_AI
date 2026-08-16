/**
 * BharatBuild CLI — Auth Manager
 * Handles login, logout, token storage in ~/.bharatbuild/auth.json
 */

import fs from "fs";
import os from "os";
import path from "path";
import { BharatBuildClient, APIError } from "./client.js";

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
  const dir = path.dirname(AUTH_PATH);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

export function saveCredentials(creds: Credentials): void {
  ensureDir();
  fs.writeFileSync(AUTH_PATH, JSON.stringify(creds, null, 2), { mode: 0o600 });
}

export function loadCredentials(): Credentials | null {
  try {
    if (fs.existsSync(AUTH_PATH)) {
      const raw = fs.readFileSync(AUTH_PATH, "utf8");
      return JSON.parse(raw) as Credentials;
    }
  } catch {
    // corrupt file — ignore
  }
  return null;
}

export function clearCredentials(): void {
  try {
    if (fs.existsSync(AUTH_PATH)) fs.unlinkSync(AUTH_PATH);
  } catch {
    // ignore
  }
}

export function isTokenExpired(creds: Credentials): boolean {
  if (!creds.expiresAt) return false;
  return Date.now() >= creds.expiresAt - 60_000; // 1 min buffer
}

// ── API calls ─────────────────────────────────────────────────────────────────

interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
    name: string;
    tier?: string;
    subscription_plan?: string;
  };
}

interface UserResponse {
  id: string;
  email: string;
  name: string;
  full_name?: string;
  tier?: string;
  subscription_plan?: string;
  token_balance?: number;
  tokens_remaining?: number;
}

export async function login(
  client: BharatBuildClient,
  email: string,
  password: string
): Promise<Credentials> {
  const res = await client.post<LoginResponse>("/api/v1/auth/login", {
    email,
    password,
  });

  const user = res.user;
  const creds: Credentials = {
    token: res.access_token,
    refreshToken: res.refresh_token,
    userId: user?.id ?? "",
    email: user?.email ?? email,
    name: user?.name ?? user?.email ?? email,
    tier: user?.subscription_plan ?? user?.tier ?? "free",
    expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24h default
  };

  saveCredentials(creds);
  client.setToken(creds.token);
  return creds;
}

export async function register(
  client: BharatBuildClient,
  name: string,
  email: string,
  password: string
): Promise<Credentials> {
  const res = await client.post<LoginResponse>("/api/v1/auth/register", {
    full_name: name,
    email,
    password,
  });

  const user = res.user;
  const creds: Credentials = {
    token: res.access_token,
    refreshToken: res.refresh_token,
    userId: user?.id ?? "",
    email: user?.email ?? email,
    name: name,
    tier: "free",
    expiresAt: Date.now() + 24 * 60 * 60 * 1000,
  };

  saveCredentials(creds);
  client.setToken(creds.token);
  return creds;
}

export async function whoami(
  client: BharatBuildClient
): Promise<{ name: string; email: string; tier: string; tokenBalance: number }> {
  const res = await client.get<UserResponse>("/api/v1/auth/me");
  return {
    name: res.full_name ?? res.name ?? res.email,
    email: res.email,
    tier: res.subscription_plan ?? res.tier ?? "free",
    tokenBalance: res.tokens_remaining ?? res.token_balance ?? 0,
  };
}

export async function refreshToken(
  client: BharatBuildClient,
  creds: Credentials
): Promise<Credentials> {
  if (!creds.refreshToken) throw new APIError(401, "No refresh token available");

  const res = await client.post<LoginResponse>("/api/v1/auth/refresh", {
    refresh_token: creds.refreshToken,
  });

  const updated: Credentials = {
    ...creds,
    token: res.access_token,
    refreshToken: res.refresh_token ?? creds.refreshToken,
    expiresAt: Date.now() + 24 * 60 * 60 * 1000,
  };

  saveCredentials(updated);
  client.setToken(updated.token);
  return updated;
}
