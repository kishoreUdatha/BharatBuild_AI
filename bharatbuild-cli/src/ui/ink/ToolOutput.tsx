/**
 * ToolOutput — Displays tool call execution with status indicators.
 *
 * Shows a spinner while running, ✓/✗ on completion, collapsible output,
 * and duration.
 */

import React, { useState } from "react";
import { Box, Text, useInput } from "ink";
import Spinner from "ink-spinner";

export type ToolStatus = "running" | "success" | "error";

export interface ToolCall {
  id: string;
  name: string;
  status: ToolStatus;
  output?: string;
  durationMs?: number;
  error?: string;
}

export interface ToolOutputProps {
  tool: ToolCall;
  isActive?: boolean;
  defaultCollapsed?: boolean;
}

const MAX_COLLAPSED_LINES = 3;

export function ToolOutput({
  tool,
  isActive = false,
  defaultCollapsed = true,
}: ToolOutputProps): React.ReactElement {
  const [expanded, setExpanded] = useState(!defaultCollapsed);

  useInput(
    (input, key) => {
      if (isActive && key.return) {
        setExpanded((prev) => !prev);
      }
    },
    { isActive },
  );

  const statusIcon = getStatusIcon(tool.status);
  const statusColor = getStatusColor(tool.status);

  const outputLines = (tool.output || "").split("\n");
  const isLong = outputLines.length > MAX_COLLAPSED_LINES;
  const displayLines = expanded
    ? outputLines
    : outputLines.slice(0, MAX_COLLAPSED_LINES);

  return (
    <Box flexDirection="column" marginLeft={2} marginBottom={1}>
      {/* Tool header */}
      <Box gap={1}>
        <Text color={statusColor}>
          {tool.status === "running" ? (
            <Spinner type="dots" />
          ) : (
            statusIcon
          )}
        </Text>
        <Text color="blue" bold>
          {tool.name}
        </Text>
        {tool.durationMs !== undefined && (
          <Text color="gray" dimColor>
            ({tool.durationMs}ms)
          </Text>
        )}
        {isLong && !expanded && (
          <Text color="gray" italic>
            [{outputLines.length - MAX_COLLAPSED_LINES} more lines]
          </Text>
        )}
      </Box>

      {/* Tool output */}
      {displayLines.length > 0 && displayLines[0] !== "" && (
        <Box
          flexDirection="column"
          marginLeft={3}
          borderStyle="single"
          borderColor="gray"
          paddingX={1}
        >
          {displayLines.map((line, i) => (
            <Text key={i} color="gray">
              {line}
            </Text>
          ))}
          {isLong && !expanded && (
            <Text color="gray" italic>
              ⋯
            </Text>
          )}
        </Box>
      )}

      {/* Error message */}
      {tool.error && (
        <Box marginLeft={3}>
          <Text color="red">✗ {tool.error}</Text>
        </Box>
      )}
    </Box>
  );
}

/** Render a list of tool calls */
export function ToolOutputList({
  tools,
}: {
  tools: ToolCall[];
}): React.ReactElement {
  return (
    <Box flexDirection="column">
      {tools.map((tool) => (
        <ToolOutput key={tool.id} tool={tool} />
      ))}
    </Box>
  );
}

function getStatusIcon(status: ToolStatus): string {
  switch (status) {
    case "running":
      return "◐";
    case "success":
      return "✓";
    case "error":
      return "✗";
  }
}

function getStatusColor(status: ToolStatus): string {
  switch (status) {
    case "running":
      return "yellow";
    case "success":
      return "green";
    case "error":
      return "red";
  }
}
