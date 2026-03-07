'use client'

import React, { useState, useEffect } from 'react'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import apiClient from '@/lib/api-client'
import {
  FileText,
  Upload,
  FolderOpen,
  Search,
  CheckCircle2,
  Clock,
  BookOpen,
  GraduationCap,
  FlaskConical,
  Building,
  Users,
  Settings,
  Heart,
} from 'lucide-react'
import Link from 'next/link'

const CRITERIA = [
  { id: 1, name: 'Curricular Aspects', icon: BookOpen, color: 'orange' },
  { id: 2, name: 'Teaching-Learning', icon: GraduationCap, color: 'blue' },
  { id: 3, name: 'Research & Extension', icon: FlaskConical, color: 'purple' },
  { id: 4, name: 'Infrastructure', icon: Building, color: 'green' },
  { id: 5, name: 'Student Support', icon: Users, color: 'pink' },
  { id: 6, name: 'Governance', icon: Settings, color: 'cyan' },
  { id: 7, name: 'Institutional Values', icon: Heart, color: 'red' },
]

export default function DocumentationTeamDashboard() {
  const { taskSummary, notifications } = useNAACRole()
  const [myTasks, setMyTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const tasksData = await apiClient.get('/naac/rbac/tasks?assigned_to_me=true&page_size=20')
        setMyTasks(tasksData.tasks || [])
      } catch (err) {
        console.error('Failed to fetch tasks:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 rounded-xl p-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
            <FileText className="w-8 h-8 text-white" />
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white">Documentation Team</h2>
            <p className="text-indigo-200">Evidence collection and document organization</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Link
          href="/admin/accreditation/criterion1/evidence"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload Evidence
        </Link>
        <Link
          href="/admin/accreditation"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <FolderOpen className="w-4 h-4" />
          Browse Documents
        </Link>
        <Link
          href="/admin/accreditation/tasks?assigned_to_me=true"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <Search className="w-4 h-4" />
          My Tasks
        </Link>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Pending Tasks</p>
              <p className="text-2xl font-bold text-white">{taskSummary?.pending || 0}</p>
            </div>
            <Clock className="w-8 h-8 text-amber-500" />
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">In Progress</p>
              <p className="text-2xl font-bold text-white">{taskSummary?.in_progress || 0}</p>
            </div>
            <FileText className="w-8 h-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Completed</p>
              <p className="text-2xl font-bold text-white">{taskSummary?.completed || 0}</p>
            </div>
            <CheckCircle2 className="w-8 h-8 text-green-500" />
          </div>
        </div>
      </div>

      {/* Criteria Quick Access */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Criteria Quick Access</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {CRITERIA.map((criterion) => {
            const Icon = criterion.icon
            return (
              <Link
                key={criterion.id}
                href={`/admin/accreditation/criterion${criterion.id}`}
                className={`flex flex-col items-center gap-2 p-4 rounded-lg bg-slate-700/50 hover:bg-${criterion.color}-500/20 border border-transparent hover:border-${criterion.color}-500/50 transition-all group`}
              >
                <div className={`w-10 h-10 bg-${criterion.color}-500/20 group-hover:bg-${criterion.color}-500/30 rounded-lg flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 text-${criterion.color}-400`} />
                </div>
                <span className="text-xs text-slate-300 text-center">C{criterion.id}</span>
              </Link>
            )
          })}
        </div>
      </div>

      {/* My Tasks */}
      <div className="bg-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">My Tasks</h3>
          <Link
            href="/admin/accreditation/tasks?assigned_to_me=true"
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            View all
          </Link>
        </div>
        <div className="space-y-3">
          {myTasks.slice(0, 6).map((task) => (
            <Link
              key={task.id}
              href={`/admin/accreditation/tasks/${task.id}`}
              className="block bg-slate-700/50 hover:bg-slate-700 rounded-lg p-3 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">{task.title}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    {task.criterion_number && `Criterion ${task.criterion_number}`}
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
          {myTasks.length === 0 && (
            <p className="text-slate-400 text-center py-4">No tasks assigned</p>
          )}
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Notifications</h3>
        <div className="space-y-3">
          {notifications.slice(0, 4).map((notif) => (
            <div
              key={notif.id}
              className={`p-3 rounded-lg ${notif.is_read ? 'bg-slate-700/30' : 'bg-slate-700'}`}
            >
              <p className="text-white text-sm font-medium">{notif.title}</p>
              <p className="text-slate-400 text-xs mt-1">{notif.message}</p>
            </div>
          ))}
          {notifications.length === 0 && (
            <p className="text-slate-400 text-center py-4">No notifications</p>
          )}
        </div>
      </div>
    </div>
  )
}
