'use client'

/**
 * Staff - the college's own guides and trainers.
 *
 * This belongs to the college, not to the platform operator. A vendor staffing
 * a customer's departments is both wrong and unworkable: they do not know who
 * joined this term or who left, and every change would be a support request.
 *
 * No password is chosen here by anyone. The account is created unusable and its
 * owner is emailed a link to set one, so a credential never passes through a
 * third person's hands.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, Check, Loader2, Mail, Search, Send, UserPlus, X,
} from 'lucide-react'
import { PageShell } from '@/components/faculty/PageShell'
import apiClient from '@/lib/api-client'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'

interface Options {
  roles: { key: string; label: string }[]
  colleges: { id: string; name: string; code: string }[]
  can_choose_college: boolean
}

interface StaffRow {
  id: string
  email: string
  full_name: string | null
  role: string
  department: string | null
  is_active: boolean
  last_login: string | null
}

const ROLE_TONE: Record<string, string> = {
  faculty: 'border-[#DDD6FE] bg-[#F5F3FF] text-[#6D28D9]',
  trainer: 'border-[#DBEAFE] bg-[#EFF6FF] text-[#1D4ED8]',
  admin: 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]',
}

const fmtWhen = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('en-IN',
    { day: '2-digit', month: 'short', year: 'numeric' }) : null

export default function FacultyStaffPage() {
  const [options, setOptions] = useState<Options | null>(null)
  const [rows, setRows] = useState<StaffRow[]>([])
  const [failed, setFailed] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [adding, setAdding] = useState(false)
  const [busy, setBusy] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      // One call per role: the users endpoint takes a single role and pages
      // with `page_size`.
      const [opts, faculty, trainers] = await Promise.all([
        apiClient.get<Options>('/admin/staff/options'),
        apiClient.get<any>('/admin/users', { params: { role: 'faculty', page_size: 100 } })
          .catch(() => ({ items: [] })),
        apiClient.get<any>('/admin/users', { params: { role: 'trainer', page_size: 100 } })
          .catch(() => ({ items: [] })),
      ])
      setOptions(opts)
      const unwrap = (r: any) => (r?.items ?? r?.users ?? r?.rows ?? []) as any[]
      setRows([...unwrap(faculty), ...unwrap(trainers)].map((u) => ({
        id: String(u.id),
        email: u.email,
        full_name: u.full_name ?? null,
        role: String(u.role),
        department: u.department ?? null,
        is_active: u.is_active !== false,
        last_login: u.last_login ?? null,
      })))
      setFailed('')
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'Staff could not be loaded.')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const shown = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return rows
    return rows.filter((r) => [r.email, r.full_name, r.department]
      .some((f) => (f ?? '').toLowerCase().includes(needle)))
  }, [rows, search])

  const resend = async (row: StaffRow) => {
    setBusy(row.id)
    setNotice('')
    try {
      const result = await apiClient.post<{ message: string }>(
        `/admin/staff/${row.id}/resend`, {})
      setNotice(result.message)
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'That could not be sent.')
    } finally { setBusy('') }
  }

  return (
    <PageShell title="Staff"
      subtitle="Your guides and trainers, and the invitations that let them in"
      actions={
        <button type="button" onClick={() => setAdding(true)}
          className="flex h-9 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8]">
          <UserPlus className="h-4 w-4" /> Add staff
        </button>
      }>
      {failed && (
        <p className="flex items-center gap-2 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[12px] text-[#B91C1C]">
          <AlertCircle className="h-4 w-4" /> {failed}
        </p>
      )}
      {notice && (
        <p className="rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-3 py-2 text-[12px] text-[#166534]">
          {notice}
        </p>
      )}

      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="border-b border-[#EEF0F7] p-3">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, email or department"
              className="h-9 w-full rounded-lg border border-[#D1D5DB] bg-white pl-8 pr-3 text-[12px] text-[#1B1B3A] placeholder:text-[#9CA3AF] focus:border-[#2563EB] focus:outline-none" />
          </label>
        </div>

        {loading ? (
          <p className="flex items-center justify-center gap-2 py-12 text-[12.5px] text-[#6B7280]">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </p>
        ) : shown.length === 0 ? (
          <p className="py-12 text-center text-[12.5px] text-[#6B7280]">
            {rows.length === 0
              ? 'No guides or trainers yet. Add the first one — they will be emailed a link to set a password.'
              : 'Nobody matches that.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2 text-center">Role</th>
                  <th className="px-3 py-2">Last signed in</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.id}
                    className={cn('border-b border-[#F1F2F8] text-[12px] last:border-0',
                      r.is_active ? '' : 'opacity-55')}>
                    <td className="px-3 py-2 text-[#1B1B3A]">
                      {r.full_name ?? '—'}
                      {r.department && (
                        <span className="block text-[10px] text-[#9CA3AF]">{r.department}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">{r.email}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={cn('rounded border px-1.5 py-0.5 text-[10.5px] font-medium capitalize',
                        ROLE_TONE[r.role] ?? ROLE_TONE.faculty)}>
                        {r.role}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[11px]">
                      {fmtWhen(r.last_login)
                        // Never signed in usually means a missed invite, which
                        // is what Resend is for.
                        ?? <span className="text-[#B45309]">Never</span>}
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex justify-end">
                        <button type="button" onClick={() => resend(r)}
                          disabled={busy === r.id}
                          title="Email the set-a-password link again"
                          className="flex h-7 items-center gap-1.5 rounded border border-[#E5E7EB] bg-white px-2 text-[11px] text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
                          {busy === r.id
                            ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            : <Send className="h-3.5 w-3.5" />}
                          Resend invite
                        </button>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
          Nobody chooses a password here. The account is created unusable and its
          owner sets their own from an emailed link, so a credential never passes
          through anyone else&rsquo;s hands.
        </p>
      </div>

      {adding && options && (
        <StaffDialog options={options}
          onClose={() => setAdding(false)}
          onSaved={async (message) => {
            setAdding(false)
            setNotice(message)
            setFailed('')
            await load()
          }} />
      )}
    </PageShell>
  )
}

function StaffDialog({ options, onClose, onSaved }: {
  options: Options
  onClose: () => void
  onSaved: (message: string) => void | Promise<void>
}) {
  const [form, setForm] = useState({
    email: '', full_name: '',
    role: options.roles[0]?.key ?? 'faculty',
    department: '', phone: '',
  })
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])

  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }))

  const submit = async () => {
    setBusy(true)
    setProblem('')
    try {
      // No college is sent: the server reads it from this admin's own record,
      // so one college cannot put staff into another's tenant.
      const result = await apiClient.post<{ message: string }>('/admin/staff', form)
      await onSaved(result.message)
    } catch (err: any) {
      setProblem(err?.response?.data?.detail ?? 'That account could not be created.')
      setBusy(false)
    }
  }

  const ready = form.email.includes('@') && form.full_name.trim().length > 1
  const input = 'h-9 rounded-lg border border-[#D1D5DB] bg-white px-3 text-[12.5px] text-[#1B1B3A] placeholder:text-[#9CA3AF] focus:border-[#2563EB] focus:outline-none'

  return (
    <div role="dialog" aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[calc(100vh-2rem)] w-full max-w-[540px] flex-col rounded-xl bg-white shadow-xl">
        <div className="flex shrink-0 items-center justify-between border-b border-[#E5E7EB] px-4 py-3">
          <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Add staff</h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className="flex h-7 w-7 items-center justify-center rounded text-[#6B7280] hover:bg-[#F3F4F6]">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto px-4 py-3">
          {problem && (
            <p className="flex items-start gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11.5px] text-[#B91C1C]">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {problem}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-[#6B7280]">Full name *</span>
              <input value={form.full_name} className={input}
                placeholder="Dr Anitha Rao"
                onChange={(e) => set({ full_name: e.target.value })} />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-[#6B7280]">Email *</span>
              <input value={form.email} type="email" className={input}
                placeholder="anitha@sgit.ac.in"
                onChange={(e) => set({ email: e.target.value })} />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-[#6B7280]">Role *</span>
              <select value={form.role} className={input}
                onChange={(e) => set({ role: e.target.value })}>
                {options.roles.map((r) => (
                  <option key={r.key} value={r.key}>{r.label}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-[#6B7280]">Department</span>
              <input value={form.department} className={input} placeholder="CSE"
                onChange={(e) => set({ department: e.target.value })} />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[11px] text-[#6B7280]">Phone</span>
            <input value={form.phone} className={input}
              onChange={(e) => set({ phone: e.target.value })} />
          </label>

          <p className="flex items-start gap-2 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[11px] text-[#1E3A8A]">
            <Mail className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              No password is set here. They are emailed a link to choose their
              own, valid for seven days — Resend invite sends it again.
            </span>
          </p>
        </div>

        <div className="flex shrink-0 items-center justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
          <button type="button" onClick={onClose} disabled={busy}
            className="h-9 rounded-lg border border-[#D1D5DB] bg-white px-3.5 text-[12.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={!ready || busy}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3.5 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            Create and invite
          </button>
        </div>
      </div>
    </div>
  )
}
