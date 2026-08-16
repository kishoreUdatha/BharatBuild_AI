import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface UsageStats {
  tokensUsed:      number;
  tokensLimit:     number;
  creditBalance:   number;
  creditsUsed:     number;   // Kiro-style fractional credits this session
  model:           string;
  sessionTokens:   number;
  sessionCost:     number;   // USD
  turns:           number;
  elapsedMs:       number;
  breakdown?:      string;   // per-turn detail from CostMeter.breakdown()
}

export function renderUsagePanel(stats: UsageStats): void {
  const t   = getTheme();
  const pct = Math.min(100, Math.round((stats.tokensUsed / Math.max(1, stats.tokensLimit)) * 100));
  const barLen = 36;
  const filled = Math.round((pct / 100) * barLen);
  const bar    = t.success("█".repeat(filled)) + t.dim("░".repeat(barLen - filled));

  console.log(t.heading("\n  📊 Usage — this session\n"));

  // ── Credits (primary metric, matches Kiro UI) ──────────────────────────────
  const creditsStr = stats.creditsUsed >= 0.01
    ? stats.creditsUsed.toFixed(2)
    : "<0.01";
  console.log(`  ${chalk.bold("Credits used:")}   ${chalk.cyan(creditsStr)}`);
  if (stats.creditBalance > 0) {
    console.log(`  ${chalk.bold("Balance:")}        ${chalk.green(stats.creditBalance.toFixed(2))} credits remaining`);
  }

  // ── Tokens ─────────────────────────────────────────────────────────────────
  console.log();
  console.log(`  ${bar} ${pct}%`);
  console.log(`  ${t.dim("Session tokens:")} ${stats.sessionTokens.toLocaleString()}`);
  if (stats.tokensLimit > 0) {
    console.log(`  ${t.dim("Context limit:")}  ${stats.tokensLimit.toLocaleString()}`);
  }

  // ── Cost + timing ──────────────────────────────────────────────────────────
  console.log();
  if (stats.sessionCost > 0) {
    console.log(`  ${t.dim("API cost (USD):")} ${t.info("$" + stats.sessionCost.toFixed(5))}`);
  }
  console.log(`  ${t.dim("Model:")}          ${stats.model}`);
  console.log(`  ${t.dim("Turns:")}          ${stats.turns}`);
  const secs = Math.round(stats.elapsedMs / 1000);
  console.log(`  ${t.dim("Elapsed:")}        ${secs}s`);

  // ── Per-turn breakdown (if available) ─────────────────────────────────────
  if (stats.breakdown) {
    console.log(t.dim("\n  Per-turn breakdown:"));
    console.log(t.dim(stats.breakdown));
  }
  console.log();
}
