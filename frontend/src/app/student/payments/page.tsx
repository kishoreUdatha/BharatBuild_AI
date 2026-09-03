'use client'

/**
 * Payments - this student's share, their team's, and the trail.
 *
 * The tables are built from the payment rows themselves rather than a separate
 * ledger: there is one share per student, and a transaction is simply a share
 * that has been settled. A second table would eventually disagree with the
 * first about who has paid.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, ArrowUpDown, Banknote, Building2, ChevronLeft, ChevronRight,
  ChevronsLeft, ChevronsRight, CreditCard, Download, FileText, History, Info,
  Loader2, Receipt, RotateCcw, Search, Smartphone,
} from 'lucide-react'
import {
  confirmPayment, downloadReceipt, openPaymentOrder, rupees,
} from '@/lib/student-api'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'

interface TeamRow {
  position: number
  student_id: string
  name: string | null
  roll_number: string | null
  is_me: boolean
  is_lead: boolean
  share: number
  paid: number
  status: string
  paid_at: string | null
  method: string | null
  receipt_number: string | null
  recorded_by: string | null
}

interface Txn {
  id: string
  at: string | null
  type: string
  by: string | null
  by_roll: string | null
  is_mine: boolean
  description: string
  amount: number
  status: string
  mode: string
  receipt_number: string | null
  recorded_by: string | null
  note: string | null
}

interface Overview {
  batch_code: string
  project_fee: number
  team_size: number
  members: number
  your_share: number
  you_paid: number
  your_status: string
  your_receipt: string | null
  paid_at: string | null
  team: TeamRow[]
  totals: {
    fee: number; paid: number; pending: number; completion: number; paid_count: number
  }
  transactions: Txn[]
  last_updated: string | null
  schedule: Instalment[]
  schedule_totals: {
    count: number; amount: number; paid: number; pending: number; overdue: number
  }
}

interface Instalment {
  number: number
  label: string
  description: string
  due: string | null
  amount: number
  status: string
  paid_at: string | null
  mode: string | null
  receipt_number: string | null
  /** Only the earliest unpaid instalment; paying a later one first would
   *  leave the earlier one outstanding. */
  payable: boolean
}

const TONE: Record<string, string> = {
  paid: 'bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]',
  pending: 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]',
  failed: 'bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]',
  refunded: 'bg-[#EEF2FF] text-[#4338CA] border-[#C7D2FE]',
  overdue: 'bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]',
  upcoming: 'bg-[#EFF6FF] text-[#1D4ED8] border-[#BFDBFE]',
}

const fmtDay = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('en-IN',
    { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

const fmtWhen = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }) : '—'

const initials = (name: string | null) =>
  (name ?? '?').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()

type Tab = 'team' | 'mine' | 'all' | 'schedule' | 'receipts'

export default function StudentPayments() {
  const [data, setData] = useState<Overview | null>(null)
  const [failed, setFailed] = useState('')
  const [tab, setTab] = useState<Tab>('team')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [paying, setPaying] = useState(false)

  const load = useCallback(async () => {
    try {
      setData(await apiClient.get<Overview>('/student/payments/overview'))
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'Your payments could not be loaded.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  /**
   * Hand the student to the gateway's own checkout.
   *
   * Card and UPI details are entered on the gateway's page, never in this
   * form, and nothing is marked paid until the server has checked the
   * signature over what comes back.
   */
  const pay = async () => {
    setPaying(true)
    setError('')
    setNotice('')
    try {
      const order = await openPaymentOrder()
      await loadCheckout()
      const Razorpay = (window as any).Razorpay
      if (!Razorpay) throw new Error('checkout unavailable')

      new Razorpay({
        key: order.key_id,
        order_id: order.order_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: 'BharatBuild AI',
        description: order.description,
        prefill: {
          name: order.student_name ?? undefined,
          email: order.student_email ?? undefined,
        },
        handler: async (response: any) => {
          try {
            const result = await confirmPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            })
            setNotice(result.message)
            await load()
          } catch (err: any) {
            // The money may well have left. Say so rather than implying it
            // failed, and point at somebody who can look it up.
            setError(err?.response?.data?.detail
              ?? 'The payment went through but could not be recorded. Show this '
                 + 'to your department with the reference from your bank.')
          } finally { setPaying(false) }
        },
        modal: { ondismiss: () => setPaying(false) },
      }).open()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Payment could not be started.')
      setPaying(false)
    }
  }

  if (failed) {
    return (
      <p className={cn(CARD, 'flex items-center gap-2 px-4 py-10 text-[12.5px] text-[#B91C1C]')}>
        <AlertCircle className="h-4 w-4" /> {failed}
      </p>
    )
  }
  if (!data) {
    return (
      <p className={cn(CARD, 'flex items-center justify-center gap-2 px-4 py-12 text-[12.5px] text-[#6B7280]')}>
        <Loader2 className="h-4 w-4 animate-spin" /> Loading your payments…
      </p>
    )
  }

  const paid = data.your_status === 'paid'
  const mine = data.transactions.filter((t) => t.is_mine)
  const receipts = data.transactions.filter((t) => t.receipt_number)

  // Only the team table earns the side panel, because the donut is about the
  // team's progress. Everywhere else it repeats the KPI row above while
  // squeezing the columns that matter.
  const fullWidth = tab !== 'team'


  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h1 className="text-[20px] font-bold leading-tight text-[#1B1B3A]">Payments</h1>
          <p className="mt-0.5 text-[12px] text-[#6B7280]">
            Your payment status, transactions and what your team still owes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" disabled={!paid}
            onClick={() => downloadReceipt().catch(() => setError('No receipt is available yet.'))}
            title={paid ? 'Download your receipt' : 'Available once your share is paid'}
            className="flex h-9 items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
            <FileText className="h-4 w-4" /> Invoice / Receipt
          </button>
          <button type="button" onClick={() => setTab('all')}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 text-[12px] font-medium text-white hover:bg-[#1D4ED8]">
            <History className="h-4 w-4" /> Payment History
          </button>
        </div>
      </div>

      {/* ---------------------------------------------------------------- kpis */}
      <div className={cn(CARD, 'grid divide-y divide-[#F1F2F8] sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-5 xl:divide-x')}>
        <Kpi label="Total Project Fee" value={rupees(data.project_fee)}
          sub="Total registration fee" tone="text-[#1B1B3A]" bg="bg-[#EEF2FF]" />
        <Kpi label="Your Share" value={rupees(data.your_share)}
          sub={`Per student · ${data.members} members`} tone="text-[#1B1B3A]" bg="bg-[#F0FDF4]" />
        <Kpi label="Amount Paid" value={rupees(data.you_paid)}
          sub="By you" tone="text-[#166534]" bg="bg-[#EFF6FF]" />
        <Kpi label="Amount Pending" value={rupees(data.your_share - data.you_paid)}
          sub="By you" tone="text-[#B45309]" bg="bg-[#FFFBEB]" />
        <Kpi label="Payment Status" value={paid ? 'Paid' : 'Not paid'}
          sub={paid ? fmtWhen(data.paid_at) : 'Payment pending'}
          tone={paid ? 'text-[#166534]' : 'text-[#B91C1C]'} bg="bg-[#FEF2F2]" />
      </div>

      {notice && (
        <p className="rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-3 py-2 text-[12.5px] text-[#166534]">
          {notice}
        </p>
      )}
      {error && (
        <p className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[12.5px] text-[#B91C1C]">
          {error}
        </p>
      )}

      {!paid && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3.5 py-3">
          <p className="flex items-start gap-2 text-[12.5px] text-[#92400E]">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Your share of {rupees(data.your_share)} is outstanding. Pay by card, UPI
              or netbanking on the gateway&rsquo;s own page — your details never reach
              BharatBuild. If you pay your department instead, they will record it here.
            </span>
          </p>
          <button type="button" onClick={pay} disabled={paying}
            className="flex h-9 shrink-0 items-center gap-2 rounded-lg bg-[#2563EB] px-4 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-50">
            {paying ? <Loader2 className="h-4 w-4 animate-spin" />
              : <CreditCard className="h-4 w-4" />}
            Pay {rupees(data.your_share)}
          </button>
        </div>
      )}

      <div className={cn('grid gap-3',
        !fullWidth && 'xl:grid-cols-[minmax(0,1fr)_320px]')}>
        <div className={cn(CARD, 'overflow-hidden')}>
          <div className="flex flex-wrap gap-1 border-b border-[#E5E7EB] px-2">
            {([['team', 'Team Payment Status'], ['mine', `My Transactions (${mine.length})`],
               ['all', `All Transactions (${data.transactions.length})`],
               ['schedule', 'Payment Schedule'],
               ['receipts', `Receipts (${receipts.length})`]] as const).map(([key, label]) => (
              <button key={key} type="button" onClick={() => setTab(key)}
                className={cn('-mb-px border-b-2 px-3 py-2 text-[12px] transition-colors',
                  tab === key
                    ? 'border-[#2563EB] font-semibold text-[#2563EB]'
                    : 'border-transparent text-[#6B7280] hover:text-[#374151]')}>
                {label}
              </button>
            ))}
          </div>

          {tab === 'team' && <TeamTab data={data} />}
          {tab === 'mine' && (
            <TxnTable rows={mine} hideStudent
              title="My Transactions"
              subtitle="Every payment and attempt on your own share."
              empty="Nothing yet. Your own payments and attempts appear here." />
          )}
          {tab === 'all' && (
            <TxnTable rows={data.transactions}
              title="All Transactions"
              subtitle="Every payment across your team, newest first."
              empty="No transactions yet. They appear here as your team pays." />
          )}
          {tab === 'schedule' && (
            <ScheduleTab data={data} onPay={pay} paying={paying} />
          )}
          {tab === 'receipts' && <ReceiptsTab rows={receipts} />}
        </div>

        {!fullWidth && (
        <aside className="space-y-3">
          <section className={cn(CARD, 'p-3.5')}>
            <h2 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">Payment Overview</h2>
            <div className="flex items-center gap-4">
              <Donut paid={data.totals.paid} pending={data.totals.pending} />
              <dl className="flex-1 space-y-2 text-[11.5px]">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#16A34A]" />
                  <dt className="flex-1 text-[#6B7280]">
                    Paid ({data.totals.completion}%)
                  </dt>
                  <dd className="font-semibold text-[#1B1B3A]">{rupees(data.totals.paid)}</dd>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#DC2626]" />
                  <dt className="flex-1 text-[#6B7280]">
                    Pending ({100 - data.totals.completion}%)
                  </dt>
                  <dd className="font-semibold text-[#1B1B3A]">{rupees(data.totals.pending)}</dd>
                </div>
              </dl>
            </div>
          </section>

          <section className={cn(CARD, 'p-3.5')}>
            <h2 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">Payment Details</h2>
            <dl className="space-y-1.5 text-[11.5px]">
              <Line label="Registration fee" value={rupees(data.project_fee)} />
              <Line label={`Your share (of ${data.members})`} value={rupees(data.your_share)} />
              <Line label="Paid" value={rupees(data.you_paid)} tone="text-[#166534]" />
              <Line label="Pending" value={rupees(data.your_share - data.you_paid)}
                tone="text-[#B91C1C]" />
              <div className="flex items-center justify-between border-t border-[#F1F2F8] pt-1.5">
                <dt className="text-[#6B7280]">Status</dt>
                <dd>
                  <span className={cn('rounded border px-1.5 py-0.5 text-[10.5px] font-medium',
                    TONE[data.your_status] ?? TONE.pending)}>
                    {paid ? 'Paid' : 'Not paid'}
                  </span>
                </dd>
              </div>
              {data.your_receipt && (
                <Line label="Receipt" value={data.your_receipt} />
              )}
              <Line label="Last payment" value={fmtWhen(data.last_updated)} />
            </dl>
          </section>

          <p className="rounded-lg bg-[#F9FAFC] px-3 py-2.5 text-[10.5px] leading-relaxed text-[#6B7280]">
            Paying online records itself. A payment handed to your department is
            entered here by them, and shows their name against it — so you can
            always see who took it.
          </p>
        </aside>
        )}
      </div>
    </div>
  )
}

// ------------------------------------------------------------------- the tabs

function TeamTab({ data }: { data: Overview }) {
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left">
          <thead>
            <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
              <th className="w-10 px-3 py-2">#</th>
              <th className="px-3 py-2">Member</th>
              <th className="px-3 py-2">Roll No.</th>
              <th className="px-3 py-2 text-right">Share</th>
              <th className="px-3 py-2 text-right">Paid</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2">Paid on</th>
              <th className="px-3 py-2">Recorded by</th>
            </tr>
          </thead>
          <tbody>
            {data.team.map((row) => (
              <tr key={row.student_id}
                className={cn('border-b border-[#F1F2F8] text-[12px] last:border-0',
                  row.is_me && 'bg-[#F7F9FF]')}>
                <td className="px-3 py-2 text-[#9CA3AF]">{row.position}</td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[10px] font-semibold text-[#4338CA]">
                      {initials(row.name)}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-[#1B1B3A]">
                        {row.name}
                        {row.is_me && <span className="text-[#6B7280]"> (you)</span>}
                      </span>
                      {row.is_lead && (
                        <span className="block text-[10px] text-[#9CA3AF]">Batch leader</span>
                      )}
                    </span>
                  </span>
                </td>
                <td className="px-3 py-2 font-mono text-[11px] text-[#6B7280]">
                  {row.roll_number ?? '—'}
                </td>
                <td className="px-3 py-2 text-right text-[#1B1B3A]">{rupees(row.share)}</td>
                <td className={cn('px-3 py-2 text-right font-medium',
                  row.paid ? 'text-[#166534]' : 'text-[#9CA3AF]')}>
                  {rupees(row.paid)}
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={cn('rounded border px-1.5 py-0.5 text-[10.5px] font-medium capitalize',
                    TONE[row.status] ?? TONE.pending)}>
                    {row.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-[11px] text-[#6B7280]">{fmtWhen(row.paid_at)}</td>
                <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                  {row.recorded_by ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 border-t border-[#E5E7EB] bg-[#F9FAFC] px-3.5 py-3 sm:grid-cols-3 xl:grid-cols-5">
        <Summary label="Members" value={String(data.members)} />
        <Summary label="Total fee" value={rupees(data.totals.fee)} />
        <Summary label="Paid" value={rupees(data.totals.paid)} tone="text-[#166534]" />
        <Summary label="Pending" value={rupees(data.totals.pending)} tone="text-[#B91C1C]" />
        <div>
          <span className="block text-[10.5px] text-[#6B7280]">
            Completion ({data.totals.paid_count} of {data.members})
          </span>
          <span className="mt-1 block h-2 overflow-hidden rounded-full bg-[#E5E7EB]">
            <span className="block h-full rounded-full bg-[#16A34A]"
              style={{ width: `${data.totals.completion}%` }} />
          </span>
          <span className="mt-0.5 block text-[11px] font-semibold text-[#1B1B3A]">
            {data.totals.completion}%
          </span>
        </div>
      </div>
    </>
  )
}

const MODE_ICON: Record<string, typeof Banknote> = {
  upi: Smartphone, card: CreditCard, razorpay: CreditCard,
  netbanking: Building2, transfer: Building2, cash: Banknote,
}

const PAGE_SIZES = [10, 25, 50]

/**
 * The transaction ledger, with the filters over it.
 *
 * Filtering runs in the browser because a team's ledger is a handful of rows -
 * one per member. Paging that on the server would be a round trip to sort five
 * things.
 */
function TxnTable({ rows, empty, title, subtitle, hideStudent }: {
  rows: Txn[]
  empty: string
  title?: string
  subtitle?: string
  /** Every row is the reader's own, so naming them in each one says nothing. */
  hideStudent?: boolean
}) {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('all')
  const [mode, setMode] = useState('all')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [newestFirst, setNewestFirst] = useState(true)
  const [size, setSize] = useState(10)
  const [page, setPage] = useState(1)

  const modes = useMemo(
    () => Array.from(new Set(rows.map((r) => r.mode).filter((m) => m && m !== '-'))),
    [rows])

  // Every control applies as you touch it. An Apply button here would be a
  // second click to do what the first one already asked for.
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const out = rows.filter((r) => {
      if (status !== 'all' && r.status !== status) return false
      if (mode !== 'all' && r.mode !== mode) return false
      if (from && (!r.at || r.at.slice(0, 10) < from)) return false
      if (to && (!r.at || r.at.slice(0, 10) > to)) return false
      if (!needle) return true
      return [r.id, r.description, r.by, r.by_roll, r.recorded_by]
        .some((f) => (f ?? '').toLowerCase().includes(needle))
    })
    return out.sort((a, b) => {
      const x = a.at ?? '', y = b.at ?? ''
      return newestFirst ? y.localeCompare(x) : x.localeCompare(y)
    })
  }, [rows, q, status, mode, from, to, newestFirst])

  // Filtering down to fewer rows than the current page would otherwise strand
  // the reader on an empty page.
  const pages = Math.max(1, Math.ceil(shown.length / size))
  const current = Math.min(page, pages)
  const slice = shown.slice((current - 1) * size, current * size)
  const dirty = Boolean(q || status !== 'all' || mode !== 'all' || from || to)

  const reset = () => {
    setQ(''); setStatus('all'); setMode('all'); setFrom(''); setTo(''); setPage(1)
  }

  const heading = title ? (
    <div className="border-b border-[#F1F2F8] px-3.5 pb-2.5 pt-3">
      <h2 className="text-[13px] font-semibold text-[#1B1B3A]">{title}</h2>
      {subtitle && <p className="text-[11.5px] text-[#6B7280]">{subtitle}</p>}
    </div>
  ) : null

  if (rows.length === 0) {
    return (
      <>
        {heading}
        <div className="px-4 py-12 text-center">
          <Search className="mx-auto h-6 w-6 text-[#D1D5DB]" />
          <p className="mt-2 text-[12.5px] text-[#6B7280]">{empty}</p>
        </div>
      </>
    )
  }

  return (
    <>
      {heading}
      <div className="flex flex-wrap items-end gap-2.5 border-b border-[#E5E7EB] px-3.5 py-3">
        <label className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
          <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }}
            placeholder={hideStudent
              ? 'Search by Txn ID or description'
              : 'Search by Txn ID, description or name'}
            className="h-9 w-full rounded-lg border border-[#D1D5DB] bg-white pl-8 pr-2.5 text-[12px] text-[#1B1B3A] placeholder:text-[#9CA3AF] focus:border-[#2563EB] focus:outline-none" />
        </label>

        <Field label="Status">
          <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}
            className="h-9 w-[130px] rounded-lg border border-[#D1D5DB] bg-white px-2 text-[12px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
            <option value="all">All statuses</option>
            <option value="paid">Paid</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
            <option value="refunded">Refunded</option>
          </select>
        </Field>

        <Field label="Payment mode">
          <select value={mode} onChange={(e) => { setMode(e.target.value); setPage(1) }}
            className="h-9 w-[130px] rounded-lg border border-[#D1D5DB] bg-white px-2 text-[12px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
            <option value="all">All modes</option>
            {modes.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </Field>

        <Field label="From">
          <input type="date" value={from} max={to || undefined}
            onChange={(e) => { setFrom(e.target.value); setPage(1) }}
            className="h-9 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[12px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none" />
        </Field>
        <Field label="To">
          <input type="date" value={to} min={from || undefined}
            onChange={(e) => { setTo(e.target.value); setPage(1) }}
            className="h-9 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[12px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none" />
        </Field>

        <button type="button" onClick={reset} disabled={!dirty}
          className="flex h-9 items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
          <RotateCcw className="h-3.5 w-3.5" /> Reset
        </button>
      </div>

      {shown.length === 0 ? (
        <div className="px-4 py-12 text-center">
          <Search className="mx-auto h-6 w-6 text-[#D1D5DB]" />
          <p className="mt-2 text-[12.5px] text-[#6B7280]">
            No transaction matches those filters.
          </p>
          <button type="button" onClick={reset}
            className="mt-2 text-[12px] font-medium text-[#2563EB] hover:underline">
            Clear them
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className={cn('w-full border-collapse text-left',
            hideStudent ? 'min-w-[820px]' : 'min-w-[940px]')}>
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
                <th className="px-3 py-2">Txn ID</th>
                <th className="px-3 py-2">
                  <button type="button" onClick={() => setNewestFirst((v) => !v)}
                    title={newestFirst ? 'Newest first' : 'Oldest first'}
                    className="flex items-center gap-1 hover:text-[#2563EB]">
                    Date &amp; time <ArrowUpDown className="h-3 w-3" />
                  </button>
                </th>
                {!hideStudent && <th className="px-3 py-2">Student</th>}
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2">Mode</th>
                <th className="px-3 py-2 text-center">Status</th>
                <th className="px-3 py-2">Receipt</th>
                <th className="px-3 py-2">Recorded by</th>
              </tr>
            </thead>
            <tbody>
              {slice.map((t) => {
                const Icon = MODE_ICON[(t.mode || '').toLowerCase()] ?? Banknote
                const credit = t.amount >= 0
                return (
                  <tr key={t.id}
                    className={cn('border-b border-[#F1F2F8] text-[12px] last:border-0',
                      t.is_mine && !hideStudent && 'bg-[#F7F9FF]')}>
                    <td className="px-3 py-2 font-mono text-[10.5px] text-[#2563EB]">{t.id}</td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">{fmtWhen(t.at)}</td>
                    {!hideStudent && (
                      <td className="px-3 py-2">
                        <span className="block text-[#1B1B3A]">
                          {t.by}{t.is_mine && <span className="text-[#6B7280]"> (you)</span>}
                        </span>
                        <span className="block font-mono text-[10px] text-[#9CA3AF]">
                          {t.by_roll}
                        </span>
                      </td>
                    )}
                    <td className="px-3 py-2 text-[#1B1B3A]">
                      {t.description}
                      {t.note && (
                        <span className="block text-[10px] text-[#B45309]">{t.note}</span>
                      )}
                    </td>
                    <td className={cn('px-3 py-2 text-right font-medium tabular-nums',
                      credit ? 'text-[#166534]' : 'text-[#B91C1C]')}>
                      {credit ? '+' : '−'} {rupees(Math.abs(t.amount))}
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1.5 text-[11px] capitalize text-[#6B7280]">
                        <Icon className="h-3.5 w-3.5 text-[#9CA3AF]" /> {t.mode}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={cn('rounded border px-1.5 py-0.5 text-[10.5px] font-medium capitalize',
                        TONE[t.status] ?? TONE.pending)}>
                        {t.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {t.receipt_number && t.is_mine ? (
                        <button type="button" onClick={() => downloadReceipt()}
                          className="flex items-center gap-1 text-[11px] font-medium text-[#2563EB] hover:underline">
                          <Download className="h-3.5 w-3.5" /> Download
                        </button>
                      ) : (
                        // A receipt belongs to the student who paid; a teammate
                        // sees that one exists, not what is on it.
                        <span className="text-[11px] text-[#9CA3AF]">
                          {t.receipt_number ? 'Issued' : '—'}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                      {t.recorded_by ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E5E7EB] px-3.5 py-2.5">
        <p className="text-[11px] text-[#6B7280]">
          {shown.length === 0
            ? 'No transactions'
            : `Showing ${(current - 1) * size + 1} to ${Math.min(current * size, shown.length)} of ${shown.length}`}
          {dirty && rows.length !== shown.length ? ` (filtered from ${rows.length})` : ''}
        </p>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-[#6B7280]">
            Rows per page
            <select value={size} onChange={(e) => { setSize(Number(e.target.value)); setPage(1) }}
              className="h-7 rounded border border-[#D1D5DB] bg-white px-1.5 text-[11px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <div className="flex items-center gap-0.5">
            <Pager label="First" disabled={current === 1} onClick={() => setPage(1)}>
              <ChevronsLeft className="h-3.5 w-3.5" />
            </Pager>
            <Pager label="Previous" disabled={current === 1} onClick={() => setPage(current - 1)}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </Pager>
            <span className="px-2 text-[11px] text-[#6B7280]">
              Page {current} of {pages}
            </span>
            <Pager label="Next" disabled={current === pages} onClick={() => setPage(current + 1)}>
              <ChevronRight className="h-3.5 w-3.5" />
            </Pager>
            <Pager label="Last" disabled={current === pages} onClick={() => setPage(pages)}>
              <ChevronsRight className="h-3.5 w-3.5" />
            </Pager>
          </div>
        </div>
      </div>

      <p className="flex items-start gap-2 border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2563EB]" />
        <span>
          A payment handed to your department is recorded here by them, and their
          name shows under Recorded by. If something looks wrong, take the Txn ID
          to your department.
        </span>
      </p>
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10.5px] text-[#6B7280]">{label}</span>
      {children}
    </label>
  )
}

function Pager({ label, disabled, onClick, children }: {
  label: string; disabled: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      title={label}
      className="flex h-7 w-7 items-center justify-center rounded border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-30">
      {children}
    </button>
  )
}

/**
 * The instalment plan.
 *
 * One row today, because the registration fee is collected as a single sum.
 * Every column the plan would need is already wired, so a college that defines
 * real instalments gets them rendered without a change here.
 */
function ScheduleTab({ data, onPay, paying }: {
  data: Overview; onPay: () => void; paying: boolean
}) {
  const t = data.schedule_totals
  return (
    <>
      <div className="border-b border-[#F1F2F8] px-3.5 pb-2.5 pt-3">
        <h2 className="text-[13px] font-semibold text-[#1B1B3A]">Payment Schedule</h2>
        <p className="text-[11.5px] text-[#6B7280]">Your payment plan and due dates.</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] border-collapse text-left">
          <thead>
            <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
              <th className="w-10 px-3 py-2">#</th>
              <th className="px-3 py-2">Instalment</th>
              <th className="px-3 py-2">Description</th>
              <th className="px-3 py-2">Due date</th>
              <th className="px-3 py-2 text-right">Amount (your share)</th>
              <th className="px-3 py-2 text-center">Status</th>
              <th className="px-3 py-2">Paid on</th>
              <th className="px-3 py-2">Payment mode</th>
              <th className="px-3 py-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {data.schedule.map((row) => (
              <tr key={row.number}
                className="border-b border-[#F1F2F8] text-[12px] last:border-0">
                <td className="px-3 py-2 text-[#9CA3AF]">{row.number}</td>
                <td className="px-3 py-2 text-[#1B1B3A]">{row.label}</td>
                <td className="px-3 py-2 text-[#1B1B3A]">{row.description}</td>
                <td className={cn('px-3 py-2 text-[11px]',
                  row.status === 'overdue' ? 'font-medium text-[#B91C1C]' : 'text-[#6B7280]')}>
                  {fmtDay(row.due)}
                </td>
                <td className="px-3 py-2 text-right font-medium tabular-nums text-[#1B1B3A]">
                  {rupees(row.amount)}
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={cn('rounded border px-1.5 py-0.5 text-[10.5px] font-medium capitalize',
                    TONE[row.status] ?? TONE.pending)}>
                    {row.status}
                  </span>
                </td>
                <td className="px-3 py-2 text-[11px] text-[#6B7280]">{fmtWhen(row.paid_at)}</td>
                <td className="px-3 py-2 text-[11px] capitalize text-[#6B7280]">
                  {row.mode ?? '—'}
                </td>
                <td className="px-3 py-2 text-right">
                  {row.payable ? (
                    <button type="button" onClick={onPay} disabled={paying}
                      className="inline-flex h-7 items-center gap-1.5 rounded-lg border border-[#2563EB] px-2.5 text-[11.5px] font-medium text-[#2563EB] hover:bg-[#EFF6FF] disabled:opacity-50">
                      {paying ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        : <CreditCard className="h-3.5 w-3.5" />}
                      Pay now
                    </button>
                  ) : (
                    <span className="text-[11px] text-[#9CA3AF]">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 border-t border-[#E5E7EB] bg-[#F9FAFC] px-3.5 py-3 sm:grid-cols-3 xl:grid-cols-5">
        <Summary label="Total instalments" value={String(t.count)} />
        <Summary label="Total amount" value={rupees(t.amount)} />
        <Summary label="Paid amount" value={rupees(t.paid)} tone="text-[#166534]" />
        <Summary label="Pending amount" value={rupees(t.pending)} tone="text-[#B45309]" />
        <Summary label="Overdue amount" value={rupees(t.overdue)}
          tone={t.overdue ? 'text-[#B91C1C]' : 'text-[#1B1B3A]'} />
      </div>

      <p className="flex items-start gap-2 border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2563EB]" />
        <span>
          The registration fee is collected in one instalment. A payment handed
          to your department is recorded here by them; for anything that looks
          wrong, contact your department.
        </span>
      </p>
    </>
  )
}

/**
 * Receipts.
 *
 * A receipt is a transaction that has one - so this reads the same list rather
 * than a separate store that could disagree about what was issued.
 */
function ReceiptsTab({ rows }: { rows: Txn[] }) {
  const [mode, setMode] = useState('all')
  const [size, setSize] = useState(10)
  const [page, setPage] = useState(1)

  const modes = useMemo(
    () => Array.from(new Set(rows.map((r) => r.mode).filter((m) => m && m !== '-'))),
    [rows])
  const shown = useMemo(
    () => rows.filter((r) => mode === 'all' || r.mode === mode),
    [rows, mode])

  const pages = Math.max(1, Math.ceil(shown.length / size))
  const current = Math.min(page, pages)
  const slice = shown.slice((current - 1) * size, current * size)

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-2 border-b border-[#F1F2F8] px-3.5 pb-2.5 pt-3">
        <div>
          <h2 className="text-[13px] font-semibold text-[#1B1B3A]">Receipts</h2>
          <p className="text-[11.5px] text-[#6B7280]">All your payment receipts in one place.</p>
        </div>
        {modes.length > 1 && (
          <Field label="Filter by mode">
            <select value={mode} onChange={(e) => { setMode(e.target.value); setPage(1) }}
              className="h-9 w-[140px] rounded-lg border border-[#D1D5DB] bg-white px-2 text-[12px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
              <option value="all">All modes</option>
              {modes.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
        )}
      </div>

      {slice.length === 0 ? (
        <div className="px-4 py-12 text-center">
          <Receipt className="mx-auto h-6 w-6 text-[#D1D5DB]" />
          <p className="mt-2 text-[12.5px] text-[#6B7280]">
            No receipts yet. One is issued for every payment recorded.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] border-collapse text-left">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
                <th className="w-10 px-3 py-2">#</th>
                <th className="px-3 py-2">Receipt ID</th>
                <th className="px-3 py-2">Transaction ID</th>
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2">Payment mode</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Receipt</th>
                <th className="px-3 py-2">Recorded by</th>
              </tr>
            </thead>
            <tbody>
              {slice.map((r, i) => {
                const Icon = MODE_ICON[(r.mode || '').toLowerCase()] ?? Banknote
                const credit = r.amount >= 0
                return (
                  <tr key={r.id}
                    className="border-b border-[#F1F2F8] text-[12px] last:border-0">
                    <td className="px-3 py-2 text-[#9CA3AF]">
                      {(current - 1) * size + i + 1}
                    </td>
                    <td className="px-3 py-2 font-mono text-[10.5px] text-[#1B1B3A]">
                      {r.receipt_number}
                    </td>
                    <td className="px-3 py-2 font-mono text-[10.5px] text-[#2563EB]">{r.id}</td>
                    <td className="px-3 py-2 text-[#1B1B3A]">{r.description}</td>
                    <td className={cn('px-3 py-2 text-right font-medium tabular-nums',
                      credit ? 'text-[#166534]' : 'text-[#B91C1C]')}>
                      {credit ? '+' : '−'} {rupees(Math.abs(r.amount))}
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1.5 text-[11px] capitalize text-[#6B7280]">
                        <Icon className="h-3.5 w-3.5 text-[#9CA3AF]" /> {r.mode}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">{fmtWhen(r.at)}</td>
                    <td className="px-3 py-2">
                      {r.is_mine ? (
                        <button type="button" onClick={() => downloadReceipt()}
                          className="flex items-center gap-1 text-[11px] font-medium text-[#2563EB] hover:underline">
                          <Download className="h-3.5 w-3.5" /> Download
                        </button>
                      ) : (
                        // Somebody else's receipt carries their payment details.
                        <span className="text-[11px] text-[#9CA3AF]">Issued</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                      {r.recorded_by ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E5E7EB] px-3.5 py-2.5">
        <p className="text-[11px] text-[#6B7280]">
          {shown.length === 0
            ? 'No receipts'
            : `Showing ${(current - 1) * size + 1} to ${Math.min(current * size, shown.length)} of ${shown.length} receipts`}
        </p>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-[#6B7280]">
            Rows per page
            <select value={size} onChange={(e) => { setSize(Number(e.target.value)); setPage(1) }}
              className="h-7 rounded border border-[#D1D5DB] bg-white px-1.5 text-[11px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <div className="flex items-center gap-0.5">
            <Pager label="First" disabled={current === 1} onClick={() => setPage(1)}>
              <ChevronsLeft className="h-3.5 w-3.5" />
            </Pager>
            <Pager label="Previous" disabled={current === 1} onClick={() => setPage(current - 1)}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </Pager>
            <span className="px-2 text-[11px] text-[#6B7280]">
              Page {current} of {pages}
            </span>
            <Pager label="Next" disabled={current === pages} onClick={() => setPage(current + 1)}>
              <ChevronRight className="h-3.5 w-3.5" />
            </Pager>
            <Pager label="Last" disabled={current === pages} onClick={() => setPage(pages)}>
              <ChevronsRight className="h-3.5 w-3.5" />
            </Pager>
          </div>
        </div>
      </div>

      <p className="flex items-start gap-2 border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2563EB]" />
        <span>
          A receipt is issued for every successful payment and refund. For
          anything that looks wrong, take the receipt ID to your department.
        </span>
      </p>
    </>
  )
}

// ---------------------------------------------------------------- small parts

function Kpi({ label, value, sub, tone, bg }: {
  label: string; value: string; sub: string; tone: string; bg: string
}) {
  return (
    <div className="flex items-center gap-3 px-3.5 py-3">
      <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-full', bg)}>
        <Receipt className="h-4 w-4 text-[#4B5563]" />
      </span>
      <span className="min-w-0">
        <span className="block text-[10.5px] text-[#6B7280]">{label}</span>
        <span className={cn('block text-[16px] font-bold leading-tight', tone)}>{value}</span>
        <span className="block truncate text-[10px] text-[#9CA3AF]">{sub}</span>
      </span>
    </div>
  )
}

function Summary({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <span className="block text-[10.5px] text-[#6B7280]">{label}</span>
      <span className={cn('block text-[14px] font-bold', tone ?? 'text-[#1B1B3A]')}>{value}</span>
    </div>
  )
}

function Line({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-[#6B7280]">{label}</dt>
      <dd className={cn('font-medium', tone ?? 'text-[#1B1B3A]')}>{value}</dd>
    </div>
  )
}

/** Paid against pending. Both figures are printed, so colour is never alone. */
function Donut({ paid, pending }: { paid: number; pending: number }) {
  const total = paid + pending
  const share = total ? paid / total : 0
  const R = 34
  const C = 2 * Math.PI * R
  return (
    <svg viewBox="0 0 88 88" className="h-[88px] w-[88px] shrink-0" role="img"
      aria-label={`${paid} paid of ${total}`}>
      <circle cx="44" cy="44" r={R} fill="none" stroke="#FEE2E2" strokeWidth="12" />
      <circle cx="44" cy="44" r={R} fill="none" stroke="#16A34A" strokeWidth="12"
        strokeDasharray={`${share * C} ${C}`} transform="rotate(-90 44 44)"
        strokeLinecap={share > 0 && share < 1 ? 'round' : 'butt'} />
      <text x="44" y="48" textAnchor="middle"
        className="fill-[#1B1B3A] text-[13px] font-bold">
        {Math.round(share * 100)}%
      </text>
    </svg>
  )
}

/**
 * Load the gateway's checkout script once, on demand.
 *
 * Not in the page head: most visits here are a student checking whether their
 * team has paid, and they should not fetch a payment SDK to read a table.
 */
function loadCheckout(): Promise<void> {
  const SRC = 'https://checkout.razorpay.com/v1/checkout.js'
  if ((window as any).Razorpay) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SRC}"]`)
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('checkout failed to load')))
      return
    }
    const tag = document.createElement('script')
    tag.src = SRC
    tag.onload = () => resolve()
    tag.onerror = () => reject(new Error('checkout failed to load'))
    document.body.appendChild(tag)
  })
}
