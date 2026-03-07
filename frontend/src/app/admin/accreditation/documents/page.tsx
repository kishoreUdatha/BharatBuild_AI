'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Download,
  Trash2,
  Clock,
  Filter,
  Search,
  ArrowLeft,
  FolderOpen
} from 'lucide-react'

interface GeneratedDocument {
  id: string
  criterion: number
  doc_type: string
  title: string
  generated_at: string
  status: 'draft' | 'finalized'
  content?: any
}

export default function DocumentsPage() {
  const router = useRouter()
  const [documents, setDocuments] = useState<GeneratedDocument[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    const savedDocs = localStorage.getItem('naac_generated_documents')
    if (savedDocs) {
      setDocuments(JSON.parse(savedDocs))
    }
  }, [])

  const filteredDocs = documents.filter(doc => {
    const matchesFilter = filter === 'all' || doc.doc_type === filter
    const matchesSearch = doc.title.toLowerCase().includes(search.toLowerCase())
    return matchesFilter && matchesSearch
  })

  const handleDownload = (doc: GeneratedDocument, format: 'json' | 'word') => {
    if (format === 'json') {
      const blob = new Blob([JSON.stringify(doc.content, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${doc.title.replace(/\s+/g, '_')}.json`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleDelete = (docId: string) => {
    const updatedDocs = documents.filter(d => d.id !== docId)
    setDocuments(updatedDocs)
    localStorage.setItem('naac_generated_documents', JSON.stringify(updatedDocs))
  }

  const handleClearAll = () => {
    if (confirm('Are you sure you want to delete all documents?')) {
      localStorage.removeItem('naac_generated_documents')
      setDocuments([])
    }
  }

  const getDocTypeLabel = (type: string) => {
    switch (type) {
      case 'full_ssr': return 'SSR'
      case 'criterion_report': return 'Criterion'
      case 'iqac': return 'IQAC'
      default: return type
    }
  }

  const getDocTypeColor = (type: string) => {
    switch (type) {
      case 'full_ssr': return 'bg-orange-500/20 text-orange-400'
      case 'criterion_report': return 'bg-blue-500/20 text-blue-400'
      case 'iqac': return 'bg-purple-500/20 text-purple-400'
      default: return 'bg-slate-500/20 text-slate-400'
    }
  }

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">Documents</h1>
              <p className="text-slate-400">Manage generated NAAC documents</p>
            </div>
          </div>
          {documents.length > 0 && (
            <button
              onClick={handleClearAll}
              className="text-sm text-red-400 hover:text-red-300 flex items-center gap-1"
            >
              <Trash2 className="w-4 h-4" />
              Clear All
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search documents..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-orange-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select
              value={filter}
              onChange={e => setFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
            >
              <option value="all">All Types</option>
              <option value="full_ssr">SSR</option>
              <option value="criterion_report">Criterion Reports</option>
              <option value="iqac">IQAC</option>
            </select>
          </div>
        </div>

        {/* Documents List */}
        {filteredDocs.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
            <FolderOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No Documents Found</h3>
            <p className="text-slate-400 mb-6">
              {documents.length === 0
                ? "You haven't generated any documents yet."
                : "No documents match your search criteria."}
            </p>
            {documents.length === 0 && (
              <div className="flex justify-center gap-3">
                <a
                  href="/admin/accreditation/ssr"
                  className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg"
                >
                  Generate SSR
                </a>
                <a
                  href="/admin/accreditation/criterion1"
                  className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg"
                >
                  Generate Criterion
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredDocs.map(doc => (
              <div
                key={doc.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-orange-500/20 rounded-lg">
                    <FileText className="w-5 h-5 text-orange-500" />
                  </div>
                  <div>
                    <h4 className="font-medium">{doc.title}</h4>
                    <div className="text-sm text-slate-400 flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(doc.generated_at).toLocaleDateString()} {new Date(doc.generated_at).toLocaleTimeString()}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs ${getDocTypeColor(doc.doc_type)}`}>
                        {getDocTypeLabel(doc.doc_type)}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs ${
                        doc.status === 'finalized' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {doc.status}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDownload(doc, 'json')}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm flex items-center gap-1"
                  >
                    <Download className="w-4 h-4" />
                    JSON
                  </button>
                  <button
                    onClick={() => handleDownload(doc, 'word')}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm"
                  >
                    Word
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary */}
        {documents.length > 0 && (
          <div className="mt-6 text-sm text-slate-400">
            Showing {filteredDocs.length} of {documents.length} documents
          </div>
        )}
      </div>
    </div>
  )
}
