'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { useAdminEnrollments, WorkshopEnrollment } from '@/hooks/admin/useAdminEnrollments'
import {
  Search,
  Download,
  ChevronUp,
  ChevronDown,
  GraduationCap,
  Mail,
  Phone,
  Building,
  Calendar,
  CheckCircle,
  XCircle
} from 'lucide-react'

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

export default function AdminEnrollmentsPage() {
  const { theme } = useAdminTheme()

  const {
    enrollments,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    sortBy,
    sortOrder,
    workshopFilter,
    refresh,
    goToPage,
    changePageSize,
    handleSearch,
    handleWorkshopFilter,
    handleSort,
    exportEnrollments,
    workshopNames,
  } = useAdminEnrollments({ initialPageSize: 10 })

  const [searchInput, setSearchInput] = useState('')
  const [selectedWorkshop, setSelectedWorkshop] = useState('')

  const isDark = theme === 'dark'
  const debouncedSearch = useDebounce(searchInput, 300)

  useEffect(() => {
    handleSearch(debouncedSearch)
  }, [debouncedSearch, handleSearch])

  const onWorkshopChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    setSelectedWorkshop(value)
    handleWorkshopFilter(value)
  }, [handleWorkshopFilter])

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: '2-digit',
    })
  }

  const getYearBadgeColor = (year: string) => {
    switch (year.toLowerCase()) {
      case '1st year':
      case '1':
        return 'bg-green-500/20 text-green-400'
      case '2nd year':
      case '2':
        return 'bg-blue-500/20 text-blue-400'
      case '3rd year':
      case '3':
        return 'bg-purple-500/20 text-purple-400'
      case '4th year':
      case '4':
        return 'bg-orange-500/20 text-orange-400'
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
        title="Workshop Enrollments"
        subtitle={`${total} enrollment${total !== 1 ? 's' : ''} total`}
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
              placeholder="Search by name, email, college, department..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className={`w-full pl-10 pr-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                  : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
              } outline-none focus:border-blue-500`}
            />
          </div>

          {/* Workshop Filter */}
          <select
            value={selectedWorkshop}
            onChange={onWorkshopChange}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            <option value="">All Workshops</option>
            {workshopNames().map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>

          {/* Export */}
          <button
            onClick={exportEnrollments}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
              isDark
                ? 'bg-[#252525] text-white hover:bg-[#333]'
                : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
            }`}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <GraduationCap className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {total}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Total Enrollments
                </p>
              </div>
            </div>
          </div>

          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {enrollments.filter(e => e.is_confirmed).length}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Confirmed
                </p>
              </div>
            </div>
          </div>

          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Building className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {new Set(enrollments.map(e => e.college_name)).size}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Colleges
                </p>
              </div>
            </div>
          </div>

          <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <Calendar className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {workshopNames().length}
                </p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Workshops
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className={`p-4 mb-6 rounded-xl ${isDark ? 'bg-red-500/10 border border-red-500/30' : 'bg-red-50 border border-red-200'}`}>
            <p className={`text-sm ${isDark ? 'text-red-400' : 'text-red-600'}`}>{error}</p>
          </div>
        )}

        {/* Table */}
        <div className={`rounded-xl border ${
          isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
        }`}>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
                  <th
                    className={`px-3 py-2 text-left font-medium uppercase cursor-pointer whitespace-nowrap ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('full_name')}
                  >
                    <div className="flex items-center gap-1">
                      Student
                      <SortIcon field="full_name" />
                    </div>
                  </th>
                  <th className={`px-3 py-2 text-left font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Contact
                  </th>
                  <th
                    className={`px-3 py-2 text-left font-medium uppercase cursor-pointer whitespace-nowrap ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('college_name')}
                  >
                    <div className="flex items-center gap-1">
                      College
                      <SortIcon field="college_name" />
                    </div>
                  </th>
                  <th className={`px-3 py-2 text-left font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Dept
                  </th>
                  <th className={`px-3 py-2 text-left font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Year
                  </th>
                  <th
                    className={`px-3 py-2 text-left font-medium uppercase cursor-pointer whitespace-nowrap ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('workshop_name')}
                  >
                    <div className="flex items-center gap-1">
                      Workshop
                      <SortIcon field="workshop_name" />
                    </div>
                  </th>
                  <th className={`px-3 py-2 text-left font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Status
                  </th>
                  <th
                    className={`px-3 py-2 text-left font-medium uppercase cursor-pointer whitespace-nowrap ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('created_at')}
                  >
                    <div className="flex items-center gap-1">
                      Date
                      <SortIcon field="created_at" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={8} className="px-3 py-3">
                        <div className="animate-pulse flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                          <div className="flex-1 space-y-1">
                            <div className={`h-3 w-32 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                            <div className={`h-2 w-24 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : enrollments.length === 0 ? (
                  <tr>
                    <td colSpan={8} className={`px-3 py-6 text-center text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No enrollments found
                    </td>
                  </tr>
                ) : (
                  enrollments.map((enrollment) => (
                    <tr
                      key={enrollment.id}
                      className={`transition-colors ${
                        isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'
                      }`}
                    >
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
                            {enrollment.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <div className={`font-medium truncate max-w-[120px] ${isDark ? 'text-white' : 'text-gray-900'}`} title={enrollment.full_name}>
                              {enrollment.full_name}
                            </div>
                            {enrollment.roll_number && (
                              <div className={`text-[10px] ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                {enrollment.roll_number}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <div className="space-y-0.5">
                          <div className={`flex items-center gap-1 truncate max-w-[150px] ${isDark ? 'text-gray-300' : 'text-gray-600'}`} title={enrollment.email}>
                            <Mail className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{enrollment.email}</span>
                          </div>
                          <div className={`flex items-center gap-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            <Phone className="w-3 h-3 flex-shrink-0" />
                            {enrollment.phone}
                          </div>
                        </div>
                      </td>
                      <td className={`px-3 py-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        <div className="max-w-[140px] truncate" title={enrollment.college_name}>
                          {enrollment.college_name}
                        </div>
                      </td>
                      <td className={`px-3 py-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        <div className="max-w-[80px] truncate" title={enrollment.department}>
                          {enrollment.department}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${getYearBadgeColor(enrollment.year_of_study)}`}>
                          {enrollment.year_of_study}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-500/20 text-blue-400 max-w-[100px] truncate`} title={enrollment.workshop_name}>
                          {enrollment.workshop_name}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {enrollment.is_confirmed ? (
                          <span className="flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                            <span className={`text-[10px] ${isDark ? 'text-green-400' : 'text-green-600'}`}>OK</span>
                          </span>
                        ) : (
                          <span className="flex items-center gap-1">
                            <XCircle className="w-3.5 h-3.5 text-yellow-500" />
                            <span className={`text-[10px] ${isDark ? 'text-yellow-400' : 'text-yellow-600'}`}>Pending</span>
                          </span>
                        )}
                      </td>
                      <td className={`px-3 py-2 whitespace-nowrap ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(enrollment.created_at)}
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
                total={total}
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
