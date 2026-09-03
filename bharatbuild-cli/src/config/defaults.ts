// BharatBuild CLI — Default configuration values

import {
  DEFAULT_API_BASE_URL, DEFAULT_MODEL, DEFAULT_TIMEOUT_MS,
  MAX_TURNS, SESSION_DIR, CHECKPOINT_DIR,
} from "./constants.js";

export interface CLIDefaults {
  apiBaseUrl:     string;
  model:          string;
  /**
   * "plan" is read-only: it refuses tools that write files or run commands.
   * It was missing here, so a configured or env-set plan mode fell through
   * checkPermission's final `return "allow"` and gated nothing outside the TUI.
   */
  permissionMode: "ask" | "auto" | "deny" | "plan";
  maxTurns:       number;
  timeoutMs:      number;
  sessionDir:     string;
  checkpointDir:  string;
  theme:          "dark" | "light" | "auto";
  verbose:        boolean;
  telemetry:      boolean;
  /**
   * Per-tool permission rules, checked before the global permissionMode.
   *
   * One mode for every tool could not express what people actually want —
   * "never touch the network, always confirm a shell command, edits are fine" —
   * so the choice was between being asked about everything and nothing.
   */
  permissions?: import("../permissions/rules.js").PermissionRules;
}

export const DEFAULTS: CLIDefaults = {
  apiBaseUrl:     DEFAULT_API_BASE_URL,
  model:          DEFAULT_MODEL,
  permissionMode: "ask",
  maxTurns:       MAX_TURNS,
  timeoutMs:      DEFAULT_TIMEOUT_MS,
  sessionDir:     SESSION_DIR,
  checkpointDir:  CHECKPOINT_DIR,
  theme:          "auto",
  verbose:        false,
  telemetry:      true,
};

