'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Building2,
  ChevronRight,
  Loader2,
  Plus,
  Search,
  X,
  Globe,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Users,
  FileText,
  Briefcase,
  CheckCircle2,
  Clock,
  AlertCircle
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface Partner {
  id: string
  name: string
  partner_type: string
  industry_sector: string | null
  website: string | null
  contact_person: string | null
  contact_email: string | null
  contact_phone: string | null
  address: string | null
  mou_number: string | null
  mou_status: string
  mou_signed_date: string | null
  mou_expiry_date: string | null
  department: string | null
  collaboration_areas: string[] | null
  students_benefited: number
  projects_completed: number
  placements_provided: number
  created_at: string
}

const PARTNER_TYPES = [
  { value: 'corporate', label: 'Corporate', color: 'blue' },
  { value: 'startup', label: 'Startup', color: 'green' },
  { value: 'government', label: 'Government', color: 'orange' },
  { value: 'research_institution', label: 'Research Institution', color: 'purple' },
  { value: 'ngo', label: 'NGO', color: 'pink' },
  { value: 'professional_body', label: 'Professional Body', color: 'teal' }
]

const MOU_STATUS_COLORS = {
  draft: 'bg-yellow-500/10 text-yellow-400',
  active: 'bg-green-500/10 text-green-400',
  expired: 'bg-red-500/10 text-red-400',
  renewed: 'bg-blue-500/10 text-blue-400',
  terminated: 'bg-slate-500/10 text-slate-400'
}

export default function IndustryPartnersPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [partners, setPartners] = useState<Partner[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [byType, setByType] = useState<Record<string, number>>({})

  const [newPartner, setNewPartner] = useState({
    name: '',
    partner_type: 'corporate',
    industry_sector: '',
    website: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    address: '',
    department: '',
    collaboration_areas: [] as string[]
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchPartners()
    }
  }, [authLoading, isAuthenticated, typeFilter, statusFilter])

  const fetchPartners = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (typeFilter) params.append('partner_type', typeFilter)
      if (statusFilter) params.append('mou_status', statusFilter)
      params.append('page_size', '50')

      const response = await apiClient.get(`/accreditation/criterion1/industry-partners?${params.toString()}`)
      setPartners(response.items || [])
      setByType(response.by_type || {})
    } catch (err: any) {
      console.error('Failed to fetch partners:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddPartner = async () => {
    if (!newPartner.name) {
      setError('Please provide partner name')
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion1/industry-partners', newPartner)
      setShowAddModal(false)
      setNewPartner({
        name: '',
        partner_type: 'corporate',
        industry_sector: '',
        website: '',
        contact_person: '',
        contact_email: '',
        contact_phone: '',
        address: '',
        department: '',
        collaboration_areas: []
      })
      fetchPartners()
    } catch (err: any) {
      console.error('Failed to add partner:', err)
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredPartners = partners.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.industry_sector && p.industry_sector.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const totalStudents = partners.reduce((sum, p) => sum + p.students_benefited, 0)
  const activeMous = partners.filter(p => p.mou_status === 'active').length

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-purple-500 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 text-purple-100 mb-2">
            <Link href="/admin/accreditation" className="hover:text-white">NAAC</Link>
            <ChevronRight className="w-4 h-4" />
            <Link href="/admin/accreditation/criterion1" className="hover:text-white">Criterion 1</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white">Industry Partners</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Building2 className="w-6 h-6" />
                Industry Partners
              </h1>
              <p className="text-purple-100">MoUs, Collaborations & Advisory Board</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-white text-purple-600 px-4 py-2 rounded-lg font-medium hover:bg-purple-50 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Partner
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <Building2 className="w-8 h-8 text-purple-500" />
              <span className="text-2xl font-bold">{partners.length}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Total Partners</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <FileText className="w-8 h-8 text-green-500" />
              <span className="text-2xl font-bold">{activeMous}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Active MoUs</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <Users className="w-8 h-8 text-blue-500" />
              <span className="text-2xl font-bold">{totalStudents}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Students Benefited</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <Briefcase className="w-8 h-8 text-orange-500" />
              <span className="text-2xl font-bold">{partners.reduce((sum, p) => sum + p.placements_provided, 0)}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Placements</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search partners..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-purple-500"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
          >
            <option value="">All Types</option>
            {PARTNER_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
          >
            <option value="">All MoU Status</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="expired">Expired</option>
          </select>
        </div>

        {/* Partners Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
          </div>
        ) : filteredPartners.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-xl">
            <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400">No partners found</h3>
            <p className="text-slate-500 mb-4">Add industry partners for collaborations</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Add First Partner
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPartners.map((partner) => {
              const typeInfo = PARTNER_TYPES.find(t => t.value === partner.partner_type)

              return (
                <div
                  key={partner.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="font-semibold text-lg">{partner.name}</h3>
                      <p className="text-sm text-slate-400 capitalize">{partner.partner_type.replace('_', ' ')}</p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs ${MOU_STATUS_COLORS[partner.mou_status as keyof typeof MOU_STATUS_COLORS] || MOU_STATUS_COLORS.draft}`}>
                      {partner.mou_status}
                    </span>
                  </div>

                  {partner.industry_sector && (
                    <p className="text-sm text-slate-500 mb-3">{partner.industry_sector}</p>
                  )}

                  <div className="space-y-2 mb-4">
                    {partner.contact_person && (
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Users className="w-4 h-4" />
                        {partner.contact_person}
                      </div>
                    )}
                    {partner.contact_email && (
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Mail className="w-4 h-4" />
                        {partner.contact_email}
                      </div>
                    )}
                    {partner.website && (
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <Globe className="w-4 h-4" />
                        <a href={partner.website} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:underline truncate">
                          {partner.website}
                        </a>
                      </div>
                    )}
                  </div>

                  {partner.collaboration_areas && partner.collaboration_areas.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {partner.collaboration_areas.slice(0, 3).map((area, idx) => (
                        <span key={idx} className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-xs">
                          {area}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-800">
                    <div className="text-center">
                      <p className="text-lg font-semibold text-blue-400">{partner.students_benefited}</p>
                      <p className="text-xs text-slate-500">Students</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-semibold text-green-400">{partner.projects_completed}</p>
                      <p className="text-xs text-slate-500">Projects</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-semibold text-orange-400">{partner.placements_provided}</p>
                      <p className="text-xs text-slate-500">Placements</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Add Partner Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Add Industry Partner</h2>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Partner Name *</label>
                <input
                  type="text"
                  value={newPartner.name}
                  onChange={(e) => setNewPartner({ ...newPartner, name: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  placeholder="Company/Organization name"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Partner Type *</label>
                  <select
                    value={newPartner.partner_type}
                    onChange={(e) => setNewPartner({ ...newPartner, partner_type: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  >
                    {PARTNER_TYPES.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Industry Sector</label>
                  <input
                    type="text"
                    value={newPartner.industry_sector}
                    onChange={(e) => setNewPartner({ ...newPartner, industry_sector: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                    placeholder="e.g., IT, Manufacturing"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Website</label>
                <input
                  type="url"
                  value={newPartner.website}
                  onChange={(e) => setNewPartner({ ...newPartner, website: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  placeholder="https://..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Contact Person</label>
                  <input
                    type="text"
                    value={newPartner.contact_person}
                    onChange={(e) => setNewPartner({ ...newPartner, contact_person: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Contact Email</label>
                  <input
                    type="email"
                    value={newPartner.contact_email}
                    onChange={(e) => setNewPartner({ ...newPartner, contact_email: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Department</label>
                <input
                  type="text"
                  value={newPartner.department}
                  onChange={(e) => setNewPartner({ ...newPartner, department: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  placeholder="Primary department for collaboration"
                />
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400">
                  {error}
                </div>
              )}
            </div>
            <div className="p-6 border-t border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddPartner}
                disabled={isSubmitting}
                className="px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Add Partner
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
