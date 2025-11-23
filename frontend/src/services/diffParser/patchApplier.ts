/**
 * Patch Applier - Applies unified diffs to files
 * Core component for AI code modifications
 */

import { ParsedDiff, DiffHunk, parseDiff } from './patchParser'

export interface PatchResult {
  success: boolean
  newContent?: string
  error?: string
  conflicts?: string[]
}

/**
 * Apply a unified diff patch to original content
 */
export function applyPatch(
  originalContent: string,
  patch: string | ParsedDiff
): PatchResult {
  try {
    const diff = typeof patch === 'string' ? parseDiff(patch) : patch
    const lines = originalContent.split('\n')

    // Apply each hunk
    for (const hunk of diff.hunks) {
      const result = applyHunk(lines, hunk)
      if (!result.success) {
        return result
      }
    }

    return {
      success: true,
      newContent: lines.join('\n')
    }
  } catch (error: any) {
    return {
      success: false,
      error: `Failed to apply patch: ${error.message}`
    }
  }
}

/**
 * Apply a single hunk to the lines array
 */
function applyHunk(lines: string[], hunk: DiffHunk): PatchResult {
  const { oldStart, changes } = hunk

  // Convert to 0-based index
  let currentLine = oldStart - 1
  const originalLines = [...lines]

  try {
    for (const change of changes) {
      switch (change.type) {
        case 'context':
          // Verify context line matches
          if (lines[currentLine] !== change.content) {
            return {
              success: false,
              error: `Context mismatch at line ${currentLine + 1}. Expected: "${change.content}", Got: "${lines[currentLine]}"`,
              conflicts: [
                `Line ${currentLine + 1}`,
                `Expected: ${change.content}`,
                `Got: ${lines[currentLine]}`
              ]
            }
          }
          currentLine++
          break

        case 'remove':
          // Verify line to remove matches
          if (lines[currentLine] !== change.content) {
            return {
              success: false,
              error: `Cannot remove line ${currentLine + 1}. Content mismatch.`,
              conflicts: [
                `Line ${currentLine + 1}`,
                `Expected to remove: ${change.content}`,
                `Got: ${lines[currentLine]}`
              ]
            }
          }
          // Remove the line
          lines.splice(currentLine, 1)
          break

        case 'add':
          // Insert new line
          lines.splice(currentLine, 0, change.content)
          currentLine++
          break
      }
    }

    return { success: true }
  } catch (error: any) {
    // Restore original lines on error
    lines.length = 0
    lines.push(...originalLines)

    return {
      success: false,
      error: `Hunk application failed: ${error.message}`
    }
  }
}

/**
 * Apply patch with fuzzy matching (more lenient)
 * Useful when exact line matching fails
 */
export function applyPatchFuzzy(
  originalContent: string,
  patch: string | ParsedDiff,
  fuzziness: number = 2
): PatchResult {
  const diff = typeof patch === 'string' ? parseDiff(patch) : patch
  const lines = originalContent.split('\n')

  for (const hunk of diff.hunks) {
    // Try exact match first
    let result = applyHunk(lines, hunk)

    // If failed, try fuzzy matching
    if (!result.success && fuzziness > 0) {
      result = applyHunkFuzzy(lines, hunk, fuzziness)
    }

    if (!result.success) {
      return result
    }
  }

  return {
    success: true,
    newContent: lines.join('\n')
  }
}

/**
 * Apply hunk with fuzzy line matching
 */
function applyHunkFuzzy(
  lines: string[],
  hunk: DiffHunk,
  fuzziness: number
): PatchResult {
  const { oldStart, changes } = hunk

  // Try to find the hunk at nearby lines
  for (let offset = -fuzziness; offset <= fuzziness; offset++) {
    const testLine = oldStart - 1 + offset
    if (testLine < 0 || testLine >= lines.length) continue

    // Create modified hunk with offset
    const modifiedHunk = {
      ...hunk,
      oldStart: oldStart + offset
    }

    const result = applyHunk([...lines], modifiedHunk)
    if (result.success) {
      // Apply to actual lines
      return applyHunk(lines, modifiedHunk)
    }
  }

  return {
    success: false,
    error: `Could not find matching context for hunk (tried fuzziness: ${fuzziness})`
  }
}

/**
 * Create a reverse patch (for undo)
 */
export function reversePatch(patch: string | ParsedDiff): ParsedDiff {
  const diff = typeof patch === 'string' ? parseDiff(patch) : patch

  return {
    oldFile: diff.newFile,
    newFile: diff.oldFile,
    hunks: diff.hunks.map(hunk => ({
      oldStart: hunk.newStart,
      oldLines: hunk.newLines,
      newStart: hunk.oldStart,
      newLines: hunk.oldLines,
      changes: hunk.changes.map(change => ({
        ...change,
        type: change.type === 'add' ? 'remove' : change.type === 'remove' ? 'add' : 'context'
      }))
    }))
  }
}

/**
 * Preview patch changes without applying
 */
export function previewPatch(
  originalContent: string,
  patch: string | ParsedDiff
): {
  additions: number
  deletions: number
  changes: Array<{ line: number, type: 'add' | 'remove', content: string }>
} {
  const diff = typeof patch === 'string' ? parseDiff(patch) : patch

  let additions = 0
  let deletions = 0
  const changes: Array<{ line: number, type: 'add' | 'remove', content: string }> = []

  for (const hunk of diff.hunks) {
    let line = hunk.newStart

    for (const change of hunk.changes) {
      if (change.type === 'add') {
        additions++
        changes.push({ line, type: 'add', content: change.content })
        line++
      } else if (change.type === 'remove') {
        deletions++
        changes.push({ line, type: 'remove', content: change.content })
      } else {
        line++
      }
    }
  }

  return { additions, deletions, changes }
}
