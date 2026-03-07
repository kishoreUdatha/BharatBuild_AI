'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Loader2,
  Download,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Plus,
  Trash2,
  Save,
  Printer,
  ChevronDown,
  ChevronUp,
  Upload,
  FileUp,
  Search,
  Filter,
  Sparkles,
  Copy,
  ClipboardCheck
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import AccreditationNav from '@/components/AccreditationNav'

// DVV Metric Categories
const METRIC_CATEGORIES = {
  '1': { name: 'Curricular Aspects', metrics: ['1.1.1', '1.1.2', '1.2.1', '1.2.2', '1.3.1', '1.3.2', '1.4.1', '1.4.2'] },
  '2': { name: 'Teaching-Learning & Evaluation', metrics: ['2.1.1', '2.1.2', '2.2.1', '2.3.1', '2.4.1', '2.4.2', '2.5.1', '2.6.1', '2.6.2', '2.6.3'] },
  '3': { name: 'Research, Innovations & Extension', metrics: ['3.1.1', '3.2.1', '3.2.2', '3.3.1', '3.3.2', '3.4.1', '3.4.2', '3.4.3', '3.5.1', '3.6.1', '3.7.1'] },
  '4': { name: 'Infrastructure & Learning Resources', metrics: ['4.1.1', '4.1.2', '4.2.1', '4.3.1', '4.3.2', '4.4.1'] },
  '5': { name: 'Student Support & Progression', metrics: ['5.1.1', '5.1.2', '5.1.3', '5.2.1', '5.2.2', '5.3.1', '5.3.2', '5.4.1'] },
  '6': { name: 'Governance, Leadership & Management', metrics: ['6.1.1', '6.2.1', '6.2.2', '6.3.1', '6.3.2', '6.4.1', '6.5.1', '6.5.2'] },
  '7': { name: 'Institutional Values & Best Practices', metrics: ['7.1.1', '7.1.2', '7.1.3', '7.2.1', '7.3.1'] }
}

// Common DVV Query Types
const DVV_QUERY_TYPES = [
  'Data mismatch between years',
  'Supporting documents not clear',
  'Calculation error in metrics',
  'Missing evidence/proof',
  'Format not as per NAAC guidelines',
  'Incomplete data submission',
  'Clarification on methodology',
  'Year-wise breakup required',
  'Additional proof needed',
  'Other'
]

interface DVVEntry {
  id: string
  metric_number: string
  criterion: string
  original_data: string
  dvv_query: string
  query_type: string
  clarification_response: string
  supporting_evidence: string[]
  status: 'pending' | 'drafted' | 'reviewed' | 'submitted'
  ai_generated: boolean
}

interface InstitutionInfo {
  name: string
  aishe_code: string
  ssr_submission_date: string
  dvv_received_date: string
  response_deadline: string
  naac_cycle: number
  previous_grade: string
}

const defaultInstitution: InstitutionInfo = {
  name: '',
  aishe_code: '',
  ssr_submission_date: '',
  dvv_received_date: '',
  response_deadline: '',
  naac_cycle: 1,
  previous_grade: ''
}

export default function DVVClarificationsPage() {
  const router = useRouter()

  const [institution, setInstitution] = useState<InstitutionInfo>(defaultInstitution)
  const [entries, setEntries] = useState<DVVEntry[]>([])
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set())
  const [isGenerating, setIsGenerating] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filterCriterion, setFilterCriterion] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    // Load saved institution profile
    const savedInstitution = localStorage.getItem('naac_institution_profile')
    if (savedInstitution) {
      const inst = JSON.parse(savedInstitution)
      setInstitution(prev => ({
        ...prev,
        name: inst.name || '',
        aishe_code: inst.aishe_code || '',
        naac_cycle: inst.naac_cycle || 1,
        previous_grade: inst.previous_grade || ''
      }))
    }

    // Load saved DVV data
    const savedDVV = localStorage.getItem('naac_dvv_clarifications')
    if (savedDVV) {
      const data = JSON.parse(savedDVV)
      setInstitution(prev => ({ ...prev, ...data.institution }))
      setEntries(data.entries || [])
    }
  }, [])

  const handleSave = () => {
    setIsSaving(true)
    localStorage.setItem('naac_dvv_clarifications', JSON.stringify({
      institution,
      entries,
      savedAt: new Date().toISOString()
    }))
    setIsSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const addNewEntry = () => {
    const newEntry: DVVEntry = {
      id: `dvv-${Date.now()}`,
      metric_number: '',
      criterion: '',
      original_data: '',
      dvv_query: '',
      query_type: '',
      clarification_response: '',
      supporting_evidence: [],
      status: 'pending',
      ai_generated: false
    }
    setEntries([...entries, newEntry])
    setExpandedEntries(new Set([...expandedEntries, newEntry.id]))
  }

  const updateEntry = (id: string, field: keyof DVVEntry, value: any) => {
    setEntries(entries.map(entry => {
      if (entry.id === id) {
        const updated = { ...entry, [field]: value }
        // Auto-detect criterion from metric number
        if (field === 'metric_number' && value) {
          updated.criterion = value.split('.')[0]
        }
        return updated
      }
      return entry
    }))
  }

  const removeEntry = (id: string) => {
    setEntries(entries.filter(entry => entry.id !== id))
    const newExpanded = new Set(expandedEntries)
    newExpanded.delete(id)
    setExpandedEntries(newExpanded)
  }

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedEntries)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedEntries(newExpanded)
  }

  const addEvidence = (entryId: string) => {
    setEntries(entries.map(entry => {
      if (entry.id === entryId) {
        return {
          ...entry,
          supporting_evidence: [...entry.supporting_evidence, '']
        }
      }
      return entry
    }))
  }

  const updateEvidence = (entryId: string, evidenceIndex: number, value: string) => {
    setEntries(entries.map(entry => {
      if (entry.id === entryId) {
        const newEvidence = [...entry.supporting_evidence]
        newEvidence[evidenceIndex] = value
        return { ...entry, supporting_evidence: newEvidence }
      }
      return entry
    }))
  }

  const removeEvidence = (entryId: string, evidenceIndex: number) => {
    setEntries(entries.map(entry => {
      if (entry.id === entryId) {
        return {
          ...entry,
          supporting_evidence: entry.supporting_evidence.filter((_, i) => i !== evidenceIndex)
        }
      }
      return entry
    }))
  }

  const generateAIResponse = async (entryId: string) => {
    const entry = entries.find(e => e.id === entryId)
    if (!entry || !entry.metric_number || !entry.dvv_query) {
      setError('Please fill in metric number and DVV query first')
      return
    }

    setIsGenerating(entryId)
    setError(null)

    try {
      const response = await apiClient.post('/accreditation/dvv/generate-response', {
        institution_name: institution.name,
        metric_number: entry.metric_number,
        original_data: entry.original_data,
        dvv_query: entry.dvv_query,
        query_type: entry.query_type
      })

      if (response.clarification) {
        updateEntry(entryId, 'clarification_response', response.clarification)
        updateEntry(entryId, 'ai_generated', true)
        updateEntry(entryId, 'status', 'drafted')

        if (response.suggested_evidence) {
          updateEntry(entryId, 'supporting_evidence', response.suggested_evidence)
        }
      }
    } catch (err: any) {
      // Fallback with template response if API fails
      const templateResponse = generateTemplateResponse(entry)
      updateEntry(entryId, 'clarification_response', templateResponse)
      updateEntry(entryId, 'ai_generated', false)
      updateEntry(entryId, 'status', 'drafted')
    } finally {
      setIsGenerating(null)
    }
  }

  const generateTemplateResponse = (entry: DVVEntry): string => {
    const templates: Record<string, string> = {
      'Data mismatch between years': `With reference to the DVV query on Metric ${entry.metric_number}, we would like to clarify that the data submitted is accurate and verified. The apparent mismatch is due to [reason]. We have attached year-wise breakup documents as supporting evidence.\n\nThe correct data is as follows:\n- Year 1: [data]\n- Year 2: [data]\n- Year 3: [data]\n- Year 4: [data]\n- Year 5: [data]\n\nSupporting documents attached for verification.`,
      'Supporting documents not clear': `In response to the DVV observation regarding Metric ${entry.metric_number}, we are providing clearer supporting documents. The original submission has been reviewed and we now attach:\n\n1. [Document 1 - Description]\n2. [Document 2 - Description]\n3. [Document 3 - Description]\n\nThese documents clearly establish the data claimed in the SSR.`,
      'Calculation error in metrics': `We acknowledge the observation on Metric ${entry.metric_number}. After reviewing our calculations, we confirm that:\n\nOriginal calculation: ${entry.original_data}\nCorrected calculation: [corrected value]\n\nThe calculation methodology follows NAAC guidelines. Detailed calculation sheet is attached.`,
      'Missing evidence/proof': `In response to the DVV query for Metric ${entry.metric_number} regarding missing evidence, we are now providing the following documents:\n\n1. [Evidence Document 1]\n2. [Evidence Document 2]\n3. [Consolidated List/Register]\n\nThese documents substantiate the data claimed in our SSR submission.`,
      'Format not as per NAAC guidelines': `We have reformatted the data for Metric ${entry.metric_number} as per NAAC DVV guidelines. The revised submission includes:\n\n1. Data in prescribed template format\n2. Year-wise segregation\n3. Required certifications\n\nPlease find the reformatted documents attached.`,
      'Other': `With reference to DVV query on Metric ${entry.metric_number}:\n\nQuery: ${entry.dvv_query}\n\nClarification:\n[Provide detailed clarification here]\n\nSupporting Evidence:\n1. [Document 1]\n2. [Document 2]\n\nWe trust this clarifies the query raised.`
    }

    return templates[entry.query_type] || templates['Other']
  }

  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(`
        <html>
          <head>
            <title>DVV Clarifications - ${institution.name}</title>
            <style>
              body { font-family: 'Times New Roman', serif; padding: 40px; line-height: 1.6; font-size: 12pt; }
              h1 { text-align: center; font-size: 16pt; margin-bottom: 5px; }
              h2 { text-align: center; font-size: 14pt; margin-top: 5px; }
              h3 { font-size: 12pt; margin-top: 20px; border-bottom: 1px solid #000; padding-bottom: 5px; }
              .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #000; padding-bottom: 20px; }
              .institution-info { margin-bottom: 20px; }
              .institution-info p { margin: 5px 0; }
              .metric-entry { margin-bottom: 30px; page-break-inside: avoid; border: 1px solid #ccc; padding: 15px; }
              .metric-header { background: #f0f0f0; padding: 10px; margin: -15px -15px 15px -15px; }
              .label { font-weight: bold; }
              .field { margin-bottom: 10px; }
              .evidence-list { margin-left: 20px; }
              .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10pt; }
              .status-submitted { background: #d4edda; color: #155724; }
              .status-reviewed { background: #cce5ff; color: #004085; }
              .status-drafted { background: #fff3cd; color: #856404; }
              .status-pending { background: #f8d7da; color: #721c24; }
              .signature { margin-top: 60px; text-align: right; }
              .footer { margin-top: 40px; text-align: center; font-size: 10pt; color: #666; }
              @media print {
                body { padding: 20px; }
                .metric-entry { page-break-inside: avoid; }
              }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>DATA VALIDATION AND VERIFICATION (DVV)</h1>
              <h2>CLARIFICATION RESPONSES</h2>
              <h2>${institution.name || '[Institution Name]'}</h2>
            </div>

            <div class="institution-info">
              <p><span class="label">AISHE Code:</span> ${institution.aishe_code || '___________'}</p>
              <p><span class="label">NAAC Cycle:</span> ${institution.naac_cycle || '___'}${institution.naac_cycle === 1 ? 'st' : institution.naac_cycle === 2 ? 'nd' : institution.naac_cycle === 3 ? 'rd' : 'th'} Cycle</p>
              <p><span class="label">SSR Submission Date:</span> ${institution.ssr_submission_date || '___________'}</p>
              <p><span class="label">DVV Queries Received:</span> ${institution.dvv_received_date || '___________'}</p>
              <p><span class="label">Response Deadline:</span> ${institution.response_deadline || '___________'}</p>
            </div>

            <h3>METRIC-WISE CLARIFICATIONS</h3>

            ${entries.map((entry, index) => `
              <div class="metric-entry">
                <div class="metric-header">
                  <strong>Metric ${entry.metric_number || '___'}</strong> - Criterion ${entry.criterion || '___'}: ${METRIC_CATEGORIES[entry.criterion as keyof typeof METRIC_CATEGORIES]?.name || ''}
                  <span class="status status-${entry.status}" style="float: right;">${entry.status.toUpperCase()}</span>
                </div>

                <div class="field">
                  <span class="label">Original Data Submitted:</span><br/>
                  ${entry.original_data || '[Original data]'}
                </div>

                <div class="field">
                  <span class="label">DVV Query/Observation:</span><br/>
                  ${entry.dvv_query || '[DVV query]'}
                </div>

                <div class="field">
                  <span class="label">Clarification Response:</span><br/>
                  ${entry.clarification_response || '[Response pending]'}
                </div>

                ${entry.supporting_evidence.length > 0 ? `
                  <div class="field">
                    <span class="label">Supporting Evidence:</span>
                    <ul class="evidence-list">
                      ${entry.supporting_evidence.map(ev => `<li>${ev}</li>`).join('')}
                    </ul>
                  </div>
                ` : ''}
              </div>
            `).join('')}

            <div class="signature">
              <p>_______________________________</p>
              <p>Head of the Institution</p>
              <p>(Signature with Seal)</p>
              <p>Date: _______________</p>
            </div>

            <div class="footer">
              <p>This document is prepared as per NAAC DVV guidelines</p>
              <p>Total Metrics Addressed: ${entries.length}</p>
            </div>
          </body>
        </html>
      `)
      printWindow.document.close()
      printWindow.print()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  // Filter entries
  const filteredEntries = entries.filter(entry => {
    if (filterCriterion !== 'all' && entry.criterion !== filterCriterion) return false
    if (filterStatus !== 'all' && entry.status !== filterStatus) return false
    if (searchQuery && !entry.metric_number.includes(searchQuery) && !entry.dvv_query.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  // Stats
  const stats = {
    total: entries.length,
    pending: entries.filter(e => e.status === 'pending').length,
    drafted: entries.filter(e => e.status === 'drafted').length,
    reviewed: entries.filter(e => e.status === 'reviewed').length,
    submitted: entries.filter(e => e.status === 'submitted').length
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <AccreditationNav />

      <div className="max-w-6xl mx-auto px-4 py-8">
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
              <h1 className="text-2xl font-bold">DVV Clarifications</h1>
              <p className="text-slate-400">Data Validation & Verification Responses</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {saved && (
              <span className="flex items-center gap-2 text-green-400 text-sm">
                <CheckCircle2 className="w-4 h-4" />
                Saved
              </span>
            )}
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
            >
              <Printer className="w-4 h-4" />
              Print
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Save All
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-300 hover:text-white">×</button>
          </div>
        )}

        {/* Institution Info */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-orange-500" />
            Institution Details
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Institution Name</label>
              <input
                type="text"
                value={institution.name}
                onChange={e => setInstitution({ ...institution, name: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                placeholder="Enter institution name"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">AISHE Code</label>
              <input
                type="text"
                value={institution.aishe_code}
                onChange={e => setInstitution({ ...institution, aishe_code: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                placeholder="e.g., C-12345"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">NAAC Cycle</label>
              <select
                value={institution.naac_cycle}
                onChange={e => setInstitution({ ...institution, naac_cycle: parseInt(e.target.value) })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              >
                <option value={1}>1st Cycle</option>
                <option value={2}>2nd Cycle</option>
                <option value={3}>3rd Cycle</option>
                <option value={4}>4th Cycle</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">SSR Submission Date</label>
              <input
                type="date"
                value={institution.ssr_submission_date}
                onChange={e => setInstitution({ ...institution, ssr_submission_date: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">DVV Queries Received Date</label>
              <input
                type="date"
                value={institution.dvv_received_date}
                onChange={e => setInstitution({ ...institution, dvv_received_date: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Response Deadline</label>
              <input
                type="date"
                value={institution.response_deadline}
                onChange={e => setInstitution({ ...institution, response_deadline: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold">{stats.total}</p>
            <p className="text-sm text-slate-400">Total Metrics</p>
          </div>
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-red-400">{stats.pending}</p>
            <p className="text-sm text-slate-400">Pending</p>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-yellow-400">{stats.drafted}</p>
            <p className="text-sm text-slate-400">Drafted</p>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-blue-400">{stats.reviewed}</p>
            <p className="text-sm text-slate-400">Reviewed</p>
          </div>
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-green-400">{stats.submitted}</p>
            <p className="text-sm text-slate-400">Submitted</p>
          </div>
        </div>

        {/* Filters & Actions */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-2">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search metrics..."
              className="bg-transparent border-none focus:outline-none w-40"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={filterCriterion}
              onChange={e => setFilterCriterion(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
            >
              <option value="all">All Criteria</option>
              {Object.entries(METRIC_CATEGORIES).map(([key, val]) => (
                <option key={key} value={key}>Criterion {key}</option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="drafted">Drafted</option>
              <option value="reviewed">Reviewed</option>
              <option value="submitted">Submitted</option>
            </select>
          </div>

          <div className="ml-auto">
            <button
              onClick={addNewEntry}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add DVV Entry
            </button>
          </div>
        </div>

        {/* DVV Entries */}
        <div className="space-y-4">
          {filteredEntries.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
              <ClipboardCheck className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No DVV Entries Yet</h3>
              <p className="text-slate-400 mb-4">Click "Add DVV Entry" to start adding metric-wise clarifications</p>
              <button
                onClick={addNewEntry}
                className="inline-flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg"
              >
                <Plus className="w-4 h-4" />
                Add First Entry
              </button>
            </div>
          ) : (
            filteredEntries.map((entry, index) => (
              <div key={entry.id} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                {/* Entry Header */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-800/50"
                  onClick={() => toggleExpanded(entry.id)}
                >
                  <div className="flex items-center gap-4">
                    <span className="text-lg font-mono font-bold text-orange-500">
                      {entry.metric_number || 'New'}
                    </span>
                    <span className="text-slate-400">
                      {entry.criterion ? `Criterion ${entry.criterion}: ${METRIC_CATEGORIES[entry.criterion as keyof typeof METRIC_CATEGORIES]?.name || ''}` : 'Select metric'}
                    </span>
                    {entry.ai_generated && (
                      <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded-full flex items-center gap-1">
                        <Sparkles className="w-3 h-3" /> AI Generated
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      entry.status === 'submitted' ? 'bg-green-500/20 text-green-400' :
                      entry.status === 'reviewed' ? 'bg-blue-500/20 text-blue-400' :
                      entry.status === 'drafted' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {entry.status.toUpperCase()}
                    </span>
                    {expandedEntries.has(entry.id) ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </div>
                </div>

                {/* Entry Content */}
                {expandedEntries.has(entry.id) && (
                  <div className="p-4 border-t border-slate-800 space-y-4">
                    {/* Row 1: Metric & Query Type */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm text-slate-400 mb-1">Metric Number *</label>
                        <select
                          value={entry.metric_number}
                          onChange={e => updateEntry(entry.id, 'metric_number', e.target.value)}
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                        >
                          <option value="">Select Metric</option>
                          {Object.entries(METRIC_CATEGORIES).map(([criterion, data]) => (
                            <optgroup key={criterion} label={`Criterion ${criterion}: ${data.name}`}>
                              {data.metrics.map(metric => (
                                <option key={metric} value={metric}>{metric}</option>
                              ))}
                            </optgroup>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-slate-400 mb-1">Query Type</label>
                        <select
                          value={entry.query_type}
                          onChange={e => updateEntry(entry.id, 'query_type', e.target.value)}
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                        >
                          <option value="">Select Type</option>
                          {DVV_QUERY_TYPES.map(type => (
                            <option key={type} value={type}>{type}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm text-slate-400 mb-1">Status</label>
                        <select
                          value={entry.status}
                          onChange={e => updateEntry(entry.id, 'status', e.target.value as DVVEntry['status'])}
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                        >
                          <option value="pending">Pending</option>
                          <option value="drafted">Drafted</option>
                          <option value="reviewed">Reviewed</option>
                          <option value="submitted">Submitted</option>
                        </select>
                      </div>
                    </div>

                    {/* Row 2: Original Data */}
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Original Data Submitted in SSR</label>
                      <textarea
                        value={entry.original_data}
                        onChange={e => updateEntry(entry.id, 'original_data', e.target.value)}
                        rows={2}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="Enter the original data/value submitted in SSR..."
                      />
                    </div>

                    {/* Row 3: DVV Query */}
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">DVV Query/Observation *</label>
                      <textarea
                        value={entry.dvv_query}
                        onChange={e => updateEntry(entry.id, 'dvv_query', e.target.value)}
                        rows={3}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="Enter the exact DVV query/observation received..."
                      />
                    </div>

                    {/* Row 4: Clarification Response */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-sm text-slate-400">Clarification Response</label>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => generateAIResponse(entry.id)}
                            disabled={isGenerating === entry.id}
                            className="flex items-center gap-1 px-3 py-1 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 rounded-lg text-sm"
                          >
                            {isGenerating === entry.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Sparkles className="w-3 h-3" />
                            )}
                            Generate AI Response
                          </button>
                          {entry.clarification_response && (
                            <button
                              onClick={() => copyToClipboard(entry.clarification_response)}
                              className="p-1 hover:bg-slate-700 rounded"
                              title="Copy to clipboard"
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                      <textarea
                        value={entry.clarification_response}
                        onChange={e => updateEntry(entry.id, 'clarification_response', e.target.value)}
                        rows={6}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="Enter your clarification response or click 'Generate AI Response'..."
                      />
                    </div>

                    {/* Row 5: Supporting Evidence */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm text-slate-400">Supporting Evidence</label>
                        <button
                          onClick={() => addEvidence(entry.id)}
                          className="flex items-center gap-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 rounded text-sm"
                        >
                          <Plus className="w-3 h-3" />
                          Add Evidence
                        </button>
                      </div>
                      <div className="space-y-2">
                        {entry.supporting_evidence.map((evidence, evidenceIndex) => (
                          <div key={evidenceIndex} className="flex items-center gap-2">
                            <span className="text-slate-500 text-sm w-6">{evidenceIndex + 1}.</span>
                            <input
                              type="text"
                              value={evidence}
                              onChange={e => updateEvidence(entry.id, evidenceIndex, e.target.value)}
                              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-orange-500"
                              placeholder="e.g., Annexure 1.2.1 - Student list with signatures"
                            />
                            <button
                              onClick={() => removeEvidence(entry.id, evidenceIndex)}
                              className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        {entry.supporting_evidence.length === 0 && (
                          <p className="text-slate-500 text-sm">No evidence added yet</p>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                      <button
                        onClick={() => removeEntry(entry.id)}
                        className="flex items-center gap-2 px-3 py-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete Entry
                      </button>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => copyToClipboard(`Metric ${entry.metric_number}\n\nDVV Query: ${entry.dvv_query}\n\nClarification: ${entry.clarification_response}\n\nSupporting Evidence:\n${entry.supporting_evidence.map((e, i) => `${i + 1}. ${e}`).join('\n')}`)}
                          className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm"
                        >
                          <Copy className="w-4 h-4" />
                          Copy All
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Help Section */}
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-xl p-6">
          <h3 className="font-semibold text-blue-400 mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5" />
            DVV Response Guidelines
          </h3>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>• Provide specific, factual responses to each DVV query</li>
            <li>• Reference exact document names and annexure numbers</li>
            <li>• Include year-wise breakup where applicable</li>
            <li>• Attach clear, legible supporting documents</li>
            <li>• Ensure all calculations match NAAC methodology</li>
            <li>• Get responses reviewed by IQAC before final submission</li>
            <li>• Submit within the deadline specified by NAAC</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
