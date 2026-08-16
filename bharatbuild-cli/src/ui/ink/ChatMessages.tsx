/**
 * ChatMessages — Scrollable chat message area.
 *
 * Renders user messages (green) and assistant messages (cyan) with timestamps.
 * Supports markdown rendering in assistant messages.
 */

import React from "react";
import { Box, Text } from "ink";

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
}

export function ChatMessages({ messages, maxHeight }: ChatMessagesProps): React.ReactElement {
  // Auto-scroll: only show the last N messages that fit
  const visibleMessages = maxHeight
    ? messages.slice(-(maxHeight))
    : messages;

  return (
    <Box flexDirection="column" flexGrow={1} paddingX={1}>
      {visibleMessages.length === 0 ? (
        <Box paddingY={1} justifyContent="center">
          <Text color="gray" italic>
            Start typing to begin a conversation...
          </Text>
        </Box>
      ) : (
        visibleMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))
      )}
    </Box>
  );
}

function MessageBubble({ message }: { message: ChatMessage }): React.ReactElement {
  const { role, content, timestamp, isStreaming } = message;

  const roleConfig = getRoleConfig(role);
  const timeStr = formatTime(timestamp);

  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* Header: role + timestamp */}
      <Box gap={1}>
        <Text color={roleConfig.color} bold>
          {roleConfig.prefix}
        </Text>
        <Text color="gray" dimColor>
          {timeStr}
        </Text>
        {isStreaming && (
          <Text color="yellow">▍</Text>
        )}
      </Box>

      {/* Content */}
      <Box marginLeft={2} flexDirection="column">
        {renderContent(content, role)}
      </Box>
    </Box>
  );
}

function renderContent(content: string, role: string): React.ReactElement {
  if (role === "assistant") {
    return <AssistantContent content={content} />;
  }
  return <Text color="white">{content}</Text>;
}

function AssistantContent({ content }: { content: string }): React.ReactElement {
  // Parse code blocks and regular text
  const segments = parseCodeBlocks(content);

  return (
    <Box flexDirection="column">
      {segments.map((seg, i) => {
        if (seg.type === "code") {
          return (
            <Box key={i} flexDirection="column" marginY={0}>
              <Text color="gray">{"┌─ "}{seg.lang || "code"}{" ─"}</Text>
              <Box borderStyle="single" borderColor="gray" paddingX={1}>
                <Text color="cyan">{seg.content}</Text>
              </Box>
              <Text color="gray">└───</Text>
            </Box>
          );
        }
        return (
          <Text key={i} color="cyanBright">
            {seg.content}
          </Text>
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

function parseCodeBlocks(text: string): ContentSegment[] {
  const segments: ContentSegment[] = [];
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    // Text before code block
    if (match.index > lastIndex) {
      const textContent = text.slice(lastIndex, match.index).trim();
      if (textContent) {
        segments.push({ type: "text", content: textContent });
      }
    }
    // Code block
    segments.push({
      type: "code",
      content: match[2]!.trim(),
      lang: match[1] || undefined,
    });
    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  const remaining = text.slice(lastIndex).trim();
  if (remaining) {
    segments.push({ type: "text", content: remaining });
  }

  // If nothing was parsed, return the whole text
  if (segments.length === 0) {
    segments.push({ type: "text", content: text });
  }

  return segments;
}

function getRoleConfig(role: string): { color: string; prefix: string } {
  switch (role) {
    case "user":
      return { color: "green", prefix: "❯ You" };
    case "assistant":
      return { color: "cyan", prefix: "⚡ Assistant" };
    case "system":
      return { color: "yellow", prefix: "⚙ System" };
    default:
      return { color: "white", prefix: "?" };
  }
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
