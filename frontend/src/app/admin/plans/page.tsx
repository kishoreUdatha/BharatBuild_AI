'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { apiClient } from '@/lib/api-client'
import { Layers, Users, Edit, Save, X, Sparkles, Database, Zap, Code, FileText, Key } from 'lucide-react'

interface FeatureFlags {
  agentic_mode?: boolean
  document_generation?: boolean
  code_execution?: boolean
  api_access?: boolean
  priority_queue?: boolean
}

interface Plan {
  id: string
  name: string
  slug: string
  plan_type: string
  price: number
  currency: string
  billing_period: string
  token_limit: number | null
  project_limit: number | null
  feature_flags: FeatureFlags
  allowed_models: string[]
  subscribers_count: number
  is_active: boolean
}

const FEATURE_LABELS: Record<string, { label: string; icon: React.ReactNode; description: string }> = {
  agentic_mode: {
    label: 'Agentic Mode',
    icon: <Zap className="w-4 h-4" />,
    description: 'AI agent that can read/write files, run commands'
  },
  document_generation: {
    label: 'Document Generation',
    icon: <FileText className="w-4 h-4" />,
    description: 'Generate SRS, reports, presentations'
  },
  code_execution: {
    label: 'Code Execution',
    icon: <Code className="w-4 h-4" />,
    description: 'Run code in secure sandbox containers'
  },
  api_access: {
    label: 'API Access',
    icon: <Key className="w-4 h-4" />,
    description: 'Create API keys for programmatic access'
  },
  priority_queue: {
    label: 'Priority Queue',
    icon: <Sparkles className="w-4 h-4" />,
    description: 'Skip queue for faster responses'
  },
}

export default function AdminPlansPage() {
  const { theme } = useAdminTheme()
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [editingPlan, setEditingPlan] = useState<string | null>(null)
  const [editedFlags, setEditedFlags] = useState<FeatureFlags>({})
  const [saving, setSaving] = useState(false)
  const [seeding, setSeeding] = useState(false)

  const isDark = theme === 'dark'

  const fetchPlans = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiClient.get<any>('/admin/plans')
      setPlans(data.items || [])
    } catch (err) {
      console.error('Failed to fetch plans:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  const handleSeedPlans = async () => {
    setSeeding(true)
    try {
      const result = await apiClient.post<any>('/admin/plans/seed', {})
      if (result.created && result.created.length > 0) {
        alert(`Plans created: ${result.created.join(', ')}`)
      } else {
        alert('All default plans already exist')
      }
      fetchPlans()
    } catch (err) {
      console.error('Failed to seed plans:', err)
      alert('Failed to seed plans')
    } finally {
      setSeeding(false)
    }
  }

  const startEditing = (plan: Plan) => {
    setEditingPlan(plan.id)
    setEditedFlags(plan.feature_flags || {})
  }

  const cancelEditing = () => {
    setEditingPlan(null)
    setEditedFlags({})
  }

  const toggleFlag = (flag: string) => {
    setEditedFlags(prev => ({
      ...prev,
      [flag]: !prev[flag as keyof FeatureFlags]
    }))
  }

  const savePlan = async (planId: string) => {
    setSaving(true)
    try {
      await apiClient.patch(`/admin/plans/${planId}`, {
        feature_flags: editedFlags
      })
      setEditingPlan(null)
      setEditedFlags({})
      fetchPlans()
    } catch (err) {
      console.error('Failed to update plan:', err)
      alert('Failed to update plan')
    } finally {
      setSaving(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount / 100)
  }

  const getPlanColor = (planType: string) => {
    const colors: Record<string, string> = {
      free: 'from-gray-500 to-gray-600',
      student: 'from-blue-500 to-blue-600',
      basic: 'from-green-500 to-green-600',
      pro: 'from-purple-500 to-purple-600',
      enterprise: 'from-orange-500 to-orange-600',
    }
    return colors[planType] || colors.free
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Plan Management"
        subtitle="Manage subscription plans and feature access"
        onRefresh={fetchPlans}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Seed Plans Button */}
        <div className="mb-6 flex justify-end">
          <button
            onClick={handleSeedPlans}
            disabled={seeding}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              isDark
                ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-blue-800'
                : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-blue-300'
            }`}
          >
            <Database className="w-4 h-4" />
            {seeding ? 'Seeding...' : 'Seed Default Plans'}
          </button>
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {loading ? (
            [...Array(4)].map((_, i) => (
              <div
                key={i}
                className={`p-6 rounded-xl animate-pulse ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}
              >
                <div className={`h-6 w-24 rounded mb-4 ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                <div className={`h-8 w-20 rounded mb-2 ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                <div className={`h-4 w-32 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
              </div>
            ))
          ) : plans.length === 0 ? (
            <div className={`col-span-full text-center py-12 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              <p>No plans found. Click "Seed Default Plans" to create default plans.</p>
            </div>
          ) : (
            plans.map((plan) => {
              const isEditing = editingPlan === plan.id
              const flags = isEditing ? editedFlags : plan.feature_flags || {}

              return (
                <div
                  key={plan.id}
                  className={`rounded-xl border overflow-hidden ${
                    isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
                  }`}
                >
                  {/* Header */}
                  <div className={`p-4 bg-gradient-to-r ${getPlanColor(plan.plan_type)}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="w-5 h-5 text-white" />
                        <span className="text-white font-semibold">{plan.name}</span>
                      </div>
                      {!plan.is_active && (
                        <span className="px-2 py-0.5 bg-black/20 rounded text-xs text-white">
                          Inactive
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4">
                    {/* Price */}
                    <div className="mb-4">
                      <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {plan.price === 0 ? 'Free' : formatCurrency(plan.price)}
                      </div>
                      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {plan.billing_period === 'one_time' ? 'One-time' : `per ${plan.billing_period}`}
                      </div>
                    </div>

                    {/* Subscribers */}
                    <div className={`flex items-center gap-2 mb-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                      <Users className="w-4 h-4" />
                      <span className="text-sm">{plan.subscribers_count} subscribers</span>
                    </div>

                    {/* Limits */}
                    <div className="space-y-1 mb-4">
                      <div className="flex items-center justify-between text-sm">
                        <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Tokens</span>
                        <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>
                          {plan.token_limit ? plan.token_limit.toLocaleString() : 'Unlimited'}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Projects</span>
                        <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>
                          {plan.project_limit || 'Unlimited'}
                        </span>
                      </div>
                    </div>

                    {/* Feature Flags */}
                    <div className={`border-t pt-4 ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                      <div className={`text-xs font-medium uppercase mb-3 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        Features
                      </div>
                      <div className="space-y-2">
                        {Object.entries(FEATURE_LABELS).map(([key, { label, icon }]) => {
                          const enabled = flags[key as keyof FeatureFlags] || false
                          return (
                            <div
                              key={key}
                              className={`flex items-center justify-between ${
                                isEditing ? 'cursor-pointer' : ''
                              }`}
                              onClick={() => isEditing && toggleFlag(key)}
                            >
                              <div className="flex items-center gap-2">
                                <span className={enabled
                                  ? (isDark ? 'text-green-400' : 'text-green-600')
                                  : (isDark ? 'text-gray-600' : 'text-gray-400')
                                }>
                                  {icon}
                                </span>
                                <span className={`text-sm ${
                                  enabled
                                    ? (isDark ? 'text-gray-200' : 'text-gray-800')
                                    : (isDark ? 'text-gray-500' : 'text-gray-400')
                                }`}>
                                  {label}
                                </span>
                              </div>
                              <div className={`w-8 h-5 rounded-full transition-colors flex items-center ${
                                enabled
                                  ? 'bg-green-500 justify-end'
                                  : (isDark ? 'bg-[#333]' : 'bg-gray-200') + ' justify-start'
                              }`}>
                                <div className={`w-4 h-4 rounded-full mx-0.5 transition-colors ${
                                  enabled ? 'bg-white' : (isDark ? 'bg-gray-600' : 'bg-gray-400')
                                }`} />
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Models */}
                    {plan.allowed_models && plan.allowed_models.length > 0 && (
                      <div className={`border-t pt-3 mt-3 ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                        <div className={`text-xs font-medium uppercase mb-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          Models
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {plan.allowed_models.map(model => (
                            <span
                              key={model}
                              className={`px-2 py-0.5 rounded text-xs ${
                                isDark ? 'bg-[#252525] text-gray-300' : 'bg-gray-100 text-gray-600'
                              }`}
                            >
                              {model}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className={`flex gap-2 mt-4 pt-4 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => savePlan(plan.id)}
                            disabled={saving}
                            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm ${
                              isDark
                                ? 'bg-green-600 text-white hover:bg-green-700 disabled:bg-green-800'
                                : 'bg-green-500 text-white hover:bg-green-600 disabled:bg-green-300'
                            }`}
                          >
                            <Save className="w-4 h-4" />
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={cancelEditing}
                            className={`flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm ${
                              isDark
                                ? 'bg-[#252525] text-white hover:bg-[#333]'
                                : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                            }`}
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => startEditing(plan)}
                          className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm ${
                            isDark
                              ? 'bg-[#252525] text-white hover:bg-[#333]'
                              : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                          }`}
                        >
                          <Edit className="w-4 h-4" />
                          Edit Features
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
