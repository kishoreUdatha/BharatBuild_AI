'use client'

import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Check, Loader2, Plus, Save, Send, X } from 'lucide-react'
import {
  projectError,
  type MethodologyInput,
  type ObjectiveInput,
  type ProjectDetailsForm,
  type ProjectDetailsPayload,
  type TechnologyInput,
} from '@/lib/project-details-api'
import { cn } from '@/lib/utils'

/**
 * The project details form, used by both portals.
 *
 * A team writes it from the student portal and a guide corrects it from the
 * faculty portal. One component, because two copies of a nine-section form
 * drift the moment either side gains a field - the same reason the server
 * keeps one service behind both routes.
 *
 * The eight completeness checks are never computed here: they arrive from the
 * server after every save, so this panel and the gate that refuses a
 * submission can never disagree about what is missing.
 */

export interface EditorProps {
  data: ProjectDetailsForm
  /** Accent for buttons and focus rings - indigo for faculty, blue for students. */
  accent?: string
  onSave: (payload: ProjectDetailsPayload) => Promise<ProjectDetailsForm>
  /** Absent for faculty, who review submissions rather than making them. */
  onSubmit?: (note: string) => Promise<void>
  onDirtyChange?: (dirty: boolean) => void
}

type Draft = {
  title: string
  domain: string
  project_type: string
  keywords: string[]
  problem_statement: string
  abstract: string
  objectives: ObjectiveInput[]
  methodology: MethodologyInput[]
  outcomes: string[]
  in_scope: string[]
  out_of_scope: string[]
  deliverables: string[]
  technologies: TechnologyInput[]
  start_date: string
  target_completion: string
  weekly_effort_hours: string
}

const toDraft = (d: ProjectDetailsForm): Draft => ({
  title: d.title ?? '',
  domain: d.domain ?? '',
  project_type: d.project_type ?? d.options.project_types[0] ?? '',
  keywords: [...d.keywords],
  problem_statement: d.problem_statement ?? '',
  abstract: d.abstract ?? '',
  objectives: d.objectives.length ? d.objectives.map((o) => ({ ...o }))
    : [{ text: '', status: 'pending' }],
  methodology: d.methodology.length ? d.methodology.map((m) => ({ ...m }))
    : [{ title: '', description: '' }],
  outcomes: [...d.outcomes],
  in_scope: [...d.in_scope],
  out_of_scope: [...d.out_of_scope],
  deliverables: [...d.deliverables],
  technologies: d.technologies.map((t) => ({ ...t })),
  start_date: d.start_date ? String(d.start_date).slice(0, 10) : '',
  target_completion: d.target_completion ? String(d.target_completion).slice(0, 10) : '',
  weekly_effort_hours: d.weekly_effort_hours == null ? '' : String(d.weekly_effort_hours),
})

/** Blank rows are how an empty slot looks while typing; they never get sent. */
const clean = (draft: Draft): ProjectDetailsPayload => ({
  title: draft.title.trim() || null,
  domain: draft.domain.trim() || null,
  project_type: draft.project_type,
  keywords: draft.keywords.map((k) => k.trim()).filter(Boolean),
  problem_statement: draft.problem_statement.trim() || null,
  abstract: draft.abstract.trim() || null,
  objectives: draft.objectives
    .filter((o) => o.text.trim())
    .map((o) => ({ text: o.text.trim(), status: o.status })),
  methodology: draft.methodology
    .filter((m) => m.title.trim())
    .map((m) => ({ title: m.title.trim(), description: (m.description || '').trim() || null })),
  outcomes: draft.outcomes.map((s) => s.trim()).filter(Boolean),
  in_scope: draft.in_scope.map((s) => s.trim()).filter(Boolean),
  out_of_scope: draft.out_of_scope.map((s) => s.trim()).filter(Boolean),
  deliverables: draft.deliverables.map((s) => s.trim()).filter(Boolean),
  technologies: draft.technologies
    .filter((t) => t.name.trim())
    .map((t) => ({ layer: t.layer.trim() || 'Other', name: t.name.trim() })),
  start_date: draft.start_date || null,
  target_completion: draft.target_completion || null,
  weekly_effort_hours: draft.weekly_effort_hours === '' ? null
    : Number(draft.weekly_effort_hours),
})

const LABEL = 'mb-1 block text-[11px] font-medium text-[#5A5F7A]'
const INPUT = 'w-full rounded-lg border border-[#DDE0EE] bg-white px-2.5 py-1.5 text-[12.5px] text-[#1B1B3A] outline-none focus:border-current disabled:bg-[#F7F8FC] disabled:text-[#8A8FA8]'

export function ProjectDetailsEditor({
  data, accent = '#4F46E5', onSave, onSubmit, onDirtyChange,
}: EditorProps) {
  const [server, setServer] = useState(data)
  const [draft, setDraft] = useState<Draft>(() => toDraft(data))
  const [saving, setSaving] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [note, setNote] = useState('')

  useEffect(() => { setServer(data); setDraft(toDraft(data)) }, [data])

  const baseline = useMemo(() => JSON.stringify(clean(toDraft(server))), [server])
  const dirty = JSON.stringify(clean(draft)) !== baseline
  useEffect(() => { onDirtyChange?.(dirty) }, [dirty, onDirtyChange])

  const locked = server.locked
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((d) => ({ ...d, [key]: value }))

  const save = async () => {
    setSaving(true); setError(''); setNotice('')
    try {
      const next = await onSave(clean(draft))
      setServer(next)
      setDraft(toDraft(next))
      const changed = next.changed_fields ?? []
      setNotice(changed.length
        ? `Saved. Updated ${changed.join(', ')}.`
        : 'Saved. Nothing had changed.')
    } catch (err) {
      setError(projectError(err, 'Those details could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  const submit = async () => {
    if (!onSubmit) return
    setSending(true); setError(''); setNotice('')
    try {
      await onSubmit(note.trim())
      setNote('')
    } catch (err) {
      setError(projectError(err, 'That could not be submitted.'))
    } finally {
      setSending(false)
    }
  }

  const unmet = server.checklist.filter((c) => !c.passed)

  return (
    <div className="space-y-2.5" style={{ color: accent }}>
      {locked && (
        <Banner tone="lock" text={server.locked_reason ?? 'These details cannot be changed now.'} />
      )}
      {error && <Banner tone="error" text={error} />}
      {notice && !error && <Banner tone="ok" text={notice} />}

      <div className="grid gap-2.5 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-2.5">
          <Card title="The project">
            <div className="grid gap-2.5 sm:grid-cols-2">
              <label className="sm:col-span-2">
                <span className={LABEL}>Project title</span>
                <input className={INPUT} disabled={locked} value={draft.title}
                  placeholder="What are you building?"
                  onChange={(e) => set('title', e.target.value)} />
              </label>
              <label>
                <span className={LABEL}>Domain</span>
                <input className={INPUT} disabled={locked} value={draft.domain}
                  placeholder="Machine Learning, IoT, Networking…"
                  onChange={(e) => set('domain', e.target.value)} />
              </label>
              <label>
                <span className={LABEL}>Project type</span>
                <select className={INPUT} disabled={locked} value={draft.project_type}
                  onChange={(e) => set('project_type', e.target.value)}>
                  {server.options.project_types.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <div className="sm:col-span-2">
                <span className={LABEL}>Keywords</span>
                <ChipInput values={draft.keywords} disabled={locked} accent={accent}
                  max={server.options.limits.keywords}
                  placeholder="Type a keyword and press Enter"
                  onChange={(v) => set('keywords', v)} />
              </div>
              <label className="sm:col-span-2">
                <span className={LABEL}>Problem statement</span>
                <textarea className={cn(INPUT, 'min-h-[70px] resize-y')} disabled={locked}
                  value={draft.problem_statement}
                  placeholder="What is wrong today, and for whom?"
                  onChange={(e) => set('problem_statement', e.target.value)} />
              </label>
              <label className="sm:col-span-2">
                <span className={LABEL}>
                  Abstract
                  <span className="ml-1.5 font-normal text-[#8A8FA8]">
                    {draft.abstract.trim().length} characters, 120 needed
                  </span>
                </span>
                <textarea className={cn(INPUT, 'min-h-[120px] resize-y')} disabled={locked}
                  value={draft.abstract}
                  placeholder="What you are building, how, and how you will know it worked."
                  onChange={(e) => set('abstract', e.target.value)} />
              </label>
            </div>
          </Card>

          <Card title="Objectives" hint="At least three, each one something you can show you met.">
            <RowList
              rows={draft.objectives} disabled={locked} accent={accent}
              max={server.options.limits.objectives}
              blank={() => ({ text: '', status: 'pending' })}
              onChange={(rows) => set('objectives', rows)}
              render={(row, update) => (
                <>
                  <input className={INPUT} disabled={locked} value={row.text}
                    placeholder="Objective" onChange={(e) => update({ ...row, text: e.target.value })} />
                  <select className={cn(INPUT, 'w-[130px] shrink-0')} disabled={locked}
                    value={row.status} onChange={(e) => update({ ...row, status: e.target.value })}>
                    {server.options.objective_statuses.map((s) => (
                      <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                  </select>
                </>
              )} />
          </Card>

          <Card title="Methodology" hint="The steps you will work through, in order.">
            <RowList
              rows={draft.methodology} disabled={locked} accent={accent}
              max={server.options.limits.methodology}
              blank={() => ({ title: '', description: '' })}
              onChange={(rows) => set('methodology', rows)}
              render={(row, update) => (
                <div className="flex flex-1 flex-col gap-1.5 sm:flex-row">
                  <input className={cn(INPUT, 'sm:w-[190px] sm:shrink-0')} disabled={locked}
                    value={row.title} placeholder="Step"
                    onChange={(e) => update({ ...row, title: e.target.value })} />
                  <input className={INPUT} disabled={locked} value={row.description ?? ''}
                    placeholder="What happens in this step"
                    onChange={(e) => update({ ...row, description: e.target.value })} />
                </div>
              )} />
          </Card>

          <div className="grid gap-2.5 md:grid-cols-2">
            <Card title="Expected outcomes" hint="What exists at the end that did not before.">
              <ListInput values={draft.outcomes} disabled={locked} accent={accent}
                max={server.options.limits.scope} placeholder="Add an outcome"
                onChange={(v) => set('outcomes', v)} />
            </Card>
            <Card title="Deliverables" hint="The artefacts you will hand over.">
              <ListInput values={draft.deliverables} disabled={locked} accent={accent}
                max={server.options.limits.scope} placeholder="Add a deliverable"
                onChange={(v) => set('deliverables', v)} />
            </Card>
            <Card title="In scope">
              <ListInput values={draft.in_scope} disabled={locked} accent={accent}
                max={server.options.limits.scope} placeholder="Add something in scope"
                onChange={(v) => set('in_scope', v)} />
            </Card>
            <Card title="Out of scope" hint="Naming these now prevents an argument later.">
              <ListInput values={draft.out_of_scope} disabled={locked} accent={accent}
                max={server.options.limits.scope} placeholder="Add something out of scope"
                onChange={(v) => set('out_of_scope', v)} />
            </Card>
          </div>

          <Card title="Technology stack">
            <RowList
              rows={draft.technologies} disabled={locked} accent={accent}
              max={server.options.limits.technologies}
              blank={() => ({ layer: server.options.layers[0] ?? 'Other', name: '' })}
              onChange={(rows) => set('technologies', rows)}
              addLabel="Add a technology"
              render={(row, update) => (
                <>
                  <select className={cn(INPUT, 'w-[150px] shrink-0')} disabled={locked}
                    value={row.layer} onChange={(e) => update({ ...row, layer: e.target.value })}>
                    {[...new Set([...server.options.layers, row.layer, 'Other'])]
                      .filter(Boolean)
                      .map((l) => <option key={l} value={l}>{l}</option>)}
                  </select>
                  <input className={INPUT} disabled={locked} value={row.name}
                    placeholder="PyTorch, FastAPI, PostgreSQL…"
                    onChange={(e) => update({ ...row, name: e.target.value })} />
                </>
              )} />
          </Card>

          <Card title="Duration">
            <div className="grid gap-2.5 sm:grid-cols-3">
              <label>
                <span className={LABEL}>Start date</span>
                <input type="date" className={INPUT} disabled={locked} value={draft.start_date}
                  onChange={(e) => set('start_date', e.target.value)} />
              </label>
              <label>
                <span className={LABEL}>Target completion</span>
                <input type="date" className={INPUT} disabled={locked}
                  value={draft.target_completion}
                  onChange={(e) => set('target_completion', e.target.value)} />
              </label>
              <label>
                <span className={LABEL}>Weekly effort (hours a student)</span>
                <input type="number" min={1} max={60} className={INPUT} disabled={locked}
                  value={draft.weekly_effort_hours}
                  onChange={(e) => set('weekly_effort_hours', e.target.value)} />
              </label>
            </div>
          </Card>
        </div>

        <div className="space-y-2.5">
          <div className="rounded-xl border border-[#E5E7EB] bg-white p-3 lg:sticky lg:top-3">
            <div className="mb-2 flex items-baseline justify-between">
              <p className="text-[12.5px] font-semibold text-[#1B1B3A]">Before you submit</p>
              <span className="text-[12px] font-semibold tabular-nums" style={{ color: accent }}>
                {server.checks_passed} of {server.checks_total}
              </span>
            </div>
            <div className="mb-2.5 h-1.5 overflow-hidden rounded-full bg-[#EEF0F7]">
              <div className="h-full rounded-full transition-all"
                style={{ width: `${(server.checks_passed / server.checks_total) * 100}%`,
                  background: accent }} />
            </div>
            <ul className="space-y-1">
              {server.checklist.map((c) => (
                <li key={c.key} className="flex items-start gap-1.5 text-[11.5px] leading-snug">
                  <span className={cn('mt-[1px] flex h-4 w-4 shrink-0 items-center justify-center rounded-full',
                    c.passed ? 'bg-[#DCFCE7] text-[#16A34A]' : 'bg-[#F3F4F6] text-[#9CA3AF]')}>
                    {c.passed ? <Check className="h-2.5 w-2.5" /> : <span className="h-1 w-1 rounded-full bg-current" />}
                  </span>
                  <span className={c.passed ? 'text-[#5A5F7A]' : 'text-[#1B1B3A]'}>
                    {c.passed ? c.label : c.hint}
                  </span>
                </li>
              ))}
            </ul>

            <div className="mt-3 space-y-1.5 border-t border-[#EEF0F7] pt-2.5">
              <button type="button" onClick={save} disabled={locked || saving || !dirty}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-[12.5px] font-medium text-white transition disabled:opacity-40"
                style={{ background: accent }}>
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                {dirty ? 'Save changes' : 'Saved'}
              </button>

              {onSubmit && (
                <>
                  <textarea className={cn(INPUT, 'min-h-[54px] resize-y')} value={note}
                    disabled={locked || !server.can_submit}
                    placeholder="A note for your guide (optional)"
                    onChange={(e) => setNote(e.target.value)} />
                  <button type="button" onClick={submit}
                    disabled={locked || sending || !server.can_submit || dirty}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-[12.5px] font-medium transition disabled:opacity-40"
                    style={{ borderColor: accent, color: accent }}>
                    {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    Send to guide
                  </button>
                  <p className="text-[10.5px] leading-snug text-[#8A8FA8]">
                    {dirty ? 'Save your changes first.'
                      : server.submit_blocked_reason ? server.submit_blocked_reason
                        : unmet.length ? `${unmet.length} thing${unmet.length === 1 ? '' : 's'} still to finish.`
                          : 'Your guide has three working days to respond.'}
                  </p>
                </>
              )}
              {!onSubmit && (
                <p className="text-[10.5px] leading-snug text-[#8A8FA8]">
                  The team submits the registration for approval; you review what they send.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ pieces

function Card({ title, hint, children }: {
  title: string; hint?: string; children: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-[#E5E7EB] bg-white p-3">
      <div className="mb-2">
        <h3 className="text-[12.5px] font-semibold text-[#1B1B3A]">{title}</h3>
        {hint && <p className="mt-0.5 text-[10.5px] text-[#8A8FA8]">{hint}</p>}
      </div>
      {children}
    </section>
  )
}

function Banner({ tone, text }: { tone: 'error' | 'ok' | 'lock'; text: string }) {
  const style = tone === 'error'
    ? 'border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]'
    : tone === 'ok'
      ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]'
      : 'border-[#FDE68A] bg-[#FFFBEB] text-[#92400E]'
  return (
    <p className={cn('flex items-start gap-1.5 rounded-lg border px-2.5 py-2 text-[11.5px] leading-snug', style)}>
      {tone === 'ok' ? <Check className="mt-[1px] h-3.5 w-3.5 shrink-0" />
        : <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" />}
      {text}
    </p>
  )
}

/** Repeating rows with add and remove, shared by objectives, steps and stack. */
function RowList<T>({ rows, disabled, accent, max, blank, render, onChange, addLabel = 'Add another' }: {
  rows: T[]
  disabled: boolean
  accent: string
  max: number
  blank: () => T
  render: (row: T, update: (next: T) => void) => React.ReactNode
  onChange: (rows: T[]) => void
  addLabel?: string
}) {
  return (
    <div className="space-y-1.5">
      {rows.map((row, i) => (
        <div key={i} className="flex items-start gap-1.5">
          {render(row, (next) => onChange(rows.map((r, j) => (j === i ? next : r))))}
          <button type="button" disabled={disabled || rows.length === 1}
            aria-label="Remove"
            onClick={() => onChange(rows.filter((_, j) => j !== i))}
            className="mt-1.5 shrink-0 text-[#C7CBDD] transition hover:text-[#DC2626] disabled:opacity-30">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      <button type="button" disabled={disabled || rows.length >= max}
        onClick={() => onChange([...rows, blank()])}
        className="flex items-center gap-1 text-[11.5px] font-medium disabled:opacity-40"
        style={{ color: accent }}>
        <Plus className="h-3 w-3" /> {addLabel}
        {rows.length >= max && <span className="text-[#8A8FA8]"> (limit {max})</span>}
      </button>
    </div>
  )
}

/** A list of one-line entries: type, press Enter, it becomes a row. */
function ListInput({ values, disabled, accent, max, placeholder, onChange }: {
  values: string[]
  disabled: boolean
  accent: string
  max: number
  placeholder: string
  onChange: (values: string[]) => void
}) {
  const [text, setText] = useState('')
  const add = () => {
    const value = text.trim()
    if (!value || values.length >= max) return
    onChange([...values, value])
    setText('')
  }
  return (
    <div className="space-y-1.5">
      {values.map((v, i) => (
        <div key={`${v}-${i}`} className="flex items-start gap-1.5 rounded-lg border border-[#EEF0F7] px-2.5 py-1.5">
          <span className="flex-1 text-[11.5px] leading-snug text-[#3A3F58]">{v}</span>
          <button type="button" disabled={disabled} aria-label="Remove"
            onClick={() => onChange(values.filter((_, j) => j !== i))}
            className="shrink-0 text-[#C7CBDD] transition hover:text-[#DC2626] disabled:opacity-30">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      <div className="flex gap-1.5">
        <input className={INPUT} disabled={disabled || values.length >= max} value={text}
          placeholder={values.length >= max ? `Limit of ${max} reached` : placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }} />
        <button type="button" disabled={disabled || !text.trim() || values.length >= max}
          onClick={add}
          className="shrink-0 rounded-lg border px-2.5 text-[11.5px] font-medium disabled:opacity-40"
          style={{ borderColor: accent, color: accent }}>
          Add
        </button>
      </div>
    </div>
  )
}

/** Keywords, as removable chips. */
function ChipInput({ values, disabled, accent, max, placeholder, onChange }: {
  values: string[]
  disabled: boolean
  accent: string
  max: number
  placeholder: string
  onChange: (values: string[]) => void
}) {
  const [text, setText] = useState('')
  const add = () => {
    const value = text.trim().replace(/,+$/, '')
    if (!value || values.length >= max) return
    if (values.some((v) => v.toLowerCase() === value.toLowerCase())) { setText(''); return }
    onChange([...values, value])
    setText('')
  }
  return (
    <div className="rounded-lg border border-[#DDE0EE] bg-white p-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {values.map((v) => (
          <span key={v} className="flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px]"
            style={{ borderColor: accent, color: accent }}>
            {v}
            <button type="button" disabled={disabled} aria-label={`Remove ${v}`}
              onClick={() => onChange(values.filter((k) => k !== v))}
              className="disabled:opacity-30">
              <X className="h-2.5 w-2.5" />
            </button>
          </span>
        ))}
        <input className="min-w-[160px] flex-1 border-0 bg-transparent px-1 py-0.5 text-[12.5px] text-[#1B1B3A] outline-none disabled:text-[#8A8FA8]"
          disabled={disabled || values.length >= max} value={text}
          placeholder={values.length >= max ? `Limit of ${max} reached` : placeholder}
          onChange={(e) => setText(e.target.value)}
          onBlur={add}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add() }
            if (e.key === 'Backspace' && !text && values.length) {
              onChange(values.slice(0, -1))
            }
          }} />
      </div>
    </div>
  )
}
