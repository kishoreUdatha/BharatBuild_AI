'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Clock, ArrowRight, Search, ArrowUpRight } from 'lucide-react'

const blogPosts = [
  {
    slug: 'react-vs-nextjs-which-to-choose-2025',
    title: 'React vs Next.js: Which Should You Learn in 2025?',
    excerpt: 'Complete comparison of React and Next.js. Learn the differences, use cases, and which framework is best for your project.',
    date: '2025-02-14',
    readTime: '10 min',
    category: 'Guide',
  },
  {
    slug: 'flutter-app-development-beginners-guide',
    title: 'Flutter App Development: Complete Beginner Guide 2025',
    excerpt: 'Learn Flutter from scratch. Build cross-platform mobile apps for iOS and Android with this comprehensive tutorial.',
    date: '2025-02-10',
    readTime: '15 min',
    category: 'Tutorial',
  },
  {
    slug: 'machine-learning-projects-for-students',
    title: 'Top 20 Machine Learning Projects for Students with Source Code',
    excerpt: 'Best ML projects for beginners and final year students. Includes Python source code, datasets, and step-by-step guides.',
    date: '2025-02-05',
    readTime: '18 min',
    category: 'Ideas',
  },
  {
    slug: 'how-to-write-srs-document',
    title: 'How to Write SRS Document: Software Requirements Specification Guide',
    excerpt: 'Complete guide to writing SRS documents. Learn IEEE format, sections, examples, and download free templates.',
    date: '2025-01-28',
    readTime: '12 min',
    category: 'Documentation',
  },
  {
    slug: 'best-tech-stack-for-web-development-2025',
    title: 'Best Tech Stack for Web Development in 2025: Complete Guide',
    excerpt: 'Compare MERN, MEAN, Next.js, Django, and more. Find the perfect tech stack for your web project.',
    date: '2025-01-20',
    readTime: '14 min',
    category: 'Guide',
  },
  {
    slug: 'complete-final-year-project-with-ai',
    title: 'How to Complete Your Final Year Project in 2 Days Using AI',
    excerpt: 'Learn how to generate complete final year projects with source code, documentation, PPT & viva Q&A using AI.',
    date: '2025-01-15',
    readTime: '8 min',
    category: 'Guide',
  },
  {
    slug: 'ieee-format-project-report-guide',
    title: 'IEEE Format Project Report: Complete Guide with Free Template',
    excerpt: 'Complete guide to writing IEEE format project reports. Learn structure, formatting rules, and download free templates.',
    date: '2025-01-10',
    readTime: '12 min',
    category: 'Documentation',
  },
  {
    slug: 'ai-code-generators-compared',
    title: 'AI Code Generators Compared: BharatBuild vs Bolt vs v0 vs Cursor',
    excerpt: 'Comprehensive comparison of AI code generators. Compare features, pricing, and capabilities.',
    date: '2025-01-05',
    readTime: '15 min',
    category: 'Comparison',
  },
  {
    slug: 'build-mvp-without-coding',
    title: 'Build Your MVP Without a Technical Co-founder',
    excerpt: 'Learn how to build your startup MVP without coding. Use AI tools to create production-ready products.',
    date: '2025-01-02',
    readTime: '10 min',
    category: 'Startup',
  },
  {
    slug: '50-final-year-project-ideas-cse',
    title: '50 Final Year Project Ideas for CSE Students (2025)',
    excerpt: 'Top 50 final year project ideas for CSE, IT, and computer science students with tech stack details.',
    date: '2025-01-01',
    readTime: '20 min',
    category: 'Ideas',
  },
]

const categories = ['All', 'Guide', 'Tutorial', 'Documentation', 'Comparison', 'Startup', 'Ideas']

export default function BlogPage() {
  const [activeCategory, setActiveCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredPosts = blogPosts.filter(post => {
    const matchesCategory = activeCategory === 'All' || post.category === activeCategory
    const matchesSearch = post.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         post.excerpt.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  const featuredPost = blogPosts[0]

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Header */}
      <header className="border-b border-white/10 sticky top-0 bg-[#0a0a0f]/90 backdrop-blur-md z-50">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-white font-bold text-sm">B</span>
              </div>
              <span className="font-semibold text-white">BharatBuild</span>
            </Link>

            <nav className="flex items-center gap-6">
              <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors">Home</Link>
              <Link href="/blog" className="text-sm text-white font-medium">Blog</Link>
              <Link href="/pricing" className="text-sm text-gray-400 hover:text-white transition-colors">Pricing</Link>
              <Link href="/build" className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                Get Started
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6">
        {/* Hero */}
        <section className="py-12 border-b border-white/10">
          <p className="text-sm font-medium text-blue-400 mb-2">Blog</p>
          <h1 className="text-3xl font-semibold text-white mb-3">
            Insights & Tutorials
          </h1>
          <p className="text-gray-400">
            Expert guides on AI development, project building, and tech careers.
          </p>
        </section>

        {/* Featured */}
        <section className="py-8 border-b border-white/10">
          <Link href={`/blog/${featuredPost.slug}`} className="group block">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-500/20">
                Featured
              </span>
              <span className="text-xs text-gray-500">
                {new Date(featuredPost.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
              {featuredPost.title}
            </h2>
            <p className="text-gray-400 text-sm mb-3">
              {featuredPost.excerpt}
            </p>
            <span className="inline-flex items-center gap-1 text-sm font-medium text-blue-400 group-hover:gap-2 transition-all">
              Read article
              <ArrowRight className="w-4 h-4" />
            </span>
          </Link>
        </section>

        {/* Search & Filter */}
        <section className="py-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
                className={`text-sm px-3 py-1.5 rounded-full whitespace-nowrap transition-all ${
                  activeCategory === category
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-56">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>
        </section>

        {/* Articles */}
        <section className="pb-16">
          <div className="divide-y divide-white/10">
            {filteredPosts.map((post) => (
              <Link href={`/blog/${post.slug}`} key={post.slug} className="group block py-5">
                <article className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-xs font-medium text-gray-500 bg-white/5 px-2 py-0.5 rounded">
                        {post.category}
                      </span>
                      <span className="text-xs text-gray-600 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {post.readTime}
                      </span>
                    </div>
                    <h3 className="text-base font-medium text-white mb-1 group-hover:text-blue-400 transition-colors">
                      {post.title}
                    </h3>
                    <p className="text-sm text-gray-500 line-clamp-1">
                      {post.excerpt}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-600">
                      {new Date(post.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                    <ArrowUpRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors" />
                  </div>
                </article>
              </Link>
            ))}
          </div>

          {filteredPosts.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No articles found.</p>
            </div>
          )}
        </section>

        {/* Newsletter */}
        <section className="py-8 border-t border-white/10">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold text-white mb-1">Stay updated</h3>
              <p className="text-sm text-gray-500">Get the latest articles in your inbox.</p>
            </div>
            <div className="flex items-center gap-2 w-full md:w-auto">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 md:w-56 px-4 py-2 text-sm bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500/50"
              />
              <button className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap">
                Subscribe
              </button>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-8 border-t border-white/10">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-semibold text-white mb-1">Ready to build?</h3>
              <p className="text-sm text-gray-500">Generate complete projects with AI. Start free.</p>
            </div>
            <Link
              href="/build"
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg hover:opacity-90 transition-opacity"
            >
              Start Building
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-8">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-white font-bold text-xs">B</span>
              </div>
              <span className="text-sm text-gray-500">© 2025 BharatBuild AI</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
              <Link href="/terms" className="hover:text-white transition-colors">Terms</Link>
              <Link href="/" className="hover:text-white transition-colors">Home</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
