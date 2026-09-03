/**
 * RewindPicker — the list esc-esc opens.
 *
 * `/rewind` could already fork the conversation, but it took three steps:
 * remember the command, run it bare to see the numbered list, then run it
 * again with a number. Going back a step is a thing you want when you have
 * just realised the last instruction was wrong, which is exactly when you do
 * not want to look up a command.
 */

import React, { useState } from "react";
import { Box, Text, useInput } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import type { Turn } from "./rewind.js";

export interface RewindPickerProps {
  turns: Turn[];
  /** Chosen turn, or null when the user backed out. */
  onDecide: (turn: Turn | null) => void;
  /**
   * How many files rewinding to a turn would put back.
   *
   * Shown per row because it is the part with consequences: dropping three
   * messages is cheap, and undoing eleven file edits is not.
   */
  filesFor?: (turn: Turn) => number;
}

/** Rows of the list on screen at once. */
const WINDOW = 8;

export function RewindPicker({ turns, onDecide, filesFor }: RewindPickerProps): React.ReactElement {
  const t = getInkTheme();
  const g = getGlyphs();

  // Starts on the most recent turn: going back one step is far and away the
  // common case, and it should cost no keystrokes to select.
  const [cursor, setCursor] = useState(turns.length - 1);

  useInput((input, key) => {
    if (key.escape) return onDecide(null);
    if (key.return) return onDecide(turns[cursor] ?? null);
    if (key.upArrow || input === "k") return setCursor((c) => Math.max(0, c - 1));
    if (key.downArrow || input === "j") return setCursor((c) => Math.min(turns.length - 1, c + 1));
  });

  // Scroll the window so the cursor stays inside it on a long conversation.
  const start = Math.max(0, Math.min(cursor - Math.floor(WINDOW / 2), turns.length - WINDOW));
  const visible = turns.slice(Math.max(0, start), Math.max(0, start) + WINDOW);
  const hiddenAbove = Math.max(0, start);
  const hiddenBelow = Math.max(0, turns.length - (Math.max(0, start) + WINDOW));

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={t.primary} paddingX={1} marginY={1}>
      <Text color={t.primary} bold>Rewind to a message</Text>
      <Box marginTop={1} flexDirection="column">
        {hiddenAbove > 0 && (
          <Text color={t.muted} dimColor>{g.up} {hiddenAbove} earlier</Text>
        )}
        {visible.map((turn, i) => {
          const index = Math.max(0, start) + i;
          const selected = index === cursor;
          return (
            <Text key={turn.index} color={selected ? t.primary : t.muted} bold={selected}>
              {selected ? `${g.cursor} ` : "  "}
              {String(index + 1).padStart(2)}. {turn.preview}
              {(() => {
                const n = filesFor?.(turn) ?? 0;
                return n > 0
                  ? <Text color={t.warning}>{"  "}({n} file{n === 1 ? "" : "s"})</Text>
                  : null;
              })()}
            </Text>
          );
        })}
        {hiddenBelow > 0 && (
          <Text color={t.muted} dimColor>{g.down} {hiddenBelow} later</Text>
        )}
      </Box>
      <Box marginTop={1}>
        <Text color={t.muted} dimColor>
          enter rewinds the conversation and the files {g.sep} esc cancels
        </Text>
      </Box>
    </Box>
  );
}
