/**
 * App — Main ink TUI application component.
 *
 * Layout:
 *   Top:    StatusBar (sticky)
 *   Middle: ChatMessages (scrollable)
 *   Bottom: InputPrompt
 *
 * Handles global keyboard shortcuts via useInput.
 */

import React, { useState, useCallback } from "react";
import { Box, Text, useInput, useApp, useStdout } from "ink";
import { StatusBar, type Phase } from "./StatusBar.js";
import { ChatMessages, type ChatMessage } from "./ChatMessages.js";
import { ToolOutputList, type ToolCall } from "./ToolOutput.js";
import { InputPrompt } from "./InputPrompt.js";

export interface AppProps {
  runtime: any;
  model: string;
  mode?: string;
}

export interface AppState {
  messages: ChatMessage[];
  tools: ToolCall[];
  phase: Phase;
  agent: string;
  tokenCount: number;
  creditBalance: number;
}

export function App({ runtime, model, mode }: AppProps): React.ReactElement {
  const { exit } = useApp();
  const { stdout } = useStdout();

  const [state, setState] = useState<AppState>({
    messages: [],
    tools: [],
    phase: "idle",
    agent: "default",
    tokenCount: 0,
    creditBalance: 0,
  });

  const [ctrlCCount, setCtrlCCount] = useState(0);

  // Global keyboard shortcuts
  useInput((input, key) => {
    // Ctrl+C: first press cancels, second exits
    if (input === "c" && key.ctrl) {
      if (state.phase !== "idle") {
        // Cancel current operation
        setState((prev) => ({ ...prev, phase: "idle" }));
        setCtrlCCount(0);
      } else {
        setCtrlCCount((prev) => {
          if (prev >= 1) {
            exit();
            return 0;
          }
          // Reset after 2 seconds
          setTimeout(() => setCtrlCCount(0), 2000);
          return prev + 1;
        });
      }
      return;
    }

    // Ctrl+O: Toggle tool output expand/collapse
    if (input === "o" && key.ctrl) {
      // This would be handled by a context/state toggle
      return;
    }

    // Ctrl+X: Toggle activity tray
    if (input === "x" && key.ctrl) {
      // Activity tray toggle
      return;
    }
  });

  const handleSubmit = useCallback(
    (input: string) => {
      // Add user message
      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: "user",
        content: input,
        timestamp: new Date(),
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg],
        phase: "thinking",
      }));

      // In a real implementation, this would call the runtime
      // For now, simulate an assistant response
      if (runtime && typeof runtime.send === "function") {
        runtime.send(input);
      } else {
        // Demo response
        setTimeout(() => {
          const assistantMsg: ChatMessage = {
            id: `msg-${Date.now()}-assistant`,
            role: "assistant",
            content: `Received: "${input}"\n\nThis is the BharatBuild ink TUI. Connect a runtime to enable AI responses.`,
            timestamp: new Date(),
          };
          setState((prev) => ({
            ...prev,
            messages: [...prev.messages, assistantMsg],
            phase: "idle",
          }));
        }, 500);
      }
    },
    [runtime],
  );

  const terminalHeight = stdout?.rows || 24;
  const chatHeight = Math.max(terminalHeight - 8, 10);

  return (
    <Box flexDirection="column" width="100%" height={terminalHeight}>
      {/* Top: Status bar (sticky) */}
      <StatusBar
        model={model}
        agent={state.agent}
        tokenCount={state.tokenCount}
        creditBalance={state.creditBalance}
        phase={state.phase}
        mode={mode}
      />

      {/* Middle: Chat messages (scrollable area) */}
      <Box flexDirection="column" flexGrow={1} height={chatHeight}>
        <ChatMessages messages={state.messages} maxHeight={chatHeight} />

        {/* Active tool calls */}
        {state.tools.length > 0 && <ToolOutputList tools={state.tools} />}
      </Box>

      {/* Ctrl+C hint */}
      {ctrlCCount > 0 && (
        <Box justifyContent="center">
          <Box paddingX={1}>
            <Text color="yellow">Press Ctrl+C again to exit</Text>
          </Box>
        </Box>
      )}

      {/* Bottom: Input prompt */}
      <InputPrompt
        onSubmit={handleSubmit}
        disabled={state.phase !== "idle"}
      />
    </Box>
  );
}
