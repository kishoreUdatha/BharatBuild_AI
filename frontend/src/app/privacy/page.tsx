'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Zap, ArrowLeft } from 'lucide-react'

export default function PrivacyPage() {
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

          <Link href="/">
            <Button variant="outline" className="border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))]">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-6 py-12 max-w-4xl">
        <h1 className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))] mb-8">Privacy Policy</h1>

        <div className="prose prose-invert max-w-none space-y-8 text-[hsl(var(--bolt-text-secondary))]">
          <p className="text-lg">
            Last updated: January 2025
          </p>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">1. Introduction</h2>
            <p>
              BharatBuild AI ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our AI-powered project generation platform.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">2. Information We Collect</h2>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">2.1 Personal Information</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Name and email address (during registration)</li>
              <li>College/University name and department (optional)</li>
              <li>Payment information (processed securely via Razorpay)</li>
              <li>Profile information you choose to provide</li>
            </ul>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">2.2 Project Data</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Project names and descriptions you provide</li>
              <li>Code generated using our AI platform</li>
              <li>Documents created (reports, presentations, etc.)</li>
              <li>Chat conversations with our AI agents</li>
            </ul>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">2.3 Usage Information</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Token usage and transaction history</li>
              <li>Feature usage patterns</li>
              <li>Device and browser information</li>
              <li>IP address and location (country level)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">3. How We Use Your Information</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>To provide and maintain our services</li>
              <li>To process payments and manage your account</li>
              <li>To generate AI-powered code and documentation</li>
              <li>To improve our AI models and services</li>
              <li>To send important updates about your account</li>
              <li>To provide customer support</li>
              <li>To detect and prevent fraud or abuse</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">4. Data Storage and Security</h2>
            <p>
              We implement industry-standard security measures to protect your data:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>All data is encrypted in transit (TLS/SSL) and at rest</li>
              <li>Passwords are hashed using industry-standard algorithms</li>
              <li>Payment data is processed by Razorpay (PCI-DSS compliant)</li>
              <li>Regular security audits and vulnerability assessments</li>
              <li>Access controls and authentication for all systems</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">5. Data Sharing</h2>
            <p>We do not sell your personal information. We may share data with:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li><strong>AI Service Providers:</strong> Anthropic (Claude API) for AI generation - only the prompts and context needed for generation</li>
              <li><strong>Payment Processors:</strong> Razorpay for payment processing</li>
              <li><strong>Cloud Infrastructure:</strong> Hosting providers for data storage</li>
              <li><strong>Legal Requirements:</strong> When required by law or to protect rights</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">6. Your Rights</h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Delete your account and associated data</li>
              <li>Export your projects and documents</li>
              <li>Opt out of marketing communications</li>
              <li>Lodge a complaint with a supervisory authority</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">7. Data Retention</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Active account data is retained while your account is active</li>
              <li>Projects are retained for 30 days after deletion request</li>
              <li>Transaction records are retained for 7 years (legal requirement)</li>
              <li>You can request complete data deletion by contacting support</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">8. Cookies and Tracking</h2>
            <p>We use essential cookies for:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Authentication and session management</li>
              <li>Remembering your preferences</li>
              <li>Security and fraud prevention</li>
            </ul>
            <p className="mt-2">
              We do not use third-party advertising cookies or trackers.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">9. Children's Privacy</h2>
            <p>
              Our services are intended for users aged 16 and above. We do not knowingly collect personal information from children under 16. If you believe we have collected data from a child, please contact us immediately.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">10. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last updated" date. Continued use of our services after changes constitutes acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">11. Contact Us</h2>
            <p>If you have any questions about this Privacy Policy, please contact us:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Email: privacy@bharatbuild.ai</li>
              <li>Support: support@bharatbuild.ai</li>
            </ul>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[hsl(var(--bolt-border))] mt-12">
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-wrap justify-center gap-6 mb-4 text-sm text-[hsl(var(--bolt-text-secondary))]">
            <Link href="/privacy" className="text-[hsl(var(--bolt-text-primary))]">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-[hsl(var(--bolt-text-primary))]">Terms of Service</Link>
            <Link href="/pricing" className="hover:text-[hsl(var(--bolt-text-primary))]">Pricing</Link>
          </div>
          <div className="text-center text-[hsl(var(--bolt-text-secondary))] text-sm">
            © 2025 BharatBuild AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
