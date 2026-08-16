import { execSync } from "child_process";
import fs from "fs";
console.log("📦 Packaging bharatbuild-cli...");
execSync("npm pack", { stdio: "inherit" });
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8")) as { name: string; version: string };
console.log(`✅ Packaged: ${pkg.name}-${pkg.version}.tgz`);
