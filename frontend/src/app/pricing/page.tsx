'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Check, X, Zap, Loader2, Crown, Star, Shield, Clock, Download, FileText, Code, Tag, Gift, Users } from 'lucide-react'
import { usePayment } from '@/hooks/usePayment'

// Plan configuration
const plans = [
  {
    name: 'Free',
    slug: 'free',
    price: 0,
    priceDisplay: '₹0',
    period: 'forever',
    description: 'Preview your project',
    popular: false,
    buttonText: 'Try Free',
    buttonVariant: 'outline' as const,
    features: [
      { text: 'Generate 3 preview files', included: true },
      { text: 'View project structure', included: true },
      { text: 'AI chat assistance', included: true },
      { text: 'No download', included: false },
      { text: 'No bug fixing', included: false },
      { text: 'No documentation', included: false },
    ],
  },
  {
    name: 'Standard',
    slug: 'standard',
    price: 199900,
    priceDisplay: '₹1,999',
    period: 'one-time',
    description: 'Full working code',
    popular: false,
    buttonText: 'Get Standard',
    buttonVariant: 'outline' as const,
    features: [
      { text: '40-50 files', included: true },
      { text: 'All Technologies', included: true },
      { text: 'Database + Auth', included: true },
      { text: 'Download (ZIP)', included: true },
      { text: '15 Bug Fixes', included: true },
      { text: 'GitHub Export', included: true },
      { text: 'Code Comments', included: true },
      { text: 'README + Setup Guide', included: true },
      { text: 'No Documentation', included: false },
      { text: '6 Months Validity', included: true },
    ],
  },
  {
    name: 'Plus',
    slug: 'plus',
    price: 299900,
    priceDisplay: '₹2,999',
    period: 'one-time',
    description: 'Code + Basic Docs',
    popular: false,
    buttonText: 'Get Plus',
    buttonVariant: 'outline' as const,
    features: [
      { text: '50-60 files', included: true },
      { text: 'All Technologies', included: true },
      { text: 'Database + OAuth', included: true },
      { text: 'Download (ZIP)', included: true },
      { text: '25 Bug Fixes', included: true },
      { text: 'GitHub Export', included: true },
      { text: 'Project Report (50-60 pages)', included: true },
      { text: 'PPT (15 slides)', included: true },
      { text: 'Viva Q&A (50 questions)', included: true },
      { text: 'No SRS/SDS/UML', included: false },
      { text: '6 Months Validity', included: true },
    ],
  },
  {
    name: 'Premium',
    slug: 'premium',
    price: 449900,
    priceDisplay: '₹4,499',
    period: 'one-time',
    description: 'Everything included',
    popular: true,
    buttonText: 'Get Premium',
    buttonVariant: 'default' as const,
    features: [
      { text: '70+ files', included: true },
      { text: 'All Tech + AI/ML', included: true },
      { text: 'Full Auth + Admin', included: true },
      { text: 'Unlimited Bug Fixes', included: true },
      { text: 'Project Report (80-100 pages)', included: true },
      { text: 'SRS + SDS Documents', included: true },
      { text: 'PPT (20 slides)', included: true },
      { text: 'Viva Q&A (100+ questions)', included: true },
      { text: 'UML Diagrams (6 types)', included: true },
      { text: 'APK/IPA Build', included: true },
      { text: 'WhatsApp Support', included: true },
      { text: '6 Months Validity', included: true },
    ],
  },
]

// Feature comparison data
const comparisonFeatures = [
  { name: 'Project Files', free: '3 preview', standard: '40-50', plus: '50-60', premium: '70+' },
  { name: 'Technologies', free: '-', standard: 'All', plus: 'All', premium: 'All + AI/ML' },
  { name: 'Database', free: false, standard: true, plus: true, premium: true },
  { name: 'Authentication', free: false, standard: 'Basic', plus: 'OAuth', premium: 'OAuth + JWT' },
  { name: 'Download Code', free: false, standard: true, plus: true, premium: true },
  { name: 'Bug Fixes', free: false, standard: '15', plus: '25', premium: 'Unlimited' },
  { name: 'GitHub Export', free: false, standard: true, plus: true, premium: true },
  { name: 'Project Report', free: false, standard: false, plus: '50-60 pages', premium: '80-100 pages' },
  { name: 'SRS + SDS', free: false, standard: false, plus: false, premium: true },
  { name: 'PPT Presentation', free: false, standard: false, plus: '15 slides', premium: '20 slides' },
  { name: 'Viva Q&A', free: false, standard: false, plus: '50', premium: '100+' },
  { name: 'UML Diagrams', free: false, standard: false, plus: false, premium: '6 types' },
  { name: 'APK/IPA Build', free: false, standard: false, plus: false, premium: true },
  { name: 'Support', free: 'Chat', standard: 'Email 24hr', plus: 'Email 12hr', premium: 'WhatsApp 4hr' },
  { name: 'Validity', free: '∞', standard: '6 Months', plus: '6 Months', premium: '6 Months' },
]

export default function PricingPage() {
  const router = useRouter()
  const {
    initiatePayment,
    validateCoupon,
    removeCoupon,
    loading,
    validatingCoupon,
    appliedCoupon,
    couponError
  } = usePayment()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [couponInput, setCouponInput] = useState('')
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)

  const handleApplyCoupon = async (planSlug: string, originalPrice: number) => {
    if (!couponInput.trim()) return

    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push(`/login?redirect=/pricing&plan=${planSlug}`)
      return
    }

    setSelectedPlan(planSlug)
    await validateCoupon(couponInput.trim(), originalPrice)
  }

  const handleRemoveCoupon = () => {
    removeCoupon()
    setCouponInput('')
    setSelectedPlan(null)
  }

  const handlePurchase = async (planSlug: string) => {
    if (planSlug === 'free') {
      const token = localStorage.getItem('access_token')
      if (!token) {
        router.push('/login?redirect=/build')
      } else {
        router.push('/build')
      }
      return
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push(`/login?redirect=/pricing&plan=${planSlug}`)
      return
    }

    setSuccessMessage(null)
    setErrorMessage(null)

    initiatePayment(
      planSlug,
      (result) => {
        setSuccessMessage(`Payment successful! Redirecting to build page...`)
        setTimeout(() => {
          router.push('/build')
        }, 2500)
      },
      (error) => {
        setErrorMessage(error || 'Payment failed. Please try again.')
        setTimeout(() => setErrorMessage(null), 5000)
      },
      selectedPlan === planSlug ? appliedCoupon?.code : undefined
    )
  }

  const getDiscountedPrice = (plan: typeof plans[0]): number => {
    if (selectedPlan === plan.slug && appliedCoupon && appliedCoupon.final_amount !== undefined) {
      return appliedCoupon.final_amount
    }
    return plan.price
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#0f0f1a]">
      {/* Header */}
      <header className="border-b border-white/10">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="font-bold text-xl text-white">BharatBuild</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8">
            <Link href="/" className="text-gray-400 hover:text-white transition-colors">Home</Link>
            <Link href="/build" className="text-gray-400 hover:text-white transition-colors">Build</Link>
            <Link href="/pricing" className="text-white font-medium">Pricing</Link>
          </nav>
          <Link href="/build">
            <Button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white shadow-lg shadow-blue-500/25">
              Start Building
            </Button>
          </Link>
        </div>
      </header>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-6 py-4 rounded-lg shadow-lg flex items-center gap-3">
          <Check className="w-5 h-5" />
          {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-red-600 text-white px-6 py-4 rounded-lg shadow-lg flex items-center gap-3">
          <X className="w-5 h-5" />
          {errorMessage}
        </div>
      )}

      <main className="container mx-auto px-6 py-16">
        {/* Hero */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/30 mb-6">
            <Star className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-300">Simple, Transparent Pricing</span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 text-white">
            Choose Your Plan
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            From preview to complete final year project with all documentation
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="max-w-7xl mx-auto mb-20">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.slug}
                className={`relative rounded-3xl p-6 transition-all ${
                  plan.popular
                    ? 'bg-gradient-to-b from-[#1a1a2e] to-[#16162a] border-2 border-blue-500/50 shadow-xl shadow-blue-500/10'
                    : 'bg-[#111118] border border-white/10 hover:border-white/20'
                }`}
              >
                {/* Popular Badge */}
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold text-sm shadow-lg">
                      <Crown className="w-4 h-4" />
                      BEST VALUE
                    </div>
                  </div>
                )}

                <div className={`mb-4 ${plan.popular ? 'mt-4' : ''}`}>
                  <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
                  <p className="text-gray-500 text-sm">{plan.description}</p>
                </div>

                <div className="mb-4">
                  {selectedPlan === plan.slug && appliedCoupon ? (
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-gray-500 line-through">{plan.priceDisplay}</span>
                      <span className="text-3xl font-bold text-white">₹{(getDiscountedPrice(plan) / 100).toLocaleString()}</span>
                    </div>
                  ) : (
                    <span className="text-3xl font-bold text-white">{plan.priceDisplay}</span>
                  )}
                  <span className="text-gray-500 ml-2 text-sm">{plan.period}</span>
                </div>

                {/* Coupon Input for paid plans */}
                {plan.price > 0 && (
                  <div className="mb-4">
                    {selectedPlan === plan.slug && appliedCoupon ? (
                      <div className="flex items-center justify-between bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-2 text-sm">
                        <div className="flex items-center gap-2">
                          <Check className="w-4 h-4 text-green-500" />
                          <span className="text-green-400">{appliedCoupon.code}</span>
                        </div>
                        <button onClick={handleRemoveCoupon} className="text-gray-400 hover:text-white text-xs">
                          Remove
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={selectedPlan === plan.slug ? couponInput : ''}
                          onChange={(e) => {
                            setSelectedPlan(plan.slug)
                            setCouponInput(e.target.value.toUpperCase())
                          }}
                          placeholder="Coupon"
                          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500/50 uppercase"
                        />
                        <Button
                          onClick={() => handleApplyCoupon(plan.slug, plan.price)}
                          disabled={validatingCoupon || (selectedPlan === plan.slug && !couponInput.trim())}
                          variant="outline"
                          size="sm"
                          className="border-blue-500/50 text-blue-400 hover:bg-blue-500/10"
                        >
                          {validatingCoupon && selectedPlan === plan.slug ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Apply'}
                        </Button>
                      </div>
                    )}
                    {couponError && selectedPlan === plan.slug && (
                      <p className="text-red-400 text-xs mt-1">{couponError}</p>
                    )}
                  </div>
                )}

                <Button
                  onClick={() => handlePurchase(plan.slug)}
                  disabled={loading}
                  variant={plan.buttonVariant}
                  className={`w-full py-5 mb-6 ${
                    plan.popular
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold shadow-lg shadow-blue-500/25'
                      : 'border-white/20 text-white hover:bg-white/5'
                  }`}
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : plan.buttonText}
                </Button>

                <ul className="space-y-3">
                  {plan.features.map((feature, index) => (
                    <li key={index} className={`flex items-center gap-2 text-sm ${feature.included ? 'text-gray-300' : 'text-gray-600'}`}>
                      {feature.included ? (
                        <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                      ) : (
                        <X className="w-4 h-4 text-gray-700 flex-shrink-0" />
                      )}
                      <span>{feature.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* College Bulk Plan */}
        <div className="max-w-4xl mx-auto mb-20">
          <div className="bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-3xl border border-purple-500/30 p-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Users className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white">College Bulk</h3>
                  <p className="text-gray-400">For groups of 10+ students</p>
                </div>
              </div>
              <div className="text-center md:text-right">
                <div className="text-3xl font-bold text-white">₹2,499<span className="text-lg text-gray-400">/student</span></div>
                <p className="text-purple-400 text-sm">Everything in Premium + College Invoice</p>
              </div>
              <Button
                onClick={() => window.open('mailto:support@bharatbuild.ai?subject=College Bulk Inquiry', '_blank')}
                className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-8"
              >
                Contact Us
              </Button>
            </div>
          </div>
        </div>

        {/* Feature Comparison Table */}
        <div className="max-w-6xl mx-auto mb-20">
          <h2 className="text-3xl font-bold text-white text-center mb-10">Feature Comparison</h2>
          <div className="bg-[#111118] rounded-2xl border border-white/10 overflow-hidden overflow-x-auto">
            <table className="w-full min-w-[800px]">
              <thead>
                <tr className="bg-white/5 border-b border-white/10">
                  <th className="text-left p-4 text-gray-400 font-medium">Feature</th>
                  <th className="text-center p-4 text-gray-400 font-medium">Free</th>
                  <th className="text-center p-4 text-gray-400 font-medium">₹1,999</th>
                  <th className="text-center p-4 text-gray-400 font-medium">₹2,999</th>
                  <th className="text-center p-4 text-cyan-400 font-medium">₹4,499</th>
                </tr>
              </thead>
              <tbody>
                {comparisonFeatures.map((feature, index) => (
                  <tr key={index} className={index !== comparisonFeatures.length - 1 ? 'border-b border-white/5' : ''}>
                    <td className="p-4 text-gray-300">{feature.name}</td>
                    {['free', 'standard', 'plus', 'premium'].map((plan) => {
                      const value = feature[plan as keyof typeof feature]
                      return (
                        <td key={plan} className="text-center p-4">
                          {typeof value === 'boolean' ? (
                            value ? (
                              <Check className="w-5 h-5 text-green-500 mx-auto" />
                            ) : (
                              <X className="w-5 h-5 text-gray-700 mx-auto" />
                            )
                          ) : (
                            <span className={plan === 'premium' ? 'text-green-400 font-medium' : 'text-gray-400'}>{value}</span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Trust Badges */}
        <div className="max-w-4xl mx-auto mb-20">
          <div className="flex flex-wrap justify-center gap-8">
            <div className="flex items-center gap-2 text-gray-400">
              <Shield className="w-5 h-5 text-green-500" />
              <span>Secure Payments via Razorpay</span>
            </div>
            <div className="flex items-center gap-2 text-gray-400">
              <Clock className="w-5 h-5 text-blue-500" />
              <span>Instant Access</span>
            </div>
            <div className="flex items-center gap-2 text-gray-400">
              <Star className="w-5 h-5 text-yellow-500" />
              <span>95,000+ Students Trust Us</span>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-10">Frequently Asked Questions</h2>
          <div className="space-y-4">
            {[
              {
                q: 'What is the difference between Standard and Premium?',
                a: 'Standard (₹1,999) gives you full working code with database and authentication. Premium (₹4,499) includes everything in Standard plus complete documentation - Project Report (80-100 pages), SRS, SDS, PPT, Viva Q&A, and UML diagrams.'
              },
              {
                q: 'Can I upgrade from Standard to Premium later?',
                a: 'Yes! You can upgrade anytime. Contact support and we will help you with the upgrade process. You only pay the difference.'
              },
              {
                q: 'What technologies are supported?',
                a: 'We support React, Next.js, Vue, Flutter, React Native, Django, FastAPI, Node.js, Spring Boot, and more. Premium plan also includes AI/ML project support.'
              },
              {
                q: 'How long is the validity?',
                a: 'All paid plans have 6 months validity. You can download your code, make bug fixes, and access documentation within this period.'
              },
              {
                q: 'Do you provide college bulk discounts?',
                a: 'Yes! For groups of 10+ students, we offer Premium features at ₹2,499/student with college invoice and dedicated WhatsApp support. Contact us for more details.'
              },
            ].map((faq, index) => (
              <div key={index} className="bg-[#111118] rounded-xl border border-white/10 p-6">
                <h3 className="text-lg font-semibold text-white mb-2">{faq.q}</h3>
                <p className="text-gray-400">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-20">
        <div className="container mx-auto px-6 py-12">
          <div className="flex flex-wrap justify-center gap-6 mb-6 text-sm text-gray-500">
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <Link href="/contact" className="hover:text-white transition-colors">Contact</Link>
          </div>
          <div className="text-center text-gray-600 text-sm">
            © 2025 BharatBuild AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
