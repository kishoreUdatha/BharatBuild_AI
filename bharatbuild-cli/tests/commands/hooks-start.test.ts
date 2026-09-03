/**
 * Hooks have to start whichever way you entered the chat.
 *
 * `hooksRuntime.start()` was called from the bare `bharatbuild` action only,
 * so the file watcher and git hooks ran or did not run depending on whether
 * you typed `bharatbuild` or `bharatbuild chat` — the same session either way,
 * with nothing on screen explaining the difference.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const SRC = path.resolve(__dirname, "../../src");
const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), "utf8");

describe("where hooks are started", () => {
  it("starts inside the chat command", () => {
    expect(read("commands/chat.ts")).toMatch(/hooksRuntime\.start\(/);
  });

  it("is not also started by the default action", () => {
    // Two call sites on a module-level singleton is how the watcher ends up
    // with two "change" listeners and every hook fires twice.
    expect(read("index.ts")).not.toMatch(/hooksRuntime\.start\(/);
  });

  it("stops when the session ends", () => {
    // An active fs.watch keeps the event loop alive, so the process would
    // linger after the UI had gone.
    expect(read("commands/chat.ts")).toMatch(/hooksRuntime\.stop\(\)/);
  });
});

describe("starting twice is harmless", () => {
  it("returns early when already active", async () => {
    // Defends the singleton against a second entry point being added later.
    const { HooksRuntime } = await import("../../src/hooks/hooks-runtime.js");
    const rt = new HooksRuntime();
    expect(rt.isActive()).toBe(false);

    // No hooks configured in a temp dir, so start() is a no-op and leaves it
    // inactive — the guard itself is asserted on the source, since forcing a
    // real watcher here would leave a live fs.watch behind.
    expect(read("hooks/hooks-runtime.ts")).toMatch(/if \(this\.active\) return;/);
  });
});
