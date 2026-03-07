'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  BookOpen,
  Plus,
  Search,
  ChevronRight,
  Loader2,
  Edit,
  Trash2,
  Calendar,
  User,
  Building2,
  ExternalLink,
  CheckCircle,
  XCircle,
  AlertCircle,
  Award
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface Publication {
  id: string
  title: string
  publication_type: string
  authors: any[]
  corresponding_author: string
  department: string
  journal_name: string
  conference_name: string
  publisher: string
  volume: string
  issue: string
  pages: string
  publication_year: number
  indexing: string
  impact_factor: number
  citations: number
  doi: string
  paper_url: string
  is_verified: boolean
  created_at: string
}

const PUBLICATION_TYPES = [
  { value: 'journal_international', label: 'International Journal' },
  { value: 'journal_national', label: 'National Journal' },
  { value: 'conference_international', label: 'International Conference' },
  { value: 'conference_national', label: 'National Conference' },
  { value: 'book', label: 'Book' },
  { value: 'book_chapter', label: 'Book Chapter' },
  { value: 'thesis', label: 'Thesis' },
  { value: 'other', label: 'Other' }
]

const INDEXING_TYPES = [
  { value: 'scopus', label: 'Scopus', color: 'orange' },
  { value: 'web_of_science', label: 'Web of Science', color: 'blue' },
  { value: 'ugc_care', label: 'UGC CARE', color: 'green' },
  { value: 'pubmed', label: 'PubMed', color: 'purple' },
  { value: 'ieee', label: 'IEEE', color: 'teal' },
  { value: 'acm', label: 'ACM', color: 'red' },
  { value: 'other', label: 'Other', color: 'gray' },
  { value: 'none', label: 'None', color: 'gray' }
]

export default function PublicationsPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [publications, setPublications] = useState<Publication[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterIndexing, setFilterIndexing] = useState('')
  const [filterYear, setFilterYear] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingPub, setEditingPub] = useState<Publication | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [formData, setFormData] = useState({
    title: '',
    publication_type: 'journal_international',
    abstract: '',
    authors: [{ name: '', affiliation: '', is_corresponding: false }],
    corresponding_author: '',
    department: '',
    journal_name: '',
    conference_name: '',
    publisher: '',
    volume: '',
    issue: '',
    pages: '',
    publication_year: new Date().getFullYear(),
    publication_date: '',
    indexing: 'none',
    impact_factor: 0,
    citations: 0,
    doi: '',
    issn: '',
    paper_url: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchPublications()
    }
  }, [authLoading, isAuthenticated, filterType, filterIndexing, filterYear])

  const fetchPublications = async () => {
    setIsLoading(true)
    try {
      let url = '/accreditation/criterion3/publications?limit=100'
      if (filterType) url += `&publication_type=${filterType}`
      if (filterIndexing) url += `&indexing=${filterIndexing}`
      if (filterYear) url += `&publication_year=${filterYear}`

      const response = await apiClient.get(url)
      setPublications(response.publications || [])
    } catch (err: any) {
      console.error('Failed to fetch publications:', err)
      setError(err.message || 'Failed to load publications')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      if (editingPub) {
        await apiClient.put(`/accreditation/criterion3/publications/${editingPub.id}`, formData)
      } else {
        await apiClient.post('/accreditation/criterion3/publications', formData)
      }
      setShowAddModal(false)
      setEditingPub(null)
      resetForm()
      fetchPublications()
    } catch (err: any) {
      setError(err.message || 'Failed to save publication')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this publication?')) return
    try {
      await apiClient.delete(`/accreditation/criterion3/publications/${id}`)
      fetchPublications()
    } catch (err: any) {
      setError(err.message || 'Failed to delete publication')
    }
  }

  const handleVerify = async (id: string) => {
    try {
      await apiClient.post(`/accreditation/criterion3/publications/${id}/verify?verified_by=${user?.email || 'admin'}`)
      fetchPublications()
    } catch (err: any) {
      setError(err.message || 'Failed to verify publication')
    }
  }

  const resetForm = () => {
    setFormData({
      title: '',
      publication_type: 'journal_international',
      abstract: '',
      authors: [{ name: '', affiliation: '', is_corresponding: false }],
      corresponding_author: '',
      department: '',
      journal_name: '',
      conference_name: '',
      publisher: '',
      volume: '',
      issue: '',
      pages: '',
      publication_year: new Date().getFullYear(),
      publication_date: '',
      indexing: 'none',
      impact_factor: 0,
      citations: 0,
      doi: '',
      issn: '',
      paper_url: ''
    })
  }

  const getIndexingColor = (indexing: string) => {
    const info = INDEXING_TYPES.find(i => i.value === indexing)
    const colors: Record<string, string> = {
      orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      green: 'bg-green-500/20 text-green-400 border-green-500/30',
      purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      teal: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
      red: 'bg-red-500/20 text-red-400 border-red-500/30',
      gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
    return colors[info?.color || 'gray']
  }

  const addAuthor = () => {
    setFormData({
      ...formData,
      authors: [...formData.authors, { name: '', affiliation: '', is_corresponding: false }]
    })
  }

  const removeAuthor = (index: number) => {
    setFormData({
      ...formData,
      authors: formData.authors.filter((_, i) => i !== index)
    })
  }

  const filteredPublications = publications.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.department.toLowerCase().includes(searchQuery.toLowerCase())
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
                <span className="text-white">Publications</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <BookOpen className="w-7 h-7 text-blue-500" />
                Research Publications
              </h1>
              <p className="text-slate-400 mt-1">Manage journals, conferences, and book publications</p>
            </div>
            <button
              onClick={() => { resetForm(); setEditingPub(null); setShowAddModal(true) }}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add Publication
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
              placeholder="Search publications..."
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
            {PUBLICATION_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <select
            value={filterIndexing}
            onChange={(e) => setFilterIndexing(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Indexing</option>
            {INDEXING_TYPES.map(i => (
              <option key={i.value} value={i.value}>{i.label}</option>
            ))}
          </select>
          <select
            value={filterYear}
            onChange={(e) => setFilterYear(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Years</option>
            {[2024, 2023, 2022, 2021, 2020].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {/* Publications List */}
        <div className="space-y-4">
          {filteredPublications.map((pub) => (
            <div key={pub.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-xs rounded border ${getIndexingColor(pub.indexing)}`}>
                      {INDEXING_TYPES.find(i => i.value === pub.indexing)?.label}
                    </span>
                    {pub.is_verified && (
                      <span className="flex items-center gap-1 text-xs text-green-400">
                        <CheckCircle className="w-3 h-3" /> Verified
                      </span>
                    )}
                    {pub.impact_factor > 0 && (
                      <span className="text-xs text-orange-400">IF: {pub.impact_factor}</span>
                    )}
                  </div>
                  <h3 className="font-semibold mb-2">{pub.title}</h3>
                  <div className="text-sm text-slate-400 space-y-1">
                    <p>{pub.journal_name || pub.conference_name}</p>
                    <div className="flex flex-wrap gap-4">
                      <span className="flex items-center gap-1">
                        <Building2 className="w-4 h-4" /> {pub.department}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" /> {pub.publication_year}
                      </span>
                      {pub.citations > 0 && (
                        <span className="flex items-center gap-1 text-blue-400">
                          <Award className="w-4 h-4" /> {pub.citations} citations
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  {pub.paper_url && (
                    <a href={pub.paper_url} target="_blank" className="p-2 hover:bg-slate-800 rounded">
                      <ExternalLink className="w-4 h-4 text-blue-400" />
                    </a>
                  )}
                  {!pub.is_verified && (
                    <button onClick={() => handleVerify(pub.id)} className="p-2 hover:bg-slate-800 rounded">
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    </button>
                  )}
                  <button onClick={() => handleDelete(pub.id)} className="p-2 hover:bg-slate-800 rounded">
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredPublications.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <BookOpen className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No publications found</p>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-xl font-semibold">Add Publication</h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Title *</label>
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
                  <label className="block text-sm font-medium mb-1">Type *</label>
                  <select
                    required
                    value={formData.publication_type}
                    onChange={(e) => setFormData({ ...formData, publication_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    {PUBLICATION_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Indexing</label>
                  <select
                    value={formData.indexing}
                    onChange={(e) => setFormData({ ...formData, indexing: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    {INDEXING_TYPES.map(i => (
                      <option key={i.value} value={i.value}>{i.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Department *</label>
                  <input
                    type="text"
                    required
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Year *</label>
                  <input
                    type="number"
                    required
                    value={formData.publication_year}
                    onChange={(e) => setFormData({ ...formData, publication_year: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Journal/Conference Name</label>
                <input
                  type="text"
                  value={formData.journal_name || formData.conference_name}
                  onChange={(e) => setFormData({
                    ...formData,
                    journal_name: formData.publication_type.includes('journal') ? e.target.value : '',
                    conference_name: formData.publication_type.includes('conference') ? e.target.value : ''
                  })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Impact Factor</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.impact_factor}
                    onChange={(e) => setFormData({ ...formData, impact_factor: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Citations</label>
                  <input
                    type="number"
                    value={formData.citations}
                    onChange={(e) => setFormData({ ...formData, citations: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">DOI</label>
                  <input
                    type="text"
                    value={formData.doi}
                    onChange={(e) => setFormData({ ...formData, doi: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Paper URL</label>
                <input
                  type="url"
                  value={formData.paper_url}
                  onChange={(e) => setFormData({ ...formData, paper_url: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
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
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
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
