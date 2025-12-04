'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Check, Zap, Loader2 } from 'lucide-react'
import { usePayment } from '@/hooks/usePayment'

export default function PricingPage() {
  const router = useRouter()
  const { initiatePayment, loading, error } = usePayment()
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const handlePurchase = async (packageId: string) => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token')
    if (!token) {
      // Redirect to login with return URL
      router.push(`/login?redirect=/pricing&plan=${packageId}`)
      return
    }

    setSelectedPlan(packageId)
    setSuccessMessage(null)

    initiatePayment(
      packageId,
      (result) => {
        setSuccessMessage(`Payment successful! ${result.tokens_credited?.toLocaleString()} tokens added.`)
        setSelectedPlan(null)
        // Redirect to dashboard after success
        setTimeout(() => {
          router.push('/dashboard')
        }, 2000)
      },
      (error) => {
        setSelectedPlan(null)
        alert(error)
      }
    )
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <header className="relative z-10 border-b border-[hsl(var(--bolt-border))]">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-[hsl(var(--bolt-text-primary))]">BharatBuild</span>
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            <Link href="/features" className="text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors">
              Features
            </Link>
            <Link href="/docs" className="text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors">
              Docs
            </Link>
            <Link href="/pricing" className="text-[hsl(var(--bolt-text-primary))] font-medium">
              Pricing
            </Link>
          </nav>

          <Link href="/bolt">
            <Button className="bolt-gradient hover:opacity-90 transition-opacity">
              Start Building
            </Button>
          </Link>
        </div>
      </header>

      {/* Success Message */}
      {successMessage && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg">
          {successMessage}
        </div>
      )}

      {/* Pricing Content */}
      <main className="container mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 text-[hsl(var(--bolt-text-primary))]">
            Student-friendly pricing
          </h1>
          <p className="text-lg md:text-xl text-[hsl(var(--bolt-text-secondary))] max-w-2xl mx-auto">
            Affordable plans designed for students and academic projects. Build your portfolio without breaking the bank.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Free Trial */}
          <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8 hover:border-[hsl(var(--bolt-accent))] transition-all">
            <h3 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">Free Trial</h3>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))]">Free</span>
              <div className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">10,000 tokens</div>
            </div>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">1 demo project to explore</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Basic project templates</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Limited AI code generation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Basic documentation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Community support</span>
              </li>
            </ul>
            <Link href="/bolt">
              <Button className="w-full bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-border))] transition-colors">
                Start Free Trial
              </Button>
            </Link>
          </div>

          {/* Starter Pack - Maps to 'starter' package */}
          <div className="bg-[hsl(var(--bolt-bg-secondary))] border-2 border-[hsl(var(--bolt-accent))] rounded-2xl p-8 relative">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[hsl(var(--bolt-accent))] text-white px-4 py-1 rounded-full text-sm font-medium">
              Most Popular
            </div>
            <h3 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">Starter Pack</h3>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))]">₹99</span>
              <div className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">50,000 tokens</div>
            </div>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">50,000 tokens</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">1 complete project with docs</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Full documentation generation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">PowerPoint presentation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Viva Q&A preparation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Valid for 3 months</span>
              </li>
            </ul>
            <Button
              onClick={() => handlePurchase('starter')}
              disabled={loading && selectedPlan === 'starter'}
              className="w-full bolt-gradient hover:opacity-90 transition-opacity"
            >
              {loading && selectedPlan === 'starter' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                'Buy Now'
              )}
            </Button>
          </div>

          {/* Pro Pack - Maps to 'pro' package */}
          <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8 hover:border-[hsl(var(--bolt-accent))] transition-all">
            <h3 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">Pro Pack</h3>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))]">₹349</span>
              <div className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">200,000 tokens</div>
            </div>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">200,000 tokens</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Multiple projects with docs</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">All document types included</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Priority AI generation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Advanced analytics</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Valid for 6 months</span>
              </li>
            </ul>
            <Button
              onClick={() => handlePurchase('pro')}
              disabled={loading && selectedPlan === 'pro'}
              className="w-full bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-border))] transition-colors"
            >
              {loading && selectedPlan === 'pro' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                'Buy Now'
              )}
            </Button>
          </div>
        </div>

        {/* Unlimited Pack */}
        <div className="max-w-2xl mx-auto mt-8">
          <div className="bg-gradient-to-r from-blue-600/20 to-cyan-600/20 border border-blue-500/30 rounded-2xl p-8 text-center">
            <h3 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">Unlimited Pack</h3>
            <div className="mb-4">
              <span className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))]">₹1,499</span>
              <span className="text-[hsl(var(--bolt-text-secondary))]"> / 1,000,000 tokens</span>
            </div>
            <p className="text-[hsl(var(--bolt-text-secondary))] mb-6">
              For power users. Generate unlimited projects, all document types, 12 months validity, dedicated support.
            </p>
            <Button
              onClick={() => handlePurchase('unlimited')}
              disabled={loading && selectedPlan === 'unlimited'}
              className="bolt-gradient hover:opacity-90 transition-opacity px-8"
            >
              {loading && selectedPlan === 'unlimited' ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                'Get Unlimited'
              )}
            </Button>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mt-20 max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-[hsl(var(--bolt-text-primary))] text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                What are tokens?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                Tokens are used to generate AI content. One complete project with documentation typically uses 300,000-500,000 tokens. Each AI request consumes tokens based on input and output length.
              </p>
            </div>
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                What's included in documentation generation?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                We automatically generate complete project documentation including 60-80 page project reports, SRS documents, PowerPoint presentations (20-25 slides), and comprehensive Viva Q&A preparation.
              </p>
            </div>
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                How do payments work?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                We use Razorpay for secure payments. You can pay using UPI, cards, net banking, or wallets. Tokens are credited instantly after successful payment. No recurring charges - buy only what you need.
              </p>
            </div>
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                Do tokens expire?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                Starter pack tokens are valid for 3 months, Pro pack for 6 months, and Unlimited pack for 12 months from purchase date. Unused tokens can be rolled over within the validity period.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[hsl(var(--bolt-border))] mt-20">
        <div className="container mx-auto px-6 py-12">
          <div className="flex flex-wrap justify-center gap-6 mb-6 text-sm text-[hsl(var(--bolt-text-secondary))]">
            <Link href="/privacy" className="hover:text-[hsl(var(--bolt-text-primary))]">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-[hsl(var(--bolt-text-primary))]">Terms of Service</Link>
            <Link href="/contact" className="hover:text-[hsl(var(--bolt-text-primary))]">Contact</Link>
          </div>
          <div className="text-center text-[hsl(var(--bolt-text-secondary))] text-sm">
            © 2025 BharatBuild AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
