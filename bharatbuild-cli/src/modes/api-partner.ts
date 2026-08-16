/**
 * BharatBuild CLI — API Partner Mode
 * API key management, token usage, billing
 */

import chalk from "chalk";
import readline from "readline";
import { BharatBuildClient, APIError } from "../api/client.js";
import { Spinner, printTable } from "../ui/spinner.js";
import type { CLIConfig } from "../config/config.js";

function ask(rl: readline.Interface, q: string): Promise<string> {
  return new Promise((resolve) =>
    rl.question(chalk.cyan(q), (a) => resolve(a.trim()))
  );
}

function maskKey(key: string): string {
  if (key.length <= 8) return "****";
  return key.slice(0, 7) + "…" + key.slice(-4);
}

// ── Token Balance ─────────────────────────────────────────────────────────────

async function showTokenBalance(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Fetching token balance…");
  try {
    const data = await client.get<Record<string, unknown>>("/api/v1/tokens/balance");
    spinner.succeed();

    const balance = Number(data.balance ?? data.tokens_remaining ?? data.available ?? 0);
    const used = Number(data.used ?? data.tokens_used ?? 0);
    const total = Number(data.total ?? data.total_tokens ?? (balance + used));

    console.log(chalk.bold("\n🪙 Token Balance\n"));
    console.log(`  ${chalk.bold("Available:")}  ${chalk.green(balance.toLocaleString("en-IN"))}`);
    if (used) console.log(`  ${chalk.bold("Used:")}       ${chalk.yellow(used.toLocaleString("en-IN"))}`);
    if (total) console.log(`  ${chalk.bold("Total:")}      ${total.toLocaleString("en-IN")}`);

    const usagePct = total > 0 ? Math.round((used / total) * 100) : 0;
    if (usagePct > 0) {
      const filled = Math.floor(usagePct / 5);
      const bar = "█".repeat(filled) + "░".repeat(20 - filled);
      console.log(`\n  Usage: [${chalk.cyan(bar)}] ${usagePct}%`);
    }
    console.log();
  } catch (err) {
    spinner.fail("Failed to fetch balance");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── API Keys ──────────────────────────────────────────────────────────────────

interface ApiKey {
  id: string;
  name: string;
  key?: string;
  key_prefix?: string;
  key_suffix?: string;
  status?: string;
  is_active?: boolean;
  created_at?: string;
  last_used_at?: string;
}

async function fetchApiKeys(client: BharatBuildClient): Promise<ApiKey[]> {
  const data = await client.get<{ api_keys?: ApiKey[]; keys?: ApiKey[]; items?: ApiKey[] }>(
    "/api/v1/api-keys"
  );
  return (data.api_keys ?? data.keys ?? data.items ?? (Array.isArray(data) ? data : [])) as ApiKey[];
}

async function listApiKeys(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading API keys…");
  try {
    const keys = await fetchApiKeys(client);
    spinner.succeed();
    if (keys.length === 0) {
      console.log(chalk.dim("\n  No API keys yet. Create one with option 3.\n"));
      return;
    }
    console.log(chalk.bold(`\n🔑 API Keys (${keys.length})\n`));
    printTable(
      ["Name", "Key (masked)", "Status", "Last Used", "Created"],
      keys.map((k) => {
        const displayKey =
          k.key_prefix && k.key_suffix
            ? `${k.key_prefix}…${k.key_suffix}`
            : k.key ? maskKey(k.key) : "—";
        const status = k.status ?? (k.is_active ? "active" : "inactive");
        return [
          k.name ?? "Unnamed",
          displayKey,
          status === "active" ? chalk.green(status) : chalk.dim(status),
          k.last_used_at ? new Date(k.last_used_at).toLocaleDateString("en-IN") : "Never",
          k.created_at ? new Date(k.created_at).toLocaleDateString("en-IN") : "—",
        ];
      })
    );
  } catch (err) {
    spinner.fail("Failed to load API keys");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

async function createApiKey(client: BharatBuildClient): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold("\n➕ Create New API Key\n"));
  const name = await ask(rl, "  Key name (e.g. 'production', 'test'): ");
  rl.close();
  if (!name) { console.log(chalk.yellow("  Name is required.\n")); return; }

  const spinner = new Spinner();
  spinner.start("Creating API key…");
  try {
    const data = await client.post<{ api_key?: string; key?: string; id?: string }>(
      "/api/v1/api-keys",
      { name, permissions: ["read", "write"] }
    );
    spinner.succeed("API key created!");
    const key = data.api_key ?? data.key ?? "";
    if (key) {
      console.log();
      console.log(chalk.bold.yellow("  ⚠  IMPORTANT: Copy this key now — it won't be shown again!\n"));
      console.log(`  ${chalk.bold("Key:")} ${chalk.green(key)}`);
      console.log();
      console.log(chalk.dim(`  Authorization: Bearer ${key}`));
      console.log();
    }
  } catch (err) {
    spinner.fail(`Failed: ${err instanceof Error ? err.message : err}`);
  }
}

async function revokeApiKey(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading keys…");
  let keys: ApiKey[];
  try { keys = await fetchApiKeys(client); spinner.succeed(); }
  catch (err) { spinner.fail(); console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`)); return; }

  if (keys.length === 0) { console.log(chalk.dim("\n  No API keys to revoke.\n")); return; }

  console.log(chalk.bold("\n🗑  Revoke API Key\n"));
  keys.forEach((k, i) => {
    const mask = k.key_prefix && k.key_suffix ? `${k.key_prefix}…${k.key_suffix}` : k.key ? maskKey(k.key) : "—";
    console.log(`  ${i + 1}. ${chalk.bold(k.name ?? "Unnamed")}  ${chalk.dim(mask)}`);
  });
  console.log();

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const idxStr = await ask(rl, "  Select key number: ");
  const confirm = await ask(rl, "  Type 'yes' to confirm: ");
  rl.close();

  if (confirm.toLowerCase() !== "yes") { console.log(chalk.dim("  Cancelled.\n")); return; }
  const idx = parseInt(idxStr, 10) - 1;
  if (isNaN(idx) || idx < 0 || idx >= keys.length) { console.log(chalk.yellow("  Invalid selection.\n")); return; }

  const spinner2 = new Spinner();
  spinner2.start("Revoking…");
  try {
    await client.delete(`/api/v1/api-keys/${keys[idx].id}`);
    spinner2.succeed(`Key "${keys[idx].name}" revoked.`);
  } catch (err) {
    spinner2.fail(`Failed: ${err instanceof Error ? err.message : err}`);
  }
}

async function showUsageHistory(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading usage history…");
  try {
    const data = await client.get<{ usage?: unknown[]; history?: unknown[]; items?: unknown[] }>(
      "/api/v1/tokens/usage?limit=20"
    );
    spinner.succeed();
    const list = (data.usage ?? data.history ?? data.items ?? (Array.isArray(data) ? data : [])) as Array<Record<string, unknown>>;
    if (list.length === 0) { console.log(chalk.dim("\n  No usage history yet.\n")); return; }
    console.log(chalk.bold(`\n📊 Usage History (last ${list.length})\n`));
    printTable(
      ["Date", "Action", "Tokens", "Cost (₹)"],
      list.map((u) => [
        u.created_at ?? u.date ?? u.timestamp ? new Date(String(u.created_at ?? u.date ?? u.timestamp)).toLocaleDateString("en-IN") : "—",
        String(u.endpoint ?? u.action ?? u.description ?? "API call"),
        String(u.tokens_used ?? u.tokens ?? 0),
        u.cost !== undefined ? `₹${Number(u.cost).toFixed(4)}` : "—",
      ])
    );
  } catch (err) {
    spinner.fail("Failed");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

function showApiDocs(): void {
  console.log(chalk.bold("\n📚 API Documentation\n"));
  console.log(`  ${chalk.bold("Swagger UI:")}   ${chalk.underline("https://api.bharatbuild.ai/docs")}`);
  console.log(`  ${chalk.bold("ReDoc:")}        ${chalk.underline("https://api.bharatbuild.ai/redoc")}`);
  console.log(`  ${chalk.bold("Web Portal:")}   ${chalk.underline("https://bharatbuild.ai/api-keys")}`);
  console.log();
  console.log(`  ${chalk.bold("Base URL:")}     ${chalk.cyan("https://api.bharatbuild.ai")}`);
  console.log(`  ${chalk.bold("Auth header:")}  ${chalk.dim("Authorization: Bearer <your-api-key>")}`);
  console.log();
  console.log(chalk.bold("  Quick Example:\n"));
  console.log(chalk.dim(`  curl -X POST https://api.bharatbuild.ai/bolt/chat/stream \\
    -H "Authorization: Bearer YOUR_KEY" \\
    -H "Content-Type: application/json" \\
    -d '{"message": "Create a React todo app", "project_id": ""}'`));
  console.log();
}

// ── interactive menu ──────────────────────────────────────────────────────────

export async function apiPartnerInteractiveMenu(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold.cyan("\n🔌 API Partner Mode\n"));
  console.log("  1. View Token Balance");
  console.log("  2. List API Keys");
  console.log("  3. Create New API Key");
  console.log("  4. Revoke API Key");
  console.log("  5. View Usage History");
  console.log("  6. View API Documentation");
  console.log("  7. Back to main REPL\n");

  const choice = await ask(rl, "Choice [1-7]: ");
  rl.close();
  if (choice === "7" || !choice) return;

  switch (choice) {
    case "1": await showTokenBalance(client); break;
    case "2": await listApiKeys(client); break;
    case "3": await createApiKey(client); break;
    case "4": await revokeApiKey(client); break;
    case "5": await showUsageHistory(client); break;
    case "6": showApiDocs(); break;
    default: console.log(chalk.yellow("  Invalid choice.\n"));
  }
}

// ── REPL handler ──────────────────────────────────────────────────────────────

export async function runApiPartnerMode(
  input: string,
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  if (input === "__menu__") { await apiPartnerInteractiveMenu(client, config); return; }
  const lower = input.toLowerCase();
  if (lower.includes("balance") || lower.includes("token")) await showTokenBalance(client);
  else if (lower.includes("key")) await listApiKeys(client);
  else if (lower.includes("usage") || lower.includes("history")) await showUsageHistory(client);
  else if (lower.includes("docs")) showApiDocs();
  else await apiPartnerInteractiveMenu(client, config);
}
