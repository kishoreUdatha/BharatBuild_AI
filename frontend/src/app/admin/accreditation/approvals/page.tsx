'use client'

import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import apiClient from '@/lib/api-client'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import {
  CheckCircle2,
  XCircle,
  RotateCcw,
  Clock,
  ChevronRight,
  FileCheck,
  Loader2,
  Filter,
  AlertTriangle,
} from 'lucide-react'
import Link from 'next/link'

interface ApprovalWorkflow {
  id: string
  record_type: string
  record_id: string
  criterion_number: number | null
  department: string | null
  academic_year: string | null
  status: string
  submitted_by: string | null
  submitted_by_name: string | null
  submitted_at: string | null
  submission_remarks: string | null
  created_at: string
}

interface PendingApprovals {
  pending_department: ApprovalWorkflow[]
  pending_criterion: ApprovalWorkflow[]
  pending_iqac: ApprovalWorkflow[]
  pending_head: ApprovalWorkflow[]
  total_pending: number
}

const LEVEL_LABELS: Record<string, string> = {
  pending_department: 'Department Review',
  pending_criterion: 'Criterion Review',
  pending_iqac: 'IQAC Review',
  pending_head: 'Final Approval',
}

const LEVEL_COLORS: Record<string, string> = {
  pending_department: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  pending_criterion: 'bg-green-500/20 text-green-400 border-green-500/30',
  pending_iqac: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  pending_head: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
}

export default function ApprovalsPage() {
  const searchParams = useSearchParams()
  const { canApprove, hasRole } = useNAACRole()

  const [pendingApprovals, setPendingApprovals] = useState<PendingApprovals | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedLevel, setSelectedLevel] = useState(searchParams.get('level') || '')

  // Modal state
  const [selectedWorkflow, setSelectedWorkflow] = useState<ApprovalWorkflow | null>(null)
  const [actionType, setActionType] = useState<'approve' | 'reject' | 'revision' | null>(null)
  const [remarks, setRemarks] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchPendingApprovals()
  }, [])

  const fetchPendingApprovals = async () => {
    try {
      setLoading(true)
      const data = await apiClient.get('/naac/rbac/approval/pending')
      setPendingApprovals(data)
    } catch (err) {
      console.error('Failed to fetch pending approvals:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async () => {
    if (!selectedWorkflow || !actionType) return

    try {
      setSubmitting(true)
      await apiClient.post(`/naac/rbac/approval/${selectedWorkflow.id}/action`, {
        action: actionType,
        remarks: remarks || null,
      })

      // Refresh data
      await fetchPendingApprovals()

      // Close modal
      setSelectedWorkflow(null)
      setActionType(null)
      setRemarks('')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Action failed')
    } finally {
      setSubmitting(false)
    }
  }

  const getApprovalLevels = () => {
    if (!pendingApprovals) return []

    const levels = []
    if (pendingApprovals.pending_department.length > 0 && canApprove('department')) {
      levels.push({ key: 'pending_department', items: pendingApprovals.pending_department })
    }
    if (pendingApprovals.pending_criterion.length > 0 && canApprove('criterion')) {
      levels.push({ key: 'pending_criterion', items: pendingApprovals.pending_criterion })
    }
    if (pendingApprovals.pending_iqac.length > 0 && canApprove('iqac')) {
      levels.push({ key: 'pending_iqac', items: pendingApprovals.pending_iqac })
    }
    if (pendingApprovals.pending_head.length > 0 && canApprove('head')) {
      levels.push({ key: 'pending_head', items: pendingApprovals.pending_head })
    }
    return levels
  }

  const approvalLevels = getApprovalLevels()
  const filteredLevels = selectedLevel
    ? approvalLevels.filter(l => l.key === selectedLevel)
    : approvalLevels

  const totalPending = pendingApprovals?.total_pending || 0

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Approval Workflows</h1>
          <p className="text-slate-400 mt-1">Review and approve NAAC submissions</p>
        </div>
        {totalPending > 0 && (
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 border border-amber-500/30 rounded-lg">
            <Clock className="w-5 h-5 text-amber-400" />
            <span className="text-amber-400 font-medium">{totalPending} pending approvals</span>
          </div>
        )}
      </div>

      {/* Filter by level */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setSelectedLevel('')}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            selectedLevel === ''
              ? 'bg-blue-600 text-white'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
        >
          All Levels
        </button>
        {canApprove('department') && (
          <button
            onClick={() => setSelectedLevel('pending_department')}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedLevel === 'pending_department'
                ? 'bg-amber-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Department ({pendingApprovals?.pending_department.length || 0})
          </button>
        )}
        {canApprove('criterion') && (
          <button
            onClick={() => setSelectedLevel('pending_criterion')}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedLevel === 'pending_criterion'
                ? 'bg-green-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Criterion ({pendingApprovals?.pending_criterion.length || 0})
          </button>
        )}
        {canApprove('iqac') && (
          <button
            onClick={() => setSelectedLevel('pending_iqac')}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedLevel === 'pending_iqac'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            IQAC ({pendingApprovals?.pending_iqac.length || 0})
          </button>
        )}
        {canApprove('head') && (
          <button
            onClick={() => setSelectedLevel('pending_head')}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              selectedLevel === 'pending_head'
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Final ({pendingApprovals?.pending_head.length || 0})
          </button>
        )}
      </div>

      {/* Approvals List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : filteredLevels.length === 0 ? (
        <div className="bg-slate-800 rounded-xl p-12 text-center">
          <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">All Caught Up!</h3>
          <p className="text-slate-400">No pending approvals at your level</p>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredLevels.map((level) => (
            <div key={level.key} className="bg-slate-800 rounded-xl overflow-hidden">
              <div className="p-4 border-b border-slate-700 flex items-center gap-3">
                <span className={`px-3 py-1 rounded-lg text-sm border ${LEVEL_COLORS[level.key]}`}>
                  {LEVEL_LABELS[level.key]}
                </span>
                <span className="text-slate-400 text-sm">
                  {level.items.length} item{level.items.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="divide-y divide-slate-700">
                {level.items.map((workflow) => (
                  <div key={workflow.id} className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FileCheck className="w-5 h-5 text-blue-400" />
                          <h3 className="text-white font-medium">
                            {workflow.record_type.replace(/_/g, ' ')}
                          </h3>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400 mt-2">
                          {workflow.criterion_number && (
                            <span className="px-2 py-0.5 bg-slate-700 rounded text-xs">
                              C{workflow.criterion_number}
                            </span>
                          )}
                          {workflow.department && (
                            <span>{workflow.department}</span>
                          )}
                          {workflow.submitted_by_name && (
                            <span>Submitted by {workflow.submitted_by_name}</span>
                          )}
                          {workflow.submitted_at && (
                            <span>{new Date(workflow.submitted_at).toLocaleDateString()}</span>
                          )}
                        </div>
                        {workflow.submission_remarks && (
                          <p className="text-sm text-slate-400 mt-2 italic">
                            "{workflow.submission_remarks}"
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => {
                            setSelectedWorkflow(workflow)
                            setActionType('approve')
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded-lg text-white text-sm transition-colors"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          Approve
                        </button>
                        <button
                          onClick={() => {
                            setSelectedWorkflow(workflow)
                            setActionType('revision')
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 rounded-lg text-white text-sm transition-colors"
                        >
                          <RotateCcw className="w-4 h-4" />
                          Revision
                        </button>
                        <button
                          onClick={() => {
                            setSelectedWorkflow(workflow)
                            setActionType('reject')
                          }}
                          className="flex items-center gap-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded-lg text-white text-sm transition-colors"
                        >
                          <XCircle className="w-4 h-4" />
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Action Modal */}
      {selectedWorkflow && actionType && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              {actionType === 'approve' && (
                <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                </div>
              )}
              {actionType === 'revision' && (
                <div className="w-10 h-10 bg-amber-500/20 rounded-full flex items-center justify-center">
                  <RotateCcw className="w-5 h-5 text-amber-500" />
                </div>
              )}
              {actionType === 'reject' && (
                <div className="w-10 h-10 bg-red-500/20 rounded-full flex items-center justify-center">
                  <XCircle className="w-5 h-5 text-red-500" />
                </div>
              )}
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {actionType === 'approve' && 'Approve Submission'}
                  {actionType === 'revision' && 'Request Revision'}
                  {actionType === 'reject' && 'Reject Submission'}
                </h3>
                <p className="text-sm text-slate-400">
                  {selectedWorkflow.record_type.replace(/_/g, ' ')}
                </p>
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-400 mb-2">
                {actionType === 'approve' ? 'Remarks (optional)' : 'Reason (required)'}
              </label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder={
                  actionType === 'approve'
                    ? 'Add any comments...'
                    : actionType === 'revision'
                    ? 'Describe what needs to be revised...'
                    : 'Provide the reason for rejection...'
                }
                rows={3}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            {actionType === 'reject' && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-400">
                    This will reject the submission and return it to the submitter.
                    This action cannot be undone.
                  </p>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setSelectedWorkflow(null)
                  setActionType(null)
                  setRemarks('')
                }}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAction}
                disabled={
                  submitting ||
                  (actionType !== 'approve' && !remarks.trim())
                }
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  actionType === 'approve'
                    ? 'bg-green-600 hover:bg-green-700'
                    : actionType === 'revision'
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    {actionType === 'approve' && <CheckCircle2 className="w-4 h-4" />}
                    {actionType === 'revision' && <RotateCcw className="w-4 h-4" />}
                    {actionType === 'reject' && <XCircle className="w-4 h-4" />}
                  </>
                )}
                {actionType === 'approve' && 'Approve'}
                {actionType === 'revision' && 'Request Revision'}
                {actionType === 'reject' && 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
