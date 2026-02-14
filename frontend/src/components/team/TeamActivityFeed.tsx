'use client'

import { useState } from 'react'
import {
  Users,
  UserPlus,
  UserMinus,
  CheckCircle2,
  ListTodo,
  FileCode2,
  GitMerge,
  MessageSquare,
  Code2,
  Flag,
  Clock,
  Filter,
  Loader2,
  RefreshCw
} from 'lucide-react'
import { useTeamActivities } from '@/hooks/useTeam'
import type { TeamActivity, ActivityType } from '@/types/team'

interface TeamActivityFeedProps {
  teamId: string
}

const activityConfig: Record<ActivityType, { icon: any; color: string; bgColor: string }> = {
  team_created: { icon: Users, color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  member_joined: { icon: UserPlus, color: 'text-green-400', bgColor: 'bg-green-500/10' },
  member_left: { icon: UserMinus, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10' },
  member_removed: { icon: UserMinus, color: 'text-red-400', bgColor: 'bg-red-500/10' },
  task_created: { icon: ListTodo, color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  task_updated: { icon: ListTodo, color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  task_assigned: { icon: Users, color: 'text-cyan-400', bgColor: 'bg-cyan-500/10' },
  task_completed: { icon: CheckCircle2, color: 'text-green-400', bgColor: 'bg-green-500/10' },
  task_commented: { icon: MessageSquare, color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  file_created: { icon: FileCode2, color: 'text-emerald-400', bgColor: 'bg-emerald-500/10' },
  file_modified: { icon: FileCode2, color: 'text-orange-400', bgColor: 'bg-orange-500/10' },
  file_deleted: { icon: FileCode2, color: 'text-red-400', bgColor: 'bg-red-500/10' },
  code_merged: { icon: GitMerge, color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  review_requested: { icon: Code2, color: 'text-yellow-400', bgColor: 'bg-yellow-500/10' },
  review_completed: { icon: Code2, color: 'text-green-400', bgColor: 'bg-green-500/10' },
  milestone_created: { icon: Flag, color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  milestone_completed: { icon: Flag, color: 'text-green-400', bgColor: 'bg-green-500/10' },
  chat_message: { icon: MessageSquare, color: 'text-gray-400', bgColor: 'bg-gray-500/10' }
}

const activityFilters = [
  { value: '', label: 'All Activity' },
  { value: 'task', label: 'Tasks' },
  { value: 'member', label: 'Members' },
  { value: 'file', label: 'Files' },
  { value: 'review', label: 'Reviews' },
  { value: 'milestone', label: 'Milestones' }
]

export function TeamActivityFeed({ teamId }: TeamActivityFeedProps) {
  const [filter, setFilter] = useState('')
  const [limit, setLimit] = useState(50)

  const { activities, isLoading, refresh } = useTeamActivities(teamId, {
    limit,
    activity_type: filter || undefined
  })

  // Group activities by date
  const groupedActivities: { date: string; activities: TeamActivity[] }[] = []
  let currentDate = ''

  activities.forEach((activity) => {
    const activityDate = new Date(activity.created_at).toDateString()
    if (activityDate !== currentDate) {
      currentDate = activityDate
      groupedActivities.push({ date: activityDate, activities: [activity] })
    } else {
      groupedActivities[groupedActivities.length - 1].activities.push(activity)
    }
  })

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const yesterday = new Date(now)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === now.toDateString()) {
      return 'Today'
    }
    if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday'
    }
    return date.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-[hsl(var(--bolt-text-primary))]">
              Activity Feed
            </h2>
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              Track what's happening in your team
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="px-3 py-1.5 bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] rounded-lg text-sm text-[hsl(var(--bolt-text-primary))]"
              >
                {activityFilters.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Refresh */}
            <button
              onClick={() => refresh()}
              disabled={isLoading}
              className="p-2 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg transition-colors"
            >
              <RefreshCw
                className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] ${isLoading ? 'animate-spin' : ''}`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Activity List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading && activities.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--bolt-accent))]" />
          </div>
        ) : activities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="w-16 h-16 rounded-full bg-[hsl(var(--bolt-bg-tertiary))] flex items-center justify-center mb-4">
              <Clock className="w-8 h-8 text-[hsl(var(--bolt-text-secondary))]" />
            </div>
            <h3 className="text-lg font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
              No activity yet
            </h3>
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              Activity will appear here as your team works on the project
            </p>
          </div>
        ) : (
          <div className="p-6">
            {groupedActivities.map((group, groupIndex) => (
              <div key={groupIndex} className="mb-8">
                {/* Date Header */}
                <div className="flex items-center gap-4 mb-4">
                  <div className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
                    {formatDate(group.date)}
                  </div>
                  <div className="flex-1 h-px bg-[hsl(var(--bolt-border))]" />
                </div>

                {/* Activities */}
                <div className="relative">
                  {/* Timeline line */}
                  <div className="absolute left-4 top-0 bottom-0 w-px bg-[hsl(var(--bolt-border))]" />

                  <div className="space-y-4">
                    {group.activities.map((activity) => (
                      <ActivityItem
                        key={activity.id}
                        activity={activity}
                        formatTime={formatTime}
                      />
                    ))}
                  </div>
                </div>
              </div>
            ))}

            {/* Load More */}
            {activities.length >= limit && (
              <div className="flex justify-center mt-6">
                <button
                  onClick={() => setLimit((prev) => prev + 50)}
                  className="px-4 py-2 text-sm text-[hsl(var(--bolt-accent))] hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg transition-colors"
                >
                  Load more
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Activity Item Component
function ActivityItem({
  activity,
  formatTime
}: {
  activity: TeamActivity
  formatTime: (date: string) => string
}) {
  const config = activityConfig[activity.activity_type] || {
    icon: Clock,
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/10'
  }
  const Icon = config.icon

  return (
    <div className="relative flex gap-4 pl-8">
      {/* Icon */}
      <div
        className={`absolute left-0 w-8 h-8 rounded-full ${config.bgColor} flex items-center justify-center z-10`}
      >
        <Icon className={`w-4 h-4 ${config.color}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 bg-[hsl(var(--bolt-bg-secondary))] rounded-xl p-4 ml-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Actor */}
            {activity.actor_name && (
              <div className="flex items-center gap-2 mb-1">
                <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
                  {activity.actor_name.charAt(0)}
                </div>
                <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                  {activity.actor_name}
                </span>
              </div>
            )}

            {/* Description */}
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              {activity.description}
            </p>

            {/* Activity Data */}
            {activity.activity_data && Object.keys(activity.activity_data).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {activity.activity_data.task_title && (
                  <span className="px-2 py-0.5 bg-[hsl(var(--bolt-bg-tertiary))] rounded text-xs text-[hsl(var(--bolt-text-secondary))]">
                    {activity.activity_data.task_title}
                  </span>
                )}
                {activity.activity_data.file_path && (
                  <span className="px-2 py-0.5 bg-[hsl(var(--bolt-bg-tertiary))] rounded text-xs text-[hsl(var(--bolt-text-secondary))] flex items-center gap-1">
                    <FileCode2 className="w-3 h-3" />
                    {String(activity.activity_data.file_path).split('/').pop()}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Time */}
          <div className="flex-shrink-0 text-xs text-[hsl(var(--bolt-text-secondary))]">
            {formatTime(activity.created_at)}
          </div>
        </div>
      </div>
    </div>
  )
}
