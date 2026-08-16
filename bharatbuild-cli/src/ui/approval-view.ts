import chalk from "chalk";
export function renderApprovalRequest(toolName: string, input: Record<string, unknown>, riskLevel: "low" | "medium" | "high") {
  const c = riskLevel === "high" ? chalk.red : riskLevel === "medium" ? chalk.yellow : chalk.green;
  console.log(c(`\n⚠  Permission Required [${riskLevel.toUpperCase()} RISK]`));
  console.log(chalk.bold(`   Tool: ${toolName}`));
  console.log(chalk.dim(`   Input: ${JSON.stringify(input).slice(0, 200)}`));
}
