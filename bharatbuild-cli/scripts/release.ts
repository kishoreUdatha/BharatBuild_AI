import { execSync } from "child_process";
import fs from "fs";
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8")) as { version: string };
console.log(`🚀 Releasing v${pkg.version}...`);
execSync("npm publish --access public", { stdio: "inherit" });
console.log("✅ Released!");
