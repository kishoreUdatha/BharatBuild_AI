/**
 * SlashOverlay — Slash command suggestion panel.
 *
 * Appears when the user types / in the input. Shows a filterable list of
 * available commands with arrow-key navigation and Enter to select.
 */

import React, { useMemo } from "react";
import { Box, Text, useInput, useStdout } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";

export interface SlashItem {
  name: string;
  description: string;
  args?: string;
}

export interface SlashOverlayProps {
  filter: string;
  commands: SlashItem[];
  selectedIndex: number;
  onSelect: (command: SlashItem) => void;
  onDismiss: () => void;
  onNavigate: (direction: "up" | "down") => void;
  visible: boolean;
  /**
   * Sigil shown before each name. "/" for commands, "@" for file mentions.
   *
   * This panel was written for slash commands and hardcoded the slash, so
   * reusing it for `@file` completion listed every path as "/README.md".
   */
  prefix?: string;
}

const MAX_VISIBLE = 8;

function truncate(s: string, width: number): string {
  return s.length <= width ? s : `${s.slice(0, Math.max(0, width - 1))}~`;
}

/** Pad to `width`, always leaving at least one space before the next column. */
function pad(s: string, width: number): string {
  const t = truncate(s, Math.max(1, width - 1));
  return t + " ".repeat(Math.max(1, width - t.length));
}

export function SlashOverlay({
  filter,
  commands,
  selectedIndex,
  onSelect,
  onDismiss,
  onNavigate,
  visible,
  prefix = "/",
}: SlashOverlayProps): React.ReactElement | null {
  const { stdout } = useStdout();
  const stdoutCols = stdout?.columns;

  // Hooks must run on every render — the early `return null` used to sit above
  // them, changing the hook count whenever the overlay opened or closed.
  const filtered = useMemo(() => {
    const q = filter.toLowerCase().replace(/^\//, "");
    if (!q) return commands;
    return commands.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q),
    );
  }, [filter, commands]);

  useInput(
    (input, key) => {
      if (key.escape) {
        onDismiss();
        return;
      }
      if (key.upArrow) {
        onNavigate("up");
        return;
      }
      if (key.downArrow) {
        onNavigate("down");
        return;
      }
      if (key.return && filtered.length > 0) {
        const safeIndex = Math.min(selectedIndex, filtered.length - 1);
        onSelect(filtered[safeIndex]!);
        return;
      }
    },
    { isActive: visible },
  );

  if (!visible) return null;

  if (filtered.length === 0) {
    return (
      <Box paddingX={2}>
        <Text color="gray" italic>
          No matching commands
        </Text>
      </Box>
    );
  }

  // Keep the selected row inside a sliding window.
  const startIdx = Math.min(
    Math.max(0, selectedIndex - MAX_VISIBLE + 1),
    Math.max(0, filtered.length - MAX_VISIBLE),
  );
  const visibleItems = filtered.slice(startIdx, startIdx + MAX_VISIBLE);
  const hasMore = filtered.length > startIdx + visibleItems.length;
  const hasBefore = startIdx > 0;

  // Two aligned columns, no frame — the palette reads as part of the terminal
  // rather than a dialog floating over it. A hard-coded width used to wrap
  // `/checkpoint` into `/checkpoi` + `nt`, so size to the terminal and give
  // each column a fixed budget so every row stays exactly one line.
  const totalWidth = Math.max(40, Math.min((stdoutCols ?? 80) - 2, 120));
  const sigWidth = Math.min(
    36,
    Math.max(...filtered.map((c) => c.name.length + (c.args?.length ?? 0) + 2), 14),
  );
  const descWidth = Math.max(10, totalWidth - sigWidth - 3);
  const t = getInkTheme();

  return (
    <Box flexDirection="column" paddingX={1}>
      {hasBefore && (
        <Text color={t.muted} dimColor>
          {"  "}{getGlyphs().up} {startIdx} more
        </Text>
      )}

      {/* One row each, built as a single Text with manual padding: nested
          fixed-width Boxes collapsed and bled into each other. */}
      {visibleItems.map((cmd, i) => {
        const globalIdx = startIdx + i;
        const isSelected = globalIdx === selectedIndex;
        const sig = pad(`${prefix}${cmd.name}${cmd.args ? " " + cmd.args : ""}`, sigWidth);
        const desc = truncate(cmd.description, descWidth);
        return (
          <Text key={cmd.name} wrap="truncate">
            <Text color={isSelected ? t.primary : t.muted} bold={isSelected}>
              {sig}
            </Text>
            <Text color={isSelected ? t.primary : t.muted} dimColor={!isSelected}>
              {desc}
            </Text>
          </Text>
        );
      })}

      {hasMore && (
        <Text color={t.muted} dimColor>
          {"  "}{getGlyphs().down} {filtered.length - startIdx - visibleItems.length} more
        </Text>
      )}
    </Box>
  );
}
