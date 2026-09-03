/**
 * Naming the model that actually answered.
 *
 * The backend's local profile routes sonnet and opus to haiku on purpose, to
 * keep development off paid tiers. That is a reasonable choice, but it was
 * silent: the status bar showed "sonnet" while haiku wrote the reply, so a
 * weaker answer looked like a Sonnet answer. Showing the substitution keeps the
 * saving and removes the lie.
 */

/**
 * Shorten a provider model id for a status bar.
 * "claude-haiku-4-5" -> "haiku-4.5", "claude-sonnet-5" -> "sonnet-5".
 */
export function shortModelName(id: string): string {
  if (!id) return "";
  const stripped = id
    .replace(/^(us|eu|apac)\./, "")           // bedrock region prefix
    .replace(/^anthropic\./, "")
    .replace(/^claude-/, "")
    .replace(/-v\d+:\d+$/, "")                // bedrock version suffix
    .replace(/-\d{8}$/, "");                  // dated snapshot
  // Versions are written 4-5 on the wire and 4.5 everywhere a human reads them.
  return stripped.replace(/(\d)-(\d)/g, "$1.$2");
}

/**
 * What to show for the model, given what was asked for and what answered.
 * Returns just the request when they agree, or "asked→served" when they differ.
 */
export function modelLabel(requested: string, served?: string | null): string {
  if (!served) return requested;

  const shortServed = shortModelName(served);
  const shortAsked = shortModelName(requested);
  if (!shortServed) return requested;

  // "auto" means the user expressed no preference, so naming the winner is
  // information rather than a discrepancy.
  if (requested === "auto") return `auto→${shortServed}`;

  // Same family and version: nothing was substituted, keep it short.
  if (shortAsked === shortServed) return requested;

  // A request for "sonnet" served by "sonnet-5" is the same model named
  // loosely, not a substitution worth flagging.
  if (shortServed.startsWith(`${shortAsked}-`)) return requested;

  return `${requested}→${shortServed}`;
}

/** True when the served model is a different family from the one requested. */
export function isSubstituted(requested: string, served?: string | null): boolean {
  if (!served || requested === "auto") return false;
  const a = shortModelName(requested);
  const s = shortModelName(served);
  return !!a && !!s && a !== s && !s.startsWith(`${a}-`);
}
