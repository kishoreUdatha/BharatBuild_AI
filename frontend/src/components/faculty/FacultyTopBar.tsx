'use client'

import { useEffect, useState } from 'react'
import { Bell, ChevronDown, GraduationCap } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { ACADEMIC_YEARS, INSTITUTE, NOTIFICATION_COUNT, formatAcademicYear } from '@/lib/faculty-data'

export function FacultyTopBar() {
  const [year, setYear] = useState(ACADEMIC_YEARS[0])
  const [name, setName] = useState('')

  useEffect(() => {
    apiClient
      .getMe()
      .then((user: any) => setName(user?.full_name || user?.email || ''))
      .catch(() => setName(''))
  }, [])

  const initials = name
    .split(' ')
    .map((part) => part[0])
    .slice(-2)
    .join('')
    .toUpperCase()

  return (
    <header className="sticky top-0 z-20 flex h-[60px] items-center justify-between border-b border-[#E8E9F2] bg-white px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#EEF0FB] text-[#2C2A6B]">
          <GraduationCap className="h-5 w-5" />
        </div>
        <span className="text-[17px] font-semibold text-[#1B1B3A]">{INSTITUTE.name}</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative">
          <select
            aria-label="Academic year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            className="h-9 w-[190px] appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-3 pr-9 text-[13px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]"
          >
            {ACADEMIC_YEARS.map((y) => (
              <option key={y} value={y}>{formatAcademicYear(y)}</option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8A8FA8]" />
        </div>

        <button type="button" aria-label="Notifications" className="relative text-[#5A5F7A] hover:text-[#1B1B3A]">
          <Bell className="h-5 w-5" />
          <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-[#EF4444] px-1 text-[10px] font-semibold text-white">
            {NOTIFICATION_COUNT}
          </span>
        </button>

        <button type="button" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#DDE3F7] text-[12px] font-semibold text-[#2C2A6B]">
            {initials || '–'}
          </span>
          <span className="text-[13px] font-medium text-[#1B1B3A]">{name || 'Faculty'}</span>
          <ChevronDown className="h-4 w-4 text-[#8A8FA8]" />
        </button>
      </div>
    </header>
  )
}
