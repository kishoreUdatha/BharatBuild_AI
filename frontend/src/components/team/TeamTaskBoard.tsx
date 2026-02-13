'use client'

import { useState } from 'react'
import {
  Clock,
  AlertCircle,
  CheckCircle2,
  Play,
  Eye,
  Code2,
  ChevronRight,
  Sparkles,
  FileCode2,
  User,
  MoreVertical,
  ArrowRight,
  Zap
} from 'lucide-react'
import type { TeamMember, TeamTask } from './TeamProjectDashboard'

interface TeamTaskBoardProps {
  tasks: TeamTask[]
  teamMembers: TeamMember[]
}

const columns = [
  { id: 'todo', title: 'To Do', color: 'gray' },
  { id: 'in_progress', title: 'In Progress', color: 'blue' },
  { id: 'review', title: 'Code Review', color: 'yellow' },
  { id: 'done', title: 'Done', color: 'green' }
]

export function TeamTaskBoard({ tasks, teamMembers }: TeamTaskBoardProps) {
  const [selectedTask, setSelectedTask] = useState<TeamTask | null>(null)
  const [draggedTask, setDraggedTask] = useState<TeamTask | null>(null)

  const getTasksByStatus = (status: string) => {
    return tasks.filter(task => task.status === status)
  }

  const handleDragStart = (task: TeamTask) => {
    setDraggedTask(task)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = (status: string) => {
    if (draggedTask) {
      // TODO: Update task status via API
      console.log(`Moving task ${draggedTask.id} to ${status}`)
      setDraggedTask(null)
    }
  }

  return (
    <div className="h-full flex overflow-hidden">
      {/* Kanban Board */}
      <div className="flex-1 flex gap-4 p-6 overflow-x-auto">
        {columns.map((column) => (
          <div
            key={column.id}
            className="flex-shrink-0 w-80 flex flex-col"
            onDragOver={handleDragOver}
            onDrop={() => handleDrop(column.id)}
          >
            {/* Column Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    column.color === 'gray'
                      ? 'bg-gray-400'
                      : column.color === 'blue'
                      ? 'bg-blue-500'
                      : column.color === 'yellow'
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                />
                <h3 className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {column.title}
                </h3>
                <span className="text-sm text-[hsl(var(--bolt-text-secondary))] bg-[hsl(var(--bolt-bg-tertiary))] px-2 py-0.5 rounded-full">
                  {getTasksByStatus(column.id).length}
                </span>
              </div>
            </div>

            {/* Task Cards */}
            <div className="flex-1 space-y-3 overflow-y-auto scrollbar-thin">
              {getTasksByStatus(column.id).map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onSelect={() => setSelectedTask(task)}
                  onDragStart={() => handleDragStart(task)}
                  isSelected={selectedTask?.id === task.id}
                />
              ))}

              {getTasksByStatus(column.id).length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center border-2 border-dashed border-[hsl(var(--bolt-border))] rounded-xl">
                  <div className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                    No tasks
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Task Detail Panel */}
      {selectedTask && (
        <TaskDetailPanel
          task={selectedTask}
          teamMembers={teamMembers}
          onClose={() => setSelectedTask(null)}
        />
      )}
    </div>
  )
}

interface TaskCardProps {
  task: TeamTask
  onSelect: () => void
  onDragStart: () => void
  isSelected: boolean
}

function TaskCard({ task, onSelect, onDragStart, isSelected }: TaskCardProps) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onClick={onSelect}
      className={`p-4 rounded-xl border cursor-pointer transition-all hover:shadow-lg ${
        isSelected
          ? 'border-[hsl(var(--bolt-accent))] bg-[hsl(var(--bolt-accent))]/5 shadow-lg'
          : 'border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] hover:border-[hsl(var(--bolt-accent))]/50'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {task.aiGenerated && (
            <div className="flex items-center gap-1 px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded-full text-xs">
              <Sparkles className="w-3 h-3" />
              AI
            </div>
          )}
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              task.priority === 'high'
                ? 'bg-red-500/10 text-red-400'
                : task.priority === 'medium'
                ? 'bg-yellow-500/10 text-yellow-400'
                : 'bg-gray-500/10 text-gray-400'
            }`}
          >
            {task.priority}
          </span>
        </div>
        <button className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded">
          <MoreVertical className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
        </button>
      </div>

      {/* Title */}
      <h4 className="font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
        {task.title}
      </h4>

      {/* Description */}
      <p className="text-sm text-[hsl(var(--bolt-text-secondary))] line-clamp-2 mb-3">
        {task.description}
      </p>

      {/* Files */}
      <div className="flex flex-wrap gap-1 mb-3">
        {task.files.slice(0, 2).map((file, index) => (
          <div
            key={index}
            className="flex items-center gap-1 px-2 py-1 bg-[hsl(var(--bolt-bg-tertiary))] rounded text-xs text-[hsl(var(--bolt-text-secondary))]"
          >
            <FileCode2 className="w-3 h-3" />
            {file.split('/').pop()}
          </div>
        ))}
        {task.files.length > 2 && (
          <div className="px-2 py-1 bg-[hsl(var(--bolt-bg-tertiary))] rounded text-xs text-[hsl(var(--bolt-text-secondary))]">
            +{task.files.length - 2} more
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-[hsl(var(--bolt-border))]">
        {/* Assignee */}
        {task.assignee ? (
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
              {task.assignee.name.charAt(0)}
            </div>
            <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
              {task.assignee.name.split(' ')[0]}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-[hsl(var(--bolt-text-secondary))]">
            <User className="w-4 h-4" />
            Unassigned
          </div>
        )}

        {/* Time */}
        {task.estimatedTime && (
          <div className="flex items-center gap-1 text-xs text-[hsl(var(--bolt-text-secondary))]">
            <Clock className="w-3 h-3" />
            {task.estimatedTime}
          </div>
        )}
      </div>
    </div>
  )
}

interface TaskDetailPanelProps {
  task: TeamTask
  teamMembers: TeamMember[]
  onClose: () => void
}

function TaskDetailPanel({ task, teamMembers, onClose }: TaskDetailPanelProps) {
  return (
    <div className="w-96 flex-shrink-0 border-l border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[hsl(var(--bolt-border))]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {task.aiGenerated && (
              <div className="flex items-center gap-1 px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded-full text-xs">
                <Sparkles className="w-3 h-3" />
                AI Generated
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
          >
            <ChevronRight className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
          </button>
        </div>
        <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
          {task.title}
        </h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Description */}
        <div>
          <h4 className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))] mb-2">
            Description
          </h4>
          <p className="text-sm text-[hsl(var(--bolt-text-primary))]">
            {task.description}
          </p>
        </div>

        {/* Status */}
        <div>
          <h4 className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))] mb-2">
            Status
          </h4>
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                task.status === 'todo'
                  ? 'bg-gray-500/10 text-gray-400'
                  : task.status === 'in_progress'
                  ? 'bg-blue-500/10 text-blue-400'
                  : task.status === 'review'
                  ? 'bg-yellow-500/10 text-yellow-400'
                  : 'bg-green-500/10 text-green-400'
              }`}
            >
              {task.status === 'todo'
                ? 'To Do'
                : task.status === 'in_progress'
                ? 'In Progress'
                : task.status === 'review'
                ? 'Code Review'
                : 'Done'}
            </span>
          </div>
        </div>

        {/* Assignee */}
        <div>
          <h4 className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))] mb-2">
            Assignee
          </h4>
          {task.assignee ? (
            <div className="flex items-center gap-3 p-3 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-bold">
                {task.assignee.name.charAt(0)}
              </div>
              <div>
                <div className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {task.assignee.name}
                </div>
                <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                  {task.assignee.email}
                </div>
              </div>
            </div>
          ) : (
            <select className="w-full px-3 py-2 bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] rounded-lg text-[hsl(var(--bolt-text-primary))]">
              <option value="">Select assignee</option>
              {teamMembers.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Files */}
        <div>
          <h4 className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))] mb-2">
            Files to Generate ({task.files.length})
          </h4>
          <div className="space-y-2">
            {task.files.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 p-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg text-sm"
              >
                <FileCode2 className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                <span className="text-[hsl(var(--bolt-text-primary))]">{file}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-[hsl(var(--bolt-border))]">
        <button className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium rounded-lg hover:from-blue-600 hover:to-cyan-600 transition-all">
          <Zap className="w-4 h-4" />
          Start AI Code Generation
        </button>
      </div>
    </div>
  )
}
