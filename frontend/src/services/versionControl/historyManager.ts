/**
 * Version Control System (Mini Internal Git)
 * Provides undo/redo, version history, and change tracking
 * Like Bolt.new and Lovable use
 */

export interface FileVersion {
  id: string
  path: string
  content: string
  timestamp: Date
  message?: string
  author: 'user' | 'ai'
  changeType: 'create' | 'modify' | 'delete'
}

export interface Commit {
  id: string
  timestamp: Date
  message: string
  author: 'user' | 'ai'
  fileChanges: FileVersion[]
  parentCommitId?: string
}

export interface VersionControlState {
  commits: Commit[]
  currentCommitId: string | null
  head: number // Index in commits array
}

class VersionControlManager {
  private commits: Commit[] = []
  private currentHead: number = -1
  private maxHistory: number = 50 // Keep last 50 commits

  /**
   * Create a new commit
   */
  commit(
    fileChanges: Omit<FileVersion, 'id' | 'timestamp'>[],
    message: string,
    author: 'user' | 'ai' = 'ai'
  ): Commit {
    // If we're not at HEAD, discard forward history
    if (this.currentHead < this.commits.length - 1) {
      this.commits = this.commits.slice(0, this.currentHead + 1)
    }

    const newCommit: Commit = {
      id: this.generateCommitId(),
      timestamp: new Date(),
      message,
      author,
      fileChanges: fileChanges.map(fc => ({
        ...fc,
        id: this.generateVersionId(),
        timestamp: new Date()
      })),
      parentCommitId: this.commits[this.currentHead]?.id
    }

    this.commits.push(newCommit)
    this.currentHead = this.commits.length - 1

    // Trim old history if needed
    if (this.commits.length > this.maxHistory) {
      this.commits = this.commits.slice(-this.maxHistory)
      this.currentHead = this.commits.length - 1
    }

    return newCommit
  }

  /**
   * Undo to previous commit
   */
  undo(): Commit | null {
    if (this.currentHead > 0) {
      this.currentHead--
      return this.commits[this.currentHead]
    }
    return null
  }

  /**
   * Redo to next commit
   */
  redo(): Commit | null {
    if (this.currentHead < this.commits.length - 1) {
      this.currentHead++
      return this.commits[this.currentHead]
    }
    return null
  }

  /**
   * Can undo?
   */
  canUndo(): boolean {
    return this.currentHead > 0
  }

  /**
   * Can redo?
   */
  canRedo(): boolean {
    return this.currentHead < this.commits.length - 1
  }

  /**
   * Get current commit
   */
  getCurrentCommit(): Commit | null {
    return this.commits[this.currentHead] || null
  }

  /**
   * Get all commits (history)
   */
  getHistory(): Commit[] {
    return [...this.commits]
  }

  /**
   * Get commits for specific file
   */
  getFileHistory(filePath: string): FileVersion[] {
    const versions: FileVersion[] = []

    for (const commit of this.commits) {
      const fileChange = commit.fileChanges.find(fc => fc.path === filePath)
      if (fileChange) {
        versions.push(fileChange)
      }
    }

    return versions.reverse() // Most recent first
  }

  /**
   * Get file at specific commit
   */
  getFileAtCommit(filePath: string, commitId: string): FileVersion | null {
    const commit = this.commits.find(c => c.id === commitId)
    if (!commit) return null

    return commit.fileChanges.find(fc => fc.path === filePath) || null
  }

  /**
   * Compare two commits
   */
  compareCommits(commitId1: string, commitId2: string): {
    added: FileVersion[]
    modified: FileVersion[]
    deleted: FileVersion[]
  } {
    const commit1 = this.commits.find(c => c.id === commitId1)
    const commit2 = this.commits.find(c => c.id === commitId2)

    if (!commit1 || !commit2) {
      return { added: [], modified: [], deleted: [] }
    }

    const added: FileVersion[] = []
    const modified: FileVersion[] = []
    const deleted: FileVersion[] = []

    // Get all unique file paths
    const allPaths = new Set([
      ...commit1.fileChanges.map(fc => fc.path),
      ...commit2.fileChanges.map(fc => fc.path)
    ])

    for (const path of Array.from(allPaths)) {
      const file1 = commit1.fileChanges.find(fc => fc.path === path)
      const file2 = commit2.fileChanges.find(fc => fc.path === path)

      if (!file1 && file2) {
        added.push(file2)
      } else if (file1 && !file2) {
        deleted.push(file1)
      } else if (file1 && file2 && file1.content !== file2.content) {
        modified.push(file2)
      }
    }

    return { added, modified, deleted }
  }

  /**
   * Create a checkpoint/save point
   */
  createCheckpoint(message: string): Commit | null {
    // Get current state of all files
    return this.getCurrentCommit()
  }

  /**
   * Restore to checkpoint
   */
  restoreCheckpoint(commitId: string): Commit | null {
    const commitIndex = this.commits.findIndex(c => c.id === commitId)
    if (commitIndex === -1) return null

    this.currentHead = commitIndex
    return this.commits[this.currentHead]
  }

  /**
   * Get diff between current and previous commit
   */
  getCurrentDiff(): {
    filesChanged: number
    additions: number
    deletions: number
    changes: Array<{ path: string, type: 'add' | 'modify' | 'delete' }>
  } {
    if (this.currentHead < 1) {
      return { filesChanged: 0, additions: 0, deletions: 0, changes: [] }
    }

    const current = this.commits[this.currentHead]
    const previous = this.commits[this.currentHead - 1]

    const comparison = this.compareCommits(previous.id, current.id)

    return {
      filesChanged: comparison.added.length + comparison.modified.length + comparison.deleted.length,
      additions: comparison.added.length,
      deletions: comparison.deleted.length,
      changes: [
        ...comparison.added.map(f => ({ path: f.path, type: 'add' as const })),
        ...comparison.modified.map(f => ({ path: f.path, type: 'modify' as const })),
        ...comparison.deleted.map(f => ({ path: f.path, type: 'delete' as const }))
      ]
    }
  }

  /**
   * Clear all history
   */
  clearHistory(): void {
    this.commits = []
    this.currentHead = -1
  }

  /**
   * Export history to JSON
   */
  exportHistory(): string {
    return JSON.stringify({
      commits: this.commits,
      currentHead: this.currentHead
    }, null, 2)
  }

  /**
   * Import history from JSON
   */
  importHistory(json: string): boolean {
    try {
      const data = JSON.parse(json)
      this.commits = data.commits.map((c: any) => ({
        ...c,
        timestamp: new Date(c.timestamp),
        fileChanges: c.fileChanges.map((fc: any) => ({
          ...fc,
          timestamp: new Date(fc.timestamp)
        }))
      }))
      this.currentHead = data.currentHead
      return true
    } catch (error) {
      console.error('Failed to import history:', error)
      return false
    }
  }

  private generateCommitId(): string {
    return `commit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  private generateVersionId(): string {
    return `version-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
}

// Singleton instance
export const versionControl = new VersionControlManager()

// Zustand store for version control
import { create } from 'zustand'
import { useProject } from '@/hooks/useProject'

interface VersionControlStore {
  canUndo: boolean
  canRedo: boolean
  currentCommit: Commit | null
  history: Commit[]

  // Actions
  commit: (changes: Omit<FileVersion, 'id' | 'timestamp'>[], message: string, author?: 'user' | 'ai') => void
  undo: () => Commit | null
  redo: () => Commit | null
  getFileHistory: (path: string) => FileVersion[]
  restoreCheckpoint: (commitId: string) => void
  clearHistory: () => void
}

export const useVersionControl = create<VersionControlStore>((set, get) => ({
  canUndo: false,
  canRedo: false,
  currentCommit: null,
  history: [],

  commit: (changes, message, author = 'ai') => {
    const commit = versionControl.commit(changes, message, author)
    set({
      canUndo: versionControl.canUndo(),
      canRedo: versionControl.canRedo(),
      currentCommit: commit,
      history: versionControl.getHistory()
    })
  },

  undo: () => {
    const commit = versionControl.undo()
    if (commit) {
      set({
        canUndo: versionControl.canUndo(),
        canRedo: versionControl.canRedo(),
        currentCommit: commit,
        history: versionControl.getHistory()
      })
      return commit
    }
    return null
  },

  redo: () => {
    const commit = versionControl.redo()
    if (commit) {
      set({
        canUndo: versionControl.canUndo(),
        canRedo: versionControl.canRedo(),
        currentCommit: commit,
        history: versionControl.getHistory()
      })
      return commit
    }
    return null
  },

  getFileHistory: (path: string) => {
    return versionControl.getFileHistory(path)
  },

  restoreCheckpoint: (commitId: string) => {
    const commit = versionControl.restoreCheckpoint(commitId)
    if (commit) {
      set({
        canUndo: versionControl.canUndo(),
        canRedo: versionControl.canRedo(),
        currentCommit: commit,
        history: versionControl.getHistory()
      })
    }
  },

  clearHistory: () => {
    versionControl.clearHistory()
    set({
      canUndo: false,
      canRedo: false,
      currentCommit: null,
      history: []
    })
  }
}))
