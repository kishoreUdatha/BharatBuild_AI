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
  description?: string
  details?: string
  taskNumber?: number
  icon?: string
  category?: string
  deliverables?: string
}

export interface PlanData {
  projectName?: string
  projectDescription?: string
  projectType?: string
  complexity?: string
  estimatedFiles?: string
  techStack?: { name: string; items: string }[]
  features?: { icon: string; name: string; description: string }[]
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
  planData?: PlanData
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
  setMessages: (messages: Message[]) => void  // Load messages from backend
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
  addThinkingStep: (id: string, step: ThinkingStep) => void
  updateThinkingStep: (id: string, label: string, updates: Partial<ThinkingStep>) => void
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

  setMessages: (messages) => {
    console.log('[chatStore.setMessages] Setting messages:', messages.length)
    set({ messages })
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
    console.log('[chatStore.updateThinkingSteps] Called with id:', id, 'steps count:', steps.length)
    console.log('[chatStore.updateThinkingSteps] Steps data:', JSON.stringify(steps, null, 2))
    set((state) => {
      const messageFound = state.messages.find(m => m.id === id && m.type === 'assistant')
      console.log('[chatStore.updateThinkingSteps] Message found:', !!messageFound, 'Message id:', messageFound?.id)

      const updatedMessages = state.messages.map((msg) =>
        msg.id === id && msg.type === 'assistant'
          ? { ...msg, thinkingSteps: steps }
          : msg
      )

      const updatedMessage = updatedMessages.find(m => m.id === id && m.type === 'assistant')
      console.log('[chatStore.updateThinkingSteps] After update, thinkingSteps count:', (updatedMessage as any)?.thinkingSteps?.length)

      return { messages: updatedMessages }
    })
  },

  addThinkingStep: (id, step) => {
    console.log('[chatStore.addThinkingStep] Adding step:', step.label, 'to message:', id)
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id === id && msg.type === 'assistant') {
          const thinkingSteps = msg.thinkingSteps || []
          console.log('[chatStore.addThinkingStep] Current steps count:', thinkingSteps.length)
          return {
            ...msg,
            thinkingSteps: [...thinkingSteps, step]
          }
        }
        return msg
      })
    }))
  },

  updateThinkingStep: (id, label, updates) => {
    console.log('[chatStore.updateThinkingStep] Updating step:', label, 'in message:', id, 'with:', updates)
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id === id && msg.type === 'assistant') {
          const thinkingSteps = msg.thinkingSteps || []
          return {
            ...msg,
            thinkingSteps: thinkingSteps.map((step) =>
              step.label === label ? { ...step, ...updates } : step
            )
          }
        }
        return msg
      })
    }))
  }
}))
