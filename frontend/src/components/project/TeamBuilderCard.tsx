'use client'

import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { Code2, ExternalLink, GitBranch, Loader2, Users } from 'lucide-react'
import type { BuilderResponse, TeamBuilder, TeamRepo } from '@/lib/student-api'

/**
 * The one build workspace a batch's team shares.
 *
 * Four students on a batch work in a single project, the way four developers
 * share a repository, and no other batch can open it. The workspace is created
 * the first time somebody asks for it rather than with the batch, because
 * batches are made empty and filled later.
 */
export function TeamBuilderCard({
  batchCode,
  load,
  open,
  canOpen = true,
  readOnlyNote,
  repoHref,
}: {
  batchCode?: string | null
  load: () => Promise<BuilderResponse>
  open: () => Promise<BuilderResponse>
  /** False for someone who may look but not start one. */
  canOpen?: boolean
  readOnlyNote?: string
  /** Where to send someone who needs to connect one. */
  repoHref?: string
}) {
  const router = useRouter()
  const [state, setState] = useState<TeamBuilder | null>(null)
  const [repo, setRepo] = useState<TeamRepo | null>(null)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  const refresh = useCallback(async () => {
    try {
      const data = await load()
      setState(data.workspace)
      setRepo(data.repo ?? null)
    } catch {
      setState(null)
      setRepo(null)
    }
  }, [load])

  useEffect(() => { refresh() }, [refresh])

  // The builder picks a project up from session storage, so the handoff is
  // written there rather than passed in the URL - a project id in a link is
  // one copy-paste away from being sent to somebody who cannot open it.
  const enter = (workspace: TeamBuilder) => {
    if (!workspace.project_id) return
    if (workspace.workspace_id) {
      sessionStorage.setItem('workspaceId', workspace.workspace_id)
    }
    sessionStorage.setItem('projectId', workspace.project_id)
    router.push('/build')
  }

  const start = async () => {
    setBusy(true)
    setProblem('')
    try {
      const data = await open()
      setState(data.workspace)
      setRepo(data.repo ?? null)
      enter(data.workspace)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail
      setProblem(typeof detail === 'string'
        ? detail
        : 'The workspace could not be opened. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const started = state?.exists === true

  return (
    <section className="rounded-xl border border-[#E5E7EB] bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#EEF4FF] text-[#2563EB]">
            <Code2 className="h-4.5 w-4.5" />
          </span>
          <div className="min-w-0">
            <h2 className="text-[13.5px] font-semibold text-[#1B1B3A]">
              Team build workspace
            </h2>
            <p className="mt-0.5 text-[11.5px] text-[#6B7280]">
              {started
                ? <>One workspace for the whole team{batchCode ? ` on ${batchCode}` : ''}. Everyone
                    on this batch opens the same project; nobody outside it can.</>
                : <>Not started yet. The first person to open it creates the
                    workspace, and the rest of the team joins the same one.</>}
            </p>
            {started && (
              <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#6B7280]">
                <span className="inline-flex items-center gap-1">
                  <Users className="h-3 w-3" /> Shared with the batch
                </span>
                {state?.status && (
                  <span className="rounded-full bg-[#F4F5FA] px-2 py-0.5 capitalize">
                    {state.status.replace(/_/g, ' ')}
                  </span>
                )}
                {typeof state?.progress === 'number' && state.progress > 0 && (
                  <span>{state.progress}% built</span>
                )}
              </p>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {started ? (
            <button type="button" onClick={() => state && enter(state)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-1.5 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8]">
              Open workspace <ExternalLink className="h-3.5 w-3.5" />
            </button>
          ) : canOpen ? (
            <button type="button" onClick={start} disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-1.5 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-60">
              {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {busy ? 'Opening…' : 'Start building'}
            </button>
          ) : (
            <span className="rounded-lg border border-[#E5E7EB] px-3 py-1.5 text-[12px] text-[#9CA3AF]">
              Not started
            </span>
          )}
        </div>
      </div>

      {/* Where the code actually lives. The workspace is where a team
          builds; the repository is what they build into, so the two belong
          on one card rather than on two screens that never mention each
          other. */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[#F1F2F8] pt-2.5">
        <span className="flex min-w-0 items-center gap-1.5 text-[11.5px] text-[#6B7280]">
          <GitBranch className="h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />
          {repo?.connected ? (
            <>
              <span className="text-[#4B5563]">Repository</span>
              {repo.url ? (
                <a href={repo.url} target="_blank" rel="noopener noreferrer"
                  className="truncate font-medium text-[#2563EB] hover:underline">
                  {repo.name ?? repo.url}
                </a>
              ) : (
                <span className="truncate font-medium text-[#1B1B3A]">{repo.name}</span>
              )}
              {repo.just_created && (
                <span className="shrink-0 rounded-full bg-[#ECFDF5] px-2 py-0.5 text-[10.5px] font-medium text-[#047857]">
                  just created
                </span>
              )}
            </>
          ) : (
            <span>
              {repo?.reason
                ?? 'No repository connected yet — the team’s code has nowhere to land.'}
            </span>
          )}
        </span>
        {!repo?.connected && repoHref && (
          <a href={repoHref}
            className="shrink-0 text-[11.5px] font-medium text-[#2563EB] hover:underline">
            Connect a repository
          </a>
        )}
      </div>

      {problem && (
        <p className="mt-2.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11.5px] text-[#B91C1C]">
          {problem}
        </p>
      )}
      {!started && !canOpen && readOnlyNote && (
        <p className="mt-2.5 text-[11px] text-[#9CA3AF]">{readOnlyNote}</p>
      )}
    </section>
  )
}
