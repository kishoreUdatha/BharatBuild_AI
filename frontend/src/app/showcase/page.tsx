'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Zap, ExternalLink, Github, Star, Code, Globe, Smartphone, Database, Search, Filter } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Project {
  id: string
  title: string
  description: string
  category: string
  tech: string[]
  image: string
  stars: number
  author: string
  demoUrl?: string
  githubUrl?: string
}

const showcaseProjects: Project[] = [
  {
    id: '1',
    title: 'E-Commerce Platform',
    description: 'Full-stack e-commerce solution with payment integration, inventory management, and admin dashboard.',
    category: 'Web App',
    tech: ['Next.js', 'TypeScript', 'PostgreSQL', 'Stripe'],
    image: '/showcase/ecommerce.png',
    stars: 245,
    author: 'Rahul S.',
  },
  {
    id: '2',
    title: 'Hospital Management System',
    description: 'Complete HMS with patient records, appointment scheduling, billing, and pharmacy management.',
    category: 'Enterprise',
    tech: ['React', 'Node.js', 'MongoDB', 'Express'],
    image: '/showcase/hospital.png',
    stars: 189,
    author: 'Priya M.',
  },
  {
    id: '3',
    title: 'Food Delivery App',
    description: 'Flutter-based food delivery app with real-time tracking, payments, and restaurant dashboard.',
    category: 'Mobile App',
    tech: ['Flutter', 'Firebase', 'Dart', 'Google Maps'],
    image: '/showcase/food-delivery.png',
    stars: 312,
    author: 'Amit K.',
  },
  {
    id: '4',
    title: 'Learning Management System',
    description: 'Online learning platform with video courses, quizzes, certificates, and progress tracking.',
    category: 'Web App',
    tech: ['Django', 'Python', 'PostgreSQL', 'Redis'],
    image: '/showcase/lms.png',
    stars: 156,
    author: 'Sneha R.',
  },
  {
    id: '5',
    title: 'Inventory Management',
    description: 'Warehouse inventory system with barcode scanning, stock alerts, and analytics dashboard.',
    category: 'Enterprise',
    tech: ['React', 'FastAPI', 'Python', 'MySQL'],
    image: '/showcase/inventory.png',
    stars: 98,
    author: 'Vikram P.',
  },
  {
    id: '6',
    title: 'Social Media Dashboard',
    description: 'Analytics dashboard for social media management with scheduling and engagement metrics.',
    category: 'Web App',
    tech: ['Vue.js', 'Node.js', 'MongoDB', 'Chart.js'],
    image: '/showcase/social.png',
    stars: 203,
    author: 'Neha T.',
  },
  {
    id: '7',
    title: 'Fitness Tracker App',
    description: 'Mobile fitness app with workout plans, calorie tracking, and progress visualization.',
    category: 'Mobile App',
    tech: ['React Native', 'Firebase', 'TypeScript'],
    image: '/showcase/fitness.png',
    stars: 178,
    author: 'Karan J.',
  },
  {
    id: '8',
    title: 'Real Estate Portal',
    description: 'Property listing platform with virtual tours, mortgage calculator, and agent management.',
    category: 'Web App',
    tech: ['Next.js', 'Prisma', 'PostgreSQL', 'Tailwind'],
    image: '/showcase/realestate.png',
    stars: 134,
    author: 'Divya S.',
  },
]

const categories = ['All', 'Web App', 'Mobile App', 'Enterprise', 'API']

export default function ShowcasePage() {
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredProjects = showcaseProjects.filter(project => {
    const matchesCategory = selectedCategory === 'All' || project.category === selectedCategory
    const matchesSearch = project.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         project.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         project.tech.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesCategory && matchesSearch
  })

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
            <Link href="/showcase" className="text-white font-medium">Showcase</Link>
            <Link href="/pricing" className="text-gray-400 hover:text-white transition-colors">Pricing</Link>
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
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 text-white">
            Project Showcase
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Explore amazing projects built with BharatBuild AI by students and developers across India.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          <div className="bg-[#111118] rounded-xl border border-white/10 p-6 text-center">
            <div className="text-3xl font-bold text-white mb-1">10,000+</div>
            <div className="text-gray-400 text-sm">Projects Built</div>
          </div>
          <div className="bg-[#111118] rounded-xl border border-white/10 p-6 text-center">
            <div className="text-3xl font-bold text-white mb-1">5,000+</div>
            <div className="text-gray-400 text-sm">Happy Students</div>
          </div>
          <div className="bg-[#111118] rounded-xl border border-white/10 p-6 text-center">
            <div className="text-3xl font-bold text-white mb-1">500+</div>
            <div className="text-gray-400 text-sm">Colleges</div>
          </div>
          <div className="bg-[#111118] rounded-xl border border-white/10 p-6 text-center">
            <div className="text-3xl font-bold text-white mb-1">50+</div>
            <div className="text-gray-400 text-sm">Technologies</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              placeholder="Search projects, technologies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-xl bg-[#111118] border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          {/* Category Filter */}
          <div className="flex gap-2 flex-wrap">
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedCategory === category
                    ? 'bg-blue-500 text-white'
                    : 'bg-[#111118] border border-white/10 text-gray-400 hover:text-white hover:border-white/20'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* Projects Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map(project => (
            <div
              key={project.id}
              className="bg-[#111118] rounded-2xl border border-white/10 overflow-hidden hover:border-blue-500/50 transition-all group"
            >
              {/* Project Image Placeholder */}
              <div className="h-48 bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                {project.category === 'Mobile App' ? (
                  <Smartphone className="w-16 h-16 text-blue-400/50" />
                ) : project.category === 'Enterprise' ? (
                  <Database className="w-16 h-16 text-blue-400/50" />
                ) : (
                  <Globe className="w-16 h-16 text-blue-400/50" />
                )}
              </div>

              <div className="p-6">
                {/* Category Badge */}
                <div className="flex items-center justify-between mb-3">
                  <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs font-medium">
                    {project.category}
                  </span>
                  <div className="flex items-center gap-1 text-yellow-400">
                    <Star className="w-4 h-4 fill-current" />
                    <span className="text-sm">{project.stars}</span>
                  </div>
                </div>

                {/* Title & Description */}
                <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
                  {project.title}
                </h3>
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">
                  {project.description}
                </p>

                {/* Tech Stack */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {project.tech.slice(0, 3).map(tech => (
                    <span
                      key={tech}
                      className="px-2 py-1 rounded bg-white/5 text-gray-300 text-xs"
                    >
                      {tech}
                    </span>
                  ))}
                  {project.tech.length > 3 && (
                    <span className="px-2 py-1 rounded bg-white/5 text-gray-500 text-xs">
                      +{project.tech.length - 3}
                    </span>
                  )}
                </div>

                {/* Author & Actions */}
                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                  <span className="text-gray-500 text-sm">by {project.author}</span>
                  <div className="flex gap-2">
                    <button className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
                      <Code className="w-4 h-4" />
                    </button>
                    <button className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {filteredProjects.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-full bg-gray-800 flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-gray-600" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">No projects found</h3>
            <p className="text-gray-400">Try adjusting your search or filter criteria</p>
          </div>
        )}

        {/* CTA Section */}
        <div className="mt-16 text-center">
          <div className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-2xl border border-blue-500/20 p-12">
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Build Your Project?
            </h2>
            <p className="text-gray-400 mb-8 max-w-xl mx-auto">
              Join thousands of students and developers who have built amazing projects with BharatBuild AI.
            </p>
            <Link href="/build">
              <Button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white px-8 py-3 text-lg shadow-lg shadow-blue-500/25">
                Start Building Now
              </Button>
            </Link>
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
              <Link href="/contact" className="hover:text-white transition-colors">Contact</Link>
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
