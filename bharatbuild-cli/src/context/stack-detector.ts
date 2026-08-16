import fs from "fs"; import path from "path";
export interface TechStack { language:string; framework?:string; database?:string; packageManager?:string; testFramework?:string; }
export function detectStack(dir: string): TechStack {
  const has = (f: string) => fs.existsSync(path.join(dir,f));
  let language = "unknown", framework: string|undefined, database: string|undefined, packageManager: string|undefined, testFramework: string|undefined;
  if (has("package.json")) {
    language = "typescript";
    packageManager = has("pnpm-lock.yaml") ? "pnpm" : has("yarn.lock") ? "yarn" : "npm";
    try {
      const p = JSON.parse(fs.readFileSync(path.join(dir,"package.json"),"utf8")) as Record<string,Record<string,string>>;
      const deps = { ...p["dependencies"], ...p["devDependencies"] };
      if (deps["next"]) framework="next.js"; else if (deps["react"]) framework="react"; else if (deps["express"]) framework="express";
      if (deps["jest"]) testFramework="jest"; else if (deps["vitest"]) testFramework="vitest";
      if (deps["pg"]||deps["postgres"]) database="postgresql"; else if (deps["mongoose"]) database="mongodb";
    } catch { /* skip */ }
  } else if (has("requirements.txt")||has("pyproject.toml")) {
    language = "python";
    try {
      const req = has("requirements.txt") ? fs.readFileSync(path.join(dir,"requirements.txt"),"utf8") : "";
      if (req.includes("fastapi")) framework="fastapi"; else if (req.includes("django")) framework="django"; else if (req.includes("flask")) framework="flask";
    } catch { /* skip */ }
  } else if (has("pom.xml")||has("build.gradle")) { language="java";
  } else if (has("go.mod")) { language="go";
  } else if (has("Cargo.toml")) { language="rust"; }
  return { language, framework, database, packageManager, testFramework };
}
