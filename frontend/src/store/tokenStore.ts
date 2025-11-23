import { create } from 'zustand'

export interface TokenUsage {
  id: string
  messageId: string
  tokensUsed: number
  timestamp: Date
  operation: string
}

interface TokenState {
  balance: number
  totalUsed: number
  usageHistory: TokenUsage[]

  // Actions
  setBalance: (balance: number) => void
  deductTokens: (amount: number, messageId: string, operation: string) => void
  addTokens: (amount: number) => void
  loadUsageHistory: (history: TokenUsage[]) => void
}

export const useTokenStore = create<TokenState>((set, get) => ({
  balance: 10000, // Default balance for demo
  totalUsed: 0,
  usageHistory: [],

  setBalance: (balance) => {
    set({ balance })
  },

  deductTokens: (amount, messageId, operation) => {
    const usage: TokenUsage = {
      id: `usage-${Date.now()}`,
      messageId,
      tokensUsed: amount,
      timestamp: new Date(),
      operation
    }

    set((state) => ({
      balance: Math.max(0, state.balance - amount),
      totalUsed: state.totalUsed + amount,
      usageHistory: [...state.usageHistory, usage]
    }))
  },

  addTokens: (amount) => {
    set((state) => ({
      balance: state.balance + amount
    }))
  },

  loadUsageHistory: (history) => {
    set({ usageHistory: history })
  }
}))
