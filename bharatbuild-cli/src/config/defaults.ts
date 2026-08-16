// BharatBuild CLI — Default configuration values

import {
  DEFAULT_API_BASE_URL, DEFAULT_MODEL, DEFAULT_TIMEOUT_MS,
  MAX_TURNS, SESSION_DIR, CHECKPOINT_DIR,
} from "./constants.js";

export interface CLIDefaults {
  apiBaseUrl:     string;
  model:          string;
  permissionMode: "ask" | "auto" | "deny";
  maxTurns:       number;
  timeoutMs:      number;
  sessionDir:     string;
  checkpointDir:  string;
  theme:          "dark" | "light" | "auto";
  verbose:        boolean;
  telemetry:      boolean;
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

