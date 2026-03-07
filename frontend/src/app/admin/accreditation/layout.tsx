'use client'

import { NAACRoleProvider } from '@/contexts/NAACRoleContext'
import AccreditationNav from '@/components/AccreditationNav'

export default function AccreditationLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <NAACRoleProvider>
      <div className="min-h-screen bg-slate-900">
        <AccreditationNav />
        <main className="pb-8">
          {children}
        </main>
      </div>
    </NAACRoleProvider>
  )
}
