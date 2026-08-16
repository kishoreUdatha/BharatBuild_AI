/** BharatBuild CLI — Token Counter (approximate, no tiktoken dependency) */
export function estimateTokens(text: string): number {
  // ~4 chars per token (rough approximation)
  return Math.ceil(text.length / 4);
}
export function estimateMessageTokens(messages: Array<{ role: string; content: string }>): number {
  return messages.reduce((sum, m) => sum + estimateTokens(m.content) + 4, 0);
}
