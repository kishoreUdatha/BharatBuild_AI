/**
 * BharatBuild CLI - inline command
 * 
 * Generate code inline within existing files or contexts
 */
import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { loadConfig } from "../config/config.js";
import { loadCredentials } from "../auth/credentials.js";
import { BharatBuildClient } from "../api/client.js";
import { attachAutoRefresh } from "../auth/refresh.js";
import { createModelClientAuto } from "../models/model-router.js";

export function inlineCommand(): Command {
  const cmd = new Command("inline");
  cmd.description("Generate code inline within existing files");

  cmd
    .argument("<prompt>", "What to generate")
    .option("-f, --file <path>", "Target file to modify")
    .option("-l, --line <number>", "Line number to insert at")
    .option("-r, --replace <pattern>", "Pattern to replace")
    .option("--model <model>", "AI model to use")
    .option("--preview", "Show preview without applying changes")
    .action(async (prompt: string, opts) => {
      const config = loadConfig();
      const creds = loadCredentials();
      
      if (!creds) {
        console.log(chalk.red("\n✗ Not logged in. Run: bharatbuild login\n"));
        process.exit(1);
      }

      const client = attachAutoRefresh(
        new BharatBuildClient({
          apiBaseUrl: config.apiBaseUrl,
          authToken: creds.token,
        }),
        config.apiBaseUrl
      );

      const modelClient = createModelClientAuto(opts.model || config.model || "auto");

      try {
        await generateInline(prompt, opts, modelClient, client);
      } catch (error) {
        console.log(chalk.red(`\n✗ Inline generation failed: ${(error as Error).message}\n`));
        process.exit(1);
      }
    });

  return cmd;
}

interface InlineOptions {
  file?: string;
  line?: string;
  replace?: string;
  model?: string;
  preview?: boolean;
}

async function generateInline(prompt: string, opts: InlineOptions, modelClient: any, client: BharatBuildClient): Promise<void> {
  console.log(chalk.bold(`\n  🔧 Inline Generation\n`));
  console.log(chalk.dim(`  Prompt: ${prompt}`));
  
  let context = "";
  let targetFile = opts.file;
  let insertLine = opts.line ? parseInt(opts.line) : undefined;

  // Auto-detect target file if not specified
  if (!targetFile) {
    const commonFiles = [
      "index.js", "index.ts", "main.js", "main.ts", 
      "app.js", "app.ts", "server.js", "server.ts"
    ];
    
    for (const file of commonFiles) {
      if (fs.existsSync(file)) {
        targetFile = file;
        break;
      }
    }
  }

  // Read existing file content for context
  if (targetFile && fs.existsSync(targetFile)) {
    context = fs.readFileSync(targetFile, 'utf8');
    console.log(chalk.dim(`  Target: ${targetFile} (${context.split('\n').length} lines)`));
  } else {
    console.log(chalk.yellow(`  ⚠ Target file not found: ${targetFile || 'auto-detect failed'}`));
    console.log(chalk.dim("    Generating standalone code...\n"));
  }

  // Build system prompt for inline generation
  const systemPrompt = `You are an expert code generator for inline modifications.

TASK: Generate code based on the user's prompt that fits seamlessly into the existing context.

CONTEXT FILE: ${targetFile || 'new file'}
${context ? `\nEXISTING CONTENT:\n\`\`\`\n${context}\n\`\`\`` : ''}

INSTRUCTIONS:
- Generate only the necessary code to fulfill the prompt
- Match the existing code style, patterns, and conventions
- If modifying existing content, provide clear insertion points
- Include necessary imports/dependencies
- Write clean, production-ready code
- Add brief comments for complex logic

OUTPUT FORMAT:
If inserting new code, wrap in comments like:
// BEGIN: Generated code for [brief description]
[your code here]
// END: Generated code

If replacing existing code, show the replacement clearly.`;

  // Generate the code
  console.log(chalk.dim("  Generating..."));
  let generatedCode = "";
  
  try {
    const stream = modelClient.complete({
      model: opts.model || "sonnet",
      system: systemPrompt,
      messages: [{ role: "user", content: prompt }],
      tools: [],
      maxTokens: 4000
    });

    for await (const chunk of stream) {
      if (chunk.type === "text_delta" && chunk.text) {
        generatedCode += chunk.text;
        process.stdout.write(chunk.text);
      }
    }
  } catch (error) {
    // Fallback to API if direct model fails
    console.log(chalk.dim("\n  Falling back to API..."));
    
    const response = await client.post("/api/v1/inline/generate", {
      prompt,
      context: context || "",
      file: targetFile || "",
      options: opts
    });
    
    const r = response as { code?: string; content?: string };
    generatedCode = r.code || r.content || "";
  }

  console.log("\n");

  if (!generatedCode.trim()) {
    console.log(chalk.red("  ✗ No code generated\n"));
    return;
  }

  // Preview mode
  if (opts.preview) {
    console.log(chalk.bold("  📋 Preview:\n"));
    console.log(generatedCode);
    console.log(chalk.dim("\n  Run without --preview to apply changes\n"));
    return;
  }

  // Apply changes
  if (targetFile) {
    if (opts.replace) {
      // Replace pattern
      const newContent = context.replace(new RegExp(opts.replace, 'g'), generatedCode.trim());
      fs.writeFileSync(targetFile, newContent);
      console.log(chalk.green(`  ✓ Replaced pattern in ${targetFile}\n`));
    } else if (insertLine) {
      // Insert at specific line
      const lines = context.split('\n');
      lines.splice(insertLine - 1, 0, generatedCode.trim());
      fs.writeFileSync(targetFile, lines.join('\n'));
      console.log(chalk.green(`  ✓ Inserted at line ${insertLine} in ${targetFile}\n`));
    } else {
      // Append to end
      const newContent = context + '\n\n' + generatedCode.trim();
      fs.writeFileSync(targetFile, newContent);
      console.log(chalk.green(`  ✓ Appended to ${targetFile}\n`));
    }
  } else {
    // Create new file
    const filename = `generated-${Date.now()}.js`;
    fs.writeFileSync(filename, generatedCode.trim());
    console.log(chalk.green(`  ✓ Created ${filename}\n`));
  }
}