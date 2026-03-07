'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Download,
  Building,
  Users,
  Shield,
  ClipboardList,
  ArrowLeft,
  Printer,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Edit3,
  Save,
  Plus,
  Trash2
} from 'lucide-react'

interface CommitteeMember {
  id: string
  name: string
  designation: string
  role: string
}

interface CriterionCoordinator {
  criterion: number
  name: string
  designation: string
  department: string
}

interface IQACData {
  institution_name: string
  academic_year: string
  ref_no: string
  order_date: string
  tenure_years: number
  principal_name: string
  steering_committee: CommitteeMember[]
  iqac_members: CommitteeMember[]
  criterion_coordinators: CriterionCoordinator[]
  dept_coordinators: CommitteeMember[]
  documentation_team: CommitteeMember[]
}

const defaultData: IQACData = {
  institution_name: '',
  academic_year: '2024-25',
  ref_no: 'NAAC/2024/',
  order_date: new Date().toISOString().split('T')[0],
  tenure_years: 5,
  principal_name: '',
  steering_committee: [
    { id: '1', name: '', designation: 'Principal', role: 'Chairperson' },
    { id: '2', name: '', designation: 'Senior Faculty', role: 'Member' },
    { id: '3', name: '', designation: 'IQAC Coordinator', role: 'Member Secretary' },
  ],
  iqac_members: [
    { id: '1', name: '', designation: 'Principal', role: 'Chairperson' },
    { id: '2', name: '', designation: 'Senior Faculty', role: 'Member' },
    { id: '3', name: '', designation: 'Senior Faculty', role: 'Member' },
    { id: '4', name: '', designation: 'Administrative Officer', role: 'Member' },
    { id: '5', name: '', designation: 'Industry Expert', role: 'External Member' },
    { id: '6', name: '', designation: 'Alumni Representative', role: 'Member' },
    { id: '7', name: '', designation: 'Student Representative', role: 'Member' },
    { id: '8', name: '', designation: 'IQAC Coordinator', role: 'Member Secretary' },
  ],
  criterion_coordinators: [
    { criterion: 1, name: '', designation: '', department: '' },
    { criterion: 2, name: '', designation: '', department: '' },
    { criterion: 3, name: '', designation: '', department: '' },
    { criterion: 4, name: '', designation: '', department: '' },
    { criterion: 5, name: '', designation: '', department: '' },
    { criterion: 6, name: '', designation: '', department: '' },
    { criterion: 7, name: '', designation: '', department: '' },
  ],
  dept_coordinators: [],
  documentation_team: [],
}

const CRITERION_NAMES = [
  'Curricular Aspects',
  'Teaching-Learning & Evaluation',
  'Research, Innovations & Extension',
  'Infrastructure & Learning Resources',
  'Student Support & Progression',
  'Governance, Leadership & Management',
  'Institutional Values & Best Practices',
]

export default function IQACDocumentsPage() {
  const router = useRouter()
  const [data, setData] = useState<IQACData>(defaultData)
  const [activeSection, setActiveSection] = useState<string | null>('structure')
  const [saved, setSaved] = useState(false)
  const printRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Load saved institution profile
    const savedInstitution = localStorage.getItem('naac_institution_profile')
    if (savedInstitution) {
      const inst = JSON.parse(savedInstitution)
      setData(prev => ({
        ...prev,
        institution_name: inst.name || '',
        principal_name: inst.principal_name || '',
      }))
    }

    // Load saved IQAC data
    const savedIQAC = localStorage.getItem('naac_iqac_data')
    if (savedIQAC) {
      setData(JSON.parse(savedIQAC))
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('naac_iqac_data', JSON.stringify(data))
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handlePrint = (sectionId: string) => {
    const printContent = document.getElementById(sectionId)
    if (printContent) {
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>NAAC Document</title>
              <style>
                body { font-family: 'Times New Roman', serif; padding: 40px; line-height: 1.6; }
                h1, h2, h3 { text-align: center; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #000; padding: 8px; text-align: left; }
                th { background: #f0f0f0; }
                .signature { margin-top: 60px; text-align: right; }
                .header { text-align: center; margin-bottom: 30px; }
                .org-chart { font-family: monospace; white-space: pre; text-align: center; }
                @media print { body { padding: 20px; } }
              </style>
            </head>
            <body>${printContent.innerHTML}</body>
          </html>
        `)
        printWindow.document.close()
        printWindow.print()
      }
    }
  }

  const addMember = (list: 'steering_committee' | 'iqac_members' | 'dept_coordinators' | 'documentation_team') => {
    setData(prev => ({
      ...prev,
      [list]: [...prev[list], { id: Date.now().toString(), name: '', designation: '', role: 'Member' }]
    }))
  }

  const removeMember = (list: 'steering_committee' | 'iqac_members' | 'dept_coordinators' | 'documentation_team', id: string) => {
    setData(prev => ({
      ...prev,
      [list]: prev[list].filter(m => m.id !== id)
    }))
  }

  const updateMember = (list: 'steering_committee' | 'iqac_members' | 'dept_coordinators' | 'documentation_team', id: string, field: string, value: string) => {
    setData(prev => ({
      ...prev,
      [list]: prev[list].map(m => m.id === id ? { ...m, [field]: value } : m)
    }))
  }

  const updateCriterionCoordinator = (criterion: number, field: string, value: string) => {
    setData(prev => ({
      ...prev,
      criterion_coordinators: prev.criterion_coordinators.map(c =>
        c.criterion === criterion ? { ...c, [field]: value } : c
      )
    }))
  }

  const Section = ({ id, title, icon: Icon, children }: { id: string, title: string, icon: React.ElementType, children: React.ReactNode }) => {
    const isOpen = activeSection === id
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-4">
        <button
          onClick={() => setActiveSection(isOpen ? null : id)}
          className="w-full flex items-center justify-between p-4 hover:bg-slate-800/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Icon className="w-5 h-5 text-orange-500" />
            <span className="font-semibold">{title}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); handlePrint(id); }}
              className="p-2 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white"
            >
              <Printer className="w-4 h-4" />
            </button>
            {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </button>
        {isOpen && (
          <div className="p-4 border-t border-slate-800">
            {children}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="max-w-5xl mx-auto">
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
              <h1 className="text-2xl font-bold">IQAC & Committee Documents</h1>
              <p className="text-slate-400">Generate official NAAC documents</p>
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
              onClick={handleSave}
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg"
            >
              <Save className="w-4 h-4" />
              Save All
            </button>
          </div>
        </div>

        {/* Basic Info */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
          <h3 className="font-semibold mb-4">Institution Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Institution Name</label>
              <input
                type="text"
                value={data.institution_name}
                onChange={e => setData({ ...data, institution_name: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Principal Name</label>
              <input
                type="text"
                value={data.principal_name}
                onChange={e => setData({ ...data, principal_name: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Academic Year</label>
              <input
                type="text"
                value={data.academic_year}
                onChange={e => setData({ ...data, academic_year: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
          </div>
        </div>

        {/* 1. Organizational Structure */}
        <Section id="structure" title="1. NAAC Organizational Structure Chart" icon={Building}>
          <div id="structure" className="bg-white text-black p-8 rounded-lg">
            <div className="header">
              <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px' }}>
                NAAC ACCREDITATION ORGANIZATIONAL STRUCTURE
              </h2>
              <h3 style={{ fontSize: '16px', marginBottom: '30px' }}>{data.institution_name || '[Institution Name]'}</h3>
            </div>

            <pre className="org-chart" style={{ fontSize: '14px', lineHeight: '1.4' }}>
{`                    Governing Body / Management
                              │
                              ▼
                     Head of Institution
                    (${data.principal_name || 'Principal / Director'})
                              │
                              ▼
               Internal Quality Assurance Cell (IQAC)
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
         IQAC            NAAC Steering    Documentation
      Coordinator         Committee        & Data Team
                              │
                              ▼
      ┌─────────────────────────────────────────────┐
      │       NAAC Criterion-wise Committees        │
      └─────────────────────────────────────────────┘
        │     │     │     │     │     │     │
        ▼     ▼     ▼     ▼     ▼     ▼     ▼
       C1    C2    C3    C4    C5    C6    C7
                              │
                              ▼
              Department NAAC Coordinators
                              │
                              ▼
           Faculty Members / Students / Alumni`}
            </pre>

            <div style={{ marginTop: '40px', fontSize: '12px', color: '#666' }}>
              <p><strong>📌 Use this chart in:</strong></p>
              <ul style={{ marginLeft: '20px' }}>
                <li>NAAC SSR</li>
                <li>IQAC files</li>
                <li>Peer Team Visit presentation</li>
              </ul>
            </div>
          </div>
        </Section>

        {/* 2. Committee Order */}
        <Section id="committee-order" title="2. NAAC Committee Order Template" icon={ClipboardList}>
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Reference No.</label>
              <input
                type="text"
                value={data.ref_no}
                onChange={e => setData({ ...data, ref_no: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Order Date</label>
              <input
                type="date"
                value={data.order_date}
                onChange={e => setData({ ...data, order_date: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
          </div>

          {/* Steering Committee Members Editor */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-slate-300">Steering Committee Members</h4>
              <button
                onClick={() => addMember('steering_committee')}
                className="flex items-center gap-1 text-sm text-orange-400 hover:text-orange-300"
              >
                <Plus className="w-4 h-4" /> Add Member
              </button>
            </div>
            <div className="space-y-2">
              {data.steering_committee.map((member, idx) => (
                <div key={member.id} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Name"
                    value={member.name}
                    onChange={e => updateMember('steering_committee', member.id, 'name', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Designation"
                    value={member.designation}
                    onChange={e => updateMember('steering_committee', member.id, 'designation', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Role"
                    value={member.role}
                    onChange={e => updateMember('steering_committee', member.id, 'role', e.target.value)}
                    className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  {idx > 2 && (
                    <button
                      onClick={() => removeMember('steering_committee', member.id)}
                      className="p-2 text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Criterion Coordinators Editor */}
          <div className="mb-6">
            <h4 className="font-medium text-slate-300 mb-3">Criterion Coordinators</h4>
            <div className="space-y-2">
              {data.criterion_coordinators.map((coord) => (
                <div key={coord.criterion} className="flex gap-2 items-center">
                  <span className="w-8 text-sm text-orange-400">C{coord.criterion}</span>
                  <input
                    type="text"
                    placeholder="Coordinator Name"
                    value={coord.name}
                    onChange={e => updateCriterionCoordinator(coord.criterion, 'name', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Designation"
                    value={coord.designation}
                    onChange={e => updateCriterionCoordinator(coord.criterion, 'designation', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Department"
                    value={coord.department}
                    onChange={e => updateCriterionCoordinator(coord.criterion, 'department', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Preview */}
          <div id="committee-order" className="bg-white text-black p-8 rounded-lg mt-4">
            <div className="header" style={{ textAlign: 'center', marginBottom: '30px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 'bold' }}>{data.institution_name || '[Institution Name]'}</h2>
              <h3 style={{ fontSize: '16px', marginTop: '10px' }}>OFFICE ORDER</h3>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
              <span>Ref No: {data.ref_no}</span>
              <span>Date: {data.order_date}</span>
            </div>

            <p><strong>Sub:</strong> Constitution of NAAC Committees – Reg.</p>

            <p style={{ marginTop: '15px', textAlign: 'justify' }}>
              In accordance with the guidelines of the National Assessment and Accreditation Council (NAAC),
              the following committees are hereby constituted to facilitate the NAAC accreditation process of the institution.
            </p>

            <h4 style={{ marginTop: '25px', fontWeight: 'bold' }}>1. NAAC Steering Committee</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr style={{ backgroundColor: '#f0f0f0' }}>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>S.No</th>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>Name</th>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>Designation</th>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>Role</th>
                </tr>
              </thead>
              <tbody>
                {data.steering_committee.map((member, idx) => (
                  <tr key={member.id}>
                    <td style={{ border: '1px solid #000', padding: '8px', textAlign: 'center' }}>{idx + 1}</td>
                    <td style={{ border: '1px solid #000', padding: '8px' }}>{member.name || '___________'}</td>
                    <td style={{ border: '1px solid #000', padding: '8px' }}>{member.designation}</td>
                    <td style={{ border: '1px solid #000', padding: '8px' }}>{member.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h4 style={{ marginTop: '25px', fontWeight: 'bold' }}>2. Criterion-wise Committees</h4>
            {data.criterion_coordinators.map((coord) => (
              <p key={coord.criterion} style={{ marginTop: '10px' }}>
                <strong>Criterion {coord.criterion} – {CRITERION_NAMES[coord.criterion - 1]}</strong><br />
                Coordinator: {coord.name || '___________'} ({coord.designation || 'Designation'})
              </p>
            ))}

            <p style={{ marginTop: '25px' }}>
              All the above committees shall function with immediate effect and submit periodical reports to IQAC.
            </p>

            <div className="signature" style={{ marginTop: '60px', textAlign: 'right' }}>
              <p>{data.principal_name || 'Principal'}</p>
              <p>(Name & Signature)</p>
              <p>Seal of the Institution</p>
            </div>
          </div>
        </Section>

        {/* 3. Role Allocation Circular */}
        <Section id="role-circular" title="3. Role Allocation Circular" icon={Users}>
          <div id="role-circular" className="bg-white text-black p-8 rounded-lg">
            <div className="header" style={{ textAlign: 'center', marginBottom: '30px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 'bold' }}>{data.institution_name || '[Institution Name]'}</h2>
              <h3 style={{ fontSize: '16px', marginTop: '10px' }}>CIRCULAR</h3>
            </div>

            <p><strong>Subject:</strong> Allocation of NAAC Roles & Responsibilities</p>

            <p style={{ marginTop: '15px' }}>
              This is to inform that the following roles and responsibilities are assigned for NAAC accreditation activities.
            </p>

            <h4 style={{ marginTop: '25px', fontWeight: 'bold' }}>IQAC Coordinator</h4>
            <ul style={{ marginLeft: '20px' }}>
              <li>Overall NAAC coordination</li>
              <li>SSR & AQAR preparation</li>
              <li>Liaison with NAAC</li>
            </ul>

            <h4 style={{ marginTop: '20px', fontWeight: 'bold' }}>Criterion Coordinators</h4>
            <ul style={{ marginLeft: '20px' }}>
              <li>Collection & validation of criterion-specific data</li>
              <li>Preparation of qualitative & quantitative metrics</li>
              <li>Evidence documentation</li>
            </ul>

            <h4 style={{ marginTop: '20px', fontWeight: 'bold' }}>Department NAAC Coordinators</h4>
            <ul style={{ marginLeft: '20px' }}>
              <li>Department-level data submission</li>
              <li>Faculty & student record maintenance</li>
              <li>Academic & result data</li>
            </ul>

            <h4 style={{ marginTop: '20px', fontWeight: 'bold' }}>Documentation Team</h4>
            <ul style={{ marginLeft: '20px' }}>
              <li>Digital evidence organization</li>
              <li>File naming & indexing</li>
              <li>Upload support</li>
            </ul>

            <p style={{ marginTop: '25px' }}>
              All concerned are requested to adhere strictly to timelines.
            </p>

            <div className="signature" style={{ marginTop: '60px', textAlign: 'right' }}>
              <p>{data.principal_name || 'Principal / Director'}</p>
            </div>
          </div>
        </Section>

        {/* 4. IQAC Formation Document */}
        <Section id="iqac-formation" title="4. IQAC Formation Document" icon={Shield}>
          {/* IQAC Members Editor */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium text-slate-300">IQAC Members</h4>
              <button
                onClick={() => addMember('iqac_members')}
                className="flex items-center gap-1 text-sm text-orange-400 hover:text-orange-300"
              >
                <Plus className="w-4 h-4" /> Add Member
              </button>
            </div>
            <div className="space-y-2">
              {data.iqac_members.map((member, idx) => (
                <div key={member.id} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Name"
                    value={member.name}
                    onChange={e => updateMember('iqac_members', member.id, 'name', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Designation"
                    value={member.designation}
                    onChange={e => updateMember('iqac_members', member.id, 'designation', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Role"
                    value={member.role}
                    onChange={e => updateMember('iqac_members', member.id, 'role', e.target.value)}
                    className="w-40 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                  />
                  {idx > 7 && (
                    <button
                      onClick={() => removeMember('iqac_members', member.id)}
                      className="p-2 text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm text-slate-400 mb-1">IQAC Tenure (Years)</label>
            <input
              type="number"
              value={data.tenure_years}
              onChange={e => setData({ ...data, tenure_years: parseInt(e.target.value) || 5 })}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2"
            />
          </div>

          {/* Preview */}
          <div id="iqac-formation" className="bg-white text-black p-8 rounded-lg mt-4">
            <div className="header" style={{ textAlign: 'center', marginBottom: '30px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 'bold' }}>INTERNAL QUALITY ASSURANCE CELL (IQAC)</h2>
            </div>

            <p><strong>Name of the Institution:</strong> {data.institution_name || '___________'}</p>
            <p><strong>Academic Year:</strong> {data.academic_year}</p>

            <h4 style={{ marginTop: '25px', fontWeight: 'bold' }}>Composition of IQAC</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
              <thead>
                <tr style={{ backgroundColor: '#f0f0f0' }}>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>S.No</th>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>Name</th>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>Designation</th>
                  <th style={{ border: '1px solid #000', padding: '8px' }}>Role</th>
                </tr>
              </thead>
              <tbody>
                {data.iqac_members.map((member, idx) => (
                  <tr key={member.id}>
                    <td style={{ border: '1px solid #000', padding: '8px', textAlign: 'center' }}>{idx + 1}</td>
                    <td style={{ border: '1px solid #000', padding: '8px' }}>{member.name || '___________'}</td>
                    <td style={{ border: '1px solid #000', padding: '8px' }}>{member.designation}</td>
                    <td style={{ border: '1px solid #000', padding: '8px' }}>{member.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h4 style={{ marginTop: '25px', fontWeight: 'bold' }}>Functions of IQAC</h4>
            <ul style={{ marginLeft: '20px' }}>
              <li>Develop quality benchmarks</li>
              <li>Facilitate learner-centric environment</li>
              <li>Organize academic audits</li>
              <li>Prepare AQAR</li>
              <li>Promote best practices</li>
            </ul>

            <h4 style={{ marginTop: '25px', fontWeight: 'bold' }}>Tenure</h4>
            <p>The IQAC shall function for a period of <strong>{data.tenure_years}</strong> years.</p>

            <div className="signature" style={{ marginTop: '60px', textAlign: 'right' }}>
              <p>Approved by:</p>
              <p>{data.principal_name || 'Principal / Director'}</p>
              <p>(Signature & Seal)</p>
            </div>
          </div>
        </Section>

        {/* Usage Note */}
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6 mt-6">
          <h3 className="font-semibold text-green-400 mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            How to Use These Documents
          </h3>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>✔ Upload during SSR submission</li>
            <li>✔ Display during Peer Team Visit</li>
            <li>✔ Maintain in IQAC file</li>
            <li>✔ Required for AQAR every year</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
