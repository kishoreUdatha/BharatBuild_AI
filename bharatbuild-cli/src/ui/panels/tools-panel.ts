import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface ToolPermission {
  tool: string;
  status: "allowed" | "denied" | "ask";
}

export function renderToolsPanel(permissions: ToolPermission[]): void {
  const t = getTheme();
  console.log(t.heading("\n  🔧 Tool Permissions\n"));
  if (permissions.length === 0) {
    console.log(t.dim("  No tool permissions set. All tools use default policy.\n"));
    return;
  }
  for (const p of permissions) {
    const icon = p.status === "allowed" ? t.success("✓") : p.status === "denied" ? t.error("✗") : t.warning("?");
    console.log(`  ${icon} ${t.tool(p.tool.padEnd(30))} ${t.dim(p.status)}`);
  }
  console.log(t.dim("\n  /tools reset  — clear all runtime permissions\n"));
}
