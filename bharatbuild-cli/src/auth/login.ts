/**
 * BharatBuild CLI — Auth Login
 * Handles login/register flow
 */
import { BharatBuildClient } from "../api/client.js";
import { saveCredentials, type Credentials } from "./credentials.js";

interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  user?: { id: string; email: string; name?: string; full_name?: string; subscription_plan?: string; tier?: string };
}

export async function loginUser(client: BharatBuildClient, email: string, password: string): Promise<Credentials> {
  const res = await client.post<LoginResponse>("/api/v1/auth/login", { email, password });
  const creds: Credentials = {
    token: res.access_token,
    refreshToken: res.refresh_token,
    userId: res.user?.id ?? "",
    email: res.user?.email ?? email,
    name: res.user?.full_name ?? res.user?.name ?? email,
    tier: res.user?.subscription_plan ?? res.user?.tier ?? "free",
    expiresAt: Date.now() + 24 * 60 * 60 * 1000,
  };
  saveCredentials(creds);
  client.setToken(creds.token);
  return creds;
}

export async function registerUser(client: BharatBuildClient, name: string, email: string, password: string): Promise<Credentials> {
  const res = await client.post<LoginResponse>("/api/v1/auth/register", { full_name: name, email, password });
  const creds: Credentials = {
    token: res.access_token,
    refreshToken: res.refresh_token,
    userId: res.user?.id ?? "",
    email: res.user?.email ?? email,
    name,
    tier: "free",
    expiresAt: Date.now() + 24 * 60 * 60 * 1000,
  };
  saveCredentials(creds);
  client.setToken(creds.token);
  return creds;
}
