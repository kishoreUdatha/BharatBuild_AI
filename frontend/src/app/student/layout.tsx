'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { StudentSidebar, StudentTopBar } from '@/components/student/StudentShell'
import { fetchRegistration, type RegistrationState } from '@/lib/student-api'

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  // Remembered per browser, and kept separate from the trainer's key so the
  // two portals do not overwrite each other's choice.
  const [collapsed, setCollapsed] = useState(false)
  useEffect(() => {
    try { setCollapsed(localStorage.getItem('student.nav.collapsed') === '1') } catch { /* private mode */ }
  }, [])
  const toggleNav = () => {
    setCollapsed((v) => {
      const next = !v
      try { localStorage.setItem('student.nav.collapsed', next ? '1' : '0') } catch { /* ignore */ }
      return next
    })
  }
  const [state, setState] = useState<RegistrationState | null>(null)

  // The top bar needs the student's own name and college; the registration
  // payload already carries them, so no extra profile call.
  useEffect(() => {
    let cancelled = false
    fetchRegistration()
      .then((data) => { if (!cancelled) setState(data) })
      .catch((err: any) => {
        if (cancelled) return
        const status = err?.response?.status
        if (status === 401) {
          // Carry the page they were actually on, query and all. An invite
          // link is /student/registration?code=BB-... and hard-coding the
          // path here dropped the code, landing a new teammate on an empty
          // form with nothing to type.
          const here = window.location.pathname + window.location.search
          router.replace(`/login?next=${encodeURIComponent(here)}`)
        }
        if (status === 403) router.replace('/build')
      })
    return () => { cancelled = true }
  }, [router])

  return (
    // The rest of the app is dark-themed; the student portal is its own light
    // surface, so colours here are explicit rather than theme tokens.
    // h-screen + overflow-hidden makes this an app shell rather than a tall
    // document: the sidebar and top bar hold their place and only <main>
    // scrolls. It also gives the sidebar a bounded parent, which is what its
    // h-full needs to fill the screen when collapsed.
    <div className="flex h-screen overflow-hidden bg-[#F5F7FB] text-[#1B1B3A]">
      <StudentSidebar collapsed={collapsed} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <StudentTopBar
          onToggleSidebar={toggleNav}
          college={state?.student.college ?? null}
          name={state?.student.name ?? null}
          roll={state?.student.roll_number ?? null}
        />
        <main className="flex-1 overflow-y-auto px-5 pb-6 pt-4">{children}</main>
      </div>
    </div>
  )
}
