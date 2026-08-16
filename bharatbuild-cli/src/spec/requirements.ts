import fs from "fs";
import path from "path";

export interface Requirement {
  id: string;
  title: string;
  description: string;
  priority: "must" | "should" | "could";
  status: "pending" | "in_progress" | "done";
}

export function parseRequirementsDoc(content: string): Requirement[] {
  const reqs: Requirement[] = [];
  const lines = content.split("\n");
  let current: Partial<Requirement> | null = null;

  for (const line of lines) {
    const headingMatch = line.match(/^###\s+(.+)/);
    if (headingMatch) {
      if (current?.id) reqs.push(current as Requirement);
      current = { id: `req-${reqs.length + 1}`, title: headingMatch[1] ?? "", description: "", priority: "should", status: "pending" };
      continue;
    }
    if (current) {
      if (line.toLowerCase().includes("must")) current.priority = "must";
      else if (line.toLowerCase().includes("could")) current.priority = "could";
      current.description = (current.description ?? "") + line + "\n";
    }
  }
  if (current?.id) reqs.push(current as Requirement);
  return reqs;
}

export function loadRequirements(dir?: string): Requirement[] {
  const f = path.join(dir ?? process.cwd(), ".bharatbuild", "specs", "requirements.md");
  if (!fs.existsSync(f)) return [];
  return parseRequirementsDoc(fs.readFileSync(f, "utf8"));
}
