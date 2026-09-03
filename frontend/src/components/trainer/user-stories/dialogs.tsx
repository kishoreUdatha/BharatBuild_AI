'use client'

/**
 * The things a trainer sets up around a backlog: a story, a sheet of stories,
 * a sprint to put them in, and the repository whose pushes get tracked.
 *
 * Each is a modal rather than a route because none of them is worth losing the
 * filtered board behind it - the trainer comes straight back to the same view.
 */

import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, Copy, Download, GitBranch, Loader2, RefreshCw,
  Upload, UserCheck, X,
} from 'lucide-react'
import type {
  GitConnection, NewSprintInput, NewStoryInput, Option, Person, SprintRef,
  StoryImportResult,
} from '@/lib/trainer-api'
import { cn } from '@/lib/utils'
import { BTN_OUTLINE, BTN_PRIMARY, FIELD, Field } from './bits'

function Modal({ title, subtitle, onClose, children }: {
  title: string
  subtitle: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      role="dialog" aria-modal="true" aria-label={title}>
      {/* The backdrop is a sibling of the card, so a click inside the card
          never reaches it and closes the dialog under the trainer's hands. */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative flex max-h-full w-full max-w-[560px] flex-col overflow-hidden rounded-xl bg-white shadow-xl">
        <header className="flex items-start justify-between gap-3 border-b border-[#E5E7EB] px-4 py-3">
          <div>
            <h2 className="text-[14px] font-bold text-[#1B1B3A]">{title}</h2>
            <p className="text-[11px] text-[#6B7280]">{subtitle}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
            <X className="h-4 w-4" />
          </button>
        </header>
        {children}
      </div>
    </div>
  )
}

/**
 * Pull the acceptance criteria back out of a description.
 *
 * They are typed in one box because that is how a trainer writes a story -
 * the narrative and what would make it done are one thought. They are still
 * stored as separate tickable items, because the ticks are what the board,
 * the progress figure and the approval checklist count.
 *
 * The split is an "Acceptance criteria" heading. Nothing else counts: a story
 * whose description happens to contain a dashed list is not a story with
 * criteria, and guessing would put half a narrative on the checklist.
 */
const AC_HEADING = /^\s*acceptance\s*criteria\s*:?\s*$/i
const BULLET = /^\s*(?:[-*\u2022\u2013]|\d+[.)])\s*/

export function splitCriteria(text: string): {
  narrative: string
  criteria: string[]
} {
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

export function AddStoryDialog({
  epics, sprints, assignees, priorities, types, statuses, busy, onClose, onSubmit,
}: {
  epics: { key: string; title: string }[]
  sprints: SprintRef[]
  assignees: Person[]
  priorities: Option[]
  types: Option[]
  statuses: Option[]
  busy: boolean
  onClose: () => void
  onSubmit: (input: NewStoryInput) => Promise<void>
}) {
  const [form, setForm] = useState<NewStoryInput>({
    title: '', narrative: '', epic_key: '', story_points: 0,
    priority: 'medium', story_type: 'story', status: 'to_do',
    assignee_id: '', sprint_id: '', acceptance_criteria: [],
  })
  const set = (patch: Partial<NewStoryInput>) => setForm((f) => ({ ...f, ...patch }))

  // Worked out as they type, so the count below the box tells them whether
  // the heading landed rather than leaving them to find out after saving.
  const parsed = splitCriteria(form.narrative ?? '')

  const submit = () => onSubmit({
    ...form,
    narrative: parsed.narrative,
    acceptance_criteria: parsed.criteria,
  })

  return (
    <Modal title="Add User Story" onClose={onClose}
      subtitle="Written by you, so it goes straight onto the backlog - no AI review step.">
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <Field label="Title">
          <input value={form.title} autoFocus className={FIELD}
            placeholder="Generate fraud alert and notification"
            onChange={(e) => set({ title: e.target.value })} />
        </Field>

        <Field label="Description">
          <textarea rows={7} value={form.narrative}
            placeholder={'As a …, I want … so that …\n\nAcceptance criteria:\n'
              + '- Alert generated when fraud score > 0.8\n- Notification sent to admin'}
            onChange={(e) => set({ narrative: e.target.value })}
            className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[12.5px] leading-relaxed outline-none focus:border-[#2563EB]" />
          <p className="mt-1 text-[11px] text-[#6B7280]">
            {parsed.criteria.length > 0 ? (
              <span className="text-[#166534]">
                {parsed.criteria.length} acceptance{' '}
                {parsed.criteria.length === 1 ? 'criterion' : 'criteria'} found — each
                becomes a tick on the story.
              </span>
            ) : (
              <>
                Put a line reading <code className="font-mono">Acceptance criteria:</code>{' '}
                and list them under it, one per line. Each becomes a tick on the story.
              </>
            )}
          </p>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Epic">
            <select value={form.epic_key} className={FIELD}
              onChange={(e) => set({ epic_key: e.target.value })}>
              <option value="">No epic</option>
              {epics.map((e) => (
                <option key={e.key} value={e.key}>{e.key} · {e.title}</option>
              ))}
            </select>
          </Field>
          <Field label="Sprint">
            <select value={form.sprint_id} className={FIELD}
              onChange={(e) => set({ sprint_id: e.target.value })}>
              <option value="">Unscheduled</option>
              {sprints.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Assignee">
            <select value={form.assignee_id} className={FIELD}
              onChange={(e) => set({ assignee_id: e.target.value })}>
              <option value="">Unassigned</option>
              {assignees.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.roll ? `${p.roll} · ${p.name}` : p.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Status">
            <select value={form.status} className={FIELD}
              onChange={(e) => set({ status: e.target.value })}>
              {statuses.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="Priority">
            <select value={form.priority} className={FIELD}
              onChange={(e) => set({ priority: e.target.value })}>
              {priorities.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="Type">
            <select value={form.story_type} className={FIELD}
              onChange={(e) => set({ story_type: e.target.value })}>
              {types.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <Field label="Story Points">
            <input type="number" min={0} max={100} value={form.story_points} className={FIELD}
              onChange={(e) => set({ story_points: Number(e.target.value) })} />
          </Field>
        </div>

      </div>

      <footer className="flex justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
        <button type="button" className={BTN_OUTLINE} onClick={onClose}>Cancel</button>
        <button type="button" className={BTN_PRIMARY} onClick={submit}
          disabled={busy || form.title.trim().length < 3}>
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Add story
        </button>
      </footer>
    </Modal>
  )
}

export function ImportStoriesDialog({
  busy, result, file, onClose, onTemplate, onPick, onConfirm,
}: {
  busy: boolean
  /** The validation pass, or the finished import once confirmed. */
  result: StoryImportResult | null
  file: File | null
  onClose: () => void
  onTemplate: () => void
  onPick: (file: File) => void
  onConfirm: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const done = Boolean(result && !result.dry_run)

  return (
    <Modal title="Import Stories" onClose={onClose}
      subtitle="The BharatBuild user stories template, as .xlsx or CSV.">
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {!result && (
          <>
            <p className="text-[12px] leading-relaxed text-[#4B5563]">
              Columns: <span className="font-medium">Story ID, Work Type, Epic, Summary,
              Description, Acceptance Criteria, Priority, Story Points, Assignee Roll No,
              Assignee Name, Sprint, Status, Labels</span>. Acceptance criteria go in one
              cell as numbered lines. An assignee is matched on roll number first, then on
              name, and matched against this batch - anyone it cannot find imports
              unassigned rather than failing the row. An epic or sprint that does not
              exist yet is created. Highest and Lowest are recorded as High and Low.
            </p>
            <button type="button" className={BTN_OUTLINE} onClick={onTemplate}>
              <Download className="h-4 w-4" /> Download the template
            </button>
          </>
        )}

        <input ref={fileRef} type="file" className="hidden"
          accept=".xlsx,.xlsm,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={(e) => {
            const chosen = e.target.files?.[0]
            if (chosen) onPick(chosen)
            e.target.value = ''
          }} />

        <button type="button" disabled={busy} onClick={() => fileRef.current?.click()}
          className={cn(result ? BTN_OUTLINE : BTN_PRIMARY, 'w-full justify-center')}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {file ? `${file.name} — choose another` : 'Choose a file'}
        </button>

        {result && (
          <>
            <div className={cn('rounded-lg border px-3 py-2 text-[12px]',
              done
                ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
                : result.ready === 0
                  ? 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]'
                  : 'border-[#BFDBFE] bg-[#EFF6FF] text-[#1E40AF]')}>
              {done
                ? `${result.count} ${result.count === 1 ? 'story' : 'stories'} added: `
                  + result.created.join(', ')
                : `${result.rows} rows read · ${result.ready} ready to import`
                  + (result.rows - result.ready > 0
                    ? ` · ${result.rows - result.ready} need fixing first` : '')
                  + (result.notes.length > 0
                    ? ` · ${result.notes.length} with notes` : '')}
            </div>

            <p className="text-[11px] text-[#9CA3AF]">
              Columns found: {result.columns.join(', ')}
            </p>

            {result.preview.length > 0 && (
              <div className="max-h-[280px] overflow-auto rounded-lg border border-[#E5E7EB]">
                <table className="w-full min-w-[560px] text-left text-[11.5px]">
                  <thead className="sticky top-0 bg-[#FAFBFF] text-[11px] text-[#6B7280]">
                    <tr>
                      {['Row', 'Summary', 'Assignee', 'Sprint', 'Status', ''].map((h) => (
                        <th key={h} className="whitespace-nowrap px-2 py-1.5 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F1F2F8]">
                    {result.preview.map((r) => (
                      <tr key={r.row} className={cn(r.issues.length > 0 && 'bg-[#FEF2F2]')}>
                        <td className="px-2 py-1.5 text-[#9CA3AF]">{r.row}</td>
                        <td className="px-2 py-1.5">
                          <span className="block max-w-[220px] truncate text-[#1B1B3A]">
                            {r.summary}
                          </span>
                          <span className="block text-[10px] text-[#9CA3AF]">
                            {r.key} · {r.criteria} criteria
                            {r.epic && <> · {r.epic}{r.new_epic && ' (new epic)'}</>}
                            {r.labels && <> · {r.labels}</>}
                          </span>
                          {r.note && (
                            <span className="block text-[10px] text-[#C2410C]">{r.note}</span>
                          )}
                        </td>
                        <td className="px-2 py-1.5 text-[#4B5563]">
                          {r.assignee?.name ?? <span className="text-[#9CA3AF]">—</span>}
                        </td>
                        <td className="px-2 py-1.5 text-[#4B5563]">
                          {r.sprint ?? '—'}{r.new_sprint && ' (new)'}
                        </td>
                        <td className="px-2 py-1.5 text-[#4B5563]">{r.status ?? '—'}</td>
                        <td className="px-2 py-1.5">
                          {/* Red stops the row; amber lets it through and says
                              what it lost on the way. */}
                          {r.issues.length > 0 ? (
                            <span className="flex items-start gap-1 text-[10.5px] text-[#DC2626]">
                              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                              {r.issues.join('; ')}
                            </span>
                          ) : r.warnings.length > 0 ? (
                            <span className="flex items-start gap-1 text-[10.5px] text-[#C2410C]">
                              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                              {r.warnings.join('; ')}
                            </span>
                          ) : (
                            <CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      <footer className="flex justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
        <button type="button" className={BTN_OUTLINE} onClick={onClose}>
          {done ? 'Done' : 'Cancel'}
        </button>
        {result && !done && (
          <button type="button" className={BTN_PRIMARY} disabled={busy || result.ready === 0}
            onClick={onConfirm}>
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Import {result.ready} {result.ready === 1 ? 'story' : 'stories'}
          </button>
        )}
      </footer>
    </Modal>
  )
}

export function AddSprintDialog({ busy, onClose, onSubmit, initial, mode = 'create' }: {
  busy: boolean
  onClose: () => void
  onSubmit: (input: NewSprintInput) => Promise<void>
  /** Present when editing: the sprint as it stands. */
  initial?: NewSprintInput
  mode?: 'create' | 'edit'
}) {
  const [form, setForm] = useState<NewSprintInput>(initial ?? {
    name: '', goal: '', start_date: '', end_date: '', state: 'planned',
  })
  const set = (patch: Partial<NewSprintInput>) => setForm((f) => ({ ...f, ...patch }))

  return (
    <Modal title={mode === 'edit' ? 'Edit Sprint' : 'Add Sprint'} onClose={onClose}
      subtitle={mode === 'edit'
        ? 'Its dates and goal. What it is carrying comes from the stories in it.'
        : 'A time box on this batch, so stories have somewhere to be scheduled.'}>
      <div className="space-y-3 px-4 py-3">
        <Field label="Name">
          <input value={form.name} autoFocus className={FIELD} placeholder="Sprint 5"
            onChange={(e) => set({ name: e.target.value })} />
        </Field>
        <Field label="Goal">
          <input value={form.goal} className={FIELD}
            placeholder="Documentation and final review"
            onChange={(e) => set({ goal: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Starts">
            <input type="date" value={form.start_date} className={FIELD}
              onChange={(e) => set({ start_date: e.target.value })} />
          </Field>
          <Field label="Ends">
            <input type="date" value={form.end_date} className={FIELD}
              onChange={(e) => set({ end_date: e.target.value })} />
          </Field>
        </div>
        <Field label="State">
          <select value={form.state} className={FIELD}
            onChange={(e) => set({ state: e.target.value })}>
            <option value="planned">Planned</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
        </Field>
      </div>

      <footer className="flex justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
        <button type="button" className={BTN_OUTLINE} onClick={onClose}>Cancel</button>
        <button type="button" className={BTN_PRIMARY} disabled={busy || form.name.trim().length < 2}
          onClick={() => onSubmit({
            ...form,
            start_date: form.start_date || undefined,
            end_date: form.end_date || undefined,
            goal: form.goal || undefined,
          })}>
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {mode === 'edit' ? 'Save sprint' : 'Add sprint'}
        </button>
      </footer>
    </Modal>
  )
}


/** One value the trainer has to paste somewhere else, with a copy button. */
function CopyRow({ label, value, mono = true }: {
  label: string
  value: string
  mono?: boolean
}) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // Clipboard is blocked on insecure origins; the value is on screen and
      // selectable, so this is a missing convenience rather than a failure.
    }
  }
  return (
    <Field label={label}>
      <div className="flex items-stretch gap-1.5">
        <input readOnly value={value} onFocus={(e) => e.currentTarget.select()}
          className={cn(FIELD, 'flex-1 bg-[#F9FAFC]', mono && 'font-mono text-[11.5px]')} />
        <button type="button" onClick={copy} aria-label={`Copy ${label}`}
          className="flex w-[38px] shrink-0 items-center justify-center rounded-lg border border-[#E5E7EB] text-[#6B7280] hover:bg-[#F4F5FA]">
          {copied ? <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
            : <Copy className="h-4 w-4" />}
        </button>
      </div>
    </Field>
  )
}

/**
 * Wiring a batch's repository to the board.
 *
 * The secret is shown in full rather than masked: a trainer who cannot read it
 * cannot paste it into GitHub, and it only ever grants the right to post
 * commits to this one batch.
 */
export function ConnectGitDialog({ busy, connection, onClose, onSave, onRotate }: {
  busy: boolean
  connection: GitConnection | null
  onClose: () => void
  onSave: (repoUrl: string) => Promise<void>
  onRotate: () => Promise<void>
}) {
  const [repo, setRepo] = useState('')
  // Only seeds the field - typing after the first load must not be overwritten
  // by the refresh that follows a save.
  const seeded = useRef(false)
  useEffect(() => {
    if (connection && !seeded.current) {
      seeded.current = true
      setRepo(connection.repo_url ?? '')
    }
  }, [connection])

  return (
    <Modal title="Connect Repository" onClose={onClose}
      subtitle="Pushes land on the story whose key the commit message names.">
      <div className="max-h-[70vh] space-y-3 overflow-y-auto px-4 py-3">
        {!connection ? (
          <p className="flex items-center gap-2 py-6 text-[12.5px] text-[#6B7280]">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading connection…
          </p>
        ) : (
          <>
            <div className={cn('flex items-center gap-2 rounded-lg border px-3 py-2 text-[12px]',
              connection.commits > 0
                ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
                : 'border-[#E5E7EB] bg-[#F9FAFC] text-[#6B7280]')}>
              <GitBranch className="h-4 w-4 shrink-0" />
              {connection.commits > 0 ? (
                <span>
                  {connection.commits} commit{connection.commits === 1 ? '' : 's'} received
                  {connection.last_received_at &&
                    ` · last on ${new Date(connection.last_received_at).toLocaleString('en-IN', {
                      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}`}
                </span>
              ) : (
                <span>Nothing received yet. Add the webhook below, then push once to test.</span>
              )}
            </div>

            {/* On a student project the lead owns the repo and is the only
                one who can add a webhook to it, so a trainer opening this
                needs to see that it is already handled. */}
            {connection.connected_by && (
              <p className="flex items-start gap-1.5 rounded-lg border border-[#DDD6FE] bg-[#FAF9FF] px-3 py-2 text-[11.5px] text-[#5B21B6]">
                <UserCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  Connected by <strong>{connection.connected_by.name}</strong>
                  {' '}({connection.connected_by.role.toLowerCase()})
                  {connection.connected_by.at &&
                    ` on ${new Date(connection.connected_by.at).toLocaleDateString('en-IN', {
                      day: '2-digit', month: 'short', year: 'numeric' })}`}
                  . You do not need to set it up again — saving here overwrites
                  what they entered.
                </span>
              </p>
            )}

            {!connection.connected && (
              <p className="flex items-start gap-1.5 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] text-[#92400E]">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  Nobody has connected a repository yet. If the team created it on
                  their own account, the batch leader can do this from their portal
                  — they are the only one with the rights to add the webhook there.
                </span>
              </p>
            )}

            <Field label="Repository link">
              <input value={repo} className={FIELD}
                placeholder="https://github.com/college/project"
                onChange={(e) => setRepo(e.target.value)} />
            </Field>

            <CopyRow label="Payload URL" value={connection.webhook_url} />
            {!connection.reachable && (
              <p className="flex items-start gap-1.5 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] text-[#92400E]">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  This address only exists on your network, so GitHub cannot post to
                  it. Point <code className="font-mono">WEBHOOK_PUBLIC_URL</code> at a
                  public address (or a tunnel while testing) and reopen this dialog.
                </span>
              </p>
            )}
            <CopyRow label="Secret" value={connection.secret ?? ''} />

            <div className="rounded-lg bg-[#F9FAFC] px-3 py-2.5 text-[11.5px] leading-relaxed text-[#4B5563]">
              <p className="font-semibold text-[#1B1B3A]">In GitHub</p>
              <p>
                Settings → Webhooks → Add webhook. Paste the two values above,
                set Content type to <code className="font-mono">application/json</code>,
                and send just the push event. GitLab works the same way, with the
                secret going in the Secret token box.
              </p>
              <p className="mt-2 font-semibold text-[#1B1B3A]">Tell the students</p>
              <p>
                Name the story in the commit message and it attaches itself:{' '}
                <code className="font-mono">git commit -m &quot;{connection.key_example}&quot;</code>.
                Commits with no key are still recorded against the batch.
              </p>
            </div>

            {/* The repository is shared; credit for what is in it is not.
                Each student links their own git account from their portal,
                because only they know the email their git is configured with. */}
            <div>
              <p className="mb-1.5 text-[11.5px] font-semibold text-[#1B1B3A]">
                Who is committing{' '}
                <span className="font-normal text-[#9CA3AF]">
                  {connection.team.filter((m) => m.connected).length} of{' '}
                  {connection.team.length} linked
                </span>
              </p>
              <ul className="divide-y divide-[#F1F2F8] rounded-lg border border-[#E5E7EB]">
                {connection.team.map((m) => (
                  <li key={m.student_id} className="flex items-center gap-2 px-2.5 py-2">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[12px] text-[#1B1B3A]">{m.name}</span>
                      <span className="block truncate font-mono text-[10.5px] text-[#9CA3AF]">
                        {m.username ? `@${m.username}` : m.emails[0] ?? 'no account linked yet'}
                      </span>
                    </span>
                    <span className="shrink-0 text-[11px] text-[#6B7280]">
                      {m.commits} commit{m.commits === 1 ? '' : 's'}
                    </span>
                    {m.verified ? (
                      <span title="Proved the account is theirs"
                        className="shrink-0 rounded bg-[#F0FDF4] px-1.5 py-0.5 text-[10px] text-[#166534]">
                        Verified
                      </span>
                    ) : m.connected ? (
                      <span className="shrink-0 rounded bg-[#F4F5FA] px-1.5 py-0.5 text-[10px] text-[#6B7280]">
                        Linked
                      </span>
                    ) : (
                      <span className="shrink-0 rounded bg-[#FFFBEB] px-1.5 py-0.5 text-[10px] text-[#92400E]">
                        Not linked
                      </span>
                    )}
                  </li>
                ))}
              </ul>
              <p className="mt-1.5 text-[11px] text-[#6B7280]">
                Students link their own account under My Stories → My Git Account.
                Until they do, their commits are credited to nobody unless git is
                configured with their college address.
              </p>
            </div>

            <button type="button" disabled={busy} onClick={onRotate}
              className="flex items-center gap-1.5 text-[11.5px] text-[#DC2626] hover:underline disabled:opacity-50">
              <RefreshCw className="h-3.5 w-3.5" />
              Rotate the secret — the old one stops working immediately
            </button>
          </>
        )}
      </div>

      <footer className="flex justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
        <button type="button" className={BTN_OUTLINE} onClick={onClose}>Close</button>
        <button type="button" className={BTN_PRIMARY} disabled={busy || !connection}
          onClick={() => onSave(repo.trim())}>
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          Save
        </button>
      </footer>
    </Modal>
  )
}
