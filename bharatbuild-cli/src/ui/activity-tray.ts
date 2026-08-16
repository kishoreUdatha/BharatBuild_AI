import chalk from "chalk";
import { getTheme } from "./theme.js";

export interface ActivityItem {
  id: string;
  label: string;
  status: "running" | "done" | "failed" | "pending";
  durationMs?: number;
}

export class ActivityTray {
  private items: ActivityItem[] = [];
  private visible = false;

  add(item: ActivityItem): void {
    this.items = this.items.filter((i) => i.id !== item.id);
    this.items.push(item);
  }

  update(id: string, updates: Partial<ActivityItem>): void {
    const item = this.items.find((i) => i.id === id);
    if (item) Object.assign(item, updates);
  }

  toggle(): void {
    this.visible = !this.visible;
    if (this.visible) this.render();
    else console.log(chalk.dim("  [Activity tray hidden]"));
  }

  render(): void {
    const t = getTheme();
    if (this.items.length === 0) {
      console.log(t.dim("\n  📋 Activity Tray — No active tasks\n"));
      return;
    }
    console.log(t.heading("\n  📋 Activity Tray\n"));
    for (const item of this.items.slice(-10)) {
      const icon =
        item.status === "running" ? t.warning("⠋") :
        item.status === "done" ? t.success("✓") :
        item.status === "failed" ? t.error("✗") : t.dim("○");
      const dur = item.durationMs ? t.dim(` (${item.durationMs}ms)`) : "";
      console.log(`  ${icon} ${item.label}${dur}`);
    }
    console.log();
  }

  isVisible(): boolean { return this.visible; }
}
