/**
 * Slash Command Handler
 * 
 * Routes slash commands to appropriate actions in the BharatBuild AI system.
 * Used by parent components to handle commands selected from SlashCommandMenu.
 */

import { SlashCommand } from '@/config/slashCommands'

export interface CommandHandlerOptions {
  // Callbacks for different command types
  onGenerate?: (prompt: string, mode?: 'standard' | 'incremental') => void
  onFix?: () => void
  onRun?: () => void
  onStop?: () => void
  onBuild?: () => void
  onExport?: () => void
  onImport?: () => void
  onDocs?: (docType?: string) => void
  onExplain?: (target: string) => void
  onEnhance?: () => void
  onRefactor?: (target: string) => void
  onTest?: () => void
  onAnalyze?: () => void
  onShare?: () => void
  onNewProject?: () => void
  onViewProjects?: () => void
  onClearChat?: () => void
  onShowLogs?: () => void
  onShowHelp?: () => void
  // Fallback: send as chat message
  onSendMessage?: (message: string) => void
}

/**
 * Handle a slash command execution.
 * Routes the command to the appropriate callback.
 * 
 * @param command - The slash command object
 * @param args - Arguments provided after the command
 * @param handlers - Object with handler callbacks
 */
export function handleSlashCommand(
  command: SlashCommand,
  args: string,
  handlers: CommandHandlerOptions
): void {
  const { 
    onGenerate, onFix, onRun, onStop, onBuild, onExport, onImport,
    onDocs, onExplain, onEnhance, onRefactor, onTest, onAnalyze,
    onShare, onNewProject, onViewProjects, onClearChat, onShowLogs,
    onShowHelp, onSendMessage
  } = handlers

  switch (command.id) {
    // --- Generation ---
    case 'generate':
      if (onGenerate) {
        onGenerate(args, 'standard')
      } else if (onSendMessage) {
        onSendMessage(args || 'Generate a project')
      }
      break

    case 'generate-incremental':
      if (onGenerate) {
        onGenerate(args, 'incremental')
      } else if (onSendMessage) {
        onSendMessage(args || 'Generate a project')
      }
      break

    case 'add':
      if (onSendMessage) {
        onSendMessage(args ? `Add feature: ${args}` : 'What feature would you like to add?')
      }
      break

    case 'enhance':
      if (onEnhance) {
        onEnhance()
      } else if (onSendMessage) {
        onSendMessage('Enhance the current project: improve UI, performance, and code quality')
      }
      break

    // --- Code ---
    case 'fix':
      if (onFix) {
        onFix()
      } else if (onSendMessage) {
        onSendMessage('Fix all errors in the project')
      }
      break

    case 'explain':
      if (args && onExplain) {
        onExplain(args)
      } else if (onSendMessage) {
        onSendMessage(args ? `Explain: ${args}` : 'Explain the project architecture')
      }
      break

    case 'refactor':
      if (args && onRefactor) {
        onRefactor(args)
      } else if (onSendMessage) {
        onSendMessage(args ? `Refactor: ${args}` : 'Refactor the project for better structure')
      }
      break

    case 'test':
      if (onTest) {
        onTest()
      } else if (onSendMessage) {
        onSendMessage('Generate unit tests for the project')
      }
      break

    // --- Documents ---
    case 'docs':
      if (onDocs) {
        onDocs()
      } else if (onSendMessage) {
        onSendMessage('Generate all project documents (SRS, Report, PPT, UML, Viva)')
      }
      break

    case 'srs':
      if (onDocs) {
        onDocs('srs')
      } else if (onSendMessage) {
        onSendMessage('Generate SRS document')
      }
      break

    case 'ppt':
      if (onDocs) {
        onDocs('ppt')
      } else if (onSendMessage) {
        onSendMessage('Generate project presentation')
      }
      break

    case 'report':
      if (onDocs) {
        onDocs('report')
      } else if (onSendMessage) {
        onSendMessage('Generate project report')
      }
      break

    case 'viva':
      if (onDocs) {
        onDocs('viva')
      } else if (onSendMessage) {
        onSendMessage('Generate viva Q&A preparation')
      }
      break

    case 'uml':
      if (onDocs) {
        onDocs('uml')
      } else if (onSendMessage) {
        onSendMessage('Generate UML diagrams')
      }
      break

    // --- Execution ---
    case 'run':
      if (onRun) {
        onRun()
      } else if (onSendMessage) {
        onSendMessage('Run the project')
      }
      break

    case 'stop':
      if (onStop) {
        onStop()
      }
      break

    case 'build':
      if (onBuild) {
        onBuild()
      } else if (onSendMessage) {
        onSendMessage('Build the project')
      }
      break

    case 'logs':
      if (onShowLogs) {
        onShowLogs()
      }
      break

    // --- Tools ---
    case 'export':
      if (onExport) {
        onExport()
      }
      break

    case 'import':
      if (onImport) {
        onImport()
      }
      break

    case 'analyze':
      if (onAnalyze) {
        onAnalyze()
      } else if (onSendMessage) {
        onSendMessage('Analyze the project for bugs, security issues, and performance')
      }
      break

    case 'share':
      if (onShare) {
        onShare()
      }
      break

    // --- Navigation ---
    case 'new':
      if (onNewProject) {
        onNewProject()
      }
      break

    case 'projects':
      if (onViewProjects) {
        onViewProjects()
      }
      break

    case 'help':
      if (onShowHelp) {
        onShowHelp()
      } else if (onSendMessage) {
        onSendMessage('/help')
      }
      break

    case 'clear':
      if (onClearChat) {
        onClearChat()
      }
      break

    // --- Fallback ---
    default:
      if (onSendMessage) {
        onSendMessage(`${command.command} ${args}`.trim())
      }
      break
  }
}

export default handleSlashCommand
