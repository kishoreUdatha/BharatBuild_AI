import { Command } from "commander";
import chalk from "chalk";
import { VoiceMode } from "../voice/voice-mode.js";
import { loadCredentials } from "../auth/credentials.js";
import { loadConfig } from "../config/config.js";
import { createModelClientAuto as createModelClient } from "../models/model-router.js";
import { resolveModel } from "../config/constants.js";

export function voiceCommand(): Command {
  return new Command("voice")
    .description("Start voice mode — speak to BharatBuild CLI")
    .option("--tts", "Enable text-to-speech for responses")
    .option("--language <lang>", "Speech language", "en")
    .action(async (opts) => {
      const creds = loadCredentials();
      const config = loadConfig();
      const model = createModelClient(resolveModel(config.model), creds?.token);
      console.log(chalk.bold("\n  🎙  BharatBuild Voice Mode\n"));
      const voice = new VoiceMode({
        tts: opts.tts,
        language: opts.language,
        onTranscription: async (text: string) => {
          let response = "";
          process.stdout.write(chalk.bold.cyan("\n  BharatBuild: "));
          for await (const chunk of model.complete({
            model: resolveModel(config.model),
            system: "You are BharatBuild CLI, an AI coding assistant. Give concise spoken responses.",
            messages: [{ role: "user", content: text }],
            tools: [], maxTokens: 500,
          })) {
            if (chunk.type === "text_delta" && chunk.text) { response += chunk.text; process.stdout.write(chunk.text); }
          }
          process.stdout.write("\n\n");
          return response;
        },
      });
      await voice.start();
      process.stdin.setRawMode?.(true);
      process.stdin.resume();
      process.stdin.on("data", (key: Buffer) => {
        const k = key.toString();
        if (k === "\x0f") voice.triggerRecording();
        if (k === "\x03") { voice.stop(); process.exit(0); }
      });
      await new Promise<void>((resolve) => { process.on("SIGINT", () => { voice.stop(); resolve(); }); });
    });
}

