/** BharatBuild CLI — AWS Bedrock Provider */
import type { ModelChunk } from "../../runtime/agent-loop.js";
import { BaseModelProvider, type ModelProviderConfig } from "../model-provider.js";

export class BedrockProvider extends BaseModelProvider {
  constructor(config: ModelProviderConfig) { super(config); }
  async *complete(params: { model: string; system: string; messages: unknown[]; tools: object[]; maxTokens: number; signal?: AbortSignal }): AsyncIterable<ModelChunk> {
    // Bedrock requires AWS SDK — provide guidance
    throw new Error(
      "AWS Bedrock provider requires @aws-sdk/client-bedrock-runtime.\n" +
      "Install: npm install @aws-sdk/client-bedrock-runtime\n" +
      "Set: AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    );
    yield { type: "stop", stopReason: "end_turn" }; // unreachable, satisfies TS
  }
}
