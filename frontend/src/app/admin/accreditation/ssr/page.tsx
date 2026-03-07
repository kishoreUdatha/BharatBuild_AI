'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Loader2,
  Download,
  CheckCircle2,
  AlertTriangle,
  FileDown,
  ArrowLeft
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface InstitutionProfile {
  name: string
  type: 'University' | 'Autonomous' | 'Affiliated'
  location: string
  state: string
  established_year: number
  naac_cycle: number
  previous_grade: string
  programs_offered: string[]
  total_students: number
  total_faculty: number
}

export default function SSRGenerationPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedDoc, setGeneratedDoc] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [institution, setInstitution] = useState<InstitutionProfile | null>(null)

  useEffect(() => {
    // Load institution profile from localStorage
    const savedInstitution = localStorage.getItem('naac_institution_profile')
    if (savedInstitution) {
      setInstitution(JSON.parse(savedInstitution))
    }
  }, [])

  const handleGenerateSSR = async () => {
    if (!institution?.name) {
      setError('Please complete institution profile first')
      return
    }

    setIsGenerating(true)
    setError(null)

    try {
      const response = await apiClient.generateSSR({
        institution: {
          name: institution.name,
          type: institution.type,
          location: institution.location,
          state: institution.state,
          established_year: institution.established_year,
          naac_cycle: institution.naac_cycle,
          previous_grade: institution.previous_grade,
          programs_offered: institution.programs_offered,
          total_students: institution.total_students,
          total_faculty: institution.total_faculty
        },
        academic_year: '2024-25',
        naac_cycle: institution.naac_cycle
      })

      setGeneratedDoc(response)

      // Save to documents list
      const savedDocs = localStorage.getItem('naac_generated_documents')
      const docs = savedDocs ? JSON.parse(savedDocs) : []
      docs.push({
        id: `ssr-${Date.now()}`,
        criterion: 0,
        doc_type: 'full_ssr',
        title: 'Complete Self Study Report (SSR)',
        generated_at: new Date().toISOString(),
        status: 'draft',
        content: response
      })
      localStorage.setItem('naac_generated_documents', JSON.stringify(docs))

    } catch (err: any) {
      setError(err.message || 'Failed to generate SSR')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = (format: 'json' | 'word') => {
    if (!generatedDoc) return

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(generatedDoc, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'SSR_Complete.json'
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => router.back()}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">SSR Generation</h1>
            <p className="text-slate-400">Generate Complete Self Study Report</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-300 hover:text-white">x</button>
          </div>
        )}

        {/* SSR Generation Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
          <div className="flex items-start gap-4 mb-6">
            <div className="p-3 bg-orange-500/20 rounded-xl">
              <FileText className="w-8 h-8 text-orange-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-1">Complete Self Study Report (SSR)</h2>
              <p className="text-slate-400">
                Generate a comprehensive SSR covering all 7 NAAC criteria, including Part A (Institutional Data),
                Part B (Criteria-wise Inputs), Extended Profile, and Quality Indicator Framework.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h4 className="text-sm text-slate-400 mb-3 font-medium">SSR will include:</h4>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  Part A: Institutional Profile
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  Extended Profile (QIF data)
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  All 7 Criteria Documentation
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  DVV-ready format
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm text-slate-400 mb-3 font-medium">Institution Summary:</h4>
              <div className="bg-slate-800 rounded-lg p-4 text-sm space-y-1">
                {institution ? (
                  <>
                    <div><strong>Name:</strong> {institution.name}</div>
                    <div><strong>Type:</strong> {institution.type}</div>
                    <div><strong>Location:</strong> {institution.location}, {institution.state}</div>
                    <div><strong>NAAC Cycle:</strong> {institution.naac_cycle}</div>
                  </>
                ) : (
                  <div className="text-yellow-400">
                    Institution profile not configured.
                    <a href="/admin/accreditation/settings" className="ml-2 underline">
                      Set up now
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={handleGenerateSSR}
            disabled={isGenerating || !institution?.name}
            className="w-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-400 hover:to-red-400 disabled:from-orange-500/50 disabled:to-red-500/50 text-white font-semibold py-4 rounded-lg flex items-center justify-center gap-2 transition-all"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Generating Complete SSR...
              </>
            ) : (
              <>
                <FileText className="w-5 h-5" />
                Generate Complete SSR
              </>
            )}
          </button>

          {!institution?.name && (
            <p className="text-yellow-500 text-sm mt-3 flex items-center gap-1">
              <AlertTriangle className="w-4 h-4" />
              Please complete institution profile first in Settings
            </p>
          )}
        </div>

        {/* Generated Document Preview */}
        {generatedDoc && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                SSR Generated Successfully
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => handleDownload('json')}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm flex items-center gap-1"
                >
                  <Download className="w-4 h-4" />
                  JSON
                </button>
                <button
                  onClick={() => handleDownload('word')}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm flex items-center gap-1"
                >
                  <FileDown className="w-4 h-4" />
                  Word
                </button>
              </div>
            </div>
            <div className="bg-slate-800 rounded-lg p-4 max-h-96 overflow-auto">
              <pre className="text-sm text-slate-300 whitespace-pre-wrap">
                {JSON.stringify(generatedDoc, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
