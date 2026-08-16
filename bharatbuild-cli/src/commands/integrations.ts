/**
 * BharatBuild CLI - integrations command
 * 
 * Manage external tool integrations (IDEs, git hooks, CI/CD, etc.)
 */
import { Command } from "commander";
import chalk from "chalk";
import fs from "fs";
import path from "path";
import { execSync } from "child_process";

export function integrationsCommand(): Command {
  const cmd = new Command("integrations");
  cmd.description("Manage external tool integrations");

  // List available integrations
  cmd
    .command("list")
    .description("Show available integrations")
    .action(() => {
      console.log(chalk.bold("\n  🔌 Available Integrations\n"));
      
      const integrations = [
        { name: "vscode", desc: "VS Code extension and settings", status: checkVSCode() },
        { name: "git", desc: "Git hooks and commit templates", status: checkGitHooks() },
        { name: "github", desc: "GitHub Actions workflows", status: checkGitHubActions() },
        { name: "docker", desc: "Docker development environment", status: checkDocker() },
        { name: "eslint", desc: "ESLint configuration and rules", status: checkESLint() },
        { name: "prettier", desc: "Code formatting configuration", status: checkPrettier() },
      ];

      for (const int of integrations) {
        const icon = int.status ? chalk.green("✓") : chalk.dim("○");
        const statusText = int.status ? chalk.green("enabled") : chalk.dim("available");
        console.log(`  ${icon} ${chalk.bold(int.name.padEnd(12))} ${int.desc}  ${statusText}`);
      }

      console.log(chalk.dim("\n  Enable: bharatbuild integrations enable <name>\n"));
    });

  // Enable an integration
  cmd
    .command("enable <name>")
    .description("Enable a specific integration")
    .action((name: string) => {
      switch (name.toLowerCase()) {
        case "vscode":
          enableVSCode();
          break;
        case "git":
          enableGitHooks();
          break;
        case "github":
          enableGitHubActions();
          break;
        case "docker":
          enableDocker();
          break;
        case "eslint":
          enableESLint();
          break;
        case "prettier":
          enablePrettier();
          break;
        default:
          console.log(chalk.red(`\n  ✗ Unknown integration: ${name}\n`));
          console.log(chalk.dim("  Run: bharatbuild integrations list\n"));
      }
    });

  return cmd;
}

// Integration status checkers
function checkVSCode(): boolean {
  return fs.existsSync(".vscode") || fs.existsSync(path.join(process.cwd(), ".vscode"));
}

function checkGitHooks(): boolean {
  const gitDir = path.join(process.cwd(), ".git");
  return fs.existsSync(gitDir) && fs.existsSync(path.join(gitDir, "hooks"));
}

function checkGitHubActions(): boolean {
  return fs.existsSync(path.join(process.cwd(), ".github/workflows"));
}

function checkDocker(): boolean {
  return fs.existsSync(path.join(process.cwd(), "Dockerfile")) || 
         fs.existsSync(path.join(process.cwd(), "docker-compose.yml"));
}

function checkESLint(): boolean {
  return fs.existsSync(path.join(process.cwd(), ".eslintrc.js")) ||
         fs.existsSync(path.join(process.cwd(), ".eslintrc.json")) ||
         fs.existsSync(path.join(process.cwd(), "eslint.config.js"));
}

function checkPrettier(): boolean {
  return fs.existsSync(path.join(process.cwd(), ".prettierrc")) ||
         fs.existsSync(path.join(process.cwd(), ".prettierrc.js")) ||
         fs.existsSync(path.join(process.cwd(), "prettier.config.js"));
}

// Integration enablers
function enableVSCode(): void {
  const vscodeDir = path.join(process.cwd(), ".vscode");
  if (!fs.existsSync(vscodeDir)) {
    fs.mkdirSync(vscodeDir, { recursive: true });
  }

  const settings = {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": true
    },
    "files.associations": {
      "*.bharatbuild": "yaml"
    },
    "bharatbuild.enableAutoSave": true
  };

  fs.writeFileSync(
    path.join(vscodeDir, "settings.json"),
    JSON.stringify(settings, null, 2)
  );

  console.log(chalk.green("\n  ✓ VS Code integration enabled"));
  console.log(chalk.dim("    Created .vscode/settings.json with BharatBuild optimizations\n"));
}

function enableGitHooks(): void {
  try {
    execSync("bharatbuild hooks install", { stdio: "inherit" });
    console.log(chalk.green("\n  ✓ Git hooks integration enabled\n"));
  } catch (error) {
    console.log(chalk.red("\n  ✗ Failed to enable git hooks integration\n"));
    console.log(chalk.dim("    Ensure you're in a git repository\n"));
  }
}

function enableGitHubActions(): void {
  const workflowsDir = path.join(process.cwd(), ".github/workflows");
  if (!fs.existsSync(workflowsDir)) {
    fs.mkdirSync(workflowsDir, { recursive: true });
  }

  const workflow = `name: BharatBuild CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Build
      run: npm run build
      
    - name: Test
      run: npm test
`;

  fs.writeFileSync(
    path.join(workflowsDir, "bharatbuild-ci.yml"),
    workflow
  );

  console.log(chalk.green("\n  ✓ GitHub Actions integration enabled"));
  console.log(chalk.dim("    Created .github/workflows/bharatbuild-ci.yml\n"));
}

function enableDocker(): void {
  const dockerfile = `FROM node:18-alpine
WORKDIR /app
RUN npm install -g @bharatbuild/cli
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
`;

  fs.writeFileSync(path.join(process.cwd(), "Dockerfile"), dockerfile);

  console.log(chalk.green("\n  ✓ Docker integration enabled"));
  console.log(chalk.dim("    Created Dockerfile\n"));
}

function enableESLint(): void {
  const eslintConfig = {
    "env": { "node": true, "es2022": true },
    "extends": ["eslint:recommended", "@typescript-eslint/recommended"],
    "parser": "@typescript-eslint/parser",
    "parserOptions": { "ecmaVersion": "latest", "sourceType": "module" },
    "plugins": ["@typescript-eslint"],
    "rules": {
      "no-unused-vars": "warn",
      "no-console": "off"
    }
  };

  fs.writeFileSync(
    path.join(process.cwd(), ".eslintrc.json"),
    JSON.stringify(eslintConfig, null, 2)
  );

  console.log(chalk.green("\n  ✓ ESLint integration enabled"));
  console.log(chalk.dim("    Created .eslintrc.json\n"));
}

function enablePrettier(): void {
  const prettierConfig = {
    "semi": true,
    "singleQuote": false,
    "tabWidth": 2,
    "trailingComma": "es5",
    "printWidth": 100
  };

  fs.writeFileSync(
    path.join(process.cwd(), ".prettierrc"),
    JSON.stringify(prettierConfig, null, 2)
  );

  console.log(chalk.green("\n  ✓ Prettier integration enabled"));
  console.log(chalk.dim("    Created .prettierrc\n"));
}