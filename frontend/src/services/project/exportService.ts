/**
 * Project Export Service
 * Exports project as ZIP file
 * Like Bolt.new "Download Project" feature
 */

import { ProjectFile } from '@/store/projectStore'
import { getShareUrl, appConfig } from '@/config'
import JSZip from 'jszip'

export interface ExportOptions {
  includeNodeModules?: boolean
  includeDotFiles?: boolean
  includeGitFolder?: boolean
}

/**
 * Recursively flatten a hierarchical file tree into a flat array
 * Handles nested children[] structure from Bolt.new-style project store
 */
function flattenFileTree(files: ProjectFile[]): ProjectFile[] {
  const result: ProjectFile[] = []

  const recurse = (items: ProjectFile[]) => {
    for (const item of items) {
      if (item.type === 'file') {
        result.push(item)
      }
      if (item.children && item.children.length > 0) {
        recurse(item.children)
      }
    }
  }

  recurse(files)
  return result
}

/**
 * Export project as ZIP download
 */
export async function exportProjectAsZip(
  projectName: string,
  files: ProjectFile[],
  options: ExportOptions = {}
): Promise<void> {
  const {
    includeNodeModules = false,
    includeDotFiles = true,
    includeGitFolder = false
  } = options

  try {
    const zip = new JSZip()

    // Flatten hierarchical tree to get ALL files (including nested ones)
    const allFiles = flattenFileTree(files)
    console.log(`[Export] Flattened ${files.length} root items to ${allFiles.length} total files`)

    // Filter files based on options
    const filesToExport = allFiles.filter(file => {
      // Skip node_modules
      if (!includeNodeModules && file.path.includes('node_modules')) {
        return false
      }

      // Skip .git folder
      if (!includeGitFolder && file.path.includes('.git/')) {
        return false
      }

      // Skip dot files (but keep .gitignore, .env.example, etc.)
      const fileName = file.path.split('/').pop() || ''
      if (!includeDotFiles && fileName.startsWith('.') &&
          !fileName.match(/^\.(gitignore|env\.example|prettierrc|eslintrc)/)) {
        return false
      }

      return true
    })

    console.log(`[Export] After filtering: ${filesToExport.length} files to export`)

    // Add files to ZIP - include files even with empty content (they're valid files)
    let addedCount = 0
    for (const file of filesToExport) {
      // Use content if available, otherwise use empty string
      // This handles lazy-loaded files that haven't been viewed
      const content = file.content ?? ''
      zip.file(file.path, content)
      addedCount++
    }

    console.log(`[Export] Added ${addedCount} files to ZIP`)

    // Generate ZIP
    const blob = await zip.generateAsync({ type: 'blob' })
    console.log(`[Export] Generated ZIP: ${blob.size} bytes`)

    // Trigger download
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${projectName}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('[Export] Failed to export project:', error)
    throw new Error('Failed to export project as ZIP')
  }
}

/**
 * Export single file
 */
export function exportFile(fileName: string, content: string): void {
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Export project to GitHub (prepare repository files)
 */
export async function prepareForGitHub(
  projectName: string,
  files: ProjectFile[]
): Promise<{
  files: Array<{ path: string, content: string }>
  readme: string
}> {
  const exportFiles = files
    .filter(f => f.type === 'file' && f.content)
    .map(f => ({ path: f.path, content: f.content! }))

  // Generate README if not exists
  let readme = files.find(f => f.path === 'README.md')?.content

  if (!readme) {
    readme = generateReadme(projectName, files)
    exportFiles.push({ path: 'README.md', content: readme })
  }

  return {
    files: exportFiles,
    readme
  }
}

/**
 * Generate README.md for project
 */
function generateReadme(projectName: string, files: ProjectFile[]): string {
  const hasPackageJson = files.some(f => f.path === 'package.json')
  const hasPythonFiles = files.some(f => f.path.endsWith('.py'))
  const hasJavaFiles = files.some(f => f.path.endsWith('.java'))

  let readme = `# ${projectName}\n\n`
  readme += `Generated with ${appConfig.name}\n\n`

  readme += `## Installation\n\n`

  if (hasPackageJson) {
    readme += `\`\`\`bash\nnpm install\n\`\`\`\n\n`
    readme += `## Usage\n\n`
    readme += `\`\`\`bash\nnpm run dev\n\`\`\`\n\n`
  } else if (hasPythonFiles) {
    readme += `\`\`\`bash\npip install -r requirements.txt\n\`\`\`\n\n`
    readme += `## Usage\n\n`
    readme += `\`\`\`bash\npython main.py\n\`\`\`\n\n`
  } else if (hasJavaFiles) {
    readme += `\`\`\`bash\nmvn install\n\`\`\`\n\n`
    readme += `## Usage\n\n`
    readme += `\`\`\`bash\nmvn spring-boot:run\n\`\`\`\n\n`
  }

  readme += `## Features\n\n`
  readme += `- Feature 1\n`
  readme += `- Feature 2\n`
  readme += `- Feature 3\n\n`

  readme += `## License\n\nMIT\n`

  return readme
}

/**
 * Create shareable link (would need backend)
 */
export async function createShareableLink(projectId: string): Promise<string> {
  // In real implementation, this would call backend API
  // to create a shareable link
  return getShareUrl(projectId)
}

/**
 * Export as CodeSandbox format
 */
export async function exportToCodeSandbox(
  files: ProjectFile[]
): Promise<{ files: Record<string, { content: string }> }> {
  const codesandboxFiles: Record<string, { content: string }> = {}

  for (const file of files) {
    if (file.type === 'file' && file.content) {
      codesandboxFiles[file.path] = {
        content: file.content
      }
    }
  }

  return { files: codesandboxFiles }
}

/**
 * Calculate project size
 */
export function calculateProjectSize(files: ProjectFile[]): {
  totalFiles: number
  totalSize: number
  sizeByType: Record<string, number>
} {
  let totalFiles = 0
  let totalSize = 0
  const sizeByType: Record<string, number> = {}

  for (const file of files) {
    if (file.type === 'file' && file.content) {
      totalFiles++
      const size = new Blob([file.content]).size
      totalSize += size

      const ext = file.path.split('.').pop() || 'other'
      sizeByType[ext] = (sizeByType[ext] || 0) + size
    }
  }

  return {
    totalFiles,
    totalSize,
    sizeByType
  }
}
