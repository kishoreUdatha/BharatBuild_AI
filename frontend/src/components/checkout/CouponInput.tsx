'use client'

import { useState } from 'react'
import { Ticket, Check, X, Loader2 } from 'lucide-react'
import apiClient from '@/lib/api-client'

interface CouponInputProps {
  amount: number // Amount in paise
  onApply: (couponCode: string, discountAmount: number, finalAmount: number) => void
  onRemove: () => void
  disabled?: boolean
  isDark?: boolean
}

interface ValidationResponse {
  valid: boolean
  code: string
  message: string
  discount_amount?: number
  discount_amount_inr?: number
  final_amount?: number
  final_amount_inr?: number
  coupon_id?: string
  owner_name?: string
}

export default function CouponInput({
  amount,
  onApply,
  onRemove,
  disabled = false,
  isDark = true
}: CouponInputProps) {
  const [couponCode, setCouponCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [appliedCoupon, setAppliedCoupon] = useState<ValidationResponse | null>(null)

  const handleApply = async () => {
    if (!couponCode.trim()) {
      setError('Please enter a coupon code')
      return
    }

    try {
      setIsLoading(true)
      setError('')

      const response = await apiClient.post<ValidationResponse>('/coupons/validate', {
        code: couponCode.toUpperCase(),
        amount: amount
      })

      if (response.valid) {
        setAppliedCoupon(response)
        onApply(
          response.code,
          response.discount_amount || 0,
          response.final_amount || amount
        )
      } else {
        setError(response.message)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to validate coupon')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRemove = () => {
    setAppliedCoupon(null)
    setCouponCode('')
    setError('')
    onRemove()
  }

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN')}`
  }

  if (appliedCoupon) {
    return (
      <div className={`p-4 rounded-lg border ${
        isDark
          ? 'bg-green-500/10 border-green-500/30'
          : 'bg-green-50 border-green-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${
              isDark ? 'bg-green-500/20' : 'bg-green-100'
            }`}>
              <Check className="w-4 h-4 text-green-500" />
            </div>
            <div>
              <p className={`text-sm font-medium ${
                isDark ? 'text-green-400' : 'text-green-700'
              }`}>
                Coupon Applied: <code className="font-mono">{appliedCoupon.code}</code>
              </p>
              <p className={`text-xs ${
                isDark ? 'text-green-500/70' : 'text-green-600'
              }`}>
                You save {formatCurrency(appliedCoupon.discount_amount || 0)}
                {appliedCoupon.owner_name && ` (via ${appliedCoupon.owner_name})`}
              </p>
            </div>
          </div>
          <button
            onClick={handleRemove}
            disabled={disabled}
            className={`p-2 rounded-lg transition-colors ${
              isDark
                ? 'hover:bg-red-500/20 text-gray-400 hover:text-red-400'
                : 'hover:bg-red-50 text-gray-500 hover:text-red-500'
            } disabled:opacity-50`}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Ticket className={`absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 ${
            isDark ? 'text-gray-500' : 'text-gray-400'
          }`} />
          <input
            type="text"
            value={couponCode}
            onChange={(e) => {
              setCouponCode(e.target.value.toUpperCase())
              setError('')
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleApply()}
            placeholder="Enter coupon code"
            disabled={disabled || isLoading}
            className={`w-full pl-10 pr-4 py-2.5 rounded-lg border text-sm font-mono ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
            } outline-none focus:border-blue-500 disabled:opacity-50`}
          />
        </div>
        <button
          onClick={handleApply}
          disabled={disabled || isLoading || !couponCode.trim()}
          className={`px-4 py-2.5 rounded-lg font-medium text-sm transition-colors ${
            isDark
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-blue-500 hover:bg-blue-600 text-white'
          } disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2`}
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Applying...</span>
            </>
          ) : (
            'Apply'
          )}
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-400 flex items-center gap-1">
          <X className="w-3 h-3" />
          {error}
        </p>
      )}
    </div>
  )
}
