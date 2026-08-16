import { spawn } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";

export interface TranscriptMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export function formatTranscript(messages: TranscriptMessage[]): string {
  return messages.map((m) => {
    const ts = new Date(m.timestamp).toLocaleTimeString();
    const prefix = m.role === "user" ? "You" : "BharatBuild";
    return `[${ts}] ${prefix}:\n${m.content}\n`;
  }).join("\n" + "─".repeat(60) + "\n\n");
}

export async function openTranscript(messages: TranscriptMessage[]): Promise<void> {
  const content = formatTranscript(messages);
  const tmpFile = path.join(os.tmpdir(), `bharatbuild-transcript-${Date.now()}.txt`);
  fs.writeFileSync(tmpFile, content, "utf8");
  const pager = process.env["PAGER"] ?? (process.platform === "win32" ? "more" : "less");
  return new Promise((resolve) => {
    const child = spawn(pager, [tmpFile], { stdio: "inherit" });
    child.on("close", () => { try { fs.unlinkSync(tmpFile); } catch {} resolve(); });
    child.on("error", () => resolve());
  });
}
