/**
 * Whose account is the provider complaining about?
 *
 * Provider errors are written for whoever holds the API key. On the proxy path
 * that is the BharatBuild server, not the person reading the screen — so
 * relaying "Your credit balance is too low… go to Plans & Billing" verbatim
 * sent the user to their own billing page to fix an account that was not at
 * fault. It cost a real debugging session: a working key was assumed dead
 * because the message said "your".
 */
import { describe, it, expect } from "vitest";
import { readableModelError } from "../../src/api/proxy-model.js";

/** Exactly what the backend relayed, Python repr and all. */
const REAL_CREDIT_ERROR =
  "Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', " +
  "'message': 'Your credit balance is too low to access the Anthropic API. " +
  "Please go to Plans & Billing to upgrade or purchase credits.'}}";

describe("an error about the key holder's account", () => {
  it("says the account is the server's", () => {
    const out = readableModelError(REAL_CREDIT_ERROR);
    expect(out).toMatch(/server's/i);
    expect(out).toMatch(/not yours/i);
  });

  it("keeps the provider's own wording, quoted", () => {
    // The original text still matters — it is what to search for and what
    // support will ask about. It just must not be the whole message.
    expect(readableModelError(REAL_CREDIT_ERROR)).toContain("credit balance is too low");
  });

  it("points at the way out", () => {
    // Without this the user can only wait; the direct-key path is right there.
    //
    // It names the stored-key command rather than the environment variable.
    // Telling someone to export a variable failed three times in a row for a
    // real user: it has to be set again in every terminal and does nothing for
    // a window already open, so the advice looked correct and did not work.
    expect(readableModelError(REAL_CREDIT_ERROR)).toContain("bharatbuild key set");
  });

  it("covers the other account-level rejections", () => {
    for (const msg of [
      "{'message': 'You have exceeded your quota'}",
      "{'message': 'Rate limit exceeded for this organization'}",
      "{'message': 'Please update your billing details'}",
    ]) {
      expect(readableModelError(msg), msg).toMatch(/server's/i);
    }
  });
});

describe("an error about this request", () => {
  it("is left exactly as the provider wrote it", () => {
    // A bad request or an oversized context is about what was just sent, not
    // about anyone's account, and reads correctly on its own.
    const msg = "{'message': 'max_tokens: must be less than or equal to 8192'}";
    expect(readableModelError(msg)).toBe("max_tokens: must be less than or equal to 8192");
  });

  it("does not rewrite a context-length error", () => {
    const msg = "{'message': 'prompt is too long: 250000 tokens > 200000 maximum'}";
    expect(readableModelError(msg)).not.toMatch(/server's/i);
  });

  it("still handles a reply with no message field", () => {
    expect(readableModelError("something went wrong")).toBe("something went wrong");
  });

  it("still handles an empty reply", () => {
    expect(readableModelError("")).toMatch(/without giving a reason/i);
  });
});
