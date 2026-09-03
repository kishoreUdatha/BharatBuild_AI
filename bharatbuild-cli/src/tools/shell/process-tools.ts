/**
 * Checking on and stopping a background process.
 *
 * `execute_command` with background:true starts something and returns straight
 * away, which is what makes running a dev server possible at all. But without
 * these two the agent is blind from that moment on: a server that compiles for
 * ten seconds and *then* fails announces itself as ready first, and nothing
 * would ever look again. It would report the app as running and move on.
 */

import type { ToolDefinition, ToolResult } from "../filesystem/index.js";
import { readBackgroundOutput, stopBackgroundProcess } from "./background.js";

export const readProcessOutputDefinition: ToolDefinition = {
  name: "read_process_output",
  description:
    "Read new output from a process started with execute_command background:true. " +
    "Returns only what has appeared since the last check, so it can be polled. " +
    "Use it to see whether a server started cleanly, to catch a compile error " +
    "that appears after startup, or to confirm something is still running. " +
    "Omit pid to list every background process and its state.",
  input_schema: {
    type: "object",
    properties: {
      pid: {
        type: "number",
        description: "Process id reported when it was started. Omit to list all.",
      },
    },
    required: [],
  },
};

export async function readProcessOutput(input: { pid?: number }): Promise<ToolResult> {
  return readBackgroundOutput(input.pid);
}

export const stopProcessDefinition: ToolDefinition = {
  name: "stop_process",
  description:
    "Stop a process started with execute_command background:true. " +
    "Use when a server needs restarting after a change, or when it is no longer " +
    "needed. Stops the whole process tree, not just the shell that launched it.",
  input_schema: {
    type: "object",
    properties: {
      pid: {
        type: "number",
        description: "Process id reported when it was started.",
      },
    },
    required: ["pid"],
  },
};

export async function stopProcess(input: { pid: number }): Promise<ToolResult> {
  if (typeof input.pid !== "number" || !Number.isFinite(input.pid)) {
    return { content: "A numeric pid is required.", isError: true };
  }
  return stopBackgroundProcess(input.pid);
}
