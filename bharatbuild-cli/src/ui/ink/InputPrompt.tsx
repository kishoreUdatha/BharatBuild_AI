/**
 * InputPrompt — Bottom input area with ❯ prompt and slash command suggestions.
 *
 * When the user types /, a SlashOverlay appears above the input.
 */

import React, { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { Box, Text, useInput, useStdout } from "ink";
import TextInput from "ink-text-input";
import { SlashOverlay, type SlashItem } from "./SlashOverlay.js";
import { commandsFor } from "../slash-registry.js";
import { loadCustomCommands } from "../custom-commands.js";
import { fuzzyRank, commonPrefix } from "./fuzzy.js";
import { getInkTheme } from "./theme.js";
import { getGlyphs } from "./glyphs.js";
import {
  loadHistory, saveHistory, pushEntry, newCursor, historyUp, historyDown,
  beginSearch, searchType, searchBackspace, searchOlder, searchValue, searchLabel,
  type HistoryCursor, type SearchState,
} from "./prompt-history.js";
import { activeMention, applyMention } from "./file-mentions.js";
import { listProjectFiles } from "./file-index.js";

export interface InputPromptProps {
  onSubmit: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  /** Text to drop into the box (from /paste, /reply). */
  prefill?: string | undefined;
  onPrefillConsumed?: () => void;
  /** Lets the App bind Esc to interrupt only when the palette is closed. */
  onOverlayChange?: (open: boolean) => void;
  /**
   * Where prompt history is stored. Tests point this at a temp directory so
   * they neither read the developer's real history nor write to it.
   */
  historyCwd?: string;
}

export function InputPrompt({
  onSubmit,
  placeholder = "Type a message or / for commands...",
  disabled = false,
  prefill,
  onPrefillConsumed,
  onOverlayChange,
  historyCwd,
}: InputPromptProps): React.ReactElement {
  const t = getInkTheme();
  const { stdout } = useStdout();
  const ruleWidth = (stdout?.columns ?? 80) - 2;
  const [value, setValue] = useState("");
  const [slashVisible, setSlashVisible] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  /**
   * ink-text-input tracks the caret internally and does not move it when the
   * value is replaced from outside. After Tab-completion the caret stayed
   * where it was, so the next keystroke landed mid-word ("/usageckpoint").
   * Bumping this key remounts the input, which puts the caret at the end.
   */
  const [inputKey, setInputKey] = useState(0);
  const setValueExternally = useCallback((next: string) => {
    setValue(next);
    setInputKey((k) => k + 1);
  }, []);

  /**
   * Prompt history. Read once on mount — re-reading per keystroke would hit
   * the disk on every arrow press, and the file only changes when this session
   * writes it.
   */
  const [cursor, setCursor] = useState<HistoryCursor>(() => newCursor(loadHistory(historyCwd)));
  // Held in a ref as well so the submit handler can append without listing the
  // cursor as a dependency, which would rebuild the handler on every arrow key.
  const cursorRef = useRef(cursor);
  cursorRef.current = cursor;

  /**
   * ctrl+r search, or null when not searching.
   *
   * The arrow keys walk history one step at a time, which is fine for the last
   * prompt and useless for one from forty turns ago. This is the shell gesture
   * for the same problem, over history that was already being stored.
   */
  const [search, setSearch] = useState<SearchState | null>(null);
  const searchRef = useRef(search);
  searchRef.current = search;

  // Accept text handed over by a command.
  useEffect(() => {
    if (prefill === undefined) return;
    setValueExternally(prefill);
    setSlashVisible(false);
    onPrefillConsumed?.();
  }, [prefill, onPrefillConsumed, setValueExternally]);

  // Get TUI slash commands
  const slashItems: SlashItem[] = useMemo(() => {
    const built = commandsFor("tui").map((c) => ({
      name: c.name, description: c.description, args: c.args,
    }));
    // Project and user .toml commands sit alongside the built-in ones — a
    // command defined by the repo you are in should be as discoverable as
    // /help, not something you have to remember exists.
    const custom = loadCustomCommands(historyCwd).commands.map((c) => ({
      name: c.name, description: c.description,
    }));
    return [...built, ...custom];
  }, [historyCwd]);

  /**
   * Filter here rather than inside the overlay: the prompt needs the match
   * count to decide whether Enter belongs to the overlay or to the text input.
   * Subsequence matching means `/ckpt` still finds `/checkpoint`.
   */
  const filtered = useMemo(() => {
    const q = value.toLowerCase().replace(/^\//, "");
    return fuzzyRank(slashItems, q);
  }, [value, slashItems]);

  /**
   * `@` file completion.
   *
   * Reuses the slash overlay rather than adding a second list widget: two
   * pickers that look different for the same gesture would be a difference
   * without a reason.
   */
  const mention = useMemo(() => activeMention(value), [value]);
  const mentionItems: SlashItem[] = useMemo(() => {
    if (!mention) return [];
    const files = listProjectFiles(historyCwd);
    // Ranked by the same matcher as commands, then capped — a bare `@` on a
    // large repo would otherwise rank twenty thousand paths on each keystroke.
    const items: SlashItem[] = files.map((f) => ({ name: f, description: "" }));
    return fuzzyRank(items, mention.query).slice(0, 50);
  }, [mention, historyCwd]);

  // The overlay picks a command; once the user types a space they are writing
  // arguments, so it gets out of the way.
  const slashOpen = slashVisible && !value.includes(" ") && filtered.length > 0;
  const mentionOpen = mention !== null && mentionItems.length > 0;
  // A mention can only be open when a slash command is not being typed, so the
  // two never compete for Enter.
  const overlayOpen = slashOpen || mentionOpen;
  /** `!command` goes straight to the shell, so the prompt says so. */
  const bashMode = value.startsWith("!");
  const items = mentionOpen ? mentionItems : filtered;
  const safeIndex = Math.min(selectedIndex, Math.max(0, items.length - 1));

  // Once the overlay closes for arguments, keep the signature on screen so the
  // user is not guessing what `/checkpoint` expects next.
  const argHint = useMemo(() => {
    if (!value.startsWith("/") || !value.includes(" ")) return undefined;
    const typed = value.slice(1).split(/\s+/)[0]?.toLowerCase();
    const match = slashItems.find((c) => c.name === typed);
    return match?.args ? match : undefined;
  }, [value, slashItems]);

  useEffect(() => {
    onOverlayChange?.(overlayOpen);
  }, [overlayOpen, onOverlayChange]);

  const handleChange = useCallback((newValue: string) => {
    setValue(newValue);
    setSlashVisible(newValue.startsWith("/"));
    setSelectedIndex(0);
  }, []);

  const handleSubmit = useCallback(
    (submitted: string) => {
      // While the overlay owns Enter, ignore the text input's submit — both
      // fired before, sending every slash command twice.
      if (overlayOpen) return;
      if (!submitted.trim()) return;
      onSubmit(submitted.trim());

      // Record before clearing, and reset the cursor: after sending, up should
      // recall what was just sent rather than resume wherever browsing stopped.
      const entries = pushEntry(cursorRef.current.entries, submitted);
      setCursor(newCursor(entries));
      saveHistory(entries, historyCwd);

      setValueExternally("");
      setSlashVisible(false);
      setSelectedIndex(0);
    },
    [onSubmit, overlayOpen, setValueExternally, historyCwd],
  );

  /**
   * ctrl+r opens reverse search; while it is open it owns the keyboard.
   *
   * Enter accepts the match, Esc restores what was being typed, and a further
   * ctrl+r steps to the next older match — the behaviour anyone who has used a
   * shell already expects.
   */
  useInput(
    (input, key) => {
      const entries = cursorRef.current.entries;
      const state = searchRef.current;

      if (!state) {
        if (key.ctrl && input === "r") {
          setSearch(beginSearch(value));
          return;
        }
        return;
      }

      if (key.ctrl && input === "r") { setSearch(searchOlder(state, entries)); return; }
      if (key.escape) {
        // Cancel puts back exactly what was in the box before searching.
        setValueExternally(state.draft);
        setSearch(null);
        return;
      }
      if (key.return) {
        setValueExternally(searchValue(state, entries));
        setSearch(null);
        return;
      }
      if (key.backspace || key.delete) { setSearch(searchBackspace(state, entries)); return; }
      // Whole runs, not single keys: a paste — and ink in a test harness —
      // delivers several characters in one event, and dropping all but the
      // first silently swallowed most of the query. Control characters are
      // filtered out so an escape sequence cannot become query text.
      if (input && !key.ctrl && !key.meta) {
        const printable = [...input].filter((c) => c >= " " && c !== "").join("");
        if (printable) setSearch(searchType(state, entries, printable));
      }
    },
    { isActive: !disabled },
  );

  /**
   * Up and down walk history when the palette is closed.
   *
   * While the palette is open those keys belong to it — moving through
   * commands and moving through history are both plausible readings of the
   * same press, and the visible list wins.
   */
  useInput(
    (_input, key) => {
      if (!key.upArrow && !key.downArrow) return;
      const move = key.upArrow ? historyUp(cursorRef.current, value) : historyDown(cursorRef.current, value);
      if (!move.handled) return;
      setCursor(move.cursor);
      // Externally, so the caret lands at the end of the recalled text rather
      // than staying where it was and typing into the middle of it.
      setValueExternally(move.value);
      setSlashVisible(move.value.startsWith("/"));
    },
    { isActive: !overlayOpen && !disabled && search === null },
  );

  const handleSlashSelect = useCallback(
    (cmd: SlashItem) => {
      // A file completes into the box; it is part of a sentence the user is
      // still writing, never something to send on its own.
      if (mentionOpen && mention) {
        setValueExternally(applyMention(value, mention, cmd.name));
        setSelectedIndex(0);
        return;
      }

      // A command that takes arguments completes into the box instead of
      // firing immediately — picking /model off the list with no value would
      // be useless. But if the whole name is already typed, the user has
      // chosen it deliberately: run it and let the handler show its default.
      const alreadyTyped = value.trim().toLowerCase() === `/${cmd.name}`;
      if (cmd.args && !alreadyTyped) {
        setValueExternally(`/${cmd.name} `);
        setSlashVisible(false);
        setSelectedIndex(0);
        return;
      }
      setValueExternally("");
      setSlashVisible(false);
      setSelectedIndex(0);
      onSubmit(`/${cmd.name}`);
    },
    [onSubmit, setValueExternally, value, mentionOpen, mention],
  );

  // Tab completes to the longest unambiguous prefix, like a shell.
  useInput(
    (_input, key) => {
      // shift+tab cycles the permission mode. It arrives here as key.tab too,
      // so without this it would complete a command *and* change the mode.
      if (!key.tab || key.shift) return;
      const names = items.map((c) => c.name);
      if (names.length === 0) return;

      // Completing a path shares the gesture but not the prefix: a file is
      // written into the mention, not after a leading slash.
      if (mentionOpen && mention) {
        const target = names.length === 1 ? names[0]! : commonPrefix(names);
        if (!target) return;
        setValueExternally(
          names.length === 1
            ? applyMention(value, mention, target)
            // Several matches: fill in as far as they agree and keep the list
            // up so the next keystroke narrows it further.
            : `${value.slice(0, mention.start)}@${target}`,
        );
        setSelectedIndex(0);
        return;
      }

      const target = names.length === 1 ? names[0]! : commonPrefix(names);
      if (target && `/${target}` !== value) {
        setValueExternally(`/${target}${names.length === 1 ? " " : ""}`);
        setSelectedIndex(0);
      }
    },
    { isActive: overlayOpen && !disabled },
  );

  const handleSlashDismiss = useCallback(() => {
    setSlashVisible(false);
  }, []);

  const handleSlashNavigate = useCallback(
    (direction: "up" | "down") => {
      setSelectedIndex((prev) => {
        // Clamp against the list actually on screen, not the full registry.
        const maxIdx = Math.max(0, items.length - 1);
        if (direction === "up") return Math.max(0, prev - 1);
        return Math.min(maxIdx, prev + 1);
      });
    },
    [items.length],
  );

  return (
    <Box flexDirection="column">
      {/* Slash overlay (appears above input) */}
      <SlashOverlay
        filter=""
        commands={items}
        prefix={mentionOpen ? "@" : "/"}
        selectedIndex={safeIndex}
        onSelect={handleSlashSelect}
        onDismiss={handleSlashDismiss}
        onNavigate={handleSlashNavigate}
        visible={overlayOpen}
      />

      {/* The shell's own reverse-search line, in the shape it has had for
          decades — the query, and the match it currently points at. */}
      {search && (
        <Box paddingX={1}>
          <Text color={t.warning}>
            {searchLabel(search, cursorRef.current.entries)}
          </Text>
          <Text color={t.text}>
            {" "}{searchValue(search, cursorRef.current.entries)}
          </Text>
        </Box>
      )}

      {/* A framed prompt, the way claude-code encloses its input. */}
      <Box
        borderStyle="round"
        // The frame turns while a command is being typed, so it is obvious
        // that Enter will run the shell rather than start a model turn.
        borderColor={disabled ? t.muted : bashMode ? t.warning : t.border}
        paddingX={1}
        width="100%"
      >
        <Text color={disabled ? t.muted : bashMode ? t.warning : t.text} bold>
          {bashMode ? "! " : "> "}
        </Text>
        {search ? (
          /* The text input is stood down while searching. Left mounted it
             also received the query keys, so ctrl+r then "valid" left
             "rvalid" in the box behind the search line. */
          <Text color={t.text}>{searchValue(search, cursorRef.current.entries)}</Text>
        ) : disabled ? (
          <Text color={t.muted} italic>
            waiting…
          </Text>
        ) : (
          <TextInput
            key={inputKey}
            value={value}
            onChange={handleChange}
            onSubmit={handleSubmit}
            placeholder={placeholder}
          />
        )}
      </Box>

      {/* Signature hint once the overlay has stepped aside for arguments */}
      {argHint && (
        <Box paddingX={1}>
          <Text color={t.muted} dimColor>
            /{argHint.name} {argHint.args}  —  {argHint.description}
          </Text>
        </Box>
      )}
    </Box>
  );
}
