'use client'

import React, { useState, useEffect } from 'react'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import apiClient from '@/lib/api-client'
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileCheck,
  Plus,
  ChevronRight,
  ListTodo,
  Upload,
  Users,
  BarChart3,
} from 'lucide-react'
import Link from 'next/link'

const CRITERION_NAMES: Record<number, string> = {
  1: 'Curricular Aspects',
  2: 'Teaching-Learning',
  3: 'Research & Extension',
  4: 'Infrastructure',
  5: 'Student Support',
  6: 'Governance',
  7: 'Institutional Values',
}

const CRITERION_COLORS: Record<number, string> = {
  1: 'orange',
  2: 'blue',
  3: 'purple',
  4: 'green',
  5: 'pink',
  6: 'cyan',
  7: 'red',
}

export default function CriterionCoordinatorDashboard() {
  const { roles, approvalSummary, taskSummary, notifications } = useNAACRole()
  const [recentTasks, setRecentTasks] = useState<any[]>([])
  const [pendingApprovals, setPendingApprovals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Get assigned criterion from role
  const criterionRole = roles.find(r => r.role_type === 'criterion_coordinator')
  const assignedCriterion = criterionRole?.criterion_number || 1

  const criterionName = CRITERION_NAMES[assignedCriterion]
  const criterionColor = CRITERION_COLORS[assignedCriterion]

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tasksData, approvalsData] = await Promise.all([
          apiClient.get(`/naac/rbac/tasks?criterion=${assignedCriterion}&page_size=10`),
          apiClient.get('/naac/rbac/approval/pending'),
        ])
        setRecentTasks(tasksData.tasks || [])
        setPendingApprovals(approvalsData.pending_criterion || [])
      } catch (err) {
        console.error('Failed to fetch data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [assignedCriterion])

  const myPendingApprovals = pendingApprovals.filter(
    a => a.criterion_number === assignedCriterion
  ).length

  return (
    <div className="space-y-6">
      {/* Criterion Header */}
      <div className={`bg-gradient-to-r from-${criterionColor}-600 to-${criterionColor}-700 rounded-xl p-6`}>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center`}>
            <span className="text-2xl font-bold text-white">C{assignedCriterion}</span>
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white">{criterionName}</h2>
            <p className="text-white/80">Criterion Coordinator Dashboard</p>
          </div>
          <Link
            href={`/admin/accreditation/criterion${assignedCriterion}`}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-white transition-colors"
          >
            View Full Criterion
          </Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          href={`/admin/accreditation/tasks/new?criterion=${assignedCriterion}`}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Task
        </Link>
        <Link
          href={`/admin/accreditation/criterion${assignedCriterion}/evidence`}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload Evidence
        </Link>
        <Link
          href="/admin/accreditation/approvals"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <FileCheck className="w-4 h-4" />
          Review Approvals
          {myPendingApprovals > 0 && (
            <span className="bg-amber-500 text-white text-xs px-2 py-0.5 rounded-full">
              {myPendingApprovals}
            </span>
          )}
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Pending Approvals</p>
              <p className="text-2xl font-bold text-white">{myPendingApprovals}</p>
            </div>
            <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
              <FileCheck className="w-5 h-5 text-amber-500" />
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Active Tasks</p>
              <p className="text-2xl font-bold text-white">
                {recentTasks.filter(t => ['assigned', 'in_progress'].includes(t.status)).length}
              </p>
            </div>
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <ListTodo className="w-5 h-5 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Completed</p>
              <p className="text-2xl font-bold text-white">
                {recentTasks.filter(t => t.status === 'completed').length}
              </p>
            </div>
            <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Overdue</p>
              <p className="text-2xl font-bold text-white">
                {recentTasks.filter(t => t.status === 'overdue').length}
              </p>
            </div>
            <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Approvals */}
        <div className="bg-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Pending Approvals</h3>
            <Link
              href="/admin/accreditation/approvals"
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              View all
            </Link>
          </div>
          {myPendingApprovals === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <p className="text-slate-400">No pending approvals</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingApprovals
                .filter(a => a.criterion_number === assignedCriterion)
                .slice(0, 5)
                .map((approval) => (
                  <Link
                    key={approval.id}
                    href={`/admin/accreditation/approvals/${approval.id}`}
                    className="block bg-slate-700/50 hover:bg-slate-700 rounded-lg p-3 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white font-medium">{approval.record_type}</p>
                        <p className="text-xs text-slate-400 mt-1">
                          Submitted by {approval.submitted_by_name || 'Unknown'}
                        </p>
                      </div>
                      <span className="text-xs px-2 py-1 bg-amber-500/20 text-amber-400 rounded-full">
                        Needs Review
                      </span>
                    </div>
                  </Link>
                ))}
            </div>
          )}
        </div>

        {/* Tasks */}
        <div className="bg-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Criterion Tasks</h3>
            <Link
              href={`/admin/accreditation/tasks?criterion=${assignedCriterion}`}
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
                      {task.assigned_to_name || 'Unassigned'}
                      {task.due_date && ` - Due ${new Date(task.due_date).toLocaleDateString()}`}
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
              <p className="text-slate-400 text-center py-4">No tasks for this criterion</p>
            )}
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Notifications</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {notifications.slice(0, 4).map((notif) => (
            <div
              key={notif.id}
              className={`p-3 rounded-lg ${notif.is_read ? 'bg-slate-700/30' : 'bg-slate-700'}`}
            >
              <p className="text-white text-sm font-medium">{notif.title}</p>
              <p className="text-slate-400 text-xs mt-1 line-clamp-2">{notif.message}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
