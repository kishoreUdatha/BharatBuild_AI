/** BharatBuild CLI — Model Provider Interface */
import type { ModelClient, ModelChunk } from "../runtime/agent-loop.js";

export interface ModelProviderConfig {
  apiKey?: string;
  baseUrl?: string;
  model: string;
  maxTokens?: number;
}

export abstract class BaseModelProvider implements ModelClient {
  protected config: ModelProviderConfig;
  constructor(config: ModelProviderConfig) { this.config = config; }
  abstract complete(params: {
    model: string; system: string; messages: unknown[]; tools: object[]; maxTokens: number; signal?: AbortSignal;
  }): AsyncIterable<ModelChunk>;
}
