'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, CheckCircle2, Search } from 'lucide-react'
import {
  Bar, CARD, Chip, Empty, Failed, FilterTabs, KpiRow, Loading, PageHeader, fmtDate,
} from '@/components/trainer/primitives'
import { decideDocument, errorText, fetchEvidence } from '@/lib/trainer-api'
import type { EvidenceRow, Kpi } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'all', label: 'All artefacts' },
  { key: 'outstanding', label: 'Outstanding' },
  { key: 'verified', label: 'Verified' },
]

const WIDTHS = ['92px', '84px', 'auto', '120px', '118px', '86px', '146px']

/** Opens on the filter the link asked for, so a worklist card lands on its own rows. */
function initialTab(allowed: string[], fallback: string) {
  if (typeof window === 'undefined') return fallback
  const wanted = new URLSearchParams(window.location.search).get('status')
  return wanted && allowed.includes(wanted) ? wanted : fallback
}

export default function EvidencePage() {
  const [data, setData] = useState<{ rows: EvidenceRow[]; kpis: Kpi[]; coverage: number } | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState(() =>
    initialTab(TABS.map((t) => t.key), 'all'))
  const [search, setSearch] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try { setData(await fetchEvidence(tab)) }
    catch (err: any) { setError(errorText(err, 'Could not load evidence.')) }
  }, [tab])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    if (!data) return []
    const needle = search.trim().toLowerCase()
    if (!needle) return data.rows
    return data.rows.filter((r) =>
      r.name.toLowerCase().includes(needle)
      || r.batch_code.toLowerCase().includes(needle)
      || r.category.toLowerCase().includes(needle))
  }, [data, search])

  const decide = async (row: EvidenceRow, decision: 'verify' | 'request_changes') => {
    if (!row.id) return
    setBusy(true)
    try {
      const result = await decideDocument(row.batch_code, row.id, decision)
      setNotice(`${result.name} — ${result.status.replace(/_/g, ' ')}.`)
      await load()
    } catch (err: any) {
      setNotice(errorText(err, 'That document could not be updated.'))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading evidence…" />

  return (
    <div className="space-y-3">
      <PageHeader
        title="Evidence"
        subtitle="Documents, base papers and submissions collected against your batches, in one list."
      />
      <KpiRow kpis={data.kpis} />

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[12.5px] text-[#1E40AF]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium">Dismiss</button>
        </div>
      )}

      <section className={cn(CARD, 'flex flex-wrap items-center gap-3 p-3.5')}>
        <span className="min-w-[190px] flex-1">
          <span className="flex items-center justify-between text-[11.5px]">
            <span className="text-[#6B7280]">Verification coverage</span>
            <span className="font-semibold text-[#1B1B3A]">{data.coverage}%</span>
          </span>
          <span className="mt-1.5 block">
            <Bar value={data.coverage} tone={data.coverage >= 80 ? 'bg-[#16A34A]' : 'bg-[#EA580C]'} />
          </span>
        </span>
        <span className="relative min-w-[220px]">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search artefact, batch or category…" aria-label="Search evidence"
            className="h-8 w-full rounded-lg border border-[#D1D5DB] pl-8 pr-2 text-[12px] outline-none focus:border-[#2563EB]" />
        </span>
      </section>

      <FilterTabs options={TABS} value={tab} onChange={setTab} />

      {rows.length === 0 ? (
        <Empty message={search ? 'No artefacts match that search.' : 'Nothing collected yet.'} />
      ) : (
        <section className={cn(CARD, 'overflow-x-auto')}>
          <table className="w-full table-fixed border-collapse text-[11.5px]">
            <colgroup>{WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
            <thead>
              <tr className="border-b border-[#E5E7EB] text-[#6B7280]">
                {['Batch', 'Kind', 'Artefact', 'Category', 'State', 'Recorded', 'Decision'].map((h, i) => (
                  <th key={h} className={cn('px-3 py-2 text-[11px] font-medium',
                    i === 2 ? 'text-left' : i === 0 ? 'text-left' : 'text-center')}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.batch_code}-${r.kind}-${r.name}-${i}`}
                  className="border-b border-[#F1F2F8] last:border-b-0">
                  <td className="px-3 py-2 font-medium text-[#1B1B3A]">{r.batch_code}</td>
                  <td className="px-3 py-2 text-center text-[#6B7280]">{r.kind}</td>
                  <td className="truncate px-3 py-2 text-[#1B1B3A]" title={r.name}>
                    {r.name}
                    {r.required && !r.verified && (
                      <span className="ml-1.5"><Chip tone="red">Required</Chip></span>
                    )}
                  </td>
                  <td className="truncate px-3 py-2 text-center text-[#6B7280]">{r.category}</td>
                  <td className="px-3 py-2 text-center">
                    <span className="inline-flex items-center gap-1.5">
                      {r.verified
                        ? <CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" />
                        : <AlertTriangle className="h-3.5 w-3.5 text-[#EA580C]" />}
                      <span className={r.verified ? 'text-[#15803D]' : 'text-[#C2410C]'}>
                        {r.state_label}
                      </span>
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center text-[10.5px] text-[#9CA3AF]">
                    {fmtDate(r.at)}
                  </td>
                  <td className="px-2 py-2 text-center">
                    {r.actionable ? (
                      <span className="flex justify-center gap-1.5">
                        <button type="button" disabled={busy || r.verified}
                          onClick={() => decide(r, 'verify')}
                          title={r.verified ? 'Already verified' : undefined}
                          className="rounded-md border border-[#BBF7D0] bg-[#F0FDF4] px-2 py-0.5 text-[10px] font-medium text-[#15803D] disabled:opacity-40">
                          Verify
                        </button>
                        <button type="button" disabled={busy}
                          onClick={() => decide(r, 'request_changes')}
                          className="rounded-md border border-[#FED7AA] bg-[#FFF7ED] px-2 py-0.5 text-[10px] font-medium text-[#C2410C] disabled:opacity-40">
                          Changes
                        </button>
                      </span>
                    ) : (
                      <span className="text-[10px] text-[#C7CBDD]">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <p className="text-[11.5px] text-[#9CA3AF]">
        Showing {rows.length} of {data.rows.length}. Verifying a document here writes the same
        record the Faculty Portal reads. Base papers and submissions show a dash because they have
        no decision route of their own yet &mdash; a base paper is verified with the paper itself.
      </p>
    </div>
  )
}
