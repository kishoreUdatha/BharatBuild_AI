/** BharatBuild CLI — Cost Calculator */
import { getModelInfo } from "../model-registry.js";
export function calculateCost(modelId: string, inputTokens: number, outputTokens: number): number {
  const info = getModelInfo(modelId);
  if (!info) return 0;
  return (inputTokens / 1000) * info.costPer1kIn + (outputTokens / 1000) * info.costPer1kOut;
}
export function formatCost(usd: number): string {
  if (usd < 0.001) return `$${(usd * 1000).toFixed(3)}m`;
  return `$${usd.toFixed(4)}`;
}
