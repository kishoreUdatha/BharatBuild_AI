/** BharatBuild CLI - model command */
import chalk from "chalk";
import { loadConfig, saveConfig } from "../config/config.js";
import { MODEL_TIERS, resolveModel } from "../config/constants.js";

const MODELS = [
  { id: "auto",                       label: "Auto              ✦ best model selected per request (default)" },
  { id: MODEL_TIERS.haiku,            label: "Claude Haiku 4.5  — fast, cheap"          },
  { id: MODEL_TIERS.sonnet,           label: "Claude Sonnet 5   — balanced"             },
  { id: MODEL_TIERS.opus,             label: "Claude Opus 5     — most capable"         },
  { id: "gpt-4o",                     label: "GPT-4o            — OpenAI"               },
  { id: "gpt-4o-mini",                label: "GPT-4o Mini       — OpenAI fast"          },
  { id: "gemini-1.5-pro",             label: "Gemini 1.5 Pro    — Google"               },
  { id: "ollama/llama3",              label: "Llama 3 (Ollama)  — local"                },
];

export function modelCommand(modelId?: string): void {
  const config = loadConfig();
  if (!modelId) {
    console.log(chalk.bold("\n🤖 Available Models:\n"));
    for (const m of MODELS) {
      const isActive = m.id === (config.model ?? "auto");
      const marker = isActive ? chalk.green(" ✓ active") : "";
      console.log(`  ${chalk.cyan(m.id.padEnd(36))} ${m.label}${marker}`);
    }
    console.log(chalk.dim("\n  Usage: bharatbuild model <model-id>"));
    console.log(chalk.dim("  Tip:   \"auto\" dynamically picks the best model based on your prompt complexity.\n"));
    return;
  }

  // Accept tier aliases ("haiku"/"sonnet"/"opus") as well as full IDs, so the
  // shorthand shown in --help and shell completion actually works here.
  const resolved = resolveModel(modelId);
  const valid = MODELS.find((m) => m.id === resolved);
  if (!valid) {
    console.log(chalk.yellow(`\n⚠  Unknown model: ${modelId}`));
    console.log(chalk.dim("  Run 'bharatbuild model' to see available models.\n"));
    return;
  }

  saveConfig({ model: resolved });

  if (resolved === "auto") {
    console.log(chalk.green(`\n✓ Model set to: ${chalk.bold("auto")} — best model will be selected per request\n`));
  } else {
    console.log(chalk.green(`\n✓ Model set to: ${chalk.bold(resolved)}\n`));
  }
}