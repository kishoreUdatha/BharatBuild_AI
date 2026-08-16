import { isDangerousCommand } from "./dangerous-command.js";
export type PolicyResult="allow"|"deny"|"require_approval";
export function evaluateCommandPolicy(command: string, mode: "ask"|"auto"|"deny"): PolicyResult {
  if (isDangerousCommand(command)) return mode==="auto"?"deny":"require_approval";
  if (mode==="deny") return "deny"; return "allow";
}
