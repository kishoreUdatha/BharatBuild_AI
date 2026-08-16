import chalk from "chalk";
import { crewManager } from "./crew-manager.js";
import type { CrewAgent, CrewSession } from "./crew-types.js";

let monitorInterval: NodeJS.Timeout | null = null;
let visible = false;

export function openCrewMonitor(sessionId?: string): void {
  visible = true;
  const sessions = sessionId ? [crewManager.getSession(sessionId)].filter(Boolean) as CrewSession[] : crewManager.listSessions();
  if (sessions.length === 0) { console.log(chalk.dim("\n  No active crew sessions. Use: bharatbuild crew spawn <task>\n")); return; }
  const render = () => {
    if (!visible) { if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; } return; }
    process.stdout.write("\x1B[2J\x1B[H");
    console.log(chalk.bold.cyan("\n  ┌────────── Crew Monitor (Ctrl+G to close) ──────────┐\n"));
    for (const session of sessions) {
      console.log(chalk.bold(`  📋 ${session.title}  `) + chalk.dim(`[${session.id.slice(0,8)}]`) + "  " + badge(session.status) + "\n");
      for (const agent of session.agents) renderAgent(agent);
      console.log();
    }
    console.log(chalk.dim("  └────────────────────────────────────────────────────┘\n"));
  };
  render();
  monitorInterval = setInterval(render, 500);
}

function renderAgent(a: CrewAgent) {
  const icons: Record<string, string> = { idle: chalk.dim("○"), running: chalk.yellow("⠋"), complete: chalk.green("✓"), failed: chalk.red("✗") };
  const icon = icons[a.status] ?? "○";
  const dur = a.startedAt && a.completedAt ? chalk.dim(` (${Math.round((new Date(a.completedAt).getTime() - new Date(a.startedAt).getTime()) / 1000)}s)`) : a.startedAt ? chalk.dim(" (running...)") : "";
  console.log(`  ${icon} ${chalk.bold(a.name.padEnd(14))} ${chalk.dim(a.role.padEnd(10))} ${a.task ? chalk.dim(a.task.slice(0, 35)) : ""}${dur}`);
}

function badge(status: string): string {
  const b: Record<string, string> = { active: chalk.cyan("ACTIVE"), complete: chalk.green("COMPLETE"), failed: chalk.red("FAILED") };
  return b[status] ?? chalk.dim(status);
}

export function closeCrewMonitor(): void { visible = false; if (monitorInterval) { clearInterval(monitorInterval); monitorInterval = null; } }
