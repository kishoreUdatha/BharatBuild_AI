'use client'

import { useCallback, useEffect, useState } from 'react'
import { Check, Copy, ExternalLink, GitBranch, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

/**
 * Start work on a story: make the branch, or be told exactly why not.
 *
 * The branch is created in the team's repository, the way Jira's "Create
 * branch" does it. What actually links the work back to the story is the story
 * key in the commit message - `story_keys()` on the server reads it out of the
 * text - so the commands stay on the card underneath. They are the fallback
 * when there is no repository to create anything in, which is most teams until
 * their lead connects one.
 */

interface BranchState {
  story_key: string
  branch: string
  repo_url: string | null
  can_create: boolean
  reason: string | null
}

interface Created {
  branch: string
  existed: boolean
  base: string
  url: string
  repo: string
}

function CopyLine({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // Refused on an insecure origin or by permission. The text is on screen
      // either way, so this is not worth an error.
    }
  }
  return (
    <div>
      <p className="text-[10.5px] uppercase tracking-wide text-[#9CA3AF]">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-md bg-[#F4F5FA] px-2 py-1.5 font-mono text-[11.5px] text-[#1B1B3A]">
          {value}
        </code>
        <button type="button" onClick={copy}
          title={`Copy ${label.toLowerCase()}`} aria-label={`Copy ${label.toLowerCase()}`}
          className="shrink-0 rounded-md border border-[#E5E7EB] p-1.5 text-[#6B7280] hover:bg-[#F4F5FA]">
          {copied ? <Check className="h-3.5 w-3.5 text-[#15803D]" />
                  : <Copy className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  )
}

export function BranchHint({
  storyId,
  storyKey,
  title,
  compact = false,
}: {
  storyId: string
  storyKey: string
  title: string
  compact?: boolean
}) {
  const [state, setState] = useState<BranchState | null>(null)
  const [made, setMade] = useState<Created | null>(null)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  const [open, setOpen] = useState(!compact)

  const load = useCallback(async () => {
    try {
      setState(await apiClient.get<BranchState>(`/stories/${storyId}/branch`))
    } catch {
      setState(null)
    }
  }, [storyId])

  useEffect(() => { if (open) load() }, [open, load])

  const create = async () => {
    setBusy(true)
    setProblem('')
    try {
      setMade(await apiClient.post<Created>(`/stories/${storyId}/branch`, {}))
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail
      setProblem(typeof detail === 'string'
        ? detail
        : 'The branch could not be created. Try again.')
    } finally {
      setBusy(false)
    }
  }

  if (compact && !open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[#2563EB] hover:underline">
        <GitBranch className="h-3.5 w-3.5" /> Work on this story
      </button>
    )
  }

  const branch = state?.branch ?? `${storyKey}`
  const canCreate = state?.can_create === true

  return (
    <section className="rounded-lg border border-[#E5E7EB] bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-[12px] font-semibold text-[#1B1B3A]">
          <GitBranch className="h-3.5 w-3.5 text-[#6B7280]" /> Work on this story
        </h3>
        {state?.repo_url && (
          <a href={state.repo_url} target="_blank" rel="noopener noreferrer"
            className="text-[11px] font-medium text-[#2563EB] hover:underline">
            Repository
          </a>
        )}
      </div>

      {made ? (
        <div className="mt-2.5 rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] p-2.5">
          <p className="text-[11.5px] font-medium text-[#15803D]">
            {made.existed ? 'Branch already exists' : 'Branch created'}
          </p>
          <p className="mt-0.5 break-all font-mono text-[11px] text-[#166534]">
            {made.branch}
          </p>
          <p className="mt-0.5 text-[10.5px] text-[#4B5563]">
            off <span className="font-mono">{made.base}</span> in {made.repo}
          </p>
          <div className="mt-2 space-y-2">
            <a href={made.url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-[11.5px] font-medium text-[#2563EB] hover:underline">
              View on GitHub <ExternalLink className="h-3 w-3" />
            </a>
            <CopyLine label="Check it out"
              value={`git fetch && git checkout ${made.branch}`} />
          </div>
        </div>
      ) : (
        <>
          <button type="button" onClick={create} disabled={busy || !canCreate}
            title={state?.reason ?? undefined}
            className="mt-2.5 inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-2 text-[12px] font-medium text-white hover:bg-[#1D4ED8] disabled:cursor-not-allowed disabled:opacity-50">
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {busy ? 'Creating…' : 'Create branch'}
          </button>

          {/* Said before the button is pressed, not after. */}
          {state && !canCreate && state.reason && (
            <p className="mt-1.5 text-[10.5px] leading-relaxed text-[#B45309]">
              {state.reason} Make it yourself with the command below.
            </p>
          )}
        </>
      )}

      <div className="mt-2.5 space-y-2.5 border-t border-[#F1F2F8] pt-2.5">
        <CopyLine label="Branch name" value={branch} />
        {!made && <CopyLine label="Or start it yourself" value={`git checkout -b ${branch}`} />}
        <CopyLine label="Commit onto this story"
          value={`git commit -m "${storyKey} <what you did>"`} />
      </div>

      {problem && (
        <p className="mt-2.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-2 text-[11px] text-[#B91C1C]">
          {problem}
        </p>
      )}

      <p className="mt-2.5 text-[10.5px] leading-relaxed text-[#6B7280]">
        Keep <span className="font-mono text-[#374151]">{storyKey}</span> in the
        commit message — the branch is a convenience, the key in the message is
        what attaches the commit to this story.
      </p>
    </section>
  )
}
