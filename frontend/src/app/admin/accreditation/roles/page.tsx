'use client'

import Link from 'next/link'
import {
  ChevronRight,
  Crown,
  Shield,
  Target,
  BookOpen,
  GraduationCap,
  FlaskConical,
  Building,
  Users,
  Settings,
  Heart,
  UserCheck,
  FileText,
  BarChart3,
  ClipboardCheck,
  UserPlus,
  Briefcase,
  Database,
  Monitor
} from 'lucide-react'
import AccreditationNav from '@/components/AccreditationNav'

interface Role {
  title: string
  icon: React.ElementType
  color: string
  description?: string
  responsibilities: string[]
  members?: string[]
}

const LEADERSHIP_ROLES: Role[] = [
  {
    title: 'Head of Institution (Principal / Director)',
    icon: Crown,
    color: 'yellow',
    responsibilities: [
      'Overall NAAC strategy & leadership',
      'Approves policies & budget for accreditation',
      'Reviews AQAR & SSR before submission',
      'Chairs key quality meetings'
    ]
  },
  {
    title: 'IQAC Coordinator',
    icon: Target,
    color: 'red',
    description: 'Most Critical Role',
    responsibilities: [
      'Leads NAAC preparation',
      'Coordinates all 7 criteria teams',
      'Ensures documentation & data accuracy',
      'Prepares AQAR (Annual Quality Assurance Report)',
      'Organizes internal audits'
    ]
  }
]

const IQAC_COMPOSITION: string[] = [
  'Chairperson (Principal)',
  'IQAC Coordinator',
  'Senior faculty members',
  'Administrative officer',
  'Industry representative',
  'Alumni representative',
  'Student representative'
]

const CRITERION_COORDINATORS: Role[] = [
  {
    title: 'Criterion 1 Coordinator',
    icon: BookOpen,
    color: 'orange',
    description: 'Curricular Aspects',
    responsibilities: [
      'CO-PO mapping',
      'Curriculum feedback',
      'Value-added courses',
      'Internship records'
    ]
  },
  {
    title: 'Criterion 2 Coordinator',
    icon: GraduationCap,
    color: 'blue',
    description: 'Teaching-Learning & Evaluation',
    responsibilities: [
      'Lesson plans',
      'ICT tools usage',
      'Student performance tracking',
      'Rubrics & evaluation records'
    ]
  },
  {
    title: 'Criterion 3 Coordinator',
    icon: FlaskConical,
    color: 'purple',
    description: 'Research & Innovation',
    responsibilities: [
      'Publications & patents',
      'Research funding records',
      'Innovation cell documentation',
      'Extension activities'
    ]
  },
  {
    title: 'Criterion 4 Coordinator',
    icon: Building,
    color: 'green',
    description: 'Infrastructure',
    responsibilities: [
      'Lab records',
      'Software licenses',
      'Library usage',
      'Maintenance logs'
    ]
  },
  {
    title: 'Criterion 5 Coordinator',
    icon: Users,
    color: 'pink',
    description: 'Student Support',
    responsibilities: [
      'Placement data',
      'Alumni records',
      'Mentoring system',
      'Scholarship data'
    ]
  },
  {
    title: 'Criterion 6 Coordinator',
    icon: Settings,
    color: 'cyan',
    description: 'Governance',
    responsibilities: [
      'Policy documentation',
      'Strategic plans',
      'IQAC meeting minutes',
      'Financial audits'
    ]
  },
  {
    title: 'Criterion 7 Coordinator',
    icon: Heart,
    color: 'red',
    description: 'Institutional Values',
    responsibilities: [
      'Green campus initiatives',
      'Gender equity programs',
      'Best practices documentation',
      'Code of conduct'
    ]
  }
]

const SUPPORT_ROLES: Role[] = [
  {
    title: 'Department NAAC Coordinators',
    icon: UserCheck,
    color: 'indigo',
    description: 'Each Department',
    responsibilities: [
      'Maintain department-level data',
      'Collect results, projects, faculty data, lab records',
      'Submit to IQAC'
    ]
  },
  {
    title: 'Documentation & Data Team',
    icon: FileText,
    color: 'slate',
    responsibilities: [
      'Organize digital evidence',
      'Maintain Google Drive / ERP records',
      'Prepare SSR file formats',
      'Scan & index documents'
    ]
  },
  {
    title: 'IT / Data Analytics Team',
    icon: BarChart3,
    color: 'emerald',
    responsibilities: [
      'Provide LMS data',
      'Attendance & result analytics',
      'Dashboard reports',
      'Website updates for NAAC compliance'
    ]
  },
  {
    title: 'SSR Drafting Committee',
    icon: ClipboardCheck,
    color: 'amber',
    responsibilities: [
      'Write Self Study Report (SSR)',
      'Ensure data consistency',
      'Cross-check metrics',
      'Upload to NAAC portal'
    ]
  },
  {
    title: 'Student Representatives',
    icon: GraduationCap,
    color: 'violet',
    responsibilities: [
      'Provide feedback',
      'Participate in IQAC meetings',
      'Support peer team visit'
    ]
  },
  {
    title: 'Administrative Officer',
    icon: Database,
    color: 'stone',
    responsibilities: [
      'HR data',
      'Salary records',
      'Finance & audit documentation'
    ]
  },
  {
    title: 'Alumni Coordinator',
    icon: UserPlus,
    color: 'teal',
    responsibilities: [
      'Maintain alumni database',
      'Conduct alumni meetings',
      'Track alumni achievements'
    ]
  },
  {
    title: 'Placement Officer',
    icon: Briefcase,
    color: 'rose',
    responsibilities: [
      'Placement statistics',
      'Internship data',
      'Employer feedback'
    ]
  }
]

const colorClasses: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  yellow: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: 'text-yellow-500' },
  red: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', icon: 'text-red-500' },
  orange: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', icon: 'text-orange-500' },
  blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: 'text-blue-500' },
  purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-400', icon: 'text-purple-500' },
  green: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', icon: 'text-green-500' },
  pink: { bg: 'bg-pink-500/10', border: 'border-pink-500/30', text: 'text-pink-400', icon: 'text-pink-500' },
  cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', text: 'text-cyan-400', icon: 'text-cyan-500' },
  indigo: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', text: 'text-indigo-400', icon: 'text-indigo-500' },
  slate: { bg: 'bg-slate-500/10', border: 'border-slate-500/30', text: 'text-slate-400', icon: 'text-slate-500' },
  emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', icon: 'text-emerald-500' },
  amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', icon: 'text-amber-500' },
  violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/30', text: 'text-violet-400', icon: 'text-violet-500' },
  stone: { bg: 'bg-stone-500/10', border: 'border-stone-500/30', text: 'text-stone-400', icon: 'text-stone-500' },
  teal: { bg: 'bg-teal-500/10', border: 'border-teal-500/30', text: 'text-teal-400', icon: 'text-teal-500' },
  rose: { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', icon: 'text-rose-500' },
}

function RoleCard({ role }: { role: Role }) {
  const colors = colorClasses[role.color] || colorClasses.slate
  const Icon = role.icon

  return (
    <div className={`${colors.bg} border ${colors.border} rounded-xl p-5`}>
      <div className="flex items-start gap-3 mb-4">
        <div className={`p-2 rounded-lg ${colors.bg}`}>
          <Icon className={`w-6 h-6 ${colors.icon}`} />
        </div>
        <div>
          <h3 className="font-semibold text-white">{role.title}</h3>
          {role.description && (
            <p className={`text-sm ${colors.text}`}>{role.description}</p>
          )}
        </div>
      </div>
      <ul className="space-y-2">
        {role.responsibilities.map((resp, idx) => (
          <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
            <span className={`mt-1.5 w-1.5 h-1.5 rounded-full ${colors.icon} flex-shrink-0`} />
            {resp}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function RolesPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Navigation */}
      <AccreditationNav />

      {/* Header */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                <Link href="/admin/accreditation" className="hover:text-white">Accreditation</Link>
                <ChevronRight className="w-4 h-4" />
                <span className="text-white">Roles & Responsibilities</span>
              </div>
              <h1 className="text-2xl font-bold">NAAC Roles & Responsibilities</h1>
              <p className="text-slate-400 mt-1">Complete organizational structure for NAAC accreditation</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Leadership Section */}
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <Crown className="w-6 h-6 text-yellow-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Leadership</h2>
              <p className="text-slate-400 text-sm">Key decision makers for NAAC accreditation</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {LEADERSHIP_ROLES.map((role, idx) => (
              <RoleCard key={idx} role={role} />
            ))}
          </div>
        </section>

        {/* IQAC Composition */}
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Shield className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold">IQAC (Internal Quality Assurance Cell)</h2>
              <p className="text-slate-400 text-sm">IQAC is mandatory for NAAC accreditation</p>
            </div>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-6">
            <h3 className="font-semibold text-white mb-4">IQAC Composition</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {IQAC_COMPOSITION.map((member, idx) => (
                <div key={idx} className="flex items-center gap-2 text-sm text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                  {member}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Criterion Coordinators */}
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Target className="w-6 h-6 text-purple-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Criterion-Wise Coordinators</h2>
              <p className="text-slate-400 text-sm">Each NAAC criterion must have a dedicated coordinator</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {CRITERION_COORDINATORS.map((role, idx) => (
              <RoleCard key={idx} role={role} />
            ))}
          </div>
        </section>

        {/* Support Roles */}
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-emerald-500/20 rounded-lg">
              <Users className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Support Teams & Other Roles</h2>
              <p className="text-slate-400 text-sm">Essential support for documentation and data management</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {SUPPORT_ROLES.map((role, idx) => (
              <RoleCard key={idx} role={role} />
            ))}
          </div>
        </section>

        {/* Quick Reference */}
        <section>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Quick Reference: Workflow</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                <div className="text-3xl font-bold text-orange-500 mb-2">1</div>
                <p className="text-sm text-slate-300">Department Coordinators collect data</p>
              </div>
              <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                <div className="text-3xl font-bold text-blue-500 mb-2">2</div>
                <p className="text-sm text-slate-300">Criterion Coordinators compile & verify</p>
              </div>
              <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                <div className="text-3xl font-bold text-purple-500 mb-2">3</div>
                <p className="text-sm text-slate-300">IQAC Coordinator reviews & prepares SSR</p>
              </div>
              <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                <div className="text-3xl font-bold text-green-500 mb-2">4</div>
                <p className="text-sm text-slate-300">Head of Institution approves & submits</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
