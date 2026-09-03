'use client'

/**
 * One batch's product backlog: the whole User Stories screen below the batch
 * selector.
 *
 * It is a component rather than a page because two routes show it - the
 * User Stories screen itself, where the trainer picks a batch by department,
 * section and batch number, and the deep link at
 * /trainer/user-stories/<code>. Both render the same board over the same
 * request; only what sits above it differs.
 *
 * Filters follow the same rule as My Batches: `draft` is what the panel holds,
 * `query` is what has been applied, and Apply Filters is what moves one to the
 * other. Typing in the search box does not fire a request per keystroke.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Link from 'next/link'
import {
  ChevronLeft, ChevronRight, Download, GitBranch, Plus, Search,
  SlidersHorizontal, Sparkles, Upload, X,
} from 'lucide-react'
import { CARD, Failed, Loading } from '@/components/trainer/primitives'
import { BTN_OUTLINE, BTN_PRIMARY, FIELD } from './bits'
import { StoryPanel } from './StoryPanel'
import {
  AddSprintDialog, AddStoryDialog, ConnectGitDialog, ImportStoriesDialog,
} from './dialogs'
import { BoardView, SprintView, StudentCards, TableView } from './views'
import {
  addSprint, addUserStory, commentOnStory, connectGit, deleteUserStory,
  downloadStoryTemplate,
  errorText, exportUserStories, fetchUserStories, getGitConnection,
  importUserStories, patchUserStory, reorderUserStories,
} from '@/lib/trainer-api'
import type {
  GitConnection, NewSprintInput, NewStoryInput, StoryImportResult, StoryPatch,
  StoryQuery, UserStoryBoard, UserStoryRow,
} from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const PAGE_SIZES = [10, 25, 50]
const EMPTY: StoryQuery = { sort: 'created_desc', page: 1, per_page: 10 }

const VIEWS = [
  { key: 'table', label: 'Table View' },
  { key: 'board', label: 'Board View' },
  { key: 'sprint', label: 'Sprint View' },
] as const
type View = (typeof VIEWS)[number]['key']

/** The filter keys that actually narrow the list. Paging and sorting do not. */
const NARROWING = ['search', 'status', 'epic', 'assignee', 'sprint', 'priority',
  'points', 'type', 'created_by', 'date_from', 'date_to'] as const

const pageWindow = (page: number, pages: number) => {
  const start = Math.max(1, Math.min(page - 2, pages - 4))
  return Array.from({ length: Math.min(5, pages) }, (_, i) => start + i)
}

export function StoriesBoard({ code, above }: { code: string; above?: ReactNode }) {
  const [data, setData] = useState<UserStoryBoard | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  const [query, setQuery] = useState<StoryQuery>(EMPTY)
  const [draft, setDraft] = useState<StoryQuery>(EMPTY)
  const [showFilters, setShowFilters] = useState(false)
  const [view, setView] = useState<View>('table')

  // A panel opened from the table would otherwise still be squeezing the board
  // when you switch across to it.
  useEffect(() => {
    if (view === 'board') setSelectedId(null)
  }, [view])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [dialog, setDialog] = useState<'story' | 'import' | 'sprint' | 'git' | null>(null)
  // Fetched only when the dialog is opened: nobody needs the batch's
  // webhook secret on the board itself.
  const [git, setGit] = useState<GitConnection | null>(null)
  const [imported, setImported] = useState<StoryImportResult | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)

  // A different batch is a different board: story filters from the last one
  // would silently narrow this one to nothing.
  useEffect(() => {
    setData(null)
    setQuery(EMPTY)
    setDraft(EMPTY)
    setSelectedId(null)
    setNotice(null)
  }, [code])

  const load = useCallback(async () => {
    setError('')
    try {
      const board = await fetchUserStories(code, {
        ...query,
        // Board and Sprint group the whole filtered set. Paging them would
        // make the column and sprint totals disagree with what is on screen.
        per_page: view === 'table' ? query.per_page : 200,
        selected: selectedId ?? undefined,
      })
      setData(board)
      setSelectedId(board.selected?.id ?? null)
    } catch (err: any) {
      const httpStatus = err?.response?.status
      if (httpStatus === 404) { setError(`No batch found with code ${code}.`); return }
      if (httpStatus === 403) {
        setError('This batch belongs to a department you are not attached to.')
        return
      }
      setError(errorText(err, 'Could not load the user stories.'))
    }
    // `selectedId` is deliberately not a dependency: it is sent with the next
    // load rather than triggering one, so opening a story stays a single
    // request fired by the click handler.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, query, view])

  useEffect(() => { load() }, [load])

  /** Run a write, then reload so every count on screen moves together. */
  const act = useCallback(async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    setNotice(null)
    try {
      await fn()
      setNotice({ tone: 'ok', text: ok })
      await load()
      return true
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'That could not be saved.') })
      return false
    } finally {
      setBusy(false)
    }
  }, [load])

  /**
   * On the board, a card opens in its own tab.
   *
   * The side panel takes 340px, which costs the board two of its six columns -
   * and a board you have to scroll sideways stops being a board. The table and
   * sprint views have room for the panel, so they keep it.
   */
  const openInTab = (row: UserStoryRow) => {
    window.open(`/stories/${row.id}`, '_blank', 'noopener')
  }

  const openStory = async (row: UserStoryRow) => {
    setSelectedId(row.id)
    try {
      const board = await fetchUserStories(code, {
        ...query,
        per_page: view === 'table' ? query.per_page : 200,
        selected: row.id,
      })
      setData(board)
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'Could not open that story.') })
    }
  }

  const patch = (storyId: string, body: StoryPatch, ok: string) =>
    act(() => patchUserStory(code, storyId, body), ok)

  const activeCount = NARROWING.filter((k) => query[k]).length
  const set = (p: Partial<StoryQuery>) => setDraft((d) => ({ ...d, ...p }))
  const apply = () => {
    setQuery({ ...draft, page: 1 })
    setShowFilters(false)
  }
  const reset = () => { setDraft(EMPTY); setQuery(EMPTY) }
  const goPage = (page: number) => setQuery((q) => ({ ...q, page }))

  const showUnassigned = () => {
    const next = { ...EMPTY, assignee: 'unassigned' }
    setDraft(next)
    setQuery(next)
  }

  const onDeleteStory = async () => {
    const target = data?.selected
    if (!target) return
    const result = await act(() => deleteUserStory(code, target.id), '')
    if (result) {
      // Nothing is left for the panel to show, so it closes with the row.
      setSelectedId(null)
      setNotice({ tone: 'ok', text: (result as any).message ?? `${target.key} deleted.` })
      await load()
    }
  }

  const onExport = () => act(() => exportUserStories(code, query),
    'Export downloaded to your Downloads folder.')

  const openGit = async () => {
    setGit(null)
    setDialog('git')
    try {
      setGit(await getGitConnection(code))
    } catch (err: any) {
      setDialog(null)
      setNotice({ tone: 'bad', text: errorText(err, 'Could not load the repository settings.') })
    }
  }

  const saveGit = async (repoUrl: string) => {
    setBusy(true)
    try {
      setGit(await connectGit(code, { repo_url: repoUrl }))
      setNotice({ tone: 'ok', text: 'Repository saved. Add the webhook in GitHub to start tracking.' })
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'Could not save that repository.') })
    } finally {
      setBusy(false)
    }
  }

  const rotateGit = async () => {
    setBusy(true)
    try {
      setGit(await connectGit(code, { rotate_secret: true }))
      setNotice({ tone: 'ok', text: 'New secret issued. Update it in the repository webhook.' })
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'Could not rotate the secret.') })
    } finally {
      setBusy(false)
    }
  }

  /**
   * Validate first, write second.
   *
   * The trainer's template documents a Validate then Confirm step, and the
   * API takes the same file twice - so a sheet with a bad row is seen before
   * anything is created rather than after.
   */
  const onPickImport = async (file: File) => {
    setBusy(true)
    setImportFile(file)
    setImported(null)
    try {
      setImported(await importUserStories(code, file, true))
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'That sheet could not be read.') })
    } finally {
      setBusy(false)
    }
  }

  const onConfirmImport = async () => {
    if (!importFile) return
    setBusy(true)
    try {
      const result = await importUserStories(code, importFile)
      setImported(result)
      await load()
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'That sheet could not be imported.') })
    } finally {
      setBusy(false)
    }
  }

  const onAddStory = async (input: NewStoryInput) => {
    const done = await act(() => addUserStory(code, input), 'Story added to the backlog.')
    if (done) setDialog(null)
  }

  const onAddSprint = async (input: NewSprintInput) => {
    const done = await act(() => addSprint(code, input), `${input.name} added.`)
    if (done) setDialog(null)
  }

  const header = data?.header
  const from = useMemo(
    () => (!data || data.total === 0 ? 0 : (data.page - 1) * data.per_page + 1),
    [data]
  )
  const to = useMemo(
    () => (data ? Math.min(data.page * data.per_page, data.total) : 0),
    [data]
  )

  if (error) {
    return <div className="space-y-3">{above}<Failed message={error} onRetry={load} /></div>
  }
  if (!data || !header) {
    return <div className="space-y-3">{above}<Loading label="Loading user stories…" /></div>
  }

  return (
    <div className="space-y-3">
      {above}

      {/* ------------------------------------------------------------ header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-[22px] font-bold leading-tight text-[#1B1B3A]">
            User Stories
            <span className="rounded-md bg-[#F4F5FA] px-2 py-0.5 text-[11.5px] font-medium text-[#6B7280]">
              {data.backlog_total} {data.backlog_total === 1 ? 'story' : 'stories'}
              {data.counts.story_points > 0 && ` · ${data.counts.story_points} pts`}
            </span>
          </h1>
          <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
            Project: {header.project_title ?? 'Untitled project'}
          </p>
          <p className="text-[11.5px] text-[#9CA3AF]">
            Batch: {header.batch_code} · Guide: {header.guide ?? '—'} · {header.members} members
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={BTN_OUTLINE} disabled={busy}
            onClick={() => { setImported(null); setImportFile(null); setDialog('import') }}>
            <Upload className="h-4 w-4" /> Import Stories
          </button>
          <button type="button" className={BTN_OUTLINE} disabled={busy || data.total === 0}
            onClick={onExport}>
            <Download className="h-4 w-4" /> Export
          </button>
          <button type="button" className={BTN_OUTLINE} disabled={busy}
            onClick={openGit} title="Track the team's commits against these stories">
            <GitBranch className="h-4 w-4" /> Connect Git
          </button>
          <button type="button" className={BTN_PRIMARY} disabled={busy}
            onClick={() => setDialog('story')}>
            <Plus className="h-4 w-4" /> Add User Story
          </button>
        </div>
      </div>

      {notice && (
        <div className={cn('flex items-start justify-between gap-3 rounded-lg border px-3 py-2 text-[12.5px]',
          notice.tone === 'ok'
            ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
            : 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]')}>
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Nothing has cleared the approval gate, so the screen says what is
          holding the backlog up instead of showing six zeroes. */}
      {data.planning && (
        <div className={cn(CARD, 'flex flex-wrap items-center gap-3 border-[#DDD6FE] bg-[#FAF9FF] p-4')}>
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#F5F3FF] text-[#7C3AED]">
            <Sparkles className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-semibold text-[#1B1B3A]">
              This backlog is still in AI Planning
            </p>
            <p className="text-[11.5px] text-[#6B7280]">
              {data.planning.drafted === 0
                ? 'No stories have been drafted for this batch yet.'
                : `${data.planning.drafted} stories drafted · `
                  + `${data.planning.needs_review} still need review`
                  + (data.planning.awaiting_move > 0
                    ? ` · ${data.planning.awaiting_move} approved and ready to move across`
                    : '')}
              . Stories appear here once they are approved and moved to the product backlog.
            </p>
          </div>
          <Link href={`/trainer/ai-planning/${encodeURIComponent(code)}`} className={BTN_PRIMARY}>
            Open AI Planning
          </Link>
        </div>
      )}

      {/* ---------------------------------------------------- list and panel */}
      <div className={cn('grid gap-3',
        data.selected && view !== 'board'
          ? 'xl:grid-cols-[minmax(0,1fr)_340px]'
          : 'grid-cols-1')}>
        <div className="space-y-3">
          <section className={cn(CARD, 'p-3')}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-[14px] font-bold text-[#1B1B3A]">Stories List</h2>
                {/* The filters live in a panel now, so the count has to be on
                    the button - otherwise a narrowed list looks like a short
                    one. */}
                <button type="button" onClick={() => setShowFilters(true)}
                  className={cn('inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5',
                    'text-[11.5px] font-medium',
                    activeCount > 0
                      ? 'border-[#BFDBFE] bg-[#EFF6FF] text-[#1D4ED8]'
                      : 'border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]')}>
                  <SlidersHorizontal className="h-3.5 w-3.5" />
                  Filters
                  {activeCount > 0 && (
                    <span className="rounded bg-[#2563EB] px-1.5 text-[10px] font-semibold text-white">
                      {activeCount}
                    </span>
                  )}
                </button>
                {activeCount > 0 && (
                  <button type="button" onClick={reset}
                    className="text-[11.5px] font-medium text-[#6B7280] hover:text-[#374151]">
                    Clear
                  </button>
                )}
                <div className="flex gap-1 rounded-lg bg-[#F4F5FA] p-0.5">
                  {VIEWS.map((v) => (
                    <button key={v.key} type="button" onClick={() => setView(v.key)}
                      className={cn('rounded-md px-2.5 py-1 text-[11.5px] font-medium transition-colors',
                        view === v.key ? 'bg-white text-[#2563EB] shadow-sm' : 'text-[#6B7280]')}>
                      {v.label}
                    </button>
                  ))}
                </div>
              </div>
              <label className="flex items-center gap-2 text-[11.5px] text-[#6B7280]">
                Sort by:
                <select value={query.sort ?? 'created_desc'} aria-label="Sort stories"
                  onChange={(e) => setQuery((q) => ({ ...q, sort: e.target.value, page: 1 }))}
                  className={cn(FIELD, 'h-8 w-auto')}>
                  {data.filters.sorts.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-3">
              {data.rows.length === 0 ? (
                <p className="px-6 py-12 text-center text-[12.5px] text-[#9CA3AF]">
                  {data.planning
                    ? 'Nothing has reached the backlog yet.'
                    : 'No stories match these filters.'}
                </p>
              ) : view === 'table' ? (
                <TableView rows={data.rows} selectedId={selectedId}
                  statuses={data.filters.statuses} onOpen={openStory}
                  onStatus={(row, status) => patch(row.id, { status }, `${row.key} moved.`)} />
              ) : view === 'board' ? (
                <BoardView rows={data.rows} statuses={data.filters.statuses}
                  selectedId={selectedId} onOpen={openInTab}
                  onStatus={(row, status) => patch(row.id, { status }, `${row.key} moved.`)}
                  onReorder={(ids) => act(() => reorderUserStories(code, ids), 'Order saved.')} />
              ) : (
                <SprintView rows={data.rows} sprints={data.filters.sprints}
                  selectedId={selectedId} onOpen={openStory}
                  onAddSprint={() => setDialog('sprint')} />
              )}
            </div>

            {view === 'table' && data.rows.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[#F1F2F8] pt-3">
                <p className="text-[11.5px] text-[#6B7280]">
                  Showing {from} to {to} of {data.total} stories
                </p>
                <div className="flex items-center gap-1.5">
                  <PageBtn onClick={() => goPage(data.page - 1)} disabled={data.page <= 1}
                    label="Previous page"><ChevronLeft className="h-3.5 w-3.5" /></PageBtn>
                  {pageWindow(data.page, data.pages).map((n) => (
                    <button key={n} type="button" onClick={() => goPage(n)}
                      aria-current={n === data.page ? 'page' : undefined}
                      className={cn('h-7 min-w-[28px] rounded-lg px-2 text-[11.5px] font-medium',
                        n === data.page
                          ? 'bg-[#2563EB] text-white'
                          : 'border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]')}>
                      {n}
                    </button>
                  ))}
                  <PageBtn onClick={() => goPage(data.page + 1)} disabled={data.page >= data.pages}
                    label="Next page"><ChevronRight className="h-3.5 w-3.5" /></PageBtn>
                  <select value={data.per_page} aria-label="Rows per page"
                    onChange={(e) =>
                      setQuery((q) => ({ ...q, per_page: Number(e.target.value), page: 1 }))}
                    className={cn(FIELD, 'ml-1 h-7 w-auto')}>
                    {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
                  </select>
                </div>
              </div>
            )}
          </section>

          {data.students.length > 0 && (
            <section className={cn(CARD, 'p-3')}>
              <h2 className="mb-2.5 text-[14px] font-bold text-[#1B1B3A]">
                Stories Assigned to Students
              </h2>
              <StudentCards students={data.students} onShowUnassigned={showUnassigned} />
            </section>
          )}
        </div>

        {data.selected && view !== 'board' && (
          <div className={cn(CARD, 'h-fit xl:sticky xl:top-4')}>
            <StoryPanel
              story={data.selected}
              sprints={data.filters.sprints}
              assignees={data.filters.assignees}
              statuses={data.filters.statuses}
              priorities={data.filters.priorities}
              types={data.filters.types}
              busy={busy}
              historyHref={`/trainer/ai-planning/${encodeURIComponent(code)}`}
              onPatch={(body) => patch(data.selected!.id, body, `${data.selected!.key} saved.`)}
              onComment={async (body) => {
                await act(() => commentOnStory(code, data.selected!.id, body), 'Comment added.')
              }}
              onClose={() => { setSelectedId(null); setData({ ...data, selected: null }) }}
              onDelete={onDeleteStory}
            />
          </div>
        )}
      </div>

      {/* --------------------------------------------------- filter panel */}
      {showFilters && (
        <div className="fixed inset-0 z-[60] flex justify-end" role="dialog" aria-modal="true"
          aria-label="Filter stories">
          {/* The backdrop is a sibling of the panel, so a click inside the
              panel never reaches it and shuts the panel mid-edit. */}
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowFilters(false)} />
          <aside className="relative flex h-full w-full max-w-[340px] flex-col bg-white shadow-xl">
            <header className="flex items-center justify-between border-b border-[#E5E7EB] px-4 py-3">
              <div>
                <h2 className="text-[14px] font-bold text-[#1B1B3A]">Filters</h2>
                <p className="text-[11px] text-[#6B7280]">
                  {activeCount === 0 ? 'Nothing applied'
                    : `${activeCount} applied`}
                </p>
              </div>
              <button type="button" onClick={() => setShowFilters(false)}
                aria-label="Close filters"
                className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
              <label className="block">
                <span className="block text-[11.5px] font-medium text-[#374151]">Search</span>
                <span className="relative mt-1 block">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
                  <input value={draft.search ?? ''} placeholder="ID, title or keyword…"
                    onChange={(e) => set({ search: e.target.value })}
                    onKeyDown={(e) => { if (e.key === 'Enter') apply() }}
                    className={cn(FIELD, 'pl-8')} />
                </span>
              </label>

              <Select label="Status" all="All Status" value={draft.status}
                options={data.filters.statuses} onChange={(v) => set({ status: v })} />
              <Select label="Epic" all="All Epics" value={draft.epic}
                options={data.filters.epics.map((e) => ({
                  value: e.key, label: `${e.key} · ${e.title}`,
                }))}
                onChange={(v) => set({ epic: v })} />
              <Select label="Assignee" all="All Students" value={draft.assignee}
                options={[
                  { value: 'unassigned', label: 'Unassigned' },
                  ...data.filters.assignees.map((a) => ({
                    value: a.id, label: a.roll ? `${a.roll} · ${a.name}` : a.name,
                  })),
                ]}
                onChange={(v) => set({ assignee: v })} />
              <Select label="Sprint" all="All Sprints" value={draft.sprint}
                options={[
                  { value: 'unscheduled', label: 'Unscheduled' },
                  ...data.filters.sprints.map((s) => ({ value: s.id, label: s.name })),
                ]}
                onChange={(v) => set({ sprint: v })} />
              <Select label="Priority" all="All Priorities" value={draft.priority}
                options={data.filters.priorities} onChange={(v) => set({ priority: v })} />
              <Select label="Story Points" all="All" value={draft.points}
                options={data.filters.points.map((p) => ({
                  value: String(p), label: String(p),
                }))}
                onChange={(v) => set({ points: v })} />
              <Select label="Type" all="All" value={draft.type}
                options={data.filters.types} onChange={(v) => set({ type: v })} />
              <Select label="Created By" all="All" value={draft.created_by}
                options={data.filters.creators.map((c) => ({ value: c, label: c }))}
                onChange={(v) => set({ created_by: v })} />

              {/* The panel is tall enough to show the date range outright, so
                  the old More Filters step has nothing left to hide. */}
              <div className="grid grid-cols-2 gap-2">
                <label className="block">
                  <span className="block text-[11.5px] font-medium text-[#374151]">
                    Created from
                  </span>
                  <input type="date" value={draft.date_from ?? ''} className={cn(FIELD, 'mt-1')}
                    onChange={(e) => set({ date_from: e.target.value })} />
                </label>
                <label className="block">
                  <span className="block text-[11.5px] font-medium text-[#374151]">
                    Created to
                  </span>
                  <input type="date" value={draft.date_to ?? ''} className={cn(FIELD, 'mt-1')}
                    onChange={(e) => set({ date_to: e.target.value })} />
                </label>
              </div>
            </div>

            <footer className="flex items-center justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
              <button type="button" onClick={reset}
                className="mr-auto text-[12px] font-medium text-[#6B7280] hover:text-[#374151]">
                Reset
              </button>
              <button type="button" className={BTN_OUTLINE}
                onClick={() => setShowFilters(false)}>Cancel</button>
              <button type="button" className={BTN_PRIMARY} onClick={apply}>Apply Filters</button>
            </footer>
          </aside>
        </div>
      )}

      {dialog === 'story' && (
        <AddStoryDialog
          epics={data.filters.epics} sprints={data.filters.sprints}
          assignees={data.filters.assignees} priorities={data.filters.priorities}
          types={data.filters.types} statuses={data.filters.statuses}
          busy={busy} onClose={() => setDialog(null)} onSubmit={onAddStory} />
      )}

      {dialog === 'import' && (
        <ImportStoriesDialog busy={busy} result={imported} file={importFile}
          onClose={() => setDialog(null)}
          onTemplate={() => downloadStoryTemplate(code).catch(() =>
            setNotice({ tone: 'bad', text: 'Could not download the template.' }))}
          onPick={onPickImport} onConfirm={onConfirmImport} />
      )}

      {dialog === 'sprint' && (
        <AddSprintDialog busy={busy} onClose={() => setDialog(null)} onSubmit={onAddSprint} />
      )}

      {dialog === 'git' && (
        <ConnectGitDialog busy={busy} connection={git} onClose={() => setDialog(null)}
          onSave={saveGit} onRotate={rotateGit} />
      )}
    </div>
  )
}

function Select({ label, all, value, options, onChange }: {
  label: string
  all: string
  value: string | undefined
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  return (
    <label className="block">
      <span className="block text-[11.5px] font-medium text-[#374151]">{label}</span>
      <select value={value ?? ''} onChange={(e) => onChange(e.target.value)}
        className={cn(FIELD, 'mt-1')}>
        <option value="">{all}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  )
}

function PageBtn({ onClick, disabled, label, children }: {
  onClick: () => void
  disabled: boolean
  label: string
  children: ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
      {children}
    </button>
  )
}
