import { execSync } from "child_process";
console.log("🔨 Building bharatbuild-cli...");
execSync("npx tsc --build", { stdio: "inherit" });
console.log("✅ Build complete!");
