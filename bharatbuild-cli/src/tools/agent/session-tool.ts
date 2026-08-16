import { loadConfig, saveConfig, type CLIConfig } from "../../config/config.js";

export interface SessionOverride { key: keyof CLIConfig; value: unknown; original: unknown; }
const overrides: SessionOverride[] = [];

export function sessionSet(key: keyof CLIConfig, value: unknown): SessionOverride {
  const config = loadConfig();
  const original = config[key];
  (config as unknown as Record<string, unknown>)[key] = value;
  saveConfig(config);
  const override = { key, value, original };
  overrides.push(override);
  return override;
}

export function sessionGet(key: keyof CLIConfig): unknown {
  return loadConfig()[key];
}

export function sessionList(): SessionOverride[] { return overrides; }

export function sessionReset(key?: keyof CLIConfig): void {
  const config = loadConfig();
  if (key) {
    const o = overrides.find((ov) => ov.key === key);
    if (o) { (config as unknown as Record<string, unknown>)[key] = o.original; saveConfig(config); }
  } else {
    for (const o of overrides) { (config as unknown as Record<string, unknown>)[o.key] = o.original; }
    saveConfig(config); overrides.length = 0;
  }
}
