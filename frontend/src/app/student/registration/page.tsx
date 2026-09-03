'use client'

import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckCircle2,
  ClipboardCopy,
  Clock,
  FileText,
  Headphones,
  Info,
  Loader2,
  Lock,
  Receipt,
  RefreshCw,
  Send,
  ShieldCheck,
  Users,
} from 'lucide-react'
import {
  downloadReceipt,
  fetchRegistration,
  joinBatch,
  rupees,
  resendInvite,
  verifyBatchCode,
  type RegistrationState,
  type TeamRow,
} from '@/lib/student-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'

function errorText(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}

/** The five-step strip across the top. */
function Stepper({ steps }: { steps: RegistrationState['steps'] }) {
  return (
    <ol className="flex flex-wrap items-start">
      {steps.map((s, i) => (
        <li key={s.key} className="flex min-w-[122px] flex-1 flex-col items-center text-center">
          <span className="flex w-full items-center">
            <span className={cn('h-[3px] flex-1', i === 0 ? 'bg-transparent'
              : steps[i - 1].state === 'done' ? 'bg-[#16A34A]' : 'bg-[#DDE0EE]')} />
            <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold',
              s.state === 'done' ? 'bg-[#16A34A] text-white'
                : s.state === 'current' ? 'bg-[#2563EB] text-white'
                  : 'border-2 border-[#C7CBDD] bg-white text-[#8A8FA8]')}>
              {s.state === 'done' ? <Check className="h-4 w-4" /> : s.position}
            </span>
            <span className={cn('h-[3px] flex-1', i === steps.length - 1 ? 'bg-transparent'
              : s.state === 'done' ? 'bg-[#2563EB]' : 'bg-[#DDE0EE]')} />
          </span>
          <span className={cn('mt-1.5 text-[12px] leading-tight',
            s.state === 'current' ? 'font-semibold text-[#2563EB]'
              : s.state === 'done' ? 'font-medium text-[#1B1B3A]' : 'text-[#8A8FA8]')}>
            {s.label}
          </span>
        </li>
      ))}
    </ol>
  )
}

function StatePill({ ok, label, pendingLabel }: {
  ok: boolean | null; label: string; pendingLabel?: string
}) {
  if (ok === null) return <span className="text-[13px] text-[#C7CBDD]">—</span>
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-medium',
      ok ? 'bg-[#F0FDF4] text-[#15803D]' : 'bg-[#FFFBEB] text-[#B45309]')}>
      {ok ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
      {ok ? label : (pendingLabel ?? label)}
    </span>
  )
}

function TeamMemberRow({ row, busy, onRemind }: {
  row: TeamRow; busy: boolean; onRemind: (id: string) => void
}) {
  const initials = (row.name ?? '?').split(' ').map((p) => p[0]).slice(-2).join('').toUpperCase()
  return (
    <li className="grid grid-cols-[28px_minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.1fr)] items-center gap-2 border-b border-[#F1F2F8] py-2.5 last:border-b-0">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#F3F4F6] text-[10.5px] font-medium text-[#6B7280]">
        {row.position}
      </span>
      <span className="flex min-w-0 items-center gap-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#DBE3F5] text-[10.5px] font-semibold text-[#1B2A6B]">
          {initials}
        </span>
        <span className="min-w-0">
          <span className="block truncate text-[12.5px] font-medium text-[#1B1B3A]">{row.name ?? '—'}</span>
          <span className="block text-[10.5px] text-[#6B7280]">{row.roll_number}</span>
        </span>
        <span className={cn('ml-1 shrink-0 rounded-md px-2 py-0.5 text-[10.5px] font-medium',
          row.is_you ? 'bg-[#DBEAFE] text-[#1D4ED8]'
            : row.invite_status === 'joined' ? 'bg-[#EFF6FF] text-[#2563EB]'
              : 'bg-[#FEF3C7] text-[#B45309]')}>
          {row.chip}
        </span>
      </span>
      <span className="text-center">
        <StatePill ok={row.identity_verified} label="Identity Verified" />
      </span>
      <span className="text-center">
        <StatePill ok={row.seat_confirmed} label="Seat Confirmed" />
      </span>
      <span className="flex items-center justify-end gap-2">
        {row.payment_status === null ? (
          <span className="text-[13px] text-[#C7CBDD]">—</span>
        ) : (
          <StatePill ok={row.payment_status === 'paid'} label="Payment Paid" pendingLabel="Payment Pending" />
        )}
        {row.can_remind && (
          <button type="button" disabled={busy} onClick={() => onRemind(row.member_id)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-[#BFDBFE] px-2.5 py-1.5 text-[11.5px] font-medium text-[#2563EB] hover:bg-[#EFF6FF] disabled:opacity-50">
            <Send className="h-3.5 w-3.5" /> Resend Invite
          </button>
        )}
      </span>
    </li>
  )
}

function RegistrationScreen() {
  // Read after mount: there is no window during the server render, and
  // building the link inline would throw.
  const [origin, setOrigin] = useState('')
  useEffect(() => { setOrigin(window.location.origin) }, [])

  // Confirmed beside the button as well as in the page notice. That notice
  // sits under the stepper, ~800px above the invite block, so on its own it
  // tells you nothing where you are actually looking.
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), 2500)
    return () => clearTimeout(timer)
  }, [copied])
  const router = useRouter()
  const [data, setData] = useState<RegistrationState | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  // A teammate arriving from "Share Invite Link" carries the batch code in the
  // URL. Seeding the field from it is the entire point of that link: nothing
  // read the parameter before, so the recipient landed on an empty box and had
  // to type the code by hand - exactly what the link was meant to save them.
  // Their own membership still wins, because `load` overwrites this below.
  const invitedCode = (useSearchParams().get('code') ?? '').trim().toUpperCase()
  const [code, setCode] = useState(invitedCode)
  const [verified, setVerified] = useState<RegistrationState['batch'] | null>(null)
  const [codeError, setCodeError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await fetchRegistration()
      setData(result)
      if (result.batch) setCode(result.batch.join_code ?? '')
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 401) {
        // Carry the full URL, not just the path: a teammate arriving from
        // the invite link has the batch code in the query string, and a
        // hardcoded path threw it away - so they came back from login to an
        // empty field, which is exactly what the link exists to prevent.
        const here = `${window.location.pathname}${window.location.search}`
        router.replace(`/login?next=${encodeURIComponent(here)}`)
        return
      }
      if (status === 403) { router.replace('/build'); return }
      setError(errorText(err, 'Could not load your registration.'))
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => { load() }, [load])

  const onVerify = async () => {
    setCodeError('')
    setVerified(null)
    if (!code.trim()) { setCodeError('Enter the batch code your department gave you.'); return }
    setBusy(true)
    try {
      const result = await verifyBatchCode(code.trim())
      setVerified(result.batch)
    } catch (err: any) {
      setCodeError(errorText(err, 'That batch code could not be verified.'))
    } finally {
      setBusy(false)
    }
  }

  // Check the invited code as soon as the page knows the student has no batch
  // yet, so an arrival from the link sees the batch card and a Join button
  // instead of a pre-filled field they still have to act on. The ref guards
  // against React's development double-invoke and against `load` re-running.
  const autoVerified = useRef(false)
  useEffect(() => {
    if (autoVerified.current || busy) return
    if (!invitedCode || !data || data.batch) return
    autoVerified.current = true
    void onVerify()
    // onVerify is stable enough here: it only reads `code`, which was seeded
    // from invitedCode and cannot have changed before the first paint.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, invitedCode, busy])

  const onJoin = async () => {
    setBusy(true)
    try {
      await joinBatch(code.trim())
      setNotice('You have joined the batch. Your seat is confirmed.')
      setVerified(null)
      await load()
    } catch (err: any) {
      setCodeError(errorText(err, 'You could not be added to that batch.'))
    } finally {
      setBusy(false)
    }
  }

  const onRemind = async (memberId: string) => {
    setBusy(true)
    try {
      const result = await resendInvite(memberId)
      setNotice(result.detail)
      await load()
    } catch (err: any) {
      setNotice(errorText(err, 'That reminder could not be recorded.'))
    } finally {
      setBusy(false)
    }
  }

  const copy = async (text: string, done: string) => {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text)
      else {
        const area = document.createElement('textarea')
        area.value = text
        area.style.position = 'fixed'
        area.style.opacity = '0'
        document.body.appendChild(area)
        area.select()
        document.execCommand('copy')
        area.remove()
      }
      setNotice(done)
    } catch {
      setNotice(`Copy failed — the code is ${text}`)
    }
  }

  if (loading && !data) {
    return (
      <div className={cn(CARD, 'flex h-[420px] flex-col items-center justify-center gap-3 text-[#6B7280]')}>
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
        <p className="text-[12.5px]">Loading your registration…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn(CARD, 'flex h-[420px] flex-col items-center justify-center gap-3')}>
        <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
        <p className="text-[12.5px] text-[#6B7280]">{error}</p>
        <button type="button" onClick={load}
          className="flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </button>
      </div>
    )
  }

  if (!data) return null

  const batch = data.batch
  const shown = verified ?? batch
  const reg = data.your_registration
  const next = reg.next_action

  // A student with no college enrolment has nothing to register for.
  if (!data.enrolled) {
    return (
      <div className={cn(CARD, 'mx-auto max-w-[520px] p-8 text-center')}>
        <Users className="mx-auto h-8 w-8 text-[#C7CBDD]" />
        <h1 className="mt-3 text-[17px] font-bold text-[#1B1B3A]">No enrolment on record</h1>
        <p className="mt-1.5 text-[12.5px] leading-snug text-[#6B7280]">
          Your college has not enrolled you for an academic year yet, so there is no batch to join.
          Your department coordinator adds students through the faculty portal.
        </p>
        <Link href="/build"
          className="mt-4 inline-block rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
          Go to the builder
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">Student Team Registration</h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
          Join your assigned batch, confirm your seat and pay your individual share.
        </p>
      </div>

      <section className="px-2 py-3"><Stepper steps={data.steps} /></section>

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[12.5px] text-[#1E40AF]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium">Dismiss</button>
        </div>
      )}

      <div className="grid gap-3 xl:grid-cols-[minmax(0,2.05fr)_minmax(0,1fr)]">
        <div className="space-y-3">
          {/* Join with batch code */}
          <section className={cn(CARD, 'p-4')}>
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
              <div>
                <h2 className="text-[14.5px] font-semibold text-[#1B1B3A]">Join with Batch Code</h2>
                <p className="mt-0.5 text-[11.5px] text-[#6B7280]">
                  Use the batch code provided by your department.
                </p>
                <div className="mt-3 flex gap-2">
                  <input value={code} onChange={(e) => { setCode(e.target.value); setCodeError(''); setVerified(null) }}
                    onKeyDown={(e) => { if (e.key === 'Enter') onVerify() }}
                    placeholder="BB-CSE-4A-014" aria-label="Batch code"
                    className="h-10 min-w-0 flex-1 rounded-lg border border-[#D1D5DB] px-3 text-[13px] uppercase tracking-wide outline-none focus:border-[#2563EB]" />
                  <button type="button" onClick={onVerify} disabled={busy}
                    className="shrink-0 rounded-lg bg-[#2563EB] px-4 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-50">
                    Verify Batch
                  </button>
                </div>

                {codeError ? (
                  <p className="mt-2 flex items-start gap-1.5 text-[11.5px] text-[#DC2626]">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {codeError}
                  </p>
                ) : verified ? (
                  <div className="mt-2">
                    <p className="flex items-center gap-1.5 text-[11.5px] font-medium text-[#15803D]">
                      <CheckCircle2 className="h-4 w-4" /> Batch code verified successfully
                    </p>
                    <button type="button" onClick={onJoin} disabled={busy}
                      className="mt-2 rounded-lg bg-[#16A34A] px-4 py-2 text-[12.5px] font-medium text-white hover:bg-[#15803D] disabled:opacity-50">
                      Join This Batch
                    </button>
                  </div>
                ) : batch ? (
                  <p className="mt-2 flex items-center gap-1.5 text-[11.5px] font-medium text-[#15803D]">
                    <CheckCircle2 className="h-4 w-4" /> Batch code verified successfully
                  </p>
                ) : null}
              </div>

              {shown ? (
                <div className="rounded-xl bg-[#F5F8FF] p-3.5">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#2563EB] text-white">
                      <Users className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="text-[16px] font-bold leading-tight text-[#1B1B3A]">{shown.display_name}</p>
                      <p className="text-[11.5px] text-[#4B5563]">
                        {[shown.department, shown.year, `Section ${shown.section}`, shown.project_type]
                          .filter(Boolean).join('  •  ')}
                      </p>
                    </div>
                  </div>
                  <dl className="mt-3 space-y-1.5">
                    {[
                      [Users, 'Faculty Guide:', shown.guide ?? 'Not assigned'],
                      [Users, 'Team Size:', `${shown.team_size} Students`],
                      [FileText, 'Project Title:', shown.title ?? 'Not added yet'],
                    ].map(([Icon, label, value]) => {
                      const I = Icon as typeof Users
                      return (
                        <div key={label as string} className="flex items-center gap-2 text-[12px]">
                          <I className="h-3.5 w-3.5 shrink-0 text-[#6B7280]" />
                          <dt className="text-[#6B7280]">{label as string}</dt>
                          <dd className="min-w-0 truncate font-medium text-[#1B1B3A]">{value as string}</dd>
                        </div>
                      )
                    })}
                  </dl>
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-xl bg-[#F5F8FF] p-6 text-center text-[12px] text-[#6B7280]">
                  Verify a batch code to see the batch it belongs to.
                </div>
              )}
            </div>

            <p className="mt-3 flex items-start gap-2 rounded-lg bg-[#EFF6FF] px-3 py-2.5 text-[12px] text-[#1E40AF]">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              No faculty registration is required. Every student must sign in and confirm the same batch code.
            </p>
          </section>

          {/* Team confirmation */}
          {batch && (
            <section className={cn(CARD, 'p-4')}>
              <h2 className="text-[14.5px] font-semibold text-[#1B1B3A]">
                Team Confirmation ({data.team_joined} of {data.team_size} joined)
              </h2>
              <ul className="mt-2">
                {data.team.map((row) => (
                  <TeamMemberRow key={row.member_id} row={row} busy={busy} onRemind={onRemind} />
                ))}
              </ul>

              {data.invite && (
                <div className="mt-3 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] p-3">
                  <p className="text-[11px] font-medium text-[#1E3A8A]">
                    Invite your teammates
                  </p>
                  <p className="mt-0.5 text-[11px] text-[#3B5BA5]">
                    Send them this. They sign up, and the code is already filled in.
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <code className="flex-1 truncate rounded border border-[#BFDBFE] bg-white px-2 py-1.5 font-mono text-[11px] text-[#1B1B3A]">
                      {origin}{data.invite.path}
                    </code>
                    <button type="button"
                      onClick={async () => {
                        await copy(
                          `${data.invite!.message}\n${origin}${data.invite!.path}`,
                          'Invite copied.')
                        setCopied(true)
                      }}
                      className="flex items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 py-1.5 text-[12px] font-medium text-white hover:bg-[#1D4ED8]">
                      {copied
                        ? <><Check className="h-3.5 w-3.5" /> Copied</>
                        : <><ClipboardCopy className="h-3.5 w-3.5" /> Copy invite</>}
                    </button>
                  </div>
                  <p className="mt-1.5 text-[10.5px] text-[#3B5BA5]">
                    Or just give them the code: <strong>{data.invite.code}</strong>
                    {' '}— <strong>{batch.batch_code}</strong> works too.
                  </p>
                </div>
              )}

              {data.eligibility_note && (
                <p className="mt-2.5 flex items-center gap-1.5 text-[11px] text-[#6B7280]">
                  <ShieldCheck className="h-3.5 w-3.5 shrink-0" /> {data.eligibility_note}
                </p>
              )}
            </section>
          )}

          {/* Help */}
          <section className={cn(CARD, 'flex flex-wrap items-center gap-3 p-4')}>
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF]">
              <Headphones className="h-5 w-5 text-[#2563EB]" />
            </span>
            <span className="min-w-[220px] flex-1">
              <span className="block text-[13px] font-semibold text-[#1B1B3A]">
                Need help with a wrong batch code or member?
              </span>
              <span className="block text-[11.5px] text-[#6B7280]">
                Our support team is here to help you.
              </span>
            </span>
            <Link href="/student/support"
              className="flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2.5 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8]">
              <Headphones className="h-4 w-4" /> Contact Coordinator
            </Link>
            <Link href="/student/support#guide"
              className="flex items-center gap-2 rounded-lg border border-[#D1D5DB] px-4 py-2.5 text-[12.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
              <BookOpen className="h-4 w-4" /> Registration Guide
            </Link>
          </section>
        </div>

        {/* Your registration */}
        <section className={cn(CARD, 'h-fit p-4')}>
          <h2 className="text-[14.5px] font-semibold text-[#1B1B3A]">Your Registration</h2>

          <div className="mt-2.5 flex items-center justify-between text-[12px]">
            <span className="text-[#6B7280]">Batch status</span>
            <span className="font-medium text-[#1B1B3A]">
              {reg.confirmed} of {reg.total} confirmed
            </span>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-[#E5E7EB]">
              <span className="block h-full rounded-full bg-[#2563EB]" style={{ width: `${reg.percent}%` }} />
            </span>
            <span className="text-[11.5px] font-medium text-[#6B7280]">{reg.percent}%</span>
          </div>

          <div className="mt-3 rounded-xl border border-[#E5E7EB] p-3">
            <div className="flex items-center justify-between text-[12.5px]">
              <span className="flex items-center gap-2 text-[#4B5563]">
                <Users className="h-4 w-4 text-[#6B7280]" /> Project Fee
              </span>
              <span className="font-semibold text-[#1B1B3A]">{rupees(reg.project_fee)}</span>
            </div>
            <div className="mt-2 flex items-center justify-between text-[12.5px]">
              <span className="flex items-center gap-2 text-[#4B5563]">
                <Users className="h-4 w-4 text-[#6B7280]" /> Team Members
              </span>
              <span className="font-semibold text-[#1B1B3A]">{reg.team_members}</span>
            </div>
            <div className="mt-2 flex items-center justify-between border-t border-[#F1F2F8] pt-2 text-[12.5px]">
              <span className="flex items-center gap-2 text-[#4B5563]">
                <Users className="h-4 w-4 text-[#6B7280]" /> Your Individual Share
              </span>
              <span className="text-[15px] font-bold text-[#2563EB]">{rupees(reg.your_share)}</span>
            </div>
            <p className="mt-1.5 flex items-start gap-1.5 text-[10.5px] text-[#6B7280]">
              <Info className="mt-0.5 h-3 w-3 shrink-0" />
              Each student pays separately from their own account.
            </p>
          </div>

          <div className="mt-3">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] font-medium text-[#1B1B3A]">Your Payment Status</span>
              {reg.payment.status && (
                <StatePill ok={reg.payment.status === 'paid'} label="Paid" pendingLabel="Pending" />
              )}
            </div>
            <div className="mt-1 flex items-center justify-between text-[12px]">
              <span className="text-[#4B5563]">{data.student.name} (You)</span>
              <span className="font-medium text-[#1B1B3A]">{rupees(reg.payment.amount)}</span>
            </div>
          </div>

          <ul className="mt-3 space-y-1.5">
            {reg.checklist.map((c) => (
              <li key={c.key} className="flex items-center gap-2 text-[12px]">
                {c.done
                  ? <CheckCircle2 className="h-4 w-4 shrink-0 text-[#16A34A]" />
                  : <Clock className="h-4 w-4 shrink-0 text-[#C7CBDD]" />}
                <span className={c.done ? 'text-[#1B1B3A]' : 'text-[#8A8FA8]'}>{c.label}</span>
              </li>
            ))}
          </ul>

          <button type="button" disabled={!next.enabled}
            onClick={() => next.enabled ? router.push('/student/workspace') : setNotice(next.reason ?? '')}
            title={next.reason ?? undefined}
            className={cn('mt-3 flex w-full items-center justify-center gap-2 rounded-lg py-2.5 text-[12.5px] font-medium',
              next.enabled
                ? 'bg-[#2563EB] text-white hover:bg-[#1D4ED8]'
                : 'cursor-not-allowed bg-[#F3F4F6] text-[#9CA3AF]')}>
            <Users className="h-4 w-4" /> {next.label}
          </button>
          {!next.enabled && next.reason && (
            <p className="mt-1 text-center text-[10.5px] text-[#8A8FA8]">{next.reason}</p>
          )}

          <button type="button"
            onClick={() => downloadReceipt()
              .then(() => setNotice('Receipt downloaded.'))
              .catch((err) => setNotice(errorText(err, 'No receipt is available yet.')))}
            disabled={reg.payment.status !== 'paid'}
            className="mt-2 flex w-full items-center justify-center gap-2 py-1.5 text-[12.5px] font-medium text-[#2563EB] hover:underline disabled:cursor-not-allowed disabled:text-[#9CA3AF] disabled:no-underline">
            <Receipt className="h-4 w-4" /> View Payment Receipt
          </button>

          <p className="mt-3 flex items-start gap-2 rounded-lg bg-[#EFF6FF] px-3 py-2.5 text-[11.5px] leading-snug text-[#1E40AF]">
            <Lock className="mt-0.5 h-4 w-4 shrink-0" />
            Project Setup unlocks after all {reg.total} students register and pay. Your team will
            then enter the project title, base paper and abstract.
          </p>
        </section>
      </div>
    </div>
  )
}

export default function StudentRegistrationPage() {

  return (
    <Suspense
      fallback={
        <div className={cn(CARD, 'flex h-[420px] flex-col items-center justify-center gap-3 text-[#6B7280]')}>
          <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
          <p className="text-[12.5px]">Loading your registration…</p>
        </div>
      }
    >
      <RegistrationScreen />
    </Suspense>
  )
}
