export interface Message { role: "user" | "assistant"; content: string; }

export function compactMessages(messages: Message[], maxTokens = 80000): Message[] {
  const estimate = (m: Message) => Math.ceil(m.content.length / 4);
  let total = messages.reduce((s, m) => s + estimate(m), 0);
  if (total <= maxTokens) return messages;

  // Keep first system message + last N messages that fit
  const result: Message[] = [];
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]!;
    const t = estimate(m);
    if (total - t >= maxTokens && i > 0) { total -= t; continue; }
    result.unshift(m);
  }
  if (result.length < messages.length) {
    result.unshift({ role: "assistant", content: "[Earlier conversation compacted to fit context window]" });
  }
  return result;
}

export function shouldCompact(messages: Message[], threshold = 0.8, maxTokens = 100000): boolean {
  const total = messages.reduce((s, m) => s + Math.ceil(m.content.length / 4), 0);
  return total > maxTokens * threshold;
}
