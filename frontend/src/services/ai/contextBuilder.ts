/**
 * Multi-File AI Context Manager
 * Builds intelligent context for AI requests
 * Based on how Bolt.new, Cursor, and Replit work
 */

import { ProjectFile } from '@/store/projectStore'

export interface AIContext {
  // Project Structure
  projectName: string
  projectType: 'react' | 'node' | 'nextjs' | 'vue' | 'python' | 'java' | 'unknown'
  fileTree: string // Text representation of folder structure

  // Selected Files (most relevant)
  selectedFiles: ContextFile[]

  // Project Metadata
  techStack: string[]
  dependencies?: Record<string, string>

  // Current State
  currentFile?: string
  cursorPosition?: { line: number, column: number }

  // Errors/Issues
  errors?: string[]
  warnings?: string[]

  // User Intent
  userGoal?: string
}

export interface ContextFile {
  path: string
  content: string
  language: string
  relevanceScore: number
  reason?: string // Why this file was included
}

export interface ContextBuildOptions {
  maxFiles?: number // Max files to include (default: 10)
  maxTokens?: number // Approximate token limit (default: 50000)
  includeTests?: boolean
  includeConfig?: boolean
}

/**
 * Build intelligent context from project files
 */
export function buildAIContext(
  userPrompt: string,
  project: {
    name: string
    files: ProjectFile[]
    selectedFile?: ProjectFile | null
  },
  options: ContextBuildOptions = {}
): AIContext {
  const {
    maxFiles = 10,
    maxTokens = 50000,
    includeTests = false,
    includeConfig = true
  } = options

  // Detect project type and tech stack
  const projectType = detectProjectType(project.files)
  const techStack = detectTechStack(project.files)

  // Build file tree representation
  const fileTree = buildFileTree(project.files)

  // Extract keywords from user prompt
  const keywords = extractKeywords(userPrompt)

  // Score and rank files by relevance
  const scoredFiles = project.files
    .map(file => ({
      file,
      score: calculateRelevance(file, keywords, project.selectedFile, {
        includeTests,
        includeConfig
      })
    }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, maxFiles)

  // Convert to context files with token limiting
  const selectedFiles: ContextFile[] = []
  let totalTokens = 0

  for (const { file, score } of scoredFiles) {
    const fileTokens = estimateTokens(file.content || '')

    if (totalTokens + fileTokens > maxTokens) {
      break // Token limit reached
    }

    selectedFiles.push({
      path: file.path,
      content: file.content || '',
      language: file.language,
      relevanceScore: score,
      reason: getInclusionReason(file, project.selectedFile, keywords)
    })

    totalTokens += fileTokens
  }

  return {
    projectName: project.name,
    projectType,
    fileTree,
    selectedFiles,
    techStack,
    dependencies: extractDependencies(project.files),
    currentFile: project.selectedFile?.path,
    userGoal: userPrompt
  }
}

/**
 * Detect project type from files
 */
function detectProjectType(files: ProjectFile[]): AIContext['projectType'] {
  const hasFile = (pattern: string) =>
    files.some(f => f.path.match(new RegExp(pattern)))

  if (hasFile('package.json')) {
    if (hasFile('next.config')) return 'nextjs'
    if (hasFile('vite.config|App.tsx|App.jsx')) return 'react'
    if (hasFile('vue.config|App.vue')) return 'vue'
    return 'node'
  }

  if (hasFile('requirements.txt|setup.py|__init__.py')) return 'python'
  if (hasFile('pom.xml|build.gradle|.java$')) return 'java'

  return 'unknown'
}

/**
 * Detect tech stack
 */
function detectTechStack(files: ProjectFile[]): string[] {
  const stack: string[] = []
  const packageJson = files.find(f => f.path === 'package.json')

  if (packageJson?.content) {
    try {
      const pkg = JSON.parse(packageJson.content)
      const deps = { ...pkg.dependencies, ...pkg.devDependencies }

      // Detect frameworks
      if (deps.react) stack.push('React')
      if (deps.next) stack.push('Next.js')
      if (deps.vue) stack.push('Vue')
      if (deps.express) stack.push('Express')
      if (deps.nest || deps['@nestjs/core']) stack.push('NestJS')

      // Detect tools
      if (deps.typescript) stack.push('TypeScript')
      if (deps.tailwindcss) stack.push('Tailwind CSS')
      if (deps.vite) stack.push('Vite')
      if (deps.webpack) stack.push('Webpack')
    } catch (e) {
      // Invalid JSON
    }
  }

  // Detect from file extensions
  const hasExtension = (ext: string) =>
    files.some(f => f.path.endsWith(ext))

  if (hasExtension('.ts') || hasExtension('.tsx')) stack.push('TypeScript')
  if (hasExtension('.py')) stack.push('Python')
  if (hasExtension('.java')) stack.push('Java')

  return stack
}

/**
 * Calculate file relevance score
 */
function calculateRelevance(
  file: ProjectFile,
  keywords: string[],
  selectedFile: ProjectFile | null | undefined,
  options: { includeTests: boolean, includeConfig: boolean }
): number {
  let score = 0

  // Current/selected file gets highest priority
  if (selectedFile && file.path === selectedFile.path) {
    score += 100
  }

  // Keyword matching in filename
  const fileName = file.path.toLowerCase()
  for (const keyword of keywords) {
    if (fileName.includes(keyword.toLowerCase())) {
      score += 30
    }
  }

  // Keyword matching in content
  const content = (file.content || '').toLowerCase()
  for (const keyword of keywords) {
    if (content.includes(keyword.toLowerCase())) {
      score += 20
    }
  }

  // File type bonuses
  if (file.path.match(/\.(tsx?|jsx?)$/)) score += 15 // Source files
  if (file.path.includes('component')) score += 10
  if (file.path.includes('util') || file.path.includes('helper')) score += 8
  if (file.path.includes('type') || file.path.includes('interface')) score += 5

  // Penalties
  if (!options.includeTests && file.path.match(/\.(test|spec)\./)) score -= 50
  if (!options.includeConfig && file.path.match(/\.(config|rc)\./)) score -= 30
  if (file.path.includes('node_modules')) score = 0
  if (file.path.includes('.git')) score = 0
  if (file.path.match(/\.(lock|log)$/)) score = 0

  // Recently modified (if we had timestamps)
  // score += isRecent(file) ? 10 : 0

  // Import relationships (if we parse imports)
  // score += importsSelectedFile(file, selectedFile) ? 25 : 0

  return Math.max(0, score)
}

/**
 * Extract keywords from user prompt
 */
function extractKeywords(prompt: string): string[] {
  // Remove common words
  const stopWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those']

  return prompt
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 2 && !stopWords.includes(word))
}

/**
 * Build file tree representation
 */
function buildFileTree(files: ProjectFile[]): string {
  const tree: Record<string, any> = {}

  for (const file of files) {
    const parts = file.path.split('/')
    let current = tree

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      if (i === parts.length - 1) {
        current[part] = file.type
      } else {
        if (!current[part]) current[part] = {}
        current = current[part]
      }
    }
  }

  return formatTree(tree, 0)
}

function formatTree(node: any, indent: number): string {
  let result = ''
  const entries = Object.entries(node)

  for (const [name, value] of entries) {
    const prefix = '  '.repeat(indent)
    const icon = typeof value === 'object' ? '📁' : '📄'
    result += `${prefix}${icon} ${name}\n`

    if (typeof value === 'object') {
      result += formatTree(value, indent + 1)
    }
  }

  return result
}

/**
 * Estimate token count
 */
function estimateTokens(text: string): number {
  // Rough estimate: 1 token ≈ 4 characters
  return Math.ceil(text.length / 4)
}

/**
 * Get reason for file inclusion
 */
function getInclusionReason(
  file: ProjectFile,
  selectedFile: ProjectFile | null | undefined,
  keywords: string[]
): string {
  if (selectedFile && file.path === selectedFile.path) {
    return 'Currently selected file'
  }

  const matchedKeywords = keywords.filter(k =>
    file.path.toLowerCase().includes(k) ||
    (file.content || '').toLowerCase().includes(k)
  )

  if (matchedKeywords.length > 0) {
    return `Matches keywords: ${matchedKeywords.join(', ')}`
  }

  if (file.path.match(/\.(tsx?|jsx?)$/)) {
    return 'Main source file'
  }

  return 'Related to project'
}

/**
 * Extract dependencies from package.json
 */
function extractDependencies(files: ProjectFile[]): Record<string, string> | undefined {
  const packageJson = files.find(f => f.path === 'package.json')

  if (packageJson?.content) {
    try {
      const pkg = JSON.parse(packageJson.content)
      return { ...pkg.dependencies, ...pkg.devDependencies }
    } catch (e) {
      return undefined
    }
  }

  return undefined
}

/**
 * Format context for AI prompt
 */
export function formatContextForAI(context: AIContext): string {
  let prompt = `# Project: ${context.projectName}\n\n`

  prompt += `## Project Type\n${context.projectType}\n\n`

  if (context.techStack.length > 0) {
    prompt += `## Tech Stack\n${context.techStack.join(', ')}\n\n`
  }

  prompt += `## File Structure\n\`\`\`\n${context.fileTree}\`\`\`\n\n`

  if (context.selectedFiles.length > 0) {
    prompt += `## Relevant Files\n\n`

    for (const file of context.selectedFiles) {
      prompt += `### ${file.path}\n`
      if (file.reason) {
        prompt += `*${file.reason}*\n\n`
      }
      prompt += `\`\`\`${file.language}\n${file.content}\n\`\`\`\n\n`
    }
  }

  if (context.currentFile) {
    prompt += `## Current File\n${context.currentFile}\n\n`
  }

  if (context.userGoal) {
    prompt += `## User Request\n${context.userGoal}\n\n`
  }

  return prompt
}
