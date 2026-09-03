'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { removeAccessToken } from '@/lib/auth-utils'
import { useAuth } from '@/hooks/useAuth'
import {
  Bell,
  ChevronDown,
  Check,
  ClipboardCheck,
  FileCheck2,
  FileSpreadsheet,
  FolderKanban,
  GraduationCap,
  HelpCircle,
  Home,
  CalendarCheck,
  CalendarRange,
  ListChecks,
  LogOut,
  PanelLeft,
  Settings,
  Sparkles,
  UsersRound,
} from 'lucide-react'
import {
  fetchTrainerColleges, getActiveCollege, setActiveCollege,
  fetchCollegeTrainers, getActiveTrainer, setActiveTrainer,
  fetchTrainerPending,
} from '@/lib/trainer-api'
import type { TrainerCollege, CollegeTrainer } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

export const NAV = [
  { href: '/trainer', label: 'Home', icon: Home },
  { href: '/trainer/batches', label: 'My Batches', icon: UsersRound },
  { href: '/trainer/reviews', label: 'Project Reviews', icon: ClipboardCheck },
  { href: '/trainer/ai-planning', label: 'AI Planning', icon: Sparkles },
  { href: '/trainer/attendance', label: 'Attendance', icon: CalendarCheck },
  { href: '/trainer/student-work', label: 'Student Work', icon: FolderKanban },
  { href: '/trainer/user-stories', label: 'User Stories', icon: ListChecks },
  { href: '/trainer/sprints', label: 'Sprints', icon: CalendarRange },
  { href: '/trainer/evidence', label: 'Evidence', icon: FileCheck2 },
  { href: '/trainer/imports', label: 'Imports', icon: FileSpreadsheet },
  { href: '/trainer/reports', label: 'Reports', icon: FileCheck2 },
  { href: '/trainer/settings', label: 'Settings', icon: Settings },
]

export function TrainerSidebar({ activeHref, collapsed = false }: {
  activeHref?: string
  collapsed?: boolean
} = {}) {
  const pathname = usePathname()
  const [pending, setPending] = useState<Record<string, number>>({})

  // Re-read on navigation: a trainer who has just verified the last document
  // should not keep seeing a badge for it. The endpoint counts rows and
  // returns integers, so this is cheap enough to do on every page.
  useEffect(() => {
    let live = true
    fetchTrainerPending()
      .then((data) => { if (live) setPending(data.counts ?? {}) })
      // A badge is a convenience. If the count cannot be fetched the nav still
      // works, and showing a stale or invented number would be worse.
      .catch(() => { if (live) setPending({}) })
    return () => { live = false }
  }, [pathname])

  // A screen that lives outside /trainer - a single story, say - still belongs
  // to one of these sections, and says which rather than lighting up nothing.
  const path = activeHref ?? pathname
  return (
    <aside className={cn(
      'hidden h-full shrink-0 flex-col overflow-y-auto bg-[#0B1B4D] text-white transition-[width] lg:flex',
      collapsed ? 'w-[60px]' : 'w-[212px]')}>
      <div className={cn('flex items-center py-4',
        collapsed ? 'justify-center px-2' : 'gap-2.5 px-4')}>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[#2563EB] text-[16px] font-bold">
          B
        </span>
        {!collapsed && (
          <span>
            <span className="block text-[15px] font-bold leading-tight">BharatBuild AI</span>
            <span className="block text-[10.5px] text-[#9DB2E8]">Trainer Portal</span>
          </span>
        )}
      </div>

      <nav className="mt-2 flex-1 px-2.5">
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            // `/trainer` must not light up for every child route.
            const active = item.href === '/trainer'
              ? path === '/trainer'
              : path.startsWith(item.href)
            const waiting = pending[item.href] ?? 0
            return (
              <li key={item.href}>
                <Link href={item.href}
                  // Collapsed, the label becomes the tooltip - the icon alone
                  // is a guess otherwise.
                  title={collapsed ? item.label : undefined}
                  className={cn('relative flex items-center rounded-lg py-2.5 text-[12.5px] transition-colors',
                    collapsed ? 'justify-center px-0' : 'gap-2.5 px-3',
                    active ? 'bg-[#1D4ED8] font-medium text-white' : 'text-[#C7D3F0] hover:bg-[#132a63]')}>
                  <item.icon className={cn('h-4 w-4 shrink-0', active ? 'text-white' : 'text-[#9DB2E8]')} />
                  {!collapsed && <span className="flex-1">{item.label}</span>}
                  {waiting > 0 && (
                    <span
                      title={`${waiting} waiting on you`}
                      className={cn('flex items-center justify-center rounded-full bg-[#DC2626] font-semibold text-white',
                        collapsed
                          // Collapsed there is no room for a number, so it
                          // becomes a dot - present, without pretending to be
                          // readable.
                          ? 'absolute right-2 top-2 h-2 w-2'
                          : 'h-[18px] min-w-[18px] px-1 text-[10px]')}>
                      {collapsed ? '' : waiting > 99 ? '99+' : waiting}
                    </span>
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

/**
 * Which college the trainer is working in.
 *
 * A trainer is BharatBuild's own staff and teaches at several institutions, so
 * "CSE section A" is ambiguous until one is chosen. Everything on every screen
 * is then that college's - the choice is sent on each request and the server
 * narrows to it, rather than each screen filtering for itself.
 *
 * Shown as plain text when they teach at one college: a picker with a single
 * option is a control that does nothing.
 */
function TrainerPicker() {
  const { user } = useAuth()
  const [trainers, setTrainers] = useState<CollegeTrainer[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  // Only a manager has colleagues to filter by; the endpoint answers empty for
  // everybody else, so this simply renders nothing for them.
  useEffect(() => {
    let live = true
    fetchCollegeTrainers()
      .then((data) => {
        if (!live) return
        setTrainers(data.trainers ?? [])
        const stored = getActiveTrainer()
        // A trainer who does not work in the college now chosen is not a
        // filter any more - drop it rather than showing an empty portal.
        const known = (data.trainers ?? []).some((t) => t.id === stored)
        if (stored && !known) setActiveTrainer(null)
        setActive(known ? stored : null)
      })
      .catch(() => { if (live) setTrainers([]) })
    return () => { live = false }
  }, [])

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (box.current?.contains(e.target as Node)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const choose = (id: string | null) => {
    setActiveTrainer(id)
    setOpen(false)
    // A full reload, for the same reason the college picker does one: the
    // previous filter's rows are already in memory on every screen.
    window.location.reload()
  }

  if (user?.role !== 'manager' || trainers.length === 0) return null

  const current = trainers.find((t) => t.id === active)

  return (
    <div className="relative min-w-0" ref={box}>
      <button type="button" onClick={() => setOpen((v) => !v)}
        title="Show one trainer's work, or everybody's"
        className={cn(
          'flex min-w-0 items-center gap-1 rounded-lg border px-2 py-1',
          current
            ? 'border-[#BFD4FF] bg-[#EEF4FF] text-[#1B2A6B]'
            : 'border-[#E5E7EB] text-[#6B7280] hover:bg-[#F4F5FA]')}>
        <UsersRound className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate text-[12px] font-medium">
          {current ? current.name : 'All trainers'}
        </span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0" />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-[#E5E7EB] bg-white py-1 shadow-lg">
          <p className="px-3 py-1.5 text-[10.5px] uppercase tracking-wide text-[#9CA3AF]">
            Whose work to show
          </p>
          <button type="button" onClick={() => choose(null)}
            className={cn('flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-[#F4F5FA]',
              !active && 'bg-[#F4F7FF]')}>
            <Check className={cn('mt-0.5 h-3.5 w-3.5 shrink-0',
              !active ? 'text-[#2563EB]' : 'text-transparent')} />
            <span className="min-w-0">
              <span className="block text-[12.5px] font-medium text-[#1B1B3A]">
                All trainers
              </span>
              <span className="block text-[10.5px] text-[#6B7280]">
                Everything in this college
              </span>
            </span>
          </button>
          {trainers.map((t) => (
            <button key={t.id} type="button" onClick={() => choose(t.id)}
              className={cn('flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-[#F4F5FA]',
                t.id === active && 'bg-[#F4F7FF]')}>
              <Check className={cn('mt-0.5 h-3.5 w-3.5 shrink-0',
                t.id === active ? 'text-[#2563EB]' : 'text-transparent')} />
              <span className="min-w-0">
                <span className="block truncate text-[12.5px] font-medium text-[#1B1B3A]">
                  {t.name}
                </span>
                <span className="block truncate text-[10.5px] text-[#6B7280]">
                  {t.scope.join(', ')} · {t.batches} batches
                </span>
              </span>
            </button>
          ))}
          <p className="border-t border-[#F1F2F8] px-3 pt-1.5 text-[10.5px] text-[#9CA3AF]">
            Filters what you see. You can still act on any of it.
          </p>
        </div>
      )}
    </div>
  )
}

function CollegePicker({ fallback }: { fallback: string | null }) {
  const { user } = useAuth()
  const role = user?.role
  const [colleges, setColleges] = useState<TrainerCollege[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let live = true
    fetchTrainerColleges()
      .then((data) => {
        if (!live) return
        setColleges(data.colleges)
        const stored = getActiveCollege()
        const known = data.colleges.some((c) => c.id === stored)
        // Default to the first college rather than leaving it unset: an
        // unscoped view merges two institutions, which is the thing this
        // exists to prevent.
        const next = known ? stored : (data.colleges[0]?.id ?? null)
        if (next !== stored) setActiveCollege(next)
        setActive(next)
      })
      .catch(() => { if (live) setColleges([]) })
    return () => { live = false }
  }, [])

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (box.current?.contains(e.target as Node)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const current = colleges.find((c) => c.id === active)
  // The same picker serves a trainer and a manager, and the difference is
  // worth a word: one is assigned their colleges, the other has every one.
  const isManager = role === 'manager'

  const choose = (id: string) => {
    setActiveCollege(id)
    setOpen(false)
    // A full reload rather than a re-render: every screen already has this
    // college's data in memory, and reloading is the one way to be certain
    // none of the previous college's rows survive on the page.
    window.location.reload()
  }

  if (colleges.length <= 1) {
    return (
      <span className="truncate text-[12.5px] font-semibold text-[#1B2A6B]">
        {current?.name ?? fallback ?? 'Your Institution'}
      </span>
    )
  }

  return (
    <div className="relative min-w-0" ref={box}>
      <button type="button" onClick={() => setOpen((v) => !v)}
        title={isManager
          ? 'Choose which college to look at'
          : 'Choose which college you are working in'}
        className="flex min-w-0 items-center gap-1 rounded-lg px-1.5 py-1 hover:bg-[#F4F5FA]">
        <span className="truncate text-[12.5px] font-semibold text-[#1B2A6B]">
          {current?.name ?? 'Choose a college'}
        </span>
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[#6B7280]" />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-[#E5E7EB] bg-white py-1 shadow-lg">
          <p className="px-3 py-1.5 text-[10.5px] uppercase tracking-wide text-[#9CA3AF]">
            {/* A manager teaches at none of them; they run all of them. */}
            {isManager
              ? `Managing all ${colleges.length} colleges`
              : `You teach at ${colleges.length} colleges`}
          </p>
          {colleges.map((c) => (
            <button key={c.id} type="button" onClick={() => choose(c.id)}
              className={cn('flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-[#F4F5FA]',
                c.id === active && 'bg-[#F4F7FF]')}>
              <Check className={cn('mt-0.5 h-3.5 w-3.5 shrink-0',
                c.id === active ? 'text-[#2563EB]' : 'text-transparent')} />
              <span className="min-w-0">
                <span className="block truncate text-[12.5px] font-medium text-[#1B1B3A]">
                  {c.name}
                </span>
                <span className="block truncate text-[10.5px] text-[#6B7280]">
                  {c.sections.join(', ')}
                </span>
              </span>
            </button>
          ))}
          <p className="border-t border-[#F1F2F8] px-3 pt-1.5 text-[10.5px] text-[#9CA3AF]">
            Every screen shows the college chosen here.
          </p>
        </div>
      )}
    </div>
  )
}

export function TrainerTopBar({ college, name, onToggleSidebar }: { college: string | null; name: string | null; onToggleSidebar?: () => void }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close only on clicks outside the menu. This listener and React's own
  // delegated one both sit on `document` - the App Router's root layout
  // renders <html>/<body>, so React 18's root container is the document -
  // and stopPropagation cannot stop a listener on the same node. Closing
  // unconditionally on mousedown unmounted the menu before the button's
  // click could fire, which is why Sign out did nothing.
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
    // 48px rather than 64. The college name is on every screen of a portal
    // the trainer signed into - it does not need 20px caps and its own icon
    // tile, and the height it was taking came out of the work below it.
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-[#E5E7EB] bg-white px-3">
      <div className="flex min-w-0 items-center gap-2">
        {onToggleSidebar && (
          <button type="button" onClick={onToggleSidebar} aria-label="Toggle navigation"
            title="Show or hide the menu"
            className="hidden rounded-lg p-1.5 text-[#6B7280] hover:bg-[#F4F5FA] lg:block">
            <PanelLeft className="h-4 w-4" />
          </button>
        )}
        <GraduationCap className="h-4 w-4 shrink-0 text-[#1B2A6B]" />
        <CollegePicker fallback={college} />
        <TrainerPicker />
      </div>

      <div className="flex items-center gap-0.5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280]" title="Notifications">
          <Bell className="h-4 w-4" />
        </span>
        <Link href="/trainer/settings" title="Help"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-[#6B7280] hover:bg-[#F4F5FA]">
          <HelpCircle className="h-4 w-4" />
        </Link>
        <div className="relative" ref={menuRef}>
          <button type="button" onClick={() => setOpen((v) => !v)}
            title={name ?? undefined}
            className="flex items-center gap-1.5 rounded-lg px-1 py-1 hover:bg-[#F4F5FA]">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#DBE3F5] text-[10.5px] font-semibold text-[#1B2A6B]">
              {initials}
            </span>
            {/* The name only when there is room; the initials carry it on a
                laptop, and the menu names them in full anyway. */}
            <span className="hidden text-[12px] font-medium text-[#1B1B3A] xl:block">
              {name ?? '—'}
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-[#9CA3AF]" />
          </button>
          {open && (
            <div className="absolute right-0 z-20 mt-1 min-w-[172px] overflow-hidden rounded-lg border border-[#E5E7EB] bg-white py-1 shadow-lg">
              <button type="button"
                onClick={() => {
                  // removeAccessToken clears the cookie as well as
                  // localStorage; setAccessToken writes both, and a
                  // localStorage-only sign out left the 7-day cookie behind.
                  removeAccessToken()
                  localStorage.removeItem('refresh_token')
                  localStorage.removeItem('user')
                  router.replace('/trainer/login')
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
