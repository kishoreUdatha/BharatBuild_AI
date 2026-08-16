/**
 * Ink TUI Entry Point
 *
 * Exports startInkTUI() which mounts the full-screen ink application.
 */

import React from "react";
import { render } from "ink";
import { App } from "./App.js";

export interface InkTUIOptions {
  runtime: any;
  model: string;
  mode?: string;
}

/**
 * Mount the ink-based TUI application.
 *
 * @param opts.runtime - The agent runtime instance (handles message send/receive)
 * @param opts.model - Active model name (auto, sonnet, opus, etc.)
 * @param opts.mode - Optional platform mode (student, developer, founder, etc.)
 * @returns The ink instance (with waitUntilExit, unmount, etc.)
 */
export function startInkTUI(opts: InkTUIOptions) {
  const instance = render(
    <App runtime={opts.runtime} model={opts.model} mode={opts.mode} />,
    {
      exitOnCtrlC: false, // We handle Ctrl+C ourselves
    },
  );

  return instance;
}

// Re-export components for external use
export { App } from "./App.js";
export { StatusBar, type Phase, type StatusBarProps } from "./StatusBar.js";
export { ChatMessages, type ChatMessage, type ChatMessagesProps } from "./ChatMessages.js";
export { ToolOutput, ToolOutputList, type ToolCall, type ToolStatus, type ToolOutputProps } from "./ToolOutput.js";
export { InputPrompt, type InputPromptProps } from "./InputPrompt.js";
export { SlashOverlay, type SlashItem, type SlashOverlayProps } from "./SlashOverlay.js";
