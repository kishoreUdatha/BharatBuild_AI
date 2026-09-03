'use client'

import { useEffect, useMemo, useState } from 'react'
import { Loader2, Plus, X } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { errorMessage } from '@/lib/faculty-api'
import { cn } from '@/lib/utils'

interface Options {
  academic_year: string
  departments: { code: string; name: string; sections: { year: string; semester: string; name: string }[] }[]
  project_types: string[]
  guides: { id: string; name: string }[]
  defaults: { team_size: number; project_fee: number }
  unassigned_students?: number
}

const FIELD = 'h-8 w-full rounded-lg border border-[#DDE0EE] px-2 text-[12px] outline-none focus:border-[#4F46E5]'
const LABEL = 'mb-1 block text-[10.5px] text-[#8A8FA8]'

/**
 * Forms empty batches for a section.
 *
 * The cohort choices come from the academic structure rather than free text, so
 * a batch cannot be created against a section that no screen can show. The
 * batch starts empty: students join with the code it returns.
 */
export function NewBatchForm({ onClose, onCreated }: {
  onClose: () => void
  onCreated: (message: string) => void
}) {
  const [options, setOptions] = useState<Options | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [created, setCreated] = useState<{ batch_code: string; join_code: string }[]>([])

  const [form, setForm] = useState({
    department: '', cohort: '', project_type: 'Major Project',
    guide_id: '', team_size: 4, project_fee: 15000, count: 1,
  })

  const loadOptions = async (department?: string, cohort?: string) => {
    const [year, , section] = (cohort ?? '').split('|')
    try {
      const params: Record<string, string> = {}
      if (department && year && section) Object.assign(params, { department, year, section })
      const data = await apiClient.get<Options>('/faculty/registrations/batch-options', { params })
      setOptions(data)
      setForm((f) => ({
        ...f,
        department: f.department || data.departments[0]?.code || '',
        team_size: f.team_size || data.defaults.team_size,
        project_fee: f.project_fee || data.defaults.project_fee,
      }))
    } catch (err: any) {
      setError(errorMessage(err, 'Could not load the form options.'))
    }
  }

  useEffect(() => { loadOptions() }, [])
  // Re-fetch once a cohort is chosen so the unassigned-student count is real.
  useEffect(() => {
    if (form.department && form.cohort) loadOptions(form.department, form.cohort)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.department, form.cohort])

  const sections = useMemo(
    () => options?.departments.find((d) => d.code === form.department)?.sections ?? [],
    [options, form.department]
  )

  const submit = async () => {
    const [year, semester, section] = form.cohort.split('|')
    if (!form.department || !year) { setError('Choose a department and a section.'); return }
    setBusy(true)
    setError('')
    try {
      const result = await apiClient.post<{ created: { batch_code: string; join_code: string }[] }>(
        '/faculty/registrations/batches',
        {
          department: form.department, year, semester, section,
          project_type: form.project_type,
          guide_id: form.guide_id || undefined,
          team_size: Number(form.team_size),
          project_fee: Number(form.project_fee),
          count: Number(form.count),
        }
      )
      setCreated(result.created)
      onCreated(`${result.created.length} batch${result.created.length === 1 ? '' : 'es'} created.`)
    } catch (err: any) {
      setError(errorMessage(err, 'Those batches could not be created.'))
    } finally {
      setBusy(false)
    }
  }

  if (!options) {
    return (
      <div className="mb-3 flex items-center gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-3 text-[12px] text-[#3A3F58]">
        <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> Loading options…
      </div>
    )
  }

  const share = Math.floor(Number(form.project_fee) / Math.max(1, Number(form.team_size)))

  return (
    <div className="mb-3 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-3">
      <div className="mb-2.5 flex items-center justify-between">
        <p className="text-[12.5px] font-semibold text-[#1B1B3A]">
          Form new batches &mdash; {options.academic_year}
        </p>
        <button type="button" onClick={onClose} aria-label="Close"
          className="text-[#5A5F7A] hover:text-[#1B1B3A]"><X className="h-4 w-4" /></button>
      </div>

      {created.length > 0 ? (
        <>
          <p className="mb-2 text-[12px] text-[#15803D]">
            Created. Give the join code to the team &mdash; that is what students type.
          </p>
          <ul className="mb-2.5 space-y-1">
            {created.map((b) => (
              <li key={b.batch_code}
                className="flex items-center justify-between rounded-md border border-[#DDE0EE] bg-white px-2.5 py-1.5">
                <span className="text-[12px] font-medium text-[#1B1B3A]">{b.batch_code}</span>
                <span className="font-mono text-[12px] text-[#4F46E5]">{b.join_code}</span>
              </li>
            ))}
          </ul>
          <button type="button" onClick={() => { setCreated([]); setForm((f) => ({ ...f, count: 1 })) }}
            className="rounded-lg border border-[#C7BDF5] bg-white px-3 py-1.5 text-[12px] font-medium text-[#4F46E5]">
            Form more
          </button>
        </>
      ) : (
        <>
          <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
            <label>
              <span className={LABEL}>Department</span>
              <select className={FIELD} value={form.department}
                onChange={(e) => setForm((f) => ({ ...f, department: e.target.value, cohort: '' }))}>
                {options.departments.map((d) => (
                  <option key={d.code} value={d.code}>{d.code} &mdash; {d.name}</option>
                ))}
              </select>
            </label>

            <label>
              <span className={LABEL}>Year, semester and section</span>
              <select className={FIELD} value={form.cohort}
                onChange={(e) => setForm((f) => ({ ...f, cohort: e.target.value }))}>
                <option value="">Choose a section…</option>
                {sections.map((s) => (
                  <option key={`${s.year}|${s.semester}|${s.name}`}
                    value={`${s.year}|${s.semester}|${s.name}`}>
                    {s.year} &middot; Sem {s.semester} &middot; Section {s.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span className={LABEL}>Project type</span>
              <select className={FIELD} value={form.project_type}
                onChange={(e) => setForm((f) => ({ ...f, project_type: e.target.value }))}>
                {options.project_types.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>

            <label>
              <span className={LABEL}>Faculty guide</span>
              <select className={FIELD} value={form.guide_id}
                onChange={(e) => setForm((f) => ({ ...f, guide_id: e.target.value }))}>
                <option value="">Assign later</option>
                {options.guides.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
              {/* A batch with no guide has nobody entitled to act on it - not even
                  the person creating it. Saying so here is cheaper than a
                  coordinator finding every button greyed out later. */}
              {!form.guide_id && (
                <span className="mt-1 block text-[10px] leading-snug text-[#B45309]">
                  Until a guide is assigned, nobody can verify documents, review
                  submissions or edit project details on these batches.
                </span>
              )}
            </label>

            <label>
              <span className={LABEL}>Team size</span>
              <input type="number" min={2} max={8} className={FIELD} value={form.team_size}
                onChange={(e) => setForm((f) => ({ ...f, team_size: Number(e.target.value) }))} />
            </label>

            <label>
              <span className={LABEL}>Project fee (&#8377;)</span>
              <input type="number" min={0} className={FIELD} value={form.project_fee}
                onChange={(e) => setForm((f) => ({ ...f, project_fee: Number(e.target.value) }))} />
            </label>

            <label>
              <span className={LABEL}>How many batches</span>
              <input type="number" min={1} max={20} className={FIELD} value={form.count}
                onChange={(e) => setForm((f) => ({ ...f, count: Number(e.target.value) }))} />
            </label>

            <div className="self-end text-[11px] text-[#5A5F7A]">
              <p>Each student pays <span className="font-semibold text-[#1B1B3A]">&#8377;{share.toLocaleString('en-IN')}</span></p>
              {options.unassigned_students != null && (
                <p className="mt-0.5">
                  {options.unassigned_students} student{options.unassigned_students === 1 ? '' : 's'}
                  {' '}in this section still need a batch
                  {options.unassigned_students > 0 && (
                    <span className="text-[#8A8FA8]">
                      {' '}(~{Math.ceil(options.unassigned_students / Math.max(1, form.team_size))} needed)
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>

          {error && <p className="mt-2 text-[11.5px] text-[#DC2626]">{error}</p>}

          <div className="mt-2.5 flex items-center gap-2">
            <button type="button" onClick={submit} disabled={busy || !form.cohort}
              title={form.cohort ? undefined : 'Choose a section first'}
              className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Form {form.count} batch{Number(form.count) === 1 ? '' : 'es'}
            </button>
            <button type="button" onClick={onClose}
              className="rounded-lg border border-[#DDE0EE] bg-white px-3.5 py-2 text-[12px] text-[#3A3F58]">
              Cancel
            </button>
            <p className="text-[10.5px] text-[#8A8FA8]">
              Batches start empty. Students join with the code, or you can assign them from Student
              Registrations.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
