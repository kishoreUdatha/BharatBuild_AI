'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Check, X, Zap, Loader2, Crown, Star, Shield, Clock, Download, FileText, Code, Bug, Presentation, HelpCircle, Search } from 'lucide-react'
import { usePayment } from '@/hooks/usePayment'

export default function PricingPage() {
  const router = useRouter()
  const { initiatePayment, loading } = usePayment()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const handlePurchase = async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      router.push(`/login?redirect=/pricing&plan=premium`)
      return
    }

    setSuccessMessage(null)
    initiatePayment(
      'premium',
      (result) => {
        setSuccessMessage(`Payment successful! You now have access to 1 complete project.`)
        setTimeout(() => router.push('/build'), 2000)
      },
      () => {}
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
    { name: 'Bug Fixing', free: false, premium: 'Unlimited', icon: Bug },
    { name: 'SRS Document', free: false, premium: true, icon: FileText },
    { name: 'SDS Document', free: false, premium: true, icon: FileText },
    { name: 'Project Report (60-80 pages)', free: false, premium: true, icon: FileText },
    { name: 'PPT Presentation (15 slides)', free: false, premium: true, icon: Presentation },
    { name: 'Viva Q&A (50+ questions)', free: false, premium: true, icon: HelpCircle },
    { name: 'Plagiarism Check', free: false, premium: true, icon: Search },
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
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg">
          {successMessage}
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
                <span className="text-5xl font-bold text-white">₹4,499</span>
                <span className="text-gray-400 ml-2">one-time</span>
              </div>
              <p className="text-green-400 text-sm mb-8">
                1 month validity
              </p>

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

        {/* What You Get Section - Detailed by Category */}
        <div className="max-w-6xl mx-auto mb-20">
          <h2 className="text-3xl font-bold text-white text-center mb-4">
            What You Get with Premium
          </h2>
          <p className="text-gray-400 text-center mb-12">
            Everything you need for your final year project submission
          </p>

          {/* Code Generation Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Code className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Code Generation</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'Full working code for any project',
                'Web Apps (React, Next.js, Vue)',
                'Backend APIs (Node.js, Python, FastAPI)',
                'Full-Stack Applications',
                'Real-time code preview',
                'Live code editing',
                'Multiple file generation',
                'Folder structure creation',
                'Package.json & dependencies',
                'Database schema generation',
                'API endpoint generation',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bug Fixing Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Bug className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Bug Fixing</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'Unlimited automatic bug fixing',
                'AI-powered error detection',
                'Instant code fixes',
                'Syntax error correction',
                'Logic error detection',
                'Runtime error fixing',
                'Code optimization suggestions',
                'Security vulnerability detection',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Project Report Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Project Report (60-80 Pages)</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'Complete IEEE format documentation',
                'Title page with project details',
                'Certificate page',
                'Abstract (project summary)',
                'Table of contents',
                'Chapter 1: Introduction',
                'Chapter 2: Literature Review',
                'Chapter 3: System Requirements',
                'Chapter 4: System Design',
                'Chapter 5: Implementation',
                'Chapter 6: Testing & Results',
                'Chapter 7: Conclusion & Future Scope',
                'References (IEEE format)',
                'Appendix with code snippets',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* SRS Document Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">SRS Document (IEEE 830 Standard)</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'Functional requirements',
                'Non-functional requirements',
                'Use case diagrams',
                'Use case descriptions',
                'System requirements',
                'Hardware requirements',
                'Software requirements',
                'User requirements',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* SDS Document Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">SDS Document (Full Design)</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'System architecture',
                'High-level design (HLD)',
                'Low-level design (LLD)',
                'Class diagrams',
                'Sequence diagrams',
                'Activity diagrams',
                'ER diagrams',
                'Data flow diagrams (DFD)',
                'Component diagrams',
                'Database schema design',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* PPT Presentation Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Presentation className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">PPT Presentation (15 Slides)</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'Professional slide design',
                'Problem statement',
                'Objectives of the project',
                'System architecture slide',
                'Technology stack used',
                'Screenshots & demos',
                'Implementation details',
                'Testing results',
                'Conclusion slide',
                'Future enhancements',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Viva Q&A Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <HelpCircle className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Viva Q&A Preparation (50+ Questions)</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                '50+ potential viva questions',
                'Detailed answers for each question',
                'Project-specific questions',
                'Technology-related questions',
                'Implementation questions',
                'Design pattern questions',
                'Tips for viva presentation',
                'Common examiner questions',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Export & Download Section */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 mb-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Download className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white">Export & Download</h3>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                'Download complete project as ZIP',
                'Export directly to GitHub',
                'GitHub repository creation',
                'README.md generation',
                'Export documentation as PDF',
                'Export documentation as DOCX',
                'Export PPT as PPTX',
                '6 months access to download',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-gray-300">
                  <Check className="w-4 h-4 text-cyan-500 flex-shrink-0" />
                  <span className="text-sm">{item}</span>
                </div>
              ))}
            </div>
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
              <span>500+ Students Trust Us</span>
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
            ) : (
              <>
                <Crown className="w-5 h-5 mr-2" />
                Get Premium - ₹4,499
              </>
            )}
          </Button>
          <p className="text-gray-500 text-sm mt-4">
            One-time payment • No subscription • 6 months validity
          </p>
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
