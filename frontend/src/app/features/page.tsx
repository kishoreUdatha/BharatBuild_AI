import type { Metadata } from 'next'
import Link from 'next/link'
import {
  Zap, Code, FileText, Presentation, MessageSquare, Bug, Download,
  Globe, Smartphone, Database, Shield, Clock, Users, Sparkles,
  GitBranch, Eye, Cpu, Layers, Terminal, BookOpen, CheckCircle,
  ArrowRight, Star, Rocket, Brain, Settings, RefreshCw
} from 'lucide-react'

export const metadata: Metadata = {
  title: 'Features - AI Code Generator, Documentation & Project Builder',
  description: 'Explore BharatBuild AI features: 31 AI agents, auto code generation, bug fixing, IEEE documentation, PPT slides, viva Q&A, live preview, and more. Build complete projects in minutes.',
  keywords: [
    'AI code generator features',
    'automatic documentation generator',
    'project report generator',
    'PPT generator AI',
    'viva questions generator',
    'bug fixing AI',
    'live code preview',
    'React project generator',
    'Next.js generator',
    'Flutter app builder',
    'full stack project generator',
    'IEEE documentation',
    'SRS document generator',
    'final year project features'
  ],
  openGraph: {
    title: 'BharatBuild AI Features - Complete Project Generation Platform',
    description: 'Discover all features: AI code generation, documentation, PPT, viva Q&A, bug fixing, and more.',
    url: 'https://bharatbuild.ai/features',
    images: [{ url: '/og-features.png', width: 1200, height: 630 }],
  },
  alternates: {
    canonical: 'https://bharatbuild.ai/features',
  },
}

const aiAgents = [
  { name: 'Planner Agent', description: 'Creates project structure and architecture', icon: Layers },
  { name: 'Coder Agent', description: 'Writes production-ready code', icon: Code },
  { name: 'Fixer Agent', description: 'Automatically fixes bugs and errors', icon: Bug },
  { name: 'Documenter Agent', description: 'Generates IEEE-format documentation', icon: FileText },
  { name: 'PPT Agent', description: 'Creates presentation slides', icon: Presentation },
  { name: 'Viva Agent', description: 'Generates Q&A for project defense', icon: MessageSquare },
  { name: 'Reviewer Agent', description: 'Reviews code quality and best practices', icon: Eye },
  { name: 'Optimizer Agent', description: 'Optimizes performance and efficiency', icon: Zap },
  { name: 'Security Agent', description: 'Checks for vulnerabilities', icon: Shield },
  { name: 'Database Agent', description: 'Designs schemas and queries', icon: Database },
  { name: 'API Agent', description: 'Creates RESTful endpoints', icon: Globe },
  { name: 'UI Agent', description: 'Builds responsive interfaces', icon: Smartphone },
]

const coreFeatures = [
  {
    title: 'AI Code Generation',
    description: 'Generate complete, production-ready code from natural language descriptions. Support for 50+ tech stacks including React, Next.js, Node.js, Python, Flutter, and more.',
    icon: Code,
    highlights: ['50+ Tech Stacks', 'Production Ready', 'Best Practices'],
  },
  {
    title: 'Automatic Bug Fixing',
    description: 'Our AI automatically detects and fixes bugs in your generated code. Unlimited iterations until your code works perfectly.',
    icon: Bug,
    highlights: ['Auto Detection', 'Unlimited Fixes', 'Error Explanation'],
  },
  {
    title: 'IEEE Documentation',
    description: 'Generate comprehensive project documentation including SRS, SDS, and project reports up to 80 pages following IEEE standards.',
    icon: FileText,
    highlights: ['60-80 Pages', 'IEEE Format', 'Academic Ready'],
  },
  {
    title: 'PPT Presentation',
    description: 'Create professional presentation slides automatically. Perfect for project submissions and viva presentations.',
    icon: Presentation,
    highlights: ['15-20 Slides', 'Professional Design', 'Editable'],
  },
  {
    title: 'Viva Q&A Generator',
    description: 'Prepare for your project defense with 50+ potential questions and detailed answers covering all aspects of your project.',
    icon: MessageSquare,
    highlights: ['50+ Questions', 'Detailed Answers', 'Topic-wise'],
  },
  {
    title: 'Live Code Preview',
    description: 'See your project running in real-time with our built-in sandbox. Test features and interactions before downloading.',
    icon: Eye,
    highlights: ['Real-time Preview', 'Interactive Testing', 'Instant Updates'],
  },
]

const techStacks = [
  { name: 'React', category: 'Frontend' },
  { name: 'Next.js', category: 'Frontend' },
  { name: 'Vue.js', category: 'Frontend' },
  { name: 'Angular', category: 'Frontend' },
  { name: 'Node.js', category: 'Backend' },
  { name: 'Python', category: 'Backend' },
  { name: 'FastAPI', category: 'Backend' },
  { name: 'Django', category: 'Backend' },
  { name: 'Flutter', category: 'Mobile' },
  { name: 'React Native', category: 'Mobile' },
  { name: 'PostgreSQL', category: 'Database' },
  { name: 'MongoDB', category: 'Database' },
]

const benefits = [
  { title: 'Save 100+ Hours', description: 'Complete projects in minutes instead of weeks', icon: Clock },
  { title: 'No Coding Required', description: 'Describe your project in plain English', icon: Brain },
  { title: 'Production Ready', description: 'Get deployable code with best practices', icon: Rocket },
  { title: 'Academic Standard', description: 'Documentation follows IEEE guidelines', icon: BookOpen },
  { title: 'Team Collaboration', description: 'Work with up to 3 team members', icon: Users },
  { title: 'Unlimited Revisions', description: 'Edit and regenerate until perfect', icon: RefreshCw },
]

export default function FeaturesPage() {
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
            <Link href="/features" className="text-white font-medium">Features</Link>
            <Link href="/pricing" className="text-gray-400 hover:text-white transition-colors">Pricing</Link>
            <Link href="/blog" className="text-gray-400 hover:text-white transition-colors">Blog</Link>
          </nav>
          <Link href="/build">
            <button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white px-6 py-2 rounded-lg font-medium shadow-lg shadow-blue-500/25 transition-all">
              Start Building
            </button>
          </Link>
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section className="container mx-auto px-6 py-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/30 mb-6">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-blue-300">Powered by Advanced AI</span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 text-white">
            Build Complete Projects with{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
              AI-Powered Features
            </span>
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto mb-10">
            31 specialized AI agents work together to generate code, fix bugs, create documentation,
            PPT presentations, and prepare you for viva - all in minutes.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/build">
              <button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white px-8 py-4 rounded-xl font-semibold text-lg shadow-lg shadow-blue-500/25 transition-all flex items-center gap-2">
                Try Free Now
                <ArrowRight className="w-5 h-5" />
              </button>
            </Link>
            <Link href="/pricing">
              <button className="border border-white/20 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-white/5 transition-all">
                View Pricing
              </button>
            </Link>
          </div>
        </section>

        {/* Core Features Grid */}
        <section className="container mx-auto px-6 py-20">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Everything You Need for Your Project
            </h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              From code generation to viva preparation - we've got you covered
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {coreFeatures.map((feature, index) => (
              <div
                key={index}
                className="bg-[#111118] rounded-2xl border border-white/10 p-8 hover:border-blue-500/50 transition-all group"
              >
                <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center mb-6 group-hover:from-blue-500/30 group-hover:to-cyan-500/30 transition-all">
                  <feature.icon className="w-7 h-7 text-blue-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
                <p className="text-gray-400 mb-6">{feature.description}</p>
                <div className="flex flex-wrap gap-2">
                  {feature.highlights.map((highlight, i) => (
                    <span
                      key={i}
                      className="text-xs px-3 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20"
                    >
                      {highlight}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* AI Agents Section */}
        <section className="container mx-auto px-6 py-20">
          <div className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-3xl border border-blue-500/20 p-12">
            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/20 border border-blue-500/30 mb-4">
                <Cpu className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-blue-300">31 Specialized AI Agents</span>
              </div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Meet Your AI Development Team
              </h2>
              <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                Each agent is specialized for a specific task, working together to deliver perfect results
              </p>
            </div>
            <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-6">
              {aiAgents.map((agent, index) => (
                <div
                  key={index}
                  className="bg-[#0a0a0f]/50 rounded-xl p-5 border border-white/5 hover:border-blue-500/30 transition-all"
                >
                  <agent.icon className="w-8 h-8 text-cyan-400 mb-3" />
                  <h4 className="font-semibold text-white mb-1">{agent.name}</h4>
                  <p className="text-sm text-gray-500">{agent.description}</p>
                </div>
              ))}
            </div>
            <p className="text-center text-gray-500 mt-8">
              + 19 more specialized agents for testing, deployment, optimization, and more
            </p>
          </div>
        </section>

        {/* Tech Stacks */}
        <section className="container mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              50+ Technology Stacks Supported
            </h2>
            <p className="text-gray-400 text-lg">
              Generate projects in any modern technology
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-4 max-w-4xl mx-auto">
            {techStacks.map((tech, index) => (
              <div
                key={index}
                className="px-6 py-3 rounded-xl bg-[#111118] border border-white/10 hover:border-cyan-500/50 transition-all"
              >
                <span className="text-white font-medium">{tech.name}</span>
                <span className="text-gray-500 text-sm ml-2">({tech.category})</span>
              </div>
            ))}
            <div className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/30">
              <span className="text-blue-300 font-medium">+ 38 more...</span>
            </div>
          </div>
        </section>

        {/* Benefits Grid */}
        <section className="container mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Why Students Choose BharatBuild
            </h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {benefits.map((benefit, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-6 rounded-xl bg-[#111118] border border-white/10"
              >
                <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <benefit.icon className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <h4 className="font-semibold text-white mb-1">{benefit.title}</h4>
                  <p className="text-sm text-gray-500">{benefit.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* How It Works */}
        <section className="container mx-auto px-6 py-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              How It Works
            </h2>
            <p className="text-gray-400 text-lg">
              Get your complete project in 4 simple steps
            </p>
          </div>
          <div className="grid md:grid-cols-4 gap-8 max-w-5xl mx-auto">
            {[
              { step: '1', title: 'Describe', desc: 'Tell us about your project in plain English' },
              { step: '2', title: 'Generate', desc: 'AI agents build your complete project' },
              { step: '3', title: 'Preview', desc: 'See your project running live' },
              { step: '4', title: 'Download', desc: 'Get code, docs, PPT & viva Q&A' },
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-white">
                  {item.step}
                </div>
                <h4 className="font-semibold text-white mb-2">{item.title}</h4>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA Section */}
        <section className="container mx-auto px-6 py-20">
          <div className="bg-gradient-to-r from-blue-600 to-cyan-600 rounded-3xl p-12 text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to Build Your Project?
            </h2>
            <p className="text-blue-100 text-lg mb-8 max-w-2xl mx-auto">
              Join 10,000+ students who have successfully completed their projects with BharatBuild AI
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link href="/build">
                <button className="bg-white text-blue-600 px-8 py-4 rounded-xl font-semibold text-lg hover:bg-blue-50 transition-all flex items-center gap-2">
                  Start Free Trial
                  <ArrowRight className="w-5 h-5" />
                </button>
              </Link>
              <Link href="/pricing">
                <button className="border-2 border-white text-white px-8 py-4 rounded-xl font-semibold text-lg hover:bg-white/10 transition-all">
                  View Pricing
                </button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10">
        <div className="container mx-auto px-6 py-12">
          <div className="flex flex-wrap justify-center gap-6 mb-6 text-sm text-gray-500">
            <Link href="/features" className="hover:text-white transition-colors">Features</Link>
            <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
            <Link href="/blog" className="hover:text-white transition-colors">Blog</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
          </div>
          <div className="text-center text-gray-600 text-sm">
            © 2025 BharatBuild AI. All rights reserved. Made with ❤️ in India
          </div>
        </div>
      </footer>
    </div>
  )
}
