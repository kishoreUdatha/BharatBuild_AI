'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertCircle, CalendarPlus, Check, Loader2, X } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import {
  fetchCohortPreview,
  fetchReviewOptions,
  reviewError,
  scheduleRound,
  tomorrow,
  type CohortPreview,
  type ReviewOptions,
} from '@/lib/reviews-api'
import { cn } from '@/lib/utils'

interface CohortOptions {
  departments: {
    code: string
    name: string
    sections: { year: string; semester: string; name: string }[]
  }[]
}

const FIELD = 'h-8 w-full rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]'
const LABEL = 'mb-1 block text-[10.5px] text-[#8A8FA8]'

/**
 * Booking a round of reviews.
 *
 * A coordinator books a section, not a batch: one review per team, back to
 * back from a start time. The preview shows exactly who is covered and who is
 * already booked before anything is written, because a round that quietly
 * covers fewer teams than expected is worse than one that refuses.
 */
export function ScheduleRound({ onClose, onBooked }: {
  onClose: () => void
  onBooked: (message: string) => void
}) {
  const [options, setOptions] = useState<ReviewOptions | null>(null)
  const [cohorts, setCohorts] = useState<CohortOptions | null>(null)
  const [preview, setPreview] = useState<CohortPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    department: '',
    cohort: '',
    review_type: '',
    date: tomorrow(),
    start_time: '10:00',
    slot_minutes: 20,
    reviewer_id: '',
  })

  useEffect(() => {
    Promise.all([
      fetchReviewOptions(),
      apiClient.get<CohortOptions>('/faculty/registrations/batch-options'),
    ]).then(([reviewOptions, cohortOptions]) => {
      setOptions(reviewOptions)
      setCohorts(cohortOptions)
      setForm((f) => ({
        ...f,
        department: f.department || cohortOptions.departments[0]?.code || '',
        review_type: f.review_type || reviewOptions.review_types[0] || '',
        start_time: reviewOptions.defaults.start_time,
        slot_minutes: reviewOptions.defaults.slot_minutes,
      }))
    }).catch((err) => setError(reviewError(err, 'Could not load the booking options.')))
  }, [])

  const sections = useMemo(() => {
    const dept = cohorts?.departments.find((d) => d.code === form.department)
    if (!dept) return []
    const seen = new Set<string>()
    return dept.sections.filter((s) => {
      const key = `${s.year}|${s.name}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [cohorts, form.department])

  // Changing the section and the review type fires two lookups. Without a
  // sequence guard the slower one can land last and show counts for a cohort
  // nobody is looking at any more - which is how a preview comes to disagree
  // with what the booking actually does.
  const request = useRef(0)

  const loadPreview = useCallback(async () => {
    const [year, section] = form.cohort.split('|')
    if (!form.department || !section || !form.review_type) { setPreview(null); return }
    const ticket = ++request.current
    try {
      const result = await fetchCohortPreview({
        department: form.department, year, section, review_type: form.review_type,
      })
      if (ticket !== request.current) return
      setPreview(result)
      setError('')
    } catch (err) {
      if (ticket !== request.current) return
      setError(reviewError(err, 'Could not read that cohort.'))
      setPreview(null)
    }
  }, [form.department, form.cohort, form.review_type])

  useEffect(() => { loadPreview() }, [loadPreview])

  const book = async () => {
    const [year, section] = form.cohort.split('|')
    setBusy(true); setError('')
    try {
      const result = await scheduleRound({
        department: form.department, year, section,
        review_type: form.review_type, date: form.date,
        start_time: form.start_time, slot_minutes: Number(form.slot_minutes),
        reviewer_id: form.reviewer_id || undefined,
      })
      onBooked(result.message)
      loadPreview()
    } catch (err) {
      setError(reviewError(err, 'Those reviews could not be booked.'))
    } finally {
      setBusy(false)
    }
  }

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  // The window the round will occupy, so a coordinator sees it finishes at a
  // sane hour before booking rather than after.
  const window = useMemo(() => {
    if (!preview?.to_book || !form.start_time) return null
    const [h, m] = form.start_time.split(':').map(Number)
    if (Number.isNaN(h) || Number.isNaN(m)) return null
    const total = preview.to_book * Number(form.slot_minutes)
    const end = new Date(2000, 0, 1, h, m + total)
    const pad = (n: number) => String(n).padStart(2, '0')
    return {
      end: `${pad(end.getHours())}:${pad(end.getMinutes())}`,
      hours: (total / 60).toFixed(total % 60 === 0 ? 0 : 1),
      spillsOvernight: end.getDate() !== 1,
    }
  }, [preview, form.start_time, form.slot_minutes])

  if (!options || !cohorts) {
    return (
      <div className="mb-3 flex items-center gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-3 text-[12px] text-[#3A3F58]">
        <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> Loading options…
      </div>
    )
  }

  return (
    <section className="rounded-xl border border-[#C7BDF5] bg-[#F5F3FF] p-3">
      <div className="mb-2.5 flex items-center justify-between">
        <p className="text-[12.5px] font-semibold text-[#1B1B3A]">Schedule a round of reviews</p>
        <button type="button" onClick={onClose} aria-label="Close"
          className="text-[#5A5F7A] hover:text-[#1B1B3A]"><X className="h-4 w-4" /></button>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-4">
        <label>
          <span className={LABEL}>Department</span>
          <select className={FIELD} value={form.department}
            onChange={(e) => { set('department', e.target.value); set('cohort', '') }}>
            {cohorts.departments.map((d) => (
              <option key={d.code} value={d.code}>{d.code} &mdash; {d.name}</option>
            ))}
          </select>
        </label>

        <label>
          <span className={LABEL}>Year and section</span>
          <select className={FIELD} value={form.cohort}
            onChange={(e) => set('cohort', e.target.value)}>
            <option value="">Choose a section&hellip;</option>
            {sections.map((s) => (
              <option key={`${s.year}|${s.name}`} value={`${s.year}|${s.name}`}>
                {s.year} &middot; Section {s.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className={LABEL}>Review</span>
          <select className={FIELD} value={form.review_type}
            onChange={(e) => set('review_type', e.target.value)}>
            {options.review_types.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>

        <label>
          <span className={LABEL}>Reviewer</span>
          <select className={FIELD} value={form.reviewer_id}
            onChange={(e) => set('reviewer_id', e.target.value)}>
            <option value="">Each batch&rsquo;s own guide</option>
            {options.reviewers.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </label>

        <label>
          <span className={LABEL}>Date</span>
          <input type="date" className={FIELD} value={form.date}
            onChange={(e) => set('date', e.target.value)} />
        </label>

        <label>
          <span className={LABEL}>Starts at</span>
          <input type="time" className={FIELD} value={form.start_time}
            onChange={(e) => set('start_time', e.target.value)} />
        </label>

        <label>
          <span className={LABEL}>Minutes per batch</span>
          <input type="number" className={FIELD}
            min={options.limits.min_slot_minutes} max={options.limits.max_slot_minutes}
            value={form.slot_minutes}
            onChange={(e) => set('slot_minutes', Number(e.target.value))} />
        </label>

        <div className="self-end text-[11px] leading-snug text-[#5A5F7A]">
          {preview ? (
            <>
              <p>
                <span className="font-semibold text-[#1B1B3A]">{preview.to_book}</span> to book
                {preview.total - preview.to_book > 0 && (
                  <span className="text-[#8A8FA8]">
                    {' '}&middot; {preview.total - preview.to_book} already scheduled
                  </span>
                )}
              </p>
              {window && (
                <p className={cn('mt-0.5', window.spillsOvernight && 'text-[#B45309]')}>
                  {form.start_time}&ndash;{window.end} ({window.hours}h)
                  {window.spillsOvernight && ' — runs past midnight'}
                </p>
              )}
            </>
          ) : (
            <p className="text-[#8A8FA8]">Choose a section to see who is covered.</p>
          )}
        </div>
      </div>

      {error && (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-2 text-[11.5px] text-[#B91C1C]">
          <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}

      {preview && preview.total > 0 && (
        <ul className="mt-2.5 flex max-h-[132px] flex-wrap gap-1.5 overflow-y-auto rounded-lg bg-white p-2">
          {preview.batches.map((b) => (
            <li key={b.batch_code}
              title={b.already_scheduled
                ? `Already has a ${preview.review_type} scheduled`
                : (b.title ?? 'Untitled')}
              className={cn('flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10.5px]',
                b.already_scheduled
                  ? 'border-[#EEF0F7] text-[#9CA3AF] line-through'
                  : 'border-[#C7BDF5] text-[#4F46E5]')}>
              {b.already_scheduled && <Check className="h-2.5 w-2.5" />}
              {b.batch_code}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        <button type="button" onClick={book}
          disabled={busy || !form.cohort || !preview || preview.to_book === 0}
          className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
            : <CalendarPlus className="h-3.5 w-3.5" />}
          Book {preview?.to_book ?? 0} review{preview?.to_book === 1 ? '' : 's'}
        </button>
        <button type="button" onClick={onClose}
          className="rounded-lg border border-[#DDE0EE] bg-white px-3.5 py-2 text-[12px] text-[#3A3F58]">
          Cancel
        </button>
        <p className="text-[10.5px] text-[#8A8FA8]">
          Batches already booked for this review are skipped, not double-booked. A reviewer
          who is busy at one of these slots is refused.
        </p>
      </div>
    </section>
  )
}
