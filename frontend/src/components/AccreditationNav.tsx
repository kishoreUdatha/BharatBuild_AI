'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  BookOpen,
  GraduationCap,
  FlaskConical,
  Building,
  Users,
  Settings,
  Heart,
  Award,
  Home,
  ChevronDown,
  Shield,
  ListTodo,
  ClipboardCheck,
  FileText,
  FolderOpen,
  BarChart3,
  FileCheck,
  TrendingUp,
  PieChart,
} from 'lucide-react'
import { useState } from 'react'

interface CriterionInfo {
  id: string
  name: string
  shortName: string
  href: string
  icon: React.ElementType
  color: string
  marks: number
}

const NAAC_CRITERIA: CriterionInfo[] = [
  { id: '1', name: 'Curricular Aspects', shortName: 'C1', href: '/admin/accreditation/criterion1', icon: BookOpen, color: 'orange', marks: 150 },
  { id: '2', name: 'Teaching-Learning', shortName: 'C2', href: '/admin/accreditation/criterion2', icon: GraduationCap, color: 'blue', marks: 200 },
  { id: '3', name: 'Research & Extension', shortName: 'C3', href: '/admin/accreditation/criterion3', icon: FlaskConical, color: 'purple', marks: 150 },
  { id: '4', name: 'Infrastructure', shortName: 'C4', href: '/admin/accreditation/criterion4', icon: Building, color: 'green', marks: 100 },
  { id: '5', name: 'Student Support', shortName: 'C5', href: '/admin/accreditation/criterion5', icon: Users, color: 'pink', marks: 100 },
  { id: '6', name: 'Governance', shortName: 'C6', href: '/admin/accreditation/criterion6', icon: Settings, color: 'cyan', marks: 100 },
  { id: '7', name: 'Institutional Values', shortName: 'C7', href: '/admin/accreditation/criterion7', icon: Heart, color: 'red', marks: 100 },
]

const colorMap: Record<string, string> = {
  orange: 'bg-orange-500 hover:bg-orange-600',
  blue: 'bg-blue-500 hover:bg-blue-600',
  purple: 'bg-purple-500 hover:bg-purple-600',
  green: 'bg-green-500 hover:bg-green-600',
  pink: 'bg-pink-500 hover:bg-pink-600',
  cyan: 'bg-cyan-500 hover:bg-cyan-600',
  red: 'bg-red-500 hover:bg-red-600',
  yellow: 'bg-yellow-500 hover:bg-yellow-600',
}

const borderColorMap: Record<string, string> = {
  orange: 'border-orange-500',
  blue: 'border-blue-500',
  purple: 'border-purple-500',
  green: 'border-green-500',
  pink: 'border-pink-500',
  cyan: 'border-cyan-500',
  red: 'border-red-500',
  yellow: 'border-yellow-500',
}

export default function AccreditationNav() {
  const pathname = usePathname()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const isActive = (href: string) => {
    if (href === '/admin/accreditation') {
      return pathname === href
    }
    return pathname.startsWith(href)
  }

  const getCurrentCriterion = () => {
    return NAAC_CRITERIA.find(c => pathname.startsWith(c.href))
  }

  const currentCriterion = getCurrentCriterion()

  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Left: Home + Quick Links */}
          <div className="flex items-center gap-2">
            <Link
              href="/admin/accreditation"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                pathname === '/admin/accreditation'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Home className="w-4 h-4" />
              <span className="font-medium hidden sm:inline">Home</span>
            </Link>
            <Link
              href="/admin/accreditation/dashboard"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                pathname === '/admin/accreditation/dashboard'
                  ? 'bg-orange-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span className="font-medium hidden sm:inline">Dashboard</span>
            </Link>
            <Link
              href="/admin/accreditation/analytics"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                pathname === '/admin/accreditation/analytics'
                  ? 'bg-purple-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <PieChart className="w-4 h-4" />
              <span className="font-medium hidden sm:inline">Analytics</span>
            </Link>
            <Link
              href="/admin/accreditation/ssr"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                pathname === '/admin/accreditation/ssr'
                  ? 'bg-blue-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span className="font-medium hidden lg:inline">SSR</span>
            </Link>
            <Link
              href="/admin/accreditation/iqac"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                pathname === '/admin/accreditation/iqac'
                  ? 'bg-purple-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span className="font-medium hidden lg:inline">IQAC</span>
            </Link>
            <Link
              href="/admin/accreditation/dvv"
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                pathname === '/admin/accreditation/dvv'
                  ? 'bg-teal-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <FileCheck className="w-4 h-4" />
              <span className="font-medium hidden lg:inline">DVV</span>
            </Link>

            {/* Criteria Dropdown for Mobile */}
            <div className="relative md:hidden">
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  currentCriterion
                    ? `${colorMap[currentCriterion.color]} text-white`
                    : 'bg-slate-800 text-slate-300'
                }`}
              >
                {currentCriterion ? (
                  <>
                    <currentCriterion.icon className="w-4 h-4" />
                    <span>{currentCriterion.shortName}</span>
                  </>
                ) : (
                  <span>Select Criterion</span>
                )}
                <ChevronDown className={`w-4 h-4 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {dropdownOpen && (
                <div className="absolute top-full left-0 mt-2 w-64 bg-slate-800 rounded-lg shadow-xl border border-slate-700 py-2 z-50">
                  {NAAC_CRITERIA.map((criterion) => {
                    const Icon = criterion.icon
                    const active = isActive(criterion.href)
                    return (
                      <Link
                        key={criterion.id}
                        href={criterion.href}
                        onClick={() => setDropdownOpen(false)}
                        className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                          active
                            ? `${colorMap[criterion.color]} text-white`
                            : 'text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        <span className="flex-1">{criterion.shortName}: {criterion.name}</span>
                        <span className="text-xs opacity-75">{criterion.marks}</span>
                      </Link>
                    )
                  })}
                  <div className="border-t border-slate-700 mt-2 pt-2">
                    <Link
                      href="/admin/accreditation/dvv"
                      onClick={() => setDropdownOpen(false)}
                      className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                        pathname.startsWith('/admin/accreditation/dvv')
                          ? 'bg-teal-500 text-white'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      <FileCheck className="w-4 h-4" />
                      <span>DVV Clarifications</span>
                    </Link>
                    <Link
                      href="/admin/accreditation/roles"
                      onClick={() => setDropdownOpen(false)}
                      className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                        pathname.startsWith('/admin/accreditation/roles')
                          ? 'bg-blue-500 text-white'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      <Shield className="w-4 h-4" />
                      <span>Roles & Responsibilities</span>
                    </Link>
                    <Link
                      href="/admin/accreditation/mbgl"
                      onClick={() => setDropdownOpen(false)}
                      className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                        pathname.startsWith('/admin/accreditation/mbgl')
                          ? 'bg-green-500 text-white'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      <TrendingUp className="w-4 h-4" />
                      <span>MBGL Assessment (2025)</span>
                    </Link>
                    <Link
                      href="/admin/accreditation/nba"
                      onClick={() => setDropdownOpen(false)}
                      className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                        pathname.startsWith('/admin/accreditation/nba')
                          ? 'bg-yellow-500 text-white'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      <Award className="w-4 h-4" />
                      <span>NBA Accreditation</span>
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Center: Criteria Pills (Desktop) */}
          <div className="hidden md:flex items-center gap-1">
            {NAAC_CRITERIA.map((criterion) => {
              const Icon = criterion.icon
              const active = isActive(criterion.href)
              return (
                <Link
                  key={criterion.id}
                  href={criterion.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    active
                      ? `${colorMap[criterion.color]} text-white shadow-lg`
                      : `text-slate-400 hover:text-white hover:bg-slate-800 border border-transparent hover:${borderColorMap[criterion.color]}`
                  }`}
                  title={`${criterion.name} (${criterion.marks} marks)`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{criterion.shortName}</span>
                </Link>
              )
            })}
          </div>

          {/* Right: Tasks, Approvals, Documents, Roles, Settings */}
          <div className="flex items-center gap-1">
            <Link
              href="/admin/accreditation/tasks"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/tasks')
                  ? 'bg-green-500 text-white'
                  : 'text-green-400 hover:bg-green-500/10'
              }`}
            >
              <ListTodo className="w-4 h-4" />
              <span className="hidden xl:inline">Tasks</span>
            </Link>
            <Link
              href="/admin/accreditation/approvals"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/approvals')
                  ? 'bg-amber-500 text-white'
                  : 'text-amber-400 hover:bg-amber-500/10'
              }`}
            >
              <ClipboardCheck className="w-4 h-4" />
              <span className="hidden xl:inline">Approvals</span>
            </Link>
            <Link
              href="/admin/accreditation/documents"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/documents')
                  ? 'bg-purple-500 text-white'
                  : 'text-purple-400 hover:bg-purple-500/10'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              <span className="hidden xl:inline">Docs</span>
            </Link>
            <Link
              href="/admin/accreditation/roles"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/roles')
                  ? 'bg-blue-500 text-white'
                  : 'text-blue-400 hover:bg-blue-500/10'
              }`}
            >
              <Shield className="w-4 h-4" />
              <span className="hidden xl:inline">Roles</span>
            </Link>
            <Link
              href="/admin/accreditation/settings"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/settings')
                  ? 'bg-slate-500 text-white'
                  : 'text-slate-400 hover:bg-slate-500/10'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span className="hidden xl:inline">Settings</span>
            </Link>
            <Link
              href="/admin/accreditation/mbgl"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/mbgl')
                  ? 'bg-green-500 text-white'
                  : 'text-green-500 hover:bg-green-500/10'
              }`}
            >
              <TrendingUp className="w-4 h-4" />
              <span className="hidden xl:inline">MBGL</span>
            </Link>
            <Link
              href="/admin/accreditation/nba"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-colors text-sm ${
                pathname.startsWith('/admin/accreditation/nba')
                  ? 'bg-yellow-500 text-white'
                  : 'text-yellow-500 hover:bg-yellow-500/10'
              }`}
            >
              <Award className="w-4 h-4" />
              <span className="hidden xl:inline">NBA</span>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
