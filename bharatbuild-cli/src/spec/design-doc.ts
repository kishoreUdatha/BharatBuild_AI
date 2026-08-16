import fs from "fs";
import path from "path";

export interface DesignDoc {
  title: string;
  overview: string;
  architecture: string;
  components: string[];
  dataFlow: string;
  openQuestions: string[];
}

export function loadDesignDoc(dir?: string): DesignDoc | null {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "specs", "design.md");
  if (!fs.existsSync(f)) return null;
  return parseDesignDoc(fs.readFileSync(f, "utf8"));
}

function parseDesignDoc(content: string): DesignDoc {
  const doc: DesignDoc = { title: "", overview: "", architecture: "", components: [], dataFlow: "", openQuestions: [] };
  const sections = content.split(/^## /m);
  for (const section of sections) {
    const lines = section.split("\n");
    const heading = lines[0]?.trim().toLowerCase() ?? "";
    const body = lines.slice(1).join("\n").trim();
    if (heading === "" && lines[0]?.startsWith("# ")) doc.title = lines[0].replace(/^# /, "").trim();
    else if (heading.includes("overview")) doc.overview = body;
    else if (heading.includes("architecture")) doc.architecture = body;
    else if (heading.includes("component")) doc.components = body.split("\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2));
    else if (heading.includes("data flow")) doc.dataFlow = body;
    else if (heading.includes("open question")) doc.openQuestions = body.split("\n").filter((l) => l.startsWith("- ")).map((l) => l.slice(2));
  }
  return doc;
}

export function saveDesignDoc(doc: DesignDoc, dir?: string) {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "specs", "design.md");
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const content = [
    `# ${doc.title}\n`,
    `## Overview\n${doc.overview}\n`,
    `## Architecture\n${doc.architecture}\n`,
    `## Components\n${doc.components.map((c) => `- ${c}`).join("\n")}\n`,
    `## Data Flow\n${doc.dataFlow}\n`,
    `## Open Questions\n${doc.openQuestions.map((q) => `- ${q}`).join("\n")}\n`,
  ].join("\n");
  fs.writeFileSync(f, content);
}
