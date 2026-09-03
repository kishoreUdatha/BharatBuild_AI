/**
 * PermissionPrompt — approval UI for a pending tool call.
 *
 * The ink TUI had none. The agent loop asked for approval through the
 * readline-based prompt, which ink immediately painted over while also holding
 * stdin in raw mode, so nobody could answer it. Every call resolved to "deny",
 * the loop skipped the tool, and the model gave up after announcing its plan.
 *
 * What replaced that was a hint line — `apply_patch needs approval`, the raw
 * arguments, and `y allow · a always · n deny`. It worked, but it asked the
 * wrong question: approving a function call by name, with the change itself
 * shown as JSON. This asks about the action and shows the diff, and answers
 * with a selected option rather than a letter, so the choice is visible before
 * it is committed and Enter is the only key that acts.
 */

import React, { useState } from "react";
import { Box, Text, useInput } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import { DiffView } from "./Diff.js";
import { permissionCopy } from "./permission-copy.js";

export type PermissionChoice = "allow" | "allow_always" | "deny";

export interface PendingPermission {
  toolName: string;
  input: Record<string, unknown>;
}

export interface PermissionPromptProps {
  pending: PendingPermission;
  onDecide: (choice: PermissionChoice) => void;
}

/** Rows the preview may occupy before it is cut short. */
const MAX_PREVIEW_ROWS = 14;

export function PermissionPrompt({ pending, onDecide }: PermissionPromptProps): React.ReactElement {
  const t = getInkTheme();
  const g = getGlyphs();
  const copy = permissionCopy(pending.toolName, pending.input);

  const options: Array<{ label: string; choice: PermissionChoice }> = [
    { label: "Yes", choice: "allow" },
    { label: copy.alwaysLabel, choice: "allow_always" },
    { label: "No, and tell BharatBuild what to do differently", choice: "deny" },
  ];

  const [cursor, setCursor] = useState(0);

  useInput((input, key) => {
    // Escape always denies, wherever the cursor is — it is the one answer a
    // user needs to be able to give without reading the list.
    if (key.escape) return onDecide("deny");
    if (key.return) return onDecide(options[cursor]!.choice);
    if (key.upArrow || input === "k") return setCursor((c) => (c + options.length - 1) % options.length);
    if (key.downArrow || input === "j") return setCursor((c) => (c + 1) % options.length);

    // A number selects and answers in one keystroke, which is how this gets
    // used once the wording is familiar.
    const n = Number.parseInt(input, 10);
    if (Number.isInteger(n) && n >= 1 && n <= options.length) {
      setCursor(n - 1);
      return onDecide(options[n - 1]!.choice);
    }
  });

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={t.warning}
      paddingX={1}
      marginY={1}
    >
      <Text color={t.warning} bold>
        {g.warn} {copy.title}
      </Text>

      <Box marginTop={1} flexDirection="column">
        <Preview copy={copy} />
      </Box>

      <Box marginTop={1}>
        <Text color={t.text}>{copy.question}</Text>
      </Box>

      <Box marginTop={1} flexDirection="column">
        {options.map((opt, i) => {
          const selected = i === cursor;
          return (
            <Text key={opt.choice} color={selected ? t.primary : t.muted} bold={selected}>
              {selected ? `${g.cursor} ` : "  "}
              {i + 1}. {opt.label}
              {opt.choice === "deny" ? <Text color={t.muted} dimColor> (esc)</Text> : null}
            </Text>
          );
        })}
      </Box>
    </Box>
  );
}

function Preview({ copy }: { copy: ReturnType<typeof permissionCopy> }): React.ReactElement {
  const t = getInkTheme();
  const g = getGlyphs();

  if (copy.preview.kind === "diff") {
    // Columns already spent: the box border and its padding.
    return <DiffView patch={copy.preview.patch} maxRows={MAX_PREVIEW_ROWS} indent={4} />;
  }

  if (copy.preview.kind === "command") {
    // A command is the thing being approved, so it gets read as code rather
    // than as a `command: …` key/value pair.
    return (
      <Box>
        <Text color={t.muted}>{g.caret} </Text>
        <Text color={t.accent}>{copy.preview.text}</Text>
      </Box>
    );
  }

  if (copy.preview.kind === "lines") {
    const shown = copy.preview.lines.slice(0, MAX_PREVIEW_ROWS);
    const rest = copy.preview.lines.length - shown.length;
    return (
      <Box flexDirection="column">
        {shown.map((line, i) => (
          <Text key={i} color={t.muted}>{line}</Text>
        ))}
        {rest > 0 && (
          <Text color={t.muted} dimColor>{g.ellipsis} {rest} more lines</Text>
        )}
      </Box>
    );
  }

  return <Text color={t.muted} dimColor>(no preview)</Text>;
}
