/**
 * Offline queue for handling file saves when offline
 * Queues operations and processes them when connection is restored
 */

interface QueuedOperation {
  type: 'save_file' | 'save_files_bulk'
  projectId: string
  path?: string
  content?: string
  files?: Array<{ path: string; content: string }>
  timestamp: number
}

class OfflineQueue {
  private queue: QueuedOperation[] = []
  private isProcessing = false
  private storageKey = 'bharatbuild_offline_queue'

  constructor() {
    // Load queue from localStorage on init
    if (typeof window !== 'undefined') {
      this.loadFromStorage()

      // Process queue when online
      window.addEventListener('online', () => this.processQueue())
    }
  }

  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.storageKey)
      if (stored) {
        this.queue = JSON.parse(stored)
      }
    } catch (e) {
      console.warn('Failed to load offline queue:', e)
    }
  }

  private saveToStorage(): void {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.queue))
    } catch (e) {
      console.warn('Failed to save offline queue:', e)
    }
  }

  /**
   * Queue a single file save operation
   */
  queueSaveFile(projectId: string, path: string, content: string): void {
    // Remove any existing operation for the same file
    this.queue = this.queue.filter(
      op => !(op.type === 'save_file' && op.projectId === projectId && op.path === path)
    )

    this.queue.push({
      type: 'save_file',
      projectId,
      path,
      content,
      timestamp: Date.now(),
    })

    this.saveToStorage()

    // Try to process immediately if online
    if (navigator.onLine) {
      this.processQueue()
    }
  }

  /**
   * Queue a bulk file save operation
   */
  queueSaveFilesBulk(projectId: string, files: Array<{ path: string; content: string }>): void {
    this.queue.push({
      type: 'save_files_bulk',
      projectId,
      files,
      timestamp: Date.now(),
    })

    this.saveToStorage()

    // Try to process immediately if online
    if (navigator.onLine) {
      this.processQueue()
    }
  }

  /**
   * Process the queue
   */
  async processQueue(): Promise<void> {
    if (this.isProcessing || this.queue.length === 0 || !navigator.onLine) {
      return
    }

    this.isProcessing = true

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
      const token = localStorage.getItem('access_token')

      while (this.queue.length > 0) {
        const operation = this.queue[0]

        try {
          if (operation.type === 'save_file' && operation.path && operation.content) {
            await fetch(`${API_BASE_URL}/sync/file`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` }),
              },
              body: JSON.stringify({
                project_id: operation.projectId,
                path: operation.path,
                content: operation.content,
              }),
            })
          } else if (operation.type === 'save_files_bulk' && operation.files) {
            await fetch(`${API_BASE_URL}/sync/files/${operation.projectId}`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...(token && { 'Authorization': `Bearer ${token}` }),
              },
              body: JSON.stringify({ files: operation.files }),
            })
          }

          // Remove processed operation
          this.queue.shift()
          this.saveToStorage()
        } catch (error) {
          console.warn('Failed to process queued operation:', error)
          break // Stop processing on error
        }
      }
    } finally {
      this.isProcessing = false
    }
  }

  /**
   * Get queue length
   */
  get length(): number {
    return this.queue.length
  }

  /**
   * Clear the queue
   */
  clear(): void {
    this.queue = []
    this.saveToStorage()
  }
}

export const offlineQueue = new OfflineQueue()
export default offlineQueue
