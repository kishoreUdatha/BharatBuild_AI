'use client'

import { LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'

interface StatsCardProps {
  title: string
  value: number
  icon: LucideIcon
  trend?: {
    value: number
    isPositive: boolean
  }
  suffix?: string
  color?: 'blue' | 'green' | 'purple' | 'orange'
}

const colorMap = {
  blue: {
    bg: 'from-blue-500/20 to-blue-600/10',
    icon: 'text-blue-400',
    border: 'border-blue-500/30'
  },
  green: {
    bg: 'from-green-500/20 to-green-600/10',
    icon: 'text-green-400',
    border: 'border-green-500/30'
  },
  purple: {
    bg: 'from-purple-500/20 to-purple-600/10',
    icon: 'text-purple-400',
    border: 'border-purple-500/30'
  },
  orange: {
    bg: 'from-orange-500/20 to-orange-600/10',
    icon: 'text-orange-400',
    border: 'border-orange-500/30'
  }
}

export function StatsCard({ title, value, icon: Icon, trend, suffix = '', color = 'blue' }: StatsCardProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const colors = colorMap[color]

  // Animated count-up effect
  useEffect(() => {
    const duration = 1000 // 1 second
    const steps = 30
    const increment = value / steps
    let current = 0

    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplayValue(value)
        clearInterval(timer)
      } else {
        setDisplayValue(Math.floor(current))
      }
    }, duration / steps)

    return () => clearInterval(timer)
  }, [value])

  return (
    <div className={`relative overflow-hidden rounded-xl border ${colors.border} bg-gradient-to-br ${colors.bg} p-6 backdrop-blur-sm`}>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-400">{title}</p>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">
              {displayValue.toLocaleString()}
            </span>
            {suffix && <span className="text-lg text-gray-400">{suffix}</span>}
          </div>
          {trend && (
            <div className={`flex items-center gap-1 text-sm ${trend.isPositive ? 'text-green-400' : 'text-red-400'}`}>
              <span>{trend.isPositive ? '+' : ''}{trend.value}%</span>
              <span className="text-gray-500">vs last month</span>
            </div>
          )}
        </div>
        <div className={`rounded-lg bg-black/20 p-3 ${colors.icon}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>

      {/* Decorative gradient */}
      <div className="absolute -bottom-4 -right-4 h-24 w-24 rounded-full bg-white/5 blur-2xl" />
    </div>
  )
}
