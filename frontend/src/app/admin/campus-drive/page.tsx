'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
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
  Percent,
  X,
  Hash,
  Calendar,
  Target
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

// Registration Details Modal Component
function RegistrationDetailsModal({
  registration,
  driveName,
  passingPercentage,
  isDark,
  onClose
}: {
  registration: Registration
  driveName: string
  passingPercentage: number
  isDark: boolean
  onClose: () => void
}) {
  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const isQualified = registration.is_qualified
  const hasScore = registration.percentage !== null && registration.percentage !== undefined

  const modalContent = (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 transition-opacity" onClick={onClose} />

      {/* Modal Container */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className={`relative w-full max-w-2xl rounded-lg shadow-xl ${
            isDark ? 'bg-[#1f1f23]' : 'bg-white'
          }`}
        >
          {/* Header */}
          <div className={`flex items-center justify-between px-6 py-4 border-b ${
            isDark ? 'border-gray-700' : 'border-gray-200'
          }`}>
            <div>
              <h2 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Registration Details
              </h2>
              <p className={`text-sm mt-0.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Campus drive registration and quiz results
              </p>
            </div>
            <button
              onClick={onClose}
              className={`p-2 rounded-md transition-colors ${
                isDark ? 'hover:bg-gray-700 text-gray-400 hover:text-white' : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700'
              }`}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-6">
            {/* Profile Section */}
            <div className="flex items-start gap-5 mb-6">
              <div className={`w-20 h-20 rounded-lg flex items-center justify-center text-2xl font-bold text-white flex-shrink-0 ${
                hasScore
                  ? isQualified
                    ? 'bg-gradient-to-br from-emerald-500 to-emerald-600'
                    : 'bg-gradient-to-br from-red-500 to-red-600'
                  : 'bg-gradient-to-br from-gray-500 to-gray-600'
              }`}>
                {registration.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {registration.full_name}
                    </h3>
                    <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      {registration.roll_number || 'No Roll Number'} • {registration.year_of_study}
                    </p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium flex-shrink-0 ${
                    hasScore
                      ? isQualified
                        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                        : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                  }`}>
                    {hasScore ? (isQualified ? 'Qualified' : 'Not Qualified') : 'Quiz Pending'}
                  </span>
                </div>
              </div>
            </div>

            {/* Score Section */}
            {hasScore && (
              <div className={`p-5 rounded-lg mb-6 ${
                isQualified
                  ? isDark ? 'bg-emerald-900/20 border border-emerald-800/30' : 'bg-emerald-50 border border-emerald-100'
                  : isDark ? 'bg-red-900/20 border border-red-800/30' : 'bg-red-50 border border-red-100'
              }`}>
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <div className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Overall Score
                    </div>
                    <div className={`text-4xl font-bold mt-1 ${isQualified ? 'text-emerald-500' : 'text-red-500'}`}>
                      {registration.percentage?.toFixed(1)}%
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Passing Score
                    </div>
                    <div className={`text-2xl font-bold mt-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      {passingPercentage}%
                    </div>
                  </div>
                </div>

                {/* Section Scores */}
                <div className={`grid grid-cols-4 gap-3 pt-4 border-t ${
                  isQualified
                    ? isDark ? 'border-emerald-800/30' : 'border-emerald-200'
                    : isDark ? 'border-red-800/30' : 'border-red-200'
                }`}>
                  <div className={`text-center p-3 rounded-md ${isDark ? 'bg-gray-800/50' : 'bg-white'}`}>
                    <Brain className="w-5 h-5 text-blue-500 mx-auto" />
                    <div className={`text-xl font-bold mt-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {registration.logical_score}
                    </div>
                    <div className={`text-xs font-medium uppercase tracking-wide mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Logical
                    </div>
                  </div>
                  <div className={`text-center p-3 rounded-md ${isDark ? 'bg-gray-800/50' : 'bg-white'}`}>
                    <Code className="w-5 h-5 text-green-500 mx-auto" />
                    <div className={`text-xl font-bold mt-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {registration.technical_score}
                    </div>
                    <div className={`text-xs font-medium uppercase tracking-wide mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      Technical
                    </div>
                  </div>
                  <div className={`text-center p-3 rounded-md ${isDark ? 'bg-gray-800/50' : 'bg-white'}`}>
                    <BookOpen className="w-5 h-5 text-purple-500 mx-auto" />
                    <div className={`text-xl font-bold mt-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {registration.ai_ml_score}
                    </div>
                    <div className={`text-xs font-medium uppercase tracking-wide mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      AI/ML
                    </div>
                  </div>
                  <div className={`text-center p-3 rounded-md ${isDark ? 'bg-gray-800/50' : 'bg-white'}`}>
                    <MessageSquare className="w-5 h-5 text-orange-500 mx-auto" />
                    <div className={`text-xl font-bold mt-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {registration.english_score}
                    </div>
                    <div className={`text-xs font-medium uppercase tracking-wide mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                      English
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Campus Drive Info */}
            <div className={`flex items-center gap-4 p-4 rounded-lg mb-6 ${
              isDark ? 'bg-blue-900/20 border border-blue-800/30' : 'bg-blue-50 border border-blue-100'
            }`}>
              <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                <Target className="w-6 h-6 text-blue-500" />
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-blue-400' : 'text-blue-600'}`}>
                  Campus Drive
                </div>
                <div className={`text-lg font-semibold mt-0.5 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {driveName}
                </div>
              </div>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-x-8 gap-y-5">
              <div>
                <label className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  College
                </label>
                <p className={`mt-1 text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {registration.college_name}
                </p>
              </div>
              <div>
                <label className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Department
                </label>
                <p className={`mt-1 text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {registration.department}
                </p>
              </div>
              {registration.cgpa && (
                <div>
                  <label className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    CGPA
                  </label>
                  <p className={`mt-1 text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {registration.cgpa}
                  </p>
                </div>
              )}
              <div>
                <label className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Email Address
                </label>
                <p className={`mt-1 text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {registration.email}
                </p>
              </div>
              <div>
                <label className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Phone Number
                </label>
                <p className={`mt-1 text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {registration.phone}
                </p>
              </div>
              <div>
                <label className={`text-xs font-medium uppercase tracking-wide ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Registration Date
                </label>
                <p className={`mt-1 text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {formatDate(registration.created_at)}
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className={`flex items-center justify-between px-6 py-4 border-t ${
            isDark ? 'border-gray-700 bg-gray-800/30' : 'border-gray-200 bg-gray-50'
          }`}>
            <span className={`text-xs font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              ID: {registration.id}
            </span>
            <button
              onClick={onClose}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                isDark
                  ? 'bg-gray-700 hover:bg-gray-600 text-white'
                  : 'bg-gray-900 hover:bg-gray-800 text-white'
              }`}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  if (typeof window !== 'undefined') {
    return createPortal(modalContent, document.body)
  }

  return null
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
  const [viewingRegistration, setViewingRegistration] = useState<Registration | null>(null)

  const fetchDrives = async () => {
    try {
      setLoading(true)
      const drives = await apiClient.get('/admin/campus-drive/')
      setDrives(drives)
      if (drives.length > 0 && !selectedDrive) {
        setSelectedDrive(drives[0])
      } else if (drives.length === 0) {
        // No drives found, stop loading
        setLoading(false)
      }
    } catch (error) {
      console.error('Error fetching drives:', error)
      setLoading(false)
    }
  }

  const fetchRegistrations = async (driveId: string) => {
    try {
      setLoading(true)
      const [registrations, stats] = await Promise.all([
        apiClient.get(`/admin/campus-drive/${driveId}/registrations`),
        apiClient.get(`/admin/campus-drive/${driveId}/stats`)
      ])
      setRegistrations(registrations)
      setStats(stats)
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
      const exportData = await apiClient.get(
        `/admin/campus-drive/${selectedDrive.id}/export?qualified_only=${filterQualified === 'qualified'}`
      )
      const { data, filename } = exportData

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
                  <th className={`px-3 py-2 text-center font-medium uppercase whitespace-nowrap ${
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
                      <td colSpan={11} className="px-3 py-3">
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
                    <td colSpan={11} className={`px-3 py-6 text-center text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
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
                      <td className="px-3 py-2 text-center">
                        <button
                          onClick={() => setViewingRegistration(reg)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            isDark ? 'hover:bg-[#333] text-blue-400' : 'hover:bg-gray-100 text-blue-600'
                          }`}
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
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

      {/* Registration Details Modal */}
      {viewingRegistration && selectedDrive && (
        <RegistrationDetailsModal
          registration={viewingRegistration}
          driveName={selectedDrive.name}
          passingPercentage={selectedDrive.passing_percentage}
          isDark={isDark}
          onClose={() => setViewingRegistration(null)}
        />
      )}
    </div>
  )
}
