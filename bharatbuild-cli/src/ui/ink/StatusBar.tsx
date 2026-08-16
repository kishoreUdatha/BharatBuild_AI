/**
 * StatusBar — Top-of-screen status display.
 *
 * Shows branding, model, agent, tokens, credits, and current phase.
 */

import React from "react";
import { Box, Text } from "ink";

export type Phase = "idle" | "thinking" | "coding" | "testing" | "tool" | "streaming";

export interface StatusBarProps {
  model: string;
  agent: string;
  tokenCount: number;
  creditBalance: number;
  phase: Phase;
  mode?: string;
}

const PHASE_COLORS: Record<Phase, string> = {
  idle: "gray",
  thinking: "yellow",
  coding: "cyan",
  testing: "magenta",
  tool: "blue",
  streaming: "green",
};

const PHASE_LABELS: Record<Phase, string> = {
  idle: "● idle",
  thinking: "◐ thinking",
  coding: "◑ coding",
  testing: "◒ testing",
  tool: "◓ tool",
  streaming: "▸ streaming",
};

export function StatusBar({
  model,
  agent,
  tokenCount,
  creditBalance,
  phase,
  mode,
}: StatusBarProps): React.ReactElement {
  return (
    <Box
      borderStyle="single"
      borderColor="blue"
      paddingX={1}
      width="100%"
      justifyContent="space-between"
    >
      {/* Left: Branding + Mode */}
      <Box gap={1}>
        <Text bold color="blueBright">
          ⚡ BharatBuild
        </Text>
        {mode && (
          <Text color="gray">
            [{mode}]
          </Text>
        )}
      </Box>

      {/* Center: Model + Agent + Phase */}
      <Box gap={2}>
        <Text>
          <Text color="gray">model:</Text>
          <Text color="white" bold> {model}</Text>
        </Text>
        <Text>
          <Text color="gray">agent:</Text>
          <Text color="white" bold> {agent}</Text>
        </Text>
        <Text color={PHASE_COLORS[phase]}>
          {PHASE_LABELS[phase]}
        </Text>
      </Box>

      {/* Right: Tokens + Credits */}
      <Box gap={2}>
        <Text>
          <Text color="gray">tokens:</Text>
          <Text color="yellowBright"> {formatNumber(tokenCount)}</Text>
        </Text>
        <Text>
          <Text color="gray">credits:</Text>
          <Text color="greenBright"> ₹{creditBalance.toFixed(2)}</Text>
        </Text>
      </Box>
    </Box>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
