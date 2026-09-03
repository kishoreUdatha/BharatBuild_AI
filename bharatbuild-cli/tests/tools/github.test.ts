/**
 * GitHub tools, built on the gh CLI.
 *
 * Nothing here touches GitHub. Argument building is tested directly, because a
 * test that opens real pull requests is not one anyone can run twice — and the
 * point of these tools is that they publish, which is exactly what a test
 * suite must not do.
 *
 * The approval rule gets the most attention: every other tool changes this
 * machine, while these are visible to everyone on the repository and cannot be
 * quietly undone.
 */
import { describe, it, expect } from "vitest";
import { buildIssueArgs, buildPrArgs, GITHUB_WRITE_ACTIONS } from "../../src/tools/github/index.js";
import { explainGhFailure } from "../../src/tools/github/gh-cli.js";
import { isPublishingAction } from "../../src/permissions/plan-mode.js";
import { checkPermission } from "../../src/permissions/permission-manager.js";

const args = (r: { args: string[] } | { error: string }): string[] => {
  if ("error" in r) throw new Error(`expected args, got error: ${r.error}`);
  return r.args;
};
const error = (r: { args: string[] } | { error: string }): string => {
  if ("args" in r) throw new Error(`expected an error, got args: ${r.args.join(" ")}`);
  return r.error;
};

describe("issue arguments", () => {
  it("lists open issues by default", () => {
    const a = args(buildIssueArgs({ action: "list" }));
    expect(a.slice(0, 2)).toEqual(["issue", "list"]);
    expect(a).toContain("open");
  });

  it("creates with a title and body", () => {
    const a = args(buildIssueArgs({ action: "create", title: "Crash on save", body: "Steps..." }));
    expect(a).toEqual(expect.arrayContaining(["issue", "create", "--title", "Crash on save", "--body", "Steps..."]));
  });

  it("passes each label separately", () => {
    // gh takes --label once per label; joining them with commas creates one
    // label literally named "bug,urgent".
    const a = args(buildIssueArgs({ action: "create", title: "t", labels: ["bug", "urgent"] }));
    expect(a.filter((x) => x === "--label")).toHaveLength(2);
    expect(a).toContain("bug");
    expect(a).toContain("urgent");
  });

  it("targets another repository when asked", () => {
    const a = args(buildIssueArgs({ action: "list", repo: "owner/name" }));
    expect(a).toEqual(expect.arrayContaining(["--repo", "owner/name"]));
  });

  it("refuses to view without a number", () => {
    expect(error(buildIssueArgs({ action: "view" }))).toMatch(/number.*required/i);
  });

  it("refuses to comment without a body", () => {
    expect(error(buildIssueArgs({ action: "comment", number: 4 }))).toMatch(/body.*required/i);
  });

  it("refuses to create without a title", () => {
    expect(error(buildIssueArgs({ action: "create" }))).toMatch(/title.*required/i);
  });
});

describe("pull request arguments", () => {
  it("creates with base and head", () => {
    const a = args(buildPrArgs({ action: "create", title: "Fix", base: "main", head: "fix/auth" }));
    expect(a).toEqual(expect.arrayContaining(["pr", "create", "--base", "main", "--head", "fix/auth"]));
  });

  it("opens a draft when asked", () => {
    expect(args(buildPrArgs({ action: "create", title: "t", draft: true }))).toContain("--draft");
  });

  it("does not pass --draft otherwise", () => {
    expect(args(buildPrArgs({ action: "create", title: "t" }))).not.toContain("--draft");
  });

  it("can show a diff and the checks", () => {
    expect(args(buildPrArgs({ action: "diff", number: 7 }))).toEqual(expect.arrayContaining(["pr", "diff", "7"]));
    expect(args(buildPrArgs({ action: "checks", number: 7 }))).toEqual(expect.arrayContaining(["pr", "checks", "7"]));
  });

  it("refuses a diff without a number", () => {
    expect(error(buildPrArgs({ action: "diff" }))).toMatch(/number.*required/i);
  });
});

describe("arguments are passed as an array, never a shell string", () => {
  it("keeps a title with shell metacharacters intact", () => {
    // gh is invoked with shell:false, so this stays one argument instead of
    // becoming a second command.
    const nasty = 'Fix "quoting"; rm -rf /';
    const a = args(buildIssueArgs({ action: "create", title: nasty }));
    expect(a).toContain(nasty);
    expect(a.filter((x) => x === nasty)).toHaveLength(1);
  });
});

describe("publishing needs confirmation", () => {
  it("classifies the writing actions", () => {
    for (const action of GITHUB_WRITE_ACTIONS) {
      expect(isPublishingAction("github_issue", { action }), action).toBe(true);
      expect(isPublishingAction("github_pr", { action }), action).toBe(true);
    }
  });

  it("leaves reading alone", () => {
    for (const action of ["list", "view", "diff", "checks"]) {
      expect(isPublishingAction("github_pr", { action }), action).toBe(false);
    }
  });

  it("does not sweep up other tools", () => {
    expect(isPublishingAction("write_file", { action: "create" })).toBe(false);
  });

  it("asks before creating an issue even in auto mode", async () => {
    // Auto-accept was chosen for local edits, not for posting under the user's
    // name to a repository other people can see. With no way to ask — a
    // headless run — the answer has to be no.
    const decision = await checkPermission(
      "github_issue",
      { action: "create", title: "t" },
      { permissionMode: "auto", nonInteractive: true } as never,
    );
    expect(decision).toBe("deny");
  });

  it("still lists issues without asking", async () => {
    const decision = await checkPermission(
      "github_issue",
      { action: "list" },
      { permissionMode: "auto", nonInteractive: true } as never,
    );
    expect(decision).toBe("allow");
  });
});

describe("failures say what actually went wrong", () => {
  const fail = (stderr: string) => explainGhFailure({ ok: false, stdout: "", stderr });

  it("names a missing repository", () => {
    expect(fail("could not determine base repository")).toMatch(/no github repository/i);
  });

  it("names an auth problem", () => {
    expect(fail("HTTP 401: Bad credentials")).toMatch(/gh auth login/i);
  });

  it("distinguishes permission from not-found", () => {
    expect(fail("HTTP 403: Forbidden")).toMatch(/permission/i);
    expect(fail("HTTP 404: Not Found")).toMatch(/not found/i);
  });

  it("explains an empty pull request", () => {
    expect(fail("No commits between main and feature")).toMatch(/nothing to open/i);
  });

  it("falls back to the raw message rather than swallowing it", () => {
    expect(fail("something unexpected happened")).toContain("something unexpected");
  });
});
