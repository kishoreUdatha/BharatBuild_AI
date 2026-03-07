'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  FileText,
  Download,
  Save,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Printer,
  Calendar,
  Building,
  Users,
  BookOpen,
  GraduationCap,
  FlaskConical,
  Shield,
  Heart,
  Target
} from 'lucide-react'

interface AQARData {
  // Part A
  institution_name: string
  academic_year: string
  naac_cycle: number
  aishe_code: string
  website_url: string
  accreditation_status: string

  // Part B - IQAC
  iqac_formation_date: string
  iqac_meetings: number
  aqar_preparation_date: string

  // Part C - Criteria
  criterion1: {
    new_courses: string
    value_added_programs: string
    curriculum_feedback: string
  }
  criterion2: {
    student_enrollment: string
    innovative_teaching: string
    ict_usage: string
  }
  criterion3: {
    publications: string
    projects: string
    extension_activities: string
  }
  criterion4: {
    new_infrastructure: string
    ict_facilities: string
    maintenance: string
  }
  criterion5: {
    scholarships: string
    placements: string
    alumni_activities: string
  }
  criterion6: {
    strategic_plans: string
    iqac_initiatives: string
    quality_improvements: string
  }
  criterion7: {
    best_practice_1_title: string
    best_practice_1_impact: string
    best_practice_2_title: string
    best_practice_2_impact: string
    institutional_distinctiveness: string
  }

  // Part D - Analysis
  strengths: string
  weaknesses: string
  opportunities: string
  threats: string
  challenges: string
  action_plan: string
}

const defaultAQAR: AQARData = {
  institution_name: '',
  academic_year: '2023-24',
  naac_cycle: 1,
  aishe_code: '',
  website_url: '',
  accreditation_status: 'Applying',
  iqac_formation_date: '',
  iqac_meetings: 4,
  aqar_preparation_date: new Date().toISOString().split('T')[0],
  criterion1: { new_courses: '', value_added_programs: '', curriculum_feedback: '' },
  criterion2: { student_enrollment: '', innovative_teaching: '', ict_usage: '' },
  criterion3: { publications: '', projects: '', extension_activities: '' },
  criterion4: { new_infrastructure: '', ict_facilities: '', maintenance: '' },
  criterion5: { scholarships: '', placements: '', alumni_activities: '' },
  criterion6: { strategic_plans: '', iqac_initiatives: '', quality_improvements: '' },
  criterion7: { best_practice_1_title: '', best_practice_1_impact: '', best_practice_2_title: '', best_practice_2_impact: '', institutional_distinctiveness: '' },
  strengths: '',
  weaknesses: '',
  opportunities: '',
  threats: '',
  challenges: '',
  action_plan: '',
}

export default function AQARPage() {
  const router = useRouter()
  const [data, setData] = useState<AQARData>(defaultAQAR)
  const [activeSection, setActiveSection] = useState<string>('partA')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    // Load institution profile
    const savedInstitution = localStorage.getItem('naac_institution_profile')
    if (savedInstitution) {
      const inst = JSON.parse(savedInstitution)
      setData(prev => ({
        ...prev,
        institution_name: inst.name || '',
        website_url: inst.website || '',
        naac_cycle: inst.naac_cycle || 1,
      }))
    }

    // Load saved AQAR
    const savedAQAR = localStorage.getItem('naac_aqar_data')
    if (savedAQAR) {
      setData(JSON.parse(savedAQAR))
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('naac_aqar_data', JSON.stringify(data))
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handlePrint = () => {
    const printContent = document.getElementById('aqar-document')
    if (printContent) {
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(`
          <html>
            <head>
              <title>AQAR ${data.academic_year}</title>
              <style>
                body { font-family: 'Times New Roman', serif; padding: 40px; line-height: 1.8; }
                h1, h2, h3 { text-align: center; margin-top: 30px; }
                h1 { font-size: 20px; }
                h2 { font-size: 16px; background: #f0f0f0; padding: 10px; }
                h3 { font-size: 14px; text-align: left; }
                table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                th, td { border: 1px solid #000; padding: 8px; text-align: left; }
                th { background: #f0f0f0; }
                .section { margin: 20px 0; page-break-inside: avoid; }
                .field { margin: 10px 0; }
                .label { font-weight: bold; }
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

  const Section = ({ id, title, icon: Icon, children }: { id: string; title: string; icon: React.ElementType; children: React.ReactNode }) => {
    const isOpen = activeSection === id
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-4">
        <button
          onClick={() => setActiveSection(isOpen ? '' : id)}
          className="w-full flex items-center justify-between p-4 hover:bg-slate-800/50"
        >
          <div className="flex items-center gap-3">
            <Icon className="w-5 h-5 text-orange-500" />
            <span className="font-semibold">{title}</span>
          </div>
          {isOpen ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        {isOpen && <div className="p-4 border-t border-slate-800">{children}</div>}
      </div>
    )
  }

  const Field = ({ label, value, onChange, type = 'text', rows = 3 }: { label: string; value: string; onChange: (v: string) => void; type?: string; rows?: number }) => (
    <div className="mb-4">
      <label className="block text-sm text-slate-400 mb-1">{label}</label>
      {type === 'textarea' ? (
        <textarea
          value={value}
          onChange={e => onChange(e.target.value)}
          rows={rows}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
        />
      ) : (
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
        />
      )}
    </div>
  )

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button onClick={() => router.back()} className="p-2 hover:bg-slate-800 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">AQAR Generator</h1>
              <p className="text-slate-400">Annual Quality Assurance Report</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {saved && (
              <span className="flex items-center gap-2 text-green-400 text-sm">
                <CheckCircle2 className="w-4 h-4" /> Saved
              </span>
            )}
            <button onClick={handlePrint} className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg">
              <Printer className="w-4 h-4" /> Print
            </button>
            <button onClick={handleSave} className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg">
              <Save className="w-4 h-4" /> Save
            </button>
          </div>
        </div>

        {/* Year Selector */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Calendar className="w-5 h-5 text-orange-500" />
            <span>Academic Year:</span>
            <select
              value={data.academic_year}
              onChange={e => setData({ ...data, academic_year: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2"
            >
              <option value="2021-22">2021-22</option>
              <option value="2022-23">2022-23</option>
              <option value="2023-24">2023-24</option>
              <option value="2024-25">2024-25</option>
            </select>
          </div>
          <div className="text-sm text-slate-400">
            NAAC Cycle: {data.naac_cycle}
          </div>
        </div>

        {/* Part A - Institution */}
        <Section id="partA" title="Part A: Institutional Details" icon={Building}>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Institution Name" value={data.institution_name} onChange={v => setData({ ...data, institution_name: v })} />
            <Field label="AISHE Code" value={data.aishe_code} onChange={v => setData({ ...data, aishe_code: v })} />
            <Field label="Website URL" value={data.website_url} onChange={v => setData({ ...data, website_url: v })} />
            <div>
              <label className="block text-sm text-slate-400 mb-1">Accreditation Status</label>
              <select
                value={data.accreditation_status}
                onChange={e => setData({ ...data, accreditation_status: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2"
              >
                <option value="Applying">Applying for 1st Cycle</option>
                <option value="Accredited">Accredited</option>
                <option value="Reaccreditation">Applying for Reaccreditation</option>
              </select>
            </div>
          </div>
        </Section>

        {/* Part B - IQAC */}
        <Section id="partB" title="Part B: IQAC Details" icon={Shield}>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Date of IQAC Formation" type="date" value={data.iqac_formation_date} onChange={v => setData({ ...data, iqac_formation_date: v })} />
            <Field label="Number of IQAC Meetings" type="number" value={data.iqac_meetings.toString()} onChange={v => setData({ ...data, iqac_meetings: parseInt(v) || 0 })} />
            <Field label="AQAR Preparation Date" type="date" value={data.aqar_preparation_date} onChange={v => setData({ ...data, aqar_preparation_date: v })} />
          </div>
        </Section>

        {/* Criterion 1 */}
        <Section id="c1" title="Criterion I: Curricular Aspects" icon={BookOpen}>
          <Field label="New Courses Introduced" type="textarea" value={data.criterion1.new_courses} onChange={v => setData({ ...data, criterion1: { ...data.criterion1, new_courses: v } })} />
          <Field label="Value-Added Programs" type="textarea" value={data.criterion1.value_added_programs} onChange={v => setData({ ...data, criterion1: { ...data.criterion1, value_added_programs: v } })} />
          <Field label="Curriculum Feedback & Action Taken" type="textarea" value={data.criterion1.curriculum_feedback} onChange={v => setData({ ...data, criterion1: { ...data.criterion1, curriculum_feedback: v } })} />
        </Section>

        {/* Criterion 2 */}
        <Section id="c2" title="Criterion II: Teaching-Learning & Evaluation" icon={GraduationCap}>
          <Field label="Student Enrollment Details" type="textarea" value={data.criterion2.student_enrollment} onChange={v => setData({ ...data, criterion2: { ...data.criterion2, student_enrollment: v } })} />
          <Field label="Innovative Teaching Practices" type="textarea" value={data.criterion2.innovative_teaching} onChange={v => setData({ ...data, criterion2: { ...data.criterion2, innovative_teaching: v } })} />
          <Field label="ICT Usage in Teaching" type="textarea" value={data.criterion2.ict_usage} onChange={v => setData({ ...data, criterion2: { ...data.criterion2, ict_usage: v } })} />
        </Section>

        {/* Criterion 3 */}
        <Section id="c3" title="Criterion III: Research, Innovations & Extension" icon={FlaskConical}>
          <Field label="Publications" type="textarea" value={data.criterion3.publications} onChange={v => setData({ ...data, criterion3: { ...data.criterion3, publications: v } })} />
          <Field label="Research Projects" type="textarea" value={data.criterion3.projects} onChange={v => setData({ ...data, criterion3: { ...data.criterion3, projects: v } })} />
          <Field label="Extension Activities" type="textarea" value={data.criterion3.extension_activities} onChange={v => setData({ ...data, criterion3: { ...data.criterion3, extension_activities: v } })} />
        </Section>

        {/* Criterion 4 */}
        <Section id="c4" title="Criterion IV: Infrastructure & Learning Resources" icon={Building}>
          <Field label="New Infrastructure Added" type="textarea" value={data.criterion4.new_infrastructure} onChange={v => setData({ ...data, criterion4: { ...data.criterion4, new_infrastructure: v } })} />
          <Field label="ICT Facilities" type="textarea" value={data.criterion4.ict_facilities} onChange={v => setData({ ...data, criterion4: { ...data.criterion4, ict_facilities: v } })} />
          <Field label="Maintenance & Upgrades" type="textarea" value={data.criterion4.maintenance} onChange={v => setData({ ...data, criterion4: { ...data.criterion4, maintenance: v } })} />
        </Section>

        {/* Criterion 5 */}
        <Section id="c5" title="Criterion V: Student Support & Progression" icon={Users}>
          <Field label="Scholarships & Financial Support" type="textarea" value={data.criterion5.scholarships} onChange={v => setData({ ...data, criterion5: { ...data.criterion5, scholarships: v } })} />
          <Field label="Placements & Career Guidance" type="textarea" value={data.criterion5.placements} onChange={v => setData({ ...data, criterion5: { ...data.criterion5, placements: v } })} />
          <Field label="Alumni Engagement Activities" type="textarea" value={data.criterion5.alumni_activities} onChange={v => setData({ ...data, criterion5: { ...data.criterion5, alumni_activities: v } })} />
        </Section>

        {/* Criterion 6 */}
        <Section id="c6" title="Criterion VI: Governance, Leadership & Management" icon={Shield}>
          <Field label="Strategic Plans & Implementation" type="textarea" value={data.criterion6.strategic_plans} onChange={v => setData({ ...data, criterion6: { ...data.criterion6, strategic_plans: v } })} />
          <Field label="IQAC Initiatives" type="textarea" value={data.criterion6.iqac_initiatives} onChange={v => setData({ ...data, criterion6: { ...data.criterion6, iqac_initiatives: v } })} />
          <Field label="Quality Improvements" type="textarea" value={data.criterion6.quality_improvements} onChange={v => setData({ ...data, criterion6: { ...data.criterion6, quality_improvements: v } })} />
        </Section>

        {/* Criterion 7 */}
        <Section id="c7" title="Criterion VII: Institutional Values & Best Practices" icon={Heart}>
          <h4 className="font-medium text-slate-300 mb-3">Best Practice 1</h4>
          <Field label="Title" value={data.criterion7.best_practice_1_title} onChange={v => setData({ ...data, criterion7: { ...data.criterion7, best_practice_1_title: v } })} />
          <Field label="Impact" type="textarea" value={data.criterion7.best_practice_1_impact} onChange={v => setData({ ...data, criterion7: { ...data.criterion7, best_practice_1_impact: v } })} />

          <h4 className="font-medium text-slate-300 mb-3 mt-6">Best Practice 2</h4>
          <Field label="Title" value={data.criterion7.best_practice_2_title} onChange={v => setData({ ...data, criterion7: { ...data.criterion7, best_practice_2_title: v } })} />
          <Field label="Impact" type="textarea" value={data.criterion7.best_practice_2_impact} onChange={v => setData({ ...data, criterion7: { ...data.criterion7, best_practice_2_impact: v } })} />

          <h4 className="font-medium text-slate-300 mb-3 mt-6">Institutional Distinctiveness</h4>
          <Field label="Describe what makes your institution unique" type="textarea" rows={5} value={data.criterion7.institutional_distinctiveness} onChange={v => setData({ ...data, criterion7: { ...data.criterion7, institutional_distinctiveness: v } })} />
        </Section>

        {/* Part D - SWOT */}
        <Section id="partD" title="Part D: SWOT Analysis & Action Plan" icon={Target}>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Strengths" type="textarea" value={data.strengths} onChange={v => setData({ ...data, strengths: v })} />
            <Field label="Weaknesses" type="textarea" value={data.weaknesses} onChange={v => setData({ ...data, weaknesses: v })} />
            <Field label="Opportunities" type="textarea" value={data.opportunities} onChange={v => setData({ ...data, opportunities: v })} />
            <Field label="Threats" type="textarea" value={data.threats} onChange={v => setData({ ...data, threats: v })} />
          </div>
          <Field label="Challenges Faced" type="textarea" value={data.challenges} onChange={v => setData({ ...data, challenges: v })} />
          <Field label="Action Plan for Next Year" type="textarea" rows={5} value={data.action_plan} onChange={v => setData({ ...data, action_plan: v })} />
        </Section>

        {/* Hidden Print Document */}
        <div id="aqar-document" className="hidden">
          <h1>ANNUAL QUALITY ASSURANCE REPORT (AQAR)</h1>
          <h2>{data.institution_name}</h2>
          <h3>Academic Year: {data.academic_year}</h3>

          <div className="section">
            <h2>PART A: INSTITUTIONAL DETAILS</h2>
            <p><span className="label">Institution Name:</span> {data.institution_name}</p>
            <p><span className="label">AISHE Code:</span> {data.aishe_code}</p>
            <p><span className="label">Website:</span> {data.website_url}</p>
            <p><span className="label">NAAC Cycle:</span> {data.naac_cycle}</p>
            <p><span className="label">Accreditation Status:</span> {data.accreditation_status}</p>
          </div>

          <div className="section">
            <h2>PART B: IQAC DETAILS</h2>
            <p><span className="label">IQAC Formation Date:</span> {data.iqac_formation_date}</p>
            <p><span className="label">Number of IQAC Meetings:</span> {data.iqac_meetings}</p>
            <p><span className="label">AQAR Preparation Date:</span> {data.aqar_preparation_date}</p>
          </div>

          <div className="section">
            <h2>PART C: CRITERION-WISE DETAILS</h2>

            <h3>Criterion I – Curricular Aspects</h3>
            <p><span className="label">New Courses:</span> {data.criterion1.new_courses}</p>
            <p><span className="label">Value-Added Programs:</span> {data.criterion1.value_added_programs}</p>
            <p><span className="label">Curriculum Feedback:</span> {data.criterion1.curriculum_feedback}</p>

            <h3>Criterion II – Teaching-Learning</h3>
            <p><span className="label">Student Enrollment:</span> {data.criterion2.student_enrollment}</p>
            <p><span className="label">Innovative Teaching:</span> {data.criterion2.innovative_teaching}</p>
            <p><span className="label">ICT Usage:</span> {data.criterion2.ict_usage}</p>

            <h3>Criterion III – Research & Extension</h3>
            <p><span className="label">Publications:</span> {data.criterion3.publications}</p>
            <p><span className="label">Projects:</span> {data.criterion3.projects}</p>
            <p><span className="label">Extension Activities:</span> {data.criterion3.extension_activities}</p>

            <h3>Criterion IV – Infrastructure</h3>
            <p><span className="label">New Infrastructure:</span> {data.criterion4.new_infrastructure}</p>
            <p><span className="label">ICT Facilities:</span> {data.criterion4.ict_facilities}</p>

            <h3>Criterion V – Student Support</h3>
            <p><span className="label">Scholarships:</span> {data.criterion5.scholarships}</p>
            <p><span className="label">Placements:</span> {data.criterion5.placements}</p>
            <p><span className="label">Alumni Activities:</span> {data.criterion5.alumni_activities}</p>

            <h3>Criterion VI – Governance</h3>
            <p><span className="label">Strategic Plans:</span> {data.criterion6.strategic_plans}</p>
            <p><span className="label">IQAC Initiatives:</span> {data.criterion6.iqac_initiatives}</p>

            <h3>Criterion VII – Best Practices</h3>
            <p><span className="label">Best Practice 1:</span> {data.criterion7.best_practice_1_title}</p>
            <p>{data.criterion7.best_practice_1_impact}</p>
            <p><span className="label">Best Practice 2:</span> {data.criterion7.best_practice_2_title}</p>
            <p>{data.criterion7.best_practice_2_impact}</p>
            <p><span className="label">Institutional Distinctiveness:</span> {data.criterion7.institutional_distinctiveness}</p>
          </div>

          <div className="section">
            <h2>PART D: SWOT ANALYSIS</h2>
            <p><span className="label">Strengths:</span> {data.strengths}</p>
            <p><span className="label">Weaknesses:</span> {data.weaknesses}</p>
            <p><span className="label">Opportunities:</span> {data.opportunities}</p>
            <p><span className="label">Threats:</span> {data.threats}</p>
            <p><span className="label">Challenges:</span> {data.challenges}</p>
            <p><span className="label">Action Plan:</span> {data.action_plan}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
