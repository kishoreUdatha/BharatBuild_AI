/**
 * `bharatbuild key` — store a provider API key once.
 *
 * The only way to call a provider directly was an environment variable, which
 * has to be set again in every new terminal and does nothing for a window
 * already open. A user with a working key hit the server's exhausted account
 * three times in a row for exactly that reason. Storing it removes the step
 * that kept being missed.
 */

import chalk from "chalk";
import {
  resolveProviderKey, storeProviderKey, clearProviderKey, maskKey,
  type Provider,
} from "../auth/provider-key.js";

/** Guess the provider from the key's own prefix, so it need not be typed. */
export function providerFromKey(key: string): Provider | null {
  if (/^sk-ant-/.test(key)) return "anthropic";
  if (/^sk-/.test(key)) return "openai";
  if (/^AIza/.test(key)) return "gemini";
  return null;
}

export function keySet(rawKey: string | undefined, explicit?: string): number {
  const key = (rawKey ?? "").trim();
  if (!key) {
    console.error(chalk.red("\n  Usage: bharatbuild key set <api-key> [--provider anthropic|openai|gemini]\n"));
    return 1;
  }

  const provider = (explicit as Provider | undefined) ?? providerFromKey(key);
  if (!provider) {
    console.error(chalk.red("\n  Could not tell which provider that key belongs to.\n"));
    console.log(chalk.dim("  Pass it explicitly: --provider anthropic|openai|gemini\n"));
    return 1;
  }

  const file = storeProviderKey(provider, key);
  console.log(chalk.green(`\n  ✓ Saved ${provider} key ${maskKey(key)}`));
  console.log(chalk.dim(`    ${file}  (readable only by you)`));
  console.log(chalk.dim("    Model calls now go direct, billed to that account, in every terminal.\n"));
  return 0;
}

export function keyShow(): number {
  const found = resolveProviderKey();
  if (!found) {
    console.log(chalk.dim("\n  No API key. Model calls go through the BharatBuild server.\n"));
    console.log(chalk.dim("  Set one with: bharatbuild key set sk-ant-…\n"));
    return 0;
  }
  const where = found.from === "env" ? `environment (${found.envVar})` : "stored file";
  console.log(chalk.green(`\n  ${found.provider} key ${maskKey(found.key)}`));
  console.log(chalk.dim(`    from ${where}\n`));
  // The environment silently wins, which is confusing when a stored key exists
  // and appears to be ignored.
  if (found.from === "env") {
    console.log(chalk.dim("    An environment variable overrides any stored key.\n"));
  }
  return 0;
}

export function keyClear(provider?: string): number {
  const removed = clearProviderKey(provider as Provider | undefined);
  if (!removed) {
    console.log(chalk.dim("\n  No stored key to remove.\n"));
    return 0;
  }
  console.log(chalk.green(`\n  ✓ Removed stored ${provider ?? "provider"} key`));
  console.log(chalk.dim("    Model calls go through the BharatBuild server again.\n"));
  return 0;
}
