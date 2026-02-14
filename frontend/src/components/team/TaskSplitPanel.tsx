'use client'

import { useState } from 'react'
import {
  Sparkles,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  FileCode2,
  User,
  ArrowRight,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import type { TeamMember, SuggestedTask, TaskSplitResponse, TaskPriority } from '@/types/team'
import { useTeamActions } from '@/hooks/useTeam'

interface TaskSplitPanelProps {
  teamId?: string
  projectDescription: string
  teamMembers: TeamMember[] | any[]
  onTasksApplied?: () => void
}

export function TaskSplitPanel({
  teamId,
  projectDescription,
  teamMembers,
  onTasksApplied
}: TaskSplitPanelProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [splitResult, setSplitResult] = useState<TaskSplitResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [balanceWorkload, setBalanceWorkload] = useState(true)
  const [maxTasks, setMaxTasks] = useState(10)
  const [expandedTasks, setExpandedTasks] = useState<Set<number>>(new Set())

  const { splitTasks, applyTaskSplit } = useTeamActions()

  const handleAnalyze = async () => {
    setIsAnalyzing(true)
    setError(null)
    setSplitResult(null)

    try {
      const result = await splitTasks(teamId || 'mock-team', {
        balance_workload: balanceWorkload,
        max_tasks: maxTasks,
        include_file_mapping: true
      })
      setSplitResult(result)
      // Expand first 3 tasks by default
      setExpandedTasks(new Set([0, 1, 2]))
    } catch (err: any) {
      setError(err.message || 'Failed to analyze project')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleApply = async () => {
    if (!splitResult) return

    setIsApplying(true)
    setError(null)

    try {
      await applyTaskSplit(teamId || 'mock-team', {
        suggested_tasks: splitResult.suggested_tasks,
        assign_to_members: true
      })
      onTasksApplied?.()
      setSplitResult(null)
    } catch (err: any) {
      setError(err.message || 'Failed to create tasks')
    } finally {
      setIsApplying(false)
    }
  }

  const toggleTaskExpanded = (index: number) => {
    const newExpanded = new Set(expandedTasks)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedTasks(newExpanded)
  }

  const getPriorityColor = (priority: TaskPriority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-500/10 text-red-400 border-red-500/20'
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
      case 'low':
        return 'bg-gray-500/10 text-gray-400 border-gray-500/20'
    }
  }

  return (
    <div className="h-full overflow-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
              AI Task Splitter
            </h2>
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              Automatically divide your project into manageable tasks
            </p>
          </div>
        </div>
      </div>

      {/* Configuration */}
      {!splitResult && (
        <div className="mb-6 p-4 bg-[hsl(var(--bolt-bg-secondary))] rounded-xl border border-[hsl(var(--bolt-border))]">
          <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-4">
            Configuration
          </h3>

          <div className="space-y-4">
            {/* Balance Workload Toggle */}
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <div className="text-sm text-[hsl(var(--bolt-text-primary))]">
                  Balance Workload
                </div>
                <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                  Distribute tasks evenly across team members
                </div>
              </div>
              <button
                onClick={() => setBalanceWorkload(!balanceWorkload)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  balanceWorkload ? 'bg-[hsl(var(--bolt-accent))]' : 'bg-[hsl(var(--bolt-bg-tertiary))]'
                }`}
              >
                <div
                  className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    balanceWorkload ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </label>

            {/* Max Tasks Slider */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm text-[hsl(var(--bolt-text-primary))]">
                  Maximum Tasks
                </div>
                <span className="text-sm font-medium text-[hsl(var(--bolt-accent))]">
                  {maxTasks}
                </span>
              </div>
              <input
                type="range"
                min="5"
                max="20"
                value={maxTasks}
                onChange={(e) => setMaxTasks(Number(e.target.value))}
                className="w-full h-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg appearance-none cursor-pointer accent-[hsl(var(--bolt-accent))]"
              />
              <div className="flex justify-between text-xs text-[hsl(var(--bolt-text-secondary))] mt-1">
                <span>5</span>
                <span>20</span>
              </div>
            </div>

            {/* Team Info */}
            <div className="flex items-center gap-2 p-3 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
              <User className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
              <span className="text-sm text-[hsl(var(--bolt-text-primary))]">
                {teamMembers.length} team members available for assignment
              </span>
            </div>
          </div>

          {/* Analyze Button */}
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="mt-6 w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-medium rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing Project...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Analyze & Split Project
              </>
            )}
          </button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-medium text-red-400">Analysis Failed</div>
            <div className="text-sm text-red-400/80 mt-1">{error}</div>
          </div>
        </div>
      )}

      {/* Results */}
      {splitResult && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="p-4 bg-[hsl(var(--bolt-bg-secondary))] rounded-xl border border-[hsl(var(--bolt-border))]">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                Analysis Complete
              </h3>
            </div>

            <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mb-4">
              {splitResult.analysis_summary}
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
                <div className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))]">
                  {splitResult.suggested_tasks.length}
                </div>
                <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">Tasks Created</div>
              </div>
              <div className="p-3 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
                <div className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))]">
                  {splitResult.total_estimated_hours}h
                </div>
                <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">Total Hours</div>
              </div>
            </div>

            <div className="mt-4 p-3 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg">
              <div className="text-xs text-[hsl(var(--bolt-text-secondary))] mb-2">Strategy</div>
              <div className="text-sm text-[hsl(var(--bolt-text-primary))]">
                {splitResult.split_strategy}
              </div>
            </div>
          </div>

          {/* Workload Distribution */}
          {Object.keys(splitResult.workload_distribution).length > 0 && (
            <div className="p-4 bg-[hsl(var(--bolt-bg-secondary))] rounded-xl border border-[hsl(var(--bolt-border))]">
              <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-3">
                Workload Distribution
              </h3>
              <div className="space-y-2">
                {Object.entries(splitResult.workload_distribution).map(([memberId, hours], index) => {
                  const member = teamMembers[index]
                  const percentage = (hours / splitResult.total_estimated_hours) * 100
                  return (
                    <div key={memberId} className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
                        {member?.user_name?.charAt(0) || index + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-[hsl(var(--bolt-text-primary))]">
                            {member?.user_name || `Member ${index + 1}`}
                          </span>
                          <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                            {hours}h ({Math.round(percentage)}%)
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-[hsl(var(--bolt-bg-primary))] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Task List */}
          <div>
            <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-3">
              Suggested Tasks ({splitResult.suggested_tasks.length})
            </h3>
            <div className="space-y-3">
              {splitResult.suggested_tasks.map((task, index) => (
                <div
                  key={index}
                  className="p-4 bg-[hsl(var(--bolt-bg-secondary))] rounded-xl border border-[hsl(var(--bolt-border))]"
                >
                  {/* Task Header */}
                  <div
                    className="flex items-start justify-between cursor-pointer"
                    onClick={() => toggleTaskExpanded(index)}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium text-[hsl(var(--bolt-text-secondary))]">
                          #{index + 1}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full border ${getPriorityColor(task.priority)}`}
                        >
                          {task.priority}
                        </span>
                        <span className="flex items-center gap-1 text-xs text-[hsl(var(--bolt-text-secondary))]">
                          <Clock className="w-3 h-3" />
                          {task.estimated_hours}h
                        </span>
                      </div>
                      <h4 className="font-medium text-[hsl(var(--bolt-text-primary))]">
                        {task.title}
                      </h4>
                    </div>
                    {expandedTasks.has(index) ? (
                      <ChevronUp className="w-5 h-5 text-[hsl(var(--bolt-text-secondary))]" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-[hsl(var(--bolt-text-secondary))]" />
                    )}
                  </div>

                  {/* Expanded Content */}
                  {expandedTasks.has(index) && (
                    <div className="mt-3 pt-3 border-t border-[hsl(var(--bolt-border))]">
                      <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mb-3">
                        {task.description}
                      </p>

                      {/* Files */}
                      {task.file_paths.length > 0 && (
                        <div className="mb-3">
                          <div className="text-xs font-medium text-[hsl(var(--bolt-text-secondary))] mb-2">
                            Files to create/modify:
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {task.file_paths.map((file, fileIndex) => (
                              <span
                                key={fileIndex}
                                className="inline-flex items-center gap-1 px-2 py-0.5 bg-[hsl(var(--bolt-bg-tertiary))] rounded text-xs text-[hsl(var(--bolt-text-secondary))]"
                              >
                                <FileCode2 className="w-3 h-3" />
                                {file.split('/').pop()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Dependencies */}
                      {task.dependencies.length > 0 && (
                        <div className="mb-3">
                          <div className="text-xs font-medium text-[hsl(var(--bolt-text-secondary))] mb-1">
                            Depends on:
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {task.dependencies.map((depIndex) => (
                              <span
                                key={depIndex}
                                className="px-2 py-0.5 bg-[hsl(var(--bolt-accent))]/10 text-[hsl(var(--bolt-accent))] rounded text-xs"
                              >
                                Task #{depIndex + 1}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Suggested Assignee */}
                      {task.suggested_assignee_index !== null &&
                        task.suggested_assignee_index !== undefined && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                              Suggested:
                            </span>
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
                                {teamMembers[task.suggested_assignee_index]?.user_name?.charAt(0) ||
                                  task.suggested_assignee_index + 1}
                              </div>
                              <span className="text-sm text-[hsl(var(--bolt-text-primary))]">
                                {teamMembers[task.suggested_assignee_index]?.user_name ||
                                  `Member ${task.suggested_assignee_index + 1}`}
                              </span>
                            </div>
                          </div>
                        )}

                      {/* Complexity Score */}
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                          Complexity:
                        </span>
                        <div className="flex gap-0.5">
                          {Array.from({ length: 10 }).map((_, i) => (
                            <div
                              key={i}
                              className={`w-2 h-2 rounded-full ${
                                i < task.complexity_score
                                  ? 'bg-[hsl(var(--bolt-accent))]'
                                  : 'bg-[hsl(var(--bolt-bg-tertiary))]'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                          {task.complexity_score}/10
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="flex items-center justify-center gap-2 px-4 py-3 border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] font-medium rounded-lg hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Re-analyze
            </button>
            <button
              onClick={handleApply}
              disabled={isApplying}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-medium rounded-lg hover:from-green-600 hover:to-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isApplying ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creating Tasks...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-5 h-5" />
                  Apply & Create Tasks
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
