/**
 * Subsequence matching for the command palette.
 *
 * Plain `includes()` meant `/ckpt` found nothing, so anyone who did not know a
 * command's exact spelling had to scroll the full list. Ranking prefers a
 * prefix hit, then a contiguous substring, then a scattered subsequence, and
 * finally a description-only match.
 */

export interface Rankable {
  name: string;
  description: string;
  args?: string;
}

const enum Tier {
  Prefix = 0,
  Substring = 1,
  Subsequence = 2,
  Description = 3,
}

/** Position of each query char in `text`, or null when not a subsequence. */
function subsequenceSpan(text: string, query: string): number | null {
  let ti = 0;
  let first = -1;
  let last = -1;
  for (const ch of query) {
    const found = text.indexOf(ch, ti);
    if (found === -1) return null;
    if (first === -1) first = found;
    last = found;
    ti = found + 1;
  }
  // Tighter spans rank higher: "ckpt" in "checkpoint" beats a scattered match.
  return last - first;
}

export function fuzzyRank<T extends Rankable>(items: T[], query: string): T[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;

  const scored: Array<{ item: T; tier: Tier; span: number }> = [];

  for (const item of items) {
    const name = item.name.toLowerCase();

    if (name.startsWith(q)) {
      scored.push({ item, tier: Tier.Prefix, span: name.length });
      continue;
    }
    if (name.includes(q)) {
      scored.push({ item, tier: Tier.Substring, span: name.indexOf(q) });
      continue;
    }
    const span = subsequenceSpan(name, q);
    if (span !== null) {
      scored.push({ item, tier: Tier.Subsequence, span });
      continue;
    }
    if (item.description.toLowerCase().includes(q)) {
      scored.push({ item, tier: Tier.Description, span: 0 });
    }
  }

  return scored
    .sort((a, b) => a.tier - b.tier || a.span - b.span || a.item.name.localeCompare(b.item.name))
    .map((s) => s.item);
}

/** Longest prefix shared by every candidate — what Tab completes to. */
export function commonPrefix(names: string[]): string {
  if (names.length === 0) return "";
  let prefix = names[0]!;
  for (const n of names.slice(1)) {
    let i = 0;
    while (i < prefix.length && i < n.length && prefix[i] === n[i]) i++;
    prefix = prefix.slice(0, i);
    if (!prefix) break;
  }
  return prefix;
}
