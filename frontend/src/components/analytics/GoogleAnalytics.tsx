'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

// Extend Window interface to include gtag
declare global {
  interface Window {
    gtag: (...args: unknown[]) => void
    dataLayer: unknown[]
  }
}

const GA_MEASUREMENT_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || 'G-XXXXXXXXXX'

// Track page views
export function usePageTracking() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (typeof window.gtag !== 'undefined') {
      const url = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : '')
      window.gtag('config', GA_MEASUREMENT_ID, {
        page_path: url,
      })
    }
  }, [pathname, searchParams])
}

// Custom event tracking
export function trackEvent(
  action: string,
  category: string,
  label?: string,
  value?: number
) {
  if (typeof window.gtag !== 'undefined') {
    window.gtag('event', action, {
      event_category: category,
      event_label: label,
      value: value,
    })
  }
}

// Conversion tracking
export function trackConversion(conversionId: string, value?: number) {
  if (typeof window.gtag !== 'undefined') {
    window.gtag('event', 'conversion', {
      send_to: conversionId,
      value: value,
      currency: 'INR',
    })
  }
}

// E-commerce tracking
export function trackPurchase(
  transactionId: string,
  value: number,
  items: Array<{
    item_id: string
    item_name: string
    price: number
    quantity: number
  }>
) {
  if (typeof window.gtag !== 'undefined') {
    window.gtag('event', 'purchase', {
      transaction_id: transactionId,
      value: value,
      currency: 'INR',
      items: items,
    })
  }
}

// Pre-defined event helpers for BharatBuild
export const analytics = {
  // User actions
  signUp: (method: string) => trackEvent('sign_up', 'engagement', method),
  login: (method: string) => trackEvent('login', 'engagement', method),

  // Project actions
  projectCreated: (projectType: string) => trackEvent('project_created', 'projects', projectType),
  projectGenerated: (techStack: string) => trackEvent('project_generated', 'projects', techStack),
  projectDownloaded: (format: string) => trackEvent('project_downloaded', 'projects', format),
  documentDownloaded: (docType: string) => trackEvent('document_downloaded', 'documents', docType),

  // Build actions
  buildStarted: (mode: string) => trackEvent('build_started', 'builder', mode),
  buildCompleted: (mode: string) => trackEvent('build_completed', 'builder', mode),
  codeGenerated: (framework: string) => trackEvent('code_generated', 'builder', framework),
  errorFixed: (errorType: string) => trackEvent('error_fixed', 'builder', errorType),

  // Pricing actions
  pricingViewed: () => trackEvent('pricing_viewed', 'conversion'),
  planSelected: (planName: string) => trackEvent('plan_selected', 'conversion', planName),
  couponApplied: (couponCode: string) => trackEvent('coupon_applied', 'conversion', couponCode),
  paymentInitiated: (planName: string, value: number) => {
    trackEvent('payment_initiated', 'conversion', planName, value)
  },
  paymentCompleted: (planName: string, value: number) => {
    trackEvent('payment_completed', 'conversion', planName, value)
    trackPurchase(`order_${Date.now()}`, value, [
      { item_id: planName, item_name: planName, price: value, quantity: 1 },
    ])
  },

  // Campus drive actions
  campusDriveRegistered: (college: string) => trackEvent('campus_registered', 'campus_drive', college),
  quizStarted: () => trackEvent('quiz_started', 'campus_drive'),
  quizCompleted: (score: number) => trackEvent('quiz_completed', 'campus_drive', 'score', score),

  // Content engagement
  showcaseViewed: (projectId: string) => trackEvent('showcase_viewed', 'engagement', projectId),
  demoClicked: (demoType: string) => trackEvent('demo_clicked', 'engagement', demoType),
  featureExplored: (featureName: string) => trackEvent('feature_explored', 'engagement', featureName),

  // Search and navigation
  searchPerformed: (query: string) => trackEvent('search', 'navigation', query),
  ctaClicked: (ctaName: string) => trackEvent('cta_clicked', 'navigation', ctaName),

  // Errors
  errorOccurred: (errorType: string, errorMessage: string) => {
    trackEvent('error', 'errors', `${errorType}: ${errorMessage}`)
  },
}

// Page tracking component
export function PageViewTracker() {
  usePageTracking()
  return null
}
