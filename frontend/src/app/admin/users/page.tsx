'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import { useAdminStore } from '@/store/adminStore'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { useAdminUsers, AdminUser } from '@/hooks/admin/useAdminUsers'
import {
  Search,
  Filter,
  Download,
  MoreVertical,
  UserCheck,
  UserX,
  Trash2,
  Edit,
  Shield,
  ChevronUp,
  ChevronDown,
  CheckSquare,
  Square
} from 'lucide-react'

// Action Menu Component with Portal
function ActionMenu({
  user,
  isDark,
  onClose,
  onSuspend,
  onActivate,
  onDelete,
  deleteConfirm,
  buttonId
}: {
  user: AdminUser
  isDark: boolean
  onClose: () => void
  onSuspend: () => void
  onActivate: () => void
  onDelete: () => void
  deleteConfirm: boolean
  buttonId: string
}) {
  const menuRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)

  useEffect(() => {
    const button = document.getElementById(buttonId)
    if (button) {
      const rect = button.getBoundingClientRect()
      setPosition({
        top: rect.bottom + 4,
        left: Math.max(8, rect.right - 160)
      })
    }

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node
      if (menuRef.current && !menuRef.current.contains(target) &&
          !document.getElementById(buttonId)?.contains(target)) {
        onClose()
      }
    }

    const handleScroll = () => onClose()

    document.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('scroll', handleScroll, true)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [buttonId, onClose])

  if (!position) return null

  const menuContent = (
    <div
      ref={menuRef}
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        zIndex: 9999
      }}
      className={`w-40 rounded-lg shadow-xl border py-1 ${
        isDark
          ? 'bg-[#1e1e1e] border-[#404040]'
          : 'bg-white border-gray-200'
      }`}
    >
      <button
        onClick={user.is_active ? onSuspend : onActivate}
        className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm transition-colors ${
          isDark
            ? 'text-gray-200 hover:bg-[#333]'
            : 'text-gray-700 hover:bg-gray-100'
        }`}
      >
        {user.is_active ? (
          <>
            <UserX className="w-4 h-4 text-orange-400" />
            Suspend
          </>
        ) : (
          <>
            <UserCheck className="w-4 h-4 text-green-400" />
            Activate
          </>
        )}
      </button>
      <button
        onClick={onDelete}
        className={`w-full flex items-center gap-2 px-4 py-2.5 text-sm transition-colors ${
          deleteConfirm
            ? 'bg-red-500/20 text-red-400'
            : isDark
              ? 'text-red-400 hover:bg-[#333]'
              : 'text-red-600 hover:bg-gray-100'
        }`}
      >
        <Trash2 className="w-4 h-4" />
        {deleteConfirm ? 'Click to Confirm' : 'Delete'}
      </button>
    </div>
  )

  if (typeof window !== 'undefined') {
    return createPortal(menuContent, document.body)
  }

  return null
}

const ROLES = [
  { value: '', label: 'All Roles' },
  { value: 'student', label: 'Student' },
  { value: 'developer', label: 'Developer' },
  { value: 'founder', label: 'Founder' },
  { value: 'faculty', label: 'Faculty' },
  { value: 'admin', label: 'Admin' },
  { value: 'api_partner', label: 'API Partner' },
]

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

export default function AdminUsersPage() {
  const { theme } = useAdminTheme()
  const { selectedUsers, toggleUserSelection, selectAllUsers, clearSelectedUsers } = useAdminStore()

  const {
    users,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    sortBy,
    sortOrder,
    refresh,
    goToPage,
    changePageSize,
    handleSearch,
    handleRoleFilter,
    handleActiveFilter,
    handleSort,
    suspendUser,
    activateUser,
    deleteUser,
    bulkAction,
    exportUsers,
  } = useAdminUsers({ initialPageSize: 10 })

  const [searchInput, setSearchInput] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('')
  const [actionMenuUser, setActionMenuUser] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const isDark = theme === 'dark'
  const debouncedSearch = useDebounce(searchInput, 300)

  useEffect(() => {
    handleSearch(debouncedSearch)
  }, [debouncedSearch, handleSearch])

  const onRoleChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    setSelectedRole(value)
    handleRoleFilter(value)
  }, [handleRoleFilter])

  const onStatusChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    setSelectedStatus(value)
    if (value === '') {
      handleActiveFilter(null)
    } else {
      handleActiveFilter(value === 'true')
    }
  }, [handleActiveFilter])

  const handleSelectAll = () => {
    if (selectedUsers.length === users.length) {
      clearSelectedUsers()
    } else {
      selectAllUsers(users.map((u) => u.id))
    }
  }

  const handleBulkSuspend = async () => {
    if (selectedUsers.length === 0) return
    try {
      await bulkAction(selectedUsers, 'suspend')
      clearSelectedUsers()
    } catch (err) {
      console.error('Bulk suspend failed:', err)
    }
  }

  const handleBulkActivate = async () => {
    if (selectedUsers.length === 0) return
    try {
      await bulkAction(selectedUsers, 'activate')
      clearSelectedUsers()
    } catch (err) {
      console.error('Bulk activate failed:', err)
    }
  }

  const handleDeleteClick = async (userId: string) => {
    if (deleteConfirm === userId) {
      try {
        await deleteUser(userId)
        setDeleteConfirm(null)
      } catch (err) {
        console.error('Delete failed:', err)
      }
    } else {
      setDeleteConfirm(userId)
      setTimeout(() => setDeleteConfirm(null), 3000)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-500/20 text-red-400'
      case 'faculty':
        return 'bg-purple-500/20 text-purple-400'
      case 'developer':
        return 'bg-blue-500/20 text-blue-400'
      case 'founder':
        return 'bg-orange-500/20 text-orange-400'
      case 'api_partner':
        return 'bg-cyan-500/20 text-cyan-400'
      default:
        return 'bg-gray-500/20 text-gray-400'
    }
  }

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) {
      return <div className="w-4 h-4" />
    }
    return sortOrder === 'asc' ? (
      <ChevronUp className="w-4 h-4 text-blue-400" />
    ) : (
      <ChevronDown className="w-4 h-4 text-blue-400" />
    )
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="User Management"
        subtitle={`${total} users total`}
        onRefresh={refresh}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Filters */}
        <div className={`flex flex-wrap items-center gap-4 mb-6 p-4 rounded-xl ${
          isDark ? 'bg-[#1a1a1a]' : 'bg-white'
        }`}>
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${
              isDark ? 'text-gray-500' : 'text-gray-400'
            }`} />
            <input
              type="text"
              placeholder="Search users..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className={`w-full pl-10 pr-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                  : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
              } outline-none focus:border-blue-500`}
            />
          </div>

          {/* Role Filter */}
          <select
            value={selectedRole}
            onChange={onRoleChange}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            {ROLES.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={onStatusChange}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            <option value="">All Status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>

          {/* Export */}
          <button
            onClick={exportUsers}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
              isDark
                ? 'bg-[#252525] text-white hover:bg-[#333]'
                : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
            }`}
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>

        {/* Bulk Actions */}
        {selectedUsers.length > 0 && (
          <div className={`flex items-center gap-4 mb-4 p-4 rounded-xl ${
            isDark ? 'bg-blue-500/10 border border-blue-500/30' : 'bg-blue-50 border border-blue-200'
          }`}>
            <span className={`text-sm font-medium ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
              {selectedUsers.length} user{selectedUsers.length > 1 ? 's' : ''} selected
            </span>
            <div className="flex-1" />
            <button
              onClick={handleBulkActivate}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-green-500/20 text-green-400 hover:bg-green-500/30"
            >
              <UserCheck className="w-4 h-4" />
              Activate
            </button>
            <button
              onClick={handleBulkSuspend}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-orange-500/20 text-orange-400 hover:bg-orange-500/30"
            >
              <UserX className="w-4 h-4" />
              Suspend
            </button>
            <button
              onClick={clearSelectedUsers}
              className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'} hover:underline`}
            >
              Clear
            </button>
          </div>
        )}

        {/* Table */}
        <div className={`rounded-xl border ${
          isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
        }`}>
          <div className="overflow-x-auto overflow-y-visible">
            <table className="w-full">
              <thead>
                <tr className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
                  <th className="w-12 px-4 py-3">
                    <button onClick={handleSelectAll}>
                      {selectedUsers.length === users.length && users.length > 0 ? (
                        <CheckSquare className="w-5 h-5 text-blue-400" />
                      ) : (
                        <Square className={`w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                      )}
                    </button>
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('email')}
                  >
                    <div className="flex items-center gap-1">
                      User
                      <SortIcon field="email" />
                    </div>
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('role')}
                  >
                    <div className="flex items-center gap-1">
                      Role
                      <SortIcon field="role" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Status
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Plan
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Projects
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider cursor-pointer ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('created_at')}
                  >
                    <div className="flex items-center gap-1">
                      Joined
                      <SortIcon field="created_at" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={8} className="px-4 py-4">
                        <div className="animate-pulse flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-full ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                          <div className="flex-1 space-y-2">
                            <div className={`h-4 w-48 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                            <div className={`h-3 w-32 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={8} className={`px-4 py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No users found
                    </td>
                  </tr>
                ) : (
                  users.map((user) => (
                    <tr
                      key={user.id}
                      className={`transition-colors ${
                        isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'
                      } ${selectedUsers.includes(user.id) ? (isDark ? 'bg-blue-500/5' : 'bg-blue-50') : ''}`}
                    >
                      <td className="px-4 py-4">
                        <button onClick={() => toggleUserSelection(user.id)}>
                          {selectedUsers.includes(user.id) ? (
                            <CheckSquare className="w-5 h-5 text-blue-400" />
                          ) : (
                            <Square className={`w-5 h-5 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium">
                            {user.full_name?.charAt(0) || user.email.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {user.full_name || 'Unnamed User'}
                            </div>
                            <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getRoleBadgeColor(user.role)}`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${user.is_active ? 'bg-green-500' : 'bg-gray-500'}`} />
                          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                            {user.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                          user.subscription_plan === 'Enterprise' ? 'bg-orange-500/20 text-orange-400' :
                          user.subscription_plan === 'Pro' ? 'bg-purple-500/20 text-purple-400' :
                          user.subscription_plan === 'Basic' ? 'bg-green-500/20 text-green-400' :
                          user.subscription_plan === 'Student' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {user.subscription_plan || 'Free'}
                        </span>
                      </td>
                      <td className={`px-4 py-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {user.projects_count}
                      </td>
                      <td className={`px-4 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-4 py-4">
                        <div className="relative">
                          <button
                            id={`action-btn-${user.id}`}
                            onClick={() => setActionMenuUser(actionMenuUser === user.id ? null : user.id)}
                            className={`p-2 rounded-lg ${
                              isDark ? 'hover:bg-[#333]' : 'hover:bg-gray-100'
                            }`}
                          >
                            <MoreVertical className="w-4 h-4" />
                          </button>

                          {actionMenuUser === user.id && (
                            <ActionMenu
                              user={user}
                              isDark={isDark}
                              buttonId={`action-btn-${user.id}`}
                              onClose={() => setActionMenuUser(null)}
                              onSuspend={() => {
                                setActionMenuUser(null)
                                suspendUser(user.id)
                              }}
                              onActivate={() => {
                                setActionMenuUser(null)
                                activateUser(user.id)
                              }}
                              onDelete={() => {
                                setActionMenuUser(null)
                                handleDeleteClick(user.id)
                              }}
                              deleteConfirm={deleteConfirm === user.id}
                            />
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={`px-4 py-3 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                pageSize={pageSize}
                totalItems={total}
                onPageChange={goToPage}
                onPageSizeChange={changePageSize}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
