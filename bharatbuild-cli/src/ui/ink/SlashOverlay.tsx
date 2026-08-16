/**
 * SlashOverlay — Slash command suggestion panel.
 *
 * Appears when the user types / in the input. Shows a filterable list of
 * available commands with arrow-key navigation and Enter to select.
 */

import React, { useMemo } from "react";
import { Box, Text, useInput } from "ink";

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
}

const MAX_VISIBLE = 8;

export function SlashOverlay({
  filter,
  commands,
  selectedIndex,
  onSelect,
  onDismiss,
  onNavigate,
  visible,
}: SlashOverlayProps): React.ReactElement | null {
  if (!visible) return null;

  const filtered = useMemo(() => {
    const q = filter.toLowerCase().replace(/^\//, "");
    if (!q) return commands;
    return commands.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q),
    );
  }, [filter, commands]);

  useInput((input, key) => {
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
  });

  if (filtered.length === 0) {
    return (
      <Box
        borderStyle="single"
        borderColor="gray"
        paddingX={1}
        marginLeft={2}
      >
        <Text color="gray" italic>
          No matching commands for "{filter}"
        </Text>
      </Box>
    );
  }

  // Calculate visible window (scroll if needed)
  const startIdx = Math.max(0, selectedIndex - MAX_VISIBLE + 1);
  const visibleItems = filtered.slice(startIdx, startIdx + MAX_VISIBLE);
  const hasMore = filtered.length > startIdx + MAX_VISIBLE;
  const hasBefore = startIdx > 0;

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor="blue"
      paddingX={1}
      marginLeft={2}
      width={60}
    >
      {/* Header */}
      <Box marginBottom={0}>
        <Text color="blue" bold>
          / Commands
        </Text>
        <Text color="gray">
          {" "}({filtered.length} available)
        </Text>
      </Box>

      {/* Scroll indicator top */}
      {hasBefore && (
        <Text color="gray" dimColor>
          ↑ more
        </Text>
      )}

      {/* Command list */}
      {visibleItems.map((cmd, i) => {
        const globalIdx = startIdx + i;
        const isSelected = globalIdx === selectedIndex;
        return (
          <Box key={cmd.name} gap={1}>
            <Text color={isSelected ? "blueBright" : "gray"}>
              {isSelected ? "▸" : " "}
            </Text>
            <Text color={isSelected ? "white" : "blue"} bold={isSelected}>
              /{cmd.name}
            </Text>
            {cmd.args && (
              <Text color="gray">{cmd.args}</Text>
            )}
            <Text color="gray" dimColor>
              — {cmd.description}
            </Text>
          </Box>
        );
      })}

      {/* Scroll indicator bottom */}
      {hasMore && (
        <Text color="gray" dimColor>
          ↓ more
        </Text>
      )}

      {/* Footer hint */}
      <Box marginTop={0}>
        <Text color="gray" dimColor>
          ↑↓ navigate · Enter select · Esc dismiss
        </Text>
      </Box>
    </Box>
  );
}
