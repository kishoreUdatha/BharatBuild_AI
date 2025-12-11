'use client'

import { useRouter } from 'next/navigation'
import {
  Plus,
  FolderKanban,
  FileText,
  Sparkles,
  Coins
} from 'lucide-react'

interface QuickActionsBarProps {
  onCreateProject?: () => void
}

export function QuickActionsBar({ onCreateProject }: QuickActionsBarProps) {
  const router = useRouter()

  const actions = [
    {
      icon: Plus,
      label: 'New Project',
      description: 'Create a new project',
      onClick: () => onCreateProject ? onCreateProject() : router.push('/bolt'),
      primary: true
    },
    {
      icon: FolderKanban,
      label: 'All Projects',
      description: 'View all your projects',
      onClick: () => router.push('/projects')
    },
    {
      icon: Sparkles,
      label: 'AI Workspace',
      description: 'Open AI-powered IDE',
      onClick: () => router.push('/bolt')
    },
    {
      icon: Coins,
      label: 'Buy Tokens',
      description: 'Purchase more tokens',
      onClick: () => router.push('/pricing')
    }
  ]

  return (
    <div className="flex flex-wrap gap-3">
      {actions.map((action) => (
        <button
          key={action.label}
          onClick={action.onClick}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all ${
            action.primary
              ? 'bg-gradient-to-r from-blue-600 to-cyan-600 border-transparent text-white hover:from-blue-500 hover:to-cyan-500 shadow-lg shadow-blue-500/20'
              : 'bg-[#1a1a1a] border-[#333] text-gray-300 hover:bg-[#252525] hover:border-[#444]'
          }`}
        >
          <action.icon className={`h-4 w-4 ${action.primary ? '' : 'text-blue-400'}`} />
          <span className="font-medium text-sm">{action.label}</span>
        </button>
      ))}
    </div>
  )
}
