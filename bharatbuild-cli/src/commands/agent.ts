import type { AgentEvent } from "../runtime/event-stream.js";
import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import os from "os";
import { openEditor } from "../ui/editor.js";
import { getAllAgents } from "../agents/agent-registry.js";

interface AgentConfig { name: string; description?: string; system?: string; model?: string; tools?: string[]; }

function getAgentsDir(): string {
  return path.join(process.env["BHARATBUILD_HOME"] ?? path.join(os.homedir(), ".bharatbuild"), "agents");
}
function getAgentPath(name: string): string { return path.join(getAgentsDir(), `${name}.json`); }
function loadAgent(name: string): AgentConfig | null {
  try { const f = getAgentPath(name); if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as AgentConfig; } catch {} return null;
}
function saveAgent(agent: AgentConfig): void {
  const dir = getAgentsDir(); fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(getAgentPath(agent.name), JSON.stringify(agent, null, 2));
}

export function agentCommand(): Command {
  const cmd = new Command("agent").description("Manage agent configurations");

  cmd.command("list").description("List all available agents").action(() => {
    const builtins = getAllAgents();
    console.log(chalk.bold("\n  🤖 Built-in Agents\n"));
    for (const a of builtins) {
      const badge = a.readOnly ? chalk.yellow(" [read-only]") : a.phases ? chalk.cyan(` [${a.phases.length} phases]`) : "";
      console.log(`  ${chalk.cyan("•")} ${chalk.bold(a.name.padEnd(14))} ${chalk.dim(a.description)}${badge}`);
    }
    const dir = getAgentsDir();
    if (fs.existsSync(dir)) {
      const custom = fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => f.replace(".json", ""));
      if (custom.length) {
        console.log(chalk.bold("\n  Custom Agents\n"));
        custom.forEach((a) => console.log(`  ${chalk.green("•")} ${a}`));
      }
    }
    console.log();
    console.log(chalk.dim("  Usage:"));
    console.log(chalk.dim("    bharatbuild agent run <name> <task>"));
    console.log(chalk.dim("    bharatbuild spec new <feature>          (Spec agent)"));
    console.log(chalk.dim("    bharatbuild spec quick <feature>        (Quick Spec agent)"));
    console.log(chalk.dim("    bharatbuild agent bugfix <description>  (Bug Fix agent)"));
    console.log();
  });

  cmd.command("run <name> <task>").description("Run a built-in or custom agent").action(async (name: string, task: string) => {
    const { loadConfig } = await import("../config/config.js");
    const { createModelClientAuto } = await import("../models/model-router.js");
    const config = loadConfig();
    const model = createModelClientAuto(config.model ?? "auto");

    const onText = (e: AgentEvent) => { if (e.type === "text" && e.delta) process.stdout.write(e.content); };
    const onStatus = (e: AgentEvent) => { if (e.type === "status") console.log(chalk.dim(`\n  ⠿ ${e.message}`)); };

    switch (name.toLowerCase()) {
      case "planner":
      case "plan": {
        const { PlannerAgent } = await import("../agents/planner-agent.js");
        const agent = new PlannerAgent(model, config.model);
        agent.events.on("text", onText); agent.events.on("status", onStatus);
        await agent.plan(task); break;
      }
      case "coder":
      case "code": {
        const { CoderAgent } = await import("../agents/coder-agent.js");
        const agent = new CoderAgent(model, config.model);
        agent.events.on("text", onText);
        await agent.implement(task); break;
      }
      case "tester":
      case "test": {
        const { TesterAgent } = await import("../agents/tester-agent.js");
        const agent = new TesterAgent(model, config.model);
        agent.events.on("text", onText);
        await agent.writeAndRunTests(task); break;
      }
      case "fixer":
      case "fix": {
        const { FixerAgent } = await import("../agents/fixer-agent.js");
        const agent = new FixerAgent(model, config.model);
        agent.events.on("text", onText);
        await agent.fix(task); break;
      }
      case "reviewer":
      case "review": {
        const { ReviewerAgent } = await import("../agents/reviewer-agent.js");
        const agent = new ReviewerAgent(model, config.model);
        agent.events.on("text", onText);
        await agent.review(task); break;
      }
      case "bugfix":
      case "bug": {
        const { BugFixAgent } = await import("../agents/bugfix-agent.js");
        const agent = new BugFixAgent(model, config.model);
        agent.events.on("text", onText);
        await agent.fix(task); break;
      }
      default:
        console.log(chalk.yellow(`\n  Unknown agent: ${name}. Run 'bharatbuild agent list' to see available agents.\n`));
    }
  });

  cmd.command("bugfix <description>").description("Run the Bug Fix agent (RCA -> Fix Design -> Implementation)").action(async (description: string) => {
    const { loadConfig } = await import("../config/config.js");
    const { BugFixAgent } = await import("../agents/bugfix-agent.js");
    const config = loadConfig();
    const agent = new BugFixAgent(undefined, config.model);
    agent.events.on("text", (e: AgentEvent) => { if (e.type === "text" && e.delta) process.stdout.write(e.content); });
    await agent.fix(description);
  });

  cmd.command("create <name>").description("Create a new custom agent config").action(async (name: string) => {
    const template = JSON.stringify({ name, description: `${name} agent`, system: "You are a helpful assistant.", model: "auto", tools: ["read_file", "write_file", "execute_command"] }, null, 2);
    const content = await openEditor(template);
    if (content) { try { const agent = JSON.parse(content) as AgentConfig; saveAgent(agent); console.log(chalk.green(`\n  ✓ Agent "${name}" created\n`)); } catch { console.log(chalk.red("  ✗ Invalid JSON")); } }
    else console.log(chalk.dim("  Cancelled."));
  });

  cmd.command("edit [name]").description("Edit an agent config").action(async (name?: string) => {
    const agentName = name ?? "default";
    const existing = loadAgent(agentName) ?? { name: agentName };
    const content = await openEditor(JSON.stringify(existing, null, 2));
    if (content) { try { saveAgent(JSON.parse(content) as AgentConfig); console.log(chalk.green(`\n  ✓ Agent "${agentName}" updated\n`)); } catch { console.log(chalk.red("  ✗ Invalid JSON")); } }
  });

  cmd.command("validate <path>").description("Validate agent config file").action((agentPath: string) => {
    try {
      const content = JSON.parse(fs.readFileSync(agentPath, "utf8")) as AgentConfig;
      const missing = ["name"].filter((k) => !(k in content));
      if (missing.length) { console.log(chalk.red(`  ✗ Missing fields: ${missing.join(", ")}`)); return; }
      console.log(chalk.green(`  ✓ Valid agent config: "${content.name}"`));
    } catch (err) { console.log(chalk.red(`  ✗ ${err instanceof Error ? err.message : err}`)); }
  });

  cmd.command("set-default <name>").description("Set default agent").action(async (name: string) => {
    const { loadConfig, saveConfig } = await import("../config/config.js");
    const config = loadConfig();
    (config as unknown as Record<string, unknown>)["defaultAgent"] = name;
    saveConfig(config);
    console.log(chalk.green(`  ✓ Default agent set to "${name}"`));
  });

  return cmd;
}