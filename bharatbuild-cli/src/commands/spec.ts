import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto } from "../models/model-router.js";
import { generateSpec } from "../spec/spec-generator.js";
import { loadRequirements } from "../spec/requirements.js";
import { loadDesignDoc } from "../spec/design-doc.js";
import { loadSteeringFile, saveSteeringFile } from "../spec/steering-file.js";
import { loadSpecTasks, setTaskChecked, taskToPrompt } from "../tasks/tasks-md.js";
import { syncTasks, updateTask, listTasks } from "../tasks/task-state.js";
import { AgentRuntime } from "../runtime/agent-runtime.js";

/**
 * Reconcile tasks.md with persisted state and return the merged board.
 *
 * A ticked checkbox is authoritative: the file is the artifact a human edits,
 * so a task marked [x] by hand counts as done even if tasks.json was deleted
 * or never written.
 */
function loadTaskBoard() {
  const parsed = loadSpecTasks();
  if (parsed.length === 0) return { parsed, states: [] };

  let states = syncTasks(parsed.map((p) => ({ title: p.title, line: p.line })));
  let changed = false;
  for (const [i, p] of parsed.entries()) {
    const st = states[i];
    if (st && p.checked && st.status !== "done") {
      updateTask(st.id, { status: "done" });
      changed = true;
    }
  }
  if (changed) states = listTasks();
  return { parsed, states };
}

export function specCommand(): Command {
  const cmd = new Command("spec").description("Spec-driven development workflow");

  // bharatbuild spec new <title>  — approval-gated (Kiro Spec agent)
  cmd.command("new <title>").description("Structured spec with approval gates (Requirements -> Design -> Tasks)").option("-d, --description <text>", "Feature description").action(async (title: string, opts) => {
    const config = loadConfig();
    const model = createModelClientAuto(config.model ?? "auto");
    const { SpecAgent } = await import("../agents/spec-agent.js");
    const agent = new SpecAgent(model, config.model);
    await agent.run(opts.description ?? title);
  });

  // bharatbuild spec quick <title>  — no gates (Kiro Quick Spec agent)
  cmd.command("quick <title>").description("Quick spec — auto-generates all phases without approval gates").option("-d, --description <text>", "Feature description").action(async (title: string, opts) => {
    const config = loadConfig();
    const model = createModelClientAuto(config.model ?? "auto");
    const { QuickSpecAgent } = await import("../agents/spec-agent.js");
    const agent = new QuickSpecAgent(model, config.model);
    await agent.run(opts.description ?? title);
  });

  // bharatbuild spec generate <title>  — legacy single-shot generation
  cmd.command("generate <title>").description("Generate requirements + design in one shot (legacy)").option("-d, --description <text>", "Feature description").action(async (title: string, opts) => {
    const config = loadConfig();
    const description = opts.description ?? title;
    console.log(chalk.bold(`\n📋 Generating spec for: ${title}\n`));
    try {
      const model = createModelClientAuto(config.model ?? "auto");
      const { requirementsPath, designPath } = await generateSpec({ title, description }, model);
      console.log(chalk.green(`\n✓ Spec generated!`));
      console.log(`  Requirements: ${chalk.cyan(requirementsPath)}`);
      console.log(`  Design:       ${chalk.cyan(designPath)}\n`);
    } catch (err) {
      console.error(chalk.red(`Error: ${err instanceof Error ? err.message : err}`));
    }
  });

  // bharatbuild spec tasks — show tasks.md items with their persisted status
  cmd.command("tasks").description("List implementation tasks and their status").action(() => {
    const { states } = loadTaskBoard();
    if (states.length === 0) {
      console.log(chalk.dim("\nNo tasks found. Run: bharatbuild spec new <title>\n"));
      return;
    }
    console.log(chalk.bold("\n✅ Implementation Tasks:\n"));
    for (const t of states) {
      const badge =
        t.status === "done"        ? chalk.green("done   ")
        : t.status === "failed"    ? chalk.red("failed ")
        : t.status === "in_progress" ? chalk.yellow("running")
        : chalk.dim("pending");
      console.log(`  [${badge}] ${chalk.cyan(t.id.padEnd(8))} ${t.title}`);
      if (t.error) console.log(chalk.red(`             ${t.error}`));
    }
    const done = states.filter((t) => t.status === "done").length;
    console.log(chalk.dim(`\n  ${done}/${states.length} complete — run 'bharatbuild spec run' to continue.\n`));
  });

  // bharatbuild spec run [taskId] — execute tasks through the agent
  cmd
    .command("run [taskId]")
    .description("Execute pending tasks from tasks.md with the full agent")
    .option("--all", "Run every pending task without stopping on failure")
    .option("--dry-run", "Show what would run, change nothing")
    .action(async (taskId: string | undefined, opts: { all?: boolean; dryRun?: boolean }) => {
      const { parsed, states } = loadTaskBoard();
      if (states.length === 0) {
        console.log(chalk.dim("\nNo tasks found. Run: bharatbuild spec new <title>\n"));
        return;
      }

      const pending = states.filter((t) => (taskId ? t.id === taskId : t.status !== "done"));

      if (pending.length === 0) {
        console.log(taskId
          ? chalk.yellow(`\nNo task named ${taskId}. Run 'bharatbuild spec tasks' to list them.\n`)
          : chalk.green("\n✓ All tasks are already complete.\n"));
        return;
      }

      const queue = taskId || opts.all ? pending : [pending[0]!];

      if (opts.dryRun) {
        console.log(chalk.bold(`\n🔍 Dry run — ${queue.length} task(s) would execute:\n`));
        for (const t of queue) console.log(`  ${chalk.cyan(t.id)}  ${t.title}`);
        console.log();
        return;
      }

      const config = loadConfig();
      const model = createModelClientAuto(config.model ?? "auto");

      console.log(chalk.bold(`\n🚀 Running ${queue.length} task(s)\n`));

      for (const task of queue) {
        const source = parsed[Number(task.id.split("-")[1]) - 1];
        if (!source) continue;

        console.log(chalk.bold.cyan(`\n▶ ${task.id}: ${task.title}\n`));
        updateTask(task.id, { status: "in_progress" });

        // A fresh runtime per task keeps one task's context from bleeding into
        // the next, which is what makes a long task list drift off-spec.
        const runtime = new AgentRuntime({ config, model });
        runtime.events.on("text", (e) => {
          if ("text" in e) process.stdout.write(String(e.text));
        });

        try {
          await runtime.run(taskToPrompt(source));
          updateTask(task.id, { status: "done" });
          setTaskChecked(source.line, true);
          console.log(chalk.green(`\n✓ ${task.id} complete\n`));
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          updateTask(task.id, { status: "failed", error: message });
          console.error(chalk.red(`\n✗ ${task.id} failed: ${message}\n`));
          if (!opts.all) {
            console.log(chalk.dim("  Stopping. Fix the issue and re-run, or use --all to continue past failures.\n"));
            await runtime.closeMCP();
            break;
          }
        } finally {
          // Each task gets its own runtime, so its MCP servers must be shut
          // down here or a long task list leaks a child process per task.
          await runtime.closeMCP();
        }
      }

      const finalStates = listTasks();
      const done = finalStates.filter((t) => t.status === "done").length;
      console.log(chalk.bold(`\n${done}/${finalStates.length} tasks complete.\n`));
    });

  cmd.command("list").description("List requirements from spec").action(() => {
    const reqs = loadRequirements();
    if (reqs.length === 0) { console.log(chalk.dim("No requirements found. Run: bharatbuild spec new <title>")); return; }
    console.log(chalk.bold("\n📋 Requirements:\n"));
    for (const r of reqs) {
      const badge = r.priority === "must" ? chalk.red("MUST") : r.priority === "should" ? chalk.yellow("SHOULD") : chalk.dim("COULD");
      console.log(`  [${badge}] ${chalk.bold(r.id)}: ${r.title}`);
    }
    console.log();
  });

  cmd.command("design").description("Show design document").action(() => {
    const doc = loadDesignDoc();
    if (!doc) { console.log(chalk.dim("No design doc found. Run: bharatbuild spec new <title>")); return; }
    console.log(chalk.bold(`\n🏗️  ${doc.title}\n`));
    if (doc.overview) console.log(chalk.bold("Overview:\n") + doc.overview + "\n");
    if (doc.components.length) console.log(chalk.bold("Components:\n") + doc.components.map((c) => `  • ${c}`).join("\n") + "\n");
    if (doc.openQuestions.length) console.log(chalk.bold("Open Questions:\n") + doc.openQuestions.map((q) => `  ? ${q}`).join("\n") + "\n");
  });

  cmd.command("steering").description("View or edit steering file").option("--set-persona <text>", "Set agent persona").option("--add-rule <rule>", "Add a rule").option("--set-model <model>", "Set preferred model").action((opts) => {
    const steering = loadSteeringFile();
    if (opts.setPersona) { steering.persona = opts.setPersona; saveSteeringFile(steering); console.log(chalk.green("✓ Persona updated")); return; }
    if (opts.addRule) { steering.rules = [...(steering.rules ?? []), opts.addRule]; saveSteeringFile(steering); console.log(chalk.green(`✓ Rule added: ${opts.addRule}`)); return; }
    if (opts.setModel) { steering.model = opts.setModel; saveSteeringFile(steering); console.log(chalk.green(`✓ Model set to: ${opts.setModel}`)); return; }
    console.log(chalk.bold("\n📋 Steering File:\n"));
    if (steering.persona) console.log(chalk.bold("Persona:") + "\n" + steering.persona);
    if (steering.rules?.length) console.log(chalk.bold("Rules:") + "\n" + steering.rules.map((r) => `  • ${r}`).join("\n"));
    if (steering.model) console.log(chalk.bold("Model:") + " " + steering.model);
    if (!steering.persona && !steering.rules?.length) console.log(chalk.dim("No steering configured."));
    console.log();
  });

  return cmd;
}