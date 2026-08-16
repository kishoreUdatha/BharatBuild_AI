import fs from "fs";
import path from "path";

export interface SteeringFile {
  persona?: string;
  rules?: string[];
  ignore?: string[];
  context?: string;
  model?: string;
}

export function loadSteeringFile(dir?: string): SteeringFile {
  const root = dir ?? process.cwd();
  // Check multiple locations like Kiro does
  const locations = [
    path.join(root, ".bharatbuild", "steering.md"),
    path.join(root, ".kiro", "steering.md"),
    path.join(root, "AGENTS.md"),
    path.join(root, "CLAUDE.md"),
  ];
  for (const loc of locations) {
    if (fs.existsSync(loc)) {
      return parseSteeringMarkdown(fs.readFileSync(loc, "utf8"));
    }
  }
  return {};
}

function parseSteeringMarkdown(content: string): SteeringFile {
  const result: SteeringFile = {};
  const lines = content.split("\n");
  let section = "";
  const rules: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## Persona")) { section = "persona"; continue; }
    if (line.startsWith("## Rules")) { section = "rules"; continue; }
    if (line.startsWith("## Ignore")) { section = "ignore"; continue; }
    if (line.startsWith("## Model")) { section = "model"; continue; }
    if (line.startsWith("#")) { section = ""; continue; }

    if (section === "persona" && line.trim()) result.persona = (result.persona ?? "") + line + "\n";
    if (section === "rules" && line.startsWith("- ")) rules.push(line.slice(2).trim());
    if (section === "model" && line.trim()) result.model = line.trim();
  }
  result.rules = rules;
  return result;
}

export function saveSteeringFile(steering: SteeringFile, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "steering.md");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const lines: string[] = ["# BharatBuild Steering File\n"];
  if (steering.persona) lines.push(`## Persona\n${steering.persona}\n`);
  if (steering.rules?.length) lines.push(`## Rules\n${steering.rules.map((r) => `- ${r}`).join("\n")}\n`);
  if (steering.model) lines.push(`## Model\n${steering.model}\n`);
  fs.writeFileSync(f, lines.join("\n"));
}
