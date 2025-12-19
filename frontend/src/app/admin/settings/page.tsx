'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { apiClient } from '@/lib/api-client'
import { Settings, ToggleLeft, ToggleRight, Save, Check } from 'lucide-react'

export default function AdminSettingsPage() {
  const { theme } = useAdminTheme()
  const [settings, setSettings] = useState<any>({})
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const isDark = theme === 'dark'

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    try {
      const [settingsData, flagsData] = await Promise.all([
        apiClient.get<any>('/admin/settings'),
        apiClient.get<any>('/admin/settings/feature-flags'),
      ])
      setSettings(settingsData.settings || {})
      setFeatureFlags(flagsData.flags || {})
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const handleToggleFlag = (flag: string) => {
    setFeatureFlags((prev) => ({
      ...prev,
      [flag]: !prev[flag],
    }))
    setSaved(false)
  }

  const handleSaveFlags = async () => {
    setSaving(true)
    try {
      await apiClient.patch('/admin/settings/feature-flags', { flags: featureFlags })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Failed to save flags:', err)
    } finally {
      setSaving(false)
    }
  }

  const ToggleSwitch = ({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) => (
    <button onClick={onToggle} className="relative">
      {enabled ? (
        <ToggleRight className="w-10 h-6 text-green-500" />
      ) : (
        <ToggleLeft className={`w-10 h-6 ${isDark ? 'text-gray-600' : 'text-gray-400'}`} />
      )}
    </button>
  )

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="System Settings"
        subtitle="Configure platform settings and features"
        onRefresh={fetchSettings}
        isLoading={loading}
      />

      <div className="p-6 max-w-4xl">
        {/* Feature Flags */}
        <div className={`rounded-xl border mb-6 ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
          <div className={`px-6 py-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  Feature Flags
                </h2>
              </div>
              <button
                onClick={handleSaveFlags}
                disabled={saving || saved}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
                  saved
                    ? 'bg-green-500 text-white'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                } ${saving ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {saved ? (
                  <>
                    <Check className="w-4 h-4" />
                    Saved
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="p-6 space-y-4">
            {loading ? (
              [...Array(4)].map((_, i) => (
                <div key={i} className="flex items-center justify-between py-3 animate-pulse">
                  <div className="space-y-2">
                    <div className={`h-4 w-32 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                    <div className={`h-3 w-48 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                  </div>
                  <div className={`w-10 h-6 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                </div>
              ))
            ) : (
              Object.entries(featureFlags).map(([flag, enabled]) => (
                <div
                  key={flag}
                  className={`flex items-center justify-between py-3 border-b last:border-0 ${
                    isDark ? 'border-[#333]' : 'border-gray-100'
                  }`}
                >
                  <div>
                    <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {flag.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                    </div>
                    <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      {getFeatureDescription(flag)}
                    </div>
                  </div>
                  <ToggleSwitch enabled={enabled} onToggle={() => handleToggleFlag(flag)} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Settings by Category */}
        {Object.entries(settings).map(([category, items]: [string, any]) => (
          <div
            key={category}
            className={`rounded-xl border mb-6 ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}
          >
            <div className={`px-6 py-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
              <h2 className={`text-lg font-semibold capitalize ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {category}
              </h2>
            </div>

            <div className="p-6 space-y-4">
              {Array.isArray(items) && items.map((item: any) => (
                <div
                  key={item.key}
                  className={`flex items-center justify-between py-3 border-b last:border-0 ${
                    isDark ? 'border-[#333]' : 'border-gray-100'
                  }`}
                >
                  <div>
                    <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {item.key.split('.').pop()?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </div>
                    {item.description && (
                      <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {item.description}
                      </div>
                    )}
                  </div>
                  <div className={`font-mono text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    {typeof item.value === 'boolean'
                      ? (item.value ? 'Enabled' : 'Disabled')
                      : String(item.value)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function getFeatureDescription(flag: string): string {
  const descriptions: Record<string, string> = {
    agentic_mode: 'Enable AI agentic mode for automated project generation',
    document_generation: 'Allow users to generate documentation (SRS, UML, etc.)',
    code_execution: 'Enable code execution in sandboxed environments',
    api_access: 'Allow users to create and use API keys',
  }
  return descriptions[flag] || `Toggle ${flag.replace(/_/g, ' ')} feature`
}
