import type { Metadata } from 'next'
import { FacultySidebar } from '@/components/faculty/FacultySidebar'
import { FacultyTopBar } from '@/components/faculty/FacultyTopBar'

export const metadata: Metadata = {
  title: 'Faculty Portal',
  description: 'Monitor registrations, attendance, project progress and upcoming reviews.',
}

export default function FacultyLayout({ children }: { children: React.ReactNode }) {
  return (
    // The rest of the app is dark-themed; the faculty portal is its own light
    // surface, so colours here are explicit rather than theme tokens.
    <div className="flex min-h-screen bg-[#F4F5FA] text-[#1B1B3A]">
      <FacultySidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <FacultyTopBar />
        <main className="flex-1 px-5 pb-4 pt-3">{children}</main>
      </div>
    </div>
  )
}
