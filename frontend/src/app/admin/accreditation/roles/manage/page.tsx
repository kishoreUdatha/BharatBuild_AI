'use client'

import React, { useState, useEffect } from 'react'
import apiClient from '@/lib/api-client'
import {
  Search,
  Plus,
  Trash2,
  User,
  Shield,
  Calendar,
  Building,
  ChevronDown,
  X,
  Check,
  Loader2,
} from 'lucide-react'

interface NAACRole {
  id: string
  role_type: string
  display_name: string
  description: string
  hierarchy_level: number
  can_access_all_criteria: boolean
  can_access_all_departments: boolean
  allowed_criteria: number[] | null
  can_approve_level: number | null
}

interface UserWithRoles {
  user_id: string
  email: string
  full_name: string | null
  department: string | null
  roles: Array<{
    id: string
    role_type: string
    role_display_name: string
    criterion_number: number | null
    department: string | null
    assigned_at: string
    is_active: boolean
  }>
}

interface UserSearchResult {
  id: string
  email: string
  full_name: string | null
  department: string | null
}

export default function RoleManagementPage() {
  const [availableRoles, setAvailableRoles] = useState<NAACRole[]>([])
  const [usersWithRoles, setUsersWithRoles] = useState<UserWithRoles[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  // Modal state
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(null)
  const [selectedRole, setSelectedRole] = useState<string>('')
  const [criterionNumber, setCriterionNumber] = useState<number | null>(null)
  const [department, setDepartment] = useState('')
  const [assignmentNotes, setAssignmentNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // User search
  const [userSearch, setUserSearch] = useState('')
  const [userSearchResults, setUserSearchResults] = useState<UserSearchResult[]>([])
  const [searchingUsers, setSearchingUsers] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [rolesData, usersData] = await Promise.all([
        apiClient.get('/naac/rbac/roles'),
        apiClient.get('/naac/rbac/users-with-roles'),
      ])
      setAvailableRoles(rolesData.roles || [])
      setUsersWithRoles(usersData || [])
    } catch (err) {
      console.error('Failed to fetch data:', err)
    } finally {
      setLoading(false)
    }
  }

  const searchUsers = async (query: string) => {
    if (query.length < 2) {
      setUserSearchResults([])
      return
    }

    try {
      setSearchingUsers(true)
      const data = await apiClient.get(`/users/search?q=${encodeURIComponent(query)}&limit=10`)
      setUserSearchResults(data.users || data || [])
    } catch (err) {
      console.error('Failed to search users:', err)
      setUserSearchResults([])
    } finally {
      setSearchingUsers(false)
    }
  }

  const handleAssignRole = async () => {
    if (!selectedUser || !selectedRole) return

    try {
      setSubmitting(true)
      await apiClient.post('/naac/rbac/assign-role', {
        user_id: selectedUser.id,
        role_type: selectedRole,
        criterion_number: criterionNumber,
        department: department || null,
        assignment_notes: assignmentNotes || null,
      })

      // Refresh data
      await fetchData()

      // Reset modal
      setShowAssignModal(false)
      setSelectedUser(null)
      setSelectedRole('')
      setCriterionNumber(null)
      setDepartment('')
      setAssignmentNotes('')
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to assign role')
    } finally {
      setSubmitting(false)
    }
  }

  const handleRevokeRole = async (assignmentId: string) => {
    if (!confirm('Are you sure you want to revoke this role assignment?')) return

    try {
      await apiClient.delete(`/naac/rbac/revoke-role/${assignmentId}`)
      await fetchData()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to revoke role')
    }
  }

  const selectedRoleInfo = availableRoles.find(r => r.role_type === selectedRole)

  const filteredUsers = usersWithRoles.filter(u =>
    u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.full_name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getRoleBadgeColor = (roleType: string) => {
    const colors: Record<string, string> = {
      head_of_institution: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      iqac_coordinator: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      criterion_coordinator: 'bg-green-500/20 text-green-400 border-green-500/30',
      department_coordinator: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      documentation_team: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
      it_data_analytics: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
      ssr_drafting_committee: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
      student_representative: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
      administrative_officer: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
      alumni_coordinator: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      placement_officer: 'bg-lime-500/20 text-lime-400 border-lime-500/30',
    }
    return colors[roleType] || 'bg-slate-500/20 text-slate-400 border-slate-500/30'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">NAAC Role Management</h1>
          <p className="text-slate-400 mt-1">Assign and manage NAAC roles for users</p>
        </div>
        <button
          onClick={() => setShowAssignModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          Assign Role
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
        <input
          type="text"
          placeholder="Search users by email or name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Available Roles Info */}
      <div className="bg-slate-800 rounded-xl p-4 mb-6">
        <h3 className="text-sm font-medium text-slate-400 mb-3">Available Roles ({availableRoles.length})</h3>
        <div className="flex flex-wrap gap-2">
          {availableRoles.map((role) => (
            <div
              key={role.id}
              className={`px-3 py-1.5 rounded-lg text-sm border ${getRoleBadgeColor(role.role_type)}`}
              title={role.description}
            >
              {role.display_name}
            </div>
          ))}
        </div>
      </div>

      {/* Users List */}
      <div className="bg-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-700">
          <h3 className="text-lg font-semibold text-white">Users with NAAC Roles ({filteredUsers.length})</h3>
        </div>
        <div className="divide-y divide-slate-700">
          {filteredUsers.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No users with NAAC roles found
            </div>
          ) : (
            filteredUsers.map((user) => (
              <div key={user.user_id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-slate-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">{user.full_name || user.email}</p>
                      <p className="text-sm text-slate-400">{user.email}</p>
                      {user.department && (
                        <p className="text-xs text-slate-500 mt-1">
                          <Building className="w-3 h-3 inline mr-1" />
                          {user.department}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* User's roles */}
                <div className="mt-3 ml-13 space-y-2">
                  {user.roles.map((role) => (
                    <div
                      key={role.id}
                      className="flex items-center justify-between bg-slate-700/50 rounded-lg p-2"
                    >
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-blue-400" />
                        <span className={`px-2 py-0.5 rounded text-xs border ${getRoleBadgeColor(role.role_type)}`}>
                          {role.role_display_name}
                        </span>
                        {role.criterion_number && (
                          <span className="text-xs text-slate-400">
                            C{role.criterion_number}
                          </span>
                        )}
                        {role.department && (
                          <span className="text-xs text-slate-400">
                            {role.department}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleRevokeRole(role.id)}
                        className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                        title="Revoke role"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Assign Role Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-xl p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Assign NAAC Role</h3>
              <button
                onClick={() => setShowAssignModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* User Search */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Select User
              </label>
              {selectedUser ? (
                <div className="flex items-center justify-between bg-slate-700 rounded-lg p-3">
                  <div>
                    <p className="text-white">{selectedUser.full_name || selectedUser.email}</p>
                    <p className="text-xs text-slate-400">{selectedUser.email}</p>
                  </div>
                  <button
                    onClick={() => setSelectedUser(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search by email or name..."
                    value={userSearch}
                    onChange={(e) => {
                      setUserSearch(e.target.value)
                      searchUsers(e.target.value)
                    }}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                  />
                  {searchingUsers && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-slate-400" />
                  )}
                  {userSearchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-700 border border-slate-600 rounded-lg overflow-hidden z-10">
                      {userSearchResults.map((user) => (
                        <button
                          key={user.id}
                          onClick={() => {
                            setSelectedUser(user)
                            setUserSearch('')
                            setUserSearchResults([])
                          }}
                          className="w-full px-3 py-2 text-left hover:bg-slate-600 transition-colors"
                        >
                          <p className="text-white text-sm">{user.full_name || user.email}</p>
                          <p className="text-xs text-slate-400">{user.email}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Role Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Role
              </label>
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">Select a role...</option>
                {availableRoles.map((role) => (
                  <option key={role.id} value={role.role_type}>
                    {role.display_name}
                  </option>
                ))}
              </select>
              {selectedRoleInfo && (
                <p className="text-xs text-slate-400 mt-1">{selectedRoleInfo.description}</p>
              )}
            </div>

            {/* Criterion Number (for criterion-specific roles) */}
            {selectedRoleInfo && !selectedRoleInfo.can_access_all_criteria && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Criterion Number
                </label>
                <select
                  value={criterionNumber || ''}
                  onChange={(e) => setCriterionNumber(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">Select criterion...</option>
                  {[1, 2, 3, 4, 5, 6, 7].map((c) => (
                    <option key={c} value={c}>Criterion {c}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Department (for department-specific roles) */}
            {selectedRoleInfo && !selectedRoleInfo.can_access_all_departments && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-400 mb-2">
                  Department
                </label>
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="e.g., Computer Science"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
                />
              </div>
            )}

            {/* Notes */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Notes (optional)
              </label>
              <textarea
                value={assignmentNotes}
                onChange={(e) => setAssignmentNotes(e.target.value)}
                placeholder="Add any notes about this assignment..."
                rows={2}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => setShowAssignModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAssignRole}
                disabled={!selectedUser || !selectedRole || submitting}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg text-white transition-colors"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                Assign Role
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
