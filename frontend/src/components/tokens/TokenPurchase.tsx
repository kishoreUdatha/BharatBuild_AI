'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/lib/api-client'
import { formatNumber, formatCurrency } from '@/lib/utils'
import { Check, Sparkles, Gift, ExternalLink } from 'lucide-react'

interface TokenPackage {
  id: string
  name: string
  tokens: number
  price: number
  currency: string
  popular?: boolean
  features: string[]
}

export function TokenPurchase() {
  const [packages, setPackages] = useState<TokenPackage[]>([])
  const [monthlyPlans, setMonthlyPlans] = useState<any[]>([])
  const [promoCode, setPromoCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    loadPackages()
  }, [])

  const loadPackages = async () => {
    try {
      const data = await apiClient.getTokenPackages()
      setPackages(data.packages || [])
      setMonthlyPlans(data.monthly_plans || [])
    } catch (error) {
      console.error('Failed to load packages:', error)
    }
  }

  const handlePurchase = async (packageId: string) => {
    setLoading(true)
    setMessage(null)

    try {
      const result = await apiClient.purchaseTokens(packageId)
      setMessage({
        type: 'success',
        text: `Purchase initiated! Redirecting to payment...`,
      })

      // In production, redirect to Razorpay payment URL
      if (result.payment_url) {
        setTimeout(() => {
          window.location.href = result.payment_url
        }, 1500)
      }
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Purchase failed. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleRedeemCode = async () => {
    if (!promoCode.trim()) {
      setMessage({ type: 'error', text: 'Please enter a promo code' })
      return
    }

    setLoading(true)
    setMessage(null)

    try {
      const result = await apiClient.redeemPromoCode(promoCode)
      setMessage({
        type: 'success',
        text: `${result.message} +${formatNumber(result.bonus_tokens)} tokens added!`,
      })
      setPromoCode('')
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Invalid promo code',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* Promo Code Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Gift className="h-5 w-5 text-purple-500" />
            Redeem Promo Code
          </CardTitle>
          <CardDescription>
            Have a promo code? Redeem it here for bonus tokens
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Input
              placeholder="Enter promo code (e.g., WELCOME2024)"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
              disabled={loading}
            />
            <Button onClick={handleRedeemCode} disabled={loading || !promoCode.trim()}>
              {loading ? 'Redeeming...' : 'Redeem'}
            </Button>
          </div>

          {message && (
            <div
              className={`mt-4 p-3 rounded-md text-sm ${
                message.type === 'success'
                  ? 'bg-green-50 text-green-900 border border-green-200'
                  : 'bg-red-50 text-red-900 border border-red-200'
              }`}
            >
              {message.text}
            </div>
          )}

          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-900 font-medium mb-2">Available Promo Codes:</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">WELCOME2024 - 10K tokens</Badge>
              <Badge variant="secondary">LAUNCH50 - 50K tokens</Badge>
              <Badge variant="secondary">BETA100 - 100K tokens</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* One-Time Packages */}
      <div>
        <h2 className="text-2xl font-bold mb-4">One-Time Token Packages</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {packages.map((pkg) => (
            <Card
              key={pkg.id}
              className={`relative ${pkg.popular ? 'border-purple-500 border-2' : ''}`}
            >
              {pkg.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-purple-500 text-white">
                    <Sparkles className="h-3 w-3 mr-1" />
                    Most Popular
                  </Badge>
                </div>
              )}

              <CardHeader>
                <CardTitle>{pkg.name}</CardTitle>
                <CardDescription>
                  <span className="text-3xl font-bold text-foreground">
                    {formatCurrency(pkg.price)}
                  </span>
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="text-center py-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold">{formatNumber(pkg.tokens)}</p>
                  <p className="text-sm text-muted-foreground">tokens</p>
                </div>

                <ul className="space-y-2">
                  {pkg.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full"
                  variant={pkg.popular ? 'default' : 'outline'}
                  onClick={() => handlePurchase(pkg.id)}
                  disabled={loading}
                >
                  {loading ? 'Processing...' : 'Purchase Now'}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Monthly Plans */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Monthly Subscription Plans</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {monthlyPlans.map((plan) => (
            <Card key={plan.id} className={plan.id === 'free' ? 'border-gray-300' : ''}>
              <CardHeader>
                <CardTitle>{plan.name}</CardTitle>
                <CardDescription>
                  {plan.price === 0 ? (
                    <span className="text-3xl font-bold text-foreground">Free</span>
                  ) : (
                    <span className="text-3xl font-bold text-foreground">
                      {formatCurrency(plan.price)}
                      <span className="text-sm text-muted-foreground">/month</span>
                    </span>
                  )}
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="text-center py-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold">{formatNumber(plan.tokens_per_month)}</p>
                  <p className="text-sm text-muted-foreground">tokens/month</p>
                </div>

                <ul className="space-y-2">
                  {plan.features.map((feature: string, index: number) => (
                    <li key={index} className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {plan.id === 'free' ? (
                  <Button className="w-full" variant="outline" disabled>
                    Current Plan
                  </Button>
                ) : (
                  <Button
                    className="w-full"
                    onClick={() => handlePurchase(plan.id)}
                    disabled={loading}
                  >
                    {loading ? 'Processing...' : 'Subscribe'}
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Payment Info */}
      <Card className="bg-gray-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <ExternalLink className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <p className="font-medium text-sm">Secure Payment via Razorpay</p>
              <p className="text-xs text-muted-foreground mt-1">
                All transactions are processed securely through Razorpay. We accept UPI, Cards,
                Net Banking, and Wallets.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
