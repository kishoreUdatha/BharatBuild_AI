/**
 * The repo shipped jest + ts-jest in devDependencies while every test file was
 * written against vitest, and there was no config of any kind — so `npm test`
 * collected dist/*.js, choked on ESM, and reported "10 suites, 0 tests" on
 * every run. Vitest handles this project's ESM + TS + TSX natively.
 */
import { defineConfig } from "vitest/config";
import os from "node:os";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "node",
    // Colour is a feature here (diff row tints, syntax highlighting), and
    // chalk disables it for a non-TTY. Force it on so those assertions test
    // the real output instead of a stripped one.
    //
    // BHARATBUILD_HOME points at a throwaway directory so a suite that mounts
    // the App cannot read or write the developer's real ~/.bharatbuild —
    // prompt history, saved agents and auth.json all live there, and a test
    // that submits input would otherwise append to the user's own history.
    env: {
      FORCE_COLOR: "3",
      BHARATBUILD_HOME: path.join(os.tmpdir(), "bharatbuild-test-home"),
    },
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
    exclude: ["node_modules/**", "dist/**"],
    testTimeout: 30_000,
    hookTimeout: 30_000,
    clearMocks: true,
    // Ink writes to stdout; keep suites from fighting over it.
    pool: "forks",
    // Ink writes to stdout; one fork keeps suites from fighting over it.
    maxWorkers: 1,
  },
  resolve: {
    // Source uses NodeNext ".js" specifiers that resolve to ".ts" on disk.
    extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
  },
});
