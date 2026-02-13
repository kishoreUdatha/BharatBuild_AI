'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  Zap, Search, Smartphone, Rocket, Globe,
  ShoppingCart, BarChart3, MessageSquare, Music, Utensils,
  Star, Sparkles, Layers, Play, ExternalLink, GraduationCap
} from 'lucide-react'

const DEMO_PROJECTS = [
  {
    id: 'lp-1',
    title: 'SaaS Landing Page',
    description: 'Modern SaaS product landing with animations, pricing tables, and testimonials',
    category: 'Landing Pages',
    tech: ['Next.js', 'Tailwind', 'Framer Motion'],
    icon: Globe,
    gradient: 'from-violet-600 via-blue-600 to-cyan-500',
    featured: true
  },
  {
    id: 'aa-1',
    title: 'E-Commerce Store',
    description: 'Full-featured online store with cart, checkout, and product catalog',
    category: 'Advanced Apps',
    tech: ['Next.js', 'Stripe', 'PostgreSQL'],
    icon: ShoppingCart,
    gradient: 'from-emerald-500 via-green-500 to-teal-500',
    featured: true
  },
  {
    id: 'aa-2',
    title: 'Project Management',
    description: 'Trello-style kanban boards with drag-drop, teams, and task management',
    category: 'Advanced Apps',
    tech: ['React', 'Node.js', 'MongoDB'],
    icon: BarChart3,
    gradient: 'from-blue-600 via-indigo-600 to-purple-600',
    featured: true
  },
  {
    id: 'lp-2',
    title: 'Restaurant Website',
    description: 'Beautiful restaurant site with online menu, reservations and gallery',
    category: 'Landing Pages',
    tech: ['Next.js', 'Tailwind CSS'],
    icon: Utensils,
    gradient: 'from-orange-500 via-red-500 to-pink-500'
  },
  {
    id: 'aa-3',
    title: 'Real-time Chat',
    description: 'WhatsApp-style messaging with real-time updates and conversations',
    category: 'Advanced Apps',
    tech: ['React', 'Socket.io', 'Firebase'],
    icon: MessageSquare,
    gradient: 'from-green-500 via-emerald-500 to-teal-500'
  },
  {
    id: 'ma-2',
    title: 'Music Player',
    description: 'Spotify-inspired music player with playlists and beautiful UI',
    category: 'Mobile Apps',
    tech: ['React Native', 'Expo'],
    icon: Music,
    gradient: 'from-purple-600 via-pink-600 to-rose-500'
  },
]

const CATEGORIES = [
  { id: 'all', label: 'All Projects', icon: Layers, count: DEMO_PROJECTS.length },
  { id: 'Landing Pages', label: 'Landing Pages', icon: Globe, count: 2 },
  { id: 'Advanced Apps', label: 'Full-Stack Apps', icon: Rocket, count: 3 },
  { id: 'Mobile Apps', label: 'Mobile Apps', icon: Smartphone, count: 1 },
]

export default function ShowcasePage() {
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')

  const filtered = DEMO_PROJECTS.filter(p => {
    const matchCat = category === 'all' || p.category === category
    const matchSearch = p.title.toLowerCase().includes(search.toLowerCase()) || p.description.toLowerCase().includes(search.toLowerCase())
    return matchCat && matchSearch
  })

  const featured = DEMO_PROJECTS.filter(p => p.featured)

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-white">BharatBuild</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/learn" className="text-purple-400 hover:text-purple-300 transition-colors font-medium">
              Prompt Course
            </Link>
            <Link href="/docs" className="text-slate-400 hover:text-white transition-colors font-medium">
              How It Works
            </Link>
            <Link href="/login" className="text-slate-400 hover:text-white transition-colors font-medium">
              Sign In
            </Link>
            <Link href="/build">
              <Button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:opacity-90 shadow-lg shadow-blue-500/20">
                Start Building
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative py-16 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-600/10 via-transparent to-transparent" />
        <div className="absolute top-20 left-1/4 w-72 h-72 bg-blue-500/20 rounded-full blur-[100px]" />
        <div className="absolute top-40 right-1/4 w-72 h-72 bg-cyan-500/20 rounded-full blur-[100px]" />

        <div className="relative max-w-7xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full text-blue-400 text-sm mb-6">
            <Sparkles className="w-4 h-4" />
            <span>Explore {DEMO_PROJECTS.length}+ Live Interactive Demos</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold text-white mb-6">
            Project <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Showcase</span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-8">
            Click on any project to experience fully interactive live demos. See how your project could look!
          </p>

          {/* Search */}
          <div className="max-w-xl mx-auto">
            <div className="relative">
              <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search projects..."
                className="w-full pl-14 pr-6 py-4 bg-slate-800/50 border border-slate-700 rounded-2xl text-white placeholder:text-slate-500 outline-none focus:border-blue-500 transition-colors"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Featured Section */}
      {category === 'all' && !search && (
        <section className="max-w-7xl mx-auto px-6 mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <Star className="w-6 h-6 text-amber-400 fill-amber-400" /> Featured Demos
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {featured.map((project) => {
              const IconComponent = project.icon
              return (
                <div
                  key={project.id}
                  className="group relative bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-slate-600 transition-all duration-300"
                >
                  <div className={`h-48 bg-gradient-to-br ${project.gradient} flex items-center justify-center relative`}>
                    <IconComponent className="w-16 h-16 text-white/30" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                      <Link
                        href={`/showcase/demo/${project.id}`}
                        className="px-6 py-3 bg-white rounded-xl text-slate-900 font-semibold flex items-center gap-2 hover:scale-105 transition-transform"
                      >
                        <Play className="w-5 h-5" /> Open Live Demo
                      </Link>
                    </div>
                  </div>
                  <div className="p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-1 bg-amber-500/20 text-amber-400 text-xs rounded-lg font-medium">Featured</span>
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">{project.title}</h3>
                    <p className="text-sm text-slate-400 mb-4">{project.description}</p>
                    <div className="flex flex-wrap gap-2">
                      {project.tech.map((t, j) => (
                        <span key={j} className="px-2.5 py-1 bg-slate-800 text-slate-400 text-xs rounded-lg">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Categories */}
      <section className="max-w-7xl mx-auto px-6 mb-8">
        <div className="flex gap-3 overflow-x-auto pb-4">
          {CATEGORIES.map((cat) => {
            const CatIcon = cat.icon
            return (
              <button
                key={cat.id}
                onClick={() => setCategory(cat.id)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl whitespace-nowrap transition-all ${
                  category === cat.id
                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg'
                    : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                <CatIcon className="w-4 h-4" />
                {cat.label}
                <span className={`text-xs px-2 py-0.5 rounded-full ${category === cat.id ? 'bg-white/20' : 'bg-slate-700'}`}>
                  {cat.count}
                </span>
              </button>
            )
          })}
        </div>
      </section>

      {/* All Projects Grid */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <h2 className="text-xl font-bold text-white mb-6">
          {category === 'all' ? 'All Demo Projects' : category} ({filtered.length})
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filtered.map((project) => {
            const IconComponent = project.icon
            return (
              <div
                key={project.id}
                className="group bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-slate-600 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/5"
              >
                <div className={`h-36 bg-gradient-to-br ${project.gradient} flex items-center justify-center relative`}>
                  <IconComponent className="w-12 h-12 text-white/30" />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                    <Link
                      href={`/showcase/demo/${project.id}`}
                      className="px-4 py-2 bg-white rounded-lg text-slate-900 font-medium flex items-center gap-2 text-sm hover:scale-105 transition-transform"
                    >
                      <Play className="w-4 h-4" /> Live Demo
                    </Link>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-white mb-1 group-hover:text-blue-400 transition-colors">{project.title}</h3>
                  <p className="text-sm text-slate-500 line-clamp-2 mb-3">{project.description}</p>
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {project.tech.slice(0, 2).map((t, j) => (
                      <span key={j} className="px-2 py-1 bg-slate-800 text-slate-500 text-xs rounded-md">{t}</span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/showcase/demo/${project.id}`} className="flex-1">
                      <button className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl text-white text-sm font-medium transition-colors flex items-center justify-center gap-2">
                        <ExternalLink className="w-4 h-4" /> Demo
                      </button>
                    </Link>
                    <Link href="/build" className="flex-1">
                      <button className="w-full py-2.5 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl text-white text-sm font-medium hover:opacity-90 transition-opacity">
                        Build
                      </button>
                    </Link>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-20">
            <div className="w-20 h-20 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">No projects found</h3>
            <p className="text-slate-500">Try adjusting your search or filter</p>
          </div>
        )}
      </section>
    </div>
  )
}
