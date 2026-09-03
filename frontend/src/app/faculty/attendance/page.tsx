'use client'

import { Suspense, useState  } from 'react'
import { useSearchParams } from 'next/navigation'
import { ClipboardCheck } from 'lucide-react'
import { DataTable, PageShell, Pill, ResourceState, TD, TD_LEFT, useFacultyResource } from '@/components/faculty/PageShell'
import { fetchAttendance } from '@/lib/faculty-api'
import { RollCall } from '@/components/faculty/RollCall'
import { StudentRegister } from '@/components/faculty/StudentRegister'

function AttendancePageContent() {
  const params = useSearchParams()
  const section = params.get('section') ?? undefined
  const belowOnly = params.get('below') === '1'

  const { data, loading, error, reload } = useFacultyResource(
    () => fetchAttendance({ section, below_floor_only: belowOnly, limit: 500 }),
    [section, belowOnly]
  )
  const items = data?.items ?? []
  const today = data?.today
  const [takingRoll, setTakingRoll] = useState(false)
  const [notice, setNotice] = useState('')
  const [openStudent, setOpenStudent] = useState<string | null>(null)

  return (
    <PageShell
      title="Attendance"
      subtitle={
        belowOnly
          ? `Students below the ${data?.floor ?? 75}% attendance floor`
          : 'Attendance rate per student for the academic year. Late counts as attended.'
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11.5px] text-[#5A5F7A]">
          {takingRoll
            ? 'Choose a section and a date, then mark the exceptions.'
            : 'Attendance is taken per section, per day. Saving a day again corrects it.'}
        </p>
        <button type="button" onClick={() => setTakingRoll((open) => !open)}
          className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]">
          <ClipboardCheck className="h-3.5 w-3.5" />
          {takingRoll ? 'Close register' : 'Take attendance'}
        </button>
      </div>

      {notice && (
        <p className="flex items-start justify-between gap-2 rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-3 py-2 text-[12px] text-[#15803D]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')}
            className="shrink-0 font-medium hover:underline">Dismiss</button>
        </p>
      )}

      {openStudent && (
        <StudentRegister studentId={openStudent} onClose={() => setOpenStudent(null)} />
      )}

      {takingRoll && (
        <RollCall
          onClose={() => setTakingRoll(false)}
          onSaved={(message) => { setNotice(message); reload() }} />
      )}

      {today && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Present today', value: today.present, tone: 'text-[#16A34A]' },
            { label: 'Absent today', value: today.absent, tone: 'text-[#DC2626]' },
            { label: 'Late today', value: today.late, tone: 'text-[#D97706]' },
          ].map((s) => (
            <div key={s.label} className="rounded-xl border border-[#E8E9F2] bg-white p-3">
              <p className={`text-[20px] font-bold leading-none ${s.tone}`}>{s.value}</p>
              <p className="mt-1 text-[11px] text-[#5A5F7A]">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <ResourceState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyMessage="No attendance records for this view."
        onRetry={reload}
      >
        <DataTable head={['Roll No.', 'Name', 'Department', 'Section', 'Attendance', 'Status']}>
          {items.map((a) => (
            <tr key={a.student_id}
              onClick={() => setOpenStudent(a.student_id)}
              title="Open this student's register"
              className="cursor-pointer border-b border-[#F1F2F8] hover:bg-[#FAFBFE]">
              <td className={TD_LEFT}>{a.roll_number ?? '–'}</td>
              <td className={TD}>{a.full_name ?? '–'}</td>
              <td className={TD}>{a.department}</td>
              <td className={TD}>{a.section ?? '–'}</td>
              <td className={TD}>{a.attendance_rate === null ? '–' : `${a.attendance_rate}%`}</td>
              <td className={TD}>
                {a.attendance_rate === null
                  ? <Pill tone="slate">No records</Pill>
                  : a.below_floor
                    ? <Pill tone="red">Below floor</Pill>
                    : <Pill tone="green">OK</Pill>}
              </td>
            </tr>
          ))}
        </DataTable>
        <p className="text-[11px] text-[#8A8FA8]">{data?.count ?? items.length} student(s)</p>
      </ResourceState>
    </PageShell>
  )
}

/**
 * useSearchParams() opts the tree out of static rendering, and Next 14
 * fails the production build unless that bail-out sits behind a Suspense
 * boundary. Without this the page compiles in dev and breaks `next build`.
 */
export default function AttendancePage() {
  return (
    <Suspense fallback={<PageShell title="Attendance" subtitle="Loading…">{null}</PageShell>}>
      <AttendancePageContent />
    </Suspense>
  )
}
