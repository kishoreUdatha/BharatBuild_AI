'use client'

import Link from 'next/link'
import { Mail, Phone, MapPin, Zap, MessageSquare, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function ContactPage() {
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
            <Link href="/pricing" className="text-gray-400 hover:text-white transition-colors">Pricing</Link>
            <Link href="/contact" className="text-white font-medium">Contact</Link>
          </nav>
          <Link href="/build">
            <Button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white shadow-lg shadow-blue-500/25">
              Start Building
            </Button>
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-6 py-16">
        {/* Hero */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 text-white">
            Get in Touch
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Have questions about BharatBuild AI? We're here to help you build amazing projects.
          </p>
        </div>

        {/* Contact Cards */}
        <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-8 mb-16">
          {/* Email Card */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 hover:border-blue-500/50 transition-all">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center mb-6">
              <Mail className="w-7 h-7 text-blue-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Email Us</h3>
            <p className="text-gray-400 mb-4">For general inquiries and support</p>
            <a
              href="mailto:support@bharatbuild.ai"
              className="text-blue-400 hover:text-blue-300 font-medium transition-colors"
            >
              support@bharatbuild.ai
            </a>
          </div>

          {/* Response Time Card */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 hover:border-blue-500/50 transition-all">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center mb-6">
              <Clock className="w-7 h-7 text-green-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Response Time</h3>
            <p className="text-gray-400 mb-4">We typically respond within</p>
            <span className="text-green-400 font-medium">24-48 hours</span>
          </div>

          {/* Phone Card */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 hover:border-blue-500/50 transition-all">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center mb-6">
              <Phone className="w-7 h-7 text-purple-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Call Us</h3>
            <p className="text-gray-400 mb-4">Monday to Friday, 10AM - 6PM IST</p>
            <a
              href="tel:+919876543210"
              className="text-purple-400 hover:text-purple-300 font-medium transition-colors"
            >
              +91 98765 43210
            </a>
          </div>

          {/* Location Card */}
          <div className="bg-[#111118] rounded-2xl border border-white/10 p-8 hover:border-blue-500/50 transition-all">
            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-orange-500/20 to-red-500/20 flex items-center justify-center mb-6">
              <MapPin className="w-7 h-7 text-orange-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Location</h3>
            <p className="text-gray-400 mb-4">Based in India</p>
            <span className="text-orange-400 font-medium">Hyderabad, Telangana</span>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-8">
            Frequently Asked Questions
          </h2>

          <div className="space-y-4">
            <div className="bg-[#111118] rounded-xl border border-white/10 p-6">
              <h3 className="text-lg font-medium text-white mb-2">
                How do I get started with BharatBuild AI?
              </h3>
              <p className="text-gray-400">
                Simply sign up for a free account, describe your project idea, and our AI will generate a complete project for you. You can preview files for free before purchasing.
              </p>
            </div>

            <div className="bg-[#111118] rounded-xl border border-white/10 p-6">
              <h3 className="text-lg font-medium text-white mb-2">
                What's included in the Premium package?
              </h3>
              <p className="text-gray-400">
                The Premium package includes 1 complete project with full working code, project report (60-80 pages), SRS & SDS documents, PPT presentation, viva Q&A, and unlimited bug fixing for 1 month.
              </p>
            </div>

            <div className="bg-[#111118] rounded-xl border border-white/10 p-6">
              <h3 className="text-lg font-medium text-white mb-2">
                Can I get a refund if I'm not satisfied?
              </h3>
              <p className="text-gray-400">
                Yes, we offer a satisfaction guarantee. If you're not happy with the generated project, contact us within 7 days for a full refund.
              </p>
            </div>

            <div className="bg-[#111118] rounded-xl border border-white/10 p-6">
              <h3 className="text-lg font-medium text-white mb-2">
                Do you offer custom enterprise solutions?
              </h3>
              <p className="text-gray-400">
                Yes! For colleges, institutions, and enterprises, we offer custom solutions with bulk pricing and dedicated support. Email us at support@bharatbuild.ai for more details.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-20">
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-blue-400" />
              <span className="text-gray-400">BharatBuild AI</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
              <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
              <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
            </div>
            <p className="text-gray-500 text-sm">
              &copy; {new Date().getFullYear()} BharatBuild AI. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
