'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api-client'
import { formatNumber, formatDate } from '@/lib/utils'
import { Coins, TrendingUp, Calendar, Activity } from 'lucide-react'

interface TokenBalance {
  total_tokens: number
  used_tokens: number
  remaining_tokens: number
  monthly_allowance: number
  monthly_used: number
  monthly_remaining: number
  monthly_used_percentage: number
  premium_tokens: number
  premium_remaining: number
  rollover_tokens: number
  month_reset_date: string
  total_requests: number
  requests_today: number
  last_request_at: string
}

export function TokenBalanceCard() {
  const [balance, setBalance] = useState<TokenBalance | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBalance()
  }, [])

  const loadBalance = async () => {
    try {
      const data = await apiClient.getTokenBalance()
      setBalance(data)
    } catch (error) {
      console.error('Failed to load token balance:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Token Balance</CardTitle>
          <CardDescription>Loading your token information...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!balance) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Token Balance</CardTitle>
          <CardDescription>Unable to load token balance</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Main Balance Card */}
      <Card className="col-span-2">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Balance</CardTitle>
          <Coins className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{formatNumber(balance.remaining_tokens)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {formatNumber(balance.used_tokens)} tokens used
          </p>
          <Progress
            value={(balance.remaining_tokens / balance.total_tokens) * 100}
            className="mt-3"
          />
          <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
            <span>{((balance.remaining_tokens / balance.total_tokens) * 100).toFixed(1)}% remaining</span>
            <span>{formatNumber(balance.total_tokens)} total</span>
          </div>
        </CardContent>
      </Card>

      {/* Monthly Allowance Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Monthly Allowance</CardTitle>
          <Calendar className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatNumber(balance.monthly_remaining)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            of {formatNumber(balance.monthly_allowance)} free tokens
          </p>
          <Progress
            value={100 - balance.monthly_used_percentage}
            className="mt-3"
          />
          <div className="flex items-center gap-2 mt-2">
            <Badge variant="secondary" className="text-xs">
              Resets: {balance.month_reset_date ? new Date(balance.month_reset_date).toLocaleDateString() : 'N/A'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Premium Tokens Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Premium Tokens</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatNumber(balance.premium_remaining)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {formatNumber(balance.premium_tokens)} purchased
          </p>
          {balance.rollover_tokens > 0 && (
            <div className="mt-3">
              <Badge variant="success" className="text-xs">
                +{formatNumber(balance.rollover_tokens)} rollover
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Usage Stats Card */}
      <Card className="col-span-2 lg:col-span-4">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Usage Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Total Requests</p>
              <p className="text-2xl font-bold">{formatNumber(balance.total_requests)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Requests Today</p>
              <p className="text-2xl font-bold">{formatNumber(balance.requests_today)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Last Activity</p>
              <p className="text-sm font-medium">
                {balance.last_request_at ? formatDate(balance.last_request_at) : 'No activity'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
