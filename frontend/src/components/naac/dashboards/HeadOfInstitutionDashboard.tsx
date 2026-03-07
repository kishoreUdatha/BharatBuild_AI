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
  Calendar,
  ChevronRight,
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

export default function HeadOfInstitutionDashboard() {
  const { approvalSummary, taskSummary, notifications, refreshDashboard } = useNAACRole()
  const [criteriaProgress, setCriteriaProgress] = useState<CriterionProgress[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await apiClient.get('/naac/rbac/dashboard')
        setCriteriaProgress(data.criteria_progress || [])
      } catch (err) {
        console.error('Failed to fetch criteria progress:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const totalPendingApprovals = approvalSummary
    ? approvalSummary.pending_head
    : 0

  const overallProgress = criteriaProgress.length > 0
    ? criteriaProgress.reduce((sum, c) => sum + c.progress_percentage, 0) / criteriaProgress.length
    : 0

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-200 text-sm">Overall Progress</p>
              <p className="text-3xl font-bold text-white">{overallProgress.toFixed(1)}%</p>
            </div>
            <TrendingUp className="w-10 h-10 text-purple-300" />
          </div>
          <div className="mt-3 bg-purple-800/50 rounded-full h-2">
            <div
              className="bg-white rounded-full h-2 transition-all"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>

        <div className="bg-gradient-to-br from-amber-600 to-amber-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-amber-200 text-sm">Awaiting Your Approval</p>
              <p className="text-3xl font-bold text-white">{totalPendingApprovals}</p>
            </div>
            <FileCheck className="w-10 h-10 text-amber-300" />
          </div>
          <Link
            href="/admin/accreditation/approvals"
            className="mt-3 inline-flex items-center text-sm text-amber-200 hover:text-white"
          >
            Review now <ChevronRight className="w-4 h-4 ml-1" />
          </Link>
        </div>

        <div className="bg-gradient-to-br from-green-600 to-green-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-200 text-sm">Tasks Completed</p>
              <p className="text-3xl font-bold text-white">{taskSummary?.completed || 0}</p>
            </div>
            <CheckCircle2 className="w-10 h-10 text-green-300" />
          </div>
          <p className="mt-3 text-sm text-green-200">
            {taskSummary?.in_progress || 0} in progress
          </p>
        </div>

        <div className="bg-gradient-to-br from-red-600 to-red-700 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-red-200 text-sm">Overdue Items</p>
              <p className="text-3xl font-bold text-white">{taskSummary?.overdue || 0}</p>
            </div>
            <AlertTriangle className="w-10 h-10 text-red-300" />
          </div>
          <Link
            href="/admin/accreditation/tasks?status=overdue"
            className="mt-3 inline-flex items-center text-sm text-red-200 hover:text-white"
          >
            View all <ChevronRight className="w-4 h-4 ml-1" />
          </Link>
        </div>
      </div>

      {/* Criteria Progress */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Criteria Progress Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {criteriaProgress.map((criterion, idx) => (
            <Link
              key={criterion.criterion_number}
              href={`/admin/accreditation/criterion${criterion.criterion_number}`}
              className="bg-slate-700/50 hover:bg-slate-700 rounded-lg p-4 transition-colors"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-8 h-8 ${CRITERION_COLORS[idx]} rounded-lg flex items-center justify-center text-white font-bold text-sm`}>
                  C{criterion.criterion_number}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">{criterion.criterion_name}</p>
                  <p className="text-xs text-slate-400">{criterion.coordinator_name || 'No coordinator'}</p>
                </div>
              </div>
              <div className="mb-2">
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
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">
                  {criterion.completed_tasks}/{criterion.total_tasks} tasks
                </span>
                {criterion.pending_approvals > 0 && (
                  <span className="text-amber-400">
                    {criterion.pending_approvals} pending
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pending Final Approvals */}
        <div className="bg-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Pending Final Approvals</h3>
            <Link
              href="/admin/accreditation/approvals"
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              View all
            </Link>
          </div>
          {totalPendingApprovals === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <p className="text-slate-400">No pending approvals</p>
            </div>
          ) : (
            <div className="space-y-3">
              {approvalSummary && approvalSummary.pending_head > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    <Clock className="w-5 h-5 text-amber-500" />
                    <div className="flex-1">
                      <p className="text-white font-medium">
                        {approvalSummary.pending_head} items awaiting final approval
                      </p>
                      <p className="text-sm text-slate-400">These have passed all previous approval stages</p>
                    </div>
                    <Link
                      href="/admin/accreditation/approvals?level=head"
                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-sm rounded-lg transition-colors"
                    >
                      Review
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-slate-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Recent Activity</h3>
          </div>
          <div className="space-y-3">
            {notifications.slice(0, 5).map((notif) => (
              <div
                key={notif.id}
                className={`p-3 rounded-lg ${notif.is_read ? 'bg-slate-700/30' : 'bg-slate-700'}`}
              >
                <p className="text-white text-sm font-medium">{notif.title}</p>
                <p className="text-slate-400 text-xs mt-1">{notif.message}</p>
                <p className="text-slate-500 text-xs mt-2">
                  {new Date(notif.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
            {notifications.length === 0 && (
              <p className="text-slate-400 text-center py-4">No recent activity</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
