'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Download,
  Upload,
  Search,
  Filter,
  Plus,
  Trash2,
  Edit3,
  Save,
  CheckCircle2,
  AlertTriangle,
  FolderOpen,
  ArrowLeft,
  ChevronDown,
  X
} from 'lucide-react'

interface EvidenceRecord {
  id: string
  criterion: number
  metric_no: string
  metric_title: string
  data_required: string
  evidence_type: string
  source_dept: string
  file_location: string
  responsible: string
  status: 'pending' | 'collected' | 'verified' | 'uploaded'
  academic_year: string
  notes: string
  uploaded_file?: string
}

const CRITERIA_NAMES = [
  'Curricular Aspects',
  'Teaching-Learning & Evaluation',
  'Research, Innovations & Extension',
  'Infrastructure & Learning Resources',
  'Student Support & Progression',
  'Governance, Leadership & Management',
  'Institutional Values & Best Practices',
]

const SAMPLE_METRICS: Partial<EvidenceRecord>[] = [
  { criterion: 1, metric_no: '1.1.1', metric_title: 'Curriculum Design & Development', data_required: 'BOS Minutes, Curriculum Documents', evidence_type: 'PDF', source_dept: 'Academics' },
  { criterion: 1, metric_no: '1.2.1', metric_title: 'Value Added Courses', data_required: 'Course List, Attendance, Certificates', evidence_type: 'PDF/Excel', source_dept: 'Departments' },
  { criterion: 1, metric_no: '1.3.1', metric_title: 'Curriculum Enrichment', data_required: 'Cross-cutting issues integration', evidence_type: 'PDF', source_dept: 'Academics' },
  { criterion: 2, metric_no: '2.1.1', metric_title: 'Student Enrollment', data_required: 'Admission data, Seat matrix', evidence_type: 'Excel', source_dept: 'Admissions' },
  { criterion: 2, metric_no: '2.3.1', metric_title: 'ICT Tools Usage', data_required: 'LMS Screenshots, Usage logs', evidence_type: 'Image/PDF', source_dept: 'IT' },
  { criterion: 2, metric_no: '2.4.1', metric_title: 'Faculty Qualifications', data_required: 'Faculty list with qualifications', evidence_type: 'Excel/PDF', source_dept: 'HR' },
  { criterion: 3, metric_no: '3.1.1', metric_title: 'Research Grants', data_required: 'Sanction letters, Utilization', evidence_type: 'PDF', source_dept: 'R&D' },
  { criterion: 3, metric_no: '3.2.1', metric_title: 'Research Papers', data_required: 'Publications list, Papers', evidence_type: 'PDF', source_dept: 'R&D' },
  { criterion: 3, metric_no: '3.3.1', metric_title: 'Extension Activities', data_required: 'Activity reports, Photos', evidence_type: 'PDF/JPG', source_dept: 'NSS/NCC' },
  { criterion: 4, metric_no: '4.1.1', metric_title: 'Infrastructure Facilities', data_required: 'Asset Register, Photos', evidence_type: 'PDF/JPG', source_dept: 'Admin' },
  { criterion: 4, metric_no: '4.2.1', metric_title: 'Library Resources', data_required: 'Book list, Subscriptions', evidence_type: 'Excel/PDF', source_dept: 'Library' },
  { criterion: 5, metric_no: '5.1.1', metric_title: 'Scholarships', data_required: 'Scholarship data, Sanctions', evidence_type: 'Excel/PDF', source_dept: 'Accounts' },
  { criterion: 5, metric_no: '5.2.1', metric_title: 'Placements', data_required: 'Offer Letters, Placement data', evidence_type: 'PDF/Excel', source_dept: 'T&P' },
  { criterion: 5, metric_no: '5.3.1', metric_title: 'Alumni Engagement', data_required: 'Alumni meet reports, Contributions', evidence_type: 'PDF', source_dept: 'Alumni Cell' },
  { criterion: 6, metric_no: '6.1.1', metric_title: 'Vision & Mission', data_required: 'Policy Documents, Display photos', evidence_type: 'PDF/JPG', source_dept: 'IQAC' },
  { criterion: 6, metric_no: '6.2.1', metric_title: 'Strategic Plan', data_required: 'Perspective plan document', evidence_type: 'PDF', source_dept: 'Management' },
  { criterion: 6, metric_no: '6.5.1', metric_title: 'IQAC Activities', data_required: 'IQAC Minutes, ATR', evidence_type: 'PDF', source_dept: 'IQAC' },
  { criterion: 7, metric_no: '7.1.1', metric_title: 'Green Campus', data_required: 'Audit reports, Photos', evidence_type: 'PDF/JPG', source_dept: 'Admin' },
  { criterion: 7, metric_no: '7.2.1', metric_title: 'Best Practices', data_required: 'Best practice documentation', evidence_type: 'PDF', source_dept: 'IQAC' },
  { criterion: 7, metric_no: '7.3.1', metric_title: 'Institutional Distinctiveness', data_required: 'Distinctiveness document', evidence_type: 'PDF', source_dept: 'IQAC' },
]

const STATUS_COLORS = {
  pending: 'bg-red-500/20 text-red-400',
  collected: 'bg-yellow-500/20 text-yellow-400',
  verified: 'bg-blue-500/20 text-blue-400',
  uploaded: 'bg-green-500/20 text-green-400',
}

export default function EvidenceMappingPage() {
  const router = useRouter()
  const [records, setRecords] = useState<EvidenceRecord[]>([])
  const [filterCriterion, setFilterCriterion] = useState<number | 'all'>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterYear, setFilterYear] = useState<string>('2023-24')
  const [search, setSearch] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const savedRecords = localStorage.getItem('naac_evidence_records')
    if (savedRecords) {
      setRecords(JSON.parse(savedRecords))
    } else {
      // Initialize with sample metrics
      const initialRecords: EvidenceRecord[] = SAMPLE_METRICS.map((m, idx) => ({
        id: `${idx + 1}`,
        criterion: m.criterion!,
        metric_no: m.metric_no!,
        metric_title: m.metric_title!,
        data_required: m.data_required!,
        evidence_type: m.evidence_type!,
        source_dept: m.source_dept!,
        file_location: `C${m.criterion}/${filterYear}`,
        responsible: `C${m.criterion} Coordinator`,
        status: 'pending',
        academic_year: filterYear,
        notes: '',
      }))
      setRecords(initialRecords)
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('naac_evidence_records', JSON.stringify(records))
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const filteredRecords = records.filter(r => {
    const matchesCriterion = filterCriterion === 'all' || r.criterion === filterCriterion
    const matchesStatus = filterStatus === 'all' || r.status === filterStatus
    const matchesYear = r.academic_year === filterYear
    const matchesSearch = search === '' ||
      r.metric_no.toLowerCase().includes(search.toLowerCase()) ||
      r.metric_title.toLowerCase().includes(search.toLowerCase())
    return matchesCriterion && matchesStatus && matchesYear && matchesSearch
  })

  const getStats = () => {
    const yearRecords = records.filter(r => r.academic_year === filterYear)
    return {
      total: yearRecords.length,
      pending: yearRecords.filter(r => r.status === 'pending').length,
      collected: yearRecords.filter(r => r.status === 'collected').length,
      verified: yearRecords.filter(r => r.status === 'verified').length,
      uploaded: yearRecords.filter(r => r.status === 'uploaded').length,
    }
  }

  const stats = getStats()
  const completionPercent = stats.total > 0 ? Math.round((stats.uploaded / stats.total) * 100) : 0

  const updateRecord = (id: string, field: keyof EvidenceRecord, value: any) => {
    setRecords(prev => prev.map(r => r.id === id ? { ...r, [field]: value } : r))
  }

  const addRecord = () => {
    const newRecord: EvidenceRecord = {
      id: Date.now().toString(),
      criterion: 1,
      metric_no: '',
      metric_title: '',
      data_required: '',
      evidence_type: 'PDF',
      source_dept: '',
      file_location: '',
      responsible: '',
      status: 'pending',
      academic_year: filterYear,
      notes: '',
    }
    setRecords(prev => [...prev, newRecord])
    setEditingId(newRecord.id)
  }

  const deleteRecord = (id: string) => {
    if (confirm('Delete this record?')) {
      setRecords(prev => prev.filter(r => r.id !== id))
    }
  }

  const exportToCSV = () => {
    const headers = ['Criterion', 'Metric No', 'Metric Title', 'Data Required', 'Evidence Type', 'Source Dept', 'File Location', 'Responsible', 'Status', 'Academic Year', 'Notes']
    const rows = filteredRecords.map(r => [
      `C${r.criterion}`,
      r.metric_no,
      r.metric_title,
      r.data_required,
      r.evidence_type,
      r.source_dept,
      r.file_location,
      r.responsible,
      r.status,
      r.academic_year,
      r.notes
    ])

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `NAAC_Evidence_Mapping_${filterYear}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button onClick={() => router.back()} className="p-2 hover:bg-slate-800 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">Evidence Mapping Sheet</h1>
              <p className="text-slate-400">Master control file for SSR & AQAR</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {saved && (
              <span className="flex items-center gap-2 text-green-400 text-sm">
                <CheckCircle2 className="w-4 h-4" /> Saved
              </span>
            )}
            <button onClick={exportToCSV} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg">
              <Download className="w-4 h-4" /> Export CSV
            </button>
            <button onClick={handleSave} className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg">
              <Save className="w-4 h-4" /> Save
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-slate-400">Total Metrics</div>
          </div>
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-400">{stats.pending}</div>
            <div className="text-sm text-red-400">Pending</div>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">{stats.collected}</div>
            <div className="text-sm text-yellow-400">Collected</div>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">{stats.verified}</div>
            <div className="text-sm text-blue-400">Verified</div>
          </div>
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-green-400">{stats.uploaded}</div>
            <div className="text-sm text-green-400">Uploaded ({completionPercent}%)</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search metrics..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2"
            />
          </div>
          <select
            value={filterYear}
            onChange={e => setFilterYear(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2"
          >
            <option value="2021-22">2021-22</option>
            <option value="2022-23">2022-23</option>
            <option value="2023-24">2023-24</option>
            <option value="2024-25">2024-25</option>
          </select>
          <select
            value={filterCriterion === 'all' ? 'all' : filterCriterion}
            onChange={e => setFilterCriterion(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2"
          >
            <option value="all">All Criteria</option>
            {[1, 2, 3, 4, 5, 6, 7].map(c => (
              <option key={c} value={c}>C{c}: {CRITERIA_NAMES[c - 1]}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="collected">Collected</option>
            <option value="verified">Verified</option>
            <option value="uploaded">Uploaded</option>
          </select>
          <button onClick={addRecord} className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg">
            <Plus className="w-4 h-4" /> Add Metric
          </button>
        </div>

        {/* Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800/50">
                  <th className="text-left p-3 font-medium">Criterion</th>
                  <th className="text-left p-3 font-medium">Metric No</th>
                  <th className="text-left p-3 font-medium">Metric Title</th>
                  <th className="text-left p-3 font-medium">Data Required</th>
                  <th className="text-left p-3 font-medium">Type</th>
                  <th className="text-left p-3 font-medium">Source</th>
                  <th className="text-left p-3 font-medium">Location</th>
                  <th className="text-left p-3 font-medium">Responsible</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((record) => (
                  <tr key={record.id} className="border-t border-slate-800 hover:bg-slate-800/30">
                    <td className="p-3">
                      <span className="px-2 py-1 bg-orange-500/20 text-orange-400 rounded text-xs font-medium">
                        C{record.criterion}
                      </span>
                    </td>
                    <td className="p-3">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.metric_no}
                          onChange={e => updateRecord(record.id, 'metric_no', e.target.value)}
                          className="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="font-mono">{record.metric_no}</span>
                      )}
                    </td>
                    <td className="p-3 max-w-xs">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.metric_title}
                          onChange={e => updateRecord(record.id, 'metric_title', e.target.value)}
                          className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="truncate block">{record.metric_title}</span>
                      )}
                    </td>
                    <td className="p-3 max-w-xs">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.data_required}
                          onChange={e => updateRecord(record.id, 'data_required', e.target.value)}
                          className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="text-slate-400 truncate block">{record.data_required}</span>
                      )}
                    </td>
                    <td className="p-3">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.evidence_type}
                          onChange={e => updateRecord(record.id, 'evidence_type', e.target.value)}
                          className="w-20 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="text-xs">{record.evidence_type}</span>
                      )}
                    </td>
                    <td className="p-3">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.source_dept}
                          onChange={e => updateRecord(record.id, 'source_dept', e.target.value)}
                          className="w-24 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="text-xs">{record.source_dept}</span>
                      )}
                    </td>
                    <td className="p-3">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.file_location}
                          onChange={e => updateRecord(record.id, 'file_location', e.target.value)}
                          className="w-28 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="text-xs font-mono text-slate-400">{record.file_location}</span>
                      )}
                    </td>
                    <td className="p-3">
                      {editingId === record.id ? (
                        <input
                          type="text"
                          value={record.responsible}
                          onChange={e => updateRecord(record.id, 'responsible', e.target.value)}
                          className="w-28 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="text-xs">{record.responsible}</span>
                      )}
                    </td>
                    <td className="p-3">
                      <select
                        value={record.status}
                        onChange={e => updateRecord(record.id, 'status', e.target.value)}
                        className={`text-xs px-2 py-1 rounded border-0 ${STATUS_COLORS[record.status]}`}
                      >
                        <option value="pending">Pending</option>
                        <option value="collected">Collected</option>
                        <option value="verified">Verified</option>
                        <option value="uploaded">Uploaded</option>
                      </select>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-1">
                        {editingId === record.id ? (
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 text-green-400 hover:bg-green-500/20 rounded"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => setEditingId(record.id)}
                            className="p-1 text-slate-400 hover:bg-slate-700 rounded"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => deleteRecord(record.id)}
                          className="p-1 text-red-400 hover:bg-red-500/20 rounded"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Folder Structure Guide */}
        <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-orange-500" />
            Recommended Folder Structure
          </h3>
          <pre className="text-sm text-slate-400 font-mono bg-slate-800 p-4 rounded-lg overflow-x-auto">
{`NAAC/
├── SSR/
├── AQAR/
│   ├── AQAR_2021-22/
│   ├── AQAR_2022-23/
│   └── AQAR_2023-24/
├── Criteria/
│   ├── C1_Curricular_Aspects/
│   │   ├── 2021-22/
│   │   ├── 2022-23/
│   │   └── 2023-24/
│   ├── C2_Teaching_Learning/
│   ├── C3_Research_Innovation/
│   ├── C4_Infrastructure/
│   ├── C5_Student_Support/
│   ├── C6_Governance/
│   └── C7_Institutional_Values/
├── IQAC/
│   ├── Formation/
│   ├── Meeting_Minutes/
│   └── Action_Taken_Reports/
└── Peer_Team_Visit/

📌 Naming Rule: MetricNo_Description_Year.pdf
   Example: 2.3.1_ICT_Usage_2023-24.pdf`}
          </pre>
        </div>

        {/* Usage Note */}
        <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-xl p-4">
          <p className="text-sm text-green-400">
            ✅ This sheet is mandatory for internal audit & Peer Team Q&A. Keep it updated regularly!
          </p>
        </div>
      </div>
    </div>
  )
}
