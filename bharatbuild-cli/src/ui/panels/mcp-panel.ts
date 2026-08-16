import chalk from "chalk";
import { getTheme } from "../theme.js";

export interface MCPServerStatus {
  name: string;
  connected: boolean;
  tools: number;
}

export function renderMCPPanel(servers: MCPServerStatus[]): void {
  const t = getTheme();
  console.log(t.heading("\n  🔌 MCP Servers\n"));
  if (servers.length === 0) {
    console.log(t.dim("  No MCP servers configured. Add servers in .bharatbuild/mcp.json\n"));
    return;
  }
  for (const s of servers) {
    const icon = s.connected ? t.success("●") : t.error("○");
    console.log(`  ${icon} ${t.tool(s.name.padEnd(25))} ${t.dim(s.connected ? `${s.tools} tools` : "disconnected")}`);
  }
  console.log();
}
