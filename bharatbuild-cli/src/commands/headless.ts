import chalk from "chalk";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto as createModelClient } from "../models/model-router.js";
import { resolveModel } from "../config/constants.js";

export interface HeadlessOptions {
  input: string;
  trustAllTools?: boolean;
  agent?: string;
  effort?: string;
  format?: string;
}

export async function runHeadless(opts: HeadlessOptions): Promise<void> {
  const creds = loadCredentials();
  const config = loadConfig();
  const model = createModelClient(resolveModel(config.model), creds?.token);
  let output = "";
  for await (const chunk of model.complete({
    model: resolveModel(config.model),
    system: "You are BharatBuild CLI, an AI coding assistant. Be concise and direct.",
    messages: [{ role: "user", content: opts.input }],
    tools: [],
    maxTokens: 4096,
  })) {
    if (chunk.type === "text_delta" && chunk.text) {
      output += chunk.text;
      if (opts.format !== "json") process.stdout.write(chunk.text);
    }
  }
  if (opts.format === "json") console.log(JSON.stringify({ output, model: config.model }));
  else process.stdout.write("\n");
}

