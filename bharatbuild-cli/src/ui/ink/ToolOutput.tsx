/**
 * ToolOutput — Displays tool call execution with status indicators.
 *
 * Shows a spinner while running, ✓/✗ on completion, collapsible output,
 * and duration.
 */

import React, { useState, useEffect } from "react";
import { Box, Text, useInput } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import { DiffView, looksLikeDiff } from "./Diff.js";
import { displayPath, looksLikePath } from "../../infra/display-path.js";

export type ToolStatus = "running" | "success" | "error";

export interface ToolCall {
  id: string;
  name: string;
  status: ToolStatus;
  input?: Record<string, unknown>;
  output?: string;
  durationMs?: number;
  error?: string;
  /**
   * Bytes of arguments received while the model is still composing the call.
   * Set before the tool runs: a large write took ~9s to compose and showed
   * nothing at all until it had finished.
   */
  pendingBytes?: number;
}

export interface ToolOutputProps {
  tool: ToolCall;
  isActive?: boolean;
  defaultCollapsed?: boolean;
  /** Ctrl+O expands every card at once. */
  forceExpanded?: boolean;
}

const MAX_COLLAPSED_LINES = 3;

export function ToolOutput({
  tool,
  isActive = false,
  defaultCollapsed = true,
  forceExpanded,
}: ToolOutputProps): React.ReactElement {
  const [localExpanded, setLocalExpanded] = useState(!defaultCollapsed);
  const expanded = forceExpanded ?? localExpanded;

  useInput(
    (input, key) => {
      if (isActive && key.return) {
        setLocalExpanded((prev) => !prev);
      }
    },
    { isActive },
  );

  const statusIcon = getStatusIcon(tool.status);
  const statusColor = getStatusColor(tool.status);

  const raw = tool.output || "";
  // A file-mutating tool returns a unified diff. Render it as a diff rather
  // than as three grey lines of truncated text.
  const isDiff = looksLikeDiff(raw);
  const diffStart = isDiff ? raw.indexOf("--- a/") : -1;
  const headline = isDiff ? raw.slice(0, diffStart).trim() : "";
  const outputLines = raw.split("\n");
  const isLong = outputLines.length > MAX_COLLAPSED_LINES;
  const displayLines = expanded
    ? outputLines
    : outputLines.slice(0, MAX_COLLAPSED_LINES);
  const argSummary = summarizeInput(tool.input);

  const t = getInkTheme();

  // `⏺ name(args)` with the result hanging off a `⎿` elbow, so a tool call
  // reads as one entry in the transcript rather than a boxed panel.
  //
  // paddingX matches the wrapper App puts around a message. Without it the
  // tool marker sat at column 0 while the assistant marker above it sat at
  // column 1, and a one-column step down the transcript reads as a rendering
  // fault rather than a choice.
  return (
    <Box flexDirection="column" marginBottom={1} paddingX={1}>
      <Box>
        <Text color={statusColor}>
          {tool.status === "running" ? <RunningMark /> : statusIcon}
        </Text>
        <Text color={t.text} bold>
          {" "}{tool.name}
        </Text>
        {argSummary && <Text color={t.muted}>({argSummary})</Text>}
        {tool.durationMs !== undefined && (
          <Text color={t.muted} dimColor>
            {"  "}{tool.durationMs}ms
          </Text>
        )}
      </Box>

      {/* Still being composed by the model. There are no arguments to
          summarise yet, so report the one thing there is — how much has
          arrived — rather than showing an idle spinner and nothing else. */}
      {tool.status === "running" && tool.pendingBytes !== undefined && !tool.output && (
        <Box>
          <Text color={t.muted} dimColor>
            {getGlyphs().elbow}writing{argSummary ? ` ${argSummary}` : ""}
            {tool.pendingBytes > 0 ? ` — ${formatBytes(tool.pendingBytes)}` : "…"}
          </Text>
        </Box>
      )}

      {/* A diff gets the full treatment: gutter, +/- tint, highlighting. */}
      {isDiff && (
        <Box flexDirection="column">
          {headline.split("\n").filter(Boolean).map((line, i) => (
            <Box key={i}>
              <Text color={t.muted} dimColor>{i === 0 ? getGlyphs().elbow : getGlyphs().elbowCont}</Text>
              <Text color={t.text}>{line}</Text>
            </Box>
          ))}
          <Box marginLeft={5}>
            <DiffView patch={raw.slice(diffStart)} maxRows={expanded ? 400 : 14} indent={5} />
          </Box>
        </Box>
      )}

      {/* Result, indented under an elbow */}
      {!isDiff && displayLines.length > 0 && displayLines[0] !== "" && (
        <Box flexDirection="column">
          {displayLines.map((line, i) => (
            <Box key={i}>
              <Text color={t.muted} dimColor>
                {i === 0 ? getGlyphs().elbow : getGlyphs().elbowCont}
              </Text>
              <DiffLine line={line} />
            </Box>
          ))}
          {isLong && !expanded && (
            <Text color={t.muted} dimColor>
              {getGlyphs().elbowCont}{getGlyphs().ellipsis} +{outputLines.length - MAX_COLLAPSED_LINES} lines (ctrl+o to expand)
            </Text>
          )}
        </Box>
      )}

      {/* Error message */}
      {tool.error && (
        <Box>
          <Text color={t.error}>{getGlyphs().elbow}{tool.error}</Text>
        </Box>
      )}
    </Box>
  );
}

/** Byte counts read better than raw digits once past a kilobyte. */
function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  return `${(n / 1024).toFixed(1)} KB`;
}

/** Animated marker using the active glyph set — ink-spinner is braille-only. */
function RunningMark(): React.ReactElement {
  const frames = getGlyphs().spinner;
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((n) => n + 1), 120);
    return () => clearInterval(id);
  }, []);
  return <Text>{frames[i % frames.length]}</Text>;
}

/**
 * Colour unified-diff output the way a reviewer expects. Tool results from
 * edit/write tools come back as plain text, so this is the only place a diff
 * gets any visual structure.
 */
function DiffLine({ line }: { line: string }): React.ReactElement {
  const t = getInkTheme();
  if (/^\+(?!\+\+)/.test(line)) return <Text color={t.diffAdd}>{line}</Text>;
  if (/^-(?!--)/.test(line)) return <Text color={t.diffRemove}>{line}</Text>;
  if (/^@@/.test(line)) return <Text color={t.diffMeta}>{line}</Text>;
  if (/^(\+\+\+|---)/.test(line)) return <Text color={t.muted} bold>{line}</Text>;
  // Body text, not chrome. This was `muted` (grey), so every file this tool
  // read — the actual content the user asked for — rendered dimmer than the
  // prose around it and was hard to read. The elbow, the timing and the
  // "+N lines" hint stay muted; what the tool returned does not.
  return <Text color={t.text}>{line}</Text>;
}

/** One-line preview of a tool's arguments, e.g. `src/index.ts` or `npm test`. */
function summarizeInput(input?: Record<string, unknown>): string {
  if (!input) return "";
  // Path-bearing keys first, and shown relative to the working directory —
  // `write_file(C:\Users\user\PalindromeChecker.java)` is mostly noise, and
  // the part that matters is which file changed.
  const pathKeys = ["path", "file_path", "file"];
  for (const key of pathKeys) {
    const v = input[key];
    if (typeof v === "string" && v.trim()) return clip(displayPath(v));
  }
  // A command or query is shown as written; shortening it would change what it
  // says it ran.
  for (const key of ["command", "pattern", "query", "url"]) {
    const v = input[key];
    if (typeof v === "string" && v.trim()) return clip(v);
  }
  const first = Object.values(input).find((v) => typeof v === "string") as string | undefined;
  if (!first) return "";
  return clip(looksLikePath(first) ? displayPath(first) : first);
}

/** Keep a summary to one line's worth. */
function clip(value: string): string {
  return value.length > 60 ? `${value.slice(0, 57)}${getGlyphs().ellipsis}` : value;
}

/** Render a list of tool calls */
export function ToolOutputList({
  tools,
  forceExpanded,
  max = 6,
}: {
  tools: ToolCall[];
  forceExpanded?: boolean;
  max?: number;
}): React.ReactElement {
  // Only the most recent calls stay on screen; older ones would push the
  // conversation out of view on a long turn.
  const visible = tools.slice(-max);
  const hidden = tools.length - visible.length;

  return (
    <Box flexDirection="column">
      {hidden > 0 && (
        /* Column 1, level with the tool markers below it. */
        <Box marginLeft={1}>
          <Text color="gray" dimColor>
            {getGlyphs().ellipsis} {hidden} earlier tool call{hidden === 1 ? "" : "s"}
          </Text>
        </Box>
      )}
      {visible.map((tool) => (
        <ToolOutput key={tool.id} tool={tool} forceExpanded={forceExpanded} />
      ))}
    </Box>
  );
}

function getStatusIcon(status: ToolStatus): string {
  switch (status) {
    case "running":
      return getGlyphs().spinner[0]!;
    case "success":
      return getGlyphs().toolOk;
    case "error":
      return getGlyphs().toolFail;
  }
}

function getStatusColor(status: ToolStatus): string {
  const t = getInkTheme();
  switch (status) {
    case "running":
      return t.warning;
    case "success":
      return t.success;
    case "error":
      return t.error;
  }
}
