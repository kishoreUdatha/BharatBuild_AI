import chalk from "chalk";
import { VoiceInput, type VoiceInputOptions } from "./voice-input.js";
import { speak, isTTSAvailable } from "./voice-output.js";
import { getTheme } from "../ui/theme.js";

export interface VoiceModeOptions {
  tts?: boolean;
  language?: string;
  onTranscription: (text: string) => Promise<string>;
}

export class VoiceMode {
  private input = new VoiceInput();
  private opts: VoiceModeOptions;
  private active = false;

  constructor(opts: VoiceModeOptions) { this.opts = opts; }

  async start(): Promise<void> {
    const t = getTheme();
    const available = await VoiceInput.isAvailable();
    if (!available) {
      console.log(t.warning("\n  ⚠  Voice input requires: whisper (pip install openai-whisper) + sox/arecord\n"));
      console.log(t.dim("  macOS: brew install sox && pip install openai-whisper\n"));
      console.log(t.dim("  Linux: apt install sox arecord && pip install openai-whisper\n"));
      return;
    }
    this.active = true;
    console.log(t.success("\n  🎙  Voice mode active. Press Ctrl+O to record, Ctrl+C to exit.\n"));
    this.input.on("start", () => { process.stdout.write(chalk.magenta("\r  🔴 Recording... (speak now)   ")); });
    this.input.on("transcription", async (text: string) => {
      console.log(chalk.bold.green("\n\n  You (voice): ") + text);
      try {
        const response = await this.opts.onTranscription(text);
        if (this.opts.tts && await isTTSAvailable()) await speak(response);
      } catch (err) { console.log(chalk.red(`\n  ✗ ${err instanceof Error ? err.message : err}\n`)); }
    });
    this.input.on("stop", () => {
      if (this.active) process.stdout.write(chalk.dim("\r  🎙  Ready. Press Ctrl+O to record.   \n"));
    });
  }

  triggerRecording(): void {
    if (this.input.isRecording()) this.input.stopRecording();
    else this.input.startRecording({ language: this.opts.language });
  }

  stop(): void { this.active = false; this.input.stopRecording(); console.log(chalk.dim("\n  Voice mode stopped.\n")); }
}
