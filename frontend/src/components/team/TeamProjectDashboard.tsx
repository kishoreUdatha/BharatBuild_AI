'use client'

import { useState } from 'react'
import {
  Users,
  Plus,
  Settings,
  Code2,
  CheckCircle2,
  Clock,
  AlertCircle,
  UserPlus,
  Sparkles,
  GitBranch,
  Play,
  Eye,
  ChevronRight,
  Crown,
  Zap
} from 'lucide-react'
import { TeamTaskBoard } from './TeamTaskBoard'
import { TeamMemberCard } from './TeamMemberCard'
import { TaskSplitPanel } from './TaskSplitPanel'

export interface TeamMember {
  id: string
  name: string
  email: string
  avatar?: string
  role: 'owner' | 'member'
  status: 'online' | 'offline' | 'coding'
  currentTask?: string
  tasksCompleted: number
  totalTasks: number
}

export interface TeamTask {
  id: string
  title: string
  description: string
  assignee?: TeamMember
  status: 'todo' | 'in_progress' | 'review' | 'done'
  priority: 'low' | 'medium' | 'high'
  files: string[]
  estimatedTime?: string
  aiGenerated: boolean
}

interface TeamProjectDashboardProps {
  projectId: string
  projectName: string
  projectDescription: string
}

export function TeamProjectDashboard({
  projectId,
  projectName,
  projectDescription
}: TeamProjectDashboardProps) {
  const [activeTab, setActiveTab] = useState<'board' | 'split' | 'members'>('board')
  const [showInviteModal, setShowInviteModal] = useState(false)

  // Mock data - replace with real API data
  const [teamMembers] = useState<TeamMember[]>([
    {
      id: '1',
      name: 'Rahul Kumar',
      email: 'rahul@college.edu',
      role: 'owner',
      status: 'coding',
      currentTask: 'User Authentication',
      tasksCompleted: 3,
      totalTasks: 5
    },
    {
      id: '2',
      name: 'Priya Sharma',
      email: 'priya@college.edu',
      role: 'member',
      status: 'online',
      currentTask: 'Product Catalog',
      tasksCompleted: 2,
      totalTasks: 4
    },
    {
      id: '3',
      name: 'Amit Patel',
      email: 'amit@college.edu',
      role: 'member',
      status: 'offline',
      tasksCompleted: 1,
      totalTasks: 3
    }
  ])

  const [tasks] = useState<TeamTask[]>([
    {
      id: '1',
      title: 'User Authentication',
      description: 'Implement login, register, and password reset functionality',
      assignee: teamMembers[0],
      status: 'in_progress',
      priority: 'high',
      files: ['src/auth/login.tsx', 'src/auth/register.tsx', 'src/context/AuthContext.tsx'],
      estimatedTime: '2 hours',
      aiGenerated: true
    },
    {
      id: '2',
      title: 'Product Catalog',
      description: 'Create product listing page with filters and search',
      assignee: teamMembers[1],
      status: 'in_progress',
      priority: 'medium',
      files: ['src/pages/products.tsx', 'src/components/ProductCard.tsx'],
      estimatedTime: '3 hours',
      aiGenerated: true
    },
    {
      id: '3',
      title: 'Shopping Cart',
      description: 'Build cart functionality with add/remove items',
      assignee: teamMembers[2],
      status: 'todo',
      priority: 'medium',
      files: ['src/pages/cart.tsx', 'src/store/cartStore.ts'],
      estimatedTime: '2 hours',
      aiGenerated: true
    },
    {
      id: '4',
      title: 'Checkout Flow',
      description: 'Payment integration and order confirmation',
      status: 'todo',
      priority: 'high',
      files: ['src/pages/checkout.tsx', 'src/api/payment.ts'],
      estimatedTime: '4 hours',
      aiGenerated: true
    },
    {
      id: '5',
      title: 'API Integration',
      description: 'Connect frontend with backend APIs',
      status: 'review',
      priority: 'high',
      files: ['src/api/index.ts', 'src/hooks/useApi.ts'],
      estimatedTime: '2 hours',
      aiGenerated: false
    }
  ])

  const completedTasks = tasks.filter(t => t.status === 'done').length
  const totalTasks = tasks.length
  const progress = Math.round((completedTasks / totalTasks) * 100)

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Users className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[hsl(var(--bolt-text-primary))]">
                  {projectName}
                </h1>
                <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Team Project • {teamMembers.length} members
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Progress Bar */}
              <div className="hidden md:flex items-center gap-3 px-4 py-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
                <div className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Progress
                </div>
                <div className="w-32 h-2 bg-[hsl(var(--bolt-bg-primary))] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                  {progress}%
                </div>
              </div>

              {/* Invite Button */}
              <button
                onClick={() => setShowInviteModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-[hsl(var(--bolt-accent))] text-white rounded-lg hover:bg-[hsl(var(--bolt-accent-hover))] transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                <span className="hidden sm:inline">Invite</span>
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 mt-4">
            <button
              onClick={() => setActiveTab('board')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'board'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
              }`}
            >
              <GitBranch className="w-4 h-4" />
              Task Board
            </button>
            <button
              onClick={() => setActiveTab('split')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'split'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              AI Task Split
            </button>
            <button
              onClick={() => setActiveTab('members')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'members'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
              }`}
            >
              <Users className="w-4 h-4" />
              Team ({teamMembers.length})
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'board' && (
          <TeamTaskBoard tasks={tasks} teamMembers={teamMembers} />
        )}
        {activeTab === 'split' && (
          <TaskSplitPanel
            projectDescription={projectDescription}
            teamMembers={teamMembers}
          />
        )}
        {activeTab === 'members' && (
          <div className="p-6 overflow-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {teamMembers.map((member) => (
                <TeamMemberCard key={member.id} member={member} />
              ))}

              {/* Add Member Card */}
              <button
                onClick={() => setShowInviteModal(true)}
                className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border-2 border-dashed border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-all"
              >
                <div className="w-12 h-12 rounded-full bg-[hsl(var(--bolt-bg-secondary))] flex items-center justify-center">
                  <Plus className="w-6 h-6 text-[hsl(var(--bolt-text-secondary))]" />
                </div>
                <span className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
                  Add Team Member
                </span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <InviteModal onClose={() => setShowInviteModal(false)} />
      )}
    </div>
  )
}

function InviteModal({ onClose }: { onClose: () => void }) {
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'member' | 'viewer'>('member')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-[hsl(var(--bolt-bg-secondary))] rounded-2xl border border-[hsl(var(--bolt-border))] shadow-2xl">
        <div className="p-6 border-b border-[hsl(var(--bolt-border))]">
          <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
            Invite Team Member
          </h2>
          <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">
            Add a student to collaborate on this project
          </p>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="student@college.edu"
              className="w-full px-4 py-3 bg-[hsl(var(--bolt-bg-primary))] border border-[hsl(var(--bolt-border))] rounded-lg text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--bolt-accent))]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
              Role
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setRole('member')}
                className={`flex items-center gap-2 p-3 rounded-lg border transition-all ${
                  role === 'member'
                    ? 'border-[hsl(var(--bolt-accent))] bg-[hsl(var(--bolt-accent))]/10'
                    : 'border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))]'
                }`}
              >
                <Code2 className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                <div className="text-left">
                  <div className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                    Member
                  </div>
                  <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                    Can code & edit
                  </div>
                </div>
              </button>
              <button
                onClick={() => setRole('viewer')}
                className={`flex items-center gap-2 p-3 rounded-lg border transition-all ${
                  role === 'viewer'
                    ? 'border-[hsl(var(--bolt-accent))] bg-[hsl(var(--bolt-accent))]/10'
                    : 'border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))]'
                }`}
              >
                <Eye className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                <div className="text-left">
                  <div className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                    Viewer
                  </div>
                  <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                    View only
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-[hsl(var(--bolt-border))] flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              // TODO: Send invite
              onClose()
            }}
            className="px-4 py-2 bg-[hsl(var(--bolt-accent))] text-white text-sm font-medium rounded-lg hover:bg-[hsl(var(--bolt-accent-hover))] transition-colors"
          >
            Send Invite
          </button>
        </div>
      </div>
    </div>
  )
}
