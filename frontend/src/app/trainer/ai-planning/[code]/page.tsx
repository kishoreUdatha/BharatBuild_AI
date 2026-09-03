'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CheckCheck,
  Eye,
  FileText,
  Layers,
  Loader2,
  Lock,
  Minus,
  Pencil,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  XCircle,
  Zap,
} from 'lucide-react'
import {
  decideStory,
  errorText,
  fetchStoryBoard,
  markStoriesReviewed,
  moveToBacklog,
  previewRegeneration,
  regenerateDrafts,
  updateStory,
  type RegenerationPlan,
  type StoryBoard,
} from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'

const STATUS_TABS = [
  { key: 'all', label: 'All Stories' },
  { key: 'needs_review', label: 'Needs Review' },
  { key: 'reviewed', label: 'Reviewed' },
  { key: 'rejected', label: 'Rejected' },
]

const KPI_ICON: Record<string, typeof Layers> = {
  epics: Layers, drafts: FileText, reviewed: Eye,
  needs: AlertTriangle, points: Zap, quality: TrendingUp,
}

function Stepper({ stages }: { stages: StoryBoard['stages'] }) {
  return (
    <ol className="flex flex-wrap items-start gap-y-3">
      {stages.map((s, i) => (
        <li key={s.key} className="flex min-w-[168px] flex-1 items-start gap-2">
          <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-[12px] font-semibold',
            s.state === 'complete' ? 'border-[#16A34A] bg-white text-[#16A34A]'
              : s.state === 'active' ? 'border-[#2563EB] bg-[#2563EB] text-white'
                : 'border-[#D1D5DB] bg-white text-[#9CA3AF]')}>
            {s.state === 'complete' ? <Check className="h-4 w-4" />
              : s.state === 'locked' ? <Lock className="h-3.5 w-3.5" /> : i + 1}
          </span>
          <span className="min-w-0 pt-0.5">
            <span className={cn('block text-[12.5px] font-medium leading-tight',
              s.state === 'active' ? 'text-[#2563EB]'
                : s.state === 'locked' ? 'text-[#9CA3AF]' : 'text-[#1B1B3A]')}>
              {s.label}
            </span>
            <span className={cn('block text-[10.5px] leading-tight',
              s.state === 'active' ? 'text-[#2563EB]' : 'text-[#9CA3AF]')}>
              {s.note}
            </span>
          </span>
          {i < stages.length - 1 && (
            <span className={cn('mt-4 hidden h-px flex-1 xl:block',
              s.state === 'complete' ? 'bg-[#16A34A]' : 'border-t border-dashed border-[#D1D5DB]')} />
          )}
        </li>
      ))}
    </ol>
  )
}

function PriorityCell({ value, label }: { value: string; label: string }) {
  const Icon = value === 'high' ? ChevronUp : value === 'low' ? ChevronDown : Minus
  const tone = value === 'high' ? 'text-[#DC2626]' : value === 'low' ? 'text-[#6B7280]' : 'text-[#D97706]'
  return (
    <span className={cn('inline-flex items-center gap-1 text-[11.5px]', tone)}>
      <Icon className="h-3.5 w-3.5" /> {label}
    </span>
  )
}

function StatusChip({ value, label }: { value: string; label: string }) {
  const tone = value === 'needs_review' ? 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]'
    : value === 'rejected' ? 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]'
      : value === 'approved' ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]'
        : value === 'revision_requested' ? 'border-[#DDD6FE] bg-[#F5F3FF] text-[#6D28D9]'
          : 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]'
  return (
    <span className={cn('inline-block whitespace-nowrap rounded-md border px-2 py-0.5 text-[10.5px] font-medium', tone)}>
      {label}
    </span>
  )
}

export default function AiStoryApprovalPage() {
  const params = useParams<{ code: string }>()
  const router = useRouter()
  const code = decodeURIComponent(params?.code ?? '')

  const [data, setData] = useState<StoryBoard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const [filters, setFilters] = useState<Record<string, string>>({ status: 'all' })
  const [search, setSearch] = useState('')
  const [selectedKey, setSelectedKey] = useState<string | undefined>()
  // Mirrors selectedKey for the loader, which cannot see state updates.
  const selectedKeyRef = useRef<string | undefined>(undefined)
  const [checked, setChecked] = useState<Set<string>>(new Set())
  // Regeneration is destructive, so the counts are shown before it runs.
  const [plan, setPlan] = useState<{ pending: RegenerationPlan; all: RegenerationPlan } | null>(null)

  // Local edits to the open story, so typing does not fight the reload.
  const [draft, setDraft] = useState<{ points: string; priority: string; comment: string }>({
    points: '', priority: '', comment: '',
  })

  const load = useCallback(async (keyOverride?: string) => {
    setLoading(true)
    setError('')
    try {
      // The key is passed in rather than read from state: state updates are not
      // visible to this closure, which previously made row clicks open the
      // previously selected story.
      const wanted = keyOverride ?? selectedKeyRef.current
      const result = await fetchStoryBoard(code, { ...filters, search, selected: wanted })
      setData(result)
      if (result.selected) {
        selectedKeyRef.current = result.selected.key
        setSelectedKey(result.selected.key)
        setDraft({
          points: String(result.selected.story_points ?? ''),
          priority: result.selected.priority,
          comment: result.selected.trainer_comment ?? '',
        })
      }
    } catch (err: any) {
      const s = err?.response?.status
      if (s === 401) { router.push(`/login?next=/trainer/ai-planning/${code}`); return }
      setError(s === 404 ? `No batch found with code ${code}.`
        : s === 403 ? 'This batch belongs to a department you are not attached to.'
          : errorText(err, 'Could not load the story board.'))
    } finally {
      setLoading(false)
    }
  }, [code, filters, search, router])

  useEffect(() => { load() }, [load])

  const selected = data?.selected ?? null

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    try {
      await fn()
      setNotice(ok)
      await load()
    } catch (err: any) {
      setNotice(errorText(err, 'That action could not be completed.'))
    } finally {
      setBusy(false)
    }
  }

  const decide = (decision: string, ok: string) => {
    if (!selected) return
    act(() => decideStory(code, selected.id, decision, draft.comment || undefined), ok)
  }

  const saveDraft = () => {
    if (!selected) return
    act(() => updateStory(code, selected.id, {
      story_points: draft.points === '' ? undefined : Number(draft.points),
      priority: draft.priority || undefined,
      trainer_comment: draft.comment,
    }), `${selected.key} saved.`)
  }

  const toggle = (id: string) => setChecked((prev) => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  const allShownChecked = useMemo(
    () => Boolean(data?.rows.length) && data!.rows.every((r) => checked.has(r.id)),
    [data, checked]
  )

  if (loading && !data) {
    return (
      <div className={cn(CARD, 'flex h-[460px] flex-col items-center justify-center gap-3 text-[#6B7280]')}>
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
        <p className="text-[12.5px]">Loading drafted stories…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div className={cn(CARD, 'flex h-[460px] flex-col items-center justify-center gap-3')}>
        <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
        <p className="text-[12.5px] text-[#6B7280]">{error}</p>
        <button type="button" onClick={() => load()}
          className="flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </button>
      </div>
    )
  }
  if (!data) return null

  const c = data.counts

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">AI Story Approval</h1>
          <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
            Review every AI-generated story before moving the approved set to the Product Backlog.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button"
            onClick={() => setNotice(data.run
              ? `Drafted by ${data.run.model} on ${new Date(data.run.generated_at!).toLocaleString('en-IN')} from ${data.run.source_summary}`
              : 'No generation run is recorded for this batch.')}
            className="flex items-center gap-2 rounded-lg border border-[#BFDBFE] px-3.5 py-2 text-[12.5px] font-medium text-[#2563EB] hover:bg-[#EFF6FF]">
            <BarChart3 className="h-4 w-4" /> View AI Analysis
          </button>
          <button type="button" disabled={busy}
            onClick={async () => {
              if (plan) { setPlan(null); return }
              try {
                const [pending, all] = await Promise.all([
                  previewRegeneration(code, 'pending'),
                  previewRegeneration(code, 'all'),
                ])
                setPlan({ pending, all })
              } catch (err: any) {
                setNotice(errorText(err, 'Could not work out what a regeneration would replace.'))
              }
            }}
            className="flex items-center gap-2 rounded-lg border border-[#BFDBFE] px-3.5 py-2 text-[12.5px] font-medium text-[#2563EB] hover:bg-[#EFF6FF] disabled:opacity-50">
            <RefreshCw className="h-4 w-4" /> Regenerate Drafts
          </button>
        </div>
      </div>

      <nav className="flex flex-wrap items-center gap-1.5 text-[12px]">
        <Link href="/trainer/batches" className="text-[#2563EB] hover:underline">My Batches</Link>
        <span className="text-[#C7CBDD]">/</span>
        <Link href="/trainer/ai-planning" className="text-[#2563EB] hover:underline">
          {data.header.display_name}
        </Link>
        <span className="text-[#C7CBDD]">/</span>
        <span className="text-[#2563EB]">{data.header.project_title ?? data.header.batch_code}</span>
        <span className="text-[#C7CBDD]">/</span>
        <span className="text-[#6B7280]">AI Story Approval</span>
      </nav>

      <section className="px-1 py-2"><Stepper stages={data.stages} /></section>

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[12.5px] text-[#1E40AF]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium">Dismiss</button>
        </div>
      )}

      {plan && (
        <section className={cn(CARD, 'space-y-2 border-[#BFDBFE] p-3')}>
          <p className="text-[12.5px] font-semibold text-[#1B1B3A]">Regenerate drafted stories</p>
          <p className="text-[11.5px] text-[#6B7280]">
            The model redrafts from this batch&apos;s approved project details. Anything it
            produces arrives as <span className="font-medium">Needs Review</span> &mdash; it
            cannot approve its own work.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <button type="button" disabled={busy || plan.pending.undecided === 0}
              onClick={() => act(() => regenerateDrafts(code, 'pending'),
                'Pending stories redrafted.').then(() => setPlan(null))}
              className="rounded-lg bg-[#2563EB] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-40">
              Redraft {plan.pending.undecided} pending
              {plan.pending.undecided === 1 ? ' story' : ' stories'}
              <span className="ml-1 font-normal opacity-80">
                (keeps {plan.pending.decided} decided)
              </span>
            </button>
            <button type="button" disabled={busy}
              onClick={() => act(() => regenerateDrafts(code, 'all', true),
                'Every story redrafted.').then(() => setPlan(null))}
              className="rounded-lg border border-[#FECACA] px-3.5 py-2 text-[12px] font-medium text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-40">
              Replace all {plan.all.total}
              {plan.all.decisions_discarded > 0 && (
                <span className="ml-1 font-normal">
                  &mdash; discards {plan.all.decisions_discarded} decision
                  {plan.all.decisions_discarded === 1 ? '' : 's'}
                </span>
              )}
            </button>
            <button type="button" onClick={() => setPlan(null)}
              className="rounded-lg border border-[#D1D5DB] px-3.5 py-2 text-[12px] text-[#374151] hover:bg-[#F9FAFB]">
              Cancel
            </button>
          </div>
        </section>
      )}

      <div className="grid gap-3 xl:grid-cols-[minmax(0,2.6fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            {data.kpis.map((k) => {
              const Icon = KPI_ICON[k.id] ?? FileText
              const tone = k.id === 'needs' ? 'bg-[#FFF7ED] text-[#EA580C]'
                : k.id === 'quality' ? 'bg-[#F5F3FF] text-[#7C3AED]'
                  : 'bg-[#EFF6FF] text-[#2563EB]'
              return (
                <div key={k.id} className={cn(CARD, 'flex items-center gap-2.5 p-3')}>
                  <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', tone)}>
                    <Icon className="h-4.5 w-4.5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[18px] font-bold leading-none text-[#1B1B3A]">{k.value}</span>
                    <span className="block text-[10.5px] leading-tight text-[#6B7280]">{k.label}</span>
                  </span>
                </div>
              )
            })}
          </div>

          {/* Toolbar */}
          <section className={cn(CARD, 'flex flex-wrap items-center gap-2 p-2.5')}>
            <span className="relative min-w-[180px] flex-1">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search stories…" aria-label="Search stories"
                className="h-8 w-full rounded-lg border border-[#D1D5DB] pl-8 pr-2 text-[12px] outline-none focus:border-[#2563EB]" />
            </span>
            {STATUS_TABS.map((t) => (
              <button key={t.key} type="button"
                onClick={() => setFilters((f) => ({ ...f, status: t.key }))}
                className={cn('rounded-lg border px-3 py-1.5 text-[11.5px] font-medium transition-colors',
                  filters.status === t.key
                    ? t.key === 'needs_review' ? 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]'
                      : t.key === 'reviewed' ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]'
                        : t.key === 'rejected' ? 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]'
                          : 'border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]'
                    : 'border-[#E5E7EB] bg-white text-[#6B7280] hover:bg-[#F9FAFB]')}>
                {t.label}
              </button>
            ))}
            {[
              ['epic', 'All Epics', data.epics.map((e) => [e.key, `${e.key} · ${e.title}`] as const)],
              ['priority', 'All Priorities', data.priorities.map((p) => [p, p[0].toUpperCase() + p.slice(1)] as const)],
              ['confidence', 'All AI Confidence', [['high', '90% and above'], ['medium', '80–89%'], ['low', 'Below 80%']] as const],
            ].map(([key, allLabel, options]) => (
              <select key={key as string} value={filters[key as string] ?? ''}
                aria-label={allLabel as string}
                onChange={(e) => setFilters((f) => ({ ...f, [key as string]: e.target.value }))}
                className="h-8 rounded-lg border border-[#D1D5DB] px-2 text-[11.5px] outline-none focus:border-[#2563EB]">
                <option value="">{allLabel as string}</option>
                {(options as readonly (readonly [string, string])[]).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            ))}
            <button type="button" disabled={busy || checked.size === 0}
              onClick={() => act(() => markStoriesReviewed(code, [...checked]),
                `${checked.size} stor${checked.size === 1 ? 'y' : 'ies'} marked reviewed.`)
                .then(() => setChecked(new Set()))}
              className="flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-1.5 text-[11.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-40">
              <CheckCheck className="h-3.5 w-3.5" /> Mark Selected Reviewed
            </button>
          </section>

          {/* Story table */}
          <section className={cn(CARD, 'p-0')}>
            <table className="w-full table-fixed border-collapse text-[11.5px]">
              <colgroup>
                {['34px', '62px', 'auto', '62px', '104px', '52px', '82px', '92px', '104px', '48px']
                  .map((w, i) => <col key={i} style={{ width: w }} />)}
              </colgroup>
              <thead>
                <tr className="border-b border-[#E5E7EB] text-[#6B7280]">
                  <th className="px-2 py-2">
                    <input type="checkbox" aria-label="Select all shown" checked={allShownChecked}
                      onChange={() => setChecked(allShownChecked ? new Set()
                        : new Set(data.rows.map((r) => r.id)))} />
                  </th>
                  {['Key', 'User Story', 'Epic', 'Acceptance Criteria', 'Points', 'Priority',
                    'AI Confidence', 'Review Status', 'Edit'].map((h, i) => (
                    <th key={h} className={cn('px-2 py-2 text-[11px] font-medium',
                      i === 1 ? 'text-left' : i === 0 ? 'text-left' : 'text-center')}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.id}
                    className={cn('cursor-pointer border-b border-[#F1F2F8] last:border-b-0 hover:bg-[#FAFBFE]',
                      selected?.key === r.key && 'bg-[#EFF6FF]')}
                    onClick={() => { selectedKeyRef.current = r.key; setSelectedKey(r.key); load(r.key) }}>
                    <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" aria-label={`Select ${r.key}`}
                        checked={checked.has(r.id)} onChange={() => toggle(r.id)} />
                    </td>
                    <td className="px-2 py-2 font-medium text-[#2563EB]">{r.key}</td>
                    <td className="truncate px-2 py-2 text-[#1B1B3A]" title={r.title}>{r.title}</td>
                    <td className="px-2 py-2 text-center">
                      {r.epic_key && (
                        <span className="rounded border border-[#DBEAFE] bg-[#EFF6FF] px-1.5 py-0.5 text-[10px] font-medium text-[#1D4ED8]">
                          {r.epic_key}
                        </span>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <span className="flex items-center justify-center gap-1.5">
                        {r.acceptance_complete
                          ? <CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" />
                          : <AlertTriangle className="h-3.5 w-3.5 text-[#EA580C]" />}
                        <span className="text-[#3A3F58]">{r.acceptance_met} / {r.acceptance_total}</span>
                      </span>
                    </td>
                    <td className="px-2 py-2 text-center text-[#3A3F58]">{r.story_points}</td>
                    <td className="px-2 py-2 text-center">
                      <PriorityCell value={r.priority} label={r.priority_label} />
                    </td>
                    <td className="px-2 py-2 text-center">
                      <span className="inline-flex items-center gap-1.5 text-[#3A3F58]">
                        <span className={cn('h-1.5 w-1.5 rounded-full',
                          (r.ai_confidence ?? 0) >= 90 ? 'bg-[#16A34A]' : 'bg-[#D97706]')} />
                        {r.ai_confidence ?? '—'}%
                      </span>
                    </td>
                    <td className="px-2 py-2 text-center">
                      <StatusChip value={r.review_status} label={r.review_status_label} />
                    </td>
                    <td className="px-2 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                      <button type="button" aria-label={`Edit ${r.key}`}
                        onClick={() => { selectedKeyRef.current = r.key; setSelectedKey(r.key); load(r.key) }}
                        className="text-[#2563EB] hover:text-[#1D4ED8]">
                        <Pencil className="mx-auto h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
                {data.rows.length === 0 && (
                  <tr><td colSpan={10} className="py-10 text-center text-[12px] text-[#9CA3AF]">
                    No stories match these filters.
                  </td></tr>
                )}
              </tbody>
            </table>
          </section>

          {/* Selected story */}
          {selected && (
            <section className={cn(CARD, 'border-[#BFDBFE] p-4')}>
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="text-[14px] font-bold text-[#2563EB]">{selected.key}</span>
                <span className="text-[14px] font-semibold text-[#1B1B3A]">{selected.title}</span>
                <StatusChip value={selected.review_status} label={selected.review_status_label} />
              </div>

              {selected.open_revision && (
                <p className="mt-2 rounded-lg border border-[#DDD6FE] bg-[#F5F3FF] px-3 py-2 text-[11.5px] text-[#5B21B6]">
                  Revision requested: {selected.open_revision.note}
                </p>
              )}

              <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1.1fr)_minmax(0,1.2fr)]">
                <div>
                  <p className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">User Story</p>
                  <p className="text-[11.5px] leading-relaxed text-[#4B5563]">{selected.narrative ?? '—'}</p>
                </div>

                <div>
                  <p className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">
                    Acceptance Criteria ({selected.acceptance_label})
                  </p>
                  <ul className="space-y-1">
                    {selected.acceptance_criteria.map((a) => (
                      <li key={a.id} className="flex gap-1.5 text-[11px] leading-snug text-[#4B5563]">
                        {a.met
                          ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                          : <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#EA580C]" />}
                        {a.text}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">Definition of Done</p>
                  <ul className="space-y-1">
                    {selected.definition_of_done.map((d) => (
                      <li key={d.id} className="flex gap-1.5 text-[11px] leading-snug text-[#4B5563]">
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                        {d.text}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-2.5">
                  <div>
                    <label className="mb-1 block text-[11px] text-[#6B7280]" htmlFor="deps">Dependencies</label>
                    <input id="deps" readOnly value={selected.dependencies ?? 'None recorded'}
                      className="h-8 w-full rounded-lg border border-[#E5E7EB] bg-[#F9FAFB] px-2 text-[11.5px] text-[#4B5563]" />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="mb-1 block text-[11px] text-[#6B7280]" htmlFor="pts">Story Points</label>
                      <input id="pts" type="number" min={0} max={100} value={draft.points}
                        onChange={(e) => setDraft((d) => ({ ...d, points: e.target.value }))}
                        className="h-8 w-full rounded-lg border border-[#D1D5DB] px-2 text-[12px] outline-none focus:border-[#2563EB]" />
                    </div>
                    <div>
                      <label className="mb-1 block text-[11px] text-[#6B7280]" htmlFor="prio">Priority</label>
                      <select id="prio" value={draft.priority}
                        onChange={(e) => setDraft((d) => ({ ...d, priority: e.target.value }))}
                        className="h-8 w-full rounded-lg border border-[#D1D5DB] px-2 text-[12px] outline-none focus:border-[#2563EB]">
                        {data.priorities.map((p) => (
                          <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-[11px] text-[#6B7280]" htmlFor="cmt">Trainer Comment</label>
                    <textarea id="cmt" rows={3} maxLength={500} value={draft.comment}
                      onChange={(e) => setDraft((d) => ({ ...d, comment: e.target.value }))}
                      placeholder="Add your comments or notes for this story…"
                      className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[11.5px] outline-none focus:border-[#2563EB]" />
                    <p className="mt-0.5 text-right text-[10px] text-[#9CA3AF]">{draft.comment.length} / 500</p>
                  </div>
                </div>
              </div>

              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <button type="button" disabled={busy}
                  onClick={() => {
                    if (!draft.comment.trim()) {
                      setNotice('Say what needs redrafting in the Trainer Comment first.')
                      return
                    }
                    decide('request_revision', `Revision requested on ${selected.key}.`)
                  }}
                  className="flex items-center justify-center gap-2 rounded-lg border border-[#DDD6FE] py-2.5 text-[12.5px] font-medium text-[#6D28D9] hover:bg-[#F5F3FF] disabled:opacity-50">
                  <Sparkles className="h-4 w-4" /> Request AI Revision
                </button>
                <button type="button" disabled={busy}
                  onClick={() => decide('reject', `${selected.key} rejected.`)}
                  className="flex items-center justify-center gap-2 rounded-lg border border-[#FECACA] py-2.5 text-[12.5px] font-medium text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-50">
                  <XCircle className="h-4 w-4" /> Reject Story
                </button>
                <button type="button" disabled={busy}
                  onClick={() => decide('approve', `${selected.key} approved.`)}
                  className="flex items-center justify-center gap-2 rounded-lg bg-[#2563EB] py-2.5 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-50">
                  <CheckCircle2 className="h-4 w-4" /> Approve Story
                </button>
              </div>
            </section>
          )}
        </div>

        {/* Right rail */}
        <div className="space-y-3">
          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Approval Checklist</h2>
            <ul className="mt-2 space-y-1.5">
              {data.checklist.items.map((i) => (
                <li key={i.key} className="flex items-center gap-2 text-[11.5px]">
                  {i.passed
                    ? <CheckCircle2 className="h-4 w-4 shrink-0 text-[#16A34A]" />
                    : <AlertTriangle className="h-4 w-4 shrink-0 text-[#EA580C]" />}
                  <span className="flex-1 text-[#4B5563]">{i.label}</span>
                  <span className={cn('whitespace-nowrap text-[10.5px]',
                    i.passed ? 'text-[#16A34A]' : 'text-[#EA580C]')}>{i.detail}</span>
                </li>
              ))}
            </ul>
            {data.checklist.outstanding > 0 && (
              <p className="mt-3 flex items-center gap-2 border-t border-[#F1F2F8] pt-2.5 text-[11.5px] text-[#EA580C]">
                <AlertTriangle className="h-4 w-4 shrink-0" /> {data.checklist.outstanding_label}
              </p>
            )}
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[14px] font-semibold text-[#1B1B3A]">After Approval</h2>
            <ol className="mt-2 space-y-2">
              {data.after_approval.map((text, i) => (
                <li key={text} className="flex gap-2 text-[11.5px] leading-snug text-[#4B5563]">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#2563EB] text-[9.5px] font-semibold text-white">
                    {i + 1}
                  </span>{text}
                </li>
              ))}
            </ol>
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="flex items-center gap-2 text-[14px] font-semibold text-[#1B1B3A]">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#F5F3FF] text-[#7C3AED]">
                <ShieldCheck className="h-4 w-4" />
              </span>
              AI Governance
            </h2>
            <p className="mt-2 text-[11.5px] leading-relaxed text-[#4B5563]">{data.governance}</p>
          </section>
        </div>
      </div>

      {/* Footer */}
      <section className={cn(CARD, 'flex flex-wrap items-center gap-3 p-3')}>
        <Link href="/trainer/ai-planning"
          className="flex items-center gap-2 rounded-lg border border-[#D1D5DB] px-4 py-2.5 text-[12.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
          <ArrowLeft className="h-4 w-4" /> Back to AI Analysis
        </Link>

        <div className={cn('flex items-center gap-2 rounded-lg border px-3 py-2',
          c.needs_review > 0 ? 'border-[#FED7AA] bg-[#FFF7ED]' : 'border-[#BBF7D0] bg-[#F0FDF4]')}>
          {c.needs_review > 0
            ? <AlertTriangle className="h-4 w-4 shrink-0 text-[#EA580C]" />
            : <CheckCircle2 className="h-4 w-4 shrink-0 text-[#16A34A]" />}
          <span>
            <span className={cn('block text-[12px] font-medium',
              c.needs_review > 0 ? 'text-[#C2410C]' : 'text-[#15803D]')}>
              {c.reviewed} of {c.total} stories reviewed
            </span>
            <span className="block text-[10.5px] text-[#6B7280]">{data.checklist.outstanding_label}</span>
          </span>
        </div>

        <span className="flex-1" />

        <button type="button" disabled={busy || !selected} onClick={saveDraft}
          className="flex items-center gap-2 rounded-lg border border-[#D1D5DB] px-4 py-2.5 text-[12.5px] font-medium text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-50">
          <Save className="h-4 w-4" /> Save Draft
        </button>

        <span className="text-right">
          <button type="button" disabled={busy || !data.can_continue}
            onClick={() => act(() => moveToBacklog(code), 'Approved stories moved to the product backlog.')}
            title={data.can_continue ? undefined : data.checklist.outstanding_label}
            className={cn('flex items-center gap-2 rounded-lg px-5 py-2.5 text-[12.5px] font-medium',
              data.can_continue
                ? 'bg-[#2563EB] text-white hover:bg-[#1D4ED8]'
                : 'cursor-not-allowed bg-[#E5E7EB] text-[#9CA3AF]')}>
            <Lock className="h-4 w-4" />
            {data.can_continue
              ? 'Approve All & Move to Backlog'
              : `Resolve ${c.needs_review} Stor${c.needs_review === 1 ? 'y' : 'ies'} to Continue`}
          </button>
          {!data.can_continue && (
            <span className="mt-1 block text-[10.5px] text-[#9CA3AF]">
              Then: Approve All &amp; Move to Backlog
            </span>
          )}
        </span>
      </section>
    </div>
  )
}
