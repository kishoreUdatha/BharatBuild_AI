'use client'

/**
 * One user story, on its own page.
 *
 * Deliberately outside /trainer: a trainer, a guide, an admin and the students
 * on the batch all open the same URL. Being outside that route means its
 * layout - the sidebar and top bar - does not come for free, so this page
 * draws them itself for staff and leaves them off for a student, who has no
 * trainer portal to be inside. What differs beyond the frame is what the
 * viewer may do: the API says whether this account can edit, and a student
 * gets a read of the story plus the comment box.
 *
 * Nothing here is invented. Attachments, work logs and repository activity are
 * not modelled, so the page does not draw empty frames for them.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import {
  AlertTriangle, CalendarClock, CheckCircle2, ChevronDown, ChevronUp, Circle,
  Download, ExternalLink, GitCommitHorizontal, Loader2, Lock, Minus, Paperclip,
  Pencil, Plus, Send, Sparkles, Trash2,
} from 'lucide-react'
import { BranchHint } from '@/components/story/BranchHint'
import {
  addCriterion, addSubTask, attachToStory, commentOnSharedStory, downloadAttachment,
  errorText, fetchStory, patchCriterion, patchSharedStory, patchSubTask,
  removeAttachment, removeCriterion,
} from '@/lib/trainer-api'
import type { SharedStory, StoryPatch } from '@/lib/trainer-api'
import { StudentSidebar, StudentTopBar } from '@/components/student/StudentShell'
import { TrainerSidebar, TrainerTopBar } from '@/components/trainer/TrainerShell'
import { Avatar, toneOf } from '@/components/trainer/user-stories/bits'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'
const FIELD = 'h-8 w-full rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px] ' +
  'text-[#374151] outline-none focus:border-[#2563EB] disabled:bg-[#F9FAFB] disabled:opacity-70'

/** The sub-task states, in the mockup's chip treatment. */
const TASK_TONE: Record<string, string> = {
  open: 'border-[#E5E7EB] bg-[#F4F5FA] text-[#6B7280]',
  in_progress: 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]',
  blocked: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  done: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
}

const STATUS_TONE: Record<string, string> = {
  to_do: 'border-[#DBEAFE] bg-[#EFF6FF] text-[#1D4ED8]',
  in_progress: 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]',
  testing: 'border-[#A5F3FC] bg-[#ECFEFF] text-[#0E7490]',
  in_review: 'border-[#DDD6FE] bg-[#F5F3FF] text-[#6D28D9]',
  done: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  blocked: 'border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]',
}

const TABS = ['All', 'Comments', 'History'] as const
type Tab = (typeof TABS)[number]

/**
 * The description and its criteria, written as one block.
 *
 * Same convention as the Add User Story dialog, so a trainer learns it once.
 * The criteria are still separate rows underneath - the ticks are what the
 * board and the approval checklist count - but nobody has to think about that
 * while writing the story.
 */
const AC_HEADING = /^\s*acceptance\s*criteria\s*:?\s*$/i
const BULLET = /^\s*(?:[-*\u2022\u2013]|\d+[.)])\s*/

function splitBody(text: string): { narrative: string; criteria: string[] } {
  const lines = (text ?? '').split('\n')
  const at = lines.findIndex((l) => AC_HEADING.test(l))
  if (at === -1) return { narrative: (text ?? '').trim(), criteria: [] }
  return {
    narrative: lines.slice(0, at).join('\n').trim(),
    criteria: lines.slice(at + 1)
      .map((l) => l.replace(BULLET, '').trim())
      .filter(Boolean),
  }
}

function composeBody(narrative: string | null, criteria: { text: string }[]): string {
  const head = (narrative ?? '').trim()
  if (criteria.length === 0) return head
  return `${head}\n\nAcceptance criteria:\n${criteria.map((c) => `- ${c.text}`).join('\n')}`
}

const fmt = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }) : '—'

/**
 * The portal frame, for the people who have one.
 *
 * Staff keep their sidebar and top bar so a story opened in a new tab is still
 * inside the portal they were working in. A student gets the bare page - the
 * trainer's navigation would be a wall of links they cannot open.
 *
 * Declared at module scope on purpose. Defined inside the page component it
 * was a new component type on every render, so React remounted the whole tree
 * for each keystroke in the comment box - resetting the scroll position and
 * rebuilding the sidebar.
 */
/**
 * "Saved", briefly.
 *
 * Auto-save is only trustworthy if it says so. This appears on each successful
 * write and clears itself after a few seconds, so the page is not permanently
 * decorated with a stale reassurance.
 */
function SavedTick({ at }: { at: number }) {
  const [show, setShow] = useState(true)
  useEffect(() => {
    setShow(true)
    const t = setTimeout(() => setShow(false), 2500)
    return () => clearTimeout(t)
  }, [at])
  if (!show) return null
  return (
    <span className="flex items-center gap-1 text-[11px] font-normal text-[#16A34A]">
      <CheckCircle2 className="h-3.5 w-3.5" /> Saved
    </span>
  )
}

function StoryShell({ bare, me, children }: {
  bare: boolean
  me: { full_name?: string; college_name?: string; roll_number?: string } | null
  children: React.ReactNode
}) {
  // Each side keeps its own navigation. A student opening a story used to get
  // a bare page - the trainer's menu would have been a wall of links they
  // cannot open - but the answer to the wrong menu is their menu, not none.
  const college = me?.college_name ?? 'Sri Guru Institute of Technology'
  return (
    <div className="flex min-h-screen bg-[#F5F7FB] text-[#1B1B3A]">
      {/* The sidebar holds the full height and stays put while the story
          scrolls. Without the wrapper it is only as tall as its own links,
          and a long story scrolls the navigation off the screen with it. */}
      <div className="sticky top-0 hidden h-screen shrink-0 bg-[#0B1B4D] lg:block">
        {bare
          ? <StudentSidebar />
          : <TrainerSidebar activeHref="/trainer/user-stories" />}
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="sticky top-0 z-30">
          {bare ? (
            <StudentTopBar college={college} name={me?.full_name ?? null}
              roll={me?.roll_number ?? null} />
          ) : (
            <TrainerTopBar college={college} name={me?.full_name ?? null} />
          )}
        </div>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  )
}

export default function StoryPage() {
  const params = useParams<{ id: string }>()
  const id = decodeURIComponent(params?.id ?? '')

  const [data, setData] = useState<SharedStory | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const [tab, setTab] = useState<Tab>('All')
  const [showDod, setShowDod] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const commentRef = useRef<HTMLTextAreaElement>(null)

  // `editing` holds the draft while the body is open for editing; null means
  // it is being read. Keeping the draft out of `data` means a failed save does
  // not leave the page showing something the server never accepted.
  const [editing, setEditing] = useState<{ title: string; narrative: string } | null>(null)
  const [newTask, setNewTask] = useState<{ title: string; assignee_id: string; due_date: string } | null>(null)
  // The criterion being reworded, and the one being typed. Separate because a
  // trainer often adds two in a row without touching the existing ones.
  const [editCriterion, setEditCriterion] = useState<{ id: string; text: string } | null>(null)
  const [newCriterion, setNewCriterion] = useState<string | null>(null)
  // When the last write landed, so the page can say so and then stop saying it.
  const [savedAt, setSavedAt] = useState<number | null>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [me, setMe] = useState<
    { full_name?: string; college_name?: string; roll_number?: string } | null>(null)

  const load = useCallback(async () => {
    setError('')
    try {
      setData(await fetchStory(id))
    } catch (err: any) {
      const httpStatus = err?.response?.status
      if (httpStatus === 404) {
        setError('That story does not exist, or has not been shared with you yet.')
        return
      }
      if (httpStatus === 403) {
        setError('This story belongs to a batch you are not on.')
        return
      }
      setError(errorText(err, 'Could not load that story.'))
    }
  }, [id])

  useEffect(() => { load() }, [load])

  // Who is looking, for the top bar. Failing is not fatal: the story is the
  // point of the page, and the bar can say "Your Institution" instead.
  useEffect(() => {
    apiClient.getMe().then(setMe).catch(() => setMe(null))
  }, [])

  // M jumps to the comment box, as the mockup's pro tip promises. Ignored
  // while something else has focus, so it cannot eat a letter mid-sentence.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (e.key.toLowerCase() !== 'm' || e.metaKey || e.ctrlKey || e.altKey) return
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      e.preventDefault()
      commentRef.current?.focus()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  /**
   * Make the stored criteria match what was typed, without losing the ticks.
   *
   * Text that is unchanged is left alone, so a tick somebody earned survives
   * an edit to the paragraph above it. What is left over is paired up in
   * order and reworded rather than deleted and recreated, which is what makes
   * fixing a typo keep its tick too.
   */
  const syncCriteria = async (wanted: string[]) => {
    const story = data?.story
    if (!story) return
    const existing = story.acceptance_criteria
    // Nothing typed and nothing stored, or the editor never had a heading and
    // the story has none either: leave it entirely alone.
    if (wanted.length === 0 && existing.length === 0) return

    const keptIds = new Set<string>()
    const unmatched: string[] = []
    for (const text of wanted) {
      const hit = existing.find((c) => c.text === text && !keptIds.has(c.id))
      if (hit) keptIds.add(hit.id)
      else unmatched.push(text)
    }
    const spare = existing.filter((c) => !keptIds.has(c.id))

    // Reword the ones we can, so their met state carries over.
    const reword = Math.min(spare.length, unmatched.length)
    for (let i = 0; i < reword; i += 1) {
      await patchCriterion(id, spare[i].id, { text: unmatched[i] })
    }
    for (const text of unmatched.slice(reword)) await addCriterion(id, text)
    for (const row of spare.slice(reword)) await removeCriterion(id, row.id)
  }

  /** Debounced auto-save for the free-text fields. */
  const queueBodySave = (next: { title: string; narrative: string }) => {
    setEditing(next)
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => { void saveBodyNow(next) }, 900)
  }

  const saveBodyNow = async (draft?: { title: string; narrative: string }) => {
    const current = draft ?? editing
    if (!current) return
    const title = current.title.trim()
    // Too short to be a title, so hold the last good one rather than reject a
    // half-typed word the moment the debounce fires.
    if (title.length < 3) return
    if (saveTimer.current) { clearTimeout(saveTimer.current); saveTimer.current = null }
    setBusy(true)
    try {
      const { narrative, criteria } = splitBody(current.narrative)
      await patchSharedStory(id, { title, narrative })
      await syncCriteria(criteria)
      setSavedAt(Date.now())
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That change could not be saved.'))
    } finally { setBusy(false) }
  }

  const patch = async (body: StoryPatch) => {
    setBusy(true)
    try {
      await patchSharedStory(id, body)
      setSavedAt(Date.now())
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That change could not be saved.'))
    } finally { setBusy(false) }
  }

  const send = async () => {
    const body = note.trim()
    if (!body) return
    setBusy(true)
    try {
      await commentOnSharedStory(id, body)
      setNote('')
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That comment could not be added.'))
    } finally { setBusy(false) }
  }

  const upload = async (file: File) => {
    setBusy(true)
    setError('')
    try {
      await attachToStory(id, file)
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That file could not be attached.'))
    } finally { setBusy(false) }
  }

  const detach = async (attachmentId: string) => {
    setBusy(true)
    try {
      await removeAttachment(id, attachmentId)
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That file could not be removed.'))
    } finally { setBusy(false) }
  }

  const saveBody = async () => {
    if (!editing) return
    const title = editing.title.trim()
    if (title.length < 3) {
      setError('A story needs a title of at least three characters.')
      return
    }
    setBusy(true)
    try {
      await patchSharedStory(id, { title, narrative: editing.narrative.trim() })
      setSavedAt(Date.now())
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That change could not be saved.'))
    } finally { setBusy(false) }
  }

  const createTask = async () => {
    if (!newTask || newTask.title.trim().length < 3) return
    setBusy(true)
    try {
      await addSubTask(id, {
        title: newTask.title.trim(),
        assignee_id: newTask.assignee_id || undefined,
        due_date: newTask.due_date || undefined,
      })
      setNewTask(null)
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That sub-task could not be added.'))
    } finally { setBusy(false) }
  }

  /** Every criterion write goes through here, so one place reloads the story. */
  const onCriteria = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await fn()
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That criterion could not be saved.'))
    } finally { setBusy(false) }
  }

  const toggleTask = async (taskId: string, done: boolean) => {
    setBusy(true)
    try {
      await patchSubTask(id, taskId, { status: done ? 'open' : 'done' })
      await load()
    } catch (err: any) {
      setError(errorText(err, 'That sub-task could not be updated.'))
    } finally { setBusy(false) }
  }


  if (error && !data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#F5F7FB] p-6">
        <div className={cn(CARD, 'flex max-w-[420px] flex-col items-center gap-3 px-6 py-10 text-center')}>
          <Lock className="h-6 w-6 text-[#DC2626]" />
          <p className="text-[13px] text-[#4B5563]">{error}</p>
          <button type="button" onClick={load}
            className="rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
            Try again
          </button>
        </div>
      </main>
    )
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#F5F7FB]">
        <span className="flex items-center gap-2 text-[12.5px] text-[#6B7280]">
          <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" /> Loading story…
        </span>
      </main>
    )
  }

  const { story, batch, permissions, options } = data
  // Written by the repository, so it sits beside the story rather than on it.
  const commits = data.commits ?? []
  const canEdit = permissions.can_edit
  // The assignee gets a narrow slice of write access: their own progress, not
  // the planning around it. Everything else on this page stays staff-only.
  const canSetStatus = canEdit || !!permissions.can_change_status
  const canProgress = canEdit || !!permissions.can_update_progress
  const viewerId = permissions.user_id
  const met = story.acceptance_criteria.filter((c) => c.met).length

  // Which navigation to show is a question about who the viewer is, not what
  // they may edit: students edit like staff now, and keying the shell off
  // that would hand them the trainer's menu.
  return (
    <StoryShell bare={data?.permissions.role === 'student'} me={me}>
      <div className="mx-auto grid max-w-[1180px] gap-4 px-5 py-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        {/* ------------------------------------------------------------ main */}
        <div className="space-y-4">
          <div>
            <p className="flex items-center gap-2 text-[12px] font-medium text-[#2563EB]">
              {story.key}
              {busy
                ? <span className="flex items-center gap-1 text-[11px] font-normal text-[#9CA3AF]">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…
                  </span>
                : savedAt && <SavedTick at={savedAt} />}
            </p>
            {editing ? (
              <input value={editing.title} autoFocus aria-label="Story title"
                onChange={(e) => queueBodySave({ ...editing, title: e.target.value })}
                onBlur={() => saveBodyNow()}
                className="mt-0.5 w-full rounded-lg border border-[#D1D5DB] px-2.5 py-1.5 text-[20px] font-bold leading-snug outline-none focus:border-[#2563EB]" />
            ) : (
              <span className="mt-0.5 flex flex-wrap items-start gap-2">
                <h1 className="text-[22px] font-bold leading-snug">{story.title}</h1>
                {canEdit && (
                  <button type="button" aria-label="Edit story"
                    onClick={() => setEditing({
                      title: story.title,
                      narrative: composeBody(story.narrative, story.acceptance_criteria),
                    })}
                    className="mt-1 inline-flex items-center gap-1 rounded-lg border border-[#D1D5DB] bg-white px-2 py-1 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                    <Pencil className="h-3 w-3" /> Edit
                  </button>
                )}
              </span>
            )}
            {permissions.role === 'student' && (
              <p className="mt-1 text-[11.5px] text-[#9CA3AF]">
                You are on {batch.batch_code}
                {permissions.is_assignee ? ', and this story is assigned to you' : ''}.
                Changes you make here are visible to your trainer and the rest of the team.
              </p>
            )}
          </div>

          {error && (
            <p className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[12px] text-[#DC2626]">
              {error}
            </p>
          )}

          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[13px] font-semibold">Description</h2>
            {editing ? (
              <div className="mt-1.5 space-y-2">
                <textarea rows={4} value={editing.narrative} aria-label="Description"
                  placeholder="As a …, I want … so that …"
                  onChange={(e) => queueBodySave({ ...editing, narrative: e.target.value })}
                  onBlur={() => saveBodyNow()}
                  className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[12.5px] leading-relaxed outline-none focus:border-[#2563EB]" />
                <div className="flex justify-end gap-2">
                  {/* Typing already saves; this only leaves the editor. */}
                  <button type="button" disabled={busy}
                    onClick={async () => { await saveBodyNow(); setEditing(null) }}
                    className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-[12px] font-medium text-white disabled:opacity-50">
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <p className="mt-1.5 whitespace-pre-line text-[12.5px] leading-relaxed text-[#4B5563]">
                {story.narrative ?? 'No description was written for this story.'}
              </p>
            )}

            {/* Part of the description, not a card of its own: one thought,
                written in one place. Hidden while editing, because then the
                textarea above already holds them as text. */}
            {!editing && (
              <>
                <h3 className="mt-4 border-t border-[#F1F2F8] pt-3 text-[12.5px] font-semibold">
                  Acceptance Criteria{' '}
                  <span className="font-normal text-[#9CA3AF]">
                    {met} / {story.acceptance_criteria.length}
                  </span>
                </h3>
            {story.acceptance_criteria.length === 0 && !newCriterion ? (
              <p className="mt-1.5 text-[12px] italic text-[#9CA3AF]">None recorded.</p>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {story.acceptance_criteria.map((c) => (
                  <li key={c.id} className="group flex items-start gap-2 text-[12.5px] leading-snug text-[#4B5563]">
                    {/* The tick is the claim the approval checklist counts, so
                        it is a control here rather than a picture of one. The
                        assignee ticks their own; rewording stays with staff. */}
                    {canProgress ? (
                      <button type="button" disabled={busy}
                        aria-label={c.met ? `Mark unmet: ${c.text}` : `Mark met: ${c.text}`}
                        onClick={() => onCriteria(
                          () => patchCriterion(id, c.id, { met: !c.met }))}
                        className="mt-0.5 shrink-0 disabled:opacity-50">
                        {c.met
                          ? <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                          : <Circle className="h-4 w-4 text-[#EA580C] hover:text-[#16A34A]" />}
                      </button>
                    ) : c.met
                      ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#16A34A]" />
                      : <Circle className="mt-0.5 h-4 w-4 shrink-0 text-[#EA580C]" />}

                    {editCriterion?.id === c.id ? (
                      <span className="flex flex-1 flex-wrap items-center gap-2">
                        <input value={editCriterion.text} autoFocus aria-label="Criterion"
                          onChange={(e) => setEditCriterion({
                            ...editCriterion, text: e.target.value,
                          })}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && editCriterion.text.trim()) {
                              onCriteria(() => patchCriterion(id, c.id, {
                                text: editCriterion.text.trim(),
                              })).then(() => setEditCriterion(null))
                            }
                            if (e.key === 'Escape') setEditCriterion(null)
                          }}
                          className="min-w-[200px] flex-1 rounded-lg border border-[#D1D5DB] px-2 py-1 text-[12.5px] outline-none focus:border-[#2563EB]" />
                        <button type="button" onClick={() => setEditCriterion(null)}
                          className="text-[11.5px] font-medium text-[#6B7280] hover:text-[#374151]">
                          Cancel
                        </button>
                        <button type="button" disabled={busy || !editCriterion.text.trim()}
                          onClick={() => onCriteria(() => patchCriterion(id, c.id, {
                            text: editCriterion.text.trim(),
                          })).then(() => setEditCriterion(null))}
                          className="rounded-lg bg-[#2563EB] px-2.5 py-1 text-[11.5px] font-medium text-white disabled:opacity-50">
                          Save
                        </button>
                      </span>
                    ) : (
                      <>
                        <span className="flex-1">{c.text}</span>
                        {canEdit && (
                          <span className="flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                            <button type="button" aria-label={`Edit criterion: ${c.text}`}
                              onClick={() => setEditCriterion({ id: c.id, text: c.text })}
                              className="rounded p-0.5 text-[#9CA3AF] hover:bg-[#F4F5FA] hover:text-[#2563EB]">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                            <button type="button" aria-label={`Remove criterion: ${c.text}`}
                              disabled={busy}
                              onClick={() => onCriteria(() => removeCriterion(id, c.id))}
                              className="rounded p-0.5 text-[#9CA3AF] hover:bg-[#FEF2F2] hover:text-[#DC2626] disabled:opacity-50">
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </span>
                        )}
                      </>
                    )}
                  </li>
                ))}

                {newCriterion !== null && (
                  <li className="flex flex-wrap items-center gap-2">
                    <Circle className="h-4 w-4 shrink-0 text-[#D1D5DB]" />
                    <input value={newCriterion} autoFocus aria-label="New criterion"
                      placeholder="What has to be true for this to be done?"
                      onChange={(e) => setNewCriterion(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && newCriterion.trim()) {
                          onCriteria(() => addCriterion(id, newCriterion.trim()))
                            .then(() => setNewCriterion(''))
                        }
                        if (e.key === 'Escape') setNewCriterion(null)
                      }}
                      className="min-w-[220px] flex-1 rounded-lg border border-[#D1D5DB] px-2 py-1 text-[12.5px] outline-none focus:border-[#2563EB]" />
                    <button type="button" onClick={() => setNewCriterion(null)}
                      className="text-[11.5px] font-medium text-[#6B7280] hover:text-[#374151]">
                      Done adding
                    </button>
                    <button type="button" disabled={busy || !newCriterion.trim()}
                      onClick={() => onCriteria(() => addCriterion(id, newCriterion.trim()))
                        .then(() => setNewCriterion(''))}
                      className="rounded-lg bg-[#2563EB] px-2.5 py-1 text-[11.5px] font-medium text-white disabled:opacity-50">
                      Add
                    </button>
                  </li>
                )}
              </ul>
            )}

            {canEdit && newCriterion === null && (
              <button type="button" onClick={() => setNewCriterion('')}
                className="mt-2 inline-flex items-center gap-1.5 text-[12px] font-medium text-[#2563EB] hover:underline">
                <Plus className="h-3.5 w-3.5" /> Add a criterion
              </button>
            )}

            {story.definition_of_done.length > 0 && (
              <>
                <button type="button" onClick={() => setShowDod((v) => !v)}
                  className="mt-3 flex items-center gap-1 text-[12px] font-medium text-[#2563EB]">
                  Definition of Done ({story.definition_of_done.length})
                  {showDod ? <ChevronUp className="h-3.5 w-3.5" />
                    : <ChevronDown className="h-3.5 w-3.5" />}
                </button>
                {showDod && (
                  <ul className="mt-2 space-y-1.5">
                    {story.definition_of_done.map((d) => (
                      <li key={d.id} className="flex gap-2 text-[12px] leading-snug text-[#4B5563]">
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                        {d.text}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
              </>
            )}
          </section>

          <section className={cn(CARD, 'p-4')}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="flex items-center gap-1.5 text-[13px] font-semibold">
                <Paperclip className="h-4 w-4 text-[#9CA3AF]" />
                Attachments{' '}
                <span className="font-normal text-[#9CA3AF]">
                  {story.attachments.length}
                </span>
              </h2>
              {/* Anyone who can see the story can add one: the screenshot of
                  the bug comes from the team, not from the trainer. */}
              <button type="button" disabled={busy} onClick={() => fileRef.current?.click()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-50">
                <Paperclip className="h-3.5 w-3.5" /> Attach a file
              </button>
              <input ref={fileRef} type="file" className="hidden"
                onChange={(e) => {
                  const chosen = e.target.files?.[0]
                  if (chosen) upload(chosen)
                  e.target.value = ''
                }} />
            </div>

            {story.attachments.length === 0 ? (
              <p className="mt-1.5 text-[12px] italic text-[#9CA3AF]">
                Nothing attached yet.
              </p>
            ) : (
              <ul className="mt-2 divide-y divide-[#F1F2F8]">
                {story.attachments.map((a) => (
                  <li key={a.id} className="flex flex-wrap items-center gap-2 py-2">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#F4F5FA] text-[10px] font-semibold uppercase text-[#6B7280]">
                      {(a.name.split('.').pop() ?? 'file').slice(0, 4)}
                    </span>
                    <span className="min-w-[160px] flex-1">
                      <span className="block truncate text-[12.5px] text-[#1B1B3A]">
                        {a.name}
                      </span>
                      <span className="block text-[10.5px] text-[#9CA3AF]">
                        {a.size_label}
                        {a.uploaded_by && ` · ${a.uploaded_by}`} · {fmt(a.uploaded_at)}
                      </span>
                    </span>
                    <button type="button" aria-label={`Download ${a.name}`}
                      onClick={() => downloadAttachment(id, a.id, a.name)
                        .catch(() => setError('That file could not be downloaded.'))}
                      className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#2563EB] hover:bg-[#F4F7FF]">
                      <Download className="h-3.5 w-3.5" />
                    </button>
                    {/* Staff, or whoever put it there - a student may take back
                        their own screenshot, not the trainer's design doc. */}
                    {(canEdit || a.uploaded_by_id === viewerId) && (
                      <button type="button" aria-label={`Remove ${a.name}`} disabled={busy}
                        onClick={() => detach(a.id)}
                        className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-50">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Written by the repository, never by a person - so there is nothing
              to add or remove here. A commit arrives because someone named this
              story in their message. */}
          {commits.length > 0 && (
            <section className={cn(CARD, 'p-4')}>
              <h2 className="flex items-center gap-1.5 text-[13px] font-semibold">
                <GitCommitHorizontal className="h-4 w-4 text-[#9CA3AF]" />
                Commits{' '}
                <span className="font-normal text-[#9CA3AF]">{commits.length}</span>
              </h2>
              <ul className="mt-2 divide-y divide-[#F1F2F8]">
                {commits.map((c) => (
                  <li key={c.sha} className="flex flex-wrap items-center gap-2 py-2">
                    <code className="shrink-0 rounded bg-[#F4F5FA] px-1.5 py-0.5 font-mono text-[10.5px] text-[#4B5563]">
                      {c.short_sha}
                    </code>
                    <span className="min-w-0 flex-1 truncate text-[12px] text-[#1B1B3A]"
                      title={c.message}>
                      {c.message}
                    </span>
                    <span className="text-[11px] text-[#6B7280]">{c.author}</span>
                    {c.branch && (
                      <span className="rounded bg-[#EFF6FF] px-1.5 py-0.5 text-[10px] text-[#1D4ED8]">
                        {c.branch}
                      </span>
                    )}
                    <span className="text-[10.5px] text-[#9CA3AF]">{fmt(c.committed_at)}</span>
                    {c.url && (
                      <a href={c.url} target="_blank" rel="noopener noreferrer"
                        aria-label={`Open commit ${c.short_sha}`}
                        className="rounded-lg border border-[#E5E7EB] p-1 text-[#2563EB] hover:bg-[#F4F7FF]">
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}


          {/* Sub-tasks are the batch's tasks that break this story down. */}
          <section className={cn(CARD, 'p-4')}>
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-[13px] font-semibold">
                Sub-tasks{' '}
                <span className="font-normal text-[#9CA3AF]">
                  {story.counts.tasks_done} / {story.counts.tasks}
                </span>
              </h2>
              <span className="flex items-center gap-2">
                {story.counts.tasks > 0 && (
                  <>
                    <span className="h-1.5 w-[120px] overflow-hidden rounded-full bg-[#EEF0F7]">
                      <span className="block h-full rounded-full bg-[#16A34A]"
                        style={{
                          width: `${Math.round(
                            (story.counts.tasks_done / story.counts.tasks) * 100)}%`,
                        }} />
                    </span>
                    <span className="text-[11px] font-medium text-[#16A34A]">
                      {Math.round((story.counts.tasks_done / story.counts.tasks) * 100)}%
                    </span>
                  </>
                )}
                {canEdit && !newTask && (
                  <button type="button" onClick={() => setNewTask({
                    title: '', assignee_id: '', due_date: '',
                  })}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                    <Plus className="h-3.5 w-3.5" /> Add sub-task
                  </button>
                )}
              </span>
            </div>

            {story.tasks.length === 0 && !newTask ? (
              <p className="mt-1.5 text-[12px] italic text-[#9CA3AF]">
                Nothing breaks this story down yet.
              </p>
            ) : (
              <ul className="mt-2 divide-y divide-[#F1F2F8]">
                {story.tasks.map((t, index) => (
                  <li key={t.id} className="flex flex-wrap items-center gap-2 py-2">
                    {/* Staff and the assignee tick a sub-task off here; for
                        anyone else the mark is a read of where the work is. */}
                    {canProgress ? (
                      <button type="button" disabled={busy}
                        aria-label={t.done ? `Reopen ${t.title}` : `Complete ${t.title}`}
                        onClick={() => toggleTask(t.id, t.done)}
                        className="shrink-0 disabled:opacity-50">
                        {t.done
                          ? <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
                          : <Circle className="h-4 w-4 text-[#9CA3AF] hover:text-[#16A34A]" />}
                      </button>
                    ) : t.done
                      ? <CheckCircle2 className="h-4 w-4 shrink-0 text-[#16A34A]" />
                      : <Circle className="h-4 w-4 shrink-0 text-[#9CA3AF]" />}
                    {/* Numbered off the story, the way the mockup keys them:
                        US-108-1, -2, -3. Nothing stores that - it is the row's
                        place in the list, so it stays right when one is removed. */}
                    <span className="shrink-0 text-[11.5px] font-medium text-[#2563EB]">
                      {story.key}-{index + 1}
                    </span>
                    <span className={cn('min-w-[160px] flex-1 text-[12.5px]',
                      t.done ? 'text-[#9CA3AF] line-through' : 'text-[#1B1B3A]')}>
                      {t.title}
                    </span>
                    <span className={cn('shrink-0 rounded-md border px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wide',
                      TASK_TONE[t.status] ?? TASK_TONE.open)}>
                      {t.status_label}
                    </span>
                    {t.assignee && (
                      <span className={cn('shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold',
                        toneOf(t.assignee.id))}>
                        {t.assignee.roll ?? t.assignee.initials}
                      </span>
                    )}
                    {t.due_date && (
                      <span className="flex items-center gap-1 text-[10.5px] text-[#9CA3AF]">
                        <CalendarClock className="h-3 w-3" />
                        {new Date(t.due_date).toLocaleDateString('en-IN',
                          { day: '2-digit', month: 'short' })}
                      </span>
                    )}
                  </li>
                ))}

                {newTask && (
                  <li className="space-y-2 py-2">
                    <input value={newTask.title} autoFocus aria-label="Sub-task title"
                      placeholder="What needs doing?"
                      onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                      onKeyDown={(e) => { if (e.key === 'Enter') createTask() }}
                      className="w-full rounded-lg border border-[#D1D5DB] px-2 py-1.5 text-[12.5px] outline-none focus:border-[#2563EB]" />
                    <div className="flex flex-wrap items-center gap-2">
                      <select value={newTask.assignee_id} aria-label="Sub-task assignee"
                        onChange={(e) => setNewTask({ ...newTask, assignee_id: e.target.value })}
                        className={cn(FIELD, 'w-auto')}>
                        <option value="">Unassigned</option>
                        {options.assignees.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.roll ? `${a.roll} · ${a.name}` : a.name}
                          </option>
                        ))}
                      </select>
                      <input type="date" value={newTask.due_date} aria-label="Sub-task due date"
                        onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                        className={cn(FIELD, 'w-auto')} />
                      <span className="flex-1" />
                      <button type="button" onClick={() => setNewTask(null)}
                        className="rounded-lg border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                        Cancel
                      </button>
                      <button type="button" onClick={createTask}
                        disabled={busy || newTask.title.trim().length < 3}
                        className="rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-[12px] font-medium text-white disabled:opacity-50">
                        Add
                      </button>
                    </div>
                  </li>
                )}
              </ul>
            )}
          </section>

          {/* ------------------------------------------------------- activity */}
          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[13px] font-semibold">Activity</h2>
            <nav className="mt-2 flex gap-1 border-b border-[#F1F2F8]">
              {TABS.map((t) => (
                <button key={t} type="button" onClick={() => setTab(t)}
                  className={cn('px-2.5 py-1.5 text-[12px] font-medium transition-colors',
                    tab === t
                      ? 'border-b-2 border-[#2563EB] text-[#2563EB]'
                      : 'text-[#6B7280] hover:text-[#374151]')}>
                  {t}
                  {t === 'Comments' && story.counts.comments > 0 && ` (${story.counts.comments})`}
                  {t === 'History' && story.counts.activity > 0 && ` (${story.counts.activity})`}
                </button>
              ))}
            </nav>

            <div className="mt-3 space-y-2">
              <textarea ref={commentRef} rows={2} value={note} maxLength={2000}
                onChange={(e) => setNote(e.target.value)}
                aria-label="Add a comment" placeholder="Add a comment…"
                className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[12.5px] outline-none focus:border-[#2563EB]" />
              <span className="flex items-center gap-3">
                <button type="button" onClick={send} disabled={busy || !note.trim()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3.5 py-1.5 text-[12px] font-medium text-white disabled:opacity-50">
                  <Send className="h-3.5 w-3.5" /> Comment
                </button>
                <span className="text-[11px] text-[#9CA3AF]">
                  Pro tip: press{' '}
                  <kbd className="rounded border border-[#D1D5DB] bg-[#F9FAFB] px-1 font-sans text-[10px] text-[#6B7280]">
                    M
                  </kbd>{' '}
                  to comment
                </span>
              </span>
            </div>

            <ul className="mt-3 space-y-2.5">
              {tab !== 'History' && story.comments.map((c) => (
                <li key={c.id} className="rounded-lg border border-[#F1F2F8] p-2.5">
                  <p className="text-[12.5px] leading-snug text-[#4B5563]">{c.body}</p>
                  <p className="mt-1 text-[10.5px] text-[#9CA3AF]">
                    {c.author} · {fmt(c.created_at)}
                  </p>
                </li>
              ))}
              {tab !== 'Comments' && story.activity.map((a) => (
                <li key={a.id} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#BFDBFE]" />
                  <span className="min-w-0">
                    <span className="block text-[12px] text-[#1B1B3A]">
                      {a.summary}
                      {a.from_value && a.to_value && (
                        <span className="text-[#6B7280]"> · {a.from_value} → {a.to_value}</span>
                      )}
                    </span>
                    <span className="block text-[10.5px] text-[#9CA3AF]">
                      {a.actor} · {fmt(a.occurred_at)}
                    </span>
                  </span>
                </li>
              ))}
              {((tab === 'Comments' && story.comments.length === 0)
                || (tab === 'History' && story.activity.length === 0)
                || (tab === 'All' && story.comments.length === 0
                  && story.activity.length === 0)) && (
                <li className="py-4 text-center text-[12px] text-[#9CA3AF]">
                  Nothing here yet.
                </li>
              )}
            </ul>
          </section>
        </div>

        {/* ---------------------------------------------------------- details */}
        <aside className="space-y-3">
          {/* Before the commits arrive, not after. Somebody opening a story to
              start work needs the branch name here; the Commits section below
              only exists once they have already got it right. */}
          <BranchHint storyId={story.id} storyKey={story.key} title={story.title} />

          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2.5 text-[13px] font-semibold">Details</h2>
            <dl className="space-y-2.5">
              <Row label="Status">
                {canSetStatus ? (
                  <select value={story.status} disabled={busy} aria-label="Status"
                    onChange={(e) => patch({ status: e.target.value })} className={FIELD}>
                    <option value="to_do">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="testing">Testing</option>
                    <option value="in_review">In Review</option>
                    <option value="done">Done</option>
                    <option value="blocked">Blocked</option>
                  </select>
                ) : (
                  <span className={cn('inline-block rounded-md border px-2 py-0.5 text-[10.5px] font-medium',
                    STATUS_TONE[story.status])}>{story.status_label}</span>
                )}
              </Row>

              <Row label="Assignee">
                {canEdit ? (
                  <span className="flex items-center gap-1.5">
                    {story.assignee && <Avatar person={story.assignee} size="sm" />}
                    <select value={story.assignee?.id ?? ''} disabled={busy} aria-label="Assignee"
                      onChange={(e) => patch({ assignee_id: e.target.value || null })}
                      className={FIELD}>
                      <option value="">Unassigned</option>
                      {options.assignees.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.roll ? `${a.roll} · ${a.name}` : a.name}
                        </option>
                      ))}
                    </select>
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-[12px] text-[#3A3F58]">
                    {story.assignee && <Avatar person={story.assignee} size="sm" />}
                    {story.assignee?.name ?? 'Unassigned'}
                  </span>
                )}
              </Row>

              <Row label="Sprint">
                {canEdit ? (
                  <select value={story.sprint?.id ?? ''} disabled={busy} aria-label="Sprint"
                    onChange={(e) => patch({ sprint_id: e.target.value || null })}
                    className={FIELD}>
                    <option value="">Unscheduled</option>
                    {options.sprints.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                ) : (
                  <span className="text-[12px] text-[#3A3F58]">
                    {story.sprint?.name ?? 'Unscheduled'}
                  </span>
                )}
              </Row>

              <Row label="Priority">
                {canEdit ? (
                  <select value={story.priority} disabled={busy} aria-label="Priority"
                    onChange={(e) => patch({ priority: e.target.value })} className={FIELD}>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                ) : (
                  <span className={cn('flex items-center gap-1 text-[12px]',
                    story.priority === 'high' ? 'text-[#DC2626]'
                      : story.priority === 'low' ? 'text-[#6B7280]' : 'text-[#D97706]')}>
                    {story.priority === 'high' ? <ChevronUp className="h-3.5 w-3.5" />
                      : story.priority === 'low' ? <ChevronDown className="h-3.5 w-3.5" />
                        : <Minus className="h-3.5 w-3.5" />}
                    {story.priority_label}
                  </span>
                )}
              </Row>

              <Row label="Reporter">
                {/* Who put the story here. "AI Planning" for the drafted set -
                    crediting the approving trainer would be a small lie. */}
                <span className="text-[12px] text-[#3A3F58]">{story.created_by}</span>
              </Row>
              <Row label="Epic">
                {story.epic_key && canEdit ? (
                  <a href={`/trainer/user-stories/${encodeURIComponent(batch.batch_code)}`}
                    className="text-[12px] font-medium text-[#2563EB] hover:underline">
                    {story.epic_key} · {story.epic_title}
                  </a>
                ) : (
                  <span className="text-[12px] text-[#3A3F58]">
                    {story.epic_key ? `${story.epic_key} · ${story.epic_title}` : '—'}
                  </span>
                )}
              </Row>
              <Row label="Type">
                <span className="text-[12px] text-[#3A3F58]">{story.type_label}</span>
              </Row>
              <Row label="Story Points">
                <span className="text-[12px] text-[#3A3F58]">{story.story_points}</span>
              </Row>
              <Row label="Due date">
                {canEdit ? (
                  <input type="date" value={story.due_date ?? ''} disabled={busy}
                    aria-label="Due date"
                    onChange={(e) => patch({ due_date: e.target.value || null })}
                    className={cn(FIELD, story.overdue && 'border-[#FECACA] text-[#DC2626]')} />
                ) : (
                  <span className={cn('flex items-center gap-1 text-[12px]',
                    story.overdue ? 'font-medium text-[#DC2626]' : 'text-[#3A3F58]')}>
                    {story.due_date && <CalendarClock className="h-3.5 w-3.5" />}
                    {story.due_date
                      ? new Date(story.due_date).toLocaleDateString('en-IN',
                        { day: '2-digit', month: 'short', year: 'numeric' })
                      : 'None set'}
                  </span>
                )}
              </Row>
              {story.overdue && (
                <Row label="">
                  <span className="flex items-center gap-1 text-[11px] font-medium text-[#DC2626]">
                    <AlertTriangle className="h-3.5 w-3.5" /> Past its due date
                  </span>
                </Row>
              )}
              {story.dependencies && (
                <Row label="Dependencies">
                  <span className="text-[12px] text-[#3A3F58]">{story.dependencies}</span>
                </Row>
              )}
              {story.labels.length > 0 && (
                <Row label="Labels">
                  <span className="flex flex-wrap gap-1">
                    {story.labels.map((l) => (
                      <span key={l}
                        className="rounded-md border border-[#E5E7EB] bg-[#F9FAFB] px-1.5 py-0.5 text-[10.5px] text-[#4B5563]">
                        {l}
                      </span>
                    ))}
                  </span>
                </Row>
              )}
              <Row label="Created">
                <span className="text-[12px] text-[#3A3F58]">{fmt(story.created_at)}</span>
              </Row>
              <Row label="Updated">
                <span className="text-[12px] text-[#3A3F58]">{fmt(story.updated_at)}</span>
              </Row>
              {story.completed_at && (
                <Row label="Completed">
                  <span className="text-[12px] text-[#3A3F58]">{fmt(story.completed_at)}</span>
                </Row>
              )}
            </dl>
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[13px] font-semibold">Project</h2>
            <p className="mt-1 text-[12.5px] text-[#4B5563]">
              {batch.project_title ?? 'Untitled project'}
            </p>
            <p className="mt-0.5 text-[11.5px] text-[#9CA3AF]">
              {batch.batch_code} · {batch.department}
              {batch.section ? `-${batch.section}` : ''} · {batch.members} members
            </p>
            <p className="text-[11.5px] text-[#9CA3AF]">Guide: {batch.guide ?? '—'}</p>
          </section>

          {/* Where the story came from, for the people who can go and look. */}
          {canEdit && story.review_status && (
            <section className={cn(CARD, 'p-4')}>
              <h2 className="flex items-center gap-1.5 text-[13px] font-semibold">
                <Sparkles className="h-4 w-4 text-[#7C3AED]" /> Origin
              </h2>
              <p className="mt-1.5 text-[11.5px] text-[#6B7280]">
                {story.created_by === 'AI Planning'
                  ? 'Drafted by AI Planning and approved by a trainer.'
                  : `Written by ${story.created_by}.`}
                {story.ai_confidence !== null && ` AI confidence ${story.ai_confidence}%.`}
              </p>
              <p className="mt-1 text-[11.5px] text-[#9CA3AF]">
                Review status: {story.review_status_label}
              </p>
              {story.trainer_comment && (
                <p className="mt-2 rounded-lg bg-[#FAFBFE] px-2 py-1.5 text-[11.5px] text-[#4B5563]">
                  {story.trainer_comment}
                </p>
              )}
            </section>
          )}

          {!canEdit && (
            <p className="flex items-start gap-2 rounded-xl border border-[#E5E7EB] bg-white px-3 py-2.5 text-[11.5px] text-[#6B7280]">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#9CA3AF]" />
              Only your trainer can change this story. Ask in the comments if
              something here looks wrong.
            </p>
          )}
        </aside>
      </div>
    </StoryShell>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[92px_minmax(0,1fr)] items-center gap-2">
      <dt className="text-[11px] text-[#9CA3AF]">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}
