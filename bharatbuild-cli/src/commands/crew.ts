/**
 * BharatBuild CLI - crew command
 *
 * Multi-agent parallel execution using the DAG executor.
 * Matches Kiro CLI's crew/subagent parallel model:
 *   - Independent stages run concurrently via Promise.all
 *   - Dependent stages wait for their prerequisites (DAG)
 *   - Review loops supported (stage -> reviewer -> loop back if NEEDS_CHANGES)
 *   - Real AgentRuntime per stage with full tool access
 */
import { Command } from "commander";
import chalk from "chalk";
import { loadConfig } from "../config/config.js";
import { executeDag, type DAGStage, type StageStatus } from "../crew/dag-executor.js";

function statusIcon(status: StageStatus): string {
  switch (status) {
    case "complete": return chalk.green("✓");
    case "failed":   return chalk.red("✗");
    case "running":  return chalk.cyan("⠿");
    case "skipped":  return chalk.dim("○");
    default:         return chalk.dim("○");
  }
}

export function crewCommand(): Command {
  const cmd = new Command("crew").description("Multi-agent parallel execution (DAG-based)");

  // bharatbuild crew spawn <task> --agents planner,coder,tester
  cmd
    .command("spawn <task>")
    .description("Spawn parallel agents for a task (all run concurrently)")
    .option("--agents <names>", "Comma-separated agent roles", "planner,coder,tester")
    .option("--model <model>", "AI model to use")
    .action(async (task: string, opts) => {
      const config = loadConfig();
      const activeModel = (opts.model as string | undefined) ?? config.model ?? "auto";
      const agentNames = (opts.agents as string).split(",").map((a) => a.trim());

      console.log(chalk.bold(`\n  ⚡ Crew spawning ${agentNames.length} agents in parallel\n`));
      console.log(chalk.dim(`  Task: ${task}\n`));
      console.log(chalk.dim(`  Agents: ${agentNames.join(", ")}\n`));

      const stages: DAGStage[] = agentNames.map((name) => ({
        name,
        task: `[${name} perspective] ${task}`,
        agent: name,
        model: activeModel,
        depends_on: [],
      }));

      const statusLines = new Map<string, string>();
      agentNames.forEach((n) => { statusLines.set(n, chalk.dim(`  ○ [${n}] waiting...`)); });

      function redraw() {
        process.stdout.write("\x1B[" + agentNames.length + "A\r");
        for (const n of agentNames) {
          process.stdout.write((statusLines.get(n) ?? "") + "\n");
        }
      }

      // Initial render
      for (const n of agentNames) process.stdout.write(chalk.dim(`  ○ [${n}] waiting...\n`));

      const result = await executeDag({
        stages,
        onProgress: (name, status) => {
          const icons: Record<StageStatus, string> = {
            pending: chalk.dim("○"),
            running: chalk.cyan("⠿"),
            complete: chalk.green("✓"),
            failed: chalk.red("✗"),
            skipped: chalk.dim("○"),
          };
          statusLines.set(name, `  ${icons[status] ?? "○"} [${chalk.bold(name)}] ${status}`);
          redraw();
        },
      });

      console.log();
      console.log(result.success
        ? chalk.bold.green("  ✓ All agents complete!\n")
        : chalk.bold.red("  ✗ Some agents failed\n")
      );

      for (const s of result.stages) {
        console.log(`  ${statusIcon(s.status)} ${chalk.bold(s.name)} ${chalk.dim(`(${s.durationMs}ms)`)}`);
        if (s.output) {
          const preview = s.output.slice(0, 200).replace(/\n/g, " ");
          console.log(chalk.dim(`    ${preview}${s.output.length > 200 ? "…" : ""}`));
        }
        if (s.error) console.log(chalk.red(`    Error: ${s.error}`));
      }
      console.log(chalk.dim(`\n  Total: ${result.totalDurationMs}ms\n`));
    });

  // bharatbuild crew dag --file pipeline.json
  cmd
    .command("dag")
    .description("Execute a DAG pipeline from a JSON file or inline definition")
    .option("--file <path>", "Path to JSON pipeline definition file")
    .option("--model <model>", "Default AI model for all stages")
    .action(async (opts) => {
      const config = loadConfig();
      let stages: DAGStage[];

      if (opts.file) {
        const fs = await import("fs");
        try {
          stages = JSON.parse(fs.readFileSync(opts.file as string, "utf8")) as DAGStage[];
        } catch (err) {
          console.error(chalk.red(`\n  ✗ Failed to load pipeline: ${err instanceof Error ? err.message : err}\n`));
          process.exit(1);
        }
      } else {
        console.log(chalk.bold("\n  DAG Pipeline Format (pipeline.json):\n"));
        console.log(JSON.stringify([
          { name: "plan", task: "Analyze and plan the feature", agent: "planner", depends_on: [] },
          { name: "code", task: "Implement the feature", agent: "coder", depends_on: ["plan"] },
          { name: "test", task: "Write and run tests", agent: "tester", depends_on: ["code"] },
          {
            name: "review",
            task: "Review the implementation",
            agent: "reviewer",
            depends_on: ["code"],
            loop_to: { target: "code", trigger: "NEEDS_CHANGES", max_iterations: 3 },
          },
        ], null, 2));
        console.log(chalk.dim("\n  Run: bharatbuild crew dag --file pipeline.json\n"));
        return;
      }

      // Apply model override
      if (opts.model) {
        stages = stages.map((s) => ({ ...s, model: s.model ?? (opts.model as string) }));
      }

      console.log(chalk.bold(`\n  ⚡ DAG Pipeline: ${stages.length} stages\n`));

      const result = await executeDag({
        stages,
        onProgress: (name, status, output) => {
          const icons: Record<StageStatus, string> = {
            pending: "○", running: "⠿", complete: "✓", failed: "✗", skipped: "○",
          };
          const icon = status === "complete" ? chalk.green("✓")
            : status === "failed" ? chalk.red("✗")
            : status === "running" ? chalk.cyan("⠿")
            : chalk.dim("○");
          console.log(`  ${icon} [${chalk.bold(name)}] ${status}`);
        },
      });

      console.log();
      for (const s of result.stages) {
        console.log(`  ${statusIcon(s.status)} ${chalk.bold(s.name.padEnd(16))} ${chalk.dim(`${s.durationMs}ms`)}${s.iterations ? chalk.dim(` (${s.iterations} iterations)`) : ""}`);
      }
      console.log(chalk.dim(`\n  Total: ${result.totalDurationMs}ms | ${result.success ? chalk.green("success") : chalk.red("failed")}\n`));
    });

  // bharatbuild crew pipeline <task> --stages "plan>code>test" (shorthand linear pipeline)
  cmd
    .command("pipeline <task>")
    .description("Run a linear pipeline: plan -> code -> test -> review with review loop")
    .option("--model <model>", "AI model to use")
    .option("--no-review", "Skip the reviewer stage")
    .action(async (task: string, opts) => {
      const config = loadConfig();
      const activeModel = (opts.model as string | undefined) ?? config.model ?? "auto";

      const stages: DAGStage[] = [
        { name: "plan",   task: `Plan the implementation for: ${task}`,           agent: "planner",  model: activeModel, depends_on: [] },
        { name: "code",   task: `Implement: ${task}`,                              agent: "coder",    model: activeModel, depends_on: ["plan"] },
        { name: "test",   task: `Write and run tests for: ${task}`,               agent: "tester",   model: activeModel, depends_on: ["code"] },
      ];

      if (opts.review !== false) {
        stages.push({
          name: "review",
          task: `Review the implementation and tests for: ${task}. If issues found, include 'NEEDS_CHANGES' and describe what to fix.`,
          agent: "reviewer",
          model: activeModel,
          depends_on: ["code"],
          loop_to: { target: "code", trigger: "NEEDS_CHANGES", max_iterations: 3 },
        });
      }

      console.log(chalk.bold(`\n  🔄 Pipeline: ${stages.map((s) => s.name).join(" → ")}\n`));

      const result = await executeDag({
        stages,
        onProgress: (name, status) => {
          if (status === "running") console.log(chalk.cyan(`\n  ⠿ Running [${name}]...`));
          if (status === "complete") console.log(chalk.green(`  ✓ [${name}] complete`));
          if (status === "failed") console.log(chalk.red(`  ✗ [${name}] failed`));
        },
      });

      console.log();
      result.success
        ? console.log(chalk.bold.green("  ✓ Pipeline complete!\n"))
        : console.log(chalk.bold.red("  ✗ Pipeline finished with failures\n"));

      console.log(chalk.dim(`  Total: ${result.totalDurationMs}ms\n`));
    });

  // bharatbuild crew list  — not needed anymore but kept for compat
  cmd.command("list").description("Show recent crew executions").action(() => {
    console.log(chalk.dim("\n  No persistent crew sessions in this version.\n"));
    console.log(chalk.dim("  Use: bharatbuild crew spawn <task>\n"));
    console.log(chalk.dim("       bharatbuild crew pipeline <task>\n"));
    console.log(chalk.dim("       bharatbuild crew dag --file pipeline.json\n"));
  });

  return cmd;
}