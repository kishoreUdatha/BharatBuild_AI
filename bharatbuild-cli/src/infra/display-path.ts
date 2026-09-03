/**
 * Shortening a path for display.
 *
 * Tool cards showed the absolute path the model happened to send:
 *
 *   ● write_file(C:\Users\user\PalindromeChecker.java)
 *
 * Most of that is noise — the interesting part is which file inside the
 * project changed. The reference CLIs show it relative to the working
 * directory, which is also how anyone would refer to it in conversation.
 *
 * Display only. Nothing here is fed back to a tool: shortening a path that a
 * later call then resolves from a different working directory is how an edit
 * lands in the wrong file.
 */

import path from "node:path";
import os from "node:os";

/**
 * `filePath` relative to `cwd` when it sits inside it, otherwise the shortest
 * honest form.
 *
 * A path outside the project keeps enough of itself to stay unambiguous —
 * collapsing `/etc/hosts` to `hosts` would hide exactly the case worth
 * noticing. `~` is used for the home directory, which is conventional and
 * still unmistakable.
 */
export function displayPath(filePath: string, cwd: string = process.cwd()): string {
  if (!filePath) return filePath;

  let absolute: string;
  try {
    absolute = path.resolve(cwd, filePath);
  } catch {
    return filePath;
  }

  const relative = path.relative(cwd, absolute);

  // Inside the working directory: use the relative form. `path.relative`
  // returns "" for the directory itself, and starts with ".." for anything
  // above it.
  if (relative && !relative.startsWith("..") && !path.isAbsolute(relative)) {
    return relative.split(path.sep).join("/");
  }

  // Outside it: fall back to ~ for the home directory, else leave it alone.
  const home = os.homedir();
  if (home && absolute.toLowerCase().startsWith(home.toLowerCase())) {
    const fromHome = path.relative(home, absolute).split(path.sep).join("/");
    return fromHome ? `~/${fromHome}` : "~";
  }

  return filePath;
}

/** True when the value looks like a path rather than a command or a query. */
export function looksLikePath(value: string): boolean {
  if (!value) return false;
  // A command has spaces and usually no separator; a path has a separator or a
  // file extension and no spaces around it.
  if (/[\\/]/.test(value) && !/\s{2,}/.test(value)) return true;
  return /^[\w.-]+\.[A-Za-z0-9]{1,8}$/.test(value);
}
