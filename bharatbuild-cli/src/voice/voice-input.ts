import { spawn, type ChildProcess } from "child_process";
import { execSync } from "child_process";
import { EventEmitter } from "events";
import fs from "fs";

export interface VoiceInputOptions {
  language?: string;
  silenceThresholdMs?: number;
}

export class VoiceInput extends EventEmitter {
  private proc: ChildProcess | null = null;
  private recording = false;

  static async isAvailable(): Promise<boolean> {
    const tools = ["whisper", "sox", "arecord"];
    for (const tool of tools) {
      try { execSync(`${tool} --version 2>&1`, { stdio: "pipe" }); return true; } catch {}
    }
    return process.platform === "win32"; // Windows has built-in speech
  }

  startRecording(opts: VoiceInputOptions = {}): void {
    if (this.recording) return;
    this.recording = true;
    this.emit("start");
    if (process.platform === "win32") this._recordWindows();
    else if (process.platform === "darwin") this._recordMac(opts);
    else this._recordLinux();
  }

  private _recordWindows() {
    const script = `Add-Type -AssemblyName System.Speech; $r = New-Object System.Speech.Recognition.SpeechRecognitionEngine; $r.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar)); $r.SetInputToDefaultAudioDevice(); $result = $r.Recognize([TimeSpan]::FromSeconds(10)); if ($result) { Write-Output $result.Text } else { Write-Output "" }`;
    this.proc = spawn("powershell", ["-Command", script], { stdio: ["ignore", "pipe", "ignore"] });
    let output = "";
    this.proc.stdout?.on("data", (d: Buffer) => { output += d.toString(); });
    this.proc.on("close", () => { this.recording = false; const text = output.trim(); if (text) this.emit("transcription", text); this.emit("stop"); });
  }

  private _recordMac(opts: VoiceInputOptions) {
    const tmpFile = `/tmp/bharatbuild-voice-${Date.now()}.wav`;
    this.proc = spawn("sox", ["-d", "-r", "16000", "-c", "1", tmpFile, "silence", "1", "0.1", "3%", "1", String((opts.silenceThresholdMs ?? 2000) / 1000), "3%"], { stdio: "ignore" });
    this.proc.on("close", async () => { this.recording = false; const text = await this._transcribe(tmpFile); try { fs.unlinkSync(tmpFile); } catch {} if (text) this.emit("transcription", text); this.emit("stop"); });
  }

  private _recordLinux() {
    const tmpFile = `/tmp/bharatbuild-voice-${Date.now()}.wav`;
    this.proc = spawn("arecord", ["-f", "cd", "-t", "wav", "-d", "10", tmpFile], { stdio: "ignore" });
    this.proc.on("close", async () => { this.recording = false; const text = await this._transcribe(tmpFile); try { fs.unlinkSync(tmpFile); } catch {} if (text) this.emit("transcription", text); this.emit("stop"); });
  }

  private async _transcribe(audioFile: string): Promise<string | null> {
    try {
      const txtFile = audioFile.replace(".wav", ".txt");
      execSync(`whisper "${audioFile}" --model tiny --output_format txt --output_dir /tmp 2>/dev/null`);
      if (fs.existsSync(txtFile)) { const text = fs.readFileSync(txtFile, "utf8").trim(); try { fs.unlinkSync(txtFile); } catch {} return text; }
    } catch {}
    return null;
  }

  stopRecording(): void {
    if (!this.recording) return;
    this.proc?.kill("SIGTERM");
    this.proc = null; this.recording = false; this.emit("stop");
  }

  isRecording(): boolean { return this.recording; }
}
