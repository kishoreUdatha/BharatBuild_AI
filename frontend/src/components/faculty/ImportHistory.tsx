'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Download,
  FileSpreadsheet,
  FileUp,
  Loader2,
  RefreshCw,
  Search,
  Table2,
  Upload,
  Users,
  XCircle,
} from 'lucide-react'
import {
  errorMessage,
  archiveImports,
  downloadImportErrors,
  downloadImportOriginal,
  downloadImportTemplate,
  fetchImportDetail,
  fetchImports,
  uploadImport,
  type FacultyFilterOptions,
  type ImportDetail,
  type ImportsView,
} from '@/lib/faculty-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
const CELL = 'px-2 py-2'
// These previously summed past the container, so the table overflowed and drew
// a scrollbar while File Name was squeezed to nothing. File Name now takes the
// remainder and the rest are sized to their content.
// Measured against the widest real content: the "Partially Imported" pill
// needs 113px and the "View Details" button 88px. Undersizing those two made
// their nowrap content spill past the column and pull a scrollbar into view.
const COL_WIDTHS = ['26px', '90px', 'auto', '86px', '42px', '40px', '58px', '44px', '46px', '114px', '68px', '50px', '88px']

const KPI_TILE: Record<string, string> = {
  total: 'bg-[#6D5AE6]', processed: 'bg-[#3B82F6]', imported: 'bg-[#16A34A]',
  failed: 'bg-[#EF4444]', duplicates: 'bg-[#F97316]', attention: 'bg-[#8B5CF6]',
}
const KPI_ICON: Record<string, typeof Upload> = {
  total: FileUp, processed: Table2, imported: CheckCircle2,
  failed: XCircle, duplicates: FileSpreadsheet, attention: AlertTriangle,
}

const STATUS_TONE: Record<string, string> = {
  successful: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  partially_imported: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  failed: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  processing: 'border-[#C7D2FE] bg-[#EEF2FF] text-[#4F46E5]',
}

const SUB_TABS = [
  { key: '', label: 'All Imports' },
  { key: 'successful', label: 'Successful' },
  { key: 'partially_imported', label: 'Partially Imported' },
  { key: 'failed', label: 'Failed' },
  { key: 'processing', label: 'Processing' },
]

const SELECT_CLASS =
  'h-8 w-full appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]'

const fmtSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`

export function ImportHistory({
  options,
  onNotice,
}: {
  options: FacultyFilterOptions | null
  onNotice: (message: string) => void
}) {
  const [filters, setFilters] = useState<Record<string, string | undefined>>({})
  const [subTab, setSubTab] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const [view, setView] = useState<ImportsView | null>(null)
  const [detail, setDetail] = useState<ImportDetail | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploadType, setUploadType] = useState('student_list')
  const fileInput = useRef<HTMLInputElement>(null)

  const query = useMemo(
    () => ({ ...filters, import_status: subTab || undefined, search: search || undefined, page, per_page: perPage }),
    [filters, subTab, search, page, perPage]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchImports(query)
      setView(data)
      setDetail(data.selected)
    } catch (err: any) {
      setError(errorMessage(err, 'Could not load import history.'))
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => { load() }, [load])
  useEffect(() => setSelected([]), [subTab, page, perPage, search, filters])

  const rows = view?.rows ?? []
  const allChecked = rows.length > 0 && selected.length === rows.length

  const openDetail = async (id: string) => {
    try { setDetail(await fetchImportDetail(id)) }
    catch { onNotice('Could not open that import.') }
  }

  const onFilePicked = async (file: File | undefined) => {
    if (!file) return
    setBusy(true)
    try {
      const result = await uploadImport(file, uploadType, { department: filters.department })
      setDetail(result)
      onNotice(
        `${result.import_code}: ${result.rows_imported} imported, ` +
        `${result.rows_failed} failed, ${result.rows_duplicate} duplicate(s) skipped.`
      )
      await load()
    } catch (err: any) {
      onNotice(errorMessage(err, 'The file could not be imported.'))
    } finally {
      setBusy(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    try { await fn(); onNotice(ok) }
    catch { onNotice('That action could not be completed.') }
    finally { setBusy(false) }
  }

  return (
    <>
      <input ref={fileInput} type="file" accept=".csv,.xlsx,.xlsm" className="hidden"
        onChange={(e) => onFilePicked(e.target.files?.[0])} />

      {/* Upload strip */}
      <section className={cn(CARD, 'flex flex-wrap items-center gap-2 p-2.5')}>
        <span className="text-[12px] font-medium text-[#1B1B3A]">New import</span>
        <div className="relative">
          <select value={uploadType} onChange={(e) => setUploadType(e.target.value)}
            aria-label="Import type" className={cn(SELECT_CLASS, 'w-[188px]')}>
            {(view?.import_types ?? [{ key: 'student_list', label: 'Student List' }]).map((t) => (
              <option key={t.key} value={t.key}>{t.label}</option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
        </div>
        <button type="button" onClick={() => fileInput.current?.click()} disabled={busy}
          className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          Choose file &amp; import
        </button>
        <button type="button" disabled={busy}
          onClick={() => act(() => downloadImportTemplate(uploadType), 'Template downloaded.')}
          className="flex items-center gap-2 rounded-lg border border-[#C7BDF5] bg-white px-4 py-2 text-[12px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF] disabled:opacity-50">
          <Download className="h-4 w-4" /> Download Template
        </button>
        <span className="text-[11px] text-[#8A8FA8]">CSV or XLSX, up to 5 MB. Rows are validated before anything is written.</span>
      </section>

      {/* Filters */}
      <section className={cn(CARD, 'grid grid-cols-2 gap-2.5 p-2.5 md:grid-cols-3 xl:grid-cols-5')}>
        <div>
          <label htmlFor="m-dept" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Department</label>
          <div className="relative">
            <select id="m-dept" value={filters.department ?? 'All Departments'} className={SELECT_CLASS}
              onChange={(e) => { const v = e.target.value; setFilters((p) => ({ ...p, department: v.startsWith('All ') ? undefined : v })); setPage(1) }}>
              {['All Departments', ...((options?.departments ?? []))].map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
          </div>
        </div>
        <div>
          <label htmlFor="m-type" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Import Type</label>
          <div className="relative">
            <select id="m-type" value={filters.import_type ?? ''} className={SELECT_CLASS}
              onChange={(e) => { setFilters((p) => ({ ...p, import_type: e.target.value || undefined })); setPage(1) }}>
              <option value="">All Types</option>
              {(view?.import_types ?? []).map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
          </div>
        </div>
        <div>
          <label htmlFor="m-status" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Status</label>
          <div className="relative">
            <select id="m-status" value={subTab} className={SELECT_CLASS}
              onChange={(e) => { setSubTab(e.target.value); setPage(1) }}>
              {SUB_TABS.map((t) => <option key={t.key} value={t.key}>{t.key ? t.label : 'All Statuses'}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
          </div>
        </div>
        <div>
          <label htmlFor="m-by" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Imported By</label>
          <div className="relative">
            <select id="m-by" value={filters.imported_by ?? ''} className={SELECT_CLASS}
              onChange={(e) => { setFilters((p) => ({ ...p, imported_by: e.target.value || undefined })); setPage(1) }}>
              <option value="">All Users</option>
              {(view?.importers ?? []).map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
          </div>
        </div>
        <div>
          <label htmlFor="m-search" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Search</label>
          <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1) }} className="relative">
            <input id="m-search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
              placeholder="File name, import ID or imported by…"
              className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] outline-none focus:border-[#4F46E5]" />
            <button type="submit" aria-label="Search imports" className="absolute right-2 top-1/2 -translate-y-1/2">
              <Search className="h-3.5 w-3.5 text-[#8A8FA8]" />
            </button>
          </form>
        </div>
      </section>

      {/* KPIs */}
      <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
        {(view?.kpis ?? []).map((k) => {
          const Icon = KPI_ICON[k.id] ?? FileUp
          return (
            <div key={k.id} className={cn(CARD, 'flex items-center gap-2.5 p-2')}>
              <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl', KPI_TILE[k.id])}>
                <Icon className="h-4 w-4 text-white" />
              </span>
              <div className="min-w-0">
                <p className="text-[19px] font-bold leading-none text-[#1B1B3A]">{k.value}</p>
                <p className="mt-0.5 text-[11px] leading-tight text-[#5A5F7A]">{k.label}</p>
              </div>
            </div>
          )
        })}
      </section>

      {/* This table carries 13 columns, so it needs ~700px of its own. A 2.4/1
          split only clears that past ~1400px viewport; below it the detail
          panel stacks underneath rather than starving the table. */}
      <div className="grid gap-2.5 min-[1400px]:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)]">
        <section className={cn(CARD, 'p-4')}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-1 rounded-lg bg-[#F4F5FA] p-0.5">
              {SUB_TABS.map((t) => (
                <button key={t.key} type="button" onClick={() => { setSubTab(t.key); setPage(1) }}
                  className={cn('rounded-md px-3 py-1.5 text-[11.5px]',
                    subTab === t.key ? 'bg-[#4F46E5] font-medium text-white' : 'text-[#5A5F7A] hover:text-[#1B1B3A]')}>
                  {t.label}
                </button>
              ))}
            </div>
            <button type="button" disabled={!selected.length || busy}
              onClick={() => act(async () => { await archiveImports(selected); await load() }, `Archived ${selected.length} import(s).`)}
              className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] bg-white px-3 py-1.5 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40">
              <Archive className="h-3.5 w-3.5" /> Archive Selected
            </button>
          </div>

          <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Import History</h2>

          {loading ? (
            <div className="flex h-[220px] items-center justify-center gap-2 text-[#5A5F7A]">
              <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> <span className="text-[12px]">Loading…</span>
            </div>
          ) : error ? (
            <div className="flex h-[220px] flex-col items-center justify-center gap-3">
              <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
              <p className="text-[12px] text-[#5A5F7A]">{error}</p>
              <button type="button" onClick={load} className="rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white">Retry</button>
            </div>
          ) : rows.length === 0 ? (
            <div className="flex h-[220px] flex-col items-center justify-center gap-2">
              <FileUp className="h-6 w-6 text-[#C7CBDD]" />
              <p className="text-[12px] text-[#8A8FA8]">No imports yet. Upload a roster above to get started.</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full table-fixed border-collapse text-[11.5px]">
                  <colgroup>{COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
                  <thead>
                    <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                      <th className={cn(CELL, 'text-left')}>
                        <input type="checkbox" checked={allChecked} aria-label="Select all imports"
                          onChange={() => setSelected(allChecked ? [] : rows.map((r) => r.id))} />
                      </th>
                      {['Import ID', 'File Name', 'Type', 'Dept', 'Rows', 'Imported', 'Failed', 'Dupes', 'Status', 'By', 'Date', 'Action'].map((h, i) => (
                        <th key={h} className={cn(CELL, 'font-medium', i <= 1 ? 'text-left' : 'text-center')}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} className={cn('border-b border-[#F1F2F8]', detail?.id === r.id && 'bg-[#F5F3FF]')}>
                        <td className={CELL}>
                          <input type="checkbox" checked={selected.includes(r.id)} aria-label={`Select ${r.import_code}`}
                            onChange={() => setSelected((s) => s.includes(r.id) ? s.filter((x) => x !== r.id) : [...s, r.id])} />
                        </td>
                        <td className={CELL}>
                          <button type="button" onClick={() => openDetail(r.id)}
                            className="whitespace-nowrap font-medium text-[#4F46E5] hover:underline">{r.import_code}</button>
                        </td>
                        <td className={cn(CELL, 'truncate text-[#3A3F58]')} title={r.file_name}>{r.file_name}</td>
                        <td className={cn(CELL, 'truncate text-center text-[#3A3F58]')}>{r.import_type}</td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.department ?? '–'}</td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.rows_total}</td>
                        <td className={cn(CELL, 'text-center font-medium text-[#16A34A]')}>{r.rows_imported}</td>
                        <td className={cn(CELL, 'text-center font-medium', r.rows_failed ? 'text-[#DC2626]' : 'text-[#8A8FA8]')}>{r.rows_failed}</td>
                        <td className={cn(CELL, 'text-center font-medium', r.rows_duplicate ? 'text-[#D97706]' : 'text-[#8A8FA8]')}>{r.rows_duplicate}</td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn('whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px]', STATUS_TONE[r.status_key])}>
                            {r.status}
                          </span>
                        </td>
                        <td className={cn(CELL, 'truncate text-center text-[#3A3F58]')}>{r.imported_by ?? '–'}</td>
                        <td className={cn(CELL, 'whitespace-nowrap text-center text-[10.5px] text-[#5A5F7A]')}>
                          {new Date(r.started_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          <button type="button" onClick={() => openDetail(r.id)}
                            className={cn('whitespace-nowrap rounded-md border px-2 py-1 text-[10.5px] font-medium',
                              r.status_key === 'failed'
                                ? 'border-[#FECACA] text-[#DC2626] hover:bg-[#FEF2F2]'
                                : 'border-[#DDE0EE] text-[#4F46E5] hover:bg-[#F7F8FC]')}>
                            {r.action}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] text-[#8A8FA8]">
                  Showing {view?.showing_from} to {view?.showing_to} of {view?.total} imports
                </p>
                <div className="flex items-center gap-2">
                  <Pager onClick={() => setPage((p) => p - 1)} disabled={(view?.page ?? 1) <= 1} aria-label="Previous page">
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </Pager>
                  <span className="text-[11px] text-[#3A3F58]">Page {view?.page} of {view?.pages}</span>
                  <Pager onClick={() => setPage((p) => p + 1)} disabled={(view?.page ?? 1) >= (view?.pages ?? 1)} aria-label="Next page">
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Pager>
                  <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
                    aria-label="Imports per page"
                    className="h-7 rounded-md border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]">
                    {[10, 25, 50].map((n) => <option key={n} value={n}>{n} per page</option>)}
                  </select>
                </div>
              </div>
            </>
          )}
        </section>

        {/* Selected import */}
        <div className="space-y-2.5">
          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">
              Selected Import {detail ? `— ${detail.import_code}` : ''}
            </h2>
            {detail ? (
              <>
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-md bg-[#DCFCE7] text-[#15803D]">
                    <FileSpreadsheet className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-[11.5px] font-medium text-[#1B1B3A]" title={detail.file_name}>{detail.file_name}</p>
                    <p className="text-[10.5px] text-[#8A8FA8]">{fmtSize(detail.file_size)}</p>
                  </div>
                </div>
                <ul className="space-y-0.5 text-[11px]">
                  <Line label="Uploaded by" value={detail.imported_by ?? '–'} />
                  <Line label="Started" value={new Date(detail.started_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })} />
                  <Line label="Duration" value={`${detail.duration_seconds} second(s)`} />
                </ul>
                <div className="mt-2 flex items-center gap-2">
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F7]">
                    <span className="block h-full rounded-full bg-[#4F46E5]" style={{ width: `${detail.percent_processed}%` }} />
                  </span>
                  <span className="text-[10.5px] text-[#5A5F7A]">{detail.percent_processed}% Processed</span>
                </div>
                <div className="mt-3 grid grid-cols-4 gap-1.5 text-center">
                  <Stat value={detail.rows_total} label="Total" tone="text-[#1B1B3A]" />
                  <Stat value={detail.rows_imported} label="Imported" tone="text-[#16A34A]" />
                  <Stat value={detail.rows_failed} label="Failed" tone="text-[#DC2626]" />
                  <Stat value={detail.rows_duplicate} label="Dupes" tone="text-[#D97706]" />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <button type="button" disabled={busy}
                    onClick={() => act(() => downloadImportOriginal(detail.id, detail.file_name), 'Original file downloaded.')}
                    className="flex items-center justify-center gap-1.5 rounded-lg border border-[#DDE0EE] py-1.5 text-[11px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-50">
                    <Download className="h-3.5 w-3.5" /> Original
                  </button>
                  <button type="button" disabled={busy || detail.issue_count === 0}
                    onClick={() => act(() => downloadImportErrors(detail.id, detail.import_code), 'Error file downloaded.')}
                    className="flex items-center justify-center gap-1.5 rounded-lg border border-[#FECACA] py-1.5 text-[11px] text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-40">
                    <Download className="h-3.5 w-3.5" /> Error File
                  </button>
                </div>
              </>
            ) : (
              <p className="py-6 text-center text-[11px] text-[#8A8FA8]">Select an import to see its summary.</p>
            )}
          </section>

          {detail && detail.issues.length > 0 && (
            <section className={cn(CARD, 'p-4')}>
              <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Validation Issues</h2>
              <ul className="space-y-1">
                {detail.issues.slice(0, 8).map((i, idx) => (
                  <li key={`${i.row}-${idx}`} className="flex items-start gap-2 text-[11px]">
                    <AlertCircle className={cn('mt-0.5 h-3.5 w-3.5 shrink-0',
                      i.severity === 'duplicate' ? 'text-[#D97706]' : 'text-[#DC2626]')} />
                    <span className="w-[46px] shrink-0 text-[#8A8FA8]">Row {i.row}</span>
                    <span className="flex-1 text-[#3A3F58]">{i.message}</span>
                  </li>
                ))}
              </ul>
              {detail.issue_count > 8 && (
                <p className="mt-2 text-[10.5px] text-[#8A8FA8]">
                  Showing 8 of {detail.issue_count}. Download the error file for all rows.
                </p>
              )}
            </section>
          )}
        </div>
      </div>

      {/* Timeline + actions */}
      {detail && (
        <section className={cn(CARD, 'p-4')}>
          <h2 className="mb-3 text-[14px] font-semibold text-[#1B1B3A]">Import Activity Timeline</h2>
          <ol className="flex flex-wrap gap-x-2 gap-y-3">
            {detail.timeline.map((e, i) => (
              <li key={`${e.step}-${i}`} className="flex min-w-[150px] flex-1 items-start gap-2">
                <span className={cn('flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
                  e.is_warning ? 'bg-[#FEF3C7] text-[#B45309]' : 'bg-[#EEF2FF] text-[#4F46E5]')}>
                  {e.is_warning ? <AlertTriangle className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                </span>
                <span className="min-w-0">
                  <span className="block text-[11.5px] font-medium text-[#1B1B3A]">{e.step}</span>
                  <span className="block text-[10px] text-[#8A8FA8]">
                    {new Date(e.occurred_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} · {e.actor}
                  </span>
                  {e.note && <span className="block text-[10px] text-[#5A5F7A]">{e.note}</span>}
                </span>
              </li>
            ))}
          </ol>

          <div className="mt-3 flex flex-wrap gap-2 border-t border-[#EEF0F7] pt-3">
            <Act icon={Upload} label="Correct & Re-upload" onClick={() => fileInput.current?.click()} />
            <Act icon={RefreshCw} label="Retry Failed Rows"
              onClick={() => onNotice('Download the error file, correct the rows, then re-upload — a re-import skips anything already loaded, so only the corrected rows land.')} />
            <Act icon={Users} label="View Imported Students"
              onClick={() => onNotice('Imported students appear on the Student Registrations tab; filter by section to see them.')} />
            <Act icon={Archive} label="Archive Import" disabled={busy}
              onClick={() => act(async () => { await archiveImports([detail.id]); await load() }, `${detail.import_code} archived.`)} />
          </div>
        </section>
      )}

      {/* Policy footer */}
      <section className={cn(CARD, 'grid gap-3 p-3 text-[10.5px] leading-snug text-[#5A5F7A] md:grid-cols-2')}>
        <p className="flex gap-2">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#4F46E5]" />
          Imports never overwrite verified student records automatically. Duplicates are skipped and failed rows require correction.
        </p>
        <p className="flex gap-2">
          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#4F46E5]" />
          Every run keeps its original file, per-row issues and step timeline, so an import can be traced back to its source.
        </p>
      </section>
    </>
  )
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex justify-between gap-2">
      <span className="text-[#8A8FA8]">{label}</span>
      <span className="truncate text-right text-[#1B1B3A]">{value}</span>
    </li>
  )
}

function Stat({ value, label, tone }: { value: number; label: string; tone: string }) {
  return (
    <div className="rounded-lg border border-[#EEF0F7] py-1.5">
      <p className={cn('text-[15px] font-bold leading-none', tone)}>{value}</p>
      <p className="mt-0.5 text-[9.5px] text-[#8A8FA8]">{label}</p>
    </div>
  )
}

function Act({ icon: Icon, label, onClick, disabled }: { icon: typeof Upload; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] px-3 py-2 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40">
      <Icon className="h-3.5 w-3.5 text-[#4F46E5]" /> {label}
    </button>
  )
}

function Pager({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" {...props}
      className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40">
      {children}
    </button>
  )
}
