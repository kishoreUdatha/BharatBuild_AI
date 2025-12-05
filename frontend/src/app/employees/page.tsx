'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useEmployees } from '@/hooks/useEmployees'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'

const ROLES = [
  { value: '', label: 'All Roles' },
  { value: 'student', label: 'Student' },
  { value: 'developer', label: 'Developer' },
  { value: 'founder', label: 'Founder' },
  { value: 'faculty', label: 'Faculty' },
  { value: 'admin', label: 'Admin' },
  { value: 'api_partner', label: 'API Partner' },
]

// Debounce hook for auto-search
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

export default function EmployeesPage() {
  const router = useRouter()
  const {
    employees,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    sortBy,
    sortOrder,
    stats,
    refresh,
    goToPage,
    changePageSize,
    handleSearch,
    handleRoleFilter,
    handleActiveFilter,
    handleSort,
    deleteEmployee,
  } = useEmployees({ initialPageSize: 10 })

  const [searchInput, setSearchInput] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<string>('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)

  // Debounce search input - auto search after 300ms of no typing
  const debouncedSearch = useDebounce(searchInput, 300)

  // Auto-search when debounced value changes
  useEffect(() => {
    handleSearch(debouncedSearch)
  }, [debouncedSearch, handleSearch])

  // Handle role filter change
  const onRoleChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    setSelectedRole(value)
    handleRoleFilter(value)
  }, [handleRoleFilter])

  // Handle status filter change
  const onStatusChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    setSelectedStatus(value)
    if (value === '') {
      handleActiveFilter(null)
    } else {
      handleActiveFilter(value === 'true')
    }
  }, [handleActiveFilter])

  // Seed sample data for testing
  const handleSeedData = async () => {
    setSeeding(true)
    try {
      await apiClient.post('/users/seed-sample-data?count=50')
      refresh()
    } catch (err) {
      console.error('Failed to seed data:', err)
    } finally {
      setSeeding(false)
    }
  }

  const handleDeleteClick = async (userId: string) => {
    if (deleteConfirm === userId) {
      try {
        await deleteEmployee(userId)
        setDeleteConfirm(null)
      } catch (err) {
        console.error('Delete failed:', err)
      }
    } else {
      setDeleteConfirm(userId)
      // Auto-reset confirm after 3 seconds
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

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) {
      return (
        <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      )
    }
    return sortOrder === 'asc' ? (
      <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    )
  }

  const TableHeader = ({ field, label }: { field: string; label: string }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <SortIcon field={field} />
      </div>
    </th>
  )

  return (
    <div className="min-h-screen bg-[#121212]">
      {/* Header */}
      <header className="bg-[#1a1a1a] border-b border-[#333]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push('/')}
                className="flex items-center gap-2 hover:opacity-80 transition-opacity"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                  </svg>
                </div>
                <span className="text-white font-semibold text-lg">BharatBuild AI</span>
              </button>
            </div>

            <nav className="flex items-center gap-6">
              <button
                onClick={() => router.push('/bolt')}
                className="text-gray-400 hover:text-white transition-colors text-sm"
              >
                Workspace
              </button>
              <button
                onClick={() => router.push('/projects')}
                className="text-gray-400 hover:text-white transition-colors text-sm"
              >
                Projects
              </button>
              <button className="text-white font-medium text-sm">
                Employees
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-[#1a1a1a] border border-[#333] rounded-lg p-4">
              <div className="text-2xl font-bold text-white">{stats.total_users}</div>
              <div className="text-sm text-gray-400">Total Users</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded-lg p-4">
              <div className="text-2xl font-bold text-green-400">{stats.active_users}</div>
              <div className="text-sm text-gray-400">Active Users</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded-lg p-4">
              <div className="text-2xl font-bold text-blue-400">{stats.verified_users}</div>
              <div className="text-sm text-gray-400">Verified Users</div>
            </div>
            <div className="bg-[#1a1a1a] border border-[#333] rounded-lg p-4">
              <div className="text-2xl font-bold text-purple-400">{stats.new_users_this_month}</div>
              <div className="text-sm text-gray-400">New This Month</div>
            </div>
          </div>
        )}

        {/* Page Title & Filters */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Employees</h1>
            <p className="text-gray-400">
              {total} user{total !== 1 ? 's' : ''} found
              {searchInput && <span className="text-blue-400"> matching "{searchInput}"</span>}
            </p>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Search - Auto lookup */}
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <input
                type="text"
                placeholder="Search name, email, org..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="bg-[#252525] border border-[#333] rounded-lg pl-10 pr-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500 w-64"
              />
              {searchInput && (
                <button
                  onClick={() => setSearchInput('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>

            {/* Role Filter */}
            <select
              value={selectedRole}
              onChange={onRoleChange}
              className="bg-[#252525] border border-[#333] rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
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
              className="bg-[#252525] border border-[#333] rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>

            {/* Seed Sample Data Button */}
            <button
              onClick={handleSeedData}
              disabled={seeding}
              className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
              title="Add 50 sample employees"
            >
              {seeding ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              )}
              {seeding ? 'Adding...' : 'Add Sample Data'}
            </button>

            {/* Refresh Button */}
            <button
              onClick={refresh}
              disabled={loading}
              className="p-2 bg-[#252525] border border-[#333] rounded-lg text-gray-400 hover:text-white hover:border-[#444] transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <svg className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
            </button>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <svg className="w-8 h-8 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-gray-400">Loading employees...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="flex items-center justify-center py-20">
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md text-center">
              <svg className="w-12 h-12 text-red-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              <h3 className="text-lg font-semibold text-white mb-2">Error Loading Employees</h3>
              <p className="text-gray-400 mb-4">{error}</p>
              <button
                onClick={refresh}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && employees.length === 0 && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center max-w-md">
              <div className="w-20 h-20 bg-[#252525] rounded-full flex items-center justify-center mx-auto mb-6">
                <svg className="w-10 h-10 text-gray-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">No employees found</h3>
              <p className="text-gray-400 mb-4">
                {searchInput || selectedRole || selectedStatus
                  ? 'Try adjusting your search or filters'
                  : 'No users have been registered yet'}
              </p>
              {(searchInput || selectedRole || selectedStatus) && (
                <button
                  onClick={() => {
                    setSearchInput('')
                    setSelectedRole('')
                    setSelectedStatus('')
                    handleSearch('')
                    handleRoleFilter('')
                    handleActiveFilter(null)
                  }}
                  className="text-blue-400 hover:text-blue-300 text-sm"
                >
                  Clear all filters
                </button>
              )}
            </div>
          </div>
        )}

        {/* Data Table */}
        {!loading && !error && employees.length > 0 && (
          <>
            <div className="bg-[#1a1a1a] border border-[#333] rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-[#252525]">
                    <tr>
                      <TableHeader field="full_name" label="Name" />
                      <TableHeader field="email" label="Email" />
                      <TableHeader field="role" label="Role" />
                      <TableHeader field="organization" label="Organization" />
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Status
                      </th>
                      <TableHeader field="created_at" label="Joined" />
                      <TableHeader field="last_login" label="Last Login" />
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#333]">
                    {employees.map((employee) => (
                      <tr key={employee.id} className="hover:bg-[#252525] transition-colors">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-3">
                            {employee.avatar_url ? (
                              <img
                                src={employee.avatar_url}
                                alt=""
                                className="w-8 h-8 rounded-full"
                              />
                            ) : (
                              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                                {(employee.full_name || employee.email)[0].toUpperCase()}
                              </div>
                            )}
                            <div>
                              <div className="text-sm font-medium text-white">
                                {employee.full_name || '-'}
                              </div>
                              {employee.username && (
                                <div className="text-xs text-gray-500">@{employee.username}</div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-300">{employee.email}</div>
                          {employee.oauth_provider && (
                            <div className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="capitalize">{employee.oauth_provider}</span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                            employee.role === 'admin'
                              ? 'bg-red-500/20 text-red-400'
                              : employee.role === 'developer'
                              ? 'bg-blue-500/20 text-blue-400'
                              : employee.role === 'founder'
                              ? 'bg-purple-500/20 text-purple-400'
                              : employee.role === 'faculty'
                              ? 'bg-yellow-500/20 text-yellow-400'
                              : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {employee.role.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-300">{employee.organization || '-'}</div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                              employee.is_active
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-red-500/20 text-red-400'
                            }`}>
                              {employee.is_active ? 'Active' : 'Inactive'}
                            </span>
                            {employee.is_verified && (
                              <svg className="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 20 20" title="Verified">
                                <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                              </svg>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-300">{formatDate(employee.created_at)}</div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-300">{formatDate(employee.last_login)}</div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleDeleteClick(employee.id)}
                              className={`p-1.5 rounded transition-colors ${
                                deleteConfirm === employee.id
                                  ? 'bg-red-600 text-white'
                                  : 'text-gray-400 hover:text-red-400 hover:bg-red-500/10'
                              }`}
                              title={deleteConfirm === employee.id ? 'Click again to confirm' : 'Deactivate'}
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            <div className="mt-6 border-t border-[#333] pt-6">
              <Pagination
                currentPage={page}
                totalPages={totalPages || 1}
                onPageChange={goToPage}
                pageSize={pageSize}
                onPageSizeChange={changePageSize}
                pageSizeOptions={[5, 10, 20, 50]}
                total={total}
                showTotal={true}
                showPageSize={true}
              />
            </div>
          </>
        )}
      </main>
    </div>
  )
}
