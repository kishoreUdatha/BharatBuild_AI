'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import {
  FileText, User, Clock, Download, Filter, ChevronDown, ChevronUp,
  Check, X, ArrowRight, Shield, Settings, CreditCard, Layers,
  UserPlus, UserMinus, UserCog, Key, ToggleLeft, Database,
  Trash2, Edit, Plus, Eye, RefreshCw, AlertTriangle, Globe
} from 'lucide-react'

// Action configuration with icons, colors, and descriptions
const ACTION_CONFIG: Record<string, {
  icon: React.ReactNode
  color: string
  bgColor: string
  label: string
  getDescription: (details: any) => string
}> = {
  // Plan actions
  plans_seeded: {
    icon: <Database className="w-4 h-4" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    label: 'Plans Seeded',
    getDescription: (d) => d?.created?.length ? `Created ${d.created.length} default plans` : 'Seeded default plans'
  },
  plan_created: {
    icon: <Plus className="w-4 h-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'Plan Created',
    getDescription: (d) => d?.name ? `Created "${d.name}" plan` : 'Created new plan'
  },
  plan_updated: {
    icon: <Edit className="w-4 h-4" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    label: 'Plan Updated',
    getDescription: (d) => d?.changes ? `Updated ${Object.keys(d.changes).length} field(s)` : 'Updated plan settings'
  },
  plan_deleted: {
    icon: <Trash2 className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'Plan Deleted',
    getDescription: (d) => d?.name ? `Deleted "${d.name}" plan` : 'Deleted plan'
  },

  // Feature flags
  feature_flags_updated: {
    icon: <ToggleLeft className="w-4 h-4" />,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    label: 'Features Updated',
    getDescription: (d) => d?.changes ? `Changed ${Object.keys(d.changes).length} feature(s)` : 'Updated feature flags'
  },

  // Settings
  setting_created: {
    icon: <Plus className="w-4 h-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'Setting Created',
    getDescription: (d) => d?.key ? `Created "${d.key}"` : 'Created new setting'
  },
  setting_updated: {
    icon: <Settings className="w-4 h-4" />,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
    label: 'Setting Changed',
    getDescription: (d) => d?.key ? `Updated "${d.key}"` : 'Updated system setting'
  },
  setting_deleted: {
    icon: <Trash2 className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'Setting Deleted',
    getDescription: (d) => d?.key ? `Deleted "${d.key}"` : 'Deleted setting'
  },

  // User actions
  user_created: {
    icon: <UserPlus className="w-4 h-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'User Created',
    getDescription: (d) => d?.email ? `Created user ${d.email}` : 'Created new user'
  },
  user_updated: {
    icon: <UserCog className="w-4 h-4" />,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    label: 'User Updated',
    getDescription: (d) => d?.email ? `Updated ${d.email}` : 'Updated user profile'
  },
  user_suspended: {
    icon: <UserMinus className="w-4 h-4" />,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
    label: 'User Suspended',
    getDescription: (d) => d?.email ? `Suspended ${d.email}` : 'Suspended user account'
  },
  user_activated: {
    icon: <Check className="w-4 h-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'User Activated',
    getDescription: (d) => d?.email ? `Activated ${d.email}` : 'Activated user account'
  },
  user_deleted: {
    icon: <Trash2 className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'User Deleted',
    getDescription: (d) => d?.email ? `Deleted ${d.email}` : 'Deleted user account'
  },
  user_role_changed: {
    icon: <Shield className="w-4 h-4" />,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    label: 'Role Changed',
    getDescription: (d) => d?.new_role ? `Changed role to ${d.new_role}` : 'Changed user role'
  },
  bulk_user_action: {
    icon: <User className="w-4 h-4" />,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/20',
    label: 'Bulk Action',
    getDescription: (d) => d?.count ? `Affected ${d.count} users` : 'Bulk user action'
  },

  // API Keys
  api_key_created: {
    icon: <Key className="w-4 h-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'API Key Created',
    getDescription: (d) => d?.name ? `Created key "${d.name}"` : 'Created new API key'
  },
  api_key_revoked: {
    icon: <X className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'API Key Revoked',
    getDescription: (d) => d?.name ? `Revoked key "${d.name}"` : 'Revoked API key'
  },

  // Billing
  subscription_created: {
    icon: <CreditCard className="w-4 h-4" />,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'Subscription Created',
    getDescription: (d) => d?.plan ? `Subscribed to ${d.plan}` : 'New subscription'
  },
  subscription_cancelled: {
    icon: <X className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'Subscription Cancelled',
    getDescription: (d) => d?.plan ? `Cancelled ${d.plan}` : 'Cancelled subscription'
  },
  refund_processed: {
    icon: <RefreshCw className="w-4 h-4" />,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
    label: 'Refund Processed',
    getDescription: (d) => d?.amount ? `Refunded ₹${d.amount / 100}` : 'Processed refund'
  },

  // Projects
  project_deleted: {
    icon: <Trash2 className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'Project Deleted',
    getDescription: (d) => d?.title ? `Deleted "${d.title}"` : 'Deleted project'
  },

  // Security
  login_as_user: {
    icon: <Eye className="w-4 h-4" />,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
    label: 'Impersonation',
    getDescription: (d) => d?.email ? `Logged in as ${d.email}` : 'Admin impersonation'
  },
  security_alert: {
    icon: <AlertTriangle className="w-4 h-4" />,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'Security Alert',
    getDescription: (d) => d?.message || 'Security event detected'
  },
}

// Default config for unknown actions
const DEFAULT_ACTION_CONFIG = {
  icon: <FileText className="w-4 h-4" />,
  color: 'text-gray-400',
  bgColor: 'bg-gray-500/20',
  label: 'Action',
  getDescription: () => 'Action performed'
}

// Get config for an action
function getActionConfig(action: string) {
  return ACTION_CONFIG[action] || {
    ...DEFAULT_ACTION_CONFIG,
    label: action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }
}

// Format details based on action type
function formatDetails(action: string, details: any): React.ReactNode {
  if (!details) return null

  // Plans seeded
  if (action === 'plans_seeded') {
    return (
      <div className="space-y-2">
        {details.created?.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {details.created.map((plan: string) => (
              <span key={plan} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-500/20 text-green-400 text-xs">
                <Check className="w-3 h-3" />
                {plan}
              </span>
            ))}
          </div>
        )}
        {details.skipped?.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {details.skipped.map((plan: string) => (
              <span key={plan} className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-500/20 text-gray-400 text-xs">
                Skipped: {plan}
              </span>
            ))}
          </div>
        )}
      </div>
    )
  }

  // Plan created
  if (action === 'plan_created') {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-gray-500" />
          <span className="font-medium text-white">{details.name}</span>
          <span className="text-gray-500">({details.slug})</span>
        </div>
        {details.price !== undefined && (
          <span className="px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 text-xs font-medium">
            ₹{(details.price / 100).toFixed(0)}/mo
          </span>
        )}
      </div>
    )
  }

  // Plan/setting updated with changes
  if ((action === 'plan_updated' || action.includes('_updated')) && details.changes) {
    return (
      <div className="space-y-2">
        {Object.entries(details.changes).map(([field, change]: [string, any]) => (
          <div key={field} className="flex items-center gap-3 text-sm">
            <span className="text-gray-500 min-w-[100px]">{field.replace(/_/g, ' ')}:</span>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-400 line-through">
                {formatValue(change.old)}
              </span>
              <ArrowRight className="w-3 h-3 text-gray-600" />
              <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400">
                {formatValue(change.new)}
              </span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Feature flags updated
  if (action === 'feature_flags_updated' && details.changes) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {Object.entries(details.changes).map(([feature, change]: [string, any]) => (
          <div key={feature} className="flex items-center justify-between p-2 rounded-lg bg-[#1a1a1a]">
            <span className="text-gray-300 text-sm">{feature.replace(/_/g, ' ')}</span>
            <div className="flex items-center gap-2">
              <span className={`w-8 h-5 rounded-full flex items-center ${
                change.old ? 'bg-green-500/30 justify-end' : 'bg-gray-700 justify-start'
              }`}>
                <span className={`w-4 h-4 rounded-full mx-0.5 ${change.old ? 'bg-green-400' : 'bg-gray-500'}`} />
              </span>
              <ArrowRight className="w-3 h-3 text-gray-600" />
              <span className={`w-8 h-5 rounded-full flex items-center ${
                change.new ? 'bg-green-500/30 justify-end' : 'bg-gray-700 justify-start'
              }`}>
                <span className={`w-4 h-4 rounded-full mx-0.5 ${change.new ? 'bg-green-400' : 'bg-gray-500'}`} />
              </span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Setting updated
  if (action === 'setting_updated') {
    return (
      <div className="flex items-center gap-3 text-sm">
        <span className="px-2 py-1 rounded bg-[#1a1a1a] text-gray-400 font-mono text-xs">{details.key}</span>
        <div className="flex items-center gap-2">
          <span className="text-red-400 line-through">{formatValue(details.old_value)}</span>
          <ArrowRight className="w-3 h-3 text-gray-600" />
          <span className="text-green-400">{formatValue(details.new_value)}</span>
        </div>
      </div>
    )
  }

  // User-related with email
  if (details.email) {
    return (
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white text-xs font-bold">
          {details.email.charAt(0).toUpperCase()}
        </div>
        <span className="text-gray-300">{details.email}</span>
        {details.role && (
          <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 text-xs">
            {details.role}
          </span>
        )}
      </div>
    )
  }

  // Simple name field
  if (details.name && Object.keys(details).length === 1) {
    return <span className="text-gray-300 font-medium">{details.name}</span>
  }

  // Default: show as compact key-value pairs
  const entries = Object.entries(details).filter(([_, v]) => v !== null && v !== undefined)
  if (entries.length > 0 && entries.length <= 4) {
    return (
      <div className="flex flex-wrap gap-3">
        {entries.map(([key, value]) => (
          <div key={key} className="text-sm">
            <span className="text-gray-500">{key.replace(/_/g, ' ')}: </span>
            <span className="text-gray-300">{formatValue(value)}</span>
          </div>
        ))}
      </div>
    )
  }

  return null
}

// Format a value for display
function formatValue(value: any): string {
  if (value === null || value === undefined) return 'none'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// Expandable details component
function ExpandableDetails({ action, details, isDark }: { action: string; details: any; isDark: boolean }) {
  const [expanded, setExpanded] = useState(false)

  const formattedContent = formatDetails(action, details)
  if (formattedContent) {
    return (
      <div className={`mt-3 p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
        {formattedContent}
      </div>
    )
  }

  // Fallback to expandable JSON for complex data
  const jsonString = JSON.stringify(details, null, 2)
  const isLong = jsonString.length > 150

  return (
    <div className={`mt-3 rounded-lg overflow-hidden ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
      {isLong ? (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className={`w-full flex items-center justify-between p-3 text-sm ${
              isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <span className="flex items-center gap-2">
              <Eye className="w-4 h-4" />
              {expanded ? 'Hide raw data' : 'View raw data'}
            </span>
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {expanded && (
            <pre className={`p-3 pt-0 text-xs font-mono overflow-x-auto ${
              isDark ? 'text-gray-400' : 'text-gray-600'
            }`}>
              {jsonString}
            </pre>
          )}
        </>
      ) : (
        <pre className={`p-3 text-xs font-mono overflow-x-auto ${
          isDark ? 'text-gray-400' : 'text-gray-600'
        }`}>
          {jsonString}
        </pre>
      )}
    </div>
  )
}

// Group logs by date
function groupLogsByDate(logs: any[]): Record<string, any[]> {
  const groups: Record<string, any[]> = {}

  logs.forEach(log => {
    const date = new Date(log.created_at).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
    if (!groups[date]) groups[date] = []
    groups[date].push(log)
  })

  return groups
}

export default function AdminAuditLogsPage() {
  const { theme } = useAdminTheme()
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [actionFilter, setActionFilter] = useState('')
  const [targetTypeFilter, setTargetTypeFilter] = useState('')
  const [actions, setActions] = useState<string[]>([])
  const [targetTypes, setTargetTypes] = useState<string[]>([])
  const [viewMode, setViewMode] = useState<'timeline' | 'table'>('timeline')

  const isDark = theme === 'dark'

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      })
      if (actionFilter) params.append('action', actionFilter)
      if (targetTypeFilter) params.append('target_type', targetTypeFilter)

      const data = await apiClient.get<any>(`/admin/audit-logs?${params.toString()}`)
      setLogs(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, actionFilter, targetTypeFilter])

  const fetchFilters = useCallback(async () => {
    try {
      const [actionsData, typesData] = await Promise.all([
        apiClient.get<any>('/admin/audit-logs/actions'),
        apiClient.get<any>('/admin/audit-logs/target-types'),
      ])
      setActions(actionsData.actions || [])
      setTargetTypes(typesData.target_types || [])
    } catch (err) {
      console.error('Failed to fetch filters:', err)
    }
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    fetchFilters()
  }, [fetchFilters])

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const params = new URLSearchParams()
      if (actionFilter) params.append('action', actionFilter)
      if (targetTypeFilter) params.append('target_type', targetTypeFilter)

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/admin/audit-logs/export?${params.toString()}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatRelativeTime = (dateString: string) => {
    const now = new Date()
    const date = new Date(dateString)
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const groupedLogs = groupLogsByDate(logs)

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Audit Logs"
        subtitle="Track all admin actions and system changes"
        onRefresh={fetchLogs}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats Bar */}
        <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 mb-6`}>
          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{total}</div>
            <div className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Total Events</div>
          </div>
          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className={`text-2xl font-bold text-green-400`}>
              {logs.filter(l => l.action.includes('created')).length}
            </div>
            <div className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Created</div>
          </div>
          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className={`text-2xl font-bold text-blue-400`}>
              {logs.filter(l => l.action.includes('updated')).length}
            </div>
            <div className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Updated</div>
          </div>
          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className={`text-2xl font-bold text-red-400`}>
              {logs.filter(l => l.action.includes('deleted') || l.action.includes('revoked')).length}
            </div>
            <div className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Deleted</div>
          </div>
        </div>

        {/* Filters */}
        <div className={`flex flex-wrap items-center gap-4 mb-6 p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
          <div className="flex items-center gap-2">
            <Filter className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
            <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>Filters:</span>
          </div>

          <select
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            }`}
          >
            <option value="">All Actions</option>
            {actions.map((action) => (
              <option key={action} value={action}>
                {getActionConfig(action).label}
              </option>
            ))}
          </select>

          <select
            value={targetTypeFilter}
            onChange={(e) => { setTargetTypeFilter(e.target.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            }`}
          >
            <option value="">All Types</option>
            {targetTypes.map((type) => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>

          <div className="flex-1" />

          <button
            onClick={handleExport}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isDark
                ? 'bg-[#252525] text-white hover:bg-[#333]'
                : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
            }`}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>

        {/* Timeline View */}
        <div className={`rounded-xl border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
          {loading ? (
            <div className="p-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex gap-4 animate-pulse">
                  <div className={`w-10 h-10 rounded-xl ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                  <div className="flex-1 space-y-2">
                    <div className={`h-4 w-48 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                    <div className={`h-3 w-32 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                  </div>
                </div>
              ))}
            </div>
          ) : logs.length === 0 ? (
            <div className={`p-12 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium mb-2">No audit logs found</p>
              <p className="text-sm">Admin actions will appear here</p>
            </div>
          ) : (
            <div className="divide-y divide-[#333]">
              {Object.entries(groupedLogs).map(([date, dateLogs]) => (
                <div key={date}>
                  {/* Date Header */}
                  <div className={`px-6 py-3 sticky top-0 z-10 ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                    <span className={`text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      {date}
                    </span>
                  </div>

                  {/* Logs for this date */}
                  {dateLogs.map((log, index) => {
                    const config = getActionConfig(log.action)
                    return (
                      <div
                        key={log.id}
                        className={`px-6 py-4 ${isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'} transition-colors`}
                      >
                        <div className="flex gap-4">
                          {/* Icon */}
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${config.bgColor}`}>
                            <span className={config.color}>{config.icon}</span>
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className={`font-semibold ${config.color}`}>
                                    {config.label}
                                  </span>
                                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                                    isDark ? 'bg-[#333] text-gray-400' : 'bg-gray-100 text-gray-500'
                                  }`}>
                                    {log.target_type}
                                  </span>
                                  {log.target_id && (
                                    <span className={`text-xs font-mono ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
                                      #{log.target_id.slice(0, 8)}
                                    </span>
                                  )}
                                </div>
                                <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                                  {config.getDescription(log.details)}
                                </p>
                              </div>

                              <div className={`text-right flex-shrink-0`}>
                                <div className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                                  {formatTime(log.created_at)}
                                </div>
                                <div className={`text-xs ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>
                                  {formatRelativeTime(log.created_at)}
                                </div>
                              </div>
                            </div>

                            {/* Admin info */}
                            <div className={`flex items-center gap-2 mt-2 text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                              <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                                <span className="text-white text-[10px] font-bold">
                                  {(log.admin_name || log.admin_email || 'A').charAt(0).toUpperCase()}
                                </span>
                              </div>
                              <span>{log.admin_name || log.admin_email}</span>
                              {log.ip_address && (
                                <>
                                  <span className="text-gray-600">•</span>
                                  <Globe className="w-3 h-3" />
                                  <span className="font-mono text-xs">{log.ip_address}</span>
                                </>
                              )}
                            </div>

                            {/* Details */}
                            {log.details && Object.keys(log.details).length > 0 && (
                              <ExpandableDetails
                                action={log.action}
                                details={log.details}
                                isDark={isDark}
                              />
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={`px-6 py-4 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                pageSize={pageSize}
                totalItems={total}
                onPageChange={setPage}
                onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
