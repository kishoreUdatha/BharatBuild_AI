/**
 * StatusBar — Top-of-screen status display.
 *
 * Shows branding, model, agent, tokens, credits, and current phase.
 *
 * The phase set mirrors StatusEvent["phase"] from the runtime. They drifted
 * apart before: the runtime emits "planning"/"fixing"/"done", which were not
 * keys here, so the label silently rendered blank mid-turn.
 */

import React, { useEffect, useState } from "react";
import { Box, Text, useStdout } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import { activityVerb, formatElapsed, formatTokens } from "./activity.js";
import { modelLabel } from "./served-model.js";

export type Phase =
  | "idle"
  | "thinking"
  | "planning"
  | "coding"
  | "testing"
  | "fixing"
  | "tool"
  | "streaming"
  | "done";

export interface StatusBarProps {
  model: string;
  agent: string;
  tokenCount: number;
  creditBalance: number;
  phase: Phase;
  mode?: string;
  /**
   * Output tokens produced so far in this turn, estimated from the streamed
   * text. The exact figure only arrives with the usage event at the end, so
   * without this the live line shows nothing at all while the model writes.
   */
  streamingTokens?: number;
  /** Percent of the context window in use, if known. */
  contextPercent?: number;
  /** Seconds the current turn has been running. */
  elapsedSec?: number;
  planMode?: boolean;
  /** Model that actually served the last turn, when it differs from `model`. */
  servedModel?: string | null;
  /** Active permission mode; drives the ask/auto/plan indicator. */
  permMode?: "ask" | "auto" | "plan";
  tangentMode?: boolean;
  /** Messages typed during this turn, waiting to be sent. */
  queuedCount?: number;
}

function phaseColors(): Record<Phase, string> {
  const t = getInkTheme();
  return {
    idle: t.muted,
    thinking: t.warning,
    planning: t.primary,
    coding: t.accent,
    testing: t.primary,
    fixing: t.warning,
    tool: t.accent,
    streaming: t.success,
    done: t.success,
  };
}

const PHASE_LABELS: Record<Phase, string> = {
  idle: "idle",
  thinking: "thinking",
  planning: "planning",
  coding: "coding",
  testing: "testing",
  fixing: "fixing",
  tool: "tool",
  streaming: "streaming",
  done: "done",
};



export function StatusBar({
  model,
  agent,
  tokenCount,
  creditBalance,
  phase,
  mode,
  contextPercent,
  streamingTokens = 0,
  elapsedSec,
  planMode,
  servedModel,
  permMode = planMode ? "plan" : "ask",
  tangentMode,
  queuedCount = 0,
}: StatusBarProps): React.ReactElement {
  const { stdout } = useStdout();
  // Everything on one row stops fitting once the interrupt hint and queue
  // count appear: the gaps collapse and words run together
  // ("developerauto", "queuedctx"). Shed the least useful parts first.
  const cols = stdout?.columns ?? 80;
  const roomy = cols >= 118;
  const medium = cols >= 96;
  // Below this the left group wraps onto a second line and the gaps collapse
  // ("default· esc to / interrupt"). Worse than ugly: the status bar is part
  // of FIXED_ROWS, so an extra row shifts everything above it.
  const narrow = cols < 80;

  const busy = phase !== "idle" && phase !== "done";
  const [tick, setTick] = useState(0);

  // Animate only while there is work to show — a timer that runs at idle keeps
  // re-rendering the whole tree for nothing.
  useEffect(() => {
    if (!busy) return;
    const id = setInterval(() => setTick((t) => t + 1), 80);
    return () => clearInterval(id);
  }, [busy]);

  const g = getGlyphs();
  const marker = busy ? g.spinner[tick % g.spinner.length] : g.idle;
  const label = PHASE_LABELS[phase] ?? String(phase);
  const t = getInkTheme();

  // No border. kiro-cli frames only two regions in its entire TUI; a boxed
  // status bar plus a boxed input made this feel like a different tool, and
  // the extra rows cost real screen height.
  // A hint line, not a stats row. claude-code hangs one short dim line under
  // the prompt; a full-width table of numbers read as clutter and repeated the
  // welcome header. The figures that still matter sit dim on the right.
  return (
    <Box paddingX={1} width="100%" justifyContent="space-between">
      <Box gap={1}>
        <Text color={phaseColors()[phase] ?? t.muted}>
          {marker}{" "}
          {busy
            ? `${activityVerb(elapsedSec ?? 0)}${g.ellipsis} (${formatElapsed(elapsedSec ?? 0)}` +
              // Prefer the live estimate: the session total is stale until the
              // turn ends, so showing it here reads as though nothing is happening.
              `${streamingTokens > 0 ? ` ${g.sep} ${formatTokens(streamingTokens)} tok` : tokenCount > 0 ? ` ${g.sep} ${formatTokens(tokenCount)} tok` : ""})`
            : label}
        </Text>
        {/* The mode decides whether the agent stops on every edit, so it is
            worth a slot of its own rather than a badge that only shows in one
            of the three states. */}
        {permMode === "auto" && <Text color={t.success} bold>{g.sep} auto-accept</Text>}
        {permMode === "plan" && <Text color={t.warning} bold>{g.sep} PLAN read-only</Text>}
        {tangentMode && <Text color={t.accent} bold>TANGENT</Text>}
        <Text color={t.muted} dimColor>
          {g.sep} {modelLabel(model, servedModel)}{narrow ? "" : ` ${g.sep} ${agent}`}
        </Text>
        {/* The keyboard hint is the first thing to go: it is the same every
            turn, so it is the least informative thing competing for the row. */}
        {!narrow && (
          <Text color={t.muted} dimColor>
            {g.sep} {busy ? "esc to interrupt" : "shift+tab cycles mode"}
          </Text>
        )}
        {queuedCount > 0 && <Text color={t.warning}>{g.sep} {queuedCount} queued</Text>}
      </Box>

      <Box gap={2}>
        {contextPercent !== undefined && medium && (
          <Text color={contextPercent > 80 ? t.error : t.muted} dimColor>
            ctx {contextPercent.toFixed(0)}%
          </Text>
        )}
        {!busy && tokenCount > 0 && (
          <Text color={t.muted} dimColor>{formatNumber(tokenCount)} tok</Text>
        )}
        {medium && creditBalance > 0 && (
          <Text color={t.muted} dimColor>{g.currency}{creditBalance.toFixed(2)}</Text>
        )}
      </Box>
    </Box>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
