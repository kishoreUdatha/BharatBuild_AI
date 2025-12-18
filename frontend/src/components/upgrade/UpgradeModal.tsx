'use client'

import React from 'react'
import { X, Sparkles, Zap, FileText, Code, Key, ArrowRight, FolderPlus } from 'lucide-react'

interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  feature: string
  currentPlan: string | null
  upgradeTo: string | null
  message: string
}

const FEATURE_INFO: Record<string, { icon: React.ReactNode; title: string; description: string }> = {
  project_limit: {
    icon: <FolderPlus className="w-8 h-8" />,
    title: 'Project Limit Reached',
    description: 'You have reached your project limit. Upgrade to Premium to create more projects and unlock unlimited project generation.'
  },
  agentic_mode: {
    icon: <Zap className="w-8 h-8" />,
    title: 'Agentic Mode',
    description: 'Let AI autonomously read files, write code, and execute commands to build your project.'
  },
  document_generation: {
    icon: <FileText className="w-8 h-8" />,
    title: 'Document Generation',
    description: 'Generate professional documents including SRS, technical reports, and presentations.'
  },
  code_execution: {
    icon: <Code className="w-8 h-8" />,
    title: 'Code Execution',
    description: 'Run your code in secure sandboxed containers to test and preview your applications.'
  },
  api_access: {
    icon: <Key className="w-8 h-8" />,
    title: 'API Access',
    description: 'Create API keys for programmatic access to BharatBuild AI services.'
  },
  priority_queue: {
    icon: <Sparkles className="w-8 h-8" />,
    title: 'Priority Queue',
    description: 'Skip the queue and get faster responses for all your AI requests.'
  }
}

const PLAN_PRICES: Record<string, string> = {
  Student: '4,499',
  Premium: '4,499',
  Pro: '4,499',
  Enterprise: '4,499'
}

export default function UpgradeModal({
  isOpen,
  onClose,
  feature,
  currentPlan,
  upgradeTo,
  message
}: UpgradeModalProps) {
  if (!isOpen) return null

  const featureInfo = FEATURE_INFO[feature] || {
    icon: <Sparkles className="w-8 h-8" />,
    title: feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    description: 'Unlock this premium feature with an upgraded plan.'
  }

  const handleUpgrade = () => {
    // Navigate to pricing page
    window.location.href = '/pricing'
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 bg-[#1a1a1a] rounded-2xl border border-[#333] shadow-2xl overflow-hidden">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-[#252525] transition-colors text-gray-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Content */}
        <div className="p-8 text-center">
          {/* Icon */}
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-white">
            {featureInfo.icon}
          </div>

          {/* Title */}
          <h2 className="text-2xl font-bold text-white mb-2">
            Upgrade to Unlock
          </h2>

          {/* Feature name */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/20 text-purple-400 text-sm font-medium mb-4">
            {featureInfo.title}
          </div>

          {/* Description */}
          <p className="text-gray-400 mb-6">
            {featureInfo.description}
          </p>

          {/* Current plan info */}
          {currentPlan && (
            <p className="text-gray-500 text-sm mb-6">
              Your current plan: <span className="text-gray-300">{currentPlan}</span>
            </p>
          )}

          {/* Upgrade button */}
          {upgradeTo && (
            <button
              onClick={handleUpgrade}
              className="w-full py-3 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold flex items-center justify-center gap-2 hover:from-purple-700 hover:to-blue-700 transition-all"
            >
              <span>Upgrade to {upgradeTo}</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          )}

          {upgradeTo && PLAN_PRICES[upgradeTo] && (
            <p className="mt-3 text-sm text-gray-500">
              Starting at just Rs. {PLAN_PRICES[upgradeTo]}
            </p>
          )}

          {/* Alternative action */}
          <button
            onClick={onClose}
            className="mt-4 text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            Maybe later
          </button>
        </div>
      </div>
    </div>
  )
}
