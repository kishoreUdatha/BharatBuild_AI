'use client'

import { useState } from 'react'
import {
  Wrench,
  Plus,
  Palette,
  Shield,
  Database,
  Smartphone,
  Zap,
  FileText,
  Bug,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Sparkles
} from 'lucide-react'

interface QuickAction {
  id: string
  icon: React.ElementType
  label: string
  prompt: string
  category: 'fix' | 'add' | 'improve'
  color: string
}

const QUICK_ACTIONS: QuickAction[] = [
  // Fix Actions
  {
    id: 'fix-errors',
    icon: Bug,
    label: 'Fix All Errors',
    prompt: 'Fix all the errors in the project. Check the terminal and browser console for issues.',
    category: 'fix',
    color: 'from-red-500 to-orange-500'
  },
  {
    id: 'fix-styling',
    icon: Palette,
    label: 'Fix Styling',
    prompt: 'Fix the styling issues. Make sure the layout looks correct and responsive.',
    category: 'fix',
    color: 'from-pink-500 to-rose-500'
  },
  {
    id: 'fix-responsive',
    icon: Smartphone,
    label: 'Fix Mobile View',
    prompt: 'Fix the mobile responsiveness. Make sure it works well on small screens.',
    category: 'fix',
    color: 'from-blue-500 to-cyan-500'
  },

  // Add Features
  {
    id: 'add-auth',
    icon: Shield,
    label: 'Add Authentication',
    prompt: 'Add user authentication with login and signup forms. Include session management.',
    category: 'add',
    color: 'from-green-500 to-emerald-500'
  },
  {
    id: 'add-database',
    icon: Database,
    label: 'Add Database',
    prompt: 'Add database integration to persist data. Use appropriate storage for this project type.',
    category: 'add',
    color: 'from-purple-500 to-violet-500'
  },
  {
    id: 'add-darkmode',
    icon: Palette,
    label: 'Add Dark Mode',
    prompt: 'Add a dark mode toggle. Implement theme switching that persists user preference.',
    category: 'add',
    color: 'from-slate-500 to-gray-600'
  },
  {
    id: 'add-api',
    icon: Zap,
    label: 'Add API Integration',
    prompt: 'Add API integration for data fetching. Include loading states and error handling.',
    category: 'add',
    color: 'from-amber-500 to-yellow-500'
  },

  // Improve
  {
    id: 'improve-ui',
    icon: Sparkles,
    label: 'Improve UI',
    prompt: 'Improve the UI design. Make it more modern, add animations and better visual hierarchy.',
    category: 'improve',
    color: 'from-indigo-500 to-blue-500'
  },
  {
    id: 'add-docs',
    icon: FileText,
    label: 'Generate Docs',
    prompt: 'Generate documentation including README, API docs, and code comments.',
    category: 'improve',
    color: 'from-teal-500 to-cyan-500'
  },
  {
    id: 'optimize',
    icon: RefreshCw,
    label: 'Optimize Code',
    prompt: 'Optimize the code for better performance. Remove redundancy and improve efficiency.',
    category: 'improve',
    color: 'from-orange-500 to-red-500'
  }
]

interface QuickActionsProps {
  onAction: (prompt: string) => void
  hasProject: boolean
  isLoading?: boolean
}

/**
 * Quick Action Buttons - Helps users fix/add features easily
 * Only shows when there's an existing project
 */
export function QuickActions({ onAction, hasProject, isLoading }: QuickActionsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [activeCategory, setActiveCategory] = useState<'all' | 'fix' | 'add' | 'improve'>('all')

  if (!hasProject) return null

  const filteredActions = activeCategory === 'all'
    ? QUICK_ACTIONS
    : QUICK_ACTIONS.filter(a => a.category === activeCategory)

  const visibleActions = isExpanded ? filteredActions : filteredActions.slice(0, 4)

  return (
    <div className="px-4 py-3 border-t border-white/10 bg-[#0d0d12]">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Wrench className="w-4 h-4 text-white/40" />
            <span className="text-xs font-medium text-white/50">Quick Actions</span>
          </div>

          {/* Category Tabs */}
          <div className="flex items-center gap-1">
            {(['all', 'fix', 'add', 'improve'] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
                  activeCategory === cat
                    ? 'bg-white/10 text-white'
                    : 'text-white/40 hover:text-white/60'
                }`}
              >
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Action Buttons Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {visibleActions.map((action) => {
            const Icon = action.icon
            return (
              <button
                key={action.id}
                onClick={() => onAction(action.prompt)}
                disabled={isLoading}
                className={`group relative flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {/* Icon with gradient */}
                <div className={`flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center`}>
                  <Icon className="w-3.5 h-3.5 text-white" />
                </div>

                {/* Label */}
                <span className="text-xs font-medium text-white/70 group-hover:text-white/90 truncate">
                  {action.label}
                </span>
              </button>
            )
          })}
        </div>

        {/* Expand/Collapse */}
        {filteredActions.length > 4 && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center justify-center gap-1 w-full mt-2 py-1.5 text-xs text-white/40 hover:text-white/60 transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" />
                Show Less
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" />
                Show More ({filteredActions.length - 4} more)
              </>
            )}
          </button>
        )}

        {/* Custom Action Hint */}
        <p className="text-center text-[10px] text-white/30 mt-2">
          Or type your own request: "Add a contact form" • "Fix the navbar" • "Make it faster"
        </p>
      </div>
    </div>
  )
}

export default QuickActions
