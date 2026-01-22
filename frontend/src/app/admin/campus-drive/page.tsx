'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import apiClient from '@/lib/api-client'
import {
  Search,
  Download,
  ChevronUp,
  ChevronDown,
  GraduationCap,
  Mail,
  Phone,
  Building,
  Trophy,
  CheckCircle,
  XCircle,
  Users,
  Brain,
  Code,
  BookOpen,
  MessageSquare,
  Plus,
  Eye,
  Percent
} from 'lucide-react'

interface CampusDrive {
  id: string
  name: string
  company_name?: string
  description?: string
  registration_start: string
  registration_end?: string
  quiz_date?: string
  quiz_duration_minutes: number
  passing_percentage: number
  total_questions: number
  is_active: boolean
  created_at: string
}

interface Registration {
  id: string
  campus_drive_id: string
  full_name: string
  email: string
  phone: string
  college_name: string
  department: string
  year_of_study: string
  roll_number?: string
  cgpa?: number
  status: string
  quiz_score?: number
  percentage?: number
  is_qualified: boolean
  logical_score: number
  technical_score: number
  ai_ml_score: number
  english_score: number
  created_at: string
}

interface DriveStats {
  total_registrations: number
  quiz_completed: number
  qualified: number
  not_qualified: number
  average_score: number
  highest_score: number
  lowest_score: number
}

export default function AdminCampusDrivePage() {
  const { theme } = useAdminTheme()
  const isDark = theme === 'dark'

  const [drives, setDrives] = useState<CampusDrive[]>([])
  const [selectedDrive, setSelectedDrive] = useState<CampusDrive | null>(null)
  const [registrations, setRegistrations] = useState<Registration[]>([])
  const [stats, setStats] = useState<DriveStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchInput, setSearchInput] = useState('')
  const [filterQualified, setFilterQualified] = useState<string>('all')
  const [sortBy, setSortBy] = useState<string>('percentage')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const fetchDrives = async () => {
    try {
      const response = await apiClient.get('/api/v1/admin/campus-drive/')
      setDrives(response.data)
      if (response.data.length > 0 && !selectedDrive) {
        setSelectedDrive(response.data[0])
      }
    } catch (error) {
      console.error('Error fetching drives:', error)
    }
  }

  const fetchRegistrations = async (driveId: string) => {
    try {
      setLoading(true)
      const [regResponse, statsResponse] = await Promise.all([
        apiClient.get(`/api/v1/admin/campus-drive/${driveId}/registrations`),
        apiClient.get(`/api/v1/admin/campus-drive/${driveId}/stats`)
      ])
      setRegistrations(regResponse.data)
      setStats(statsResponse.data)
    } catch (error) {
      console.error('Error fetching registrations:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDrives()
  }, [])

  useEffect(() => {
    if (selectedDrive) {
      fetchRegistrations(selectedDrive.id)
    }
  }, [selectedDrive])

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  const exportResults = async () => {
    if (!selectedDrive) return
    try {
      const response = await apiClient.get(
        `/api/v1/admin/campus-drive/${selectedDrive.id}/export?qualified_only=${filterQualified === 'qualified'}`
      )
      const { data, filename } = response.data

      // Convert to CSV
      const csvContent = data.map((row: string[]) => row.join(',')).join('\n')
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Error exporting:', error)
    }
  }

  // Filter and sort registrations
  const filteredRegistrations = registrations
    .filter(r => {
      const matchesSearch = searchInput === '' ||
        r.full_name.toLowerCase().includes(searchInput.toLowerCase()) ||
        r.email.toLowerCase().includes(searchInput.toLowerCase()) ||
        r.college_name.toLowerCase().includes(searchInput.toLowerCase())

      const matchesFilter = filterQualified === 'all' ||
        (filterQualified === 'qualified' && r.is_qualified) ||
        (filterQualified === 'not_qualified' && !r.is_qualified && r.percentage !== null)

      return matchesSearch && matchesFilter
    })
    .sort((a, b) => {
      let aVal = a[sortBy as keyof Registration]
      let bVal = b[sortBy as keyof Registration]

      if (aVal === null || aVal === undefined) aVal = 0
      if (bVal === null || bVal === undefined) bVal = 0

      if (typeof aVal === 'string') {
        return sortOrder === 'asc'
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal)
      }

      return sortOrder === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number)
    })

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <div className="w-4 h-4" />
    return sortOrder === 'asc'
      ? <ChevronUp className="w-4 h-4 text-blue-400" />
      : <ChevronDown className="w-4 h-4 text-blue-400" />
  }

  const getStatusBadge = (reg: Registration) => {
    if (reg.percentage === null || reg.percentage === undefined) {
      return (
        <span className="px-2 py-1 rounded text-xs bg-gray-500/20 text-gray-400">
          Not Started
        </span>
      )
    }
    if (reg.is_qualified) {
      return (
        <span className="px-2 py-1 rounded text-xs bg-green-500/20 text-green-400 flex items-center gap-1">
          <CheckCircle className="w-3 h-3" /> Qualified
        </span>
      )
    }
    return (
      <span className="px-2 py-1 rounded text-xs bg-red-500/20 text-red-400 flex items-center gap-1">
        <XCircle className="w-3 h-3" /> Not Qualified
      </span>
    )
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Campus Drive Management"
        subtitle={selectedDrive ? `${selectedDrive.name}` : 'Select a drive'}
        onRefresh={() => selectedDrive && fetchRegistrations(selectedDrive.id)}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Drive Selector */}
        <div className={`flex flex-wrap items-center gap-4 mb-6 p-4 rounded-xl ${
          isDark ? 'bg-[#1a1a1a]' : 'bg-white'
        }`}>
          <select
            value={selectedDrive?.id || ''}
            onChange={(e) => {
              const drive = drives.find(d => d.id === e.target.value)
              if (drive) setSelectedDrive(drive)
            }}
            className={`flex-1 min-w-[200px] px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            {drives.map(drive => (
              <option key={drive.id} value={drive.id}>
                {drive.name} {drive.company_name ? `- ${drive.company_name}` : ''}
              </option>
            ))}
          </select>

          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${
              isDark ? 'text-gray-500' : 'text-gray-400'
            }`} />
            <input
              type="text"
              placeholder="Search by name, email, college..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className={`w-full pl-10 pr-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                  : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
              } outline-none focus:border-blue-500`}
            />
          </div>

          {/* Filter */}
          <select
            value={filterQualified}
            onChange={(e) => setFilterQualified(e.target.value)}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            <option value="all">All Students</option>
            <option value="qualified">Qualified Only</option>
            <option value="not_qualified">Not Qualified</option>
          </select>

          {/* Export */}
          <button
            onClick={exportResults}
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
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <Users className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.total_registrations}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Total Registered
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.quiz_completed}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Quiz Done
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <Trophy className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.qualified}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Qualified
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                  <XCircle className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.not_qualified}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Not Qualified
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                  <Percent className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.average_score.toFixed(1)}%
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Avg Score
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                  <ChevronUp className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.highest_score.toFixed(1)}%
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Highest
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                  <ChevronDown className="w-5 h-5 text-orange-400" />
                </div>
                <div>
                  <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {stats.lowest_score.toFixed(1)}%
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Lowest
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Results Table */}
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
                    Dept/Year
                  </th>
                  <th
                    className={`px-3 py-2 text-center font-medium uppercase cursor-pointer whitespace-nowrap ${
                      isDark ? 'text-gray-400' : 'text-gray-500'
                    }`}
                    onClick={() => handleSort('percentage')}
                  >
                    <div className="flex items-center justify-center gap-1">
                      Score
                      <SortIcon field="percentage" />
                    </div>
                  </th>
                  <th className={`px-3 py-2 text-center font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    <span title="Logical"><Brain className="w-4 h-4 mx-auto text-blue-400" /></span>
                  </th>
                  <th className={`px-3 py-2 text-center font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    <span title="Technical"><Code className="w-4 h-4 mx-auto text-green-400" /></span>
                  </th>
                  <th className={`px-3 py-2 text-center font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    <span title="AI/ML"><BookOpen className="w-4 h-4 mx-auto text-purple-400" /></span>
                  </th>
                  <th className={`px-3 py-2 text-center font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    <span title="English"><MessageSquare className="w-4 h-4 mx-auto text-orange-400" /></span>
                  </th>
                  <th className={`px-3 py-2 text-center font-medium uppercase whitespace-nowrap ${
                    isDark ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={10} className="px-3 py-3">
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
                ) : filteredRegistrations.length === 0 ? (
                  <tr>
                    <td colSpan={10} className={`px-3 py-6 text-center text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No registrations found
                    </td>
                  </tr>
                ) : (
                  filteredRegistrations.map((reg) => (
                    <tr
                      key={reg.id}
                      className={`transition-colors ${
                        isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'
                      }`}
                    >
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-medium flex-shrink-0 ${
                            reg.is_qualified
                              ? 'bg-gradient-to-br from-green-500 to-emerald-600'
                              : 'bg-gradient-to-br from-gray-500 to-gray-600'
                          }`}>
                            {reg.full_name.charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <div className={`font-medium truncate max-w-[120px] ${isDark ? 'text-white' : 'text-gray-900'}`} title={reg.full_name}>
                              {reg.full_name}
                            </div>
                            {reg.roll_number && (
                              <div className={`text-[10px] ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                {reg.roll_number}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <div className="space-y-0.5">
                          <div className={`flex items-center gap-1 truncate max-w-[150px] ${isDark ? 'text-gray-300' : 'text-gray-600'}`} title={reg.email}>
                            <Mail className="w-3 h-3 flex-shrink-0" />
                            <span className="truncate">{reg.email}</span>
                          </div>
                          <div className={`flex items-center gap-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            <Phone className="w-3 h-3 flex-shrink-0" />
                            {reg.phone}
                          </div>
                        </div>
                      </td>
                      <td className={`px-3 py-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        <div className="max-w-[140px] truncate" title={reg.college_name}>
                          {reg.college_name}
                        </div>
                      </td>
                      <td className={`px-3 py-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        <div className="text-xs">
                          <div>{reg.department}</div>
                          <div className={`text-[10px] ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                            {reg.year_of_study}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-center">
                        {reg.percentage !== null && reg.percentage !== undefined ? (
                          <span className={`font-bold text-lg ${
                            reg.is_qualified ? 'text-green-500' : 'text-red-500'
                          }`}>
                            {reg.percentage.toFixed(1)}%
                          </span>
                        ) : (
                          <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>-</span>
                        )}
                      </td>
                      <td className={`px-3 py-2 text-center ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                        {reg.logical_score}
                      </td>
                      <td className={`px-3 py-2 text-center ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                        {reg.technical_score}
                      </td>
                      <td className={`px-3 py-2 text-center ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>
                        {reg.ai_ml_score}
                      </td>
                      <td className={`px-3 py-2 text-center ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
                        {reg.english_score}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {getStatusBadge(reg)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary */}
        {!loading && filteredRegistrations.length > 0 && (
          <div className={`mt-4 text-sm text-center ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
            Showing {filteredRegistrations.length} of {registrations.length} registrations
          </div>
        )}
      </div>
    </div>
  )
}
