/**
 * Which way model calls are going out.
 *
 * There was no signal at all. `Using direct API key` printed only when you
 * were *not* logged in; being logged in and silently routed through the
 * BharatBuild server printed nothing, so the first indication of which path
 * you were on was a turn failing. When the server's own model account ran out
 * of credit, the error read as though the user's key was dead — and a working
 * key was abandoned on that basis.
 */

import { resolveProviderKey } from "../auth/provider-key.js";

const PROVIDER_NAME: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  gemini: "Gemini",
};

export interface RouteInfo {
  /** "direct" when calling a provider from this machine, "server" via proxy. */
  via: "direct" | "server";
  /** Provider name for a direct call, or the server's host. */
  target: string;
  /**
   * Where a direct key came from: the variable name, or "stored key". A key
   * left in a shell profile is otherwise invisible and explains a session that
   * bypasses the server without being asked to.
   */
  source?: string;
}

export function modelRoute(
  proxied: boolean,
  env: NodeJS.ProcessEnv = process.env,
  serverHost?: string,
): RouteInfo {
  if (!proxied) {
    const key = resolveProviderKey(env);
    if (key) {
      return {
        via: "direct",
        target: PROVIDER_NAME[key.provider] ?? key.provider,
        source: key.from === "env" ? key.envVar : "stored key",
      };
    }
    // Not proxied and no key: a local provider such as ollama, or a config
    // that will fail on the first call. Either way it is not going to a server.
    return { via: "direct", target: "local provider" };
  }
  return { via: "server", target: serverHost ?? "BharatBuild server" };
}

/** One line for the startup banner. */
export function describeRoute(route: RouteInfo, model: string): string {
  if (route.via === "direct") {
    const via = route.source ? `direct to ${route.target} (${route.source})` : `direct to ${route.target}`;
    return `model: ${model} · ${via}`;
  }
  return `model: ${model} · via ${route.target} (credits billed to your account)`;
}
