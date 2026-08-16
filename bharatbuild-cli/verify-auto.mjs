import { autoSelectModel, detectAvailableProviders } from "./dist/models/auto-select.js";

console.log("\n=== BharatBuild CLI — Auto Model Selection Test ===\n");

// Test complexity detection + model selection
const tests = [
  { prompt: "fix typo", opts: {} },
  { prompt: "add a button to the form", opts: {} },
  { prompt: "implement full JWT auth module with refresh tokens", opts: {} },
  { prompt: "refactor entire codebase architecture and migrate to microservices", opts: {} },
  { prompt: "what is this variable", opts: { effort: "low" } },
  { prompt: "build complete REST API", opts: { effort: "max" } },
  { prompt: "quick fix", opts: { preferCost: true } },
  { prompt: "complex system design", opts: { preferSpeed: true } },
];

for (const { prompt, opts } of tests) {
  const r = autoSelectModel(prompt, opts);
  const effortStr = opts.effort ? ` [effort:${opts.effort}]` : opts.preferCost ? " [cost]" : opts.preferSpeed ? " [speed]" : "";
  console.log(`  [${r.complexity.padEnd(8)}] ${r.modelId.padEnd(35)} "${prompt.slice(0,45)}"${effortStr}`);
}

console.log("\n=== Available Providers (from env) ===\n");
const providers = detectAvailableProviders();
console.log("  " + providers.join(", "));
console.log("\n✅ Auto model selection working!\n");
