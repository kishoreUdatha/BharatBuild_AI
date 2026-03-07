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
  Upload,
  FileText,
  Building,
} from 'lucide-react'
import Link from 'next/link'

export default function DepartmentCoordinatorDashboard() {
  const { roles, taskSummary, notifications } = useNAACRole()
  const [myTasks, setMyTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  // Get assigned department from role
  const deptRole = roles.find(r => r.role_type === 'department_coordinator')
  const assignedDepartment = deptRole?.department || 'Unknown Department'
  const assignedCriterion = deptRole?.criterion_number

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

  const pendingTasks = myTasks.filter(t => ['pending', 'assigned'].includes(t.status))
  const inProgressTasks = myTasks.filter(t => t.status === 'in_progress')
  const overdueTasks = myTasks.filter(t => t.status === 'overdue')

  return (
    <div className="space-y-6">
      {/* Department Header */}
      <div className="bg-gradient-to-r from-slate-700 to-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-blue-500/20 rounded-xl flex items-center justify-center">
            <Building className="w-8 h-8 text-blue-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-white">{assignedDepartment}</h2>
            <p className="text-slate-400">
              Department Coordinator
              {assignedCriterion && ` - Criterion ${assignedCriterion}`}
            </p>
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
          href="/admin/accreditation/tasks"
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
        >
          <FileText className="w-4 h-4" />
          View My Tasks
          {pendingTasks.length > 0 && (
            <span className="bg-amber-500 text-white text-xs px-2 py-0.5 rounded-full">
              {pendingTasks.length}
            </span>
          )}
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Pending Tasks</p>
              <p className="text-2xl font-bold text-white">{pendingTasks.length}</p>
            </div>
            <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-amber-500" />
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">In Progress</p>
              <p className="text-2xl font-bold text-white">{inProgressTasks.length}</p>
            </div>
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
              <FileCheck className="w-5 h-5 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Completed</p>
              <p className="text-2xl font-bold text-white">{taskSummary?.completed || 0}</p>
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
              <p className="text-2xl font-bold text-white">{overdueTasks.length}</p>
            </div>
            <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
          </div>
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

        {myTasks.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-2" />
            <p className="text-slate-400">No tasks assigned</p>
          </div>
        ) : (
          <div className="space-y-3">
            {myTasks.slice(0, 8).map((task) => (
              <Link
                key={task.id}
                href={`/admin/accreditation/tasks/${task.id}`}
                className="block bg-slate-700/50 hover:bg-slate-700 rounded-lg p-4 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium">{task.title}</p>
                    <p className="text-sm text-slate-400 mt-1 line-clamp-2">
                      {task.description || 'No description'}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                      {task.criterion_number && (
                        <span className="px-2 py-0.5 bg-slate-600 rounded">
                          C{task.criterion_number}
                        </span>
                      )}
                      {task.due_date && (
                        <span className={task.status === 'overdue' ? 'text-red-400' : ''}>
                          Due: {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      )}
                      {task.priority && (
                        <span className={`${
                          task.priority === 'critical' ? 'text-red-400' :
                          task.priority === 'high' ? 'text-amber-400' :
                          ''
                        }`}>
                          {task.priority}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full whitespace-nowrap ml-3 ${
                    task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    task.status === 'overdue' ? 'bg-red-500/20 text-red-400' :
                    task.status === 'in_progress' ? 'bg-blue-500/20 text-blue-400' :
                    task.status === 'submitted' ? 'bg-purple-500/20 text-purple-400' :
                    'bg-slate-600 text-slate-300'
                  }`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Notifications */}
      <div className="bg-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Notifications</h3>
        <div className="space-y-3">
          {notifications.slice(0, 5).map((notif) => (
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
