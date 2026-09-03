'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  ChevronDown,
  HelpCircle,
  FileText,
  FolderKanban,
  ListChecks,
  GraduationCap,
  Headphones,
  Home,
  LogOut,
  PanelLeft,
  Settings,
  UserCheck,
  Wallet,
  Send,
  CalendarCheck,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { removeAccessToken } from '@/lib/auth-utils'

const NAV = [
  { href: '/student', label: 'Home', icon: Home },
  { href: '/student/registration', label: 'Registration', icon: UserCheck },
  { href: '/student/workspace', label: 'Project Workspace', icon: FolderKanban },
  { href: '/student/stories', label: 'My Stories', icon: ListChecks },
  { href: '/student/payments', label: 'Payments', icon: Wallet },
  { href: '/student/submissions', label: 'Submissions', icon: Send },
  { href: '/student/attendance', label: 'Attendance', icon: CalendarCheck },
  { href: '/student/documents', label: 'Documents', icon: FileText },
  { href: '/student/support', label: 'Help & Support', icon: Headphones },
  { href: '/student/settings', label: 'Settings', icon: Settings },
]

export function StudentSidebar({ collapsed = false }: { collapsed?: boolean } = {}) {
  const pathname = usePathname()
  return (
    <aside className={cn(
      'hidden h-full shrink-0 flex-col overflow-y-auto bg-gradient-to-b from-[#0B1B4D] to-[#0A1740]',
      'text-white transition-[width] lg:flex',
      collapsed ? 'w-[60px]' : 'w-[214px]')}>
      <div className={cn('flex items-center py-4',
        collapsed ? 'justify-center px-2' : 'gap-2.5 px-4')}>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#2563EB] text-[16px] font-bold">
          B
        </span>
        {!collapsed && (
          <span>
            <span className="block text-[15px] font-bold leading-tight">BharatBuild AI</span>
            <span className="block text-[10.5px] text-[#9DB2E8]">Student Portal</span>
          </span>
        )}
      </div>

      <nav className="mt-2 flex-1 px-2.5">
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            // `/student` must not light up for every child route.
            const active = item.href === '/student'
              ? pathname === '/student'
              : pathname.startsWith(item.href)
            return (
              <li key={item.href}>
                <Link href={item.href}
                  // Collapsed, the label becomes the tooltip - an icon on its
                  // own is a guess.
                  title={collapsed ? item.label : undefined}
                  className={cn('flex items-center rounded-lg py-2.5 text-[12.5px] transition-colors',
                    collapsed ? 'justify-center px-0' : 'gap-2.5 px-3',
                    active ? 'bg-[#16306E]' : 'hover:bg-[#122457]')}>
                  <item.icon className={cn('h-4 w-4 shrink-0', active ? 'text-white' : 'text-[#9DB2E8]')} />
                  {!collapsed && (
                    <span className={active ? 'font-medium text-white' : 'text-[#C7D3F0]'}>{item.label}</span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}

export function StudentTopBar({ college, name, roll, onToggleSidebar }: {
  college: string | null
  name: string | null
  roll: string | null
  onToggleSidebar?: () => void
}) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on clicks outside the menu only. This listener and React's own
  // delegated one both sit on `document` - the App Router's root layout
  // renders <html>/<body>, so React 18's root container is the document
  // itself - and stopPropagation cannot stop a listener on the same node.
  // Closing unconditionally on mousedown unmounted the menu before the
  // button's click could fire, which is why Sign out did nothing.
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (menuRef.current?.contains(e.target as Node)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const initials = (name ?? '?').split(' ').map((p) => p[0]).slice(-2).join('').toUpperCase()

  return (
    // Matched to the trainer portal: 48px, so the two do not disagree about
    // how much of the screen a header is worth.
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-[#E5E7EB] bg-white px-3">
      <div className="flex min-w-0 items-center gap-2">
        {onToggleSidebar && (
          <button type="button" onClick={onToggleSidebar} aria-label="Toggle navigation"
            title="Show or hide the menu"
            className="hidden rounded-lg p-1.5 text-[#4B5563] hover:bg-[#F4F5FA] lg:block">
            <PanelLeft className="h-4 w-4" />
          </button>
        )}
        <GraduationCap className="h-4 w-4 shrink-0 text-[#1B2A6B]" />
        <span className="truncate text-[12.5px] font-semibold text-[#1B2A6B]">
          {college ?? 'Your Institution'}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <Link href="/student/support" title="Registration help"
          className="flex h-8 items-center gap-1.5 rounded-lg border border-[#DBE3F5] px-2.5 text-[11.5px] font-medium text-[#2563EB] hover:bg-[#F4F7FF]">
          <HelpCircle className="h-3.5 w-3.5" />
          <span className="hidden lg:inline">Help</span>
        </Link>

        <div className="relative" ref={menuRef}>
          <button type="button" onClick={() => setOpen((v) => !v)}
            title={[name, roll].filter(Boolean).join(' · ') || undefined}
            className="flex items-center gap-1.5 rounded-lg px-1 py-1 hover:bg-[#F4F5FA]">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#DBE3F5] text-[10.5px] font-semibold text-[#1B2A6B]">
              {initials}
            </span>
            <span className="hidden text-[12px] font-medium text-[#1B1B3A] xl:block">
              {name ?? '—'}
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-[#9CA3AF]" />
          </button>
          {open && (
            <div className="absolute right-0 z-20 mt-1 min-w-[168px] overflow-hidden rounded-lg border border-[#E5E7EB] bg-white py-1 shadow-lg">
              <Link href="/student/settings"
                className="block px-3 py-1.5 text-[12px] text-[#3A3F58] hover:bg-[#F7F8FC]">Settings</Link>
              <button type="button"
                onClick={() => {
                  // removeAccessToken clears the cookie as well as
                  // localStorage; setAccessToken writes both, and a
                  // localStorage-only sign out left the 7-day cookie behind.
                  removeAccessToken()
                  localStorage.removeItem('refresh_token')
                  localStorage.removeItem('user')
                  router.replace('/login')
                }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-[12px] text-[#DC2626] hover:bg-[#FEF2F2]">
                <LogOut className="h-3.5 w-3.5" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
