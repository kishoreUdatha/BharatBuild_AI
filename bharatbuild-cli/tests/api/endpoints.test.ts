/**
 * `ask` and `plan` both failed with a bare "Not Found". Each had hard-coded
 * "/api/v1/chat/stream", which the backend does not serve - the agentic
 * endpoints are mounted under "/agentic". proxy-model.ts already knew this and
 * even carried a comment about it; the knowledge simply wasn't shared, so two
 * copies went stale.
 *
 * Then, with the path fixed, the first chunk threw "Cannot read properties of
 * undefined (reading 'content')": both commands read `event.data.content`, but
 * streamSSE yields the parsed payload itself, not a {type, data} envelope.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { AGENTIC_CHAT_STREAM, AGENTIC_CHAT, AGENTIC_TOOLS } from "../../src/api/endpoints.js";

const SRC = path.resolve(__dirname, "../../src");

function read(rel: string): string {
  return fs.readFileSync(path.join(SRC, rel), "utf8");
}

describe("the agentic path", () => {
  it("is mounted under /agentic", () => {
    // Without the prefix the backend 404s, which is what shipped.
    expect(AGENTIC_CHAT_STREAM).toBe("/api/v1/agentic/chat/stream");
    expect(AGENTIC_CHAT).toBe("/api/v1/agentic/chat");
    expect(AGENTIC_TOOLS).toBe("/api/v1/agentic/tools");
  });

  it("is not hard-coded as the unprefixed path anywhere", () => {
    // The exact string that broke both commands.
    for (const file of ["commands/ask.ts", "commands/plan.ts", "api/proxy-model.ts"]) {
      expect(read(file), file).not.toContain('"/api/v1/chat/stream"');
    }
  });

  it("is reached through the shared constant, not a fourth copy", () => {
    for (const file of ["commands/ask.ts", "commands/plan.ts"]) {
      expect(read(file), file).toContain("AGENTIC_CHAT_STREAM");
    }
  });
});

describe("reading a streamed event", () => {
  it("does not assume an event.data envelope", () => {
    // streamSSE does `JSON.parse(dataLine) as SSEEvent; yield parsed`, so the
    // payload *is* the event: {type: "text_delta", text: "..."}.
    for (const file of ["commands/ask.ts", "commands/plan.ts"]) {
      expect(read(file), file).not.toMatch(/event\.data as Record/);
    }
  });

  it("reads the field the backend actually sends", () => {
    // proxy-model.ts handles the same stream and uses ev.text.
    for (const file of ["commands/ask.ts", "commands/plan.ts"]) {
      expect(read(file), file).toMatch(/\["text"\]/);
    }
  });

  it("surfaces a stream error instead of printing nothing", () => {
    for (const file of ["commands/ask.ts", "commands/plan.ts"]) {
      expect(read(file), file).toMatch(/event\.type === "error"/);
    }
  });
});
