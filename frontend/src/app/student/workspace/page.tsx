'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Clock, Loader2, Lock, Users } from 'lucide-react'
import {
  fetchRegistration, fetchTeamBuilder, openTeamBuilder,
  type RegistrationState,
} from '@/lib/student-api'
import { TeamBuilderCard } from '@/components/project/TeamBuilderCard'
import {
  fetchStudentProject,
  projectError,
  saveStudentProject,
  submitStudentProject,
  type ProjectDetailsForm,
  type ProjectDetailsPayload,
} from '@/lib/project-details-api'
import { ProjectDetailsEditor } from '@/components/project/ProjectDetailsEditor'

const ACCENT = '#2563EB'

/**
 * Project Setup - where a team writes the project it registered for.
 *
 * Reachable as soon as the student holds a seat. Deliberately not gated on the
 * registration fee: planning and paying are separate, and the fee gateway is
 * not connected, so gating on it would leave this screen permanently shut.
 */
export default function StudentWorkspace() {
  const [registration, setRegistration] = useState<RegistrationState | null>(null)
  const [project, setProject] = useState<ProjectDetailsForm | null>(null)
  const [blocked, setBlocked] = useState('')
  const [loading, setLoading] = useState(true)
  const [flash, setFlash] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [reg, proj] = await Promise.allSettled([fetchRegistration(), fetchStudentProject()])
      if (reg.status === 'fulfilled') setRegistration(reg.value)
      if (proj.status === 'fulfilled') {
        setProject(proj.value)
        setBlocked('')
      } else {
        // 409 is the expected answer for a student with no seat yet, and its
        // detail already says what to do about it.
        setBlocked(projectError(proj.reason, 'Your project workspace is not open yet.'))
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async (payload: ProjectDetailsPayload) => {
    const next = await saveStudentProject(payload)
    setProject(next)
    return next
  }

  const submit = async (note: string) => {
    const result = await submitStudentProject(note)
    setFlash(result.message)
    await load()
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-[#E5E7EB] bg-white p-8 text-[12.5px] text-[#6B7280]">
        <Loader2 className="h-4 w-4 animate-spin text-[#2563EB]" /> Loading your project…
      </div>
    )
  }

  if (blocked || !project) {
    const waiting = registration?.your_registration.waiting_for ?? 0
    return (
      <div className="space-y-3">
        <Header batch={null} status={null} />
        <section className="rounded-xl border border-[#E5E7EB] bg-white p-8 text-center">
          <Lock className="mx-auto h-8 w-8 text-[#C7CBDD]" />
          <h2 className="mt-3 text-[16px] font-semibold text-[#1B1B3A]">Project Setup is not open</h2>
          <p className="mx-auto mt-1.5 max-w-md text-[12.5px] leading-snug text-[#6B7280]">
            {blocked || (waiting > 0
              ? `Waiting for ${waiting} student${waiting === 1 ? '' : 's'} to take a seat.`
              : 'Finish your registration first.')}
          </p>
          <Link href="/student/registration"
            className="mt-4 inline-block rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
            Go to registration
          </Link>
        </section>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <Header batch={project.batch_code} status={project.status} />

      {flash && (
        <p className="flex items-start gap-1.5 rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-2.5 py-2 text-[12px] text-[#15803D]">
          <CheckCircle2 className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {flash}
        </p>
      )}

      {registration?.batch && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-[#E5E7EB] bg-white px-3 py-2 text-[11.5px] text-[#5A5F7A]">
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-[#8A8FA8]" />
            {registration.team_joined} of {registration.team_size} seats taken
          </span>
          {registration.batch.guide
            ? <span>Guide: <span className="text-[#1B1B3A]">{registration.batch.guide}</span></span>
            : <span className="text-[#B45309]">No guide assigned yet</span>}
          {!project.is_lead && (
            <span className="flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-[#8A8FA8]" />
              You can edit; your batch leader submits
            </span>
          )}
        </div>
      )}

      <TeamBuilderCard
        batchCode={registration?.batch?.batch_code ?? null}
        load={fetchTeamBuilder} open={openTeamBuilder}
        repoHref="/student/stories" />

      <ProjectDetailsEditor
        data={project} accent={ACCENT} onSave={save} onSubmit={submit} />
    </div>
  )
}

function Header({ batch, status }: { batch: string | null; status: string | null }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">Project Setup</h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
          What your team is building, and how you will show it worked.
        </p>
      </div>
      {batch && (
        <span className="flex items-center gap-2 text-[11.5px]">
          <span className="rounded-md border border-[#DDE0EE] px-2 py-0.5 font-medium text-[#3A3F58]">
            {batch}
          </span>
          {status && (
            <span className="rounded-md bg-[#EEF2FF] px-2 py-0.5 font-medium capitalize text-[#4F46E5]">
              {status.replace(/_/g, ' ')}
            </span>
          )}
        </span>
      )}
    </div>
  )
}
