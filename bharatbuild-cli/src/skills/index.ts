/**
 * BharatBuild CLI - Skills System
 *
 * Reusable agent capabilities stored in .bharatbuild/skills/<name>/SKILL.md
 * Auto-discovered when a session starts and injected into the agent system prompt.
 * Mirrors Kiro CLI's Skills system exactly.
 *
 * SKILL.md format:
 *   ---
 *   name: my-skill
 *   description: What this skill does
 *   tools: [read_file, write_file]   (optional tool restrictions)
 *   ---
 *
 *   # Skill: My Skill
 *   [Instructions / knowledge / patterns the agent should follow]
 */

import fs from "fs";
import path from "path";

export interface Skill {
  name: string;
  description: string;
  tools?: string[];
  content: string;
  filePath: string;
}

export interface SkillFrontMatter {
  name?: string;
  description?: string;
  tools?: string[];
}

// ── Front matter parser ────────────────────────────────────────────────────

function parseFrontMatter(raw: string): { meta: SkillFrontMatter; body: string } {
  const fm: SkillFrontMatter = {};
  if (!raw.startsWith("---")) return { meta: fm, body: raw };

  const end = raw.indexOf("\n---", 3);
  if (end === -1) return { meta: fm, body: raw };

  const block = raw.slice(3, end).trim();
  const body = raw.slice(end + 4).trim();

  for (const line of block.split("\n")) {
    const colon = line.indexOf(":");
    if (colon === -1) continue;
    const key = line.slice(0, colon).trim();
    const val = line.slice(colon + 1).trim();
    if (key === "name") fm.name = val;
    else if (key === "description") fm.description = val;
    else if (key === "tools") {
      fm.tools = val.replace(/[\[\]]/g, "").split(",").map((t) => t.trim()).filter(Boolean);
    }
  }

  return { meta: fm, body };
}

// ── Discovery ──────────────────────────────────────────────────────────────

/**
 * Discover all skills in .bharatbuild/skills/<name>/SKILL.md
 * Falls back to checking .kiro/skills/ for Kiro compatibility.
 */
export function discoverSkills(workingDir?: string): Skill[] {
  const root = workingDir ?? process.cwd();
  const searchDirs = [
    path.join(root, ".bharatbuild", "skills"),
    path.join(root, ".kiro", "skills"),
  ];

  const skills: Skill[] = [];

  for (const skillsDir of searchDirs) {
    if (!fs.existsSync(skillsDir)) continue;

    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(skillsDir, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const skillFile = path.join(skillsDir, entry.name, "SKILL.md");
      if (!fs.existsSync(skillFile)) continue;

      try {
        const raw = fs.readFileSync(skillFile, "utf8");
        const { meta, body } = parseFrontMatter(raw);
        skills.push({
          name: meta.name ?? entry.name,
          description: meta.description ?? `Skill: ${entry.name}`,
          tools: meta.tools,
          content: body,
          filePath: skillFile,
        });
      } catch {
        // skip malformed skills
      }
    }
  }

  return skills;
}

/**
 * Build a system prompt addition from discovered skills.
 * Injected into the agent's system prompt automatically.
 */
export function buildSkillsPrompt(skills: Skill[]): string {
  if (skills.length === 0) return "";

  const parts = ["\n## Active Skills\n", `${skills.length} skill(s) are active for this session:\n`];

  for (const skill of skills) {
    parts.push(`### Skill: ${skill.name}`);
    if (skill.description) parts.push(`> ${skill.description}\n`);
    parts.push(skill.content.trim());
    parts.push("");
  }

  return parts.join("\n");
}

/**
 * Create a new skill scaffold.
 */
export function createSkill(name: string, description: string, workingDir?: string): string {
  const root = workingDir ?? process.cwd();
  const skillDir = path.join(root, ".bharatbuild", "skills", name);
  fs.mkdirSync(skillDir, { recursive: true });

  const template = `---
name: ${name}
description: ${description}
tools: []
---

# Skill: ${name}

${description}

## Instructions

[Add instructions, patterns, or knowledge the agent should follow when this skill is active]

## Examples

[Optional: add examples of how to apply this skill]
`;

  const skillPath = path.join(skillDir, "SKILL.md");
  fs.writeFileSync(skillPath, template);
  return skillPath;
}

/**
 * List all skills (for CLI display).
 */
export function listSkills(workingDir?: string): Skill[] {
  return discoverSkills(workingDir);
}