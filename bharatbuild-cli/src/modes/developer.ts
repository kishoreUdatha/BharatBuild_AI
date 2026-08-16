/**
 * BharatBuild CLI — Developer Mode
 * Bolt.new-style code generation and project builder
 */

import chalk from "chalk";
import readline from "readline";
import { BharatBuildClient, APIError } from "../api/client.js";
import { Spinner, ProgressRenderer } from "../ui/spinner.js";
import type { CLIConfig } from "../config/config.js";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const chatHistory: ChatMessage[] = [];
let currentProjectId: string | null = null;

// ── helpers ───────────────────────────────────────────────────────────────────

function ask(rl: readline.Interface, q: string): Promise<string> {
  return new Promise((resolve) =>
    rl.question(chalk.cyan(q), (a) => resolve(a.trim()))
  );
}

// ── streaming chat ────────────────────────────────────────────────────────────

async function streamChat(
  client: BharatBuildClient,
  message: string,
  projectId: string | null
): Promise<string> {
  const renderer = new ProgressRenderer();
  const parts: string[] = [];

  chatHistory.push({ role: "user", content: message });

  try {
    const stream = client.streamSSE("/bolt/chat/stream", {
      message,
      project_id: projectId ?? "",
      model: "sonnet",
      history: chatHistory.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      })),
    });

    for await (const event of stream) {
      const type = event.type;
      const data = event.data as Record<string, unknown>;

      if (type === "text") {
        const chunk = String(data?.content ?? data?.text ?? "");
        if (chunk) {
          renderer.onChunk(chunk);
          parts.push(chunk);
        }
      } else if (type === "status") {
        const msg = String(data?.message ?? data?.status ?? "");
        if (msg) renderer.onStage(msg, "start");
      } else if (type === "file") {
        const filePath = String(data?.path ?? "");
        const action = String(data?.action ?? "create");
        if (filePath) {
          const icon =
            action === "delete" ? "✗" : action === "update" ? "✎" : "✓";
          const color =
            action === "delete"
              ? chalk.red
              : action === "update"
              ? chalk.yellow
              : chalk.green;
          console.log(color(`  ${icon} ${action}: ${filePath}`));
        }
      } else if (type === "complete") {
        renderer.onComplete();
        const pid = String(data?.project_id ?? "");
        if (pid && pid !== currentProjectId) {
          currentProjectId = pid;
          console.log(
            chalk.dim(`\n  📁 Project ID: ${chalk.cyan(pid)}\n`)
          );
        }
        break;
      } else if (type === "error") {
        renderer.onError(String(data?.message ?? data?.detail ?? "Unknown error"));
        break;
      }
    }
  } catch (err) {
    renderer.onComplete();
    if (err instanceof APIError) {
      if (err.statusCode === 401)
        console.error(chalk.red("\n✗ Not authenticated. Run /login first.\n"));
      else
        console.error(chalk.red(`\n✗ API error (${err.statusCode}): ${err.detail}\n`));
    } else {
      console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : String(err)}\n`));
    }
  }

  const reply = parts.join("");
  if (reply) chatHistory.push({ role: "assistant", content: reply });
  return reply;
}

// ── project chat loop ─────────────────────────────────────────────────────────

async function projectChatLoop(
  client: BharatBuildClient,
  projectId: string | null,
  firstMessage?: string
): Promise<void> {
  currentProjectId = projectId;

  if (projectId)
    console.log(chalk.dim(`\n  Continuing project ${chalk.cyan(projectId.slice(0, 8))}…`));

  console.log(
    chalk.dim(
      `  Type your request, or type ${chalk.cyan("back")} to return to menu.\n`
    )
  );

  if (firstMessage) {
    await streamChat(client, firstMessage, projectId);
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  while (true) {
    const input = await ask(rl, `[developer] > `);
    if (!input) continue;
    if (input.toLowerCase() === "back" || input.toLowerCase() === "/back") {
      rl.close();
      return;
    }
    if (input.toLowerCase() === "exit" || input.toLowerCase() === "/exit") {
      rl.close();
      console.log(chalk.dim("\nGoodbye! 👋\n"));
      process.exit(0);
    }
    await streamChat(client, input, currentProjectId);
  }
}

// ── list projects ─────────────────────────────────────────────────────────────

async function listProjects(
  client: BharatBuildClient
): Promise<Array<Record<string, unknown>>> {
  const spinner = new Spinner();
  spinner.start("Loading projects…");
  try {
    const data = await client.get<{ projects?: unknown[]; items?: unknown[] }>(
      "/api/v1/projects?limit=20"
    );
    spinner.succeed();
    return (
      data.projects ??
      data.items ??
      (Array.isArray(data) ? data : [])
    ) as Array<Record<string, unknown>>;
  } catch (err) {
    spinner.fail();
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
    return [];
  }
}

function printProjects(list: Array<Record<string, unknown>>): void {
  if (list.length === 0) {
    console.log(chalk.dim("\n  No projects found.\n"));
    return;
  }
  console.log(chalk.bold(`\n  Your Projects:\n`));
  list.forEach((p, i) => {
    const name = String(p.name ?? p.project_name ?? "Unnamed");
    const id = String(p.id ?? "").slice(0, 8);
    const tech = String(p.tech_stack ?? p.framework ?? "—");
    console.log(
      `  ${chalk.dim(`${i + 1}.`)} ${chalk.bold(name)}  ${chalk.dim(`[${id}]`)}  ${chalk.cyan(tech)}`
    );
  });
  console.log();
}

// ── interactive menu ──────────────────────────────────────────────────────────

export async function developerInteractiveMenu(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(chalk.bold.cyan("\n💻 Developer Mode\n"));
  console.log("  1. Start new project (describe what to build)");
  console.log("  2. Continue existing project");
  console.log("  3. List my projects");
  console.log("  4. Download project as ZIP");
  console.log("  5. Delete project");
  console.log("  6. Back to main REPL\n");

  const choice = await ask(rl, "Choice [1-6]: ");
  rl.close();

  if (choice === "6" || choice === "") return;

  if (choice === "1") {
    const rl2 = readline.createInterface({ input: process.stdin, output: process.stdout });
    const description = await ask(rl2, "\n  What do you want to build?\n  > ");
    const name = await ask(rl2, "  Project name (optional, Enter to skip): ");
    rl2.close();

    if (!description) return;

    // Create project first, then enter chat
    const spinner = new Spinner();
    spinner.start("Creating project…");
    let projectId: string | null = null;
    try {
      const p = await client.post<{ id: string }>("/api/v1/projects", {
        name: name || description.slice(0, 50),
        description,
        tech_stack: "auto",
      });
      projectId = p.id ?? null;
      spinner.succeed(`Project created: ${projectId?.slice(0, 8)}`);
    } catch {
      spinner.stop();
      // Continue without project ID — backend can create one
    }

    chatHistory.length = 0;
    await projectChatLoop(client, projectId, description);

  } else if (choice === "2") {
    const list = await listProjects(client);
    if (list.length === 0) return;
    printProjects(list);

    const rl2 = readline.createInterface({ input: process.stdin, output: process.stdout });
    const idxStr = await ask(rl2, "  Select project number: ");
    rl2.close();

    const idx = parseInt(idxStr, 10) - 1;
    if (isNaN(idx) || idx < 0 || idx >= list.length) {
      console.log(chalk.yellow("  Invalid selection.\n"));
      return;
    }

    const selected = list[idx];
    const projectId = String(selected.id ?? "");
    chatHistory.length = 0;
    await projectChatLoop(client, projectId);

  } else if (choice === "3") {
    const list = await listProjects(client);
    printProjects(list);

  } else if (choice === "4") {
    const list = await listProjects(client);
    if (list.length === 0) return;
    printProjects(list);

    const rl2 = readline.createInterface({ input: process.stdin, output: process.stdout });
    const idxStr = await ask(rl2, "  Select project number to download: ");
    rl2.close();

    const idx = parseInt(idxStr, 10) - 1;
    if (isNaN(idx) || idx < 0 || idx >= list.length) {
      console.log(chalk.yellow("  Invalid selection.\n"));
      return;
    }

    const pid = String(list[idx].id ?? "");
    console.log(
      chalk.dim(`\n  Run: ${chalk.cyan(`bharatbuild download ${pid}`)}\n`)
    );

  } else if (choice === "5") {
    const list = await listProjects(client);
    if (list.length === 0) return;
    printProjects(list);

    const rl2 = readline.createInterface({ input: process.stdin, output: process.stdout });
    const idxStr = await ask(rl2, "  Select project number to delete: ");
    const confirm = await ask(rl2, "  Type 'yes' to confirm: ");
    rl2.close();

    if (confirm.toLowerCase() !== "yes") {
      console.log(chalk.dim("  Cancelled.\n"));
      return;
    }

    const idx = parseInt(idxStr, 10) - 1;
    if (isNaN(idx) || idx < 0 || idx >= list.length) return;

    const pid = String(list[idx].id ?? "");
    const spinner = new Spinner();
    spinner.start("Deleting…");
    try {
      await client.delete(`/api/v1/projects/${pid}`);
      spinner.succeed("Project deleted.");
    } catch (err) {
      spinner.fail(`Failed: ${err instanceof Error ? err.message : err}`);
    }
  }
}

// ── REPL handler ──────────────────────────────────────────────────────────────

export async function runDeveloperMode(
  input: string,
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  if (input === "__menu__") {
    await developerInteractiveMenu(client, config);
    return;
  }

  // Treat raw input as a build request
  await projectChatLoop(client, currentProjectId, input);
}
