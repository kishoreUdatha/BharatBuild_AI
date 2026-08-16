/**
 * BharatBuild CLI — Founder Mode
 * PRD, Business Plan, GTM Strategy, MVP Planning, Pitch Deck
 */

import fs from "fs";
import path from "path";
import chalk from "chalk";
import readline from "readline";
import { BharatBuildClient, APIError } from "../api/client.js";
import { Spinner, ProgressRenderer } from "../ui/spinner.js";
import type { CLIConfig } from "../config/config.js";

type FounderTask =
  | "prd"
  | "business_plan"
  | "gtm"
  | "mvp"
  | "pitch"
  | "general";

function ask(rl: readline.Interface, q: string): Promise<string> {
  return new Promise((resolve) =>
    rl.question(chalk.cyan(q), (a) => resolve(a.trim()))
  );
}

function detectTask(input: string): FounderTask {
  const lower = input.toLowerCase();
  if (lower.includes("prd") || lower.includes("product requirement")) return "prd";
  if (lower.includes("business plan") || lower.includes("biz plan")) return "business_plan";
  if (lower.includes("gtm") || lower.includes("go-to-market") || lower.includes("go to market"))
    return "gtm";
  if (lower.includes("mvp") || lower.includes("minimum viable")) return "mvp";
  if (lower.includes("pitch") || lower.includes("deck") || lower.includes("investor"))
    return "pitch";
  return "general";
}

const TASK_LABELS: Record<FounderTask, string> = {
  prd: "Product Requirements Document",
  business_plan: "Business Plan",
  gtm: "Go-To-Market Strategy",
  mvp: "MVP Plan",
  pitch: "Pitch Deck Outline",
  general: "Founder Assistant",
};

// ── stream founder content ────────────────────────────────────────────────────

async function streamFounderContent(
  client: BharatBuildClient,
  task: FounderTask,
  message: string,
  context: Record<string, string>
): Promise<string> {
  const renderer = new ProgressRenderer();
  const parts: string[] = [];

  console.log(chalk.bold(`\n🚀 Generating ${TASK_LABELS[task]}...\n`));

  try {
    const stream = client.streamSSE("/bolt/chat/stream", {
      message,
      mode: "founder",
      task,
      context,
      history: [],
    });

    for await (const event of stream) {
      const type = event.type;
      const data = event.data as Record<string, unknown>;

      if (type === "text") {
        const chunk = String(data?.content ?? data?.text ?? "");
        if (chunk) {
          renderer.onChunk(chunk);
          parts.push(chunk);
        }
      } else if (type === "stage") {
        renderer.onStage(
          String(data?.name ?? data?.stage ?? "Processing"),
          (data?.status as "start" | "done" | "error") ?? "start"
        );
      } else if (type === "complete") {
        renderer.onComplete();
        break;
      } else if (type === "error") {
        renderer.onError(String(data?.message ?? "Unknown error"));
        break;
      }
    }
  } catch (err) {
    renderer.onComplete();
    if (err instanceof APIError) {
      if (err.statusCode === 401)
        console.error(chalk.red("\n✗ Not authenticated. Run /login first.\n"));
      else
        console.error(chalk.red(`\n✗ API error (${err.statusCode}): ${err.detail}\n`));
    } else {
      console.error(chalk.red(`\n✗ ${err instanceof Error ? err.message : String(err)}\n`));
    }
  }

  return parts.join("");
}

// ── save to file ──────────────────────────────────────────────────────────────

async function saveToFile(
  content: string,
  productName: string,
  taskType: string,
  rl: readline.Interface
): Promise<void> {
  const save = await ask(rl, "\n  Save as markdown file? [y/N]: ");
  if (save.toLowerCase() !== "y") return;

  const slug = productName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const filename = `${slug}-${taskType}.md`;
  const filepath = path.join(process.cwd(), filename);

  try {
    fs.writeFileSync(filepath, content, "utf8");
    console.log(chalk.green(`\n  ✓ Saved to: ${chalk.underline(filepath)}\n`));
  } catch (err) {
    console.error(chalk.red(`\n  ✗ Failed to save: ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── task flows ────────────────────────────────────────────────────────────────

async function generatePRD(client: BharatBuildClient): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold("\n📋 PRD Generator\n"));
  const productName = await ask(rl, "  Product name: ");
  const targetUsers = await ask(rl, "  Target users/market: ");
  const problem = await ask(rl, "  Core problem being solved: ");
  const features = await ask(rl, "  Key features (comma separated): ");
  const competitors = await ask(rl, "  Competitors (optional): ");

  const message = `Generate a comprehensive Product Requirements Document (PRD) for:
Product: ${productName}
Target Users: ${targetUsers}
Problem: ${problem}
Key Features: ${features}
Competitors: ${competitors || "None specified"}

Include: Executive Summary, Problem Statement, Goals & Objectives, User Stories, Functional Requirements, Non-Functional Requirements, Success Metrics, Timeline.`;

  const content = await streamFounderContent(client, "prd", message, {
    product_name: productName,
    target_users: targetUsers,
  });

  await saveToFile(content, productName, "prd", rl);
  rl.close();
}

async function generateBusinessPlan(client: BharatBuildClient): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold("\n📊 Business Plan Generator\n"));
  const productName = await ask(rl, "  Company/Product name: ");
  const industry = await ask(rl, "  Industry/sector: ");
  const model = await ask(rl, "  Business model (SaaS/marketplace/service/etc.): ");
  const market = await ask(rl, "  Target market size: ");
  const revenue = await ask(rl, "  Revenue model: ");

  const message = `Generate a detailed Business Plan for:
Company: ${productName}
Industry: ${industry}
Business Model: ${model}
Target Market: ${market}
Revenue Model: ${revenue}

Include: Executive Summary, Company Overview, Market Analysis, Competitive Analysis, Products/Services, Marketing Strategy, Operations Plan, Financial Projections (3-year), Funding Requirements.`;

  const content = await streamFounderContent(client, "business_plan", message, {
    product_name: productName,
    industry,
  });

  await saveToFile(content, productName, "business-plan", rl);
  rl.close();
}

async function generateGTM(client: BharatBuildClient): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold("\n🎯 GTM Strategy Generator\n"));
  const productName = await ask(rl, "  Product name: ");
  const segment = await ask(rl, "  Primary customer segment: ");
  const channels = await ask(rl, "  Preferred channels (digital/offline/both): ");
  const budget = await ask(rl, "  Monthly marketing budget (INR, optional): ");
  const launchDate = await ask(rl, "  Target launch date (optional): ");

  const message = `Create a Go-To-Market (GTM) Strategy for:
Product: ${productName}
Customer Segment: ${segment}
Channels: ${channels}
Budget: ${budget || "Not specified"}
Launch Date: ${launchDate || "TBD"}

Include: Target Audience, Value Proposition, Pricing Strategy, Distribution Channels, Marketing Channels, Sales Strategy, Launch Plan, KPIs & Metrics, India-specific considerations.`;

  const content = await streamFounderContent(client, "gtm", message, {
    product_name: productName,
    segment,
  });

  await saveToFile(content, productName, "gtm-strategy", rl);
  rl.close();
}

async function generateMVP(client: BharatBuildClient): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold("\n🔨 MVP Planner\n"));
  const productName = await ask(rl, "  Product name: ");
  const coreFeature = await ask(rl, "  Core problem/feature: ");
  const techStack = await ask(rl, "  Preferred tech stack (or 'auto'): ");
  const timeline = await ask(rl, "  Build timeline (weeks): ");

  const message = `Create a detailed MVP Plan for:
Product: ${productName}
Core Feature: ${coreFeature}
Tech Stack: ${techStack}
Timeline: ${timeline} weeks

Include: MVP Scope, Feature Prioritization (Must-have/Nice-to-have/Out-of-scope), Technical Architecture, Week-by-week Sprint Plan, Resource Requirements, Success Criteria, Post-MVP Roadmap.`;

  const content = await streamFounderContent(client, "mvp", message, {
    product_name: productName,
  });

  await saveToFile(content, productName, "mvp-plan", rl);
  rl.close();
}

async function generatePitch(client: BharatBuildClient): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold("\n🎤 Pitch Deck Generator\n"));
  const companyName = await ask(rl, "  Company name: ");
  const tagline = await ask(rl, "  One-line tagline: ");
  const problem = await ask(rl, "  Problem you're solving: ");
  const traction = await ask(rl, "  Current traction (users/revenue, if any): ");
  const ask_ = await ask(rl, "  Funding ask (INR crores): ");

  const message = `Create a compelling Pitch Deck outline for:
Company: ${companyName}
Tagline: ${tagline}
Problem: ${problem}
Traction: ${traction || "Pre-launch"}
Funding Ask: ₹${ask_} crore

Create a 12-15 slide deck outline with content for each slide:
Problem, Solution, Market Size (TAM/SAM/SOM), Product Demo, Business Model, Traction, Competition, Team, Financials, Use of Funds, Vision. 
Include India-specific market data and context.`;

  const content = await streamFounderContent(client, "pitch", message, {
    company_name: companyName,
  });

  await saveToFile(content, companyName, "pitch-deck", rl);
  rl.close();
}

async function generalChat(
  client: BharatBuildClient,
  firstMessage?: string
): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(
    chalk.bold("\n🚀 Founder Assistant\n") +
      chalk.dim("  Ask anything about your startup. Type 'back' to return.\n")
  );

  if (firstMessage) {
    const msg = firstMessage;
    rl.close();
    await streamFounderContent(client, "general", msg, {});
    return;
  }

  while (true) {
    const input = await ask(rl, "  founder > ");
    if (!input) continue;
    if (input.toLowerCase() === "back" || input.toLowerCase() === "/back") break;
    await streamFounderContent(client, "general", input, {});
  }
  rl.close();
}

// ── interactive menu ──────────────────────────────────────────────────────────

export async function founderInteractiveMenu(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold.cyan("\n🚀 Founder Mode\n"));
  console.log("  1. Generate PRD (Product Requirements Document)");
  console.log("  2. Generate Business Plan");
  console.log("  3. Create GTM Strategy");
  console.log("  4. Plan MVP");
  console.log("  5. Generate Pitch Deck Outline");
  console.log("  6. General Founder Assistant (chat)");
  console.log("  7. Back to main REPL\n");

  const choice = await ask(rl, "Choice [1-7]: ");
  rl.close();

  if (choice === "7" || choice === "") return;

  switch (choice) {
    case "1": await generatePRD(client); break;
    case "2": await generateBusinessPlan(client); break;
    case "3": await generateGTM(client); break;
    case "4": await generateMVP(client); break;
    case "5": await generatePitch(client); break;
    case "6": await generalChat(client); break;
    default:
      console.log(chalk.yellow("  Invalid choice.\n"));
  }
}

// ── REPL handler ──────────────────────────────────────────────────────────────

export async function runFounderMode(
  input: string,
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  if (input === "__menu__") {
    await founderInteractiveMenu(client, config);
    return;
  }

  const task = detectTask(input);
  if (task === "general") {
    await generalChat(client, input);
  } else {
    // Route to specific generator
    switch (task) {
      case "prd": await generatePRD(client); break;
      case "business_plan": await generateBusinessPlan(client); break;
      case "gtm": await generateGTM(client); break;
      case "mvp": await generateMVP(client); break;
      case "pitch": await generatePitch(client); break;
    }
  }
}
