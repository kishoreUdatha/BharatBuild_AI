import chalk from "chalk"; import readline from "readline";
export type ApprovalDecision="allow"|"deny"|"cancel";
export async function requestApproval(toolName: string, input: Record<string,unknown>): Promise<ApprovalDecision> {
  console.log(chalk.yellow(`\n?  Permission required: ${chalk.bold(toolName)}`)); console.log(chalk.dim(`   Input: ${JSON.stringify(input).slice(0,120)}`));
  const rl=readline.createInterface({input:process.stdin,output:process.stdout});
  return new Promise((resolve)=>{ rl.question(chalk.cyan("  Allow? [y/n/c]: "),(ans)=>{ rl.close(); const a=ans.trim().toLowerCase(); if (a==="y"||a==="yes") resolve("allow"); else if (a==="c") resolve("cancel"); else resolve("deny"); }); });
}
