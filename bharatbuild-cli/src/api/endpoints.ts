/**
 * Backend paths, in one place.
 *
 * `ask` and `plan` each hard-coded "/api/v1/chat/stream", which the backend
 * does not serve — both commands failed with a bare "Not Found". The router
 * mounts the agentic endpoints under "/agentic", which proxy-model.ts already
 * knew; the knowledge just wasn't shared, so two copies went stale.
 *
 * Anything added here should be checked against the backend's openapi.json
 * rather than assumed.
 */

/** Streaming agentic conversation — the endpoint the CLI's model calls go to. */
export const AGENTIC_CHAT_STREAM = "/api/v1/agentic/chat/stream";

/** Non-streaming variant of the same. */
export const AGENTIC_CHAT = "/api/v1/agentic/chat";

/** Tool definitions the server advertises. */
export const AGENTIC_TOOLS = "/api/v1/agentic/tools";
