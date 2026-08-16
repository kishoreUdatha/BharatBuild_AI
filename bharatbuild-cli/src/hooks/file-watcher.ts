import fs from "fs";
import path from "path";
import { EventEmitter } from "events";

export interface FileChangeEvent {
  type: "created" | "modified" | "deleted";
  filePath: string;
  timestamp: Date;
}

export class FileWatcher extends EventEmitter {
  private watchers: Map<string, fs.FSWatcher> = new Map();
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();
  private debounceMs: number;

  constructor(debounceMs = 300) {
    super();
    this.debounceMs = debounceMs;
  }

  watch(dir: string, patterns: string[] = ["**/*"]) {
    const ignored = ["node_modules", ".git", "dist", "build", ".bharatbuild"];
    this._watchDir(dir, ignored);
  }

  private _watchDir(dir: string, ignored: string[]) {
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (ignored.includes(entry.name)) continue;
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          this._watchDir(full, ignored);
        } else {
          const watcher = fs.watch(full, (eventType) => {
            this._debounce(full, () => {
              const exists = fs.existsSync(full);
              this.emit("change", {
                type: eventType === "rename" ? (exists ? "created" : "deleted") : "modified",
                filePath: full,
                timestamp: new Date(),
              } as FileChangeEvent);
            });
          });
          this.watchers.set(full, watcher);
        }
      }
    } catch {}
  }

  private _debounce(key: string, fn: () => void) {
    const existing = this.debounceTimers.get(key);
    if (existing) clearTimeout(existing);
    this.debounceTimers.set(key, setTimeout(() => { fn(); this.debounceTimers.delete(key); }, this.debounceMs));
  }

  stop() {
    for (const w of this.watchers.values()) w.close();
    this.watchers.clear();
    for (const t of this.debounceTimers.values()) clearTimeout(t);
    this.debounceTimers.clear();
  }
}
