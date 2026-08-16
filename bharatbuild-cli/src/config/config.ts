// BharatBuild CLI — Config manager
// Reads/writes ~/.bharatbuild/config.json + env vars

import fs from "fs";
import os from "os";
import path from "path";
import { DEFAULTS, CLIDefaults } from "./defaults.js";

export interface CLIConfig extends CLIDefaults {
  // auth (populated after login)
  authToken?:    string;
  userId?:       string;
  userEmail?:    string;
  userName?:     string;
  userTier?:     string;

  // runtime overrides
  workingDir:    string;
  nonInteractive: boolean;
}

const CONFIG_DIR  = path.join(os.homedir(), ".bharatbuild");
const CONFIG_PATH = path.join(CONFIG_DIR, "config.json");

function ensureDir(): void {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
}

function loadFromDisk(): Partial<CLIConfig> {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
    }
  } catch { /* ignore */ }
  return {};
}

function loadFromEnv(): Partial<CLIConfig> {
  const env: Partial<CLIConfig> = {};
  if (process.env.BHARATBUILD_API_URL)   env.apiBaseUrl     = process.env.BHARATBUILD_API_URL;
  if (process.env.BHARATBUILD_MODEL)     env.model          = process.env.BHARATBUILD_MODEL;
  if (process.env.BHARATBUILD_TOKEN)     env.authToken      = process.env.BHARATBUILD_TOKEN;
  if (process.env.BHARATBUILD_VERBOSE)   env.verbose        = process.env.BHARATBUILD_VERBOSE === "true";
  if (process.env.BHARATBUILD_MODE)      env.permissionMode = process.env.BHARATBUILD_MODE as any;
  return env;
}

export function loadConfig(): CLIConfig {
  const disk = loadFromDisk();
  const env  = loadFromEnv();
  return {
    ...DEFAULTS,
    workingDir:     process.cwd(),
    nonInteractive: false,
    ...disk,
    ...env,
  };
}

export function saveConfig(config: Partial<CLIConfig>): void {
  ensureDir();
  const existing = loadFromDisk();
  // never persist runtime-only fields
  const { workingDir, nonInteractive, ...saveable } = { ...existing, ...config } as any;
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(saveable, null, 2));
}

export function getConfigDir(): string {
  ensureDir();
  return CONFIG_DIR;
}
