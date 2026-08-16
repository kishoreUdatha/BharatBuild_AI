import { getTheme } from "../theme.js";
import { commandsFor, shortcutsFor, type Surface } from "../slash-registry.js";

/**
 * Render help for one surface.
 *
 * Both lists come from the slash registry rather than a local copy, so the
 * panel cannot advertise a command or shortcut that has no handler - it
 * previously listed Shift+Tab, which nothing implemented.
 */
export function renderHelpPanel(surface: Surface = "tui"): void {
  const t = getTheme();

  console.log(t.heading("\n  📖 Slash Commands\n"));
  const commands = commandsFor(surface);
  const width = Math.max(...commands.map((c) => c.name.length + (c.args ? c.args.length + 1 : 0))) + 2;
  for (const c of commands) {
    const label = `/${c.name}${c.args ? " " + c.args : ""}`;
    console.log(`  ${t.info(label.padEnd(width))} ${t.dim(c.description)}`);
  }

  const keys = shortcutsFor(surface);
  if (keys.length > 0) {
    console.log(t.heading("\n  ⌨  Key Shortcuts\n"));
    const kw = Math.max(...keys.map((k) => k.key.length)) + 2;
    for (const k of keys) {
      console.log(`  ${t.warning(k.key.padEnd(kw))} ${t.dim(k.description)}`);
    }
  }
  console.log();
}
