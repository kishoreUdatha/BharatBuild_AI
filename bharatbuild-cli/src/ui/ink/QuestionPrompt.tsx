/**
 * QuestionPrompt — the picker `ask_user` puts on screen.
 *
 * Shaped like the approval prompt on purpose: both interrupt to ask something
 * and hold the keyboard until answered, so they should look and behave alike
 * rather than being two different dialogs to learn.
 *
 * The difference is what a refusal means. Declining a tool call denies it;
 * dismissing a question just hands the decision back to the agent, which is
 * told to choose and say which way it went.
 */

import React, { useState } from "react";
import { Box, Text, useInput } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import type { PendingQuestion } from "../../tools/agent/ask-user.js";

export interface QuestionPromptProps {
  question: PendingQuestion;
  /** Chosen labels, or null when dismissed. */
  onAnswer: (chosen: string[] | null) => void;
}

export function QuestionPrompt({ question, onAnswer }: QuestionPromptProps): React.ReactElement {
  const t = getInkTheme();
  const g = getGlyphs();
  const options = question.options;
  const multi = question.multiSelect === true;

  const [cursor, setCursor] = useState(0);
  const [picked, setPicked] = useState<Set<number>>(new Set());

  useInput((input, key) => {
    if (key.escape) return onAnswer(null);

    if (key.return) {
      if (!multi) return onAnswer([options[cursor]!.label]);
      // Enter with nothing ticked takes the row under the cursor, so the key
      // does something sensible rather than nothing.
      const chosen = picked.size > 0
        ? [...picked].sort((a, b) => a - b).map((i) => options[i]!.label)
        : [options[cursor]!.label];
      return onAnswer(chosen);
    }

    if (key.upArrow || input === "k") return setCursor((c) => (c + options.length - 1) % options.length);
    if (key.downArrow || input === "j") return setCursor((c) => (c + 1) % options.length);

    if (multi && input === " ") {
      return setPicked((prev) => {
        const next = new Set(prev);
        if (next.has(cursor)) next.delete(cursor);
        else next.add(cursor);
        return next;
      });
    }

    const n = Number.parseInt(input, 10);
    if (Number.isInteger(n) && n >= 1 && n <= options.length) {
      if (multi) {
        setCursor(n - 1);
        return setPicked((prev) => {
          const next = new Set(prev);
          if (next.has(n - 1)) next.delete(n - 1);
          else next.add(n - 1);
          return next;
        });
      }
      setCursor(n - 1);
      return onAnswer([options[n - 1]!.label]);
    }
  });

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={t.accent}
      paddingX={1}
      marginY={1}
    >
      <Text color={t.accent} bold>
        {question.header ? `${question.header} — ` : ""}{question.question}
      </Text>

      <Box marginTop={1} flexDirection="column">
        {options.map((opt, i) => {
          const selected = i === cursor;
          const ticked = picked.has(i);
          return (
            <Box key={opt.label} flexDirection="column">
              <Text color={selected ? t.primary : t.text} bold={selected}>
                {selected ? `${g.cursor} ` : "  "}
                {multi ? `${g.task(ticked)} ` : ""}
                {i + 1}. {opt.label}
              </Text>
              {opt.description && (
                <Text color={t.muted} dimColor>
                  {"     "}{opt.description}
                </Text>
              )}
            </Box>
          );
        })}
      </Box>

      <Box marginTop={1}>
        <Text color={t.muted} dimColor>
          {multi ? "space toggles · enter confirms" : "enter chooses"} {g.sep}{" "}
          esc lets the agent decide
        </Text>
      </Box>
    </Box>
  );
}
