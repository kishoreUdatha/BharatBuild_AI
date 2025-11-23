'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api-client'
import { formatNumber, formatCurrency } from '@/lib/utils'
import { BarChart, PieChart, TrendingUp, DollarSign } from 'lucide-react'

interface TokenAnalytics {
  total_tokens_used: number
  total_tokens_added: number
  total_transactions: number
  agent_usage_breakdown: Record<string, number>
  model_usage_breakdown: Record<string, number>
  estimated_cost: {
    usd: number
    inr: number
  }
  average_tokens_per_request: number
}

const AGENT_COLORS: Record<string, string> = {
  idea: 'bg-blue-500',
  srs: 'bg-green-500',
  code: 'bg-purple-500',
  uml: 'bg-yellow-500',
  report: 'bg-red-500',
  ppt: 'bg-pink-500',
  viva: 'bg-indigo-500',
  prd: 'bg-orange-500',
}

export function TokenAnalytics() {
  const [analytics, setAnalytics] = useState<TokenAnalytics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAnalytics()
  }, [])

  const loadAnalytics = async () => {
    try {
      const data = await apiClient.getTokenAnalytics()
      setAnalytics(data)
    } catch (error) {
      console.error('Failed to load analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Token Analytics</CardTitle>
          <CardDescription>Loading analytics...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!analytics) return null

  const totalAgentTokens = Object.values(analytics.agent_usage_breakdown).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Used</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(analytics.total_tokens_used)}</div>
            <p className="text-xs text-muted-foreground">tokens consumed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Added</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(analytics.total_tokens_added)}</div>
            <p className="text-xs text-muted-foreground">tokens purchased</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transactions</CardTitle>
            <BarChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(analytics.total_transactions)}</div>
            <p className="text-xs text-muted-foreground">total operations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estimated Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(analytics.estimated_cost.inr)}</div>
            <p className="text-xs text-muted-foreground">${analytics.estimated_cost.usd.toFixed(2)} USD</p>
          </CardContent>
        </Card>
      </div>

      {/* Agent Usage Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Usage Breakdown</CardTitle>
          <CardDescription>Token consumption by AI agent type</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.entries(analytics.agent_usage_breakdown)
              .sort((a, b) => b[1] - a[1])
              .map(([agent, tokens]) => {
                const percentage = totalAgentTokens > 0 ? (tokens / totalAgentTokens) * 100 : 0
                const colorClass = AGENT_COLORS[agent] || 'bg-gray-500'

                return (
                  <div key={agent} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${colorClass}`} />
                        <span className="text-sm font-medium capitalize">{agent}Agent</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-muted-foreground">
                          {formatNumber(tokens)} tokens
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {percentage.toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${colorClass} transition-all`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
          </div>
        </CardContent>
      </Card>

      {/* Model Usage Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Model Usage</CardTitle>
            <CardDescription>Haiku vs Sonnet distribution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(analytics.model_usage_breakdown).map(([model, tokens]) => {
                const totalModelTokens = Object.values(analytics.model_usage_breakdown).reduce(
                  (a, b) => a + b,
                  0
                )
                const percentage = totalModelTokens > 0 ? (tokens / totalModelTokens) * 100 : 0

                return (
                  <div key={model} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium capitalize">{model}</span>
                      <span className="text-sm text-muted-foreground">
                        {formatNumber(tokens)} ({percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all ${
                          model === 'haiku' ? 'bg-blue-500' : 'bg-purple-500'
                        }`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Efficiency Metrics</CardTitle>
            <CardDescription>Usage patterns and averages</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm text-muted-foreground">Avg. Tokens/Request</span>
                <span className="text-lg font-semibold">
                  {formatNumber(Math.round(analytics.average_tokens_per_request))}
                </span>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm text-muted-foreground">Total Requests</span>
                <span className="text-lg font-semibold">
                  {formatNumber(analytics.total_transactions)}
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-muted-foreground">Cost per Token</span>
                <span className="text-lg font-semibold">
                  ₹{(analytics.estimated_cost.inr / analytics.total_tokens_used).toFixed(4)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
