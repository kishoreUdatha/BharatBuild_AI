'use client'

import { useState } from 'react'
import {
  Sparkles,
  Code2,
  Smartphone,
  Brain,
  ShoppingCart,
  FileText,
  Gamepad2,
  Globe,
  Rocket,
  Zap
} from 'lucide-react'

interface WelcomeScreenProps {
  onExampleClick: (example: string) => void
}

const EXAMPLE_PROMPTS = [
  {
    icon: ShoppingCart,
    title: "E-commerce Store",
    prompt: "Build a modern e-commerce store with product catalog, cart, and checkout",
    gradient: "from-orange-500 to-pink-500"
  },
  {
    icon: Code2,
    title: "Portfolio Website",
    prompt: "Create a stunning developer portfolio with projects showcase and contact form",
    gradient: "from-blue-500 to-cyan-500"
  },
  {
    icon: Smartphone,
    title: "Task Manager App",
    prompt: "Build a beautiful task management app with drag-and-drop and categories",
    gradient: "from-green-500 to-emerald-500"
  },
  {
    icon: Brain,
    title: "AI Chat Interface",
    prompt: "Create a ChatGPT-like interface with streaming responses and markdown support",
    gradient: "from-purple-500 to-violet-500"
  },
  {
    icon: FileText,
    title: "Student Project + Docs",
    prompt: "Generate a complete student project with SRS, UML diagrams, and documentation",
    gradient: "from-amber-500 to-yellow-500"
  },
  {
    icon: Globe,
    title: "Social Dashboard",
    prompt: "Build a social media analytics dashboard with charts and real-time updates",
    gradient: "from-rose-500 to-red-500"
  }
]

/**
 * Bolt.new-style welcome screen
 * Shows when chat is empty - animated, inspiring design
 */
export function WelcomeScreen({ onExampleClick }: WelcomeScreenProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  return (
    <div className="h-full flex flex-col items-center justify-center px-6 py-12 overflow-y-auto">
      {/* Animated Background Orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-3xl w-full text-center">
        {/* Logo */}
        <div className="flex items-center justify-center mb-6">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-2xl shadow-violet-500/25">
              <Zap className="w-10 h-10 text-white" />
            </div>
            <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-green-500 border-4 border-[#0a0a0f] flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          <span className="bg-gradient-to-r from-white via-white to-white/60 bg-clip-text text-transparent">
            What do you want to
          </span>
          <br />
          <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
            build today?
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-white/50 text-lg mb-10 max-w-xl mx-auto">
          Describe your project and watch AI build it in real-time.
          Complete code, beautiful UI, ready to deploy.
        </p>

        {/* Example Prompts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {EXAMPLE_PROMPTS.map((example, index) => {
            const Icon = example.icon
            const isHovered = hoveredIndex === index

            return (
              <button
                key={index}
                onClick={() => onExampleClick(example.prompt)}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
                className={`group relative p-4 rounded-xl border text-left transition-all duration-300 ${
                  isHovered
                    ? 'bg-white/5 border-white/20 scale-[1.02]'
                    : 'bg-white/[0.02] border-white/10 hover:bg-white/5'
                }`}
              >
                {/* Gradient Glow on Hover */}
                {isHovered && (
                  <div className={`absolute inset-0 rounded-xl bg-gradient-to-br ${example.gradient} opacity-10 blur-xl`} />
                )}

                <div className="relative z-10 flex items-start gap-3">
                  {/* Icon */}
                  <div className={`flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br ${example.gradient} flex items-center justify-center shadow-lg`}>
                    <Icon className="w-5 h-5 text-white" />
                  </div>

                  {/* Text */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-white mb-1 truncate">
                      {example.title}
                    </h3>
                    <p className="text-xs text-white/40 line-clamp-2">
                      {example.prompt}
                    </p>
                  </div>
                </div>

                {/* Arrow on Hover */}
                <div className={`absolute right-3 top-1/2 -translate-y-1/2 transition-all duration-300 ${
                  isHovered ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-2'
                }`}>
                  <Rocket className="w-4 h-4 text-white/40" />
                </div>
              </button>
            )
          })}
        </div>

        {/* Bottom Hint */}
        <p className="mt-8 text-sm text-white/30">
          Or just start typing your own idea below
        </p>
      </div>
    </div>
  )
}

export default WelcomeScreen
