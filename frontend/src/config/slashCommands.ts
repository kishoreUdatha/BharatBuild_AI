/**
 * Slash Commands Configuration
 * 
 * Defines all available slash commands organized by category.
 * Used by the SlashCommandMenu component.
 */

export interface SlashCommand {
  id: string
  command: string        // The slash command (e.g., "/generate")
  label: string          // Display label
  description: string    // Short description shown in menu
  category: CommandCategory
  icon: string           // Lucide icon name
  shortcut?: string      // Optional keyboard shortcut hint
  requiresProject?: boolean  // Only available when a project is open
  args?: string          // Placeholder for arguments (e.g., "<description>")
}

export type CommandCategory = 
  | 'generation'
  | 'code'
  | 'documents'
  | 'execution'
  | 'tools'
  | 'navigation'

export interface CommandCategoryInfo {
  id: CommandCategory
  label: string
  icon: string
}

// =============================================================================
// CATEGORIES
// =============================================================================

export const COMMAND_CATEGORIES: CommandCategoryInfo[] = [
  { id: 'generation', label: 'Generation', icon: 'Sparkles' },
  { id: 'code', label: 'Code', icon: 'Code' },
  { id: 'documents', label: 'Documents', icon: 'FileText' },
  { id: 'execution', label: 'Execution', icon: 'Play' },
  { id: 'tools', label: 'Tools', icon: 'Wrench' },
  { id: 'navigation', label: 'Navigation', icon: 'Compass' },
]

// =============================================================================
// COMMANDS
// =============================================================================

export const SLASH_COMMANDS: SlashCommand[] = [
  // --- Generation ---
  {
    id: 'generate',
    command: '/generate',
    label: 'Generate Project',
    description: 'Generate a complete new project from description',
    category: 'generation',
    icon: 'Sparkles',
    args: '<project description>',
  },
  {
    id: 'generate-incremental',
    command: '/generate:incremental',
    label: 'Generate (Incremental)',
    description: 'Generate file-by-file with inline verification (more accurate)',
    category: 'generation',
    icon: 'ListChecks',
    args: '<project description>',
  },
  {
    id: 'add',
    command: '/add',
    label: 'Add Feature',
    description: 'Add a new feature to the current project',
    category: 'generation',
    icon: 'Plus',
    args: '<feature description>',
    requiresProject: true,
  },
  {
    id: 'enhance',
    command: '/enhance',
    label: 'Enhance',
    description: 'Improve existing code (better UI, performance, security)',
    category: 'generation',
    icon: 'Wand2',
    requiresProject: true,
  },

  // --- Code ---
  {
    id: 'fix',
    command: '/fix',
    label: 'Fix Errors',
    description: 'Auto-detect and fix errors in the project',
    category: 'code',
    icon: 'Bug',
    requiresProject: true,
  },
  {
    id: 'explain',
    command: '/explain',
    label: 'Explain Code',
    description: 'Explain how a file or function works',
    category: 'code',
    icon: 'MessageCircleQuestion',
    args: '<file or concept>',
    requiresProject: true,
  },
  {
    id: 'refactor',
    command: '/refactor',
    label: 'Refactor',
    description: 'Refactor code for better structure and readability',
    category: 'code',
    icon: 'RefreshCw',
    args: '<file or component>',
    requiresProject: true,
  },
  {
    id: 'test',
    command: '/test',
    label: 'Generate Tests',
    description: 'Generate unit tests for the project',
    category: 'code',
    icon: 'FlaskConical',
    requiresProject: true,
  },

  // --- Documents ---
  {
    id: 'docs',
    command: '/docs',
    label: 'Generate All Documents',
    description: 'Generate SRS, Report, PPT, UML, and Viva Q&A',
    category: 'documents',
    icon: 'Files',
    requiresProject: true,
  },
  {
    id: 'srs',
    command: '/srs',
    label: 'Generate SRS',
    description: 'Generate Software Requirements Specification',
    category: 'documents',
    icon: 'FileText',
    requiresProject: true,
  },
  {
    id: 'ppt',
    command: '/ppt',
    label: 'Generate PPT',
    description: 'Generate project presentation (15-20 slides)',
    category: 'documents',
    icon: 'Presentation',
    requiresProject: true,
  },
  {
    id: 'report',
    command: '/report',
    label: 'Generate Report',
    description: 'Generate project report (60-80 pages)',
    category: 'documents',
    icon: 'BookOpen',
    requiresProject: true,
  },
  {
    id: 'viva',
    command: '/viva',
    label: 'Viva Preparation',
    description: 'Generate viva Q&A for project defense',
    category: 'documents',
    icon: 'GraduationCap',
    requiresProject: true,
  },
  {
    id: 'uml',
    command: '/uml',
    label: 'Generate UML',
    description: 'Generate UML diagrams (class, sequence, use case)',
    category: 'documents',
    icon: 'GitBranch',
    requiresProject: true,
  },

  // --- Execution ---
  {
    id: 'run',
    command: '/run',
    label: 'Run Project',
    description: 'Build and run the project in Docker',
    category: 'execution',
    icon: 'Play',
    requiresProject: true,
  },
  {
    id: 'stop',
    command: '/stop',
    label: 'Stop Project',
    description: 'Stop running containers',
    category: 'execution',
    icon: 'Square',
    requiresProject: true,
  },
  {
    id: 'build',
    command: '/build',
    label: 'Build Only',
    description: 'Build the project without running',
    category: 'execution',
    icon: 'Hammer',
    requiresProject: true,
  },
  {
    id: 'logs',
    command: '/logs',
    label: 'Show Logs',
    description: 'Show build and runtime logs',
    category: 'execution',
    icon: 'Terminal',
    requiresProject: true,
  },

  // --- Tools ---
  {
    id: 'export',
    command: '/export',
    label: 'Export Project',
    description: 'Download project as ZIP file',
    category: 'tools',
    icon: 'Download',
    requiresProject: true,
  },
  {
    id: 'import',
    command: '/import',
    label: 'Import Project',
    description: 'Import an existing project (ZIP or GitHub)',
    category: 'tools',
    icon: 'Upload',
  },
  {
    id: 'analyze',
    command: '/analyze',
    label: 'Analyze Project',
    description: 'Full project analysis (bugs, security, performance)',
    category: 'tools',
    icon: 'Search',
    requiresProject: true,
  },
  {
    id: 'share',
    command: '/share',
    label: 'Share Project',
    description: 'Get a shareable preview link',
    category: 'tools',
    icon: 'Share2',
    requiresProject: true,
  },

  // --- Navigation ---
  {
    id: 'model',
    command: '/model',
    label: 'Switch Model',
    description: 'Change AI model (Auto, Fast, Balanced, Smart)',
    category: 'navigation',
    icon: 'Sparkles',
  },
  {
    id: 'new',
    command: '/new',
    label: 'New Project',
    description: 'Start a fresh new project',
    category: 'navigation',
    icon: 'FolderPlus',
  },
  {
    id: 'projects',
    command: '/projects',
    label: 'My Projects',
    description: 'View all your projects',
    category: 'navigation',
    icon: 'Folder',
  },
  {
    id: 'help',
    command: '/help',
    label: 'Help',
    description: 'Show available commands and tips',
    category: 'navigation',
    icon: 'HelpCircle',
  },
  {
    id: 'clear',
    command: '/clear',
    label: 'Clear Chat',
    description: 'Clear the chat conversation',
    category: 'navigation',
    icon: 'Trash2',
  },
]

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Search/filter commands by query string
 */
export function filterCommands(
  query: string,
  options?: { hasProject?: boolean }
): SlashCommand[] {
  const normalizedQuery = query.toLowerCase().replace('/', '')
  
  let commands = SLASH_COMMANDS

  // Filter out project-required commands if no project is open
  if (options?.hasProject === false) {
    commands = commands.filter(cmd => !cmd.requiresProject)
  }

  if (!normalizedQuery) return commands

  return commands.filter(cmd =>
    cmd.command.toLowerCase().includes(normalizedQuery) ||
    cmd.label.toLowerCase().includes(normalizedQuery) ||
    cmd.description.toLowerCase().includes(normalizedQuery) ||
    cmd.category.includes(normalizedQuery)
  )
}

/**
 * Get commands grouped by category
 */
export function getCommandsByCategory(
  commands: SlashCommand[]
): Map<CommandCategory, SlashCommand[]> {
  const grouped = new Map<CommandCategory, SlashCommand[]>()
  
  for (const cmd of commands) {
    const existing = grouped.get(cmd.category) || []
    existing.push(cmd)
    grouped.set(cmd.category, existing)
  }

  return grouped
}

/**
 * Find a command by its slash string
 */
export function findCommand(input: string): SlashCommand | undefined {
  const cmd = input.trim().split(' ')[0].toLowerCase()
  return SLASH_COMMANDS.find(c => c.command === cmd)
}
