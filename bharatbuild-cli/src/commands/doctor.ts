import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import os from "os";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";

interface Check {
  name:     string;
  category: string;
  passed:   boolean;
  warning?: boolean;   // non-fatal issue
  message:  string;
  detail?:  string;
  fix?:     string;
}

// ── Individual check helpers ──────────────────────────────────────────────────

function cmd(command: string): string | null {
  try { return execSync(command, { encoding: "utf8", stdio: ["pipe","pipe","pipe"] }).trim(); }
  catch { return null; }
}

function hasCmd(bin: string): boolean {
  return !!cmd(`${process.platform === "win32" ? "where" : "which"} ${bin}`);
}

// ── Check suites ──────────────────────────────────────────────────────────────

async function checksRuntime(): Promise<Check[]> {
  const checks: Check[] = [];

  // Node.js
  const nodeVer    = process.version;
  const nodeMajor  = parseInt(nodeVer.slice(1));
  checks.push({
    name: "Node.js version", category: "Runtime",
    passed: nodeMajor >= 18,
    message: nodeVer,
    fix: nodeMajor < 18 ? "Install Node.js 18+ from nodejs.org" : undefined,
  });

  // npm
  const npmVer = cmd("npm --version");
  checks.push({
    name: "npm", category: "Runtime",
    passed: !!npmVer,
    message: npmVer ? `v${npmVer}` : "not found",
    fix: !npmVer ? "npm comes with Node.js — reinstall Node.js" : undefined,
  });

  // TypeScript (local)
  const tscVer = cmd("npx tsc --version");
  checks.push({
    name: "TypeScript", category: "Runtime",
    passed: !!tscVer, warning: !tscVer,
    message: tscVer ?? "not installed locally",
    fix: !tscVer ? "npm install -D typescript" : undefined,
  });

  // OS / platform
  checks.push({
    name: "Platform", category: "Runtime",
    passed: true,
    message: `${os.platform()} ${os.arch()} — ${os.release()}`,
  });

  // Memory
  const freeMem = Math.round(os.freemem() / 1024 / 1024);
  const totalMem = Math.round(os.totalmem() / 1024 / 1024);
  checks.push({
    name: "Memory", category: "Runtime",
    passed: freeMem > 256,
    warning: freeMem <= 256,
    message: `${freeMem}MB free of ${totalMem}MB`,
    fix: freeMem <= 256 ? "Close unused applications to free memory" : undefined,
  });

  return checks;
}

async function checksAuth(): Promise<Check[]> {
  const checks: Check[] = [];
  const creds = loadCredentials();

  checks.push({
    name: "Login status", category: "Auth",
    passed: !!creds,
    message: creds ? `Logged in as ${creds.name} (${creds.tier})` : "Not logged in",
    fix: !creds ? "Run: bharatbuild login" : undefined,
  });

  if (creds) {
    // Token expiry
    const expired = creds.expiresAt ? Date.now() >= creds.expiresAt : false;
    checks.push({
      name: "Token expiry", category: "Auth",
      passed: !expired,
      message: expired ? "Token expired" : "Token valid",
      fix: expired ? "Run: bharatbuild login" : undefined,
    });

    // Tier
    checks.push({
      name: "Subscription tier", category: "Auth",
      passed: true,
      message: creds.tier ?? "free",
    });
  }

  return checks;
}

async function checksAPIKeys(): Promise<Check[]> {
  const checks: Check[] = [];

  const keys: Array<{ name: string; env: string; provider: string }> = [
    { name: "Anthropic (Claude)", env: "ANTHROPIC_API_KEY", provider: "anthropic" },
    { name: "OpenAI (GPT-5.6)",   env: "OPENAI_API_KEY",   provider: "openai"    },
    { name: "DeepSeek",           env: "DEEPSEEK_API_KEY", provider: "deepseek"  },
    { name: "MiniMax",            env: "MINIMAX_API_KEY",  provider: "minimax"   },
    { name: "Zhipu (GLM)",        env: "ZHIPU_API_KEY",    provider: "zhipu"     },
    { name: "Qwen",               env: "QWEN_API_KEY",     provider: "qwen"      },
    { name: "Google Gemini",      env: "GEMINI_API_KEY",   provider: "google"    },
  ];

  const creds = loadCredentials();
  const hasAuth = !!creds?.token;
  let anyKey = false;

  for (const k of keys) {
    const has = !!process.env[k.env];
    if (has) anyKey = true;
    checks.push({
      name: k.name, category: "API Keys",
      passed: has || hasAuth,
      warning: !has && hasAuth,   // logged in covers it
      message: has ? "✓ set" : hasAuth ? "not set (using BharatBuild proxy)" : "not set",
      fix: !has && !hasAuth ? `Set ${k.env} in your shell profile` : undefined,
    });
  }

  // Summary
  checks.push({
    name: "At least one key / login", category: "API Keys",
    passed: anyKey || hasAuth,
    message: anyKey ? `${keys.filter((k) => !!process.env[k.env]).length} key(s) found`
            : hasAuth ? "Using BharatBuild proxy (no direct keys needed)"
            : "No API keys and not logged in",
    fix: !anyKey && !hasAuth ? "Run: bharatbuild login  OR  set ANTHROPIC_API_KEY" : undefined,
  });

  return checks;
}

async function checksNetwork(): Promise<Check[]> {
  const checks: Check[] = [];
  const config = loadConfig();
  const apiUrl = config.apiBaseUrl ?? "http://localhost:8000";

  // Backend connectivity
  try {
    const res = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(3000) });
    checks.push({
      name: "BharatBuild backend", category: "Network",
      passed: res.ok,
      message: res.ok ? `reachable (${res.status})` : `error (${res.status})`,
      detail: apiUrl,
      fix: !res.ok ? `Check backend is running at ${apiUrl}` : undefined,
    });
  } catch {
    checks.push({
      name: "BharatBuild backend", category: "Network",
      passed: false, warning: true,
      message: "unreachable",
      detail: apiUrl,
      fix: `Start backend or set BHARATBUILD_API_URL`,
    });
  }

  // Internet
  try {
    await fetch("https://api.anthropic.com", { signal: AbortSignal.timeout(3000) });
    checks.push({ name: "Internet (Anthropic)", category: "Network", passed: true, message: "reachable" });
  } catch {
    checks.push({
      name: "Internet (Anthropic)", category: "Network",
      passed: false,
      message: "unreachable — check your network / proxy",
    });
  }

  return checks;
}

async function checksGit(): Promise<Check[]> {
  const checks: Check[] = [];

  const gitVer = cmd("git --version");
  checks.push({
    name: "Git", category: "Git",
    passed: !!gitVer,
    message: gitVer ?? "not found",
    fix: !gitVer ? "Install Git from git-scm.com" : undefined,
  });

  if (gitVer) {
    // In a repo?
    const inRepo = !!cmd("git rev-parse --git-dir");
    checks.push({
      name: "Git repository", category: "Git",
      passed: inRepo, warning: !inRepo,
      message: inRepo ? "Inside a git repository" : "Not in a git repository",
    });

    if (inRepo) {
      const branch = cmd("git rev-parse --abbrev-ref HEAD");
      const status = cmd("git status --porcelain");
      checks.push({
        name: "Current branch", category: "Git",
        passed: true,
        message: branch ?? "unknown",
      });
      checks.push({
        name: "Working tree", category: "Git",
        passed: true, warning: (status ?? "").trim().length > 0,
        message: (status ?? "").trim() ? `${(status ?? "").trim().split("\n").length} uncommitted change(s)` : "clean",
      });
    }
  }

  return checks;
}

async function checksProject(): Promise<Check[]> {
  const checks: Check[] = [];
  const cwd = process.cwd();

  // package.json
  const hasPkg = fs.existsSync(path.join(cwd, "package.json"));
  checks.push({
    name: "package.json", category: "Project",
    passed: hasPkg, warning: !hasPkg,
    message: hasPkg ? "found" : "not found in current directory",
  });

  // tsconfig.json
  const hasTsc = fs.existsSync(path.join(cwd, "tsconfig.json"));
  checks.push({
    name: "tsconfig.json", category: "Project",
    passed: hasTsc, warning: !hasTsc,
    message: hasTsc ? "found" : "not found — TypeScript not configured",
    fix: !hasTsc && hasPkg ? "Run: npx tsc --init" : undefined,
  });

  // .bharatbuild config
  const configPath = path.join(cwd, ".bharatbuild.json");
  checks.push({
    name: "Project config (.bharatbuild.json)", category: "Project",
    passed: fs.existsSync(configPath), warning: !fs.existsSync(configPath),
    message: fs.existsSync(configPath) ? "found" : "not found",
    fix: !fs.existsSync(configPath) ? "Run: bharatbuild init" : undefined,
  });

  // .gitignore
  const hasGitignore = fs.existsSync(path.join(cwd, ".gitignore"));
  checks.push({
    name: ".gitignore", category: "Project",
    passed: hasGitignore, warning: !hasGitignore,
    message: hasGitignore ? "found" : "not found",
  });

  // node_modules
  if (hasPkg) {
    const hasModules = fs.existsSync(path.join(cwd, "node_modules"));
    checks.push({
      name: "node_modules", category: "Project",
      passed: hasModules,
      message: hasModules ? "installed" : "not installed",
      fix: !hasModules ? "Run: npm install" : undefined,
    });
  }

  return checks;
}

async function checksMCP(): Promise<Check[]> {
  const checks: Check[] = [];
  const mcpConfig = path.join(process.cwd(), ".bharatbuild", "mcp.json");
  const globalMcp = path.join(os.homedir(), ".bharatbuild", "mcp.json");

  const hasMcp = fs.existsSync(mcpConfig) || fs.existsSync(globalMcp);
  checks.push({
    name: "MCP config", category: "MCP",
    passed: true, warning: !hasMcp,
    message: hasMcp ? "configured" : "no MCP servers configured",
    fix: !hasMcp ? "Add .bharatbuild/mcp.json to enable MCP servers" : undefined,
  });

  return checks;
}

// ── Main runner ───────────────────────────────────────────────────────────────

async function runAllChecks(all: boolean): Promise<Check[]> {
  const suites = [
    checksRuntime(),
    checksAuth(),
    checksAPIKeys(),
    all ? checksNetwork() : Promise.resolve<Check[]>([]),
    checksGit(),
    checksProject(),
    all ? checksMCP() : Promise.resolve<Check[]>([]),
  ];
  const results = await Promise.all(suites);
  return results.flat();
}

// ── Command ───────────────────────────────────────────────────────────────────

export function doctorCommand(): Command {
  return new Command("doctor")
    .description("Run environment diagnostics — checks runtime, auth, API keys, network, git, project")
    .option("-a, --all",             "Run all checks including network and MCP")
    .option("-s, --strict",          "Exit with error code if any check fails")
    .option("-f, --format <fmt>",    "Output format: plain|json", "plain")
    .action(async (opts) => {
      const checks = await runAllChecks(!!opts.all);

      if (opts.format === "json") {
        console.log(JSON.stringify(checks, null, 2));
        return;
      }

      console.log(chalk.bold("\n  🩺 BharatBuild Doctor\n"));

      // Group by category
      const categories = [...new Set(checks.map((c) => c.category))];
      let failCount = 0;
      let warnCount = 0;

      for (const cat of categories) {
        const group = checks.filter((c) => c.category === cat);
        console.log(chalk.bold.dim(`  ── ${cat} ${"─".repeat(Math.max(0, 35 - cat.length))}`));

        for (const c of group) {
          const icon = c.passed && !c.warning ? chalk.green("✔")
                     : c.warning             ? chalk.yellow("⚠")
                     :                         chalk.red("✗");
          const label = c.name.padEnd(38);
          const msg   = c.passed && !c.warning ? chalk.dim(c.message)
                      : c.warning              ? chalk.yellow(c.message)
                      :                          chalk.red(c.message);

          console.log(`  ${icon} ${label} ${msg}`);
          if (c.detail)  console.log(chalk.dim(`       ${c.detail}`));
          if (c.fix)     console.log(chalk.cyan(`       → ${c.fix}`));
          if (!c.passed) failCount++;
          if (c.warning && c.passed) warnCount++;
        }
        console.log();
      }

      // Summary
      const total  = checks.length;
      const passed = checks.filter((c) => c.passed && !c.warning).length;

      if (failCount === 0 && warnCount === 0) {
        console.log(chalk.bold.green(`  ✔ All ${total} checks passed.\n`));
      } else {
        if (failCount > 0) console.log(chalk.bold.red(`  ✗ ${failCount} check(s) failed.`));
        if (warnCount > 0) console.log(chalk.yellow(`  ⚠ ${warnCount} warning(s).`));
        console.log(chalk.dim(`  ${passed}/${total} passed.\n`));
      }

      if (opts.strict && failCount > 0) process.exit(1);
    });
}

