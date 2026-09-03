'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, Check, Clock, Loader2, UserX, X } from 'lucide-react'
import {
  attendanceError, fetchStudentAttendance, type StudentAttendance,
} from '@/lib/attendance-api'
import { cn } from '@/lib/utils'

const TONE = {
  present: { label: 'Present', chip: 'bg-[#DCFCE7] text-[#15803D]', Icon: Check },
  late: { label: 'Late', chip: 'bg-[#FEF3C7] text-[#B45309]', Icon: Clock },
  absent: { label: 'Absent', chip: 'bg-[#FEE2E2] text-[#B91C1C]', Icon: UserX },
} as const

/**
 * One student's register, opened from the attendance list.
 *
 * A rate on its own is not a conversation anyone can have. This is the list of
 * days it was built from, which is what a coordinator needs in front of them
 * when a student disputes it.
 */
export function StudentRegister({ studentId, onClose }: {
  studentId: string
  onClose: () => void
}) {
  const [data, setData] = useState<StudentAttendance | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null); setError('')
    fetchStudentAttendance(studentId)
      .then(setData)
      .catch((err) => setError(attendanceError(err, 'Could not load that register.')))
  }, [studentId])

  return (
    <section className="rounded-xl border border-[#C7BDF5] bg-[#F5F3FF] p-3">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <p className="text-[12.5px] font-semibold text-[#1B1B3A]">
            {data?.student?.full_name ?? 'Attendance register'}
            {data?.student?.roll_number && (
              <span className="ml-2 font-mono font-normal text-[11px] text-[#5A5F7A]">
                {data.student.roll_number}
              </span>
            )}
          </p>
          {data?.student && (
            <p className="text-[10.5px] text-[#8A8FA8]">
              {[data.student.department, data.student.section && `Section ${data.student.section}`,
                data.academic_year].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <button type="button" onClick={onClose} aria-label="Close"
          className="text-[#5A5F7A] hover:text-[#1B1B3A]"><X className="h-4 w-4" /></button>
      </div>

      {error && <p className="text-[11.5px] text-[#B91C1C]">{error}</p>}

      {!data && !error && (
        <p className="flex items-center gap-2 py-3 text-[12px] text-[#5A5F7A]">
          <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> Loading&hellip;
        </p>
      )}

      {data && (
        data.days_recorded === 0 ? (
          <p className="py-3 text-[12px] text-[#8A8FA8]">
            Nothing has been marked for this student in {data.academic_year}.
          </p>
        ) : (
          <>
            {data.below_floor && (
              <p className="mb-2 flex items-start gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-1.5 text-[11.5px] text-[#B91C1C]">
                <AlertTriangle className="mt-[1px] h-3.5 w-3.5 shrink-0" />
                Below the {data.floor}% requirement.
              </p>
            )}
            <div className="mb-2 flex flex-wrap gap-3 text-[11.5px]">
              <Stat label="Attendance"
                value={data.attendance_rate === null ? '—' : `${data.attendance_rate}%`}
                tone={data.below_floor ? 'text-[#B91C1C]' : 'text-[#15803D]'} />
              <Stat label="Days" value={String(data.days_recorded)} tone="text-[#1B1B3A]" />
              <Stat label="Late" value={String(data.late)} tone="text-[#B45309]" />
              <Stat label="Absent" value={String(data.absent)} tone="text-[#B91C1C]" />
            </div>
            <ul className="max-h-[220px] space-y-0.5 overflow-y-auto rounded-lg bg-white p-2">
              {data.days.map((d) => {
                const tone = TONE[d.status as keyof typeof TONE] ?? TONE.present
                return (
                  <li key={d.date} className="flex items-center justify-between px-1 py-1">
                    <span className="text-[11.5px] text-[#3A3F58]">
                      {new Date(`${d.date}T00:00:00`).toLocaleDateString('en-IN', {
                        weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
                      })}
                    </span>
                    <span className={cn('flex items-center gap-1 rounded px-1.5 py-0.5 text-[10.5px] font-medium', tone.chip)}>
                      <tone.Icon className="h-2.5 w-2.5" /> {tone.label}
                    </span>
                  </li>
                )
              })}
            </ul>
          </>
        )
      )}
    </section>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <span className="rounded-lg border border-[#DDE0EE] bg-white px-2.5 py-1">
      <span className={cn('text-[14px] font-bold tabular-nums', tone)}>{value}</span>
      <span className="ml-1.5 text-[10.5px] text-[#8A8FA8]">{label}</span>
    </span>
  )
}
