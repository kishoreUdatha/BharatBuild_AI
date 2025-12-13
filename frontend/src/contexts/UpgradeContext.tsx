'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import UpgradeModal from '@/components/upgrade/UpgradeModal'

interface FeatureRestriction {
  feature: string
  currentPlan: string | null
  upgradeTo: string | null
  message: string
}

interface UpgradeContextType {
  showUpgradePrompt: (restriction: FeatureRestriction) => void
  hideUpgradePrompt: () => void
  checkFeatureError: (error: any) => boolean
}

const UpgradeContext = createContext<UpgradeContextType | undefined>(undefined)

export function UpgradeProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [restriction, setRestriction] = useState<FeatureRestriction | null>(null)

  const showUpgradePrompt = useCallback((restriction: FeatureRestriction) => {
    setRestriction(restriction)
    setIsOpen(true)
  }, [])

  // Listen for feature-restricted events from API client
  useEffect(() => {
    const handleFeatureRestricted = (event: CustomEvent<FeatureRestriction>) => {
      showUpgradePrompt(event.detail)
    }

    window.addEventListener('feature-restricted', handleFeatureRestricted as EventListener)
    return () => {
      window.removeEventListener('feature-restricted', handleFeatureRestricted as EventListener)
    }
  }, [showUpgradePrompt])

  const hideUpgradePrompt = useCallback(() => {
    setIsOpen(false)
    setRestriction(null)
  }, [])

  const checkFeatureError = useCallback((error: any): boolean => {
    // Check if this is a feature restriction error
    if (error?.response?.status === 403) {
      const detail = error?.response?.data?.detail
      if (detail?.error === 'feature_not_available') {
        showUpgradePrompt({
          feature: detail.feature,
          currentPlan: detail.current_plan,
          upgradeTo: detail.upgrade_to,
          message: detail.message
        })
        return true
      }
    }

    // Also check for direct detail object (from axios or fetch)
    if (error?.status === 403 && error?.detail?.error === 'feature_not_available') {
      const detail = error.detail
      showUpgradePrompt({
        feature: detail.feature,
        currentPlan: detail.current_plan,
        upgradeTo: detail.upgrade_to,
        message: detail.message
      })
      return true
    }

    return false
  }, [showUpgradePrompt])

  return (
    <UpgradeContext.Provider value={{ showUpgradePrompt, hideUpgradePrompt, checkFeatureError }}>
      {children}
      {restriction && (
        <UpgradeModal
          isOpen={isOpen}
          onClose={hideUpgradePrompt}
          feature={restriction.feature}
          currentPlan={restriction.currentPlan}
          upgradeTo={restriction.upgradeTo}
          message={restriction.message}
        />
      )}
    </UpgradeContext.Provider>
  )
}

export function useUpgrade() {
  const context = useContext(UpgradeContext)
  if (context === undefined) {
    throw new Error('useUpgrade must be used within an UpgradeProvider')
  }
  return context
}
