'use client'

import React from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: {
    value: number
    label: string
    isPositive?: boolean
  }
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red' | 'cyan'
  loading?: boolean
}

const colorClasses = {
  blue: {
    bg: 'bg-blue-500/10',
    icon: 'text-blue-400',
    trend: 'text-blue-400',
  },
  green: {
    bg: 'bg-green-500/10',
    icon: 'text-green-400',
    trend: 'text-green-400',
  },
  purple: {
    bg: 'bg-purple-500/10',
    icon: 'text-purple-400',
    trend: 'text-purple-400',
  },
  orange: {
    bg: 'bg-orange-500/10',
    icon: 'text-orange-400',
    trend: 'text-orange-400',
  },
  red: {
    bg: 'bg-red-500/10',
    icon: 'text-red-400',
    trend: 'text-red-400',
  },
  cyan: {
    bg: 'bg-cyan-500/10',
    icon: 'text-cyan-400',
    trend: 'text-cyan-400',
  },
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'blue',
  loading = false,
}: StatCardProps) {
  const { theme } = useAdminTheme()
  const isDark = theme === 'dark'
  const colors = colorClasses[color]

  if (loading) {
    return (
      <div
        className={`p-6 rounded-xl border ${
          isDark
            ? 'bg-[#1a1a1a] border-[#333]'
            : 'bg-white border-gray-200'
        }`}
      >
        <div className="animate-pulse">
          <div className="flex items-center justify-between mb-4">
            <div className={`h-4 w-24 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
            <div className={`h-10 w-10 rounded-lg ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
          </div>
          <div className={`h-8 w-20 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
          <div className={`h-4 w-32 rounded mt-2 ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
        </div>
      </div>
    )
  }

  return (
    <div
      className={`p-6 rounded-xl border transition-all hover:shadow-lg ${
        isDark
          ? 'bg-[#1a1a1a] border-[#333] hover:border-[#444]'
          : 'bg-white border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <span className={`text-sm font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          {title}
        </span>
        <div className={`p-2.5 rounded-lg ${colors.bg}`}>
          <Icon className={`w-5 h-5 ${colors.icon}`} />
        </div>
      </div>

      <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>

      <div className="mt-2 flex items-center gap-2">
        {trend && (
          <div className={`flex items-center gap-1 text-sm ${
            trend.isPositive !== false ? 'text-green-400' : 'text-red-400'
          }`}>
            {trend.isPositive !== false ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            <span>{trend.value > 0 ? '+' : ''}{trend.value}%</span>
          </div>
        )}
        {subtitle && (
          <span className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            {subtitle}
          </span>
        )}
      </div>
    </div>
  )
}
