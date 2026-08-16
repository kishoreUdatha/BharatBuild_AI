import chalk from "chalk";
import { getTheme } from "./theme.js";

export interface ToolOutputEntry {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  output: string;
  isError: boolean;
  durationMs: number;
  collapsed: boolean;
}

const MAX_COLLAPSED_LINES = 3;

export class ToolOutputManager {
  private entries: Map<string, ToolOutputEntry> = new Map();

  add(entry: ToolOutputEntry): void {
    this.entries.set(entry.id, entry);
    this.render(entry);
  }

  toggleCollapse(id: string): void {
    const entry = this.entries.get(id);
    if (!entry) return;
    entry.collapsed = !entry.collapsed;
    this.render(entry);
  }

  toggleLast(): void {
    const last = Array.from(this.entries.values()).pop();
    if (last) this.toggleCollapse(last.id);
  }

  getAll(): ToolOutputEntry[] {
    return Array.from(this.entries.values());
  }

  private render(entry: ToolOutputEntry): void {
    const t = getTheme();
    const icon = entry.isError ? t.error("✗") : t.success("✓");
    const title = `${icon} ${t.tool(entry.toolName)} ${t.dim("(" + entry.durationMs + "ms)")}`;
    console.log(`\n  ${title}`);
    if (entry.output) {
      const lines = entry.output.split("\n").filter(Boolean);
      const display = entry.collapsed ? lines.slice(0, MAX_COLLAPSED_LINES) : lines;
      for (const line of display) {
        console.log(t.dim(`  │ ${line.slice(0, process.stdout.columns ?? 80 - 6)}`));
      }
      if (entry.collapsed && lines.length > MAX_COLLAPSED_LINES) {
        console.log(t.dim(`  │ ... (${lines.length - MAX_COLLAPSED_LINES} more lines) — Ctrl+O to expand`));
      } else if (!entry.collapsed && lines.length > MAX_COLLAPSED_LINES) {
        console.log(t.dim(`  │ (Ctrl+O to collapse)`));
      }
    }
  }
}
