/**
 * BharatBuild CLI - plan command
 * Generate a step-by-step plan for a task without executing it.
 * Uses auto model selection by default.
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { Spinner } from "../ui/spinner.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto, isAutoModel } from "../models/model-router.js";
import { AGENTIC_CHAT_STREAM } from "../api/endpoints.js";

export async function planCommand(
  goal: string | undefined,
  opts: { model?: string },
  client: BharatBuildClient
): Promise<void> {
  if (!goal) {
    console.error(chalk.red('\n  Usage: bharatbuild plan "add JWT authentication"\n'));
    process.exit(1);
  }

  const config = loadConfig();
  const activeModel = opts.model ?? config.model ?? "auto";
  const usingAuto = isAutoModel(activeModel);

  const spinner = new Spinner();
  spinner.start(`Planning… ${chalk.dim(usingAuto ? "[auto model]" : `[${activeModel}]`)}`);

  const planPrompt = `Create a detailed, step-by-step implementation plan for:\n\n${goal}\n\nList concrete steps with:\n- File(s) to create or modify\n- What changes to make\n- Any dependencies or prerequisites\n\nDo NOT write code yet — just plan.`;

  try {
    const hasDirectKey =
      process.env["ANTHROPIC_API_KEY"] ||
      process.env["OPENAI_API_KEY"] ||
      process.env["GEMINI_API_KEY"] ||
      process.env["GOOGLE_API_KEY"];

    spinner.stop();
    console.log(chalk.bold(`\n📋 Plan for: ${goal}\n`));

    if (hasDirectKey) {
      const modelClient = createModelClientAuto(activeModel);
      for await (const chunk of modelClient.complete({
        model: activeModel,
        system: "You are a senior software architect. Create clear, actionable implementation plans.",
        messages: [{ role: "user", content: planPrompt }],
        tools: [],
        maxTokens: 4096,
      })) {
        if (chunk.type === "text_delta" && chunk.text) process.stdout.write(chunk.text);
      }
    } else {
      const stream = client.streamSSE(AGENTIC_CHAT_STREAM, {
        model: usingAuto ? "auto" : activeModel,
        messages: [{ role: "user", content: planPrompt }],
        max_tokens: 4096,
      });
      for await (const event of stream) {
        // See ask.ts: the payload is the event, there is no .data wrapper.
        const e = event as unknown as Record<string, unknown>;
        if (event.type === "text" || event.type === "text_delta") process.stdout.write(String(e["text"] ?? e["content"] ?? ""));
        else if (event.type === "error") throw new Error(String(e["message"] ?? e["error"] ?? "stream error"));
        else if (event.type === "complete" || event.type === "done") break;
      }
    }

    console.log("\n");
  } catch (err) {
    spinner.fail();
    console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : err}\n`));
    process.exit(1);
  }
}