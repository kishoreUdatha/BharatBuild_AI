'use client'

import { useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import {
  Zap, Upload, FileArchive, FolderTree, Bug, FileText,
  Shield, Gauge, ArrowRight, CheckCircle, AlertCircle,
  Loader2, X, ChevronRight, Download
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface UploadedProject {
  project_id: string
  project_name: string
  total_files: number
  total_size: number
  file_tree: any
  files: Array<{ path: string; language: string; size: number }>
}

type AnalysisType = 'full' | 'bugs' | 'security' | 'performance' | 'docs'

const ANALYSIS_OPTIONS = [
  {
    id: 'full' as AnalysisType,
    name: 'Full Analysis',
    description: 'Complete code review covering quality, bugs, security, and performance',
    icon: FileText,
    color: 'from-blue-500 to-cyan-500'
  },
  {
    id: 'bugs' as AnalysisType,
    name: 'Bug Detection',
    description: 'Find potential bugs, logic errors, and edge cases',
    icon: Bug,
    color: 'from-red-500 to-orange-500'
  },
  {
    id: 'security' as AnalysisType,
    name: 'Security Audit',
    description: 'Identify vulnerabilities and security issues',
    icon: Shield,
    color: 'from-purple-500 to-pink-500'
  },
  {
    id: 'performance' as AnalysisType,
    name: 'Performance Review',
    description: 'Find bottlenecks and optimization opportunities',
    icon: Gauge,
    color: 'from-green-500 to-emerald-500'
  }
]

const DOC_OPTIONS = [
  { id: 'readme', name: 'README.md', description: 'Professional project README' },
  { id: 'srs', name: 'SRS Document', description: 'Software Requirements Specification' },
  { id: 'api', name: 'API Docs', description: 'API reference documentation' },
  { id: 'architecture', name: 'Architecture', description: 'System architecture docs' },
  { id: 'all', name: 'All Docs', description: 'Generate complete documentation package' }
]

export default function ImportPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<'upload' | 'analyze' | 'results'>('upload')
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [project, setProject] = useState<UploadedProject | null>(null)

  const [analyzing, setAnalyzing] = useState(false)
  const [analysisType, setAnalysisType] = useState<AnalysisType | null>(null)
  const [analysisResult, setAnalysisResult] = useState<string>('')

  const [generatingDocs, setGeneratingDocs] = useState(false)
  const [docType, setDocType] = useState<string | null>(null)
  const [docResult, setDocResult] = useState<string>('')

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const file = e.dataTransfer.files[0]
    if (file && file.name.endsWith('.zip')) {
      uploadFile(file)
    } else {
      setUploadError('Please upload a ZIP file')
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadFile(file)
    }
  }

  const uploadFile = async (file: File) => {
    setUploading(true)
    setUploadError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('project_name', file.name.replace('.zip', ''))

      const token = localStorage.getItem('access_token')
      const response = await fetch(`${API_URL}/import/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      const data = await response.json()

      if (data.success) {
        setProject(data)
        setStep('analyze')
      } else {
        setUploadError(data.detail || 'Upload failed')
      }
    } catch (error) {
      setUploadError('Failed to upload file. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const runAnalysis = async (type: AnalysisType) => {
    if (!project) return

    setAnalysisType(type)
    setAnalyzing(true)
    setAnalysisResult('')

    try {
      const token = localStorage.getItem('access_token')
      const formData = new FormData()
      formData.append('analysis_type', type)

      const response = await fetch(`${API_URL}/import/analyze/${project.project_id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.type === 'content') {
                  setAnalysisResult(prev => prev + data.text)
                }
              } catch {}
            }
          }
        }
      }

      setStep('results')
    } catch (error) {
      setUploadError('Analysis failed. Please try again.')
    } finally {
      setAnalyzing(false)
    }
  }

  const generateDocs = async (type: string) => {
    if (!project) return

    setDocType(type)
    setGeneratingDocs(true)
    setDocResult('')

    try {
      const token = localStorage.getItem('access_token')
      const formData = new FormData()
      formData.append('doc_type', type)

      const response = await fetch(`${API_URL}/import/generate-docs/${project.project_id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.type === 'content') {
                  setDocResult(prev => prev + data.text)
                }
              } catch {}
            }
          }
        }
      }
    } catch (error) {
      setUploadError('Documentation generation failed. Please try again.')
    } finally {
      setGeneratingDocs(false)
    }
  }

  const downloadResult = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <header className="border-b border-[hsl(var(--bolt-border))]">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-[hsl(var(--bolt-text-primary))]">BharatBuild</span>
          </Link>

          <div className="flex items-center gap-4">
            <Link href="/build">
              <Button variant="outline" className="border-[hsl(var(--bolt-border))]">
                Go to Editor
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-12 max-w-5xl">
        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-12">
          {['Upload', 'Analyze', 'Results'].map((s, i) => (
            <div key={s} className="flex items-center">
              <div className={`
                w-10 h-10 rounded-full flex items-center justify-center font-bold
                ${step === s.toLowerCase() ? 'bg-gradient-to-br from-blue-500 to-cyan-500 text-white' :
                  ['upload', 'analyze', 'results'].indexOf(step) > i ? 'bg-green-500 text-white' :
                  'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))]'}
              `}>
                {['upload', 'analyze', 'results'].indexOf(step) > i ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  i + 1
                )}
              </div>
              <span className={`ml-2 font-medium ${
                step === s.toLowerCase() ? 'text-[hsl(var(--bolt-text-primary))]' : 'text-[hsl(var(--bolt-text-secondary))]'
              }`}>
                {s}
              </span>
              {i < 2 && (
                <ChevronRight className="w-5 h-5 mx-4 text-[hsl(var(--bolt-text-tertiary))]" />
              )}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* Step 1: Upload */}
          {step === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-[hsl(var(--bolt-text-primary))] mb-3">
                  Import Existing Project
                </h1>
                <p className="text-[hsl(var(--bolt-text-secondary))]">
                  Upload your project ZIP to analyze code, find bugs, and generate documentation
                </p>
              </div>

              {/* Upload Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`
                  border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all
                  ${isDragging ? 'border-cyan-500 bg-cyan-500/10' : 'border-[hsl(var(--bolt-border))] hover:border-cyan-500/50'}
                  ${uploading ? 'pointer-events-none opacity-50' : ''}
                `}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".zip"
                  onChange={handleFileSelect}
                  className="hidden"
                />

                {uploading ? (
                  <div className="flex flex-col items-center">
                    <Loader2 className="w-16 h-16 text-cyan-500 animate-spin mb-4" />
                    <p className="text-[hsl(var(--bolt-text-primary))] font-medium">Uploading and extracting...</p>
                  </div>
                ) : (
                  <>
                    <FileArchive className="w-16 h-16 text-[hsl(var(--bolt-text-secondary))] mx-auto mb-4" />
                    <p className="text-[hsl(var(--bolt-text-primary))] font-medium text-lg mb-2">
                      Drag & drop your project ZIP here
                    </p>
                    <p className="text-[hsl(var(--bolt-text-secondary))] text-sm mb-4">
                      or click to browse
                    </p>
                    <p className="text-[hsl(var(--bolt-text-tertiary))] text-xs">
                      Supports: .zip files up to 10MB
                    </p>
                  </>
                )}
              </div>

              {uploadError && (
                <div className="mt-4 flex items-center gap-2 text-red-400 bg-red-900/20 p-4 rounded-lg">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  {uploadError}
                </div>
              )}

              {/* Features */}
              <div className="grid md:grid-cols-3 gap-6 mt-12">
                {[
                  { icon: Bug, title: 'Bug Detection', desc: 'AI finds potential bugs and issues' },
                  { icon: Shield, title: 'Security Audit', desc: 'Identify vulnerabilities in your code' },
                  { icon: FileText, title: 'Auto Documentation', desc: 'Generate SRS, README, API docs' }
                ].map((feature, i) => (
                  <div key={i} className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6">
                    <feature.icon className="w-8 h-8 text-cyan-500 mb-3" />
                    <h3 className="font-semibold text-[hsl(var(--bolt-text-primary))] mb-1">{feature.title}</h3>
                    <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">{feature.desc}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2: Analyze */}
          {step === 'analyze' && project && (
            <motion.div
              key="analyze"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-[hsl(var(--bolt-text-primary))] mb-3">
                  Choose Analysis Type
                </h1>
                <p className="text-[hsl(var(--bolt-text-secondary))]">
                  Select what you want to analyze or generate for your project
                </p>
              </div>

              {/* Project Info */}
              <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6 mb-8">
                <div className="flex items-center gap-4">
                  <FolderTree className="w-10 h-10 text-cyan-500" />
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-[hsl(var(--bolt-text-primary))]">
                      {project.project_name}
                    </h2>
                    <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                      {project.total_files} files | {formatFileSize(project.total_size)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setStep('upload')
                      setProject(null)
                    }}
                  >
                    <X className="w-4 h-4 mr-1" /> Change
                  </Button>
                </div>
              </div>

              {/* Analysis Options */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">
                  Code Analysis
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {ANALYSIS_OPTIONS.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => runAnalysis(option.id)}
                      disabled={analyzing}
                      className={`
                        p-6 rounded-xl border text-left transition-all
                        ${analyzing && analysisType === option.id
                          ? 'border-cyan-500 bg-cyan-500/10'
                          : 'border-[hsl(var(--bolt-border))] hover:border-cyan-500/50 bg-[hsl(var(--bolt-bg-secondary))]'}
                        ${analyzing && analysisType !== option.id ? 'opacity-50' : ''}
                      `}
                    >
                      <div className="flex items-start gap-4">
                        <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${option.color} flex items-center justify-center`}>
                          <option.icon className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-semibold text-[hsl(var(--bolt-text-primary))] mb-1">
                            {option.name}
                          </h4>
                          <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                            {option.description}
                          </p>
                        </div>
                        {analyzing && analysisType === option.id ? (
                          <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
                        ) : (
                          <ArrowRight className="w-5 h-5 text-[hsl(var(--bolt-text-tertiary))]" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Documentation Options */}
              <div>
                <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] mb-4">
                  Generate Documentation
                </h3>
                <div className="grid md:grid-cols-3 gap-4">
                  {DOC_OPTIONS.map((option) => (
                    <button
                      key={option.id}
                      onClick={() => generateDocs(option.id)}
                      disabled={generatingDocs}
                      className={`
                        p-4 rounded-xl border text-left transition-all
                        ${generatingDocs && docType === option.id
                          ? 'border-cyan-500 bg-cyan-500/10'
                          : 'border-[hsl(var(--bolt-border))] hover:border-cyan-500/50 bg-[hsl(var(--bolt-bg-secondary))]'}
                        ${generatingDocs && docType !== option.id ? 'opacity-50' : ''}
                      `}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                          {option.name}
                        </span>
                        {generatingDocs && docType === option.id ? (
                          <Loader2 className="w-4 h-4 text-cyan-500 animate-spin" />
                        ) : (
                          <FileText className="w-4 h-4 text-[hsl(var(--bolt-text-tertiary))]" />
                        )}
                      </div>
                      <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                        {option.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Live Results Preview */}
              {(analysisResult || docResult) && (
                <div className="mt-8">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
                      {analysisResult ? 'Analysis Results' : 'Generated Documentation'}
                    </h3>
                    <Button
                      size="sm"
                      onClick={() => downloadResult(
                        analysisResult || docResult,
                        analysisResult ? `${project.project_name}-analysis.md` : `${project.project_name}-${docType}.md`
                      )}
                    >
                      <Download className="w-4 h-4 mr-1" /> Download
                    </Button>
                  </div>
                  <div className="bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6 max-h-96 overflow-y-auto">
                    <pre className="text-sm text-[hsl(var(--bolt-text-primary))] whitespace-pre-wrap font-mono">
                      {analysisResult || docResult}
                    </pre>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Step 3: Results */}
          {step === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="text-center mb-8">
                <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                <h1 className="text-3xl font-bold text-[hsl(var(--bolt-text-primary))] mb-3">
                  Analysis Complete!
                </h1>
                <p className="text-[hsl(var(--bolt-text-secondary))]">
                  Review the results below and download the report
                </p>
              </div>

              {/* Results */}
              <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-xl p-6 mb-8">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
                    {analysisType === 'full' ? 'Full Code Review' :
                     analysisType === 'bugs' ? 'Bug Detection Report' :
                     analysisType === 'security' ? 'Security Audit Report' :
                     'Performance Analysis'}
                  </h3>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadResult(analysisResult, `${project?.project_name}-${analysisType}.md`)}
                    >
                      <Download className="w-4 h-4 mr-1" /> Download Report
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => setStep('analyze')}
                    >
                      Run Another Analysis
                    </Button>
                  </div>
                </div>
                <div className="bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg p-6 max-h-[500px] overflow-y-auto">
                  <pre className="text-sm text-[hsl(var(--bolt-text-primary))] whitespace-pre-wrap font-mono">
                    {analysisResult}
                  </pre>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-center gap-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setStep('upload')
                    setProject(null)
                    setAnalysisResult('')
                  }}
                >
                  Import Another Project
                </Button>
                <Button onClick={() => router.push('/build')}>
                  Open in Editor <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
