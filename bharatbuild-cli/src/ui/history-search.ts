import readline from "readline";
import chalk from "chalk";

export class HistorySearch {
  private history: string[];
  private navIndex = -1; // -1 = current line (not navigating)
  private savedLine = ""; // what was typed before navigating

  constructor(history: string[]) {
    this.history = history;
  }

  add(entry: string): void {
    if (!entry.trim()) return;
    // Remove duplicate and prepend
    const idx = this.history.indexOf(entry);
    if (idx !== -1) this.history.splice(idx, 1);
    this.history.unshift(entry);
    if (this.history.length > 1000) this.history.pop();
    this.navIndex = -1;
  }

  /**
   * Navigate to previous (older) history entry.
   * Call with the current line buffer so we can save it.
   */
  prev(currentLine: string): string | null {
    if (this.history.length === 0) return null;
    if (this.navIndex === -1) {
      this.savedLine = currentLine;
    }
    const next = Math.min(this.navIndex + 1, this.history.length - 1);
    if (next === this.navIndex) return null;
    this.navIndex = next;
    return this.history[this.navIndex] ?? null;
  }

  /**
   * Navigate to next (newer) history entry, or return to saved line.
   */
  next(): string | null {
    if (this.navIndex <= 0) {
      this.navIndex = -1;
      return this.savedLine;
    }
    this.navIndex--;
    return this.history[this.navIndex] ?? null;
  }

  /**
   * Reset navigation state (call after submitting a line).
   */
  resetNav(): void {
    this.navIndex = -1;
    this.savedLine = "";
  }

  /**
   * Interactive reverse history search (Ctrl+R).
   * Temporarily disables raw mode, shows a search prompt, returns the match.
   */
  async interactiveSearch(): Promise<string | null> {
    return new Promise((resolve) => {
      let query = "";
      let match: string | null = null;

      const redraw = () => {
        match = this.history.find((h) => h.includes(query)) ?? null;
        process.stdout.write(
          "\r\x1b[2K" +
          chalk.dim(`  (reverse-i-search) \`${query}\`: `) +
          chalk.cyan(match ?? "")
        );
      };

      process.stdout.write("\n");
      redraw();

      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

      rl.on("line", () => {
        rl.close();
        resolve(match);
      });

      rl.on("close", () => resolve(match));

      // We can't intercept keystrokes through readline easily here,
      // so use a simple "type query then Enter" approach
      rl.on("line", (line) => {
        query = line.trim();
        redraw();
      });
    });
  }

  getAll(): string[] {
    return [...this.history];
  }

  /** @deprecated use interactiveSearch() */
  async search(): Promise<string | null> {
    return this.interactiveSearch();
  }
}
