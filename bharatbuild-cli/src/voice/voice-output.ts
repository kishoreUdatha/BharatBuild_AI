import { spawn } from "child_process";
import { execSync } from "child_process";

export interface TTSOptions { voice?: string; rate?: number; }

export async function speak(text: string, opts: TTSOptions = {}): Promise<void> {
  return new Promise((resolve) => {
    let child;
    const safe = text.replace(/'/g, "\\'");
    if (process.platform === "win32") {
      const script = `Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('${safe}');`;
      child = spawn("powershell", ["-Command", script], { stdio: "ignore" });
    } else if (process.platform === "darwin") {
      const args = [text];
      if (opts.voice) args.push("-v", opts.voice);
      if (opts.rate) args.push("-r", String(opts.rate));
      child = spawn("say", args, { stdio: "ignore" });
    } else {
      child = spawn("espeak", [text], { stdio: "ignore" });
    }
    child.on("close", resolve);
    child.on("error", () => resolve());
  });
}

export async function isTTSAvailable(): Promise<boolean> {
  const tools = process.platform === "win32" ? ["powershell"] : process.platform === "darwin" ? ["say"] : ["espeak", "festival"];
  for (const t of tools) { try { execSync(`${t} --version 2>&1`, { stdio: "pipe" }); return true; } catch {} }
  return false;
}
