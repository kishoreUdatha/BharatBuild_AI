'use client'

/**
 * Import history.
 *
 * The results screen at /trainer/imports/<id> could only ever be reached by
 * following a redirect straight after an upload - there was no way back to a
 * run once you left it, and no way to see any run but the last. An import
 * rewrites batch allocations, so being unable to look one up afterwards is the
 * gap this closes.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import {
  AlertTriangle, ArrowRight, ChevronLeft, ChevronRight, Download, FileSpreadsheet,
  Loader2, RotateCcw, Search, Upload,
} from 'lucide-react'
import { CARD, Chip, Failed, Loading, PageHeader } from '@/components/trainer/primitives'
import {
  downloadImportReport, downloadSampleSheet, errorText, fetchImports,
  importBatchAllocation,
} from '@/lib/trainer-api'
import type { ImportHistory, ImportHistoryRow } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const BTN = 'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12.5px] font-medium'
const BTN_OUTLINE = `${BTN} border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]`
const BTN_PRIMARY = `${BTN} bg-[#2563EB] text-white hover:bg-[#1D4ED8]`

/** Status → chip colour. Partial is amber because it needs a human to look. */
const TONE: Record<string, 'green' | 'amber' | 'red' | 'blue' | 'grey'> = {
  completed: 'green',
  imported: 'green',
  partially_imported: 'amber',
  processing: 'blue',
  pending: 'grey',
  failed: 'red',
}

const fmtWhen = (iso: string | null) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export default function ImportHistoryPage() {
  const router = useRouter()
  const { user } = useAuth()
  // The list a manager gets is every trainer's, not their own, and saying
  // otherwise would read as "nothing here" when the truth is "nobody has
  // imported into this college yet".
  const isManager = user?.role === 'manager'

  const [data, setData] = useState<ImportHistory | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState('')
  const [uploading, setUploading] = useState(false)

  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    try {
      setError('')
      setData(await fetchImports({
        page, limit: 20, search, import_type: type, status,
      }))
    } catch (err) {
      setError(errorText(err, 'Your imports could not be loaded.'))
    }
  }, [page, search, type, status])

  // Debounced so typing in the search box does not fire a request per keystroke.
  useEffect(() => {
    const timer = setTimeout(load, search ? 300 : 0)
    return () => clearTimeout(timer)
  }, [load, search])

  const upload = async (file: File) => {
    setUploading(true)
    setError('')
    setNotice('')
    try {
      const result = await importBatchAllocation(file)
      // Straight to the run: the tallies and any rejected rows are what you
      // need to see next, and they only live on the results screen.
      router.push(`/trainer/imports/${result.id}`)
    } catch (err) {
      setError(errorText(err, 'That sheet could not be imported.'))
      setUploading(false)
    }
  }

  const report = async (row: ImportHistoryRow) => {
    setBusy(row.id)
    try {
      await downloadImportReport(row.id, row.import_code)
    } catch (err) {
      setError(errorText(err, 'That report could not be downloaded.'))
    } finally { setBusy('') }
  }

  const dirty = Boolean(search || type || status)
  const reset = () => { setSearch(''); setType(''); setStatus(''); setPage(1) }

  const attention = useMemo(
    () => data?.kpis.find((k) => k.id === 'attention'),
    [data])

  if (!data && error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading your imports…" />

  return (
    <div className="space-y-3">
      <PageHeader
        title="Imports"
        subtitle={isManager
          ? 'Every roster and allocation sheet uploaded into this college this year'
          : 'Every roster and allocation sheet you have uploaded this year'}
        right={
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className={BTN_OUTLINE}
              onClick={() => downloadSampleSheet('xlsx').catch(
                () => setError('The sample sheet could not be downloaded.'))}>
              <FileSpreadsheet className="h-4 w-4" /> Sample sheet
            </button>
            <label className={cn(BTN_PRIMARY, 'cursor-pointer',
              uploading && 'pointer-events-none opacity-60')}>
              {uploading
                ? <Loader2 className="h-4 w-4 animate-spin" />
                : <Upload className="h-4 w-4" />}
              {uploading ? 'Importing…' : 'Import a sheet'}
              <input type="file" className="sr-only" accept=".csv,.xlsx"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) upload(file)
                  e.target.value = ''
                }} />
            </label>
          </div>
        } />

      {error && (
        <p className="flex items-start gap-2 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[12px] text-[#B91C1C]">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}
      {notice && (
        <p className="rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-3 py-2 text-[12px] text-[#166534]">
          {notice}
        </p>
      )}

      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-3.5 py-2">
          {data.kpis.map((k) => (
            <span key={k.id} className="flex items-baseline gap-1.5">
              <span className="text-[10.5px] text-[#6B7280]">{k.label}</span>
              <span className={cn('text-[13px] font-bold',
                k.id === 'attention' && Number(k.value) > 0
                  ? 'text-[#B91C1C]'
                  : k.id === 'failed' && Number(k.value) > 0
                    ? 'text-[#B45309]'
                    : 'text-[#1B1B3A]')}>
                {k.value}
              </span>
            </span>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-[#F1F2F8] bg-[#FCFCFD] px-3.5 py-2">
          <label className="relative min-w-[200px] flex-1">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
            <input value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Search by file name or import code"
              className="h-7 w-full rounded-lg border border-[#D1D5DB] bg-white pl-7 pr-2 text-[11.5px] text-[#1B1B3A] placeholder:text-[#9CA3AF] focus:border-[#2563EB] focus:outline-none" />
          </label>
          <select value={type} aria-label="Import type"
            onChange={(e) => { setType(e.target.value); setPage(1) }}
            className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-1.5 text-[11.5px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
            <option value="">All types</option>
            {data.import_types.map((t) => (
              <option key={t.key} value={t.key}>{t.label}</option>
            ))}
          </select>
          <select value={status} aria-label="Status"
            onChange={(e) => { setStatus(e.target.value); setPage(1) }}
            className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-1.5 text-[11.5px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
            <option value="">All statuses</option>
            {data.statuses.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
          {dirty && (
            <button type="button" onClick={reset}
              className="flex h-7 items-center gap-1 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
              <RotateCcw className="h-3 w-3" /> Reset
            </button>
          )}
        </div>
      </div>

      {attention && Number(attention.value) > 0 && !dirty && (
        <p className="flex items-start gap-2 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] text-[#92400E]">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            {attention.value} {Number(attention.value) === 1 ? 'import' : 'imports'} finished
            with rejected rows. Open one to see which rows were refused and why —
            the batches in them were never created.
          </span>
        </p>
      )}

      <div className={cn(CARD, 'overflow-hidden')}>
        {data.rows.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <FileSpreadsheet className="mx-auto h-6 w-6 text-[#D1D5DB]" />
            <p className="mt-2 text-[12.5px] text-[#6B7280]">
              {dirty
                ? 'No import matches those filters.'
                : isManager
                  ? 'Nobody has imported a sheet into this college yet.'
                  : 'You have not imported a sheet yet. Download the sample to see the columns.'}
            </p>
            {dirty && (
              <button type="button" onClick={reset}
                className="mt-2 text-[12px] font-medium text-[#2563EB] hover:underline">
                Clear them
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] border-collapse text-left">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
                  <th className="px-3 py-2">Import</th>
                  <th className="px-3 py-2">File</th>
                  <th className="px-3 py-2">Uploaded</th>
                  <th className="px-3 py-2 text-right">Rows</th>
                  <th className="px-3 py-2 text-right">Imported</th>
                  <th className="px-3 py-2 text-right">Failed</th>
                  <th className="px-3 py-2 text-right">Duplicates</th>
                  <th className="px-3 py-2 text-center">Status</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.id}
                    className="border-b border-[#F1F2F8] text-[12px] last:border-0 hover:bg-[#FAFBFF]">
                    <td className="px-3 py-2">
                      <Link href={`/trainer/imports/${row.id}`}
                        className="font-mono text-[10.5px] font-medium text-[#2563EB] hover:underline">
                        {row.import_code}
                      </Link>
                    </td>
                    <td className="max-w-[220px] truncate px-3 py-2 text-[#1B1B3A]"
                      title={row.file_name}>
                      {row.file_name}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                      {fmtWhen(row.started_at)}
                      {row.imported_by && (
                        <span className="block text-[10px] text-[#9CA3AF]">
                          {row.imported_by}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[#1B1B3A]">
                      {row.rows_total}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-[#166534]">
                      {row.rows_imported}
                    </td>
                    <td className={cn('px-3 py-2 text-right tabular-nums',
                      row.rows_failed ? 'font-medium text-[#B91C1C]' : 'text-[#9CA3AF]')}>
                      {row.rows_failed}
                    </td>
                    <td className={cn('px-3 py-2 text-right tabular-nums',
                      row.rows_duplicate ? 'text-[#B45309]' : 'text-[#9CA3AF]')}>
                      {row.rows_duplicate}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <Chip tone={TONE[row.status_key] ?? 'grey'}>{row.status}</Chip>
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => report(row)}
                          disabled={busy === row.id}
                          aria-label="Download the report" title="Download the report"
                          className="flex h-7 w-7 items-center justify-center rounded border border-[#E5E7EB] bg-white text-[#2563EB] hover:bg-[#F9FAFB] disabled:opacity-40">
                          {busy === row.id
                            ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            : <Download className="h-3.5 w-3.5" />}
                        </button>
                        <Link href={`/trainer/imports/${row.id}`}
                          aria-label="Open this import" title="Open this import"
                          className="flex h-7 w-7 items-center justify-center rounded border border-[#E5E7EB] bg-white text-[#374151] hover:bg-[#F9FAFB]">
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E5E7EB] px-3.5 py-2.5">
          <p className="text-[11px] text-[#6B7280]">
            {data.total === 0
              ? 'No imports'
              : `Showing ${data.showing_from} to ${data.showing_to} of ${data.total}`}
          </p>
          {data.pages > 1 && (
            <div className="flex items-center gap-0.5">
              <button type="button" disabled={data.page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                aria-label="Previous" title="Previous"
                className="flex h-7 w-7 items-center justify-center rounded border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-30">
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <span className="px-2 text-[11px] text-[#6B7280]">
                Page {data.page} of {data.pages}
              </span>
              <button type="button" disabled={data.page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
                aria-label="Next" title="Next"
                className="flex h-7 w-7 items-center justify-center rounded border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-30">
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>

        <p className="border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
          {isManager
            ? 'Every trainer’s imports into this college are listed.'
            : 'Only your own imports are listed.'}{' '}
          A sheet rewrites batch allocations, so who uploaded it is the first
          thing anyone asks when a roster looks wrong.
        </p>
      </div>
    </div>
  )
}
