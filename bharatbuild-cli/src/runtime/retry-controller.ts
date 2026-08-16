// BharatBuild CLI — Retry Controller
// Exponential backoff with jitter, mirrors Amazon Q's retry logic

import {
  RETRY_BASE_DELAY_MS,
  RETRY_MAX_DELAY_MS,
  RETRY_MAX_ATTEMPTS,
} from "../config/constants.js";

export interface RetryOptions {
  maxAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  onRetry?: (attempt: number, error: Error, delayMs: number) => void;
}

const RETRYABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);
const RETRYABLE_MESSAGES = [
  "ECONNRESET", "ETIMEDOUT", "ENOTFOUND",
  "socket hang up", "network error",
  "rate limit", "overloaded", "too many requests",
];

export function isRetryable(error: unknown): boolean {
  if (error instanceof Error) {
    const msg = error.message.toLowerCase();
    if (RETRYABLE_MESSAGES.some(m => msg.includes(m.toLowerCase()))) return true;
    if ("status" in error && RETRYABLE_STATUS_CODES.has((error as any).status)) return true;
    if ("statusCode" in error && RETRYABLE_STATUS_CODES.has((error as any).statusCode)) return true;
  }
  return false;
}

function jitteredDelay(attempt: number, base: number, max: number): number {
  // exponential backoff + ±25% jitter
  const exp   = Math.min(base * Math.pow(2, attempt), max);
  const jitter = exp * 0.25 * (Math.random() * 2 - 1);
  return Math.max(base, Math.floor(exp + jitter));
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  opts: RetryOptions = {},
): Promise<T> {
  const maxAttempts = opts.maxAttempts ?? RETRY_MAX_ATTEMPTS;
  const baseDelayMs = opts.baseDelayMs ?? RETRY_BASE_DELAY_MS;
  const maxDelayMs  = opts.maxDelayMs  ?? RETRY_MAX_DELAY_MS;

  let lastError: Error = new Error("Unknown error");

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));

      if (attempt === maxAttempts - 1 || !isRetryable(lastError)) {
        throw lastError;
      }

      const delay = jitteredDelay(attempt, baseDelayMs, maxDelayMs);
      opts.onRetry?.(attempt + 1, lastError, delay);
      await sleep(delay);
    }
  }

  throw lastError;
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
