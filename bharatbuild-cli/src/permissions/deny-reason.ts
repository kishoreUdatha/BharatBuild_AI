/**
 * A side channel for explaining a refusal.
 *
 * The approval callback can only answer allow/deny, so a refusal reached the
 * model as a bare "Tool 'write_file' was denied." In plan mode that reads as a
 * transient failure, and the model retries the same call until it runs out of
 * turns. Whoever decides to deny parks the reason here and the dispatcher
 * attaches it to the tool result.
 *
 * This lives in the permissions layer rather than next to the TUI modes that
 * currently set it: the runtime must not import from `ui/`.
 */

let pendingDenyReason: string | null = null;

export function setDenyReason(reason: string | null): void {
  pendingDenyReason = reason;
}

/** Read and clear, so a reason is never attached to an unrelated later denial. */
export function takeDenyReason(): string | null {
  const reason = pendingDenyReason;
  pendingDenyReason = null;
  return reason;
}
