/**
 * InputPrompt — Bottom input area with ❯ prompt and slash command suggestions.
 *
 * When the user types /, a SlashOverlay appears above the input.
 */

import React, { useState, useCallback } from "react";
import { Box, Text } from "ink";
import TextInput from "ink-text-input";
import { SlashOverlay, type SlashItem } from "./SlashOverlay.js";
import { SLASH_COMMANDS, commandsFor } from "../slash-registry.js";

export interface InputPromptProps {
  onSubmit: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function InputPrompt({
  onSubmit,
  placeholder = "Type a message or / for commands...",
  disabled = false,
}: InputPromptProps): React.ReactElement {
  const [value, setValue] = useState("");
  const [slashVisible, setSlashVisible] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Get TUI slash commands
  const slashItems: SlashItem[] = commandsFor("tui").map((c) => ({
    name: c.name,
    description: c.description,
    args: c.args,
  }));

  const handleChange = useCallback((newValue: string) => {
    setValue(newValue);
    // Show slash overlay when input starts with /
    if (newValue.startsWith("/")) {
      setSlashVisible(true);
      setSelectedIndex(0);
    } else {
      setSlashVisible(false);
    }
  }, []);

  const handleSubmit = useCallback(
    (submitted: string) => {
      if (!submitted.trim()) return;
      onSubmit(submitted.trim());
      setValue("");
      setSlashVisible(false);
      setSelectedIndex(0);
    },
    [onSubmit],
  );

  const handleSlashSelect = useCallback(
    (cmd: SlashItem) => {
      const fullCmd = `/${cmd.name}`;
      setValue("");
      setSlashVisible(false);
      setSelectedIndex(0);
      onSubmit(fullCmd);
    },
    [onSubmit],
  );

  const handleSlashDismiss = useCallback(() => {
    setSlashVisible(false);
  }, []);

  const handleSlashNavigate = useCallback(
    (direction: "up" | "down") => {
      setSelectedIndex((prev) => {
        const maxIdx = slashItems.length - 1;
        if (direction === "up") return Math.max(0, prev - 1);
        return Math.min(maxIdx, prev + 1);
      });
    },
    [slashItems.length],
  );

  return (
    <Box flexDirection="column">
      {/* Slash overlay (appears above input) */}
      <SlashOverlay
        filter={value}
        commands={slashItems}
        selectedIndex={selectedIndex}
        onSelect={handleSlashSelect}
        onDismiss={handleSlashDismiss}
        onNavigate={handleSlashNavigate}
        visible={slashVisible}
      />

      {/* Input line */}
      <Box
        borderStyle="single"
        borderColor={disabled ? "gray" : "green"}
        paddingX={1}
        width="100%"
      >
        <Text color={disabled ? "gray" : "green"} bold>
          ❯{" "}
        </Text>
        {disabled ? (
          <Text color="gray" italic>
            waiting...
          </Text>
        ) : (
          <TextInput
            value={value}
            onChange={handleChange}
            onSubmit={handleSubmit}
            placeholder={placeholder}
          />
        )}
      </Box>
    </Box>
  );
}
