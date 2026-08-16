/** BharatBuild CLI - Model Registry */
import { MODEL_TIERS } from "../config/constants.js";

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  contextWindow: number;
  costPer1kIn: number;
  costPer1kOut: number;
  supportsTools: boolean;
  /** Kiro credit multiplier relative to Auto (1.0x baseline) */
  creditMultiplier: number;
  /** Whether this model is available on the free tier */
  freeAvailable: boolean;
}

// ── Model Registry — mirrors kiro.dev/docs/models/ exactly ───────────────────
//
// costPer1kIn / costPer1kOut are list-price USD per 1K tokens.
// creditMultiplier is relative to Kiro's Auto baseline (1.0x).
// All Anthropic Claude models go through Anthropic API directly.
// GPT-5.6 models go through OpenAI API.
// Budget open-weight models through their respective provider APIs.
export const MODEL_REGISTRY: ModelInfo[] = [

  // ── Auto ──────────────────────────────────────────────────────────────────
  { id: "auto",                      name: "Auto",                    provider: "auto",      contextWindow: 1000000, costPer1kIn: 0,        costPer1kOut: 0,       supportsTools: true,  creditMultiplier: 1.0,  freeAvailable: true  },

  // ── Claude Haiku ──────────────────────────────────────────────────────────
  { id: MODEL_TIERS.haiku,           name: "Claude Haiku 4.5",        provider: "anthropic", contextWindow: 200000,  costPer1kIn: 0.0008,   costPer1kOut: 0.004,   supportsTools: true,  creditMultiplier: 0.4,  freeAvailable: false },

  // ── Claude Sonnet (newest first) ──────────────────────────────────────────
  { id: MODEL_TIERS.sonnet,          name: "Claude Sonnet 5",         provider: "anthropic", contextWindow: 1000000, costPer1kIn: 0.003,    costPer1kOut: 0.015,   supportsTools: true,  creditMultiplier: 1.3,  freeAvailable: false },
  { id: MODEL_TIERS.sonnet46,        name: "Claude Sonnet 4.6",       provider: "anthropic", contextWindow: 1000000, costPer1kIn: 0.003,    costPer1kOut: 0.015,   supportsTools: true,  creditMultiplier: 1.3,  freeAvailable: false },
  { id: MODEL_TIERS.sonnet45,        name: "Claude Sonnet 4.5",       provider: "anthropic", contextWindow: 200000,  costPer1kIn: 0.003,    costPer1kOut: 0.015,   supportsTools: true,  creditMultiplier: 1.3,  freeAvailable: true  },
  { id: MODEL_TIERS.sonnet40,        name: "Claude Sonnet 4.0",       provider: "anthropic", contextWindow: 200000,  costPer1kIn: 0.003,    costPer1kOut: 0.015,   supportsTools: true,  creditMultiplier: 1.3,  freeAvailable: true  },

  // ── Claude Opus (newest first) ────────────────────────────────────────────
  { id: MODEL_TIERS.opus,            name: "Claude Opus 5",           provider: "anthropic", contextWindow: 1000000, costPer1kIn: 0.015,    costPer1kOut: 0.075,   supportsTools: true,  creditMultiplier: 2.2,  freeAvailable: false },
  { id: MODEL_TIERS.opus48,          name: "Claude Opus 4.8",         provider: "anthropic", contextWindow: 1000000, costPer1kIn: 0.015,    costPer1kOut: 0.075,   supportsTools: true,  creditMultiplier: 2.2,  freeAvailable: false },
  { id: MODEL_TIERS.opus47,          name: "Claude Opus 4.7",         provider: "anthropic", contextWindow: 1000000, costPer1kIn: 0.015,    costPer1kOut: 0.075,   supportsTools: true,  creditMultiplier: 2.2,  freeAvailable: false },
  { id: MODEL_TIERS.opus46,          name: "Claude Opus 4.6",         provider: "anthropic", contextWindow: 1000000, costPer1kIn: 0.015,    costPer1kOut: 0.075,   supportsTools: true,  creditMultiplier: 2.2,  freeAvailable: false },
  { id: MODEL_TIERS.opus45,          name: "Claude Opus 4.5",         provider: "anthropic", contextWindow: 200000,  costPer1kIn: 0.015,    costPer1kOut: 0.075,   supportsTools: true,  creditMultiplier: 2.2,  freeAvailable: false },

  // ── GPT-5.6 (OpenAI) ──────────────────────────────────────────────────────
  { id: MODEL_TIERS.gpt56sol,        name: "GPT-5.6 Sol",             provider: "openai",    contextWindow: 272000,  costPer1kIn: 0.012,    costPer1kOut: 0.048,   supportsTools: true,  creditMultiplier: 2.4,  freeAvailable: false },
  { id: MODEL_TIERS.gpt56terra,      name: "GPT-5.6 Terra",           provider: "openai",    contextWindow: 272000,  costPer1kIn: 0.005,    costPer1kOut: 0.020,   supportsTools: true,  creditMultiplier: 1.0,  freeAvailable: false },
  { id: MODEL_TIERS.gpt56luna,       name: "GPT-5.6 Luna",            provider: "openai",    contextWindow: 272000,  costPer1kIn: 0.0005,   costPer1kOut: 0.002,   supportsTools: true,  creditMultiplier: 0.1,  freeAvailable: false },

  // ── Budget open-weight models ─────────────────────────────────────────────
  { id: MODEL_TIERS.deepseek,        name: "DeepSeek 3.2",            provider: "deepseek",  contextWindow: 128000,  costPer1kIn: 0.00027,  costPer1kOut: 0.0011,  supportsTools: true,  creditMultiplier: 0.25, freeAvailable: true  },
  { id: MODEL_TIERS.minimax25,       name: "MiniMax M2.5",            provider: "minimax",   contextWindow: 200000,  costPer1kIn: 0.00027,  costPer1kOut: 0.0011,  supportsTools: true,  creditMultiplier: 0.25, freeAvailable: true  },
  { id: MODEL_TIERS.minimax21,       name: "MiniMax M2.1",            provider: "minimax",   contextWindow: 200000,  costPer1kIn: 0.00016,  costPer1kOut: 0.00064, supportsTools: true,  creditMultiplier: 0.15, freeAvailable: true  },
  { id: MODEL_TIERS.glm5,            name: "GLM-5",                   provider: "zhipu",     contextWindow: 200000,  costPer1kIn: 0.00054,  costPer1kOut: 0.0022,  supportsTools: true,  creditMultiplier: 0.5,  freeAvailable: true  },
  { id: MODEL_TIERS.qwen3,           name: "Qwen3 Coder Next",        provider: "qwen",      contextWindow: 256000,  costPer1kIn: 0.000054, costPer1kOut: 0.00022, supportsTools: true,  creditMultiplier: 0.05, freeAvailable: true  },
];

export function getModelInfo(id: string): ModelInfo | undefined {
  return MODEL_REGISTRY.find((m) => m.id === id);
}

export function getModelsByProvider(provider: string): ModelInfo[] {
  return MODEL_REGISTRY.filter((m) => m.provider === provider);
}

export function getFreeModels(): ModelInfo[] {
  return MODEL_REGISTRY.filter((m) => m.freeAvailable);
}
