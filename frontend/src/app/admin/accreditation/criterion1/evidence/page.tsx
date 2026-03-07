'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  FileText,
  ChevronRight,
  Loader2,
  Plus,
  Upload,
  CheckCircle2,
  Clock,
  AlertCircle,
  Search,
  Download,
  X,
  Trash2,
  Eye,
  Filter,
  FolderOpen
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface Evidence {
  id: string
  evidence_type: string
  key_indicator: string
  title: string
  description: string | null
  file_name: string
  file_path: string
  file_size: number | null
  file_type: string | null
  department: string | null
  academic_year: string
  is_verified: boolean
  verified_by: string | null
  verified_at: string | null
  uploaded_by: string
  created_at: string
}

const EVIDENCE_TYPES = [
  { value: 'syllabus', label: 'Syllabus' },
  { value: 'co_po_matrix', label: 'CO-PO Matrix' },
  { value: 'mou', label: 'MoU' },
  { value: 'feedback_report', label: 'Feedback Report' },
  { value: 'meeting_minutes', label: 'Meeting Minutes' },
  { value: 'course_file', label: 'Course File' },
  { value: 'attainment_report', label: 'Attainment Report' },
  { value: 'curriculum_revision', label: 'Curriculum Revision' },
  { value: 'board_resolution', label: 'Board Resolution' },
  { value: 'other', label: 'Other' }
]

const KEY_INDICATORS = [
  { value: '1.1', label: '1.1 - Curriculum Planning' },
  { value: '1.2', label: '1.2 - Academic Flexibility' },
  { value: '1.3', label: '1.3 - Curriculum Enrichment' },
  { value: '1.4', label: '1.4 - Feedback System' }
]

export default function EvidenceManagementPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [evidenceList, setEvidenceList] = useState<Evidence[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [keyIndicatorFilter, setKeyIndicatorFilter] = useState<string>('')
  const [evidenceTypeFilter, setEvidenceTypeFilter] = useState<string>('')
  const [verifiedFilter, setVerifiedFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [byIndicator, setByIndicator] = useState<Record<string, number>>({})

  // Upload form
  const [uploadForm, setUploadForm] = useState({
    evidence_type: 'syllabus',
    key_indicator: '1.1',
    title: '',
    description: '',
    department: '',
    academic_year: '2024-25'
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchEvidence()
    }
  }, [authLoading, isAuthenticated, keyIndicatorFilter, evidenceTypeFilter, verifiedFilter])

  const fetchEvidence = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (keyIndicatorFilter) params.append('key_indicator', keyIndicatorFilter)
      if (evidenceTypeFilter) params.append('evidence_type', evidenceTypeFilter)
      if (verifiedFilter) params.append('is_verified', verifiedFilter)
      params.append('page_size', '50')

      const response = await apiClient.get(`/accreditation/criterion1/evidence?${params.toString()}`)
      setEvidenceList(response.items || [])
      setByIndicator(response.by_key_indicator || {})
    } catch (err: any) {
      console.error('Failed to fetch evidence:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      if (!uploadForm.title) {
        setUploadForm({ ...uploadForm, title: file.name.replace(/\.[^/.]+$/, '') })
      }
    }
  }

  const handleUpload = async () => {
    if (!selectedFile || !uploadForm.title) {
      setError('Please select a file and provide a title')
      return
    }

    setIsSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('evidence_type', uploadForm.evidence_type)
      formData.append('key_indicator', uploadForm.key_indicator)
      formData.append('title', uploadForm.title)
      formData.append('academic_year', uploadForm.academic_year)
      formData.append('uploaded_by', user?.email || 'admin')
      if (uploadForm.description) formData.append('description', uploadForm.description)
      if (uploadForm.department) formData.append('department', uploadForm.department)

      await apiClient.post('/accreditation/criterion1/evidence/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      setShowUploadModal(false)
      setSelectedFile(null)
      setUploadForm({
        evidence_type: 'syllabus',
        key_indicator: '1.1',
        title: '',
        description: '',
        department: '',
        academic_year: '2024-25'
      })
      fetchEvidence()
    } catch (err: any) {
      console.error('Failed to upload evidence:', err)
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleVerify = async (evidenceId: string) => {
    try {
      await apiClient.post(`/accreditation/criterion1/evidence/${evidenceId}/verify`, {
        verified_by: user?.email || 'admin',
        verification_remarks: 'Verified by admin'
      })
      fetchEvidence()
    } catch (err: any) {
      console.error('Failed to verify evidence:', err)
      alert('Failed to verify: ' + err.message)
    }
  }

  const handleDelete = async (evidenceId: string) => {
    if (!confirm('Are you sure you want to delete this evidence?')) return

    try {
      await apiClient.delete(`/accreditation/criterion1/evidence/${evidenceId}`)
      fetchEvidence()
    } catch (err: any) {
      console.error('Failed to delete evidence:', err)
      alert('Failed to delete: ' + err.message)
    }
  }

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const filteredEvidence = evidenceList.filter(e =>
    e.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (e.department && e.department.toLowerCase().includes(searchQuery.toLowerCase()))
  )

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
      <div className="bg-gradient-to-r from-blue-600 to-blue-500 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 text-blue-100 mb-2">
            <Link href="/admin/accreditation" className="hover:text-white">NAAC</Link>
            <ChevronRight className="w-4 h-4" />
            <Link href="/admin/accreditation/criterion1" className="hover:text-white">Criterion 1</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white">Evidence</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <FileText className="w-6 h-6" />
                Evidence Repository
              </h1>
              <p className="text-blue-100">Upload and manage supporting documents</p>
            </div>
            <button
              onClick={() => setShowUploadModal(true)}
              className="bg-white text-blue-600 px-4 py-2 rounded-lg font-medium hover:bg-blue-50 transition-colors flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Upload Evidence
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {KEY_INDICATORS.map(ki => (
            <div key={ki.value} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-slate-400 text-sm">{ki.label}</span>
                <span className="text-2xl font-bold text-blue-500">{byIndicator[ki.value] || 0}</span>
              </div>
              <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${Math.min(100, (byIndicator[ki.value] || 0) * 20)}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            />
          </div>
          <select
            value={keyIndicatorFilter}
            onChange={(e) => setKeyIndicatorFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">All Indicators</option>
            {KEY_INDICATORS.map(ki => (
              <option key={ki.value} value={ki.value}>{ki.label}</option>
            ))}
          </select>
          <select
            value={evidenceTypeFilter}
            onChange={(e) => setEvidenceTypeFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">All Types</option>
            {EVIDENCE_TYPES.map(et => (
              <option key={et.value} value={et.value}>{et.label}</option>
            ))}
          </select>
          <select
            value={verifiedFilter}
            onChange={(e) => setVerifiedFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="">All Status</option>
            <option value="true">Verified</option>
            <option value="false">Pending</option>
          </select>
        </div>

        {/* Evidence Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        ) : filteredEvidence.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-xl">
            <FolderOpen className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400">No evidence found</h3>
            <p className="text-slate-500 mb-4">Upload supporting documents for NAAC criteria</p>
            <button
              onClick={() => setShowUploadModal(true)}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Upload First Document
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredEvidence.map((evidence) => (
              <div
                key={evidence.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                      <FileText className="w-5 h-5 text-blue-500" />
                    </div>
                    <div>
                      <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-xs">
                        {evidence.key_indicator}
                      </span>
                    </div>
                  </div>
                  {evidence.is_verified ? (
                    <span className="flex items-center gap-1 text-green-400 text-sm">
                      <CheckCircle2 className="w-4 h-4" />
                      Verified
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-yellow-400 text-sm">
                      <Clock className="w-4 h-4" />
                      Pending
                    </span>
                  )}
                </div>

                <h3 className="font-semibold mb-1 truncate" title={evidence.title}>
                  {evidence.title}
                </h3>
                <p className="text-sm text-slate-400 mb-3 capitalize">
                  {evidence.evidence_type.replace('_', ' ')}
                </p>

                {evidence.description && (
                  <p className="text-sm text-slate-500 mb-3 line-clamp-2">{evidence.description}</p>
                )}

                <div className="flex items-center justify-between text-xs text-slate-500 mb-4">
                  <span>{evidence.file_name}</span>
                  <span>{formatFileSize(evidence.file_size)}</span>
                </div>

                <div className="flex items-center gap-2 pt-3 border-t border-slate-800">
                  {!evidence.is_verified && (
                    <button
                      onClick={() => handleVerify(evidence.id)}
                      className="flex-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 py-2 rounded-lg text-sm transition-colors flex items-center justify-center gap-1"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      Verify
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(evidence.id)}
                    className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Upload Evidence</h2>
              <button onClick={() => setShowUploadModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {/* File Drop Zone */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  selectedFile ? 'border-blue-500 bg-blue-500/10' : 'border-slate-700 hover:border-slate-600'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png"
                />
                {selectedFile ? (
                  <div>
                    <FileText className="w-10 h-10 text-blue-500 mx-auto mb-2" />
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-slate-400">{formatFileSize(selectedFile.size)}</p>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-10 h-10 text-slate-500 mx-auto mb-2" />
                    <p className="text-slate-400">Click to select file</p>
                    <p className="text-sm text-slate-500">PDF, DOC, XLS, PPT, or images</p>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Key Indicator *</label>
                  <select
                    value={uploadForm.key_indicator}
                    onChange={(e) => setUploadForm({ ...uploadForm, key_indicator: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    {KEY_INDICATORS.map(ki => (
                      <option key={ki.value} value={ki.value}>{ki.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Evidence Type *</label>
                  <select
                    value={uploadForm.evidence_type}
                    onChange={(e) => setUploadForm({ ...uploadForm, evidence_type: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    {EVIDENCE_TYPES.map(et => (
                      <option key={et.value} value={et.value}>{et.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Title *</label>
                <input
                  type="text"
                  value={uploadForm.title}
                  onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  placeholder="Document title"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
                <textarea
                  value={uploadForm.description}
                  onChange={(e) => setUploadForm({ ...uploadForm, description: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 min-h-[80px]"
                  placeholder="Brief description..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Department</label>
                  <input
                    type="text"
                    value={uploadForm.department}
                    onChange={(e) => setUploadForm({ ...uploadForm, department: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Academic Year</label>
                  <select
                    value={uploadForm.academic_year}
                    onChange={(e) => setUploadForm({ ...uploadForm, academic_year: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="2024-25">2024-25</option>
                    <option value="2023-24">2023-24</option>
                    <option value="2022-23">2022-23</option>
                  </select>
                </div>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400">
                  {error}
                </div>
              )}
            </div>
            <div className="p-6 border-t border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={isSubmitting || !selectedFile}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Upload
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
