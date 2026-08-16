import fs from "fs";
import path from "path";

export type HookEvent = "file-saved" | "file-created" | "file-deleted" | "git-commit" | "git-push" | "build-complete" | "test-complete";

export interface HookDefinition {
  id: string;
  name: string;
  event: HookEvent;
  pattern?: string;       // glob pattern for file-based events
  agent?: string;         // which agent to trigger
  prompt?: string;        // prompt template
  enabled: boolean;
}

export interface HooksConfig {
  hooks: HookDefinition[];
}

const DEFAULT_CONFIG: HooksConfig = { hooks: [] };

export function loadHooksConfig(dir?: string): HooksConfig {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "hooks.json");
  try {
    if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, "utf8")) as HooksConfig;
  } catch {}
  return DEFAULT_CONFIG;
}

export function saveHooksConfig(config: HooksConfig, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "hooks.json");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, JSON.stringify(config, null, 2));
}

export function addHook(hook: HookDefinition, dir?: string) {
  const config = loadHooksConfig(dir);
  config.hooks = config.hooks.filter((h) => h.id !== hook.id);
  config.hooks.push(hook);
  saveHooksConfig(config, dir);
}

export function removeHook(id: string, dir?: string) {
  const config = loadHooksConfig(dir);
  config.hooks = config.hooks.filter((h) => h.id !== id);
  saveHooksConfig(config, dir);
}
