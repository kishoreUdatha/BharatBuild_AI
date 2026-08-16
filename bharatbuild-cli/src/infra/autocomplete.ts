import fs from "fs";
import os from "os";
import path from "path";

const ALL_COMMANDS = "chat ask build test fix review task plan spec hooks model init login logout whoami settings doctor update translate diagnostic issue version mcp agent crew acp voice autocomplete";

export function generateBashCompletion(): string {
  return `# BharatBuild CLI bash completion
_bharatbuild_completion() {
  local cur prev
  COMPREPLY=()
  cur="\${COMP_WORDS[COMP_CWORD]}"
  prev="\${COMP_WORDS[COMP_CWORD-1]}"
  local commands="${ALL_COMMANDS}"
  if [[ \${COMP_CWORD} -eq 1 ]]; then
    COMPREPLY=( \$(compgen -W "\$commands" -- "\$cur") ); return
  fi
  case "\$prev" in
    --effort) COMPREPLY=( \$(compgen -W "low medium high xhigh max" -- "\$cur") );;
    --agent) COMPREPLY=( \$(compgen -W "default planner coder tester fixer reviewer guide" -- "\$cur") );;
    --format) COMPREPLY=( \$(compgen -W "plain json json-pretty" -- "\$cur") );;
    model) COMPREPLY=( \$(compgen -W "auto haiku sonnet opus gpt-4o gpt-4o-mini gemini-1.5-pro ollama/llama3" -- "\$cur") );;
    *) COMPREPLY=( \$(compgen -f -- "\$cur") );;
  esac
}
complete -F _bharatbuild_completion bharatbuild`;
}

export function generateZshCompletion(): string {
  return `#compdef bharatbuild
_bharatbuild() {
  local -a commands
  commands=(
    'chat:Start interactive chat' 'ask:Ask a question' 'build:Build project'
    'test:Run tests' 'fix:Fix errors' 'review:Review code' 'task:Manage tasks'
    'plan:Create plan' 'spec:Spec-driven workflow' 'hooks:Manage hooks'
    'model:Switch model' 'init:Init project' 'login:Authenticate' 'logout:Sign out'
    'whoami:Current user' 'settings:Manage settings' 'doctor:Diagnose issues'
    'update:Update CLI' 'translate:Natural language to shell' 'diagnostic:System info'
    'issue:Create GitHub issue' 'version:Show version' 'mcp:MCP servers'
    'agent:Manage agents' 'crew:Multi-agent crew' 'acp:ACP server/client'
    'voice:Voice mode' 'autocomplete:Install shell completion'
  )
  _describe 'command' commands
}
_bharatbuild`;
}

export function generatePowerShellCompletion(): string {
  return `# BharatBuild CLI PowerShell completion
Register-ArgumentCompleter -Native -CommandName bharatbuild -ScriptBlock {
  param($wordToComplete, $commandAst, $cursorPosition)
  $commands = @('${ALL_COMMANDS.split(" ").join("','")}')
  $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
  }
}`;
}

export function installCompletion(shell?: string): string {
  const detected = shell ?? (process.env["SHELL"] ?? "bash").split("/").pop() ?? "bash";
  let script = "";
  let installPath = "";
  if (detected.includes("zsh")) {
    script = generateZshCompletion();
    installPath = path.join(os.homedir(), ".zsh", "completions", "_bharatbuild");
  } else if (detected.includes("powershell") || process.platform === "win32") {
    script = generatePowerShellCompletion();
    installPath = path.join(os.homedir(), "Documents", "PowerShell", "bharatbuild-completion.ps1");
  } else {
    script = generateBashCompletion();
    installPath = path.join(os.homedir(), ".bash_completion.d", "bharatbuild");
  }
  fs.mkdirSync(path.dirname(installPath), { recursive: true });
  fs.writeFileSync(installPath, script);
  return installPath;
}
