'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Building,
  Save,
  ArrowLeft,
  MapPin,
  User,
  Globe,
  Mail,
  Phone,
  CheckCircle2,
  Award,
  TrendingUp,
  Calendar,
  Shield,
  Info
} from 'lucide-react'

// Binary Accreditation Status (NAAC 2025)
type BinaryStatus = 'not_applied' | 'applied' | 'under_review' | 'accredited' | 'not_accredited' | 'expired'

// MBGL Levels (NAAC 2025)
type MBGLLevel = 'not_assessed' | 'level_1' | 'level_2' | 'level_3' | 'level_4' | 'level_5'

interface InstitutionProfile {
  name: string
  type: 'University' | 'Autonomous' | 'Affiliated'
  location: string
  state: string
  established_year: number
  naac_cycle: number
  previous_grade: string
  affiliated_university: string
  programs_offered: string[]
  total_students: number
  total_faculty: number
  website: string
  email: string
  phone: string
  iqac_coordinator: string
  principal_name: string
  // NAAC 2025 Framework
  framework_type: 'old_raf' | 'new_binary_mbgl'
  binary_status: BinaryStatus
  binary_accreditation_date: string
  binary_validity_end: string
  mbgl_level: MBGLLevel
  mbgl_assessment_date: string
  mbgl_score: number
  validity_years: number
}

const defaultProfile: InstitutionProfile = {
  name: '',
  type: 'Affiliated',
  location: '',
  state: '',
  established_year: 2000,
  naac_cycle: 1,
  previous_grade: '',
  affiliated_university: '',
  programs_offered: [],
  total_students: 0,
  total_faculty: 0,
  website: '',
  email: '',
  phone: '',
  iqac_coordinator: '',
  principal_name: '',
  // NAAC 2025 Framework
  framework_type: 'new_binary_mbgl',
  binary_status: 'not_applied',
  binary_accreditation_date: '',
  binary_validity_end: '',
  mbgl_level: 'not_assessed',
  mbgl_assessment_date: '',
  mbgl_score: 0,
  validity_years: 3
}

const BINARY_STATUS_OPTIONS = [
  { value: 'not_applied', label: 'Not Applied', color: 'gray' },
  { value: 'applied', label: 'Applied', color: 'blue' },
  { value: 'under_review', label: 'Under Review', color: 'yellow' },
  { value: 'accredited', label: 'Accredited', color: 'green' },
  { value: 'not_accredited', label: 'Not Accredited', color: 'red' },
  { value: 'expired', label: 'Expired', color: 'orange' }
]

const MBGL_LEVELS = [
  { value: 'not_assessed', label: 'Not Assessed', number: 0, color: 'gray', description: 'MBGL assessment not yet completed' },
  { value: 'level_1', label: 'Level 1 - Basic Compliance', number: 1, color: 'red', description: 'Meets basic accreditation requirements' },
  { value: 'level_2', label: 'Level 2 - Developing', number: 2, color: 'orange', description: 'Shows developing quality practices' },
  { value: 'level_3', label: 'Level 3 - Established', number: 3, color: 'yellow', description: 'Has established quality systems' },
  { value: 'level_4', label: 'Level 4 - Advanced', number: 4, color: 'blue', description: 'Demonstrates advanced quality practices' },
  { value: 'level_5', label: 'Level 5 - Excellence', number: 5, color: 'green', description: 'Achieves excellence in all dimensions' }
]

export default function SettingsPage() {
  const router = useRouter()
  const [institution, setInstitution] = useState<InstitutionProfile>(defaultProfile)
  const [saved, setSaved] = useState(false)
  const [activeTab, setActiveTab] = useState<'basic' | 'naac' | 'framework'>('basic')

  useEffect(() => {
    const savedInstitution = localStorage.getItem('naac_institution_profile')
    if (savedInstitution) {
      const parsed = JSON.parse(savedInstitution)
      setInstitution({ ...defaultProfile, ...parsed })
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('naac_institution_profile', JSON.stringify(institution))
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleReset = () => {
    if (confirm('Are you sure you want to reset all settings?')) {
      localStorage.removeItem('naac_institution_profile')
      setInstitution(defaultProfile)
    }
  }

  const getBinaryStatusColor = (status: BinaryStatus) => {
    const option = BINARY_STATUS_OPTIONS.find(o => o.value === status)
    const colorMap: Record<string, string> = {
      gray: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      green: 'bg-green-500/20 text-green-400 border-green-500/30',
      red: 'bg-red-500/20 text-red-400 border-red-500/30',
      orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30'
    }
    return colorMap[option?.color || 'gray']
  }

  const getMBGLColor = (level: MBGLLevel) => {
    const option = MBGL_LEVELS.find(o => o.value === level)
    const colorMap: Record<string, string> = {
      gray: 'bg-slate-500',
      red: 'bg-red-500',
      orange: 'bg-orange-500',
      yellow: 'bg-yellow-500',
      blue: 'bg-blue-500',
      green: 'bg-green-500'
    }
    return colorMap[option?.color || 'gray']
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
              <h1 className="text-2xl font-bold">Institution Settings</h1>
              <p className="text-slate-400">Configure your institution profile for NAAC 2025</p>
            </div>
          </div>
          {saved && (
            <div className="flex items-center gap-2 text-green-400 bg-green-500/20 px-4 py-2 rounded-lg">
              <CheckCircle2 className="w-4 h-4" />
              Saved successfully
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('basic')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'basic'
                ? 'bg-orange-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Building className="w-4 h-4 inline mr-2" />
            Basic Info
          </button>
          <button
            onClick={() => setActiveTab('naac')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'naac'
                ? 'bg-orange-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Award className="w-4 h-4 inline mr-2" />
            NAAC Details
          </button>
          <button
            onClick={() => setActiveTab('framework')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'framework'
                ? 'bg-orange-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <TrendingUp className="w-4 h-4 inline mr-2" />
            Binary + MBGL (2025)
          </button>
        </div>

        {/* Content */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          {activeTab === 'basic' && (
            <>
              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-800">
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <Building className="w-6 h-6 text-orange-500" />
                </div>
                <div>
                  <h2 className="font-semibold">Institution Profile</h2>
                  <p className="text-sm text-slate-400">Basic information for SSR generation</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Basic Info */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Institution Name *</label>
                    <input
                      type="text"
                      value={institution.name}
                      onChange={e => setInstitution({ ...institution, name: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      placeholder="e.g., ABC College of Engineering"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Type *</label>
                      <select
                        value={institution.type}
                        onChange={e => setInstitution({ ...institution, type: e.target.value as any })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      >
                        <option value="University">University</option>
                        <option value="Autonomous">Autonomous College</option>
                        <option value="Affiliated">Affiliated College</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Established Year</label>
                      <input
                        type="number"
                        value={institution.established_year}
                        onChange={e => setInstitution({ ...institution, established_year: parseInt(e.target.value) })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Location *</label>
                      <div className="relative">
                        <MapPin className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                        <input
                          type="text"
                          value={institution.location}
                          onChange={e => setInstitution({ ...institution, location: e.target.value })}
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-orange-500"
                          placeholder="City"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">State *</label>
                      <input
                        type="text"
                        value={institution.state}
                        onChange={e => setInstitution({ ...institution, state: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="State"
                      />
                    </div>
                  </div>

                  {institution.type === 'Affiliated' && (
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Affiliated to University</label>
                      <input
                        type="text"
                        value={institution.affiliated_university}
                        onChange={e => setInstitution({ ...institution, affiliated_university: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="e.g., JNTU Hyderabad"
                      />
                    </div>
                  )}
                </div>

                {/* Contact Info */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Principal Name</label>
                    <div className="relative">
                      <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                      <input
                        type="text"
                        value={institution.principal_name}
                        onChange={e => setInstitution({ ...institution, principal_name: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="Dr. Name"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Website</label>
                    <div className="relative">
                      <Globe className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                      <input
                        type="url"
                        value={institution.website}
                        onChange={e => setInstitution({ ...institution, website: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="https://www.college.edu"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Email</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                      <input
                        type="email"
                        value={institution.email}
                        onChange={e => setInstitution({ ...institution, email: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="iqac@college.edu"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Phone</label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                      <input
                        type="tel"
                        value={institution.phone}
                        onChange={e => setInstitution({ ...institution, phone: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="+91 XXXXX XXXXX"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Programs */}
              <div className="mt-6 pt-6 border-t border-slate-800">
                <label className="block text-sm text-slate-400 mb-1">Programs Offered (comma separated)</label>
                <textarea
                  value={institution.programs_offered.join(', ')}
                  onChange={e => setInstitution({
                    ...institution,
                    programs_offered: e.target.value.split(',').map(p => p.trim()).filter(p => p)
                  })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500 h-24"
                  placeholder="B.Tech, M.Tech, MBA, MCA..."
                />
              </div>
            </>
          )}

          {activeTab === 'naac' && (
            <>
              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-800">
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <Award className="w-6 h-6 text-orange-500" />
                </div>
                <div>
                  <h2 className="font-semibold">NAAC Information</h2>
                  <p className="text-sm text-slate-400">Accreditation cycle and IQAC details</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">NAAC Cycle</label>
                      <select
                        value={institution.naac_cycle}
                        onChange={e => setInstitution({ ...institution, naac_cycle: parseInt(e.target.value) })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      >
                        <option value={1}>1st Cycle (First time)</option>
                        <option value={2}>2nd Cycle (Re-accreditation)</option>
                        <option value={3}>3rd Cycle</option>
                        <option value={4}>4th Cycle</option>
                        <option value={5}>5th+ Cycle</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Previous Grade (Old RAF)</label>
                      <select
                        value={institution.previous_grade}
                        onChange={e => setInstitution({ ...institution, previous_grade: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      >
                        <option value="">N/A (First Cycle)</option>
                        <option value="A++">A++ (3.51-4.00)</option>
                        <option value="A+">A+ (3.26-3.50)</option>
                        <option value="A">A (3.01-3.25)</option>
                        <option value="B++">B++ (2.76-3.00)</option>
                        <option value="B+">B+ (2.51-2.75)</option>
                        <option value="B">B (2.01-2.50)</option>
                        <option value="C">C (1.51-2.00)</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Total Students</label>
                      <input
                        type="number"
                        value={institution.total_students}
                        onChange={e => setInstitution({ ...institution, total_students: parseInt(e.target.value) || 0 })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Total Faculty</label>
                      <input
                        type="number"
                        value={institution.total_faculty}
                        onChange={e => setInstitution({ ...institution, total_faculty: parseInt(e.target.value) || 0 })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">IQAC Coordinator</label>
                    <input
                      type="text"
                      value={institution.iqac_coordinator}
                      onChange={e => setInstitution({ ...institution, iqac_coordinator: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      placeholder="Dr. Name"
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Accreditation Framework</label>
                    <select
                      value={institution.framework_type}
                      onChange={e => setInstitution({ ...institution, framework_type: e.target.value as any })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    >
                      <option value="old_raf">Old RAF (CGPA-based: A++ to C)</option>
                      <option value="new_binary_mbgl">New Binary + MBGL (2025)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Validity Period</label>
                    <select
                      value={institution.validity_years}
                      onChange={e => setInstitution({ ...institution, validity_years: parseInt(e.target.value) })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    >
                      <option value={3}>3 Years (New Framework)</option>
                      <option value={5}>5 Years (Old RAF)</option>
                    </select>
                  </div>

                  {/* Info Box */}
                  <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-blue-300">
                        <p className="font-medium mb-1">NAAC 2025 Framework Changes:</p>
                        <ul className="list-disc list-inside text-blue-400 space-y-1">
                          <li>Binary Accreditation (Accredited/Not Accredited)</li>
                          <li>MBGL Levels 1-5 for quality grading</li>
                          <li>3-year validity (reduced from 5)</li>
                          <li>10 Attributes (expanded from 7 criteria)</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'framework' && (
            <>
              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-800">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-green-500" />
                </div>
                <div>
                  <h2 className="font-semibold">Binary Accreditation + MBGL (NAAC 2025)</h2>
                  <p className="text-sm text-slate-400">New accreditation framework effective from 2025</p>
                </div>
              </div>

              {/* Binary Accreditation Section */}
              <div className="mb-8">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" />
                  Binary Accreditation Status
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Current Status</label>
                    <select
                      value={institution.binary_status}
                      onChange={e => setInstitution({ ...institution, binary_status: e.target.value as BinaryStatus })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    >
                      {BINARY_STATUS_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Accreditation Date</label>
                    <input
                      type="date"
                      value={institution.binary_accreditation_date}
                      onChange={e => setInstitution({ ...institution, binary_accreditation_date: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Validity End Date</label>
                    <input
                      type="date"
                      value={institution.binary_validity_end}
                      onChange={e => setInstitution({ ...institution, binary_validity_end: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    />
                  </div>
                </div>

                {/* Binary Status Display */}
                <div className={`p-4 rounded-lg border ${getBinaryStatusColor(institution.binary_status)}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-lg">
                        {BINARY_STATUS_OPTIONS.find(o => o.value === institution.binary_status)?.label}
                      </p>
                      <p className="text-sm opacity-80">
                        {institution.binary_status === 'accredited'
                          ? 'Institution meets NAAC quality standards'
                          : institution.binary_status === 'not_accredited'
                            ? 'Institution does not meet minimum requirements'
                            : 'Binary accreditation status'}
                      </p>
                    </div>
                    {institution.binary_status === 'accredited' && (
                      <CheckCircle2 className="w-10 h-10 opacity-50" />
                    )}
                  </div>
                </div>
              </div>

              {/* MBGL Section */}
              <div>
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  MBGL - Maturity-Based Graded Levels
                </h3>

                {institution.binary_status !== 'accredited' && (
                  <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg mb-4">
                    <p className="text-yellow-400 text-sm">
                      MBGL assessment is only available for institutions with Binary Accreditation status of "Accredited".
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Current MBGL Level</label>
                    <select
                      value={institution.mbgl_level}
                      onChange={e => setInstitution({ ...institution, mbgl_level: e.target.value as MBGLLevel })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      disabled={institution.binary_status !== 'accredited'}
                    >
                      {MBGL_LEVELS.map(level => (
                        <option key={level.value} value={level.value}>{level.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">MBGL Assessment Date</label>
                    <input
                      type="date"
                      value={institution.mbgl_assessment_date}
                      onChange={e => setInstitution({ ...institution, mbgl_assessment_date: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      disabled={institution.binary_status !== 'accredited'}
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">MBGL Score (0-100)</label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={institution.mbgl_score}
                      onChange={e => setInstitution({ ...institution, mbgl_score: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      disabled={institution.binary_status !== 'accredited'}
                    />
                  </div>
                </div>

                {/* MBGL Levels Visual */}
                <div className="grid grid-cols-5 gap-2 mb-6">
                  {MBGL_LEVELS.filter(l => l.number > 0).map(level => {
                    const isActive = institution.mbgl_level === level.value
                    const isAchieved = MBGL_LEVELS.findIndex(l => l.value === institution.mbgl_level) >= MBGL_LEVELS.findIndex(l => l.value === level.value) && institution.mbgl_level !== 'not_assessed'
                    return (
                      <div
                        key={level.value}
                        className={`p-3 rounded-lg text-center border-2 transition-all ${
                          isActive
                            ? `${getMBGLColor(level.value as MBGLLevel)} text-white border-transparent`
                            : isAchieved
                              ? `${getMBGLColor(level.value as MBGLLevel)}/20 border-${level.color}-500/50`
                              : 'bg-slate-800 border-slate-700 text-slate-500'
                        }`}
                      >
                        <div className="text-2xl font-bold">{level.number}</div>
                        <div className="text-xs mt-1">{level.label.split(' - ')[1] || level.label}</div>
                      </div>
                    )
                  })}
                </div>

                {/* Level Description */}
                {institution.mbgl_level !== 'not_assessed' && (
                  <div className={`p-4 rounded-lg ${getMBGLColor(institution.mbgl_level)}/20 border border-${MBGL_LEVELS.find(l => l.value === institution.mbgl_level)?.color}-500/30`}>
                    <p className="font-semibold">
                      {MBGL_LEVELS.find(l => l.value === institution.mbgl_level)?.label}
                    </p>
                    <p className="text-sm text-slate-400 mt-1">
                      {MBGL_LEVELS.find(l => l.value === institution.mbgl_level)?.description}
                    </p>
                  </div>
                )}

                {/* Quick Link to MBGL Assessment */}
                <div className="mt-6 pt-6 border-t border-slate-800">
                  <a
                    href="/admin/accreditation/mbgl"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg transition-colors"
                  >
                    <TrendingUp className="w-4 h-4" />
                    Go to MBGL Assessment Dashboard
                  </a>
                </div>
              </div>
            </>
          )}

          <div className="mt-6 pt-6 border-t border-slate-800 flex justify-end gap-3">
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
            >
              Reset
            </button>
            <button
              onClick={handleSave}
              className="px-6 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              Save Profile
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
