import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'

// Reset store between tests
beforeEach(async () => {
  vi.resetModules()
})

describe('Chat Store', () => {
  describe('Message Management', () => {
    it('should have initial empty messages', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      expect(result.current.messages).toBeDefined()
      expect(Array.isArray(result.current.messages)).toBe(true)
    })

    it('should add a user message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      const userMessage = {
        id: 'msg-1',
        type: 'user' as const,
        content: 'Hello, build me a todo app',
        timestamp: new Date()
      }

      act(() => {
        result.current.addMessage(userMessage)
      })

      expect(result.current.messages).toContainEqual(userMessage)
    })

    it('should add an AI assistant message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      const aiMessage = {
        id: 'msg-2',
        type: 'assistant' as const,
        content: "I'll help you build a todo app",
        timestamp: new Date(),
        status: 'complete' as const
      }

      act(() => {
        result.current.addMessage(aiMessage)
      })

      expect(result.current.messages).toContainEqual(aiMessage)
    })

    it('should update an existing message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      const message = {
        id: 'msg-update',
        type: 'assistant' as const,
        content: 'Initial content',
        timestamp: new Date()
      }

      act(() => {
        result.current.addMessage(message)
      })

      act(() => {
        result.current.updateMessage('msg-update', { content: 'Updated content' })
      })

      const updated = result.current.messages.find(m => m.id === 'msg-update')
      expect(updated?.content).toBe('Updated content')
    })

    it('should delete a message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      const message = {
        id: 'msg-delete',
        type: 'user' as const,
        content: 'To be deleted',
        timestamp: new Date()
      }

      act(() => {
        result.current.addMessage(message)
      })

      expect(result.current.messages.find(m => m.id === 'msg-delete')).toBeDefined()

      act(() => {
        result.current.deleteMessage('msg-delete')
      })

      expect(result.current.messages.find(m => m.id === 'msg-delete')).toBeUndefined()
    })

    it('should clear all messages', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-1',
          type: 'user' as const,
          content: 'First',
          timestamp: new Date()
        })
        result.current.addMessage({
          id: 'msg-2',
          type: 'assistant' as const,
          content: 'Second',
          timestamp: new Date()
        })
      })

      act(() => {
        result.current.clearMessages()
      })

      expect(result.current.messages.length).toBe(0)
    })

    it('should append content to message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-stream',
          type: 'assistant' as const,
          content: 'Hello',
          timestamp: new Date()
        })
      })

      act(() => {
        result.current.appendToMessage('msg-stream', ' World')
      })

      const msg = result.current.messages.find(m => m.id === 'msg-stream')
      expect(msg?.content).toBe('Hello World')
    })
  })

  describe('Streaming State', () => {
    it('should have isStreaming state initially false', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      expect(result.current.isStreaming).toBe(false)
    })

    it('should set isStreaming to true when streaming starts', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.startStreaming('msg-streaming')
      })

      expect(result.current.isStreaming).toBe(true)
      expect(result.current.currentStreamingId).toBe('msg-streaming')
    })

    it('should reset streaming state when stopped', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      // Add a message first
      act(() => {
        result.current.addMessage({
          id: 'msg-streaming',
          type: 'assistant' as const,
          content: 'Streaming...',
          timestamp: new Date(),
          isStreaming: true
        })
      })

      act(() => {
        result.current.startStreaming('msg-streaming')
      })

      act(() => {
        result.current.stopStreaming()
      })

      expect(result.current.isStreaming).toBe(false)
      expect(result.current.currentStreamingId).toBeNull()
    })
  })

  describe('Message Status', () => {
    it('should update message status', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-status',
          type: 'assistant' as const,
          content: 'Processing...',
          timestamp: new Date(),
          status: 'thinking'
        })
      })

      act(() => {
        result.current.updateMessageStatus('msg-status', 'planning')
      })

      const msg = result.current.messages.find(m => m.id === 'msg-status')
      expect((msg as any)?.status).toBe('planning')
    })

    it('should transition through status states', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-lifecycle',
          type: 'assistant' as const,
          content: '',
          timestamp: new Date(),
          status: 'thinking'
        })
      })

      const statuses: ('thinking' | 'planning' | 'generating' | 'complete')[] =
        ['thinking', 'planning', 'generating', 'complete']

      for (const status of statuses) {
        act(() => {
          result.current.updateMessageStatus('msg-lifecycle', status)
        })
        const msg = result.current.messages.find(m => m.id === 'msg-lifecycle')
        expect((msg as any)?.status).toBe(status)
      }
    })
  })

  describe('File Operations', () => {
    it('should add file operation to message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-files',
          type: 'assistant' as const,
          content: 'Creating files...',
          timestamp: new Date()
        })
      })

      const operation = {
        type: 'create' as const,
        path: 'src/index.js',
        description: 'Main entry point',
        content: 'console.log("Hello")',
        status: 'pending' as const
      }

      act(() => {
        result.current.addFileOperation('msg-files', operation)
      })

      const msg = result.current.messages.find(m => m.id === 'msg-files')
      expect((msg as any)?.fileOperations).toContainEqual(operation)
    })

    it('should update file operation status', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-file-update',
          type: 'assistant' as const,
          content: 'Updating files...',
          timestamp: new Date(),
          fileOperations: [{
            type: 'create' as const,
            path: 'src/App.js',
            description: 'App component',
            status: 'pending' as const
          }]
        })
      })

      act(() => {
        result.current.updateFileOperation('msg-file-update', 'src/App.js', { status: 'complete' })
      })

      const msg = result.current.messages.find(m => m.id === 'msg-file-update')
      const operation = (msg as any)?.fileOperations?.find((op: any) => op.path === 'src/App.js')
      expect(operation?.status).toBe('complete')
    })

    it('should handle multiple file operations', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-multi-files',
          type: 'assistant' as const,
          content: 'Creating multiple files...',
          timestamp: new Date()
        })
      })

      const files = [
        { type: 'create' as const, path: 'package.json', description: 'Package config', status: 'pending' as const },
        { type: 'create' as const, path: 'src/index.js', description: 'Entry point', status: 'pending' as const },
        { type: 'create' as const, path: 'src/App.js', description: 'App component', status: 'pending' as const }
      ]

      for (const file of files) {
        act(() => {
          result.current.addFileOperation('msg-multi-files', file)
        })
      }

      const msg = result.current.messages.find(m => m.id === 'msg-multi-files')
      expect((msg as any)?.fileOperations?.length).toBe(3)
    })
  })

  describe('Thinking Steps', () => {
    it('should add thinking step to message', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-thinking',
          type: 'assistant' as const,
          content: '',
          timestamp: new Date()
        })
      })

      const step = {
        label: 'Analyzing requirements',
        status: 'active' as const,
        description: 'Understanding the project needs'
      }

      act(() => {
        result.current.addThinkingStep('msg-thinking', step)
      })

      const msg = result.current.messages.find(m => m.id === 'msg-thinking')
      expect((msg as any)?.thinkingSteps).toContainEqual(step)
    })

    it('should update thinking step', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-step-update',
          type: 'assistant' as const,
          content: '',
          timestamp: new Date(),
          thinkingSteps: [{
            label: 'Planning',
            status: 'pending' as const
          }]
        })
      })

      act(() => {
        result.current.updateThinkingStep('msg-step-update', 'Planning', { status: 'complete' })
      })

      const msg = result.current.messages.find(m => m.id === 'msg-step-update')
      const step = (msg as any)?.thinkingSteps?.find((s: any) => s.label === 'Planning')
      expect(step?.status).toBe('complete')
    })

    it('should update all thinking steps at once', async () => {
      const { useChatStore } = await import('@/store/chatStore')
      const { result } = renderHook(() => useChatStore())

      act(() => {
        result.current.addMessage({
          id: 'msg-bulk-steps',
          type: 'assistant' as const,
          content: '',
          timestamp: new Date()
        })
      })

      const steps = [
        { label: 'Step 1', status: 'complete' as const },
        { label: 'Step 2', status: 'active' as const },
        { label: 'Step 3', status: 'pending' as const }
      ]

      act(() => {
        result.current.updateThinkingSteps('msg-bulk-steps', steps)
      })

      const msg = result.current.messages.find(m => m.id === 'msg-bulk-steps')
      expect((msg as any)?.thinkingSteps).toEqual(steps)
    })
  })
})

describe('Project Store', () => {
  it('should have projectStore exports', async () => {
    const projectStore = await import('@/store/projectStore')

    expect(projectStore).toBeDefined()
    expect(projectStore.useProjectStore).toBeDefined()
  })

  it('should have initial null project', async () => {
    const { useProjectStore } = await import('@/store/projectStore')
    const { result } = renderHook(() => useProjectStore())

    expect(result.current.currentProject).toBeNull()
  })

  it('should set current project', async () => {
    const { useProjectStore } = await import('@/store/projectStore')
    const { result } = renderHook(() => useProjectStore())

    const project = {
      id: 'proj-1',
      name: 'Test Project',
      description: 'A test project',
      files: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }

    act(() => {
      result.current.setCurrentProject(project)
    })

    expect(result.current.currentProject?.id).toBe('proj-1')
    expect(result.current.currentProject?.name).toBe('Test Project')
  })

  it('should update project', async () => {
    const { useProjectStore } = await import('@/store/projectStore')
    const { result } = renderHook(() => useProjectStore())

    const project = {
      id: 'proj-update',
      name: 'Original Name',
      files: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }

    act(() => {
      result.current.setCurrentProject(project)
    })

    act(() => {
      result.current.updateProject({ name: 'Updated Name' })
    })

    expect(result.current.currentProject?.name).toBe('Updated Name')
  })

  it('should add file to project', async () => {
    const { useProjectStore } = await import('@/store/projectStore')
    const { result } = renderHook(() => useProjectStore())

    act(() => {
      result.current.setCurrentProject({
        id: 'proj-files',
        name: 'File Test',
        files: [],
        createdAt: new Date(),
        updatedAt: new Date()
      })
    })

    const file = {
      path: 'src/index.js',
      content: 'console.log("test")',
      language: 'javascript',
      type: 'file' as const
    }

    act(() => {
      result.current.addFile(file)
    })

    // Find file in nested structure
    const findFile = (files: any[], path: string): any => {
      for (const f of files) {
        if (f.path === path || f.path.endsWith(path.split('/').pop()!)) return f
        if (f.children) {
          const found = findFile(f.children, path)
          if (found) return found
        }
      }
      return null
    }

    const found = findFile(result.current.currentProject?.files || [], 'index.js')
    expect(found).toBeDefined()
  })

  it('should update file content', async () => {
    const { useProjectStore } = await import('@/store/projectStore')
    const { result } = renderHook(() => useProjectStore())

    act(() => {
      result.current.setCurrentProject({
        id: 'proj-update-file',
        name: 'Update File Test',
        files: [{
          path: 'test.js',
          content: 'original',
          language: 'javascript',
          type: 'file'
        }],
        createdAt: new Date(),
        updatedAt: new Date()
      })
    })

    act(() => {
      result.current.updateFile('test.js', 'updated content')
    })

    const file = result.current.currentProject?.files.find(f => f.path === 'test.js')
    expect(file?.content).toBe('updated content')
  })

  it('should delete file from project', async () => {
    const { useProjectStore } = await import('@/store/projectStore')
    const { result } = renderHook(() => useProjectStore())

    act(() => {
      result.current.setCurrentProject({
        id: 'proj-delete-file',
        name: 'Delete File Test',
        files: [{
          path: 'to-delete.js',
          content: 'delete me',
          language: 'javascript',
          type: 'file'
        }],
        createdAt: new Date(),
        updatedAt: new Date()
      })
    })

    act(() => {
      result.current.deleteFile('to-delete.js')
    })

    const file = result.current.currentProject?.files.find(f => f.path === 'to-delete.js')
    expect(file).toBeUndefined()
  })

  describe('Tab Management', () => {
    it('should open a tab', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      const file = {
        path: 'src/index.js',
        content: 'code',
        language: 'javascript',
        type: 'file' as const
      }

      act(() => {
        result.current.openTab(file)
      })

      expect(result.current.openTabs).toContainEqual(file)
      expect(result.current.activeTabPath).toBe('src/index.js')
    })

    it('should close a tab', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      const file = {
        path: 'to-close.js',
        content: 'code',
        language: 'javascript',
        type: 'file' as const
      }

      act(() => {
        result.current.openTab(file)
      })

      act(() => {
        result.current.closeTab('to-close.js')
      })

      expect(result.current.openTabs.find(t => t.path === 'to-close.js')).toBeUndefined()
    })

    it('should set active tab', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      const file1 = { path: 'file1.js', content: '', language: 'javascript', type: 'file' as const }
      const file2 = { path: 'file2.js', content: '', language: 'javascript', type: 'file' as const }

      act(() => {
        result.current.openTab(file1)
        result.current.openTab(file2)
      })

      act(() => {
        result.current.setActiveTab('file1.js')
      })

      expect(result.current.activeTabPath).toBe('file1.js')
    })

    it('should close all tabs', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.openTab({ path: 'a.js', content: '', language: 'javascript', type: 'file' })
        result.current.openTab({ path: 'b.js', content: '', language: 'javascript', type: 'file' })
        result.current.openTab({ path: 'c.js', content: '', language: 'javascript', type: 'file' })
      })

      act(() => {
        result.current.closeAllTabs()
      })

      expect(result.current.openTabs.length).toBe(0)
      expect(result.current.activeTabPath).toBeNull()
    })
  })

  describe('Session Management', () => {
    it('should set session ID', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.setSessionId('session-123')
      })

      expect(result.current.sessionId).toBe('session-123')
    })

    it('should set download URL', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.setDownloadUrl('https://example.com/download.zip')
      })

      expect(result.current.downloadUrl).toBe('https://example.com/download.zip')
    })

    it('should clear session', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.setSessionId('session-to-clear')
        result.current.setDownloadUrl('https://example.com/file.zip')
      })

      act(() => {
        result.current.clearSession()
      })

      expect(result.current.sessionId).toBeNull()
      expect(result.current.downloadUrl).toBeNull()
    })
  })

  describe('File Sync', () => {
    it('should mark file pending save', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.markFilePendingSave('src/pending.js')
      })

      expect(result.current.pendingSaves.has('src/pending.js')).toBe(true)
    })

    it('should mark file saved', async () => {
      const { useProjectStore } = await import('@/store/projectStore')
      const { result } = renderHook(() => useProjectStore())

      act(() => {
        result.current.markFilePendingSave('src/saved.js')
      })

      act(() => {
        result.current.markFileSaved('src/saved.js')
      })

      expect(result.current.pendingSaves.has('src/saved.js')).toBe(false)
    })
  })
})
