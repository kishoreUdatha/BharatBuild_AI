'use client'

/**
 * My Stories - every user story assigned to the signed-in student.
 *
 * Scoped by assignee on the server, so this is their work rather than the
 * batch's whole backlog. The tabs and the filter row drive the same query:
 * a tab is just the status filter with a count attached.
 */

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, ChevronsLeft,
  ChevronsRight, Copy, ExternalLink, Eye, GitBranch, GitCommitHorizontal,
  Github, Loader2, Plus, Search, X,
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'
const FIELD = 'h-9 rounded-lg border border-[#D1D5DB] bg-white px-2.5 text-[12.5px] ' +
  'text-[#374151] outline-none focus:border-[#2563EB]'
const PAGE_SIZES = [10, 25, 50]

interface StoryRow {
  id: string
  key: string
  title: string
  epic: string
  priority: string
  priority_label: string
  story_points: number
  status: string
  status_label: string
  sprint: string | null
  due_date: string | null
  batch_code: string | null
  narrative: string | null
  acceptance_criteria: { text: string; met: boolean }[]
}

interface StoriesView {
  rows: StoryRow[]
  total: number
  page: number
  pages: number
  per_page: number
  counts: Record<string, number>
  filters: {
    statuses: { value: string; label: string }[]
    priorities: { value: string; label: string }[]
    sprints: string[]
  }
}

const PRIORITY_STYLE: Record<string, string> = {
  high: 'bg-[#FEE2E2] text-[#DC2626]',
  medium: 'bg-[#FEF3C7] text-[#B45309]',
  low: 'bg-[#DCFCE7] text-[#15803D]',
}

const STATUS_STYLE: Record<string, string> = {
  to_do: 'bg-[#FEF3C7] text-[#B45309]',
  in_progress: 'bg-[#DBEAFE] text-[#1D4ED8]',
  testing: 'bg-[#CFFAFE] text-[#0E7490]',
  in_review: 'bg-[#EDE9FE] text-[#6D28D9]',
  done: 'bg-[#DCFCE7] text-[#15803D]',
  blocked: 'bg-[#FEE2E2] text-[#B91C1C]',
}

const fmtDue = (iso: string | null) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? '—'
    : d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function MyStoriesPage() {
  const [data, setData] = useState<StoriesView | null>(null)
  const [error, setError] = useState('')

  const [gitOpen, setGitOpen] = useState(false)
  // Set by the OAuth callback on its way back here.
  const [gitNotice, setGitNotice] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const outcome = params.get('git')
    if (!outcome) return
    setGitNotice(outcome === 'linked'
      ? { ok: true, text: 'GitHub connected. Your commits are credited to you from now on.' }
      : { ok: false, text: params.get('reason') || 'GitHub could not be connected.' })
    if (outcome === 'linked') setGitOpen(true)
    // Take it out of the URL so a refresh does not repeat the message.
    window.history.replaceState({}, '', window.location.pathname)
  }, [])
  const [view, setView] = useState<'stories' | 'commits'>('stories')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [priority, setPriority] = useState('')
  const [sprint, setSprint] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const load = useCallback(async () => {
    setError('')
    try {
      const params: Record<string, string | number> = { page, per_page: perPage }
      if (search) params.search = search
      if (status) params.status = status
      if (priority) params.priority = priority
      if (sprint) params.sprint = sprint
      setData(await apiClient.get<StoriesView>('/student/stories', { params }))
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not load your stories.')
    }
  }, [search, status, priority, sprint, page, perPage])

  useEffect(() => { load() }, [load])

  /** Same destination as the trainer board: the story's own page, new tab. */
  const openStory = (id: string) => window.open(`/stories/${id}`, '_blank', 'noopener')

  const clearFilters = () => {
    setSearch(''); setStatus(''); setPriority(''); setSprint(''); setPage(1)
  }

  if (error) {
    return (
      <div className={cn(CARD, 'p-8 text-center text-[12.5px] text-[#DC2626]')}>
        {error}
      </div>
    )
  }
  if (!data) {
    return (
      <div className={cn(CARD, 'flex h-[320px] flex-col items-center justify-center gap-2')}>
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
        <p className="text-[12.5px] text-[#6B7280]">Loading your stories…</p>
      </div>
    )
  }

  const c = data.counts
  const from = data.total === 0 ? 0 : (data.page - 1) * data.per_page + 1
  const to = Math.min(data.page * data.per_page, data.total)

  // A tab is the status filter with a count on it. The stages come from the
  // API's own status list, so adding one to the workflow adds its tab here
  // rather than leaving those stories reachable only through "All".
  const TABS: { value: string; label: string; count: number }[] = [
    { value: '', label: 'All Stories', count: c.total ?? 0 },
    ...data.filters.statuses.map((s) => ({
      value: s.value,
      label: s.value === 'done' ? 'Completed' : s.label,
      count: c[s.value] ?? 0,
    })),
  ]

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">My Stories</h1>
          <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
            All the user stories assigned to you.
          </p>
        </div>
        <button type="button" onClick={() => setGitOpen(true)}
          title="Link your own git account so your commits are credited to you"
          className="flex h-9 items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 text-[12.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
          <GitBranch className="h-4 w-4" /> My Git Account
        </button>
      </div>

      {gitNotice && (
        <div className={cn('flex items-start justify-between gap-3 rounded-lg border px-3 py-2 text-[12.5px]',
          gitNotice.ok
            ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
            : 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]')}>
          <span>{gitNotice.text}</span>
          <button type="button" onClick={() => setGitNotice(null)} aria-label="Dismiss">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {gitOpen && <GitIdentityDialog onClose={() => setGitOpen(false)} />}

      {/* Two halves of the same work: what was assigned, and what was pushed. */}
      <div className="flex gap-1 border-b border-[#E5E7EB]">
        {([['stories', 'My Stories'], ['commits', 'My Commits']] as const).map(([key, label]) => (
          <button key={key} type="button" onClick={() => setView(key)}
            className={cn('-mb-px border-b-2 px-3 py-2 text-[12.5px] transition-colors',
              view === key
                ? 'border-[#2563EB] font-semibold text-[#2563EB]'
                : 'border-transparent text-[#6B7280] hover:text-[#374151]')}>
            {label}
          </button>
        ))}
      </div>

      {view === 'commits' && <MyCommits />}

      {view === 'stories' && (<>
      {/* --------------------------------------------------------- filters */}
      <div className={cn(CARD, 'flex flex-wrap items-center gap-3 p-3.5')}>
        <span className="relative block min-w-[220px] flex-1">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
          <input value={search} aria-label="Search stories"
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search by title, ID or epic…"
            className={cn(FIELD, 'w-full pl-8')} />
        </span>

        <label className="flex items-center gap-1.5 text-[12px] text-[#374151]">
          Status
          <select value={status} aria-label="Filter by status"
            onChange={(e) => { setStatus(e.target.value); setPage(1) }} className={FIELD}>
            <option value="">All</option>
            {data.filters.statuses.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-[12px] text-[#374151]">
          Priority
          <select value={priority} aria-label="Filter by priority"
            onChange={(e) => { setPriority(e.target.value); setPage(1) }} className={FIELD}>
            <option value="">All</option>
            {data.filters.priorities.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-[12px] text-[#374151]">
          Sprint
          <select value={sprint} aria-label="Filter by sprint"
            onChange={(e) => { setSprint(e.target.value); setPage(1) }} className={FIELD}>
            <option value="">All</option>
            {data.filters.sprints.map((s) => <option key={s} value={s}>{s}</option>)}
            <option value="none">No sprint</option>
          </select>
        </label>

        <button type="button" onClick={clearFilters}
          className="rounded-lg border border-[#2563EB] px-3 py-1.5 text-[12px] font-medium text-[#2563EB] hover:bg-[#F4F7FF]">
          Clear Filters
        </button>
      </div>

      {/* ---------------------------------------------------- list + panel */}
      {/* Same shape as the trainer's board: the story opens beside the list
          rather than over it, so the row it came from stays visible. */}
      <div className={cn(CARD, 'p-4')}>
        <div className="flex flex-wrap gap-4 border-b border-[#E5E7EB]">
          {TABS.map((t) => (
            <button key={t.label} type="button"
              onClick={() => { setStatus(t.value); setPage(1) }}
              className={cn('-mb-px border-b-2 pb-2 text-[12.5px] font-medium',
                status === t.value
                  ? 'border-[#2563EB] text-[#2563EB]'
                  : 'border-transparent text-[#6B7280] hover:text-[#374151]')}>
              {t.label} ({t.count})
            </button>
          ))}
        </div>

        {data.rows.length === 0 ? (
          <p className="py-10 text-center text-[12.5px] text-[#6B7280]">
            {c.total === 0
              ? 'Nothing is assigned to you yet. Stories appear here once your guide assigns them.'
              : 'No stories match these filters.'}
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-[12px]">
              <thead>
                <tr className="border-y border-[#E5E7EB] bg-[#FAFBFF] text-[11.5px] text-[#374151]">
                  {['Story ID', 'Summary / Title', 'Epic', 'Priority', 'Story Points',
                    'Status', 'Sprint', 'Due Date', 'Actions'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2.5 font-bold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F2F8]">
                {data.rows.map((r) => (
                  <tr key={r.id} onClick={() => openStory(r.id)}
                    // The row is the target, not just the icon: a student
                    // reaching for a story aims at its title. Enter opens it
                    // too, so the list stays usable from the keyboard.
                    tabIndex={0} role="button" aria-label={`Open ${r.key} in a new tab`}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        openStory(r.id)
                      }
                    }}
                    className="cursor-pointer align-middle hover:bg-[#FAFBFF] focus:bg-[#F4F7FF] focus:outline-none">
                    <td className="whitespace-nowrap px-3 py-3"
                      onClick={(e) => e.stopPropagation()}>
                      <Link href={`/stories/${r.id}`} target="_blank" rel="noopener"
                        title={`Open ${r.key} in a new tab`}
                        className="font-medium text-[#2563EB] hover:underline">
                        {r.key}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <span className="block max-w-[260px] text-[#374151]">{r.title}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">{r.epic}</td>
                    <td className="whitespace-nowrap px-3 py-3">
                      <span className={cn('rounded-md px-2 py-0.5 text-[11px] font-medium',
                        PRIORITY_STYLE[r.priority] ?? PRIORITY_STYLE.low)}>
                        {r.priority_label}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-[#4B5563]">{r.story_points}</td>
                    <td className="whitespace-nowrap px-3 py-3">
                      <span className={cn('rounded-md px-2 py-0.5 text-[11px] font-medium',
                        STATUS_STYLE[r.status] ?? STATUS_STYLE.to_do)}>
                        {r.status_label}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">{r.sprint ?? '—'}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">{fmtDue(r.due_date)}</td>
                    <td className="whitespace-nowrap px-3 py-3">
                      <Link href={`/stories/${r.id}`} target="_blank" rel="noopener"
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`Open ${r.key} in a new tab`} title="Open story"
                        className="inline-flex rounded-lg border border-[#E5E7EB] p-1.5 text-[#2563EB] hover:bg-[#F4F7FF]">
                        <Eye className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[#F1F2F8] pt-3">
          <p className="text-[11.5px] text-[#6B7280]">
            Showing {from} to {to} of {data.total} stories
          </p>
          <div className="flex items-center gap-1.5">
            <select value={perPage} aria-label="Stories per page"
              onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
              className={cn(FIELD, 'h-7 w-auto')}>
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} per page</option>)}
            </select>
            <PageBtn label="First page" disabled={data.page <= 1} onClick={() => setPage(1)}>
              <ChevronsLeft className="h-3.5 w-3.5" />
            </PageBtn>
            <PageBtn label="Previous page" disabled={data.page <= 1}
              onClick={() => setPage(data.page - 1)}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </PageBtn>
            <span className="flex h-7 min-w-[28px] items-center justify-center rounded-lg bg-[#2563EB] px-2 text-[11.5px] font-medium text-white">
              {data.page}
            </span>
            <PageBtn label="Next page" disabled={data.page >= data.pages}
              onClick={() => setPage(data.page + 1)}>
              <ChevronRight className="h-3.5 w-3.5" />
            </PageBtn>
            <PageBtn label="Last page" disabled={data.page >= data.pages}
              onClick={() => setPage(data.pages)}>
              <ChevronsRight className="h-3.5 w-3.5" />
            </PageBtn>
          </div>
        </div>
      </div>
      </>)}
    </div>
  )
}

function PageBtn({ onClick, disabled, label, children }: {
  onClick: () => void; disabled: boolean; label: string; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
      {children}
    </button>
  )
}


// ==========================================================================
// My Git Account
// ==========================================================================

interface GitIdentity {
  batch_code: string
  /** The team's repository. One per batch - the trainer connects it. */
  repo_url: string | null
  repo_connected: boolean
  /** The lead created the repo, so the lead is the one who can hook it up. */
  is_lead: boolean
  provider: string | null
  username: string | null
  emails: string[]
  verified: boolean
  verify_code: string | null
  my_commits: number
  unclaimed_commits: number
  last_commit_at: string | null
  key_example: string
}

/**
 * The student's own end of the team repository.
 *
 * Everyone on the batch pushes to the same repo, so the only thing that says
 * which commits are whose is the email each of them commits under. That is
 * personal, it is not the college address in most cases, and nobody but the
 * student knows it - so they enter it themselves rather than a trainer
 * guessing on their behalf.
 */
function GitIdentityDialog({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<GitIdentity | null>(null)
  const [username, setUsername] = useState('')
  const [emails, setEmails] = useState<string[]>([''])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  // Only fetched for the lead: it carries the push secret, and a teammate has
  // no use for it.
  const [repo, setRepo] = useState<TeamRepo | null>(null)
  const [repoUrl, setRepoUrl] = useState('')

  const load = useCallback(async () => {
    try {
      const row = await apiClient.get<GitIdentity>('/student/git')
      setData(row)
      setUsername(row.username ?? '')
      setEmails(row.emails.length ? row.emails : [''])
      if (row.is_lead) {
        const team = await apiClient.get<TeamRepo>('/student/git/repo')
        setRepo(team)
        setRepoUrl(team.repo_url ?? '')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not load your git settings.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setBusy(true)
    setError(null)
    try {
      const row = await apiClient.post<GitIdentity>('/student/git', {
        username: username.trim() || null,
        provider: 'github',
        emails: emails.map((e) => e.trim()).filter(Boolean),
      })
      setData(row)
      setEmails(row.emails.length ? row.emails : [''])
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not save that.')
    } finally {
      setBusy(false)
    }
  }

  const saveRepo = async (rotate = false) => {
    setBusy(true)
    setError(null)
    try {
      setRepo(await apiClient.post<TeamRepo>('/student/git/repo', {
        repo_url: repoUrl.trim() || null, rotate_secret: rotate,
      }))
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not save the repository.')
    } finally {
      setBusy(false)
    }
  }

  // Sends the browser to GitHub. Coming back is the callback page's job.
  const connectGitHub = async () => {
    setBusy(true)
    setError(null)
    try {
      const { authorization_url, state } = await apiClient.get<{
        authorization_url: string; state: string
      }>('/student/git/oauth/url')
      sessionStorage.setItem('oauth_state', state)
      sessionStorage.setItem('oauth_purpose', 'link_git')
      window.location.href = authorization_url
    } catch (err: any) {
      setBusy(false)
      setError(err?.response?.data?.detail
        ?? 'GitHub linking is unavailable. Enter your details by hand instead.')
    }
  }

  const copyCode = async () => {
    if (!data?.verify_code) return
    try {
      await navigator.clipboard.writeText(data.verify_code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch { /* insecure origin - the code is on screen anyway */ }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      role="dialog" aria-modal="true" aria-label="My Git Account">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative flex max-h-full w-full max-w-[560px] flex-col overflow-hidden rounded-xl bg-white shadow-xl">
        <header className="flex items-start justify-between gap-3 border-b border-[#E5E7EB] px-4 py-3">
          <div>
            <h2 className="text-[14px] font-bold text-[#1B1B3A]">My Git Account</h2>
            <p className="text-[11px] text-[#6B7280]">
              The team shares one repository. This is how your commits in it are
              recognised as yours.
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="max-h-[70vh] space-y-3 overflow-y-auto px-4 py-3">
          {!data ? (
            <p className="flex items-center gap-2 py-6 text-[12.5px] text-[#6B7280]">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </p>
          ) : (
            <>
              <div className={cn('flex items-start gap-2 rounded-lg border px-3 py-2 text-[12px]',
                data.verified
                  ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
                  : 'border-[#E5E7EB] bg-[#F9FAFC] text-[#6B7280]')}>
                <GitBranch className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  {data.my_commits} commit{data.my_commits === 1 ? '' : 's'} credited to you
                  {data.verified && ' · account verified'}
                  {data.repo_url && (
                    <>
                      {' · '}
                      <a href={data.repo_url} target="_blank" rel="noopener noreferrer"
                        className="underline">team repository</a>
                    </>
                  )}
                </span>
              </div>

              {/* At the top, not the bottom: the buttons that fail are up
                  here, and a message below the fold reads as nothing
                  happening at all. */}
              {error && (
                <p className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11.5px] text-[#DC2626]">
                  {error}
                </p>
              )}

              {!data.repo_connected && (
                <p className="flex items-start gap-1.5 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] text-[#92400E]">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    {data.is_lead
                      ? 'The team repository is not connected yet, so no commits are arriving. Set it up below — you are the one who can.'
                      : 'Nobody has connected the team repository yet, so no commits are arriving. Your batch leader sets this up. You can still add your details now.'}
                  </span>
                </p>
              )}

              {/* Two clicks instead of two fields, and GitHub confirms both
                  the account and the addresses - which is why linking this way
                  needs no verification code afterwards. */}
              {!data.verified && (
                <div className="rounded-lg border border-[#E5E7EB] bg-[#F9FAFC] px-3 py-2.5">
                  <button type="button" onClick={connectGitHub} disabled={busy}
                    className="flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-[#1B1B3A] px-3 text-[12.5px] font-medium text-white hover:bg-[#2D2D5A] disabled:opacity-50">
                    <Github className="h-4 w-4" /> Connect GitHub
                  </button>
                  <p className="mt-1.5 text-center text-[11px] text-[#6B7280]">
                    Fastest way — GitHub tells us your username and addresses, so
                    there is nothing to type and nothing to verify.
                  </p>
                  <p className="mt-1.5 text-center text-[11px] text-[#9CA3AF]">
                    Or fill it in yourself below (GitLab, or a git set up with an
                    address that is not on your GitHub account).
                  </p>
                </div>
              )}

              <label className="block">
                <span className="mb-1 block text-[11.5px] font-medium text-[#374151]">
                  GitHub or GitLab username
                </span>
                <input value={username} onChange={(e) => setUsername(e.target.value)}
                  placeholder="your-handle" className={cn(FIELD, 'w-full')} />
              </label>

              <div>
                <span className="mb-1 block text-[11.5px] font-medium text-[#374151]">
                  The email you commit with
                </span>
                {/* Run `git config user.email` - it is often a personal
                    address, and it is what git actually stamps on a commit. */}
                <p className="mb-1.5 text-[11px] text-[#6B7280]">
                  Not sure? Run <code className="font-mono">git config user.email</code> in
                  your project folder. Add more than one if you commit from more
                  than one machine.
                </p>
                <div className="space-y-1.5">
                  {emails.map((value, i) => (
                    <div key={i} className="flex items-center gap-1.5">
                      <input value={value} className={cn(FIELD, 'flex-1')}
                        placeholder="you@example.com"
                        onChange={(e) => setEmails((list) =>
                          list.map((v, j) => (j === i ? e.target.value : v)))} />
                      {emails.length > 1 && (
                        <button type="button" aria-label="Remove this address"
                          onClick={() => setEmails((list) => list.filter((_, j) => j !== i))}
                          className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#6B7280] hover:bg-[#F4F5FA]">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                {emails.length < 5 && (
                  <button type="button" onClick={() => setEmails((list) => [...list, ''])}
                    className="mt-1.5 flex items-center gap-1 text-[11.5px] text-[#2563EB] hover:underline">
                    <Plus className="h-3.5 w-3.5" /> Add another address
                  </button>
                )}
              </div>

              {data.verify_code && (
                <div className="rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2.5 text-[11.5px] text-[#1E3A8A]">
                  <p className="font-semibold">Prove the account is yours</p>
                  <p className="mt-0.5">
                    Put this code in any commit message and push. It proves the
                    address is really yours, and it only has to happen once.
                  </p>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <code className="rounded bg-white px-2 py-1 font-mono text-[12px] font-bold">
                      {data.verify_code}
                    </code>
                    <button type="button" onClick={copyCode} aria-label="Copy the code"
                      className="rounded-lg border border-[#BFDBFE] bg-white p-1.5 text-[#1D4ED8] hover:bg-[#F4F7FF]">
                      {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" />
                        : <Copy className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>
              )}

              {repo && (
                <div className="rounded-lg border border-[#DDD6FE] bg-[#FAF9FF] px-3 py-2.5">
                  <p className="text-[11.5px] font-semibold text-[#1B1B3A]">
                    Team repository{' '}
                    <span className="font-normal text-[#7C3AED]">you are the batch leader</span>
                  </p>
                  <p className="mt-0.5 text-[11px] text-[#6B7280]">
                    You created the repo, so you are the one who can add the webhook.
                    Do this once and every teammate&apos;s pushes start arriving.
                  </p>

                  <div className="mt-2 space-y-2">
                    <label className="block">
                      <span className="mb-1 block text-[11px] text-[#374151]">Repository link</span>
                      <input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)}
                        placeholder="https://github.com/your-team/project"
                        className={cn(FIELD, 'w-full')} />
                    </label>
                    <CopyField label="Payload URL" value={repo.webhook_url} />
                    {!repo.reachable && (
                      <p className="flex items-start gap-1.5 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-2.5 py-1.5 text-[11px] text-[#92400E]">
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        <span>
                          This address only exists on the college network, so GitHub
                          cannot post to it yet. Ask your trainer.
                        </span>
                      </p>
                    )}
                    <CopyField label="Secret" value={repo.secret ?? ''}
                      empty="Issued when you save the repository above." />
                  </div>

                  <p className="mt-2 text-[11px] leading-relaxed text-[#4B5563]">
                    On GitHub: <strong>Settings → Webhooks → Add webhook</strong>. Paste
                    both values, set Content type to{' '}
                    <code className="font-mono">application/json</code>, choose
                    &quot;Just the push event&quot;, and Add webhook.
                  </p>

                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <button type="button" onClick={() => saveRepo(false)} disabled={busy}
                      className="flex h-8 items-center gap-1.5 rounded-lg bg-[#7C3AED] px-2.5 text-[11.5px] font-medium text-white hover:bg-[#6D28D9] disabled:opacity-50">
                      Save repository
                    </button>
                    <button type="button" onClick={() => saveRepo(true)} disabled={busy}
                      className="text-[11px] text-[#DC2626] hover:underline disabled:opacity-50">
                      Rotate the secret
                    </button>
                  </div>
                </div>
              )}

              <div className="rounded-lg bg-[#F9FAFC] px-3 py-2.5 text-[11.5px] leading-relaxed text-[#4B5563]">
                <p className="font-semibold text-[#1B1B3A]">Getting a commit onto a story</p>
                <p>
                  Name the story in the message and it attaches itself:{' '}
                  <code className="font-mono">git commit -m &quot;{data.key_example}&quot;</code>
                </p>
                {data.unclaimed_commits > 0 && (
                  <p className="mt-1.5">
                    {data.unclaimed_commits} commit
                    {data.unclaimed_commits === 1 ? ' in' : 's in'} this repository
                    {data.unclaimed_commits === 1 ? ' is' : ' are'} credited to nobody
                    yet — if any are yours, adding that address above claims them.
                  </p>
                )}
              </div>

            </>
          )}
        </div>

        <footer className="flex justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
          <button type="button" onClick={onClose}
            className="flex h-9 items-center rounded-lg border border-[#D1D5DB] bg-white px-3 text-[12.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
            Close
          </button>
          <button type="button" onClick={save} disabled={busy || !data}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-50">
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </button>
        </footer>
      </div>
    </div>
  )
}


// ==========================================================================
// My Commits
// ==========================================================================

interface CommitRow {
  sha: string
  short_sha: string
  message: string
  url: string | null
  branch: string | null
  committed_at: string | null
  /** Null when the message named no story - worth showing, not hiding. */
  story: { id: string; key: string; title: string } | null
}

interface CommitPage {
  rows: CommitRow[]
  total: number
  page: number
  per_page: number
  pages: number
  counts: { all: number; linked: number; unlinked: number }
}

const SCOPES = [
  { key: 'all', label: 'All' },
  { key: 'linked', label: 'On a story' },
  { key: 'unlinked', label: 'No story' },
] as const

/**
 * Everything this student has pushed, newest first.
 *
 * The story column is the point: it answers "did the work I did actually land
 * on the story it was for?", which the story pages can only answer one at a
 * time. Commits that landed nowhere get their own tab rather than being
 * filtered away - a missing US-xxx key is the usual reason a story looks
 * emptier than the work behind it.
 */
function MyCommits() {
  const [data, setData] = useState<CommitPage | null>(null)
  const [scope, setScope] = useState<'all' | 'linked' | 'unlinked'>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ scope, page: String(page), per_page: '20' })
      if (search.trim()) params.set('search', search.trim())
      setData(await apiClient.get<CommitPage>(`/student/commits?${params}`))
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not load your commits.')
    }
  }, [scope, search, page])

  useEffect(() => {
    const id = setTimeout(load, search ? 300 : 0)
    return () => clearTimeout(id)
  }, [load, search])

  if (error) {
    return (
      <p className={cn(CARD, 'px-4 py-6 text-center text-[12.5px] text-[#DC2626]')}>{error}</p>
    )
  }
  if (!data) {
    return (
      <p className={cn(CARD, 'flex items-center justify-center gap-2 px-4 py-10 text-[12.5px] text-[#6B7280]')}>
        <Loader2 className="h-4 w-4 animate-spin" /> Loading your commits…
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className={cn(CARD, 'flex flex-wrap items-center gap-3 p-3.5')}>
        <span className="relative block min-w-[220px] flex-1">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
          <input value={search} aria-label="Search commit messages"
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search commit messages…"
            className={cn(FIELD, 'w-full pl-8')} />
        </span>
        <div className="flex gap-1">
          {SCOPES.map((sc) => (
            <button key={sc.key} type="button"
              onClick={() => { setScope(sc.key); setPage(1) }}
              className={cn('flex h-9 items-center gap-1.5 rounded-lg border px-2.5 text-[12px]',
                scope === sc.key
                  ? 'border-[#2563EB] bg-[#EFF6FF] font-medium text-[#2563EB]'
                  : 'border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]')}>
              {sc.label}
              <span className="text-[11px] text-[#9CA3AF]">{data.counts[sc.key]}</span>
            </button>
          ))}
        </div>
      </div>

      <div className={cn(CARD, 'p-3.5')}>
        {data.rows.length === 0 ? (
          <div className="px-4 py-10 text-center">
            <GitCommitHorizontal className="mx-auto h-6 w-6 text-[#D1D5DB]" />
            <p className="mt-2 text-[12.5px] text-[#6B7280]">
              {data.counts.all === 0
                ? 'Nothing yet. Push a commit to the team repository and it shows up here.'
                : 'No commit matches that.'}
            </p>
            {data.counts.all === 0 && (
              <p className="mt-1 text-[11.5px] text-[#9CA3AF]">
                If you have pushed already, check that the email you commit with is
                listed under My Git Account.
              </p>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-[#F1F2F8]">
            {data.rows.map((c) => (
              <li key={c.sha} className="flex flex-wrap items-center gap-2 py-2.5">
                <code className="shrink-0 rounded bg-[#F4F5FA] px-1.5 py-0.5 font-mono text-[10.5px] text-[#4B5563]">
                  {c.short_sha}
                </code>
                <span className="min-w-0 flex-1 truncate text-[12.5px] text-[#1B1B3A]"
                  title={c.message}>
                  {c.message}
                </span>
                {c.story ? (
                  <Link href={`/stories/${c.story.id}`} target="_blank" rel="noopener"
                    title={c.story.title}
                    className="shrink-0 rounded bg-[#EFF6FF] px-1.5 py-0.5 text-[10.5px] font-medium text-[#1D4ED8] hover:underline">
                    {c.story.key}
                  </Link>
                ) : (
                  <span title="This commit named no story, so it is not on any board"
                    className="shrink-0 rounded bg-[#FFFBEB] px-1.5 py-0.5 text-[10.5px] text-[#92400E]">
                    No story
                  </span>
                )}
                {c.branch && (
                  <span className="hidden shrink-0 text-[10.5px] text-[#9CA3AF] sm:inline">
                    {c.branch}
                  </span>
                )}
                <span className="shrink-0 text-[10.5px] text-[#9CA3AF]">
                  {fmtWhen(c.committed_at)}
                </span>
                {c.url && (
                  <a href={c.url} target="_blank" rel="noopener noreferrer"
                    aria-label={`Open commit ${c.short_sha}`}
                    className="shrink-0 rounded-lg border border-[#E5E7EB] p-1 text-[#2563EB] hover:bg-[#F4F7FF]">
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}

        {data.counts.unlinked > 0 && scope !== 'unlinked' && (
          <p className="mt-3 flex items-start gap-1.5 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] text-[#92400E]">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              {data.counts.unlinked} of your commits named no story, so they are not
              showing on any board. Start the message with the story ID next time —
              your trainer sees the board, not the repository.
            </span>
          </p>
        )}

        {data.pages > 1 && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[#F1F2F8] pt-3">
            <p className="text-[11.5px] text-[#6B7280]">
              Page {data.page} of {data.pages} · {data.total} commits
            </p>
            <div className="flex items-center gap-1.5">
              <PageBtn label="Previous page" disabled={data.page <= 1}
                onClick={() => setPage(data.page - 1)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </PageBtn>
              <PageBtn label="Next page" disabled={data.page >= data.pages}
                onClick={() => setPage(data.page + 1)}>
                <ChevronRight className="h-3.5 w-3.5" />
              </PageBtn>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const fmtWhen = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  }) : '—'


interface TeamRepo {
  webhook_url: string
  reachable: boolean
  repo_url: string | null
  secret: string | null
  commits: number
}

/** A value that has to be pasted somewhere else, with a copy button. */
function CopyField({ label, value, empty }: {
  label: string
  value: string
  /** Shown in place of the box before there is anything to copy. */
  empty?: string
}) {
  const [done, setDone] = useState(false)
  if (!value) {
    return (
      <label className="block">
        <span className="mb-1 block text-[11px] text-[#374151]">{label}</span>
        <span className="block rounded-lg border border-dashed border-[#D1D5DB] px-2.5 py-2 text-[11px] text-[#9CA3AF]">
          {empty ?? 'Not set yet.'}
        </span>
      </label>
    )
  }
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] text-[#374151]">{label}</span>
      <span className="flex items-stretch gap-1.5">
        <input readOnly value={value} onFocus={(e) => e.currentTarget.select()}
          className={cn(FIELD, 'flex-1 bg-white font-mono text-[11px]')} />
        <button type="button" aria-label={`Copy ${label}`}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value)
              setDone(true)
              setTimeout(() => setDone(false), 1600)
            } catch { /* insecure origin - the value is selectable anyway */ }
          }}
          className="flex w-[34px] shrink-0 items-center justify-center rounded-lg border border-[#D1D5DB] bg-white text-[#6B7280] hover:bg-[#F4F5FA]">
          {done ? <CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" />
            : <Copy className="h-3.5 w-3.5" />}
        </button>
      </span>
    </label>
  )
}
