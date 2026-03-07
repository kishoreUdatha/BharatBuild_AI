'use client'

import React, { useState, useEffect } from 'react'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import apiClient from '@/lib/api-client'
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileCheck,
  Users,
  TrendingUp,
  Plus,
  ChevronRight,
  ListTodo,
  ClipboardCheck,
} from 'lucide-react'
import Link from 'next/link'

interface CriterionProgress {
  criterion_number: number
  criterion_name: string
  total_tasks: number
  completed_tasks: number
  progress_percentage: number
  pending_approvals: number
  coordinator_name: string | null
}

const CRITERION_COLORS = [
  'bg-orange-500', 'bg-blue-500', 'bg-purple-500', 'bg-green-500',
  'bg-pink-500', 'bg-cyan-500', 'bg-red-500'
]

export default function IQACCoordinatorDashboard() {
  const { approvalSummary, taskSummary, notifications, refreshDashboard } = useNAACRole()
  const [criteriaProgress, setCriteriaProgress] = useState<CriterionProgress[]>([])
  const [recentTasks, setRecentTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await apiClient.get('/naac/rbac/dashboard')
        setCriteriaProgress(data.criteria_progress || [])
        setRecentTasks(data.recent_tasks || [])
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const totalPendingApprovals = approvalSummary
    ? approvalSummary.pending_iqac + approvalSummary.pending_criterion + approvalSummary.pending_department
    : 0

  const myPendingApprovals = approvalSummary?.pending_iqac || 0

  return (
    <div className="space-y-6">
      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          href="/admin/accreditation/tasks/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Task
        </Link>
        <Link
          href="/admin/accreditation/roles/manage"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <Users className="w-4 h-4" />
          Manage Roles
        </Link>
        <Link
          href="/admin/accreditation/approvals"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <ClipboardCheck className="w-4 h-4" />
          Review Approvals
          {myPendingApprovals > 0 && (
            <span className="bg-amber-500 text-white text-xs px-2 py-0.5 rounded-full">
              {myPendingApprovals}
            </span>
          )}
        </Link>
      </div>

      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-200 text-sm">My Pending Approvals</p>
              <p className="text-3xl font-bold text-white">{myPendingApprovals}</p>
            </div>
            <FileCheck className="w-10 h-10 text-blue-300" />
          </div>
          <Link
            href="/admin/accreditation/approvals?level=iqac"
            className="mt-3 inline-flex items-center text-sm text-blue-200 hover:text-white"
          >
            Review now <ChevronRight className="w-4 h-4 ml-1" />
          </Link>
        </div>

        <div className="bg-gradient-to-br from-amber-600 to-amber-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-amber-200 text-sm">Total Pending</p>
              <p className="text-3xl font-bold text-white">{totalPendingApprovals}</p>
            </div>
            <Clock className="w-10 h-10 text-amber-300" />
          </div>
          <p className="mt-3 text-sm text-amber-200">
            Across all approval levels
          </p>
        </div>

        <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-200 text-sm">Active Tasks</p>
              <p className="text-3xl font-bold text-white">
                {(taskSummary?.assigned || 0) + (taskSummary?.in_progress || 0)}
              </p>
            </div>
            <ListTodo className="w-10 h-10 text-green-300" />
          </div>
          <Link
            href="/admin/accreditation/tasks"
            className="mt-3 inline-flex items-center text-sm text-green-200 hover:text-white"
          >
            View tasks <ChevronRight className="w-4 h-4 ml-1" />
          </Link>
        </div>

        <div className="bg-gradient-to-br from-red-600 to-red-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-200 text-sm">Overdue</p>
              <p className="text-3xl font-bold text-white">{taskSummary?.overdue || 0}</p>
            </div>
            <AlertTriangle className="w-10 h-10 text-red-300" />
          </div>
          <Link
            href="/admin/accreditation/tasks?status=overdue"
            className="mt-3 inline-flex items-center text-sm text-red-200 hover:text-white"
          >
            Address now <ChevronRight className="w-4 h-4 ml-1" />
          </Link>
        </div>
      </div>

      {/* Criteria Progress Cards */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">All Criteria Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {criteriaProgress.map((criterion, idx) => (
            <Link
              key={criterion.criterion_number}
              href={`/admin/accreditation/criterion${criterion.criterion_number}`}
              className="bg-slate-700/50 hover:bg-slate-700 rounded-lg p-4 transition-colors group"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 ${CRITERION_COLORS[idx]} rounded-lg flex items-center justify-center text-white font-bold`}>
                  C{criterion.criterion_number}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate group-hover:text-blue-400 transition-colors">
                    {criterion.criterion_name}
                  </p>
                  <p className="text-xs text-slate-400 truncate">
                    {criterion.coordinator_name || 'Unassigned'}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Progress</span>
                    <span className="text-white font-medium">{criterion.progress_percentage.toFixed(0)}%</span>
                  </div>
                  <div className="bg-slate-600 rounded-full h-2">
                    <div
                      className={`${CRITERION_COLORS[idx]} rounded-full h-2 transition-all`}
                      style={{ width: `${criterion.progress_percentage}%` }}
                    />
                  </div>
                </div>

                <div className="flex justify-between text-xs pt-1">
                  <span className="text-slate-400">
                    <CheckCircle2 className="w-3 h-3 inline mr-1" />
                    {criterion.completed_tasks}/{criterion.total_tasks}
                  </span>
                  {criterion.pending_approvals > 0 && (
                    <span className="text-amber-400">
                      <Clock className="w-3 h-3 inline mr-1" />
                      {criterion.pending_approvals} pending
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* My Tasks */}
        <div className="bg-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Recent Tasks</h3>
            <Link
              href="/admin/accreditation/tasks"
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {recentTasks.slice(0, 5).map((task) => (
              <Link
                key={task.id}
                href={`/admin/accreditation/tasks/${task.id}`}
                className="block bg-slate-700/50 hover:bg-slate-700 rounded-lg p-3 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{task.title}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {task.criterion_number && `C${task.criterion_number}`}
                      {task.department && ` - ${task.department}`}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    task.status === 'overdue' ? 'bg-red-500/20 text-red-400' :
                    task.status === 'in_progress' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-slate-600 text-slate-300'
                  }`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </Link>
            ))}
            {recentTasks.length === 0 && (
              <p className="text-slate-400 text-center py-4">No tasks assigned</p>
            )}
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Notifications</h3>
          </div>
          <div className="space-y-3">
            {notifications.slice(0, 5).map((notif) => (
              <div
                key={notif.id}
                className={`p-3 rounded-lg border-l-4 ${
                  notif.is_important
                    ? 'border-amber-500 bg-amber-500/10'
                    : 'border-slate-600 bg-slate-700/30'
                } ${!notif.is_read && 'bg-opacity-100'}`}
              >
                <p className="text-white text-sm font-medium">{notif.title}</p>
                <p className="text-slate-400 text-xs mt-1 line-clamp-2">{notif.message}</p>
                <div className="flex items-center justify-between mt-2">
                  <p className="text-slate-500 text-xs">
                    {new Date(notif.created_at).toLocaleDateString()}
                  </p>
                  {notif.action_url && (
                    <Link
                      href={notif.action_url}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      View
                    </Link>
                  )}
                </div>
              </div>
            ))}
            {notifications.length === 0 && (
              <p className="text-slate-400 text-center py-4">No notifications</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
