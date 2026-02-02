'use client'

import { useState, useEffect, useCallback } from 'react'
import { Wallet, TrendingUp, Users, Gift, ChevronRight, Loader2, Copy, Check } from 'lucide-react'
import apiClient from '@/lib/api-client'

interface WalletData {
  has_coupon: boolean
  coupon_code: string | null
  total_uses: number
  total_earned: number
  total_earned_inr: number
  wallet_balance: number
  wallet_balance_inr: number
  reward_per_use: number
  reward_per_use_inr: number
}

interface WalletCardProps {
  isDark?: boolean
}

export default function WalletCard({ isDark = true }: WalletCardProps) {
  const [data, setData] = useState<WalletData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const response = await apiClient.get<WalletData>('/coupons/earnings')
      setData(response)
      setError('')
    } catch (err: any) {
      // Don't show error if user simply doesn't have a coupon
      if (err.response?.status !== 404) {
        setError('Failed to load wallet data')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const copyCode = () => {
    if (data?.coupon_code) {
      navigator.clipboard.writeText(data.coupon_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const formatCurrency = (value: number) => {
    return `₹${value.toLocaleString('en-IN')}`
  }

  if (loading) {
    return (
      <div className={`rounded-xl border p-6 ${
        isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
      }`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className={`w-6 h-6 animate-spin ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
        </div>
      </div>
    )
  }

  if (error) {
    return null // Don't show card if there's an error
  }

  if (!data?.has_coupon) {
    return (
      <div className={`rounded-xl border p-6 ${
        isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
      }`}>
        <div className="flex items-center gap-3 mb-4">
          <div className={`p-2 rounded-lg ${isDark ? 'bg-purple-500/20' : 'bg-purple-100'}`}>
            <Gift className="w-5 h-5 text-purple-500" />
          </div>
          <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Referral Program
          </h3>
        </div>
        <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          You don&apos;t have a referral code yet. Contact support to get one and start earning rewards!
        </p>
        <a
          href="mailto:support@bharatbuild.ai?subject=Request%20Referral%20Code"
          className={`inline-flex items-center gap-1 text-sm font-medium text-blue-500 hover:text-blue-400`}
        >
          Request a referral code
          <ChevronRight className="w-4 h-4" />
        </a>
      </div>
    )
  }

  return (
    <div className={`rounded-xl border overflow-hidden ${
      isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
    }`}>
      {/* Header with gradient */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-lg">
              <Wallet className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">My Wallet</h3>
              <p className="text-xs text-white/70">Referral Earnings</p>
            </div>
          </div>
        </div>

        <div className="text-3xl font-bold text-white mb-1">
          {formatCurrency(data.wallet_balance_inr)}
        </div>
        <p className="text-sm text-white/70">Available Balance</p>
      </div>

      {/* Coupon Code */}
      <div className={`p-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
        <p className={`text-xs font-medium mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
          YOUR REFERRAL CODE
        </p>
        <div className="flex items-center gap-2">
          <code className={`flex-1 px-3 py-2 rounded-lg font-mono text-lg ${
            isDark ? 'bg-[#252525] text-white' : 'bg-gray-100 text-gray-900'
          }`}>
            {data.coupon_code}
          </code>
          <button
            onClick={copyCode}
            className={`p-2 rounded-lg transition-colors ${
              isDark
                ? 'bg-[#252525] hover:bg-[#333] text-gray-400'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-600'
            }`}
          >
            {copied ? (
              <Check className="w-5 h-5 text-green-500" />
            ) : (
              <Copy className="w-5 h-5" />
            )}
          </button>
        </div>
        <p className={`text-xs mt-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
          Share this code to earn {formatCurrency(data.reward_per_use_inr)} per use
        </p>
      </div>

      {/* Stats */}
      <div className="p-4 grid grid-cols-2 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Users className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Uses</span>
          </div>
          <p className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {data.total_uses}
          </p>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
            <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Earned</span>
          </div>
          <p className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            {formatCurrency(data.total_earned_inr)}
          </p>
        </div>
      </div>

      {/* How it works */}
      <div className={`px-4 pb-4`}>
        <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
          <p className={`text-xs font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
            How it works
          </p>
          <ul className={`text-xs space-y-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            <li>• Share your code with friends</li>
            <li>• They get {formatCurrency(data.reward_per_use_inr)} off on their purchase</li>
            <li>• You earn {formatCurrency(data.reward_per_use_inr)} to your wallet</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
