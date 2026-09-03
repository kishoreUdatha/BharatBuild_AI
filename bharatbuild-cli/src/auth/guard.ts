/**
 * BharatBuild CLI — Auth Guard
 *
 * Utility to check if the user is logged in before executing commands.
 * If not logged in, prompts to login first.
 */

import chalk from "chalk";
import { loadCredentials, isTokenExpired, canRefreshSession, type Credentials } from "../api/auth.js";

export interface AuthCheckResult {
  authenticated: boolean;
  credentials: Credentials | null;
  reason?: string;
}

/**
 * Check if the user is authenticated. Returns credentials or null.
 * Does NOT exit the process — lets the caller decide what to do.
 */
export function checkAuth(): AuthCheckResult {
  const creds = loadCredentials();

  if (!creds) {
    return {
      authenticated: false,
      credentials: null,
      reason: "not_logged_in",
    };
  }

  // An expired access token is fine as long as a refresh token can renew it —
  // the client refreshes transparently on the first 401.
  if (isTokenExpired(creds) && !canRefreshSession(creds)) {
    return {
      authenticated: false,
      credentials: creds,
      reason: "token_expired",
    };
  }

  return {
    authenticated: true,
    credentials: creds,
  };
}

/**
 * Require authentication — if not logged in, prints error and exits.
 * Use this at the start of any command that needs auth.
 */
export function requireAuth(): Credentials {
  const result = checkAuth();

  if (result.authenticated && result.credentials) {
    return result.credentials;
  }

  if (result.reason === "token_expired") {
    console.error(chalk.yellow("\n  ⚠ Your session has expired. Please log in again.\n"));
  } else {
    console.error(chalk.red("\n  ✗ Not logged in.\n"));
  }

  console.log(chalk.dim("  Run: ") + chalk.cyan("bharatbuild login") + chalk.dim(" to authenticate.\n"));
  process.exit(1);
}

/**
 * Check if user has a direct API key set (ANTHROPIC_API_KEY, etc.)
 * This allows usage without BharatBuild login.
 */
export function hasDirectAPIKey(): boolean {
  return !!(
    process.env["ANTHROPIC_API_KEY"] ||
    process.env["OPENAI_API_KEY"] ||
    process.env["GEMINI_API_KEY"] ||
    process.env["GOOGLE_API_KEY"]
  );
}

/**
 * Require either BharatBuild login OR a direct API key.
 * Used by chat/ask commands that can work with either.
 */
export function requireAuthOrAPIKey(): Credentials | null {
  if (hasDirectAPIKey()) return null; // direct key mode

  const result = checkAuth();
  if (result.authenticated && result.credentials) return result.credentials;

  console.error(chalk.red("\n  ✗ Not logged in.\n"));
  console.log(chalk.dim("  Option 1: ") + chalk.cyan("bharatbuild login"));
  console.log(chalk.dim("  Option 2: ") + chalk.cyan("set ANTHROPIC_API_KEY=sk-ant-...") + "\n");
  process.exit(1);
}
