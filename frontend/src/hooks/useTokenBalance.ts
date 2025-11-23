import { useCallback } from 'react'
import { useTokenStore } from '@/store/tokenStore'

export const useTokenBalance = () => {
  const {
    balance,
    totalUsed,
    usageHistory,
    setBalance,
    deductTokens,
    addTokens,
    loadUsageHistory
  } = useTokenStore()

  const hasEnoughTokens = useCallback((required: number): boolean => {
    return balance >= required
  }, [balance])

  const formatBalance = useCallback((): string => {
    return balance.toLocaleString()
  }, [balance])

  const getUsagePercentage = useCallback((total: number = 10000): number => {
    return Math.round((totalUsed / total) * 100)
  }, [totalUsed])

  return {
    balance,
    totalUsed,
    usageHistory,
    setBalance,
    deductTokens,
    addTokens,
    loadUsageHistory,
    hasEnoughTokens,
    formatBalance,
    getUsagePercentage
  }
}
