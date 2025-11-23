import { create } from 'zustand'

export interface UserMessage {
  id: string
  type: 'user'
  content: string
  timestamp: Date
  attachedFiles?: string[]
}

export interface ThinkingStep {
  label: string
  status: 'pending' | 'active' | 'complete'
}

export interface AIMessage {
  id: string
  type: 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
  status?: 'thinking' | 'planning' | 'generating' | 'complete'
  fileOperations?: FileOperation[]
  thinkingSteps?: ThinkingStep[]
}

export interface FileOperation {
  type: 'create' | 'modify' | 'delete'
  path: string
  description: string
  content?: string
  status: 'pending' | 'in-progress' | 'complete' | 'error'
}

export type Message = UserMessage | AIMessage

interface ChatState {
  messages: Message[]
  currentStreamingId: string | null
  isStreaming: boolean

  // Actions
  addMessage: (message: Message) => void
  updateMessage: (id: string, updates: Partial<Message>) => void
  deleteMessage: (id: string) => void
  clearMessages: () => void
  startStreaming: (messageId: string) => void
  stopStreaming: () => void
  appendToMessage: (id: string, content: string) => void
  updateMessageStatus: (id: string, status: AIMessage['status']) => void
  addFileOperation: (messageId: string, operation: FileOperation) => void
  updateFileOperation: (messageId: string, operationPath: string, updates: Partial<FileOperation>) => void
  updateThinkingSteps: (id: string, steps: ThinkingStep[]) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  currentStreamingId: null,
  isStreaming: false,

  addMessage: (message) => {
    set((state) => ({
      messages: [...state.messages, message]
    }))
  },

  updateMessage: (id, updates) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...updates } : msg
      )
    }))
  },

  deleteMessage: (id) => {
    set((state) => ({
      messages: state.messages.filter((msg) => msg.id !== id)
    }))
  },

  clearMessages: () => {
    set({ messages: [] })
  },

  startStreaming: (messageId) => {
    set({
      currentStreamingId: messageId,
      isStreaming: true
    })
  },

  stopStreaming: () => {
    const { currentStreamingId } = get()
    if (currentStreamingId) {
      get().updateMessage(currentStreamingId, { isStreaming: false })
    }
    set({
      currentStreamingId: null,
      isStreaming: false
    })
  },

  appendToMessage: (id, content) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id
          ? { ...msg, content: msg.content + content }
          : msg
      )
    }))
  },

  updateMessageStatus: (id, status) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id && msg.type === 'assistant'
          ? { ...msg, status }
          : msg
      )
    }))
  },

  addFileOperation: (messageId, operation) => {
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id === messageId && msg.type === 'assistant') {
          const fileOperations = msg.fileOperations || []
          return {
            ...msg,
            fileOperations: [...fileOperations, operation]
          }
        }
        return msg
      })
    }))
  },

  updateFileOperation: (messageId, operationPath, updates) => {
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id === messageId && msg.type === 'assistant') {
          const fileOperations = msg.fileOperations || []
          return {
            ...msg,
            fileOperations: fileOperations.map((op) =>
              op.path === operationPath ? { ...op, ...updates } : op
            )
          }
        }
        return msg
      })
    }))
  },

  updateThinkingSteps: (id, steps) => {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id && msg.type === 'assistant'
          ? { ...msg, thinkingSteps: steps }
          : msg
      )
    }))
  }
}))
