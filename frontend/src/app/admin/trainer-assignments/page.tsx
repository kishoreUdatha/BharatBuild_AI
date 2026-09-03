'use client'

/**
 * Trainer assignments - which colleges each trainer works at.
 *
 * Trainers are BharatBuild's own staff, so this is the platform operator's
 * decision: a college must not be able to grant itself somebody else s
 * trainer. An assignment is the only thing that gives a trainer reach - with
 * none they see an empty system, and with one they see that whole college.
 *
 * The batch count beside each is the point of the page: an assignment
 * reaching nothing looks identical to a correct one until somebody notices
 * the trainer has no work.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, Building2, Check, GraduationCap, Loader2, Plus, Search,
  Trash2, Users, X,
} from 'lucide-react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import apiClient from '@/lib/api-client'

interface Assignment {
  id: string
  college_id: string
  college: string
  department: string | null
  section: string | null
  label: string
  batches: number
}

interface Trainer {
  id: string
  name: string
  email: string
  is_active: boolean
  assignments: Assignment[]
  colleges: number
  batches: number
}

interface Payload {
  academic_year: string
  trainers: Trainer[]
  colleges: { id: string; name: string; code: string }[]
  /** college id -> branch -> sections that actually have batches. */
  structure: Record<string, Record<string, string[]>>
  unassigned: { id: string; name: string }[]
}

export default function TrainerAssignmentsPage() {
  const { theme } = useAdminTheme()
  const isDark = theme === 'dark'

  const [data, setData] = useState<Payload | null>(null)
  const [failed, setFailed] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState<Trainer | null>(null)
  const [creating, setCreating] = useState(false)
  const [busy, setBusy] = useState('')

  const load = useCallback(async () => {
    try {
      setData(await apiClient.get<Payload>('/admin/trainer-assignments'))
      setFailed('')
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'Assignments could not be loaded.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const shown = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return data?.trainers ?? []
    return (data?.trainers ?? []).filter((t) =>
      [t.name, t.email].some((f) => f.toLowerCase().includes(needle))
      || t.assignments.some((a) =>
        `${a.college} ${a.label}`.toLowerCase().includes(needle)))
  }, [data, search])

  const revoke = async (trainer: Trainer, a: Assignment) => {
    setBusy(a.id)
    setNotice('')
    try {
      await apiClient.delete(`/admin/trainer-assignments/${a.id}`)
      setNotice(`${trainer.name} no longer teaches ${a.label} at ${a.college}.`)
      await load()
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'That could not be revoked.')
    } finally { setBusy('') }
  }

  const card = isDark ? 'border-white/10 bg-[#141414]' : 'border-gray-200 bg-white'
  const ink = isDark ? 'text-gray-100' : 'text-gray-900'
  const muted = isDark ? 'text-gray-400' : 'text-gray-500'

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-50'}`}>
      <AdminHeader title="Trainer assignments"
        subtitle="Which colleges each trainer works at"
        onRefresh={load} />

      <div className="space-y-4 p-6">
        {failed && (
          <p className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            <AlertCircle className="h-4 w-4" /> {failed}
          </p>
        )}
        {notice && (
          <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400">
            {notice}
          </p>
        )}

        {(data?.unassigned.length ?? 0) > 0 && (
          <p className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-400">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {data!.unassigned.map((u) => u.name).join(', ')}{' '}
              {data!.unassigned.length === 1 ? 'has' : 'have'} no assignment, so
              they see an empty portal. Give them a college below.
            </span>
          </p>
        )}

        <div className={`rounded-xl border ${card}`}>
          <div className={`flex flex-wrap items-center gap-3 border-b p-3 ${
            isDark ? 'border-white/10' : 'border-gray-200'}`}>
            <label className="relative min-w-[240px] flex-1">
              <Search className={`pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 ${muted}`} />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by trainer, college or section"
                className={`h-9 w-full rounded-lg border pl-9 pr-3 text-sm outline-none ${
                  isDark ? 'border-white/10 bg-[#0a0a0a] text-gray-100' : 'border-gray-200 bg-white text-gray-900'}`} />
            </label>
            <span className={`text-xs ${muted}`}>
              Academic year {data?.academic_year ?? '—'}
            </span>
            <button type="button" onClick={() => setCreating(true)}
              className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3 text-sm font-medium text-white hover:bg-blue-700">
              <Plus className="h-4 w-4" /> Add staff
            </button>
          </div>

          {!data ? (
            <p className={`flex items-center justify-center gap-2 py-12 text-sm ${muted}`}>
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </p>
          ) : shown.length === 0 ? (
            <p className={`py-12 text-center text-sm ${muted}`}>
              {data.trainers.length === 0
                ? 'No trainers yet. Add one — they are BharatBuild staff, not a college\u2019s.'
                : 'Nobody matches that.'}
            </p>
          ) : (
            <ul className={`divide-y ${isDark ? 'divide-white/5' : 'divide-gray-100'}`}>
              {shown.map((t) => (
                <li key={t.id} className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-500/15 text-blue-400">
                        <GraduationCap className="h-4 w-4" />
                      </span>
                      <span>
                        <span className={`block text-sm font-medium ${ink}`}>
                          {t.name}
                        </span>
                        <span className={`block text-xs ${muted}`}>{t.email}</span>
                        <span className={`mt-0.5 block text-xs ${muted}`}>
                          {t.assignments.length === 0
                            ? 'No college — sees nothing'
                            : `${t.colleges} ${t.colleges === 1 ? 'college' : 'colleges'} · ${t.batches} batches`}
                        </span>
                      </span>
                    </div>
                    <button type="button" onClick={() => setAdding(t)}
                      className="flex h-8 items-center gap-1.5 rounded-lg border border-blue-500/40 px-2.5 text-xs font-medium text-blue-400 hover:bg-blue-500/10">
                      <Plus className="h-3.5 w-3.5" /> Assign a college
                    </button>
                  </div>

                  {t.assignments.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 pl-12">
                      {t.assignments.map((a) => (
                        <span key={a.id}
                          className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 ${
                            isDark ? 'border-white/10 bg-white/5' : 'border-gray-200 bg-gray-50'}`}>
                          <Building2 className={`h-3.5 w-3.5 ${muted}`} />
                          <span>
                            <span className={`block text-xs font-medium ${ink}`}>
                              {a.label}
                            </span>
                            <span className={`block text-[11px] ${muted}`}>
                              {a.college}
                            </span>
                          </span>
                          <span className={`rounded px-1.5 py-0.5 text-[10.5px] ${
                            a.batches === 0
                              // Zero is the one worth seeing: the assignment
                              // reaches nothing, which is almost always a typo
                              // in the branch or section.
                              ? 'bg-amber-500/15 text-amber-500'
                              : isDark ? 'bg-white/10 text-gray-300' : 'bg-gray-200 text-gray-600'}`}>
                            {a.batches} {a.batches === 1 ? 'batch' : 'batches'}
                          </span>
                          <button type="button" onClick={() => revoke(t, a)}
                            disabled={busy === a.id}
                            aria-label={`Revoke ${a.label}`}
                            title="Stop them working at this college"
                            className="text-red-400 hover:text-red-300 disabled:opacity-40">
                            {busy === a.id
                              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              : <Trash2 className="h-3.5 w-3.5" />}
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}

          <p className={`border-t px-4 py-2.5 text-xs ${muted} ${
            isDark ? 'border-white/10' : 'border-gray-200'}`}>
            An assignment is revoked, never deleted — the attendance a trainer
            marked and the documents they verified stay explainable afterwards.
          </p>
        </div>
      </div>

      {creating && (
        <NewTrainerDialog isDark={isDark}
          onClose={() => setCreating(false)}
          onSaved={async (message) => {
            setCreating(false)
            setNotice(message)
            setFailed('')
            await load()
          }} />
      )}

      {adding && data && (
        <AssignDialog isDark={isDark} trainer={adding} data={data}
          onClose={() => setAdding(null)}
          onSaved={async (message) => {
            setAdding(null)
            setNotice(message)
            setFailed('')
            await load()
          }} />
      )}
    </div>
  )
}

/**
 * Create a platform trainer.
 *
 * BharatBuild's own teaching staff, so they are created here rather than by a
 * college - a customer should not be creating accounts they do not employ.
 *
 * The account belongs to no college and therefore sees nothing until it is
 * given one below. That is the right default: an account that could see every
 * tenant the moment it was created would be the opposite.
 */
function NewTrainerDialog({ isDark, onClose, onSaved }: {
  isDark: boolean
  onClose: () => void
  onSaved: (message: string) => void | Promise<void>
}) {
  const [form, setForm] = useState({ full_name: '', email: '', phone: '' })
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  // Asked for rather than assumed: the operator may create a manager, a
  // manager may not, and hard-coding "trainer" meant the one role only the
  // operator can grant had no way to be granted at all.
  const [roles, setRoles] = useState<{ key: string; label: string }[]>([])
  const [role, setRole] = useState('trainer')

  useEffect(() => {
    let live = true
    apiClient.get<{ roles: { key: string; label: string }[] }>('/admin/staff/options')
      .then((data) => {
        if (!live) return
        // Only the platform's own staff belong on this screen; a college
        // administrator is created from the college's own row.
        const mine = (data.roles ?? []).filter(
          (r) => r.key === 'trainer' || r.key === 'manager')
        setRoles(mine)
        setRole(mine.some((r) => r.key === 'trainer') ? 'trainer' : mine[0]?.key ?? '')
      })
      .catch(() => { if (live) setRoles([{ key: 'trainer', label: 'Trainer' }]) })
    return () => { live = false }
  }, [])

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])

  const submit = async () => {
    setBusy(true)
    setProblem('')
    try {
      const result = await apiClient.post<{ message: string }>('/admin/staff', {
        ...form, role,
      })
      await onSaved(result.message)
    } catch (err: any) {
      setProblem(err?.response?.data?.detail ?? 'That account could not be created.')
      setBusy(false)
    }
  }

  const field = isDark
    ? 'border-white/10 bg-[#0a0a0a] text-gray-100 placeholder:text-gray-600'
    : 'border-gray-200 bg-white text-gray-900 placeholder:text-gray-400'
  const label = isDark ? 'text-gray-400' : 'text-gray-500'
  const ready = form.email.includes('@') && form.full_name.trim().length > 1

  return (
    <div role="dialog" aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className={`flex w-full max-w-[520px] flex-col rounded-xl border ${
        isDark ? 'border-white/10 bg-[#141414]' : 'border-gray-200 bg-white'}`}>
        <div className={`flex items-center justify-between border-b px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <h2 className={`text-sm font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
            Add platform staff
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className={`flex h-7 w-7 items-center justify-center rounded ${
              isDark ? 'text-gray-400 hover:bg-white/5' : 'text-gray-500 hover:bg-gray-100'}`}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-2.5 px-4 py-3">
          {problem && (
            <p className="flex items-start gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {problem}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Full name *</span>
              <input value={form.full_name} placeholder="Dr Anitha Rao"
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Email *</span>
              <input value={form.email} type="email" placeholder="anitha@bharatbuild.ai"
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Role *</span>
              <select value={role} onChange={(e) => setRole(e.target.value)}
                disabled={roles.length <= 1}
                className={`h-9 rounded-lg border px-2 text-sm outline-none disabled:opacity-60 ${field}`}>
                {roles.map((r) => (
                  <option key={r.key} value={r.key}>{r.label}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Phone</span>
              <input value={form.phone}
                onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
          </div>

          <p className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${
            isDark ? 'border-blue-500/30 bg-blue-500/10 text-blue-300' : 'border-blue-200 bg-blue-50 text-blue-800'}`}>
            <Users className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              {role === 'manager'
                ? 'A manager runs every college and the trainers across them, but not billing, plans or API keys. They need no assignment.'
                : 'BharatBuild staff, not a college\u2019s. They belong to no college and see nothing until you assign them one — do that next.'}
              {' '}No password is set here; they are emailed a link to choose one.
            </span>
          </p>
        </div>

        <div className={`flex items-center justify-end gap-2 border-t px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <button type="button" onClick={onClose} disabled={busy}
            className={`h-9 rounded-lg border px-3.5 text-sm ${
              isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={!ready || busy}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            Create and invite
          </button>
        </div>
      </div>
    </div>
  )
}

function AssignDialog({ isDark, trainer, data, onClose, onSaved }: {
  isDark: boolean
  trainer: Trainer
  data: Payload
  onClose: () => void
  onSaved: (message: string) => void | Promise<void>
}) {
  const [collegeId, setCollegeId] = useState(data.colleges[0]?.id ?? '')
  const [department, setDepartment] = useState('')
  const [section, setSection] = useState('')
  // Folded away: a trainer normally takes the whole college, and naming each
  // branch is data entry that goes stale the moment the college adds one.
  const [narrow, setNarrow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])

  // Only branches and sections that actually have batches. A free-text box
  // would let a typo through, and the assignment would silently reach nothing.
  const branches = useMemo(
    () => Object.keys(data.structure[collegeId] ?? {}).sort(),
    [data.structure, collegeId])
  const sections = useMemo(
    () => (data.structure[collegeId]?.[department] ?? []),
    [data.structure, collegeId, department])

  useEffect(() => {
    setDepartment((d) => (branches.includes(d) ? d : branches[0] ?? ''))
  }, [branches])
  useEffect(() => { setSection('') }, [department, collegeId])
  useEffect(() => { setNarrow(false) }, [collegeId])

  const submit = async () => {
    setBusy(true)
    setProblem('')
    try {
      await apiClient.post('/admin/trainer-assignments', {
        trainer_id: trainer.id,
        college_id: collegeId,
        // Null unless deliberately narrowed - that is what makes the
        // assignment cover the whole college, branches added later included.
        department: narrow ? department : null,
        section: narrow ? (section || null) : null,
        academic_year: data.academic_year,
      })
      const college = data.colleges.find((c) => c.id === collegeId)?.name ?? ''
      const where = !narrow
        ? college
        : `${section ? department + '-' + section : 'all of ' + department} at ${college}`
      await onSaved(`${trainer.name} now works at ${where}.`)
    } catch (err: any) {
      setProblem(err?.response?.data?.detail ?? 'That could not be assigned.')
      setBusy(false)
    }
  }

  const field = isDark
    ? 'border-white/10 bg-[#0a0a0a] text-gray-100'
    : 'border-gray-200 bg-white text-gray-900'
  const label = isDark ? 'text-gray-400' : 'text-gray-500'

  return (
    <div role="dialog" aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className={`flex w-full max-w-[520px] flex-col rounded-xl border ${
        isDark ? 'border-white/10 bg-[#141414]' : 'border-gray-200 bg-white'}`}>
        <div className={`flex items-center justify-between border-b px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <h2 className={`text-sm font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
            Assign a college to {trainer.name}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className={`flex h-7 w-7 items-center justify-center rounded ${
              isDark ? 'text-gray-400 hover:bg-white/5' : 'text-gray-500 hover:bg-gray-100'}`}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-2.5 px-4 py-3">
          {problem && (
            <p className="flex items-start gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {problem}
            </p>
          )}

          <label className="flex flex-col gap-1">
            <span className={`text-xs ${label}`}>College</span>
            <select value={collegeId} onChange={(e) => setCollegeId(e.target.value)}
              className={`h-9 rounded-lg border px-2 text-sm outline-none ${field}`}>
              {data.colleges.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>

          <label className="flex items-start gap-2">
            <input type="checkbox" className="mt-0.5" checked={narrow}
              onChange={(e) => setNarrow(e.target.checked)} />
            <span className={`text-xs ${label}`}>
              Limit to one branch or section
              <span className="block text-[11px] opacity-80">
                Rarely needed. Without it they teach the whole college,
                including branches and sections added later.
              </span>
            </span>
          </label>

          {narrow && (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1">
                <span className={`text-xs ${label}`}>Branch</span>
                <select value={department} onChange={(e) => setDepartment(e.target.value)}
                  disabled={branches.length === 0}
                  className={`h-9 rounded-lg border px-2 text-sm outline-none disabled:opacity-50 ${field}`}>
                  {branches.length === 0 && <option value="">No branches here</option>}
                  {branches.map((b) => <option key={b} value={b}>{b}</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className={`text-xs ${label}`}>Section</span>
                <select value={section} onChange={(e) => setSection(e.target.value)}
                  className={`h-9 rounded-lg border px-2 text-sm outline-none ${field}`}>
                  <option value="">Whole branch</option>
                  {sections.map((sec) => <option key={sec} value={sec}>{sec}</option>)}
                </select>
              </label>
            </div>
          )}

          <p className={`rounded-lg border px-3 py-2 text-xs ${
            isDark ? 'border-blue-500/30 bg-blue-500/10 text-blue-300' : 'border-blue-200 bg-blue-50 text-blue-800'}`}>
            {!narrow
              ? 'They will see every branch and section at this college - its batches, students, attendance and documents - and can import batches for it.'
              : section
                ? `They will see only ${department}-${section} at this college.`
                : `They will see every section of ${department || 'this branch'} at this college.`}
          </p>
        </div>

        <div className={`flex items-center justify-end gap-2 border-t px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <button type="button" onClick={onClose} disabled={busy}
            className={`h-9 rounded-lg border px-3.5 text-sm ${
              isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            Cancel
          </button>
          <button type="button" onClick={submit}
            disabled={busy || !collegeId || !department}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            Assign
          </button>
        </div>
      </div>
    </div>
  )
}
