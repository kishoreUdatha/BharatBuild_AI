export interface KeyBinding {
  key: string;
  ctrl?: boolean;
  description: string;
  action: string;
}

export const DEFAULT_KEY_BINDINGS: KeyBinding[] = [
  { key: "c", ctrl: true, description: "Cancel / interrupt", action: "cancel" },
  { key: "d", ctrl: true, description: "Exit", action: "exit" },
  { key: "l", ctrl: true, description: "Clear screen", action: "clear" },
  { key: "r", ctrl: true, description: "Retry last message", action: "retry" },
  { key: "u", ctrl: true, description: "Clear input line", action: "clear-input" },
  { key: "Up", description: "Previous history", action: "history-prev" },
  { key: "Down", description: "Next history", action: "history-next" },
];

export function printKeyBindings() {
  console.log("\n  Key Bindings:");
  for (const kb of DEFAULT_KEY_BINDINGS) {
    const key = kb.ctrl ? `Ctrl+${kb.key.toUpperCase()}` : kb.key;
    console.log(`    ${key.padEnd(12)} ${kb.description}`);
  }
  console.log();
}
