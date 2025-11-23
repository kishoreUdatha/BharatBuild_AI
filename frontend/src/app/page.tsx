'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ArrowRight, Code2, Zap, Globe } from 'lucide-react'
import { useState, useEffect } from 'react'

export default function Home() {
  const [placeholderIndex, setPlaceholderIndex] = useState(0)
  const placeholders = [
    'Build a React dashboard with TypeScript and Tailwind CSS',
    'Create a REST API with Node.js, Express and MongoDB',
    'Develop a full-stack Next.js app with authentication',
    'Build a Python Flask API with PostgreSQL database',
    'Create a Vue.js SPA with Vuex state management',
    'Develop a Django web app with user authentication',
    'Build a GraphQL API with Apollo Server and Prisma',
    'Create a microservices architecture with Docker and Kubernetes'
  ]

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((prev) => (prev + 1) % placeholders.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] relative overflow-hidden">
      {/* Gradient background effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-cyan-500/5" />

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
            <Link href="/pricing" className="text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors">
              Pricing
            </Link>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost" className="text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button className="bolt-gradient hover:opacity-90 transition-opacity">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10">
        <div className="container mx-auto px-6 py-20 md:py-32">
          <div className="text-center max-w-5xl mx-auto">
            {/* Main Heading */}
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 text-[hsl(var(--bolt-text-primary))]">
              What will you <span className="bolt-gradient-text">build</span> today?
            </h1>

            {/* Subheading */}
            <p className="text-lg md:text-xl text-[hsl(var(--bolt-text-secondary))] mb-8 max-w-3xl mx-auto">
              Create stunning apps & websites by chatting with AI
            </p>

            {/* Prompt Input */}
            <div className="max-w-3xl mx-auto mb-6">
              <div className="group relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition duration-200"></div>
                <div className="relative bg-[hsl(var(--bolt-bg-secondary))] border-2 border-[hsl(var(--bolt-border))] rounded-2xl p-2 hover:border-[hsl(var(--bolt-accent))] transition-all">
                  <form onSubmit={(e) => {
                    e.preventDefault()
                    const input = e.currentTarget.querySelector('input') as HTMLInputElement
                    const prompt = input.value.trim()
                    if (prompt) {
                      // Store the prompt in sessionStorage to pass to bolt page
                      sessionStorage.setItem('initialPrompt', prompt)
                      window.location.href = '/bolt'
                    }
                  }}>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder={placeholders[placeholderIndex]}
                        className="flex-1 bg-transparent border-none outline-none text-[hsl(var(--bolt-text-primary))] placeholder:text-[hsl(var(--bolt-text-secondary))] px-4 py-3 text-base transition-all duration-500"
                      />
                      <Button type="submit" className="bolt-gradient hover:opacity-90 transition-opacity px-6 py-3">
                        Start
                        <ArrowRight className="ml-2 w-4 h-4" />
                      </Button>
                    </div>
                  </form>
                </div>
              </div>
            </div>

            {/* Quick Examples */}
            <div className="flex flex-wrap gap-2 justify-center mb-12">
              <button
                onClick={() => {
                  sessionStorage.setItem('initialPrompt', 'Build a mobile app with React Native')
                  window.location.href = '/bolt'
                }}
                className="text-sm px-4 py-2 rounded-full bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:border-[hsl(var(--bolt-accent))] hover:text-[hsl(var(--bolt-text-primary))] transition-all"
              >
                📱 Mobile app
              </button>
              <button
                onClick={() => {
                  sessionStorage.setItem('initialPrompt', 'Create an e-commerce website with shopping cart')
                  window.location.href = '/bolt'
                }}
                className="text-sm px-4 py-2 rounded-full bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:border-[hsl(var(--bolt-accent))] hover:text-[hsl(var(--bolt-text-primary))] transition-all"
              >
                🛍️ E-commerce site
              </button>
              <button
                onClick={() => {
                  sessionStorage.setItem('initialPrompt', 'Build an analytics dashboard with charts')
                  window.location.href = '/bolt'
                }}
                className="text-sm px-4 py-2 rounded-full bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:border-[hsl(var(--bolt-accent))] hover:text-[hsl(var(--bolt-text-primary))] transition-all"
              >
                📊 Dashboard
              </button>
              <button
                onClick={() => {
                  sessionStorage.setItem('initialPrompt', 'Create a simple browser game')
                  window.location.href = '/bolt'
                }}
                className="text-sm px-4 py-2 rounded-full bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:border-[hsl(var(--bolt-accent))] hover:text-[hsl(var(--bolt-text-primary))] transition-all"
              >
                🎮 Game
              </button>
            </div>

          </div>
        </div>

        {/* Features Section */}
        <div className="container mx-auto px-6 py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-[hsl(var(--bolt-text-primary))] mb-4">
              Build faster with AI
            </h2>
            <p className="text-xl text-[hsl(var(--bolt-text-secondary))] max-w-2xl mx-auto">
              Everything you need to go from idea to deployed application
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Feature 1 */}
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
              <div className="relative bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8 hover:border-[hsl(var(--bolt-accent))] transition-all">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-6">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-3">
                  Lightning Fast
                </h3>
                <p className="text-[hsl(var(--bolt-text-secondary))] leading-relaxed">
                  Generate full-stack applications in seconds. No setup, no configuration - just describe what you want to build.
                </p>
              </div>
            </div>

            {/* Feature 2 */}
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
              <div className="relative bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8 hover:border-[hsl(var(--bolt-accent))] transition-all">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-6">
                  <Code2 className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-3">
                  Full Code Control
                </h3>
                <p className="text-[hsl(var(--bolt-text-secondary))] leading-relaxed">
                  Edit and refine generated code in real-time. Export your project anytime with full source code access.
                </p>
              </div>
            </div>

            {/* Feature 3 */}
            <div className="group relative">
              <div className="absolute inset-0 bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-2xl blur-xl group-hover:blur-2xl transition-all" />
              <div className="relative bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8 hover:border-[hsl(var(--bolt-accent))] transition-all">
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center mb-6">
                  <Globe className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-3">
                  Instant Deploy
                </h3>
                <p className="text-[hsl(var(--bolt-text-secondary))] leading-relaxed">
                  Deploy your application with a single click. Get a live URL instantly to share with the world.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Use Cases Section */}
        <div className="container mx-auto px-6 py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-[hsl(var(--bolt-text-primary))] mb-4">
              Built for everyone
            </h2>
            <p className="text-xl text-[hsl(var(--bolt-text-secondary))] max-w-2xl mx-auto">
              From students to founders, BharatBuild AI accelerates your development
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
            {[
              { title: 'Students', desc: 'Complete academic projects with documentation', icon: '🎓' },
              { title: 'Developers', desc: 'Prototype and build production apps faster', icon: '💻' },
              { title: 'Founders', desc: 'Validate ideas and build MVPs quickly', icon: '🚀' },
              { title: 'Teams', desc: 'Collaborate and ship features in hours', icon: '👥' },
            ].map((item, i) => (
              <div
                key={i}
                className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6 hover:border-[hsl(var(--bolt-accent))] transition-all cursor-pointer"
              >
                <div className="text-4xl mb-4">{item.icon}</div>
                <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                  {item.title}
                </h3>
                <p className="text-[hsl(var(--bolt-text-secondary))] text-sm">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Final CTA */}
        <div className="container mx-auto px-6 py-20">
          <div className="max-w-4xl mx-auto text-center bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-12">
            <h2 className="text-4xl md:text-5xl font-bold text-[hsl(var(--bolt-text-primary))] mb-6">
              Ready to build something amazing?
            </h2>
            <p className="text-xl text-[hsl(var(--bolt-text-secondary))] mb-8">
              Join thousands of developers building with AI
            </p>
            <div className="flex items-center justify-center gap-4">
              <Link href="/register">
                <Button size="lg" className="bolt-gradient hover:opacity-90 transition-opacity text-lg px-8 py-6 h-auto">
                  Start Building for Free
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <Link href="/login">
                <Button size="lg" variant="outline" className="text-lg px-8 py-6 h-auto border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))]">
                  Sign In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[hsl(var(--bolt-border))] mt-20">
        <div className="container mx-auto px-6 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <span className="font-bold text-lg text-[hsl(var(--bolt-text-primary))]">BharatBuild</span>
              </div>
              <p className="text-[hsl(var(--bolt-text-secondary))] text-sm">
                AI-powered development platform for the next generation
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">Product</h4>
              <ul className="space-y-2 text-[hsl(var(--bolt-text-secondary))] text-sm">
                <li><Link href="/features" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Features</Link></li>
                <li><Link href="/pricing" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Pricing</Link></li>
                <li><Link href="/docs" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Documentation</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">Company</h4>
              <ul className="space-y-2 text-[hsl(var(--bolt-text-secondary))] text-sm">
                <li><Link href="/about" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">About</Link></li>
                <li><Link href="/blog" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Blog</Link></li>
                <li><Link href="/contact" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Contact</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">Legal</h4>
              <ul className="space-y-2 text-[hsl(var(--bolt-text-secondary))] text-sm">
                <li><Link href="/privacy" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Privacy</Link></li>
                <li><Link href="/terms" className="hover:text-[hsl(var(--bolt-text-primary))] transition-colors">Terms</Link></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-[hsl(var(--bolt-border))] mt-12 pt-8 text-center text-[hsl(var(--bolt-text-secondary))] text-sm">
            © 2025 BharatBuild AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  )
}
