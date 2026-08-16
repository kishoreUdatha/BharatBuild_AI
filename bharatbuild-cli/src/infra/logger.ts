import fs from "fs";
import path from "path";
import os from "os";

export type LogLevel = "error" | "warn" | "info" | "debug" | "trace";
const LEVELS: Record<LogLevel, number> = { error:0, warn:1, info:2, debug:3, trace:4 };

function getLogPath(): string {
  const custom = process.env["BHARATBUILD_CHAT_LOG_FILE"];
  if (custom) return custom;
  const base = process.platform === "win32"
    ? path.join(process.env["TEMP"] ?? os.tmpdir(), "bharatbuild-log")
    : process.platform === "darwin"
    ? path.join(process.env["TMPDIR"] ?? os.tmpdir(), "bharatbuild-log")
    : path.join(process.env["XDG_RUNTIME_DIR"] ?? "/tmp", "bharatbuild-log");
  return path.join(base, "bharatbuild-chat.log");
}

function getLevel(): LogLevel {
  return (process.env["BHARATBUILD_LOG_LEVEL"] as LogLevel) ?? "error";
}

class Logger {
  private logPath = getLogPath();
  private level = getLevel();
  private noColor = !!process.env["BHARATBUILD_LOG_NO_COLOR"];

  private write(level: LogLevel, msg: string, meta?: unknown) {
    if (LEVELS[level] > LEVELS[this.level]) return;
    const line = JSON.stringify({ ts: new Date().toISOString(), level, msg, ...(meta ? { meta } : {}) });
    try { fs.mkdirSync(path.dirname(this.logPath), { recursive: true }); fs.appendFileSync(this.logPath, line + "\n"); } catch {}
  }

  error(msg: string, meta?: unknown) { this.write("error", msg, meta); }
  warn(msg: string, meta?: unknown) { this.write("warn", msg, meta); }
  info(msg: string, meta?: unknown) { this.write("info", msg, meta); }
  debug(msg: string, meta?: unknown) { this.write("debug", msg, meta); }
  trace(msg: string, meta?: unknown) { this.write("trace", msg, meta); }
  getLogPath() { return this.logPath; }
}

export const logger = new Logger();
