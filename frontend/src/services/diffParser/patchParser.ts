/**
 * Unified Diff/Patch Parser
 * Parses unified diff format (like Git) for AI code modifications
 */

export interface DiffHunk {
  oldStart: number
  oldLines: number
  newStart: number
  newLines: number
  changes: DiffChange[]
}

export interface DiffChange {
  type: 'add' | 'remove' | 'context'
  content: string
  lineNumber: number
}

export interface ParsedDiff {
  oldFile: string
  newFile: string
  hunks: DiffHunk[]
}

/**
 * Parse unified diff format
 *
 * Example input:
 * --- a/src/App.tsx
 * +++ b/src/App.tsx
 * @@ -10,3 +10,7 @@
 *  existing line
 * -removed line
 * +added line
 *  existing line
 */
export function parseDiff(diffText: string): ParsedDiff {
  const lines = diffText.split('\n')
  const diff: ParsedDiff = {
    oldFile: '',
    newFile: '',
    hunks: []
  }

  let currentHunk: DiffHunk | null = null
  let lineNumber = 0

  for (const line of lines) {
    // Parse file headers
    if (line.startsWith('---')) {
      diff.oldFile = line.replace(/^--- a\//, '').trim()
      continue
    }

    if (line.startsWith('+++')) {
      diff.newFile = line.replace(/^\+\+\+ b\//, '').trim()
      continue
    }

    // Parse hunk header: @@ -10,3 +10,7 @@
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@/)
      if (match) {
        if (currentHunk) {
          diff.hunks.push(currentHunk)
        }

        currentHunk = {
          oldStart: parseInt(match[1]),
          oldLines: match[2] ? parseInt(match[2]) : 1,
          newStart: parseInt(match[3]),
          newLines: match[4] ? parseInt(match[4]) : 1,
          changes: []
        }
        lineNumber = parseInt(match[3])
      }
      continue
    }

    // Parse changes
    if (currentHunk && line.length > 0) {
      const firstChar = line[0]
      const content = line.slice(1)

      if (firstChar === '+') {
        currentHunk.changes.push({
          type: 'add',
          content,
          lineNumber: lineNumber++
        })
      } else if (firstChar === '-') {
        currentHunk.changes.push({
          type: 'remove',
          content,
          lineNumber: lineNumber
        })
      } else if (firstChar === ' ') {
        currentHunk.changes.push({
          type: 'context',
          content,
          lineNumber: lineNumber++
        })
      }
    }
  }

  // Add last hunk
  if (currentHunk) {
    diff.hunks.push(currentHunk)
  }

  return diff
}

/**
 * Extract file path from diff
 */
export function extractFilePath(diffText: string): string {
  const match = diffText.match(/^\+\+\+ b\/(.+)$/m)
  return match ? match[1] : ''
}

/**
 * Check if diff is valid
 */
export function isValidDiff(diffText: string): boolean {
  return diffText.includes('---') &&
         diffText.includes('+++') &&
         diffText.includes('@@')
}

/**
 * Parse multiple diffs from AI response
 * AI might return multiple file changes
 */
export function parseMultipleDiffs(text: string): ParsedDiff[] {
  const diffs: ParsedDiff[] = []

  // Split by file headers
  const diffBlocks = text.split(/(?=--- a\/)/)

  for (const block of diffBlocks) {
    if (isValidDiff(block)) {
      try {
        diffs.push(parseDiff(block))
      } catch (error) {
        console.error('Failed to parse diff block:', error)
      }
    }
  }

  return diffs
}
