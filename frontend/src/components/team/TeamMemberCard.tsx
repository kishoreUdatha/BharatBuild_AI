'use client'

import { useState } from 'react'
import {
  Crown,
  Code2,
  Eye,
  MoreVertical,
  Mail,
  Trash2,
  UserMinus,
  Shield,
  Clock,
  CheckCircle2,
  Circle
} from 'lucide-react'
import type { TeamMember as TeamMemberType, MemberSkill } from '@/types/team'

// Allow both the strict type and a more flexible local type
type TeamMemberLike = TeamMemberType | {
  id: string
  name?: string
  email?: string
  avatar?: string
  role: string
  status?: string
  currentTask?: string
  tasksCompleted?: number
  totalTasks?: number
  user_name?: string
  user_email?: string
  user_avatar?: string
  user_id?: string
  team_id?: string
  joined_at?: string
  is_active?: boolean
  skills?: MemberSkill[]
  current_task?: string
  tasks_completed?: number
  total_tasks?: number
}

interface TeamMemberCardProps {
  member: TeamMemberLike
  isCurrentUser?: boolean
  isLeader?: boolean
  onRemove?: (memberId: string) => void
  onChangeRole?: (memberId: string, role: 'member' | 'viewer') => void
}

export function TeamMemberCard({
  member,
  isCurrentUser = false,
  isLeader = false,
  onRemove,
  onChangeRole
}: TeamMemberCardProps) {
  const [showMenu, setShowMenu] = useState(false)

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500'
      case 'coding':
        return 'bg-blue-500'
      case 'offline':
      default:
        return 'bg-gray-500'
    }
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'leader':
        return <Crown className="w-4 h-4 text-yellow-500" />
      case 'member':
        return <Code2 className="w-4 h-4 text-blue-400" />
      case 'viewer':
        return <Eye className="w-4 h-4 text-gray-400" />
      default:
        return null
    }
  }

  const getInitials = (name?: string, email?: string) => {
    const displayName = name || email || 'U'
    return displayName.substring(0, 2).toUpperCase()
  }

  // Support both old (name/email) and new (user_name/user_email) property names
  const memberName = (member as any).user_name || (member as any).name
  const memberEmail = (member as any).user_email || (member as any).email
  const memberAvatar = (member as any).user_avatar || (member as any).avatar
  const memberStatus = (member as any).status
  const memberCurrentTask = (member as any).current_task || (member as any).currentTask
  const memberTasksCompleted = (member as any).tasks_completed ?? (member as any).tasksCompleted
  const memberTotalTasks = (member as any).total_tasks ?? (member as any).totalTasks
  const memberSkills = (member as any).skills

  const displayName = memberName || memberEmail?.split('@')[0] || 'Team Member'

  return (
    <div className="relative p-4 rounded-xl border border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] hover:border-[hsl(var(--bolt-accent))]/50 transition-all">
      {/* Status Badge */}
      <div className="absolute top-3 right-3 flex items-center gap-2">
        {member.role === 'leader' && (
          <div className="flex items-center gap-1 px-2 py-0.5 bg-yellow-500/10 text-yellow-500 rounded-full text-xs font-medium">
            <Crown className="w-3 h-3" />
            Leader
          </div>
        )}
        {isLeader && !isCurrentUser && (
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
          >
            <MoreVertical className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
          </button>
        )}

        {/* Dropdown Menu */}
        {showMenu && (
          <div className="absolute top-8 right-0 z-10 w-48 py-1 bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] rounded-lg shadow-xl">
            {member.role !== 'viewer' && (
              <button
                onClick={() => {
                  onChangeRole?.(member.id, 'viewer')
                  setShowMenu(false)
                }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))]"
              >
                <Eye className="w-4 h-4" />
                Change to Viewer
              </button>
            )}
            {member.role !== 'member' && member.role !== 'leader' && (
              <button
                onClick={() => {
                  onChangeRole?.(member.id, 'member')
                  setShowMenu(false)
                }}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))]"
              >
                <Code2 className="w-4 h-4" />
                Change to Member
              </button>
            )}
            <button
              onClick={() => {
                onRemove?.(member.id)
                setShowMenu(false)
              }}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-400 hover:bg-[hsl(var(--bolt-bg-secondary))]"
            >
              <UserMinus className="w-4 h-4" />
              Remove from Team
            </button>
          </div>
        )}
      </div>

      {/* Avatar & Basic Info */}
      <div className="flex items-start gap-3 mb-4">
        <div className="relative">
          {memberAvatar ? (
            <img
              src={memberAvatar}
              alt={displayName}
              className="w-12 h-12 rounded-full"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-bold">
              {getInitials(memberName, memberEmail)}
            </div>
          )}
          {/* Online Status Indicator */}
          <div
            className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-[hsl(var(--bolt-bg-secondary))] ${getStatusColor(memberStatus)}`}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-[hsl(var(--bolt-text-primary))] truncate">
              {displayName}
              {isCurrentUser && (
                <span className="text-xs text-[hsl(var(--bolt-text-secondary))] ml-1">(You)</span>
              )}
            </h3>
          </div>
          <div className="flex items-center gap-1 text-sm text-[hsl(var(--bolt-text-secondary))]">
            {getRoleIcon(member.role)}
            <span className="capitalize">{member.role}</span>
          </div>
        </div>
      </div>

      {/* Current Task */}
      {memberCurrentTask && (
        <div className="mb-3 p-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
          <div className="text-xs text-[hsl(var(--bolt-text-secondary))] mb-1">Working on:</div>
          <div className="text-sm text-[hsl(var(--bolt-text-primary))] font-medium truncate">
            {memberCurrentTask}
          </div>
        </div>
      )}

      {/* Skills */}
      {memberSkills && memberSkills.length > 0 && (
        <div className="mb-3">
          <div className="flex flex-wrap gap-1">
            {memberSkills.slice(0, 4).map((skill: MemberSkill, index: number) => (
              <span
                key={index}
                className={`px-2 py-0.5 text-xs rounded-full ${
                  skill.is_primary
                    ? 'bg-[hsl(var(--bolt-accent))]/10 text-[hsl(var(--bolt-accent))]'
                    : 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))]'
                }`}
              >
                {skill.skill_name}
              </span>
            ))}
            {memberSkills.length > 4 && (
              <span className="px-2 py-0.5 text-xs bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] rounded-full">
                +{memberSkills.length - 4}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Task Progress */}
      {(memberTasksCompleted !== undefined || memberTotalTasks !== undefined) && (
        <div className="pt-3 border-t border-[hsl(var(--bolt-border))]">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--bolt-text-secondary))]">Tasks</span>
            <span className="text-[hsl(var(--bolt-text-primary))] font-medium">
              {memberTasksCompleted || 0}/{memberTotalTasks || 0}
            </span>
          </div>
          <div className="mt-2 w-full h-1.5 bg-[hsl(var(--bolt-bg-primary))] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
              style={{
                width: `${memberTotalTasks ? ((memberTasksCompleted || 0) / memberTotalTasks) * 100 : 0}%`
              }}
            />
          </div>
        </div>
      )}

      {/* Email */}
      {memberEmail && (
        <div className="mt-3 flex items-center gap-2 text-xs text-[hsl(var(--bolt-text-secondary))]">
          <Mail className="w-3 h-3" />
          <span className="truncate">{memberEmail}</span>
        </div>
      )}
    </div>
  )
}
