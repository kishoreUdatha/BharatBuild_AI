/**
 * BharatBuild CLI - ask command
 * Single-shot question, no tool use, prints answer and exits.
 * Uses auto model selection by default.
 */
import chalk from "chalk";
import { BharatBuildClient } from "../api/client.js";
import { Spinner } from "../ui/spinner.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto, isAutoModel } from "../models/model-router.js";
import { loadCredentials } from "../auth/credentials.js";
import { AGENTIC_CHAT_STREAM } from "../api/endpoints.js";

export async function askCommand(
  question: string,
  opts: { model?: string },
  client: BharatBuildClient
): Promise<void> {
  if (!question.trim()) {
    console.error(chalk.red("  Please provide a question.\n"));
    process.exit(1);
  }

  const config = loadConfig();
  const creds = loadCredentials();
  const activeModel = opts.model ?? config.model ?? "auto";
  const usingAuto = isAutoModel(activeModel);

  const spinner = new Spinner();
  spinner.start(`Thinking… ${chalk.dim(usingAuto ? "[auto model]" : `[${activeModel}]`)}`);

  try {
    const hasDirectKey =
      process.env["ANTHROPIC_API_KEY"] ||
      process.env["OPENAI_API_KEY"] ||
      process.env["GEMINI_API_KEY"] ||
      process.env["GOOGLE_API_KEY"];

    spinner.stop();
    console.log();

    if (hasDirectKey) {
      // Use direct provider via auto-selector
      const modelClient = createModelClientAuto(activeModel);
      for await (const chunk of modelClient.complete({
        model: activeModel,
        system: "You are BharatBuild AI, an expert software engineer assistant. Answer concisely and accurately.",
        messages: [{ role: "user", content: question }],
        tools: [],
        maxTokens: 4096,
      })) {
        if (chunk.type === "text_delta" && chunk.text) process.stdout.write(chunk.text);
      }
    } else {
      // Route through backend
      const stream = client.streamSSE(AGENTIC_CHAT_STREAM, {
        model: usingAuto ? "auto" : activeModel,
        messages: [{ role: "user", content: question }],
        max_tokens: 4096,
        stream: true,
      });
      for await (const event of stream) {
        // streamSSE yields the parsed payload itself, not an {type, data}
        // envelope. Reading event.data gave undefined, so the first text chunk
        // threw "Cannot read properties of undefined (reading 'content')".
        const e = event as unknown as Record<string, unknown>;
        if (event.type === "text" || event.type === "text_delta") {
          process.stdout.write(String(e["text"] ?? e["content"] ?? ""));
        } else if (event.type === "error") {
          throw new Error(String(e["message"] ?? e["error"] ?? "stream error"));
        } else if (event.type === "complete" || event.type === "done") {
          break;
        }
      }
    }

    console.log("\n");
  } catch (err) {
    spinner.fail();
    console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : err}\n`));
    process.exit(1);
  }
}