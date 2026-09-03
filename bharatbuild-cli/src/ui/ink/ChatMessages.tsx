/**
 * ChatMessages — Scrollable chat message area.
 *
 * Renders user messages (green) and assistant messages (cyan) with timestamps.
 * Supports markdown rendering in assistant messages.
 */

import React from "react";
import { Box, Text } from "ink";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import { Markdown } from "./markdown.js";
import { parseThinking } from "./thinking.js";
import { CodeBlock } from "./CodeBlock.js";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatMessagesProps {
  messages: ChatMessage[];
  maxHeight?: number;
  /** /compact — drop the header line and blank row between messages. */
  compact?: boolean;
  mode?: string;
}

export function ChatMessages({
  messages,
  maxHeight,
  compact = false,
  mode,
}: ChatMessagesProps): React.ReactElement {
  // Auto-scroll by rendered HEIGHT, not message count. Counting messages let a
  // handful of long ones overflow the pane, and the overflow was clipped from
  // the bottom — hiding the newest output, which is the part being read.
  const visibleMessages = maxHeight ? fitToHeight(messages, maxHeight, compact) : messages;

  // No flexGrow: the conversation stacks from the top and tool cards sit
  // directly beneath the last message instead of being pushed to the bottom
  // of the screen by an expanding spacer.
  return (
    <Box flexDirection="column" flexShrink={1} paddingX={1}>
      {visibleMessages.length === 0 ? (
        <Welcome mode={mode} />
      ) : (
        visibleMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} compact={compact} />
        ))
      )}
    </Box>
  );
}

/**
 * First-run panel. An empty screen with "Start typing…" gave no hint that a
 * command palette existed at all, which is how /model ended up being typed as
 * a chat message.
 */
export function Welcome({ mode }: { mode?: string }): React.ReactElement {
  const t = getInkTheme();
  const g = getGlyphs();
  // The working directory belongs here. A session started from the home folder
  // wrote a generated site straight into C:\Users\user, and nothing on screen
  // said where the agent was pointed.
  const cwd = process.cwd();

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box
        flexDirection="column"
        borderStyle="round"
        borderColor={t.primary}
        paddingX={1}
      >
        <Text color={t.primary} bold>
          BharatBuild AI
        </Text>
        <Box marginTop={1} flexDirection="column">
          <Text color={t.muted}>
            cwd:   <Text color={t.text}>{cwd}</Text>
          </Text>
          {mode && (
            <Text color={t.muted}>
              mode:  <Text color={t.text}>{mode}</Text>
            </Text>
          )}
        </Box>
      </Box>

      <Box paddingX={1} marginTop={1}>
        <Text color={t.muted} dimColor>
          <Text color={t.text}>/</Text> commands {g.sep} <Text color={t.text}>Tab</Text> complete{" "}
          {g.sep} <Text color={t.text}>ctrl+o</Text> expand {g.sep}{" "}
          <Text color={t.text}>esc</Text> interrupt
        </Text>
      </Box>
    </Box>
  );
}

export function MessageBubble({
  message,
  compact = false,
}: {
  message: ChatMessage;
  compact?: boolean;
}): React.ReactElement {
  const { role, content, timestamp, isStreaming } = message;

  const roleConfig = getRoleConfig(role);
  const timeStr = formatTime(timestamp);

  // A marker in the gutter instead of a "⚡ Assistant  12:38:58" header line.
  // The header cost a row per message and pushed the actual content right;
  // the marker carries the same information in the space of one character.
  void timeStr;

  return (
    <Box flexDirection="column" marginBottom={compact ? 0 : 1}>
      <Box>
        <Text color={roleConfig.color} bold>
          {roleConfig.sigil}{" "}
        </Text>
        <Box flexDirection="column" flexGrow={1}>
          {renderContent(content, role)}
        </Box>
        {isStreaming && <Text color={getInkTheme().warning}> {getGlyphs().caret}</Text>}
      </Box>
    </Box>
  );
}

function renderContent(content: string, role: string): React.ReactElement {
  if (role === "assistant") {
    return <AssistantContent content={content} />;
  }
  // Command output is pre-formatted (aligned tables, help text) — it must keep
  // its own spacing rather than being reflowed as prose.
  if (role === "system") {
    return (
      <Box flexDirection="column">
        {content.split("\n").map((line, i) => (
          <Text key={i} color={/^(Error|Command failed)/.test(line) ? "redBright" : "gray"}>
            {line}
          </Text>
        ))}
      </Box>
    );
  }
  // Through the theme, not a literal: a hardcoded "white" is ANSI 37, which
  // renders grey, and it also ignored the light theme entirely — black-on-white
  // terminals got white text on white.
  return <Text color={getInkTheme().text}>{content}</Text>;
}

/** Reasoning lines shown before it is folded down. */
const THINKING_PREVIEW_LINES = 3;

/**
 * A `<thinking>` block: set apart, dimmed, and folded.
 *
 * Printed in full it drowned the answer — one reply put 190 lines of monologue
 * above its own conclusion. Removing it entirely would be worse: reasoning is
 * how you tell a considered answer from a guess, and reading it is how a wrong
 * answer got caught here.
 */
function ThinkingBlock({ content }: { content: string }): React.ReactElement {
  const t = getInkTheme();
  const g = getGlyphs();
  const lines = content.split("\n").filter((l) => l.trim() !== "");
  const shown = lines.slice(0, THINKING_PREVIEW_LINES);
  const hidden = lines.length - shown.length;

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color={t.muted} dimColor italic>
        {g.thinking} thinking{hidden > 0 ? ` (${lines.length} lines)` : ""}
      </Text>
      {shown.map((line, i) => (
        <Text key={i} color={t.muted} dimColor italic>
          {"  "}{line.length > 96 ? `${line.slice(0, 95)}${g.ellipsis}` : line}
        </Text>
      ))}
      {hidden > 0 && (
        <Text color={t.muted} dimColor>
          {"  "}{g.ellipsis} {hidden} more line{hidden === 1 ? "" : "s"}
        </Text>
      )}
    </Box>
  );
}

function AssistantContent({ content }: { content: string }): React.ReactElement {
  // Reasoning first: it wraps prose and code alike, so splitting it out here
  // keeps the code-fence parser from seeing fences that live inside a
  // monologue and framing them as if they were part of the answer.
  const reply = parseThinking(content);

  return (
    <Box flexDirection="column">
      {reply.map((part, r) =>
        part.kind === "thinking" ? (
          <ThinkingBlock key={`th${r}`} content={part.content} />
        ) : (
          <AnswerBody key={`tx${r}`} content={part.content} />
        ),
      )}
    </Box>
  );
}

/** The answer itself — prose and fenced code. */
function AnswerBody({ content }: { content: string }): React.ReactElement {
  const segments = parseCodeBlocks(content);

  return (
    <Box flexDirection="column">
      {segments.map((seg, i) => {
        if (seg.type === "code") {
          // One frame, not two — the old version drew an ASCII header and
          // footer around an already-bordered box.
          return (
            <Box
              key={i}
              flexDirection="column"
              borderStyle="round"
              borderColor={getInkTheme().border}
              paddingX={1}
              // One blank row above and below, rather than whatever survived
              // trimming. The box used to butt straight up against the
              // paragraph before it.
              marginTop={i === 0 ? 0 : 1}
              marginBottom={1}
            >
              <Text color="gray" dimColor>
                {seg.lang || "code"}
              </Text>
              <CodeBlock code={seg.content} lang={seg.lang} />
            </Box>
          );
        }
        // Prose goes through the markdown renderer; headings and bold were
        // printed literally as "##" and "**".
        return (
          <Box key={i} flexDirection="column">
            <Markdown content={seg.content} />
          </Box>
        );
      })}
    </Box>
  );
}

interface ContentSegment {
  type: "text" | "code";
  content: string;
  lang?: string;
}

/**
 * Strip blank lines from the ends of a prose run without touching its inside.
 *
 * A plain `.trim()` also ate the indentation of the first line, and the blank
 * row that separated the paragraph from the fence — the code box then sat hard
 * against the sentence above it. The gap is reinstated as margin on the box
 * itself, so it is exactly one row whatever the source did.
 */
function trimBlankEdges(text: string): string {
  return text.replace(/^(?:[ \t]*\n)+/, "").replace(/(?:\n[ \t]*)+$/, "");
}

function parseCodeBlocks(text: string): ContentSegment[] {
  const segments: ContentSegment[] = [];
  // The closing fence is optional. While a reply streams in, the opening fence
  // arrives long before the closing one, and requiring both meant the code was
  // rendered as prose — backticks and all — until the block finished, then
  // snapped into a box. Treating end-of-text as a terminator renders it as
  // code from the first line.
  const codeBlockRegex = /```(\w*)[ \t]*\n([\s\S]*?)(?:```|$)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    // Text before code block
    if (match.index > lastIndex) {
      const textContent = trimBlankEdges(text.slice(lastIndex, match.index));
      if (textContent) {
        segments.push({ type: "text", content: textContent });
      }
    }
    // Code block
    segments.push({
      type: "code",
      content: trimBlankEdges(match[2]!),
      lang: match[1] || undefined,
    });
    lastIndex = match.index + match[0].length;
    // A zero-width match at the end (an opening fence with nothing after it)
    // would otherwise spin here forever.
    if (match[0].length === 0) break;
  }

  // Remaining text
  const remaining = trimBlankEdges(text.slice(lastIndex));
  if (remaining) {
    segments.push({ type: "text", content: remaining });
  }

  // If nothing was parsed, return the whole text
  if (segments.length === 0) {
    segments.push({ type: "text", content: text });
  }

  return segments;
}

function getRoleConfig(role: string): { color: string; prefix: string; sigil: string } {
  const t = getInkTheme();
  const g = getGlyphs();
  switch (role) {
    case "user":
      return { color: t.user, prefix: "You", sigil: g.user };
    case "assistant":
      return { color: t.assistant, prefix: "Assistant", sigil: g.assistant };
    case "system":
      return { color: t.muted, prefix: "System", sigil: g.system };
    default:
      return { color: t.text, prefix: "?", sigil: "." };
  }
}

/** Rows a message occupies: header + body lines + code-fence borders + margin. */
function estimateHeight(msg: ChatMessage, compact: boolean): number {
  const bodyLines = msg.content.split("\n").length;
  const fences = (msg.content.match(/```/g) ?? []).length;
  // Each fenced block gains a border top, a language row and a border bottom.
  const codeChrome = Math.floor(fences / 2) * 3;
  return (compact ? 0 : 2) + bodyLines + codeChrome;
}

/**
 * Newest messages that fit in `budget` rows, oldest-first.
 *
 * A single message can exceed the whole budget on its own (`/help`, a long
 * file dump). Those get clipped with a marker — letting them through made Ink
 * paint past the last row, which corrupts the frame rather than scrolling.
 */
function fitToHeight(messages: ChatMessage[], budget: number, compact: boolean): ChatMessage[] {
  const kept: ChatMessage[] = [];
  let used = 0;
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i]!;
    const h = estimateHeight(msg, compact);
    if (used + h > budget) {
      if (kept.length > 0) break;
      kept.unshift(clampMessage(msg, Math.max(3, budget - (compact ? 0 : 2))));
      break;
    }
    kept.unshift(msg);
    used += h;
  }
  return kept;
}

function clampMessage(msg: ChatMessage, maxLines: number): ChatMessage {
  const lines = msg.content.split("\n");
  if (lines.length <= maxLines) return msg;
  const shown = lines.slice(0, maxLines - 1);
  const hidden = lines.length - shown.length;
  return { ...msg, content: [...shown, `${getGlyphs().ellipsis} ${hidden} more lines`].join("\n") };
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
