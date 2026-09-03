'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  ClipboardList,
  CalendarCheck,
  GitBranch,
  ClipboardCheck,
  Building2,
  FileText,
  UserCog,
  UserPlus,
  Calendar,
  BarChart3,
  Sparkles,
  Settings,
  ChevronLeft,
} from 'lucide-react'

const NAV = [
  { href: '/faculty', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/faculty/registrations', label: 'Registrations', icon: ClipboardList },
  { href: '/faculty/attendance', label: 'Attendance', icon: CalendarCheck },
  { href: '/faculty/project-tracking', label: 'Project Tracking', icon: GitBranch },
  { href: '/faculty/project-reviews', label: 'Project Reviews', icon: ClipboardCheck },
  { href: '/faculty/departments', label: 'Departments & Sections', icon: Building2 },
  { href: '/faculty/base-papers', label: 'Base Papers', icon: FileText },
  { href: '/faculty/guides', label: 'Faculty Guides', icon: UserCog },
  { href: '/faculty/staff', label: 'Staff', icon: UserPlus },
  { href: '/faculty/calendar', label: 'Calendar', icon: Calendar },
  { href: '/faculty/reports', label: 'Reports & Analytics', icon: BarChart3 },
  { href: '/faculty/ai-assistant', label: 'AI Assistant', icon: Sparkles },
  { href: '/faculty/settings', label: 'Settings', icon: Settings },
]

export function FacultySidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        'sticky top-0 flex h-screen shrink-0 flex-col bg-[#2C2A6B] text-white transition-[width] duration-200',
        collapsed ? 'w-[76px]' : 'w-[232px]'
      )}
    >
      <div className={cn('px-5 pb-6 pt-5', collapsed && 'px-4')}>
        {collapsed ? (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15 text-sm font-bold">B</div>
        ) : (
          <>
            <p className="text-[15px] font-bold leading-tight">BharatBuild AI</p>
            <p className="mt-0.5 text-[11px] text-white/55">Faculty Portal</p>
          </>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] transition-colors',
                active
                  ? 'bg-[#4F46E5] font-medium text-white shadow-sm shadow-[#4F46E5]/40'
                  : 'text-white/70 hover:bg-white/10 hover:text-white',
                collapsed && 'justify-center px-0'
              )}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.8} />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          )
        })}
      </nav>

      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className={cn(
          'm-3 flex items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] text-white/70 transition-colors hover:bg-white/10 hover:text-white',
          collapsed && 'justify-center px-0'
        )}
      >
        <ChevronLeft className={cn('h-[18px] w-[18px] shrink-0 transition-transform', collapsed && 'rotate-180')} />
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  )
}
