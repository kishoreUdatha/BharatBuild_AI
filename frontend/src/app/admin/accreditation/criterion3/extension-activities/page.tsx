'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Heart,
  Plus,
  Search,
  ChevronRight,
  Loader2,
  Edit,
  Trash2,
  Calendar,
  Users,
  Building2,
  MapPin,
  XCircle,
  AlertCircle,
  Target
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface ExtensionActivity {
  id: string
  title: string
  activity_type: string
  description: string
  organized_by: string
  department: string
  academic_year: string
  venue: string
  village_adopted: string
  district: string
  state: string
  activity_date: string
  end_date: string
  duration_days: number
  students_participated: number
  beneficiaries_count: number
  beneficiaries_type: string
  sdg_goals_addressed: number[]
  created_at: string
}

const ACTIVITY_TYPES = [
  { value: 'nss', label: 'NSS', color: 'blue' },
  { value: 'ncc', label: 'NCC', color: 'green' },
  { value: 'community_service', label: 'Community Service', color: 'purple' },
  { value: 'awareness_program', label: 'Awareness Program', color: 'orange' },
  { value: 'health_camp', label: 'Health Camp', color: 'red' },
  { value: 'literacy_drive', label: 'Literacy Drive', color: 'teal' },
  { value: 'environment', label: 'Environmental', color: 'green' },
  { value: 'skill_development', label: 'Skill Development', color: 'yellow' },
  { value: 'village_adoption', label: 'Village Adoption', color: 'indigo' },
  { value: 'other', label: 'Other', color: 'gray' }
]

const SDG_GOALS = [
  { id: 1, name: 'No Poverty' },
  { id: 2, name: 'Zero Hunger' },
  { id: 3, name: 'Good Health' },
  { id: 4, name: 'Quality Education' },
  { id: 5, name: 'Gender Equality' },
  { id: 6, name: 'Clean Water' },
  { id: 7, name: 'Clean Energy' },
  { id: 8, name: 'Economic Growth' },
  { id: 9, name: 'Innovation' },
  { id: 10, name: 'Reduced Inequalities' },
  { id: 11, name: 'Sustainable Cities' },
  { id: 12, name: 'Responsible Consumption' },
  { id: 13, name: 'Climate Action' },
  { id: 14, name: 'Life Below Water' },
  { id: 15, name: 'Life on Land' },
  { id: 16, name: 'Peace & Justice' },
  { id: 17, name: 'Partnerships' }
]

export default function ExtensionActivitiesPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [activities, setActivities] = useState<ExtensionActivity[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterYear, setFilterYear] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [formData, setFormData] = useState({
    title: '',
    activity_type: 'community_service',
    description: '',
    objectives: [],
    outcomes: [],
    organized_by: '',
    department: '',
    academic_year: '2024-25',
    venue: '',
    village_adopted: '',
    district: '',
    state: '',
    activity_date: '',
    end_date: '',
    duration_days: 1,
    students_participated: 0,
    beneficiaries_count: 0,
    beneficiaries_type: '',
    sdg_goals_addressed: [] as number[],
    funding_received: 0,
    funding_source: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchActivities()
    }
  }, [authLoading, isAuthenticated, filterType, filterYear])

  const fetchActivities = async () => {
    setIsLoading(true)
    try {
      let url = '/accreditation/criterion3/extension-activities?limit=100'
      if (filterType) url += `&activity_type=${filterType}`
      if (filterYear) url += `&academic_year=${filterYear}`

      const response = await apiClient.get(url)
      setActivities(response.extension_activities || [])
    } catch (err: any) {
      console.error('Failed to fetch activities:', err)
      setError(err.message || 'Failed to load activities')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion3/extension-activities', formData)
      setShowAddModal(false)
      resetForm()
      fetchActivities()
    } catch (err: any) {
      setError(err.message || 'Failed to save activity')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this activity?')) return
    try {
      await apiClient.delete(`/accreditation/criterion3/extension-activities/${id}`)
      fetchActivities()
    } catch (err: any) {
      setError(err.message || 'Failed to delete activity')
    }
  }

  const resetForm = () => {
    setFormData({
      title: '',
      activity_type: 'community_service',
      description: '',
      objectives: [],
      outcomes: [],
      organized_by: '',
      department: '',
      academic_year: '2024-25',
      venue: '',
      village_adopted: '',
      district: '',
      state: '',
      activity_date: '',
      end_date: '',
      duration_days: 1,
      students_participated: 0,
      beneficiaries_count: 0,
      beneficiaries_type: '',
      sdg_goals_addressed: [],
      funding_received: 0,
      funding_source: ''
    })
  }

  const getTypeColor = (type: string) => {
    const info = ACTIVITY_TYPES.find(t => t.value === type)
    const colors: Record<string, string> = {
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      green: 'bg-green-500/20 text-green-400 border-green-500/30',
      purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      red: 'bg-red-500/20 text-red-400 border-red-500/30',
      teal: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
      yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      indigo: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
      gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
    return colors[info?.color || 'gray']
  }

  const toggleSDG = (sdgId: number) => {
    setFormData(prev => ({
      ...prev,
      sdg_goals_addressed: prev.sdg_goals_addressed.includes(sdgId)
        ? prev.sdg_goals_addressed.filter(id => id !== sdgId)
        : [...prev.sdg_goals_addressed, sdgId]
    }))
  }

  const filteredActivities = activities.filter(a =>
    a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.department?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.venue?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                <Link href="/admin/accreditation" className="hover:text-white">Accreditation</Link>
                <ChevronRight className="w-4 h-4" />
                <Link href="/admin/accreditation/criterion3" className="hover:text-white">Criterion 3</Link>
                <ChevronRight className="w-4 h-4" />
                <span className="text-white">Extension Activities</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <Heart className="w-7 h-7 text-red-500" />
                Extension Activities
              </h1>
              <p className="text-slate-400 mt-1">NSS, NCC, community outreach & social responsibility programs</p>
            </div>
            <button
              onClick={() => { resetForm(); setShowAddModal(true) }}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add Activity
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-400">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto">
              <XCircle className="w-5 h-5 text-red-400" />
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex-1 min-w-64 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search activities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Types</option>
            {ACTIVITY_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <select
            value={filterYear}
            onChange={(e) => setFilterYear(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Years</option>
            <option value="2024-25">2024-25</option>
            <option value="2023-24">2023-24</option>
            <option value="2022-23">2022-23</option>
          </select>
        </div>

        {/* Activities Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredActivities.map((activity) => (
            <div key={activity.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <span className={`px-2 py-1 text-xs rounded border ${getTypeColor(activity.activity_type)}`}>
                  {ACTIVITY_TYPES.find(t => t.value === activity.activity_type)?.label}
                </span>
                <button onClick={() => handleDelete(activity.id)} className="p-1.5 hover:bg-slate-800 rounded">
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </div>

              <h3 className="font-semibold mb-2 line-clamp-2">{activity.title}</h3>

              <div className="space-y-2 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span>{activity.activity_date}</span>
                </div>
                {activity.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate">{activity.venue}</span>
                  </div>
                )}
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Users className="w-4 h-4 text-blue-400" />
                    {activity.students_participated || 0} students
                  </span>
                  <span className="flex items-center gap-1">
                    <Heart className="w-4 h-4 text-red-400" />
                    {activity.beneficiaries_count || 0} beneficiaries
                  </span>
                </div>
              </div>

              {activity.sdg_goals_addressed && activity.sdg_goals_addressed.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800">
                  <div className="flex flex-wrap gap-1">
                    {activity.sdg_goals_addressed.map(sdg => (
                      <span key={sdg} className="text-xs px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded">
                        SDG {sdg}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {filteredActivities.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <Heart className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No extension activities found</p>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-xl font-semibold">Add Extension Activity</h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Activity Title *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Activity Type *</label>
                  <select
                    required
                    value={formData.activity_type}
                    onChange={(e) => setFormData({ ...formData, activity_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    {ACTIVITY_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Academic Year *</label>
                  <input
                    type="text"
                    required
                    value={formData.academic_year}
                    onChange={(e) => setFormData({ ...formData, academic_year: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Organized By *</label>
                  <input
                    type="text"
                    required
                    value={formData.organized_by}
                    onChange={(e) => setFormData({ ...formData, organized_by: e.target.value })}
                    placeholder="NSS Unit, NCC, Department..."
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Department</label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Activity Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.activity_date}
                    onChange={(e) => setFormData({ ...formData, activity_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Venue</label>
                  <input
                    type="text"
                    value={formData.venue}
                    onChange={(e) => setFormData({ ...formData, venue: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Students Participated</label>
                  <input
                    type="number"
                    value={formData.students_participated}
                    onChange={(e) => setFormData({ ...formData, students_participated: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Beneficiaries Count</label>
                  <input
                    type="number"
                    value={formData.beneficiaries_count}
                    onChange={(e) => setFormData({ ...formData, beneficiaries_count: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">UN SDG Goals Addressed</label>
                <div className="flex flex-wrap gap-2">
                  {SDG_GOALS.slice(0, 10).map(sdg => (
                    <button
                      key={sdg.id}
                      type="button"
                      onClick={() => toggleSDG(sdg.id)}
                      className={`px-2 py-1 text-xs rounded border transition-colors ${
                        formData.sdg_goals_addressed.includes(sdg.id)
                          ? 'bg-green-500/20 text-green-400 border-green-500/30'
                          : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      {sdg.id}. {sdg.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
