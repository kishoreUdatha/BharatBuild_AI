'use client'

import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import apiClient from '@/lib/api-client'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import {
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ChevronRight,
  Calendar,
  User,
  Loader2,
  X,
} from 'lucide-react'
import Link from 'next/link'

interface Task {
  id: string
  title: string
  description: string | null
  task_type: string | null
  criterion_number: number | null
  key_indicator: string | null
  department: string | null
  academic_year: string | null
  created_by: string | null
  created_by_name: string | null
  assigned_to: string | null
  assigned_to_name: string | null
  status: string
  priority: string
  due_date: string | null
  progress_percentage: number
  is_overdue: boolean
  created_at: string
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'completed', label: 'Completed' },
  { value: 'overdue', label: 'Overdue' },
]

const PRIORITY_OPTIONS = [
  { value: '', label: 'All Priorities' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

const CRITERION_OPTIONS = [
  { value: '', label: 'All Criteria' },
  { value: '1', label: 'C1: Curricular Aspects' },
  { value: '2', label: 'C2: Teaching-Learning' },
  { value: '3', label: 'C3: Research' },
  { value: '4', label: 'C4: Infrastructure' },
  { value: '5', label: 'C5: Student Support' },
  { value: '6', label: 'C6: Governance' },
  { value: '7', label: 'C7: Values' },
]

export default function TasksPage() {
  const searchParams = useSearchParams()
  const { canApprove, hasRole } = useNAACRole()

  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  // Filters
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [criterionFilter, setCriterionFilter] = useState(searchParams.get('criterion') || '')
  const [assignedToMe, setAssignedToMe] = useState(searchParams.get('assigned_to_me') === 'true')
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    fetchTasks()
  }, [page, statusFilter, priorityFilter, criterionFilter, assignedToMe])

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      params.append('page', page.toString())
      params.append('page_size', pageSize.toString())
      if (statusFilter) params.append('status_filter', statusFilter)
      if (priorityFilter) params.append('priority', priorityFilter)
      if (criterionFilter) params.append('criterion', criterionFilter)
      if (assignedToMe) params.append('assigned_to_me', 'true')

      const data = await apiClient.get(`/naac/rbac/tasks?${params.toString()}`)
      setTasks(data.tasks || [])
      setTotal(data.total || 0)
    } catch (err) {
      console.error('Failed to fetch tasks:', err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string, isOverdue: boolean) => {
    if (isOverdue && !['completed', 'overdue'].includes(status)) {
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    }
    const statusColors: Record<string, string> = {
      pending: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
      assigned: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      in_progress: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      submitted: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      completed: 'bg-green-500/20 text-green-400 border-green-500/30',
      overdue: 'bg-red-500/20 text-red-400 border-red-500/30',
    }
    return statusColors[status] || statusColors.pending
  }

  const getPriorityBadge = (priority: string) => {
    const priorityColors: Record<string, string> = {
      low: 'text-slate-400',
      medium: 'text-blue-400',
      high: 'text-amber-400',
      critical: 'text-red-400',
    }
    return priorityColors[priority] || priorityColors.medium
  }

  const filteredTasks = tasks.filter(task =>
    task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    task.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const canCreateTasks = hasRole('iqac_coordinator') || hasRole('criterion_coordinator') || hasRole('head_of_institution')

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">NAAC Tasks</h1>
          <p className="text-slate-400 mt-1">Manage and track accreditation tasks</p>
        </div>
        {canCreateTasks && (
          <Link
            href="/admin/accreditation/tasks/new"
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors w-fit"
          >
            <Plus className="w-4 h-4" />
            Create Task
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="bg-slate-800 rounded-xl p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Quick filters */}
          <div className="flex gap-2">
            <button
              onClick={() => setAssignedToMe(!assignedToMe)}
              className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                assignedToMe
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              My Tasks
            </button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                showFilters
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <Filter className="w-4 h-4" />
              Filters
            </button>
          </div>
        </div>

        {/* Advanced filters */}
        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-700">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Priority</label>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              >
                {PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Criterion</label>
              <select
                value={criterionFilter}
                onChange={(e) => setCriterionFilter(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
              >
                {CRITERION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Tasks List */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No tasks found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {filteredTasks.map((task) => (
              <Link
                key={task.id}
                href={`/admin/accreditation/tasks/${task.id}`}
                className="block p-4 hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-white font-medium truncate">{task.title}</h3>
                      <span className={`px-2 py-0.5 rounded text-xs border ${getStatusBadge(task.status, task.is_overdue)}`}>
                        {task.is_overdue && task.status !== 'overdue' ? 'Overdue' : task.status.replace('_', ' ')}
                      </span>
                    </div>
                    {task.description && (
                      <p className="text-sm text-slate-400 line-clamp-1 mb-2">
                        {task.description}
                      </p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                      {task.criterion_number && (
                        <span className="px-2 py-0.5 bg-slate-700 rounded">
                          C{task.criterion_number}
                        </span>
                      )}
                      {task.key_indicator && (
                        <span>{task.key_indicator}</span>
                      )}
                      {task.assigned_to_name && (
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          {task.assigned_to_name}
                        </span>
                      )}
                      {task.due_date && (
                        <span className={`flex items-center gap-1 ${task.is_overdue ? 'text-red-400' : ''}`}>
                          <Calendar className="w-3 h-3" />
                          {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      )}
                      <span className={getPriorityBadge(task.priority)}>
                        {task.priority}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-500 flex-shrink-0" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white text-sm"
          >
            Previous
          </button>
          <span className="text-slate-400 text-sm">
            Page {page} of {Math.ceil(total / pageSize)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(total / pageSize)}
            className="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed rounded text-white text-sm"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
