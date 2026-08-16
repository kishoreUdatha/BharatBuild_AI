import type { FileChangeEvent } from "./file-watcher.js";
import { loadHooksConfig, type HookDefinition, type HookEvent } from "./hook-config.js";
import { minimatch } from "minimatch";

export interface HookContext {
  event: HookEvent;
  filePath?: string;
  payload?: Record<string, unknown>;
}

export type HookHandler = (hook: HookDefinition, ctx: HookContext) => Promise<void>;

export class HookRunner {
  private handler: HookHandler;
  private dir: string;

  constructor(handler: HookHandler, dir?: string) {
    this.handler = handler;
    this.dir = dir ?? process.cwd();
  }

  async runForFileChange(change: FileChangeEvent) {
    const event: HookEvent =
      change.type === "created" ? "file-created" :
      change.type === "deleted" ? "file-deleted" : "file-saved";
    const config = loadHooksConfig(this.dir);
    const matching = config.hooks.filter((h) => {
      if (!h.enabled) return false;
      if (h.event !== event) return false;
      if (h.pattern && !minimatch(change.filePath, h.pattern)) return false;
      return true;
    });
    for (const hook of matching) {
      await this.handler(hook, { event, filePath: change.filePath });
    }
  }

  async runForEvent(event: HookEvent, payload?: Record<string, unknown>) {
    const config = loadHooksConfig(this.dir);
    const matching = config.hooks.filter((h) => h.enabled && h.event === event);
    for (const hook of matching) {
      await this.handler(hook, { event, payload });
    }
  }
}
