#!/usr/bin/env node
/**
 * BharatBuild CLI — Entry Point
 *
 * Usage:
 *   bharatbuild                          Interactive REPL
 *   bharatbuild login                    Authenticate
 *   bharatbuild logout                   Clear credentials
 *   bharatbuild register                 Create account
 *   bharatbuild whoami                   Show account info
 *   bharatbuild projects                 List projects
 *   bharatbuild download <id>            Download project as ZIP
 *   bharatbuild delete <id>              Delete project
 *   bharatbuild tokens                   Show token balance
 *   bharatbuild mode <mode>              Set default mode
 *
 *   bharatbuild student "hospital mgmt system"
 *   bharatbuild developer "build a todo app in React"
 *   bharatbuild founder "create PRD for food delivery app"
 */

import { Command } from "commander";
import chalk from "chalk";
import path from "path";
import fs from "fs";
import os from "os";

import { loadConfig, saveConfig } from "./config/config.js";
import { BharatBuildClient } from "./api/client.js";
import { attachAutoRefresh } from "./auth/refresh.js";
import {
  loadCredentials,
  clearCredentials,
  whoami,
  login,
  register,
} from "./api/auth.js";
import { printBanner, printModeSelector, Spinner, prompt, promptPassword } from "./ui/spinner.js";
// Types only. The REPL class this module also exports is never constructed
// anywhere — `chat` runs the ink TUI, or TUISession when there is no TTY — so
// importing it made a third chat surface look reachable when it is not.
// The mode-handler map and the MODES list that used to sit here fed
// BharatBuildREPL, a third chat surface that was never constructed. Each mode
// is reached through its own subcommand below, which loads its handler
// directly.

// ── Bootstrap client ──────────────────────────────────────────────────────────

function makeClient(apiUrl?: string): BharatBuildClient {
  const config = loadConfig();
  const creds = loadCredentials();
  const baseUrl = apiUrl ?? config.apiBaseUrl;
  const client = new BharatBuildClient({
    apiBaseUrl: baseUrl,
    authToken: creds?.token,
  });
  attachAutoRefresh(client, baseUrl);
  return client;
}

// ── CLI Program ───────────────────────────────────────────────────────────────

const program = new Command();

program
  .name("bharatbuild")
  .description("BharatBuild AI — AI-powered platform for Indian developers, students & founders")
  .version("1.0.0")
  .option("--api-url <url>", "Override API base URL")
  .option("--mode <mode>", "Set platform mode (student|developer|founder|college|api-partner)")
  .option("--model <model>", "AI model to use (auto, haiku, sonnet, opus, or a full provider ID) [default: auto]")
  .option("-v, --verbose", "Verbose output");

// ── login ─────────────────────────────────────────────────────────────────────

/*
 * `key` — store a provider key so direct calls do not depend on the shell.
 *
 * An environment variable has to be set again in every new terminal and does
 * nothing for a window already open, which is how a user with a working key
 * hit the server's exhausted account three times in a row.
 */
const keyCmd = program
  .command("key")
  .description("Manage a provider API key for direct (non-proxied) model calls");

keyCmd
  .command("set <api-key>")
  .description("Store an API key (anthropic|openai|gemini, detected from the key)")
  .option("--provider <name>", "Force the provider instead of detecting it")
  .action(async (apiKey: string, opts: { provider?: string }) => {
    const { keySet } = await import("./commands/key.js");
    process.exitCode = keySet(apiKey, opts.provider);
  });

keyCmd
  .command("show")
  .description("Show which key is in use, and where it came from")
  .action(async () => {
    const { keyShow } = await import("./commands/key.js");
    process.exitCode = keyShow();
  });

keyCmd
  .command("clear")
  .description("Remove the stored key and go back to the BharatBuild server")
  .option("--provider <name>", "Remove only this provider's key")
  .action(async (opts: { provider?: string }) => {
    const { keyClear } = await import("./commands/key.js");
    process.exitCode = keyClear(opts.provider);
  });

program
  .command("login")
  .description("Login to your BharatBuild account (opens browser)")
  .option("-t, --token <token>", "Use a pre-issued CLI token")
  .option("--email", "Log in with email/password in terminal (no browser)")
  .option("--no-browser-open", "Print the login URL instead of launching a browser")
  .option("--use-device-flow", "Force device flow for SSH/remote environments")
  .action(async (opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);

    // Check if already logged in
    const existingCreds = loadCredentials();
    if (existingCreds) {
      console.log(chalk.yellow(`\n  Already logged in as ${chalk.bold(existingCreds.name)} (${existingCreds.email})`));
      console.log(chalk.dim(`  Run: bharatbuild logout first, then login again.\n`));
      return;
    }

    if (opts.token) {
      // Token-based login: validate by calling /me
      client.setToken(opts.token);
      const spinner = new Spinner();
      spinner.start("Validating token…");
      try {
        const info = await whoami(client);
        const { saveCredentials } = await import("./api/auth.js");
        saveCredentials({
          token: opts.token,
          userId: "",
          email: info.email,
          name: info.name,
          tier: info.tier,
        });
        spinner.succeed(`Logged in as ${chalk.green(info.name)}`);
      } catch {
        spinner.fail("Invalid token");
        process.exit(1);
      }
      return;
    }

    if (opts.email) {
      // Email/password login in terminal (fallback)
      const email = await prompt("  Email: ");
      const password = await promptPassword("  Password: ");

      const spinner = new Spinner();
      spinner.start("Verifying credentials…");
      try {
        const creds = await login(client, email, password);
        spinner.succeed(`Logged in as ${chalk.green(creds.name)} (${creds.tier})`);
        console.log(chalk.dim(`\n  You now have full access to BharatBuild CLI.\n`));
      } catch (err) {
        spinner.fail("Login failed — invalid email or password");
        console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
        process.exit(1);
      }
      return;
    }

    // ── Default: Browser-based login ──────────────────────────────────────
    // Opens browser with login form → user enters credentials →
    // server verifies → CLI gets access token
    const { startBrowserLogin } = await import("./auth/browser-auth.js");
    const { saveCredentials } = await import("./api/auth.js");

    console.log(chalk.bold("\n  🔐 BharatBuild CLI Login\n"));
    console.log(chalk.dim("  Opening your browser to sign in…\n"));

    const spinner = new Spinner();
    try {
      const result = await startBrowserLogin({
        apiBaseUrl: config.apiBaseUrl,
        noBrowser: opts.browserOpen === false,
        onUrl: (url: string) => {
          console.log(chalk.dim(`  Login page: ${chalk.cyan(url)}`));
          if (opts.browserOpen === false) {
            console.log(chalk.dim(`\n  Open this URL in your browser to sign in.\n`));
          }
          spinner.start("Waiting for you to sign in via browser…");
        },
      });
      spinner.stop();

      // Save credentials
      saveCredentials({
        token: result.token,
        refreshToken: result.refreshToken,
        userId: result.userId,
        email: result.email,
        name: result.name,
        tier: result.tier,
      });

      console.log(chalk.green(`\n  ✓ Login successful!`));
      console.log(chalk.bold(`    Welcome, ${result.name}!`));
      console.log(chalk.dim(`    Email: ${result.email}`));
      console.log(chalk.dim(`    Plan:  ${result.tier}\n`));
      console.log(chalk.dim(`  You now have full access to BharatBuild CLI.\n`));
    } catch (err) {
      spinner.stop();
      console.error(chalk.red(`\n  ✗ Login failed: ${err instanceof Error ? err.message : err}\n`));
      console.log(chalk.dim(`  Alternatives:`));
      console.log(chalk.dim(`    bharatbuild login --email         Terminal-based login`));
      console.log(chalk.dim(`    bharatbuild login --token <tok>   Use a pre-issued token\n`));
      process.exit(1);
    }
  });

// ── logout ────────────────────────────────────────────────────────────────────

program
  .command("logout")
  .description("Clear stored credentials")
  .action(() => {
    clearCredentials();
    console.log(chalk.green("✓ Logged out."));
  });

// ── register ──────────────────────────────────────────────────────────────────

program
  .command("register")
  .description("Create a new BharatBuild account")
  .action(async () => {
    const client = makeClient(program.opts().apiUrl);
    const name = await prompt("  Full name: ");
    const email = await prompt("  Email: ");
    const password = await promptPassword("  Password (min 8 chars): ");

    const spinner = new Spinner();
    spinner.start("Creating account…");
    try {
      const creds = await register(client, name, email, password);
      spinner.succeed(`Account created! Welcome, ${chalk.green(creds.name)}`);
    } catch (err) {
      spinner.fail("Registration failed");
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
      process.exit(1);
    }
  });

// ── whoami ────────────────────────────────────────────────────────────────────

program
  .command("whoami")
  .description("Show logged-in account details")
  .action(async () => {
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (!creds) {
      console.log(chalk.yellow("Not logged in. Run: bharatbuild login"));
      process.exit(1);
    }
    const spinner = new Spinner();
    spinner.start("Fetching user info…");
    try {
      const info = await whoami(client);
      spinner.succeed();
      console.log();
      console.log(`  ${chalk.bold("Name:")}    ${info.name}`);
      console.log(`  ${chalk.bold("Email:")}   ${info.email}`);
      console.log(`  ${chalk.bold("Plan:")}    ${chalk.cyan(info.tier)}`);
      console.log(`  ${chalk.bold("Tokens:")}  ${chalk.green(info.tokenBalance.toLocaleString())}`);
      console.log();
    } catch (err) {
      spinner.fail();
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
      process.exit(1);
    }
  });

// ── projects ──────────────────────────────────────────────────────────────────

program
  .command("projects")
  .description("List your projects")
  .option("-l, --limit <n>", "Max results", "20")
  .action(async (opts) => {
    const client = makeClient(program.opts().apiUrl);
    const spinner = new Spinner();
    spinner.start("Loading projects…");
    try {
      const data = await client.get<{ projects?: unknown[]; items?: unknown[] }>(
        `/api/v1/projects?limit=${opts.limit}`
      );
      spinner.succeed();
      const list = (data.projects ?? data.items ?? (Array.isArray(data) ? data : [])) as Array<Record<string, unknown>>;
      if (list.length === 0) {
        console.log(chalk.dim("  No projects yet."));
        return;
      }
      console.log(chalk.bold(`\n  Your Projects (${list.length}):\n`));
      for (const p of list) {
        const id = String(p.id ?? "").slice(0, 8);
        const name = String(p.name ?? p.project_name ?? "Unnamed");
        const status = String(p.status ?? "");
        const sc = status === "completed" ? chalk.green : status === "failed" ? chalk.red : chalk.yellow;
        console.log(`  ${chalk.cyan("•")} ${chalk.bold(name)}  ${chalk.dim(`[${id}]`)}  ${sc(status)}`);
      }
      console.log();
    } catch (err) {
      spinner.fail();
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
      process.exit(1);
    }
  });

// ── download ──────────────────────────────────────────────────────────────────

program
  .command("download <projectId>")
  .description("Download a project as ZIP")
  .option("-d, --dest <dir>", "Destination directory", ".")
  .action(async (projectId: string, opts) => {
    const client = makeClient(program.opts().apiUrl);
    const spinner = new Spinner();
    spinner.start("Preparing download…");
    try {
      const data = await client.get<{ download_url?: string; url?: string }>(
        `/api/v1/projects/${projectId}/download`
      );
      spinner.succeed();
      const url = data.download_url ?? data.url ?? "";
      if (url) {
        console.log(chalk.green(`\n  ✓ Download URL: ${chalk.underline(url)}\n`));
        console.log(chalk.dim(`  Run: curl -L "${url}" -o project.zip`));
      } else {
        console.log(chalk.yellow("  No download URL returned."));
      }
    } catch (err) {
      spinner.fail();
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
      process.exit(1);
    }
  });

// ── delete ────────────────────────────────────────────────────────────────────

program
  .command("delete <projectId>")
  .description("Delete a project")
  .option("-f, --force", "Skip confirmation")
  .action(async (projectId: string, opts) => {
    if (!opts.force) {
      const answer = await prompt(`  Delete project ${projectId.slice(0, 8)}? [y/N]: `);
      if (answer.toLowerCase() !== "y") {
        console.log(chalk.dim("  Cancelled."));
        return;
      }
    }
    const client = makeClient(program.opts().apiUrl);
    const spinner = new Spinner();
    spinner.start("Deleting…");
    try {
      await client.delete(`/api/v1/projects/${projectId}`);
      spinner.succeed("Project deleted.");
    } catch (err) {
      spinner.fail();
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
      process.exit(1);
    }
  });

// ── tokens ────────────────────────────────────────────────────────────────────

program
  .command("tokens")
  .description("Show your token balance")
  .action(async () => {
    const client = makeClient(program.opts().apiUrl);
    const spinner = new Spinner();
    spinner.start("Fetching token balance…");
    try {
      const data = await client.get<Record<string, unknown>>(TOKENS_BALANCE);
      spinner.succeed();
      // The field is `remaining_tokens`. This read `tokens_remaining` — the
      // same two words the other way round — so it always fell through to 0
      // and an account with 100,000 tokens displayed as empty.
      const b = parseTokenBalance(data);
      console.log(`\n  ${chalk.bold("Token Balance:")} ${chalk.green(formatTokenBalance(b))}`);
      if (!b.unknown) {
        console.log(chalk.dim(`  used ${b.used.toLocaleString("en-IN")} of ${b.total.toLocaleString("en-IN")}`));
      }
      console.log();
    } catch (err) {
      spinner.fail();
      console.error(chalk.red(`  ${err instanceof Error ? err.message : err}`));
      process.exit(1);
    }
  });

// ── mode subcommands ──────────────────────────────────────────────────────────

// bharatbuild student "describe project"
program
  .command("student [prompt]")
  .description("🎓 Student mode — generate academic project, SRS, UML, docs, viva")
  .action(async (userPrompt?: string) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (creds) client.setToken(creds.token);

    const { runStudentMode, studentInteractiveMenu } = await import("./modes/student.js");
    if (userPrompt) {
      await runStudentMode(userPrompt, client, config);
    } else {
      await studentInteractiveMenu(client, config);
    }
  });

program
  .command("developer [prompt]")
  .alias("dev")
  .description("💻 Developer mode — Bolt-style code generation")
  .action(async (userPrompt?: string) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (creds) client.setToken(creds.token);

    const { runDeveloperMode, developerInteractiveMenu } = await import("./modes/developer.js");
    if (userPrompt) {
      await runDeveloperMode(userPrompt, client, config);
    } else {
      await developerInteractiveMenu(client, config);
    }
  });

program
  .command("founder [prompt]")
  .description("🚀 Founder mode — PRD, business plan, GTM strategy")
  .action(async (userPrompt?: string) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (creds) client.setToken(creds.token);

    const { runFounderMode, founderInteractiveMenu } = await import("./modes/founder.js");
    if (userPrompt) {
      await runFounderMode(userPrompt, client, config);
    } else {
      await founderInteractiveMenu(client, config);
    }
  });

program
  .command("college")
  .description("🏫 College mode — faculty, batch, project monitoring")
  .action(async () => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (creds) client.setToken(creds.token);

    const { collegeInteractiveMenu } = await import("./modes/college.js");
    await collegeInteractiveMenu(client, config);
  });

program
  .command("api-partner")
  .alias("api")
  .description("🔌 API Partner mode — keys, token usage, billing")
  .action(async () => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (creds) client.setToken(creds.token);

    const { apiPartnerInteractiveMenu } = await import("./modes/api-partner.js");
    await apiPartnerInteractiveMenu(client, config);
  });

// ── doctor ────────────────────────────────────────────────────────────────────

program
  .command("doctor")
  .description("Run environment diagnostics")
  .action(async () => {
    printBanner();
    console.log(chalk.bold("🩺 Diagnostics\n"));
    let allOk = true;

    // Node version
    const nodeVer = process.version;
    const nodeOk = parseInt(nodeVer.slice(1)) >= 18;
    console.log(`  Node.js  ${nodeOk ? chalk.green("✓") : chalk.red("✗")}  ${nodeVer}${!nodeOk ? chalk.red("  (requires ≥18 — visit nodejs.org)") : ""}`);
    if (!nodeOk) allOk = false;

    // Config dir
    const configDir = path.join(os.homedir(), ".bharatbuild");
    const configExists = fs.existsSync(configDir);
    if (!configExists) fs.mkdirSync(configDir, { recursive: true });
    console.log(`  Config   ${chalk.green("✓")}  ${configDir}`);

    // Auth — stored credentials alone prove nothing; the access token may be
    // expired and unrefreshable, so report what the server actually accepts.
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials();
    if (creds) {
      const who = creds.email ?? creds.name;
      process.stdout.write(`  Auth     `);
      try {
        await client.get("/api/v1/auth/me");
        console.log(`${chalk.green("✓")}  Logged in as ${chalk.green(who)}`);
      } catch {
        console.log(
          `${chalk.yellow("⚠")}  Session for ${who} is not valid  ${chalk.dim("→ run: bharatbuild login")}`
        );
      }
    } else {
      console.log(`  Auth     ${chalk.yellow("⚠")}  Not logged in  ${chalk.dim("→ run: bharatbuild login")}`);
    }

    // API connectivity — only warn, don't fail
    process.stdout.write(`  API      `);
    try {
      await Promise.race([
        client.get("/api/v1/health"),
        new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), 3000)),
      ]);
      console.log(`${chalk.green("✓")}  ${config.apiBaseUrl} reachable`);
    } catch {
      console.log(`${chalk.yellow("⚠")}  ${config.apiBaseUrl} not reachable  ${chalk.dim("→ offline or set BHARATBUILD_API_URL")}`);
      // Not a hard failure — CLI works offline with direct API keys
    }

    console.log();
    if (allOk) {
      console.log(chalk.bold.green("  ✔ Everything looks good!\n"));
    } else {
      console.log(chalk.yellow("  ⚠  Some checks need attention. Follow the hints above.\n"));
    }
  });

// ── default: interactive TUI (like kiro-cli) ──────────────────────────────────

program
  .action(async () => {
    const config = loadConfig();
    const opts = program.opts();
    if (opts.apiUrl) config.apiBaseUrl = opts.apiUrl;

    const client = makeClient(opts.apiUrl);
    const creds = loadCredentials();
    if (creds) client.setToken(creds.token);

    // Apply --model flag if provided (overrides config; default is 'auto')
    if (opts.model) config.model = opts.model;

    // Hooks start inside chatCommand now, so `bharatbuild` and
    // `bharatbuild chat` behave identically rather than differing by which
    // one you happened to type.

    // Launch the full TUI chat session (like kiro-cli does by default)
    const { chatCommand: runChat } = await import("./commands/chat.js");
    await runChat(undefined, {
      model: opts.model,
    }, config, client);
  });

// ── Kiro-matching commands ────────────────────────────────────────────────────

import { translateCommand } from "./commands/translate.js";
import { updateCommand } from "./commands/update.js";
import { settingsCommand } from "./commands/settings.js";
import { diagnosticCommand } from "./commands/diagnostic.js";
import { issueCommand } from "./commands/issue.js";
import { versionCommand } from "./commands/version.js";
import { mcpCommand } from "./commands/mcp.js";
import { agentCommand } from "./commands/agent.js";
import { hooksCommand } from "./commands/hooks.js";
import { specCommand } from "./commands/spec.js";
import { voiceCommand } from "./commands/voice.js";
import { acpCommand } from "./commands/acp.js";
import { crewCommand } from "./commands/crew.js";
import { autocompleteCommand } from "./commands/autocomplete.js";
import { chatCommand }         from "./commands/chat.js";
import { askCommand }          from "./commands/ask.js";
import { buildCommand }        from "./commands/build.js";
import { testCommand }         from "./commands/test.js";
import { fixCommand }          from "./commands/fix.js";
import { planCommand }         from "./commands/plan.js";
import { taskCommand }         from "./commands/task.js";
import { reviewCommand }       from "./commands/review.js";
import { modelCommand }        from "./commands/model.js";

import { hookRunCommand } from "./commands/hook-run.js";
import { themeCommand } from "./commands/theme.js";
import { integrationsCommand } from "./commands/integrations.js";
import { inlineCommand } from "./commands/inline.js";
import { TOKENS_BALANCE, parseTokenBalance, formatTokenBalance } from "./api/token-balance.js";

program.addCommand(hookRunCommand());
program.addCommand(updateCommand());
program.addCommand(settingsCommand());
program.addCommand(diagnosticCommand());
program.addCommand(issueCommand());
program.addCommand(versionCommand());
program.addCommand(mcpCommand());
program.addCommand(agentCommand());
program.addCommand(hooksCommand());
program.addCommand(specCommand());
program.addCommand(voiceCommand());
program.addCommand(acpCommand());
program.addCommand(crewCommand());
program.addCommand(autocompleteCommand());
program.addCommand(translateCommand());
program.addCommand(themeCommand());
program.addCommand(integrationsCommand());
program.addCommand(inlineCommand());

// -- skills command
program
  .command("skills")
  .description("Manage agent skills (.bharatbuild/skills/)")
  .option("--list", "List all active skills")
  .option("--new <name>", "Create a new skill scaffold")
  .option("--description <text>", "Description for new skill", "Custom skill")
  .action(async (opts) => {
    const { discoverSkills, createSkill } = await import("./skills/index.js");
    if (opts.new) {
      const skillPath = createSkill(opts.new as string, opts.description as string);
      console.log(chalk.green(`\n  ✓ Skill "${opts.new}" created at ${skillPath}\n`));
      console.log(chalk.dim("  Edit the SKILL.md file to add instructions, then restart your session.\n"));
    } else {
      const skills = discoverSkills(process.cwd());
      if (skills.length === 0) {
        console.log(chalk.dim("\n  No skills found.\n"));
        console.log(chalk.dim("  Create one: bharatbuild skills --new <name>\n"));
        console.log(chalk.dim("  Or add manually: .bharatbuild/skills/<name>/SKILL.md\n"));
      } else {
        console.log(chalk.bold(`\n  ✦ Active Skills (${skills.length})\n`));
        for (const s of skills) {
          console.log(`  ${chalk.cyan("•")} ${chalk.bold(s.name.padEnd(20))} ${chalk.dim(s.description)}`);
          console.log(chalk.dim(`    ${s.filePath}`));
        }
        console.log();
      }
    }
  });

// ── Parse ─────────────────────────────────────────────────────────────────────


// -- chat command
program
  .command("chat [prompt]")
  .description("Interactive chat session with full agent (tool use)")
  .option("--model <model>",           "AI model to use")
  .option("-r, --resume",              "Resume the most recent session for this directory")
  // Same behaviour, the name people reach for first — and what claude-code
  // and several other CLIs call it.
  .option("-c, --continue",            "Alias for --resume")
  .option("--resume-id <id>",          "Resume a specific session by ID")
  .option("--resume-picker",           "Open interactive session picker")
  .option("--list-sessions",           "List all saved sessions and exit")
  .option("--delete-session <id>",     "Delete a saved session by ID")
  .option("--agent <name>",            "Start with a specific agent (default|planner|coder|tester|fixer|reviewer)")
  .option("--trust-all-tools",         "Skip confirmation prompts for all tools")
  .option("--effort <level>",          "Reasoning effort: low|medium|high|xhigh|max")
  .option("--no-interactive",          "Print response to stdout without TUI (headless)")
  .action(async (prompt, opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    const { chatCommand: runChat } = await import("./commands/chat.js");
    await runChat(prompt, {
      model:          opts.model ?? program.opts().model,
      resume:         opts.resume,
      resumeId:       opts.resumeId,
      resumePicker:   opts.resumePicker,
      listSessions:   opts.listSessions,
      deleteSession:  opts.deleteSession,
      agent:          opts.agent,
      trustAllTools:  opts.trustAllTools,
      effort:         opts.effort,
      noInteractive:  opts.noInteractive,
    }, config, client);
  });

// -- ask command
program
  .command("ask <question>")
  .description("Single-shot question, prints answer and exits (no tools)")
  .option("--model <model>", "AI model to use")
  .action(async (question, opts) => {
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    const { askCommand: runAsk } = await import("./commands/ask.js");
    await runAsk(question, { model: opts.model ?? program.opts().model }, client);
  });

// -- build command
program
  .command("build")
  .description("Detect build system and build the project")
  .option("--fix", "Auto-fix build errors using AI")
  .option("--model <model>", "AI model to use")
  .action(async (opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    if (program.opts().model) config.model = program.opts().model;
    const { buildCommand: runBuild } = await import("./commands/build.js");
    await runBuild({ fix: opts.fix, model: opts.model ?? program.opts().model }, config, client);
  });

// -- test command
program
  .command("test [filter]")
  .description("Run tests, optionally auto-fix failures")
  .option("--fix", "Auto-fix failing tests using AI")
  .option("--model <model>", "AI model to use")
  .action(async (filter, opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    if (program.opts().model) config.model = program.opts().model;
    const { testCommand: runTest } = await import("./commands/test.js");
    await runTest({ fix: opts.fix, filter, model: opts.model ?? program.opts().model }, config, client);
  });

// -- fix command
program
  .command("fix [description]")
  .description("Fix errors: build errors, test failures, or a described issue")
  .option("--build", "Fix build errors")
  .option("--test", "Fix failing tests")
  .option("--model <model>", "AI model to use")
  .action(async (description, opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    if (program.opts().model) config.model = program.opts().model;
    const { fixCommand: runFix } = await import("./commands/fix.js");
    await runFix(description, { build: opts.build, test: opts.test, model: opts.model ?? program.opts().model }, config, client);
  });

// -- plan command
program
  .command("plan [goal]")
  .description("Generate a step-by-step implementation plan")
  .option("--model <model>", "AI model to use")
  .action(async (goal, opts) => {
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    const { planCommand: runPlan } = await import("./commands/plan.js");
    await runPlan(goal, { model: opts.model ?? program.opts().model }, client);
  });

// -- task command
program
  .command("task [description]")
  .description("Run a task with the full AI agent")
  .option("--file <path>", "Load task from file")
  .option("--model <model>", "AI model to use")
  .action(async (description, opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    if (program.opts().model) config.model = program.opts().model;
    const { taskCommand: runTask } = await import("./commands/task.js");
    await runTask(description, { file: opts.file, model: opts.model ?? program.opts().model }, config, client);
  });

// -- review command
program
  .command("review [target]")
  .description("AI code review of a file or recent git changes")
  .option("--staged", "Review staged git changes")
  .option("--model <model>", "AI model to use")
  .action(async (target, opts) => {
    const config = loadConfig();
    const client = makeClient(program.opts().apiUrl);
    const creds = loadCredentials(); if (creds) client.setToken(creds.token);
    if (program.opts().model) config.model = program.opts().model;
    const { reviewCommand: runReview } = await import("./commands/review.js");
    await runReview(target, { staged: opts.staged, model: opts.model ?? program.opts().model }, config, client);
  });

// -- model command
program
  .command("model [modelId]")
  .description("Show or set the AI model (default: auto)")
  .action(async (modelId?: string) => {
    const { modelCommand: runModel } = await import("./commands/model.js");
    runModel(modelId);
  });
program.parseAsync(process.argv).catch((err) => {
  console.error(chalk.red(`\nFatal: ${err instanceof Error ? err.message : err}\n`));
  process.exit(1);
});
