'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Zap, ArrowLeft } from 'lucide-react'

export default function TermsPage() {
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
        <h1 className="text-4xl font-bold text-[hsl(var(--bolt-text-primary))] mb-8">Terms of Service</h1>

        <div className="prose prose-invert max-w-none space-y-8 text-[hsl(var(--bolt-text-secondary))]">
          <p className="text-lg">
            Last updated: January 2025
          </p>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">1. Acceptance of Terms</h2>
            <p>
              By accessing or using BharatBuild AI ("Service"), you agree to be bound by these Terms of Service ("Terms"). If you disagree with any part of the terms, you may not access the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">2. Description of Service</h2>
            <p>
              BharatBuild AI is an AI-powered platform that helps users generate:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Software project code and structure</li>
              <li>Academic documentation (project reports, SRS, etc.)</li>
              <li>Presentations and visual materials</li>
              <li>Viva preparation materials</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">3. User Accounts</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>You must provide accurate and complete information when creating an account</li>
              <li>You are responsible for maintaining the security of your account</li>
              <li>You must notify us immediately of any unauthorized access</li>
              <li>One account per person; account sharing is prohibited</li>
              <li>We reserve the right to suspend or terminate accounts that violate these terms</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">4. Token System and Payments</h2>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">4.1 Token Usage</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Tokens are required to use AI generation features</li>
              <li>Token consumption varies based on the complexity and length of generation</li>
              <li>Free tier tokens are provided for trial purposes</li>
              <li>Purchased tokens have validity periods as specified at purchase</li>
            </ul>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">4.2 Payments</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>All payments are processed securely through Razorpay</li>
              <li>Prices are in Indian Rupees (INR) unless otherwise stated</li>
              <li>All purchases are final and non-refundable</li>
              <li>Refunds may be considered on a case-by-case basis for technical issues</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">5. Acceptable Use</h2>
            <p>You agree NOT to use the Service to:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Generate content that infringes on intellectual property rights</li>
              <li>Create malicious software, malware, or security exploits</li>
              <li>Generate content that is illegal, harmful, or offensive</li>
              <li>Impersonate others or misrepresent your identity</li>
              <li>Attempt to bypass security measures or rate limits</li>
              <li>Resell or redistribute generated content as a competing service</li>
              <li>Use automated systems to abuse the service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">6. Academic Integrity</h2>
            <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4 mt-2">
              <p className="text-yellow-200 font-medium mb-2">Important Notice:</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Generated content is intended as a learning aid and starting point</li>
                <li>You are responsible for understanding and customizing the generated content</li>
                <li>Submitting AI-generated work without proper disclosure may violate your institution's academic integrity policy</li>
                <li>We recommend consulting your institution's guidelines on AI-assisted work</li>
                <li>BharatBuild AI is not responsible for academic consequences of misuse</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">7. Intellectual Property</h2>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">7.1 Your Content</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>You retain ownership of content you input into the Service</li>
              <li>You grant us a license to process your content for service delivery</li>
              <li>Generated code and documents belong to you</li>
            </ul>

            <h3 className="text-xl font-medium text-[hsl(var(--bolt-text-primary))] mt-4 mb-2">7.2 Our Content</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>The Service, including UI, branding, and features, is our property</li>
              <li>You may not copy, modify, or distribute our Service</li>
              <li>Generated content may include common patterns from training data</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">8. Disclaimers</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>The Service is provided "AS IS" without warranties of any kind</li>
              <li>AI-generated content may contain errors or inaccuracies</li>
              <li>We do not guarantee that generated code will work for your specific use case</li>
              <li>We are not responsible for any damages from using generated content</li>
              <li>Generated documentation should be reviewed and customized before submission</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">9. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, BharatBuild AI shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of profits or revenues, whether incurred directly or indirectly, or any loss of data, use, goodwill, or other intangible losses resulting from:
            </p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Your use or inability to use the Service</li>
              <li>Any unauthorized access to your account</li>
              <li>Any errors or inaccuracies in generated content</li>
              <li>Academic or professional consequences of content usage</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">10. Service Availability</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>We strive for high availability but do not guarantee uninterrupted service</li>
              <li>We may perform maintenance that temporarily affects availability</li>
              <li>We reserve the right to modify or discontinue features</li>
              <li>Token validity extensions may be provided for significant outages</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">11. Termination</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>You may delete your account at any time</li>
              <li>We may suspend or terminate accounts for violations of these Terms</li>
              <li>Upon termination, your access to the Service will cease</li>
              <li>You may export your projects before account deletion</li>
              <li>Unused tokens are not refundable upon termination</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">12. Governing Law</h2>
            <p>
              These Terms shall be governed by and construed in accordance with the laws of India. Any disputes shall be subject to the exclusive jurisdiction of courts in Hyderabad, Telangana, India.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">13. Changes to Terms</h2>
            <p>
              We reserve the right to modify these Terms at any time. We will notify users of significant changes via email or through the Service. Continued use after changes constitutes acceptance of the new Terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">14. Contact</h2>
            <p>For questions about these Terms, contact us at:</p>
            <ul className="list-disc pl-6 space-y-2 mt-2">
              <li>Email: legal@bharatbuild.ai</li>
              <li>Support: support@bharatbuild.ai</li>
            </ul>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[hsl(var(--bolt-border))] mt-12">
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-wrap justify-center gap-6 mb-4 text-sm text-[hsl(var(--bolt-text-secondary))]">
            <Link href="/privacy" className="hover:text-[hsl(var(--bolt-text-primary))]">Privacy Policy</Link>
            <Link href="/terms" className="text-[hsl(var(--bolt-text-primary))]">Terms of Service</Link>
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
