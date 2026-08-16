/**
 * BharatBuild CLI — Student Mode
 * Academic project generation: SRS, UML, code, docs, viva Q&A
 */

import chalk from "chalk";
import readline from "readline";
import { BharatBuildClient, APIError } from "../api/client.js";
import { Spinner, ProgressRenderer, printTable } from "../ui/spinner.js";
import type { CLIConfig } from "../config/config.js";

type GenerateType = "full" | "srs" | "uml" | "code" | "docs" | "viva";

// ── helpers ───────────────────────────────────────────────────────────────────

function askQuestion(rl: readline.Interface, q: string): Promise<string> {
  return new Promise((resolve) =>
    rl.question(chalk.cyan(q), (a) => resolve(a.trim()))
  );
}

function detectGenerateType(input: string): GenerateType {
  const lower = input.toLowerCase();
  if (lower.includes("srs") || lower.includes("software requirement"))
    return "srs";
  if (lower.includes("uml") || lower.includes("diagram") || lower.includes("class diagram"))
    return "uml";
  if (lower.includes("viva") || lower.includes("interview") || lower.includes("q&a"))
    return "viva";
  if (lower.includes("documentation") || lower.includes("report") || lower.includes("docs"))
    return "docs";
  if (lower.includes("only code") || lower.includes("source code") || lower.includes("just code"))
    return "code";
  return "full";
}

const STAGE_LABELS: Record<string, string> = {
  planning: "📋 Planning project structure",
  srs: "📄 Generating SRS document",
  uml: "🔷 Creating UML diagrams",
  code: "💻 Writing source code",
  docs: "📚 Generating documentation",
  viva: "🎤 Preparing Viva Q&A",
  report: "📃 Generating final report",
  ppt: "📊 Creating presentation",
  packaging: "📦 Packaging project",
};

// ── core generation ───────────────────────────────────────────────────────────

async function generateProject(
  client: BharatBuildClient,
  projectName: string,
  description: string,
  techStack: string,
  generateType: GenerateType
): Promise<void> {
  const renderer = new ProgressRenderer();

  console.log(
    chalk.bold(`\n🎓 Generating ${generateType === "full" ? "full academic project" : generateType.toUpperCase()}...\n`)
  );

  try {
    const stream = client.streamSSE("/api/v1/orchestrator/generate", {
      project_name: projectName,
      description,
      tech_stack: techStack,
      generate_type: generateType,
      mode: "student",
    });

    for await (const event of stream) {
      const type = event.type;
      const data = event.data as Record<string, unknown>;

      if (type === "stage") {
        const stageName = String(data?.name ?? data?.stage ?? "");
        const status = String(data?.status ?? "start") as "start" | "done" | "error";
        const label = STAGE_LABELS[stageName] ?? stageName;
        renderer.onStage(label, status);
      } else if (type === "text") {
        const content = String(data?.content ?? data?.text ?? "");
        if (content) renderer.onChunk(content);
      } else if (type === "file") {
        const filePath = String(data?.path ?? "");
        if (filePath)
          console.log(chalk.green(`  ✓ Generated: ${filePath}`));
      } else if (type === "complete") {
        renderer.onComplete();
        const projectId = String(data?.project_id ?? "");
        const downloadUrl = String(data?.download_url ?? "");
        console.log(chalk.bold.green("\n✅ Generation complete!\n"));
        if (projectId) {
          console.log(`  ${chalk.bold("Project ID:")}   ${chalk.cyan(projectId)}`);
          console.log(
            `  ${chalk.bold("Download:")}     ${chalk.dim(`bharatbuild download ${projectId}`)}`
          );
        }
        if (downloadUrl)
          console.log(`  ${chalk.bold("Direct URL:")}   ${chalk.underline(downloadUrl)}`);
        console.log();
        return;
      } else if (type === "error") {
        renderer.onError(String(data?.message ?? data?.detail ?? "Unknown error"));
        return;
      }
    }
  } catch (err) {
    renderer.onComplete();
    if (err instanceof APIError) {
      if (err.statusCode === 401) {
        console.error(chalk.red("\n✗ Not authenticated. Run /login first.\n"));
      } else {
        console.error(chalk.red(`\n✗ API error (${err.statusCode}): ${err.detail}\n`));
      }
    } else {
      console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : String(err)}\n`));
    }
  }
}

// ── list projects ─────────────────────────────────────────────────────────────

async function listStudentProjects(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading your projects…");
  try {
    const data = await client.get<{ projects?: unknown[]; items?: unknown[] }>(
      "/api/v1/projects?limit=20"
    );
    spinner.succeed();
    const list: Array<Record<string, unknown>> = (
      data.projects ?? data.items ?? (Array.isArray(data) ? data : [])
    ) as Array<Record<string, unknown>>;

    if (list.length === 0) {
      console.log(chalk.dim("\n  No projects yet. Generate your first project!\n"));
      return;
    }

    printTable(
      ["Name", "Type", "Status", "Created"],
      list.map((p) => [
        String(p.name ?? p.project_name ?? "Unnamed"),
        String(p.project_type ?? p.generate_type ?? "full"),
        String(p.status ?? "unknown"),
        p.created_at
          ? new Date(String(p.created_at)).toLocaleDateString("en-IN")
          : "—",
      ])
    );
  } catch (err) {
    spinner.fail("Failed to load projects");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── interactive menu ──────────────────────────────────────────────────────────

export async function studentInteractiveMenu(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const close = () => rl.close();

  console.log(chalk.bold.cyan("\n🎓 Student Mode\n"));
  console.log("  1. Generate Full Academic Project");
  console.log("  2. Generate SRS Document");
  console.log("  3. Generate UML Diagrams");
  console.log("  4. Generate Source Code");
  console.log("  5. Generate Documentation");
  console.log("  6. Generate Viva Q&A");
  console.log("  7. List My Projects");
  console.log("  8. Back to main REPL\n");

  const choice = await askQuestion(rl, "Choice [1-8]: ");

  if (choice === "8" || choice === "") {
    close();
    return;
  }

  const typeMap: Record<string, GenerateType> = {
    "1": "full",
    "2": "srs",
    "3": "uml",
    "4": "code",
    "5": "docs",
    "6": "viva",
  };

  if (choice === "7") {
    close();
    await listStudentProjects(client);
    return;
  }

  const generateType = typeMap[choice] ?? "full";

  const projectName = await askQuestion(rl, "\nProject name (e.g. Online Voting System): ");
  if (!projectName) {
    close();
    console.log(chalk.yellow("  Project name is required.\n"));
    return;
  }

  const description = await askQuestion(
    rl,
    "Brief description (what does it do?): "
  );
  const techStack = await askQuestion(
    rl,
    "Tech stack (e.g. React, Node.js, MySQL) [press Enter to skip]: "
  );

  close();

  await generateProject(
    client,
    projectName,
    description || projectName,
    techStack || "Not specified",
    generateType
  );
}

// ── REPL handler ──────────────────────────────────────────────────────────────

export async function runStudentMode(
  input: string,
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  // Special token for menu trigger from REPL
  if (input === "__menu__") {
    await studentInteractiveMenu(client, config);
    return;
  }

  // Detect what they want to generate
  const generateType = detectGenerateType(input);

  // Extract project name from input heuristically
  // e.g. "generate SRS for hospital management system"
  const nameMatch = input.match(
    /(?:for|of|about|called|named|project[:\s]+)\s+(.+)/i
  );
  const projectName = nameMatch
    ? nameMatch[1].trim().replace(/['"]/g, "")
    : input.slice(0, 60);

  if (!projectName) {
    await studentInteractiveMenu(client, config);
    return;
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(
    chalk.dim(`\n  Detected: generate ${chalk.cyan(generateType)} for "${projectName}"\n`)
  );

  const confirm = await new Promise<string>((resolve) =>
    rl.question(chalk.cyan("  Press Enter to continue or type a different name: "), resolve)
  );
  const finalName = confirm.trim() || projectName;

  const techStack = await new Promise<string>((resolve) =>
    rl.question(
      chalk.cyan("  Tech stack (e.g. React, FastAPI, PostgreSQL) [Enter to skip]: "),
      resolve
    )
  );
  rl.close();

  await generateProject(
    client,
    finalName,
    input,
    techStack.trim() || "Not specified",
    generateType
  );
}
