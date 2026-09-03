'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { TrainerSidebar, TrainerTopBar } from '@/components/trainer/TrainerShell'
import { apiClient } from '@/lib/api-client'

export default function TrainerLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  // The sign-in page lives inside this segment but must not be wrapped in the
  // portal shell, and must not run the guard - that would bounce a signed-out
  // visitor away from the very page they were sent to.
  const isLoginPage = pathname === '/trainer/login'
  const [me, setMe] = useState<{ full_name?: string; college_name?: string } | null>(null)
  // Remembered per browser: someone who collapses the menu wants it collapsed
  // next time too. Read after mount so the server and client agree on the
  // first paint.
  const [collapsed, setCollapsed] = useState(false)
  useEffect(() => {
    try { setCollapsed(localStorage.getItem('trainer.nav.collapsed') === '1') } catch { /* private mode */ }
  }, [])
  const toggleNav = () => {
    setCollapsed((v) => {
      const next = !v
      try { localStorage.setItem('trainer.nav.collapsed', next ? '1' : '0') } catch { /* ignore */ }
      return next
    })
  }

  useEffect(() => {
    if (isLoginPage) return
    let cancelled = false
    apiClient.getMe()
      .then((u: any) => { if (!cancelled) setMe(u) })
      .catch((err: any) => {
        if (cancelled) return
        // Trainers have their own door now, and it carries them back to the
        // page they were on.
        if (err?.response?.status === 401) {
          router.replace(`/trainer/login?next=${encodeURIComponent(pathname)}`)
        }
      })
    return () => { cancelled = true }
  }, [router, pathname, isLoginPage])

  if (isLoginPage) return <>{children}</>

  return (
    // The rest of the app is dark-themed; the trainer portal is its own light
    // surface, so colours here are explicit rather than theme tokens.
    // h-screen + overflow-hidden makes this an app shell rather than a tall
    // document: the sidebar and top bar hold their place and only <main>
    // scrolls. With min-h-screen the whole page scrolled as one, carrying the
    // navigation off the top of the screen.
    <div className="flex h-screen overflow-hidden bg-[#F5F7FB] text-[#1B1B3A]">
      <TrainerSidebar collapsed={collapsed} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TrainerTopBar
          college={me?.college_name ?? 'Sri Guru Institute of Technology'}
          name={me?.full_name ?? null}
          onToggleSidebar={toggleNav}
        />
        <main className="flex-1 overflow-y-auto px-5 pb-6 pt-4">{children}</main>
      </div>
    </div>
  )
}
