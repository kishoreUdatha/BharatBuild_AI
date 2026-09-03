/**
 * The provider API key, from wherever it is.
 *
 * Calling a provider directly required an environment variable, and nothing
 * else. That is fine on a server and poor on a desktop: it has to be set again
 * in every new terminal, it does not survive a reboot unless someone edits a
 * profile, and setting it in one window does nothing for a window already
 * open. A user with a perfectly good key hit "credit balance too low" from the
 * server proxy three times in a row because the variable was not where the
 * process could see it.
 *
 * So the key can also be stored once, in the same directory as the auth token
 * and with the same permissions. The environment still wins when both are set,
 * because that is what a CI job or a one-off override expects.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export type Provider = "anthropic" | "openai" | "gemini";

/** Environment variable per provider, in the order they are preferred. */
const ENV_VARS: ReadonlyArray<[Provider, string]> = [
  ["anthropic", "ANTHROPIC_API_KEY"],
  ["openai", "OPENAI_API_KEY"],
  ["gemini", "GEMINI_API_KEY"],
  ["gemini", "GOOGLE_API_KEY"],
];

function keyDir(): string {
  return process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild");
}

function keyPath(): string {
  return path.join(keyDir(), "provider-keys.json");
}

type Stored = Partial<Record<Provider, string>>;

function readStored(): Stored {
  try {
    const parsed: unknown = JSON.parse(fs.readFileSync(keyPath(), "utf8"));
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Stored;
  } catch {
    // Missing or corrupt: no stored key, which is a normal state.
    return {};
  }
}

export interface ResolvedKey {
  provider: Provider;
  key: string;
  /** Where it came from, so the startup banner can say. */
  from: "env" | "stored";
  /** The variable name, when it came from the environment. */
  envVar?: string;
}

/**
 * The direct key to use, or null to go through the server.
 *
 * Environment first: an explicitly exported variable is a deliberate override
 * for this one session, and should beat a file written months ago.
 */
export function resolveProviderKey(env: NodeJS.ProcessEnv = process.env): ResolvedKey | null {
  for (const [provider, envVar] of ENV_VARS) {
    const value = env[envVar];
    if (value && value.trim()) return { provider, key: value.trim(), from: "env", envVar };
  }

  const stored = readStored();
  for (const [provider] of ENV_VARS) {
    const value = stored[provider];
    if (value && value.trim()) return { provider, key: value.trim(), from: "stored" };
  }
  return null;
}

/**
 * Save a key for future sessions.
 *
 * 0600, like the auth token beside it — this is a credential, and the home
 * directory is not private on a shared machine.
 */
export function storeProviderKey(provider: Provider, key: string): string {
  const dir = keyDir();
  fs.mkdirSync(dir, { recursive: true });
  const file = keyPath();
  const next: Stored = { ...readStored(), [provider]: key.trim() };
  fs.writeFileSync(file, JSON.stringify(next, null, 2), { mode: 0o600 });
  // Re-apply on an existing file: writeFileSync only honours mode on create.
  try { fs.chmodSync(file, 0o600); } catch { /* not POSIX */ }
  return file;
}

/** Forget a stored key. Returns false when there was nothing to forget. */
export function clearProviderKey(provider?: Provider): boolean {
  const stored = readStored();
  if (Object.keys(stored).length === 0) return false;
  if (!provider) {
    try { fs.rmSync(keyPath()); return true; } catch { return false; }
  }
  if (!stored[provider]) return false;
  delete stored[provider];
  fs.writeFileSync(keyPath(), JSON.stringify(stored, null, 2), { mode: 0o600 });
  return true;
}

/**
 * Every provider a key exists for, from the environment or from storage.
 *
 * The model router had its own environment-only check. Once a key could live
 * in a file, that check reported nothing, so the router's candidate list came
 * back empty and it hard-fell-back to the cheapest model — for every task,
 * however it had been classified. Tasks graded "expert" ran on Haiku, and the
 * scope instructions Haiku ignores produced a 3,000-line answer to a five-line
 * question. Any place that asks "do we have a key" has to ask the same way.
 */
export function availableProviders(env: NodeJS.ProcessEnv = process.env): Provider[] {
  const found = new Set<Provider>();
  for (const [provider, envVar] of ENV_VARS) {
    if (env[envVar]?.trim()) found.add(provider);
  }
  const stored = readStored();
  for (const provider of Object.keys(stored) as Provider[]) {
    if (stored[provider]?.trim()) found.add(provider);
  }
  return [...found];
}

/** Masked for display. Never print a key in full. */
export function maskKey(key: string): string {
  if (key.length <= 12) return "…";
  return `${key.slice(0, 8)}…${key.slice(-4)}`;
}
