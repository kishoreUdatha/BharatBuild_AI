'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Check, X, Zap, Loader2, Crown, Star, Shield, Clock, Download, FileText, Code, Tag, Gift } from 'lucide-react'
import { usePayment } from '@/hooks/usePayment'

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

  // Original price in paise (₹4,499 = 449900 paise)
  const originalPrice = 449900
  const discountedPrice = appliedCoupon?.final_amount || originalPrice

  const handleApplyCoupon = async () => {
    if (!couponInput.trim()) return

    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push(`/login?redirect=/pricing&plan=premium`)
      return
    }

    await validateCoupon(couponInput.trim(), originalPrice)
  }

  const handleRemoveCoupon = () => {
    removeCoupon()
    setCouponInput('')
  }

  const handlePurchase = async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push(`/login?redirect=/pricing&plan=premium`)
      return
    }

    setSuccessMessage(null)
    setErrorMessage(null)

    initiatePayment(
      'complete',
      (result) => {
        console.log('[Pricing] Payment success:', result)
        const tokens = result.tokens_credited ? ` ${result.tokens_credited.toLocaleString()} tokens credited.` : ''
        setSuccessMessage(`Payment successful!${tokens} Redirecting to build page...`)
        // Give user time to see the success message
        setTimeout(() => {
          router.push('/build')
        }, 2500)
      },
      (error) => {
        console.error('[Pricing] Payment failed:', error)
        setErrorMessage(error || 'Payment failed. Please try again or contact support.')
        // Auto-hide error after 5 seconds
        setTimeout(() => setErrorMessage(null), 5000)
      },
      appliedCoupon?.code
    )
  }

  const handleFreeTrial = () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push('/login?redirect=/build')
    } else {
      router.push('/build')
    }
  }

  // Features comparison
  const features = [
    { name: 'Complete Projects', free: '3 Files Only', premium: '1 Full Project', icon: Code },
    { name: 'Working Code', free: false, premium: true, icon: Code },
    { name: 'Bug Fixing', free: false, premium: 'Unlimited', icon: Code },
    { name: 'SRS Document', free: false, premium: true, icon: FileText },
    { name: 'SDS Document', free: false, premium: true, icon: FileText },
    { name: 'Project Report (60-80 pages)', free: false, premium: true, icon: FileText },
    { name: 'PPT Presentation (15 slides)', free: false, premium: true, icon: FileText },
    { name: 'Viva Q&A (50+ questions)', free: false, premium: true, icon: FileText },
    { name: 'Code Execution & Preview', free: false, premium: true, icon: Code },
    { name: 'Download ZIP', free: false, premium: true, icon: Download },
    { name: 'GitHub Export', free: false, premium: true, icon: Download },
    { name: 'Validity', free: '7 days', premium: '1 month', icon: Clock },
  ]

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

      {/* Success Message */}
      {successMessage && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-6 py-4 rounded-lg shadow-lg flex items-center gap-3 animate-pulse">
          <Check className="w-5 h-5" />
          {successMessage}
        </div>
      )}

      {/* Error Message */}
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
            <span className="text-sm font-medium text-blue-300">Special Launch Offer</span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 text-white">
            Complete Project Package
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Full working code + Project Report + SRS + SDS + PPT + Viva Q&A
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400 font-semibold">
              Everything for your final year submission
            </span>
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="max-w-5xl mx-auto mb-20">
          <div className="grid md:grid-cols-2 gap-8">
            {/* FREE Plan */}
            <div className="relative bg-[#111118] rounded-3xl border border-white/10 p-8 hover:border-white/20 transition-all">
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-white mb-2">Free</h3>
                <p className="text-gray-500">Preview your project</p>
              </div>

              <div className="mb-8">
                <span className="text-5xl font-bold text-white">₹0</span>
                <span className="text-gray-500 ml-2">forever</span>
              </div>

              <Button
                onClick={handleFreeTrial}
                variant="outline"
                className="w-full py-6 text-lg border-white/20 text-white hover:bg-white/5 mb-8"
              >
                Try Free
              </Button>

              <ul className="space-y-4">
                <li className="flex items-center gap-3 text-gray-400">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Generate 3 preview files only</span>
                </li>
                <li className="flex items-center gap-3 text-gray-400">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Preview project structure</span>
                </li>
                <li className="flex items-center gap-3 text-gray-400">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>AI chat assistance</span>
                </li>
                <li className="flex items-center gap-3 text-gray-500">
                  <X className="w-5 h-5 text-gray-700" />
                  <span>No bug fixing</span>
                </li>
                <li className="flex items-center gap-3 text-gray-500">
                  <X className="w-5 h-5 text-gray-700" />
                  <span>No documentation</span>
                </li>
                <li className="flex items-center gap-3 text-gray-500">
                  <X className="w-5 h-5 text-gray-700" />
                  <span>No download</span>
                </li>
              </ul>
            </div>

            {/* PREMIUM Plan */}
            <div className="relative bg-gradient-to-b from-[#1a1a2e] to-[#16162a] rounded-3xl border-2 border-blue-500/50 p-8 shadow-xl shadow-blue-500/10">
              {/* Popular Badge */}
              <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold text-sm shadow-lg">
                  <Crown className="w-4 h-4" />
                  MOST POPULAR
                </div>
              </div>

              <div className="mb-6 mt-4">
                <h3 className="text-2xl font-bold text-white mb-2">Premium</h3>
                <p className="text-cyan-400">1 Complete Project</p>
              </div>

              <div className="mb-2">
                {appliedCoupon ? (
                  <div className="flex items-baseline gap-3">
                    <span className="text-3xl font-bold text-gray-500 line-through">₹4,499</span>
                    <span className="text-5xl font-bold text-white">₹{(discountedPrice / 100).toLocaleString()}</span>
                  </div>
                ) : (
                  <>
                    <span className="text-5xl font-bold text-white">₹4,499</span>
                    <span className="text-gray-400 ml-2">one-time</span>
                  </>
                )}
              </div>
              {appliedCoupon && (
                <div className="flex items-center gap-2 mb-2">
                  <Gift className="w-4 h-4 text-green-400" />
                  <span className="text-green-400 text-sm font-medium">
                    You save ₹{(appliedCoupon.discount_amount_inr || 0).toLocaleString()}!
                  </span>
                </div>
              )}
              <p className="text-green-400 text-sm mb-4">
                1 month validity
              </p>

              {/* Coupon Code Input */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-2">
                  <Tag className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-400">Have a coupon code?</span>
                </div>
                {appliedCoupon ? (
                  <div className="flex items-center justify-between bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Check className="w-5 h-5 text-green-500" />
                      <span className="text-green-400 font-medium">{appliedCoupon.code}</span>
                      <span className="text-green-400/70 text-sm">applied</span>
                    </div>
                    <button
                      onClick={handleRemoveCoupon}
                      className="text-gray-400 hover:text-white text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={couponInput}
                      onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                      placeholder="Enter coupon code"
                      className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 uppercase"
                      disabled={validatingCoupon}
                    />
                    <Button
                      onClick={handleApplyCoupon}
                      disabled={validatingCoupon || !couponInput.trim()}
                      variant="outline"
                      className="border-blue-500/50 text-blue-400 hover:bg-blue-500/10"
                    >
                      {validatingCoupon ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        'Apply'
                      )}
                    </Button>
                  </div>
                )}
                {couponError && (
                  <p className="text-red-400 text-sm mt-2">{couponError}</p>
                )}
              </div>

              <Button
                onClick={handlePurchase}
                disabled={loading}
                className="w-full py-6 text-lg bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold shadow-lg shadow-blue-500/25 mb-8"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : appliedCoupon ? (
                  `Pay ₹${(discountedPrice / 100).toLocaleString()}`
                ) : (
                  'Get 1 Project'
                )}
              </Button>

              <ul className="space-y-4">
                <li className="flex items-center gap-3 text-white">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span><strong>1 Complete Project</strong></span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Full working code</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Unlimited bug fixing</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Project Report (60-80 pages)</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>SRS + SDS Documents</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>PPT (15 slides)</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Viva Q&A (50+ questions)</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Plagiarism check</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>Download + GitHub export</span>
                </li>
                <li className="flex items-center gap-3 text-gray-300">
                  <Check className="w-5 h-5 text-cyan-500" />
                  <span>1 month validity</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Feature Comparison Table */}
        <div className="max-w-4xl mx-auto mb-20">
          <h2 className="text-3xl font-bold text-white text-center mb-10">
            Feature Comparison
          </h2>
          <div className="bg-[#111118] rounded-2xl border border-white/10 overflow-hidden">
            <div className="grid grid-cols-3 gap-4 p-4 bg-white/5 border-b border-white/10">
              <div className="text-gray-400 font-medium">Feature</div>
              <div className="text-center text-gray-400 font-medium">Free</div>
              <div className="text-center text-cyan-400 font-medium">Premium</div>
            </div>
            {features.map((feature, index) => (
              <div
                key={index}
                className={`grid grid-cols-3 gap-4 p-4 ${index !== features.length - 1 ? 'border-b border-white/5' : ''}`}
              >
                <div className="flex items-center gap-2 text-gray-300">
                  <feature.icon className="w-4 h-4 text-gray-500" />
                  {feature.name}
                </div>
                <div className="text-center">
                  {typeof feature.free === 'boolean' ? (
                    feature.free ? (
                      <Check className="w-5 h-5 text-green-500 mx-auto" />
                    ) : (
                      <X className="w-5 h-5 text-gray-700 mx-auto" />
                    )
                  ) : (
                    <span className="text-gray-500">{feature.free}</span>
                  )}
                </div>
                <div className="text-center">
                  {typeof feature.premium === 'boolean' ? (
                    feature.premium ? (
                      <Check className="w-5 h-5 text-green-500 mx-auto" />
                    ) : (
                      <X className="w-5 h-5 text-gray-700 mx-auto" />
                    )
                  ) : (
                    <span className="text-green-400 font-medium">{feature.premium}</span>
                  )}
                </div>
              </div>
            ))}
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
          <h2 className="text-3xl font-bold text-white text-center mb-10">
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            {[
              {
                q: 'What types of projects can I create?',
                a: 'You can create any type of project - E-commerce, Hospital Management, Student Portal, Food Delivery, Chat Apps, Social Media clones, and more. Our AI supports React, Next.js, Node.js, Python, and many other technologies.'
              },
              {
                q: 'How long does it take to generate a project?',
                a: 'A complete project with all documentation typically takes 15-30 minutes depending on complexity. You can start using your project immediately after generation.'
              },
              {
                q: 'Can I modify the generated code?',
                a: 'Yes! You get full ownership of the code. You can edit, modify, and customize everything to your needs directly in our editor or after downloading.'
              },
              {
                q: 'What format are the documents in?',
                a: 'Project reports and documentation are generated as PDF files. PPT is provided in PPTX format. All documents follow IEEE standards appropriate for academic submission.'
              },
              {
                q: 'Is there a refund policy?',
                a: 'Due to the nature of AI-generated content, we cannot offer refunds once projects are generated. However, we provide a free demo so you can try before purchasing.'
              },
            ].map((faq, index) => (
              <div key={index} className="bg-[#111118] rounded-xl border border-white/10 p-6">
                <h3 className="text-lg font-semibold text-white mb-2">{faq.q}</h3>
                <p className="text-gray-400">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Final CTA */}
        <div className="max-w-2xl mx-auto mt-20 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Build Your Project?
          </h2>
          <p className="text-gray-400 mb-8">
            Join 500+ students who have successfully submitted their projects
          </p>
          <Button
            onClick={handlePurchase}
            disabled={loading}
            size="lg"
            className="px-12 py-6 text-lg bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-semibold shadow-lg shadow-blue-500/25"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Processing...
              </>
            ) : appliedCoupon ? (
              <>
                <Crown className="w-5 h-5 mr-2" />
                Get Premium - ₹{(discountedPrice / 100).toLocaleString()}
              </>
            ) : (
              <>
                <Crown className="w-5 h-5 mr-2" />
                Get Premium - ₹4,499
              </>
            )}
          </Button>
          <p className="text-gray-500 text-sm mt-4">
            One-time payment • No subscription • 1 month validity
          </p>
          {appliedCoupon && (
            <p className="text-green-400 text-sm mt-2">
              Coupon {appliedCoupon.code} applied - Save ₹{(appliedCoupon.discount_amount_inr || 0).toLocaleString()}!
            </p>
          )}
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
