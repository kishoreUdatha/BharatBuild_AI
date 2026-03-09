'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { apiClient } from '@/lib/api-client'
import { Settings, ToggleLeft, ToggleRight, Save, Check, Bell, Mail, MessageCircle, Send, AlertCircle } from 'lucide-react'

interface NotificationConfig {
  email: { enabled: boolean; admin_email: string }
  whatsapp: {
    enabled: boolean
    admin_number: string
    provider: string
    exotel: { sid: string; token: string; whatsapp_number: string }
    twilio: { sid: string; token: string; whatsapp_number: string }
  }
  webhooks: { slack: string; discord: string }
}

export default function AdminSettingsPage() {
  const { theme } = useAdminTheme()
  const [settings, setSettings] = useState<any>({})
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>({})
  const [notifConfig, setNotifConfig] = useState<NotificationConfig>({
    email: { enabled: false, admin_email: '' },
    whatsapp: {
      enabled: false,
      admin_number: '',
      provider: 'exotel',
      exotel: { sid: '', token: '', whatsapp_number: '' },
      twilio: { sid: '', token: '', whatsapp_number: '' }
    },
    webhooks: { slack: '', discord: '' }
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [savingNotif, setSavingNotif] = useState(false)
  const [savedNotif, setSavedNotif] = useState(false)
  const [testingChannel, setTestingChannel] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'features' | 'notifications'>('features')

  const isDark = theme === 'dark'

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    try {
      const [settingsData, flagsData, notifData] = await Promise.all([
        apiClient.get<any>('/admin/settings'),
        apiClient.get<any>('/admin/settings/feature-flags'),
        apiClient.get<any>('/admin/settings/notifications/config'),
      ])
      setSettings(settingsData.settings || {})
      setFeatureFlags(flagsData.flags || {})
      if (notifData.notifications) {
        setNotifConfig(notifData.notifications)
      }
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

  const handleSaveNotifications = async () => {
    setSavingNotif(true)
    setTestResult(null)
    try {
      const result = await apiClient.patch<any>('/admin/settings/notifications/config', notifConfig)
      setSavedNotif(true)
      setTestResult({ success: true, message: `Settings saved! ${result.changes_count || 0} changes applied.` })
      setTimeout(() => setSavedNotif(false), 3000)
      // Refresh settings from server
      const notifData = await apiClient.get<any>('/admin/settings/notifications/config')
      if (notifData.notifications) {
        setNotifConfig(notifData.notifications)
      }
    } catch (err: any) {
      console.error('Failed to save notification settings:', err)
      setTestResult({ success: false, message: err.message || 'Failed to save settings' })
    } finally {
      setSavingNotif(false)
    }
  }

  const handleTestNotification = async (channel: string) => {
    setTestingChannel(channel)
    setTestResult(null)
    try {
      const result = await apiClient.post<any>(`/admin/settings/notifications/test?channel=${channel}`)
      setTestResult({ success: true, message: result.message })
    } catch (err: any) {
      setTestResult({ success: false, message: err.message || 'Test failed' })
    } finally {
      setTestingChannel(null)
    }
  }

  const updateNotifConfig = (path: string, value: any) => {
    setNotifConfig(prev => {
      const newConfig = { ...prev }
      const keys = path.split('.')
      let obj: any = newConfig
      for (let i = 0; i < keys.length - 1; i++) {
        obj = obj[keys[i]]
      }
      obj[keys[keys.length - 1]] = value
      return newConfig
    })
    setSavedNotif(false)
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
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('features')}
            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${
              activeTab === 'features'
                ? 'bg-blue-500 text-white'
                : isDark ? 'bg-[#2a2a2a] text-gray-300 hover:bg-[#333]' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Settings className="w-4 h-4" />
            Features
          </button>
          <button
            onClick={() => setActiveTab('notifications')}
            className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 ${
              activeTab === 'notifications'
                ? 'bg-blue-500 text-white'
                : isDark ? 'bg-[#2a2a2a] text-gray-300 hover:bg-[#333]' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            <Bell className="w-4 h-4" />
            Notifications
          </button>
        </div>

        {/* Notification Settings Tab */}
        {activeTab === 'notifications' && (
          <div className="space-y-6">
            {/* Test Result */}
            {testResult && (
              <div className={`p-4 rounded-lg flex items-center gap-3 ${
                testResult.success ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
              }`}>
                <AlertCircle className="w-5 h-5" />
                {testResult.message}
              </div>
            )}

            {/* Email Notifications */}
            <div className={`rounded-xl border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
              <div className={`px-6 py-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <Mail className={`w-5 h-5 ${isDark ? 'text-blue-400' : 'text-blue-500'}`} />
                  <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Email Notifications
                  </h2>
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>Enable Email Alerts</div>
                    <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Receive email when new users register
                    </div>
                  </div>
                  <ToggleSwitch
                    enabled={notifConfig.email.enabled}
                    onToggle={() => updateNotifConfig('email.enabled', !notifConfig.email.enabled)}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Admin Email Address
                  </label>
                  <input
                    type="email"
                    value={notifConfig.email.admin_email}
                    onChange={(e) => updateNotifConfig('email.admin_email', e.target.value)}
                    placeholder="admin@company.com"
                    className={`w-full px-4 py-2 rounded-lg border ${
                      isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                    }`}
                  />
                </div>
                <button
                  onClick={() => handleTestNotification('email')}
                  disabled={testingChannel === 'email' || !notifConfig.email.admin_email}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  {testingChannel === 'email' ? 'Sending...' : 'Send Test Email'}
                </button>
              </div>
            </div>

            {/* WhatsApp Notifications */}
            <div className={`rounded-xl border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
              <div className={`px-6 py-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <MessageCircle className={`w-5 h-5 ${isDark ? 'text-green-400' : 'text-green-500'}`} />
                  <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    WhatsApp Notifications
                  </h2>
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>Enable WhatsApp Alerts</div>
                    <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Receive WhatsApp message when new users register
                    </div>
                  </div>
                  <ToggleSwitch
                    enabled={notifConfig.whatsapp.enabled}
                    onToggle={() => updateNotifConfig('whatsapp.enabled', !notifConfig.whatsapp.enabled)}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Admin WhatsApp Number (with country code)
                  </label>
                  <input
                    type="text"
                    value={notifConfig.whatsapp.admin_number}
                    onChange={(e) => updateNotifConfig('whatsapp.admin_number', e.target.value)}
                    placeholder="+919876543210"
                    className={`w-full px-4 py-2 rounded-lg border ${
                      isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                    }`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    WhatsApp Provider
                  </label>
                  <select
                    value={notifConfig.whatsapp.provider}
                    onChange={(e) => updateNotifConfig('whatsapp.provider', e.target.value)}
                    className={`w-full px-4 py-2 rounded-lg border ${
                      isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                    }`}
                  >
                    <option value="exotel">Exotel (Recommended for India)</option>
                    <option value="twilio">Twilio</option>
                  </select>
                </div>

                {notifConfig.whatsapp.provider === 'exotel' && (
                  <div className="space-y-3 p-4 rounded-lg bg-green-500/5 border border-green-500/20">
                    <h4 className={`font-medium ${isDark ? 'text-green-400' : 'text-green-600'}`}>Exotel Configuration</h4>
                    <input
                      type="text"
                      value={notifConfig.whatsapp.exotel.sid}
                      onChange={(e) => updateNotifConfig('whatsapp.exotel.sid', e.target.value)}
                      placeholder="Exotel Account SID"
                      className={`w-full px-4 py-2 rounded-lg border ${
                        isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    />
                    <input
                      type="password"
                      value={notifConfig.whatsapp.exotel.token}
                      onChange={(e) => updateNotifConfig('whatsapp.exotel.token', e.target.value)}
                      placeholder="Exotel Auth Token"
                      className={`w-full px-4 py-2 rounded-lg border ${
                        isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    />
                    <input
                      type="text"
                      value={notifConfig.whatsapp.exotel.whatsapp_number}
                      onChange={(e) => updateNotifConfig('whatsapp.exotel.whatsapp_number', e.target.value)}
                      placeholder="Exotel WhatsApp Business Number"
                      className={`w-full px-4 py-2 rounded-lg border ${
                        isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    />
                  </div>
                )}

                {notifConfig.whatsapp.provider === 'twilio' && (
                  <div className="space-y-3 p-4 rounded-lg bg-purple-500/5 border border-purple-500/20">
                    <h4 className={`font-medium ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>Twilio Configuration</h4>
                    <input
                      type="text"
                      value={notifConfig.whatsapp.twilio.sid}
                      onChange={(e) => updateNotifConfig('whatsapp.twilio.sid', e.target.value)}
                      placeholder="Twilio Account SID"
                      className={`w-full px-4 py-2 rounded-lg border ${
                        isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    />
                    <input
                      type="password"
                      value={notifConfig.whatsapp.twilio.token}
                      onChange={(e) => updateNotifConfig('whatsapp.twilio.token', e.target.value)}
                      placeholder="Twilio Auth Token"
                      className={`w-full px-4 py-2 rounded-lg border ${
                        isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    />
                    <input
                      type="text"
                      value={notifConfig.whatsapp.twilio.whatsapp_number}
                      onChange={(e) => updateNotifConfig('whatsapp.twilio.whatsapp_number', e.target.value)}
                      placeholder="Twilio WhatsApp Number (e.g., +14155238886)"
                      className={`w-full px-4 py-2 rounded-lg border ${
                        isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                      }`}
                    />
                  </div>
                )}

                <button
                  onClick={() => handleTestNotification('whatsapp')}
                  disabled={testingChannel === 'whatsapp' || !notifConfig.whatsapp.admin_number}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  {testingChannel === 'whatsapp' ? 'Sending...' : 'Send Test WhatsApp'}
                </button>
              </div>
            </div>

            {/* Webhook Notifications */}
            <div className={`rounded-xl border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
              <div className={`px-6 py-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <Bell className={`w-5 h-5 ${isDark ? 'text-purple-400' : 'text-purple-500'}`} />
                  <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Webhook Notifications (Slack/Discord)
                  </h2>
                </div>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Slack Webhook URL
                  </label>
                  <input
                    type="url"
                    value={notifConfig.webhooks.slack}
                    onChange={(e) => updateNotifConfig('webhooks.slack', e.target.value)}
                    placeholder="https://hooks.slack.com/services/..."
                    className={`w-full px-4 py-2 rounded-lg border ${
                      isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                    }`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Discord Webhook URL
                  </label>
                  <input
                    type="url"
                    value={notifConfig.webhooks.discord}
                    onChange={(e) => updateNotifConfig('webhooks.discord', e.target.value)}
                    placeholder="https://discord.com/api/webhooks/..."
                    className={`w-full px-4 py-2 rounded-lg border ${
                      isDark ? 'bg-[#2a2a2a] border-[#444] text-white' : 'bg-white border-gray-300 text-gray-900'
                    }`}
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleTestNotification('slack')}
                    disabled={testingChannel === 'slack' || !notifConfig.webhooks.slack}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                    {testingChannel === 'slack' ? 'Sending...' : 'Test Slack'}
                  </button>
                  <button
                    onClick={() => handleTestNotification('discord')}
                    disabled={testingChannel === 'discord' || !notifConfig.webhooks.discord}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                    {testingChannel === 'discord' ? 'Sending...' : 'Test Discord'}
                  </button>
                </div>
              </div>
            </div>

            {/* Save Button */}
            <button
              onClick={handleSaveNotifications}
              disabled={savingNotif || savedNotif}
              className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-lg font-medium ${
                savedNotif
                  ? 'bg-green-500 text-white'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              } ${savingNotif ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {savedNotif ? (
                <>
                  <Check className="w-5 h-5" />
                  Settings Saved!
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  {savingNotif ? 'Saving...' : 'Save Notification Settings'}
                </>
              )}
            </button>
          </div>
        )}

        {/* Feature Flags Tab */}
        {activeTab === 'features' && (
        <>
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

        {/* Settings by Category (exclude notifications - shown in tab) */}
        {Object.entries(settings)
          .filter(([category]) => category !== 'notifications')
          .map(([category, items]: [string, any]) => (
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
        </>
        )}
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
