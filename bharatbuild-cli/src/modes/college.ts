/**
 * BharatBuild CLI — College Mode
 * Faculty management, batch/student tracking, project monitoring, analytics
 */

import chalk from "chalk";
import readline from "readline";
import { BharatBuildClient, APIError } from "../api/client.js";
import { Spinner, printTable } from "../ui/spinner.js";
import type { CLIConfig } from "../config/config.js";

function ask(rl: readline.Interface, q: string): Promise<string> {
  return new Promise((resolve) =>
    rl.question(chalk.cyan(q), (a) => resolve(a.trim()))
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

async function showDashboard(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading dashboard…");
  try {
    const data = await client.get<Record<string, unknown>>(
      "/api/v1/admin/dashboard"
    );
    spinner.succeed();
    console.log(chalk.bold("\n📊 College Dashboard\n"));

    const stats: Array<[string, unknown]> = [
      ["Total Students", data.total_students ?? data.students_count ?? 0],
      ["Total Projects", data.total_projects ?? data.projects_count ?? 0],
      ["Active Projects", data.active_projects ?? 0],
      ["Completed Projects", data.completed_projects ?? 0],
      ["Total Faculty", data.total_faculty ?? data.faculty_count ?? 0],
      ["Token Usage (month)", data.monthly_token_usage ?? 0],
    ];

    for (const [label, value] of stats) {
      console.log(
        `  ${chalk.bold(String(label).padEnd(28))} ${chalk.cyan(String(value))}`
      );
    }
    console.log();
  } catch (err) {
    spinner.fail("Failed to load dashboard");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── Students ──────────────────────────────────────────────────────────────────

async function listStudents(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading students…");
  try {
    const data = await client.get<{ users?: unknown[]; items?: unknown[] }>(
      "/api/v1/admin/users?role=student&limit=50"
    );
    spinner.succeed();
    const list = (
      data.users ?? data.items ?? (Array.isArray(data) ? data : [])
    ) as Array<Record<string, unknown>>;

    if (list.length === 0) {
      console.log(chalk.dim("\n  No students found.\n"));
      return;
    }

    console.log(chalk.bold(`\n🎓 Students (${list.length})\n`));
    printTable(
      ["Name", "Email", "Plan", "Projects", "Joined"],
      list.map((u) => [
        String(u.full_name ?? u.name ?? "—"),
        String(u.email ?? "—"),
        String(u.subscription_plan ?? u.tier ?? "free"),
        String(u.project_count ?? u.projects_count ?? 0),
        u.created_at
          ? new Date(String(u.created_at)).toLocaleDateString("en-IN")
          : "—",
      ])
    );
  } catch (err) {
    spinner.fail("Failed to load students");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── Projects ──────────────────────────────────────────────────────────────────

async function listAllProjects(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading all projects…");
  try {
    const data = await client.get<{ projects?: unknown[]; items?: unknown[] }>(
      "/api/v1/admin/projects?limit=50"
    );
    spinner.succeed();
    const list = (
      data.projects ?? data.items ?? (Array.isArray(data) ? data : [])
    ) as Array<Record<string, unknown>>;

    if (list.length === 0) {
      console.log(chalk.dim("\n  No projects found.\n"));
      return;
    }

    console.log(chalk.bold(`\n📁 All Projects (${list.length})\n`));
    printTable(
      ["Project Name", "Student", "Status", "Type", "Created"],
      list.map((p) => [
        String(p.name ?? p.project_name ?? "Unnamed"),
        String(
          (p.user as Record<string, unknown>)?.email ??
            p.user_email ??
            p.owner_email ??
            "—"
        ),
        String(p.status ?? "unknown"),
        String(p.project_type ?? p.generate_type ?? "—"),
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

// ── Analytics ─────────────────────────────────────────────────────────────────

async function showAnalytics(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading analytics…");
  try {
    const data = await client.get<Record<string, unknown>>(
      "/api/v1/admin/analytics/dashboard"
    );
    spinner.succeed();

    console.log(chalk.bold("\n📈 Analytics Dashboard\n"));

    // Show whatever the backend returns in a readable format
    const displayKeys = [
      "total_users",
      "new_users_today",
      "new_users_this_week",
      "total_projects_generated",
      "projects_today",
      "total_tokens_used",
      "tokens_used_today",
      "active_subscriptions",
      "revenue_this_month",
      "conversion_rate",
    ];

    let shown = 0;
    for (const key of displayKeys) {
      if (data[key] !== undefined) {
        const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        console.log(
          `  ${chalk.bold(label.padEnd(30))} ${chalk.cyan(String(data[key]))}`
        );
        shown++;
      }
    }

    if (shown === 0) {
      // Fallback: print all keys
      for (const [k, v] of Object.entries(data)) {
        if (typeof v === "number" || typeof v === "string") {
          const label = k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
          console.log(`  ${chalk.bold(label.padEnd(30))} ${chalk.cyan(String(v))}`);
        }
      }
    }
    console.log();
  } catch (err) {
    spinner.fail("Failed to load analytics");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── Campus Drive ──────────────────────────────────────────────────────────────

async function showCampusDrive(client: BharatBuildClient): Promise<void> {
  const spinner = new Spinner();
  spinner.start("Loading campus drive data…");
  try {
    const data = await client.get<{ drives?: unknown[]; items?: unknown[] }>(
      "/api/v1/campus-drive?limit=20"
    );
    spinner.succeed();
    const list = (
      data.drives ?? data.items ?? (Array.isArray(data) ? data : [])
    ) as Array<Record<string, unknown>>;

    if (list.length === 0) {
      console.log(chalk.dim("\n  No campus drive data found.\n"));
      return;
    }

    console.log(chalk.bold(`\n🏢 Campus Drives (${list.length})\n`));
    printTable(
      ["Company", "Role", "Date", "Eligible", "Applied", "Selected"],
      list.map((d) => [
        String(d.company_name ?? d.company ?? "—"),
        String(d.role ?? d.job_role ?? "—"),
        d.drive_date
          ? new Date(String(d.drive_date)).toLocaleDateString("en-IN")
          : "—",
        String(d.eligible_count ?? d.eligible ?? 0),
        String(d.applied_count ?? d.applied ?? 0),
        String(d.selected_count ?? d.selected ?? 0),
      ])
    );
  } catch (err) {
    spinner.fail("Failed to load campus drive data");
    console.error(chalk.red(`  ${err instanceof Error ? err.message : err}\n`));
  }
}

// ── Export Report ─────────────────────────────────────────────────────────────

async function exportReport(client: BharatBuildClient): Promise<void> {
  console.log(
    chalk.dim(
      "\n  📤 Export is available via the web dashboard at:\n" +
        chalk.underline("  https://bharatbuild.ai/admin/reports\n")
    )
  );
}

// ── interactive menu ──────────────────────────────────────────────────────────

export async function collegeInteractiveMenu(
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  console.log(chalk.bold.cyan("\n🏫 College Mode\n"));
  console.log("  1. View Dashboard (stats overview)");
  console.log("  2. List Students");
  console.log("  3. List All Projects");
  console.log("  4. View Analytics");
  console.log("  5. Campus Drive Status");
  console.log("  6. Export Report (web)");
  console.log("  7. Back to main REPL\n");

  const choice = await ask(rl, "Choice [1-7]: ");
  rl.close();

  if (choice === "7" || choice === "") return;

  switch (choice) {
    case "1": await showDashboard(client); break;
    case "2": await listStudents(client); break;
    case "3": await listAllProjects(client); break;
    case "4": await showAnalytics(client); break;
    case "5": await showCampusDrive(client); break;
    case "6": await exportReport(client); break;
    default: console.log(chalk.yellow("  Invalid choice.\n"));
  }
}

// ── REPL handler ──────────────────────────────────────────────────────────────

export async function runCollegeMode(
  input: string,
  client: BharatBuildClient,
  config: CLIConfig
): Promise<void> {
  if (input === "__menu__") {
    await collegeInteractiveMenu(client, config);
    return;
  }

  const lower = input.toLowerCase();
  if (lower.includes("student")) {
    await listStudents(client);
  } else if (lower.includes("project")) {
    await listAllProjects(client);
  } else if (lower.includes("analytic") || lower.includes("stats")) {
    await showAnalytics(client);
  } else if (lower.includes("campus") || lower.includes("drive")) {
    await showCampusDrive(client);
  } else if (lower.includes("dashboard")) {
    await showDashboard(client);
  } else {
    await collegeInteractiveMenu(client, config);
  }
}
