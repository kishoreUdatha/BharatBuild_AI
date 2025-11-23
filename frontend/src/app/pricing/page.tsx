'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Check, Zap } from 'lucide-react'

export default function PricingPage() {
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
              <div className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">7 days trial</div>
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

          {/* Student Plan */}
          <div className="bg-[hsl(var(--bolt-bg-secondary))] border-2 border-[hsl(var(--bolt-accent))] rounded-2xl p-8 relative">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[hsl(var(--bolt-accent))] text-white px-4 py-1 rounded-full text-sm font-medium">
              Most Popular
            </div>
            <h3 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">Student</h3>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))]">₹199</span>
              <span className="text-[hsl(var(--bolt-text-secondary))]">/month</span>
            </div>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Unlimited academic projects</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Advanced project templates</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Full documentation generation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">PowerPoint presentations</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Video tutorials included</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Priority support</span>
              </li>
            </ul>
            <Link href="/bolt">
              <Button className="w-full bolt-gradient hover:opacity-90 transition-opacity">
                Get Started
              </Button>
            </Link>
          </div>

          {/* Premium Plan */}
          <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8 hover:border-[hsl(var(--bolt-accent))] transition-all">
            <h3 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">Premium</h3>
            <div className="mb-6">
              <span className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))]">₹499</span>
              <span className="text-[hsl(var(--bolt-text-secondary))]">/month</span>
            </div>
            <ul className="space-y-4 mb-8">
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Everything in Student</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Commercial projects allowed</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Custom branding options</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">API access for automation</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">Dedicated account manager</span>
              </li>
              <li className="flex items-start gap-3">
                <Check className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-[hsl(var(--bolt-text-secondary))]">24/7 priority support</span>
              </li>
            </ul>
            <Link href="/bolt">
              <Button className="w-full bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-border))] transition-colors">
                Get Started
              </Button>
            </Link>
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
                Do you offer student discounts?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                Yes! Our Student plan is specifically priced for students at just ₹199/month. You'll need to verify your student status with a valid college ID.
              </p>
            </div>
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                What's included in documentation generation?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                We automatically generate complete project documentation including README files, technical specifications, API documentation, and user guides - everything you need to submit your academic project.
              </p>
            </div>
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                Can I use my projects commercially after graduation?
              </h3>
              <p className="text-[hsl(var(--bolt-text-secondary))]">
                Projects created on the Student plan are for academic use only. If you want to use them commercially, you'll need to upgrade to the Premium plan.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[hsl(var(--bolt-border))] mt-20">
        <div className="container mx-auto px-6 py-12">
          <div className="text-center text-[hsl(var(--bolt-text-secondary))] text-sm">
            © 2025 BharatBuild AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
