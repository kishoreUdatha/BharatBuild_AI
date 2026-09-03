'use client'

/**
 * Colleges - onboarding a new institution onto the platform.
 *
 * This is the first step of an onboarding and, until now, the only one with no
 * screen: the sole college in the system was inserted by a seeder. Everything
 * after it - departments, rosters, batches - already has one.
 *
 * The email domains matter more than they look. They are what decides which
 * tenant a signup lands in, so a wrong domain here puts one college's students
 * inside another's rosters and exports.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, Building2, Check, Globe, Loader2, Mail, Pencil, Plus, Power,
  Search, UserPlus, Users, X,
} from 'lucide-react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import apiClient from '@/lib/api-client'

interface College {
  id: string
  name: string
  code: string
  email_domains: string[]
  default_project_fee: number
  /** The kinds of project this college runs, e.g. Major and Minor. */
  project_types: string[]
  /** A fee per type. A minor project rarely costs what a major one does. */
  project_fees: Record<string, number>
  city: string | null
  state: string | null
  email: string | null
  phone: string | null
  website: string | null
  github_org: string | null
  github_installation_id: string | null
  /** Both halves recorded here, and the app's credentials on the server. */
  github_ready: boolean
  is_active: boolean
  is_self_serve: boolean
  accounts: number
  created_at: string | null
  editable: boolean
}

interface Payload {
  rows: College[]
  totals: {
    colleges: number; active: number; accounts: number; without_domains: number
  }
  available_project_types: string[]
}

const blank = {
  name: '', code: '', email_domains: [] as string[],
  default_project_fee: 15000,
  // Most colleges run these two, so they start ticked - the common case
  // should not need clicking.
  project_types: ['Major Project', 'Minor Project'] as string[],
  project_fees: {} as Record<string, number>,
  city: '', state: '',
  email: '', phone: '', website: '', is_active: true,
  github_org: '', github_installation_id: '',
}

const rupees = (n: number) => `₹${n.toLocaleString('en-IN')}`

export default function AdminCollegesPage() {
  const { theme } = useAdminTheme()
  const isDark = theme === 'dark'

  const [data, setData] = useState<Payload | null>(null)
  const [failed, setFailed] = useState('')
  const [notice, setNotice] = useState('')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<College | 'new' | null>(null)
  // Handing over a college: the one account the platform operator creates.
  // Everything after this belongs to the college's own administrator.
  const [handover, setHandover] = useState<College | null>(null)
  const [busy, setBusy] = useState('')

  const load = useCallback(async () => {
    try {
      setData(await apiClient.get<Payload>('/admin/colleges'))
      setFailed('')
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'Colleges could not be loaded.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return (data?.rows ?? []).filter((c) => !needle
      || c.name.toLowerCase().includes(needle)
      || c.code.toLowerCase().includes(needle)
      || c.email_domains.some((d) => d.includes(needle)))
  }, [data, search])

  const toggle = async (college: College) => {
    setBusy(college.id)
    setNotice('')
    try {
      await apiClient.post(
        `/admin/colleges/${college.id}/active?active=${!college.is_active}`, {})
      setNotice(`${college.name} is now ${college.is_active ? 'inactive' : 'active'}.`)
      await load()
    } catch (err: any) {
      setFailed(err?.response?.data?.detail ?? 'That could not be changed.')
    } finally { setBusy('') }
  }

  const card = isDark ? 'border-white/10 bg-[#141414]' : 'border-gray-200 bg-white'
  const ink = isDark ? 'text-gray-100' : 'text-gray-900'
  const muted = isDark ? 'text-gray-400' : 'text-gray-500'

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-50'}`}>
      <AdminHeader title="Colleges"
        subtitle="Institutions on the platform, and the domains that place students in them"
        onRefresh={load} />

      <div className="space-y-4 p-6">
        {failed && (
          <p className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
            <AlertCircle className="h-4 w-4" /> {failed}
          </p>
        )}
        {notice && (
          <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400">
            {notice}
          </p>
        )}

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Tile card={card} ink={ink} muted={muted} icon={Building2}
            label="Colleges" value={String(data?.totals.colleges ?? 0)} />
          <Tile card={card} ink={ink} muted={muted} icon={Power}
            label="Active" value={String(data?.totals.active ?? 0)} />
          <Tile card={card} ink={ink} muted={muted} icon={Users}
            label="Accounts" value={String(data?.totals.accounts ?? 0)} />
          <Tile card={card} ink={ink} muted={muted} icon={Globe}
            label="Without domains"
            value={String(data?.totals.without_domains ?? 0)}
            // A college with no domain cannot take self-service signups at
            // all, so this is the number that stalls an onboarding.
            warn={(data?.totals.without_domains ?? 0) > 0} />
        </div>

        <div className={`rounded-xl border ${card}`}>
          <div className={`flex flex-wrap items-center gap-3 border-b p-3 ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
            <label className="relative min-w-[220px] flex-1">
              <Search className={`pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 ${muted}`} />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name, code or domain"
                className={`h-9 w-full rounded-lg border pl-9 pr-3 text-sm outline-none ${
                  isDark ? 'border-white/10 bg-[#0a0a0a] text-gray-100' : 'border-gray-200 bg-white text-gray-900'}`} />
            </label>
            <button type="button" onClick={() => setEditing('new')}
              className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3 text-sm font-medium text-white hover:bg-blue-700">
              <Plus className="h-4 w-4" /> Onboard a college
            </button>
          </div>

          {!data && failed ? (
            // A refused request left this spinning forever, which reads as a
            // slow page rather than a locked door. The banner above says what
            // went wrong; this says the list is not coming.
            <p className={`py-12 text-center text-sm ${muted}`}>
              The list could not be loaded.
              <button type="button" onClick={load}
                className="ml-1 font-medium text-blue-400 hover:underline">
                Try again
              </button>
            </p>
          ) : !data ? (
            <p className={`flex items-center justify-center gap-2 py-12 text-sm ${muted}`}>
              <Loader2 className="h-4 w-4 animate-spin" /> Loading…
            </p>
          ) : rows.length === 0 ? (
            <p className={`py-12 text-center text-sm ${muted}`}>
              No college matches that.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead>
                  <tr className={`border-b text-xs ${isDark ? 'border-white/10 text-gray-400' : 'border-gray-200 text-gray-500'}`}>
                    <th className="px-4 py-2 font-medium">College</th>
                    <th className="px-4 py-2 font-medium">Code</th>
                    <th className="px-4 py-2 font-medium">Email domains</th>
                    <th className="px-4 py-2 text-right font-medium">Default fee</th>
                    <th className="px-4 py-2 text-right font-medium">Accounts</th>
                    <th className="px-4 py-2 text-center font-medium">Status</th>
                    <th className="px-4 py-2 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((c) => (
                    <tr key={c.id}
                      className={`border-b ${isDark ? 'border-white/5' : 'border-gray-100'} ${
                        c.is_active ? '' : 'opacity-55'}`}>
                      <td className={`px-4 py-2.5 ${ink}`}>
                        {c.name}
                        {c.is_self_serve && (
                          <span className={`ml-2 rounded border px-1.5 py-0.5 text-[10px] ${
                            isDark ? 'border-white/15 text-gray-400' : 'border-gray-300 text-gray-500'}`}>
                            unmatched signups
                          </span>
                        )}
                        {c.city && <span className={`block text-xs ${muted}`}>{c.city}</span>}
                      </td>
                      <td className={`px-4 py-2.5 font-mono text-xs ${muted}`}>{c.code}</td>
                      <td className="px-4 py-2.5">
                        {c.email_domains.length === 0 ? (
                          <span className={`text-xs ${c.is_self_serve ? muted : 'text-amber-500'}`}>
                            {c.is_self_serve ? '—' : 'none — cannot self-serve'}
                          </span>
                        ) : (
                          <span className="flex flex-wrap gap-1">
                            {c.email_domains.map((d) => (
                              <span key={d}
                                className="rounded border border-blue-500/30 bg-blue-500/10 px-1.5 py-0.5 font-mono text-[11px] text-blue-400">
                                @{d}
                              </span>
                            ))}
                          </span>
                        )}
                      </td>
                      <td className={`px-4 py-2.5 text-right tabular-nums ${ink}`}>
                        {c.is_self_serve ? '—' : (
                          // Every type this college runs and what each costs,
                          // because one number cannot describe a college
                          // charging differently for major and minor.
                          <span className="inline-flex flex-col items-end">
                            {(c.project_types ?? []).length === 0
                              ? rupees(c.default_project_fee)
                              : c.project_types.map((t) => (
                                <span key={t} className="whitespace-nowrap">
                                  <span className={`mr-1.5 text-[11px] ${muted}`}>
                                    {t.replace(' Project', '')}
                                  </span>
                                  {rupees(c.project_fees?.[t] ?? c.default_project_fee)}
                                </span>
                              ))}
                          </span>
                        )}
                      </td>
                      <td className={`px-4 py-2.5 text-right tabular-nums ${muted}`}>
                        {c.accounts}
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`rounded border px-1.5 py-0.5 text-[11px] ${
                          c.is_active
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                            : 'border-gray-500/30 bg-gray-500/10 text-gray-400'}`}>
                          {c.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className="flex items-center justify-end gap-1">
                          <button type="button" disabled={!c.editable}
                            onClick={() => setEditing(c)}
                            title={c.editable ? 'Edit' : 'The self-serve tenant cannot be edited'}
                            className={`flex h-7 w-7 items-center justify-center rounded border disabled:opacity-30 ${
                              isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button type="button" disabled={!c.editable}
                            onClick={() => setHandover(c)}
                            title={c.editable
                              ? 'Create this college\u2019s administrator'
                              : 'The self-serve tenant has no administrator'}
                            className={`flex h-7 w-7 items-center justify-center rounded border disabled:opacity-30 ${
                              isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                            <UserPlus className="h-3.5 w-3.5" />
                          </button>
                          <button type="button" disabled={!c.editable || busy === c.id}
                            onClick={() => toggle(c)}
                            title={c.editable
                              ? (c.is_active ? 'Deactivate' : 'Activate')
                              : 'The self-serve tenant cannot be switched off'}
                            className={`flex h-7 w-7 items-center justify-center rounded border disabled:opacity-30 ${
                              c.is_active ? 'text-amber-500' : 'text-emerald-500'} ${
                              isDark ? 'border-white/10 hover:bg-white/5' : 'border-gray-200 hover:bg-gray-50'}`}>
                            {busy === c.id
                              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              : <Power className="h-3.5 w-3.5" />}
                          </button>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className={`border-t px-4 py-2.5 text-xs ${muted} ${isDark ? 'border-white/10' : 'border-gray-200'}`}>
            A college is deactivated, never deleted — accounts, batches and
            attendance point at it, and removing one would orphan its history.
            An inactive college stops taking new signups and keeps everything
            it has.
          </p>
        </div>
      </div>

      {handover && (
        <HandoverDialog isDark={isDark} college={handover}
          onClose={() => setHandover(null)}
          onSaved={async (message) => {
            setHandover(null)
            setNotice(message)
            setFailed('')
            await load()
          }} />
      )}

      {editing && (
        <CollegeDialog
          isDark={isDark}
          college={editing === 'new' ? null : editing}
          projectTypes={data?.available_project_types ?? []}
          onClose={() => setEditing(null)}
          onSaved={async (message) => {
            setEditing(null)
            setNotice(message)
            setFailed('')
            await load()
          }} />
      )}
    </div>
  )
}

function Tile({ card, ink, muted, icon: Icon, label, value, warn }: {
  card: string; ink: string; muted: string
  icon: typeof Building2; label: string; value: string; warn?: boolean
}) {
  return (
    <div className={`flex items-center gap-3 rounded-xl border p-3 ${card}`}>
      <span className={`flex h-9 w-9 items-center justify-center rounded-full ${
        warn ? 'bg-amber-500/15 text-amber-500' : 'bg-blue-500/15 text-blue-400'}`}>
        <Icon className="h-4 w-4" />
      </span>
      <span>
        <span className={`block text-xs ${muted}`}>{label}</span>
        <span className={`block text-lg font-bold ${warn ? 'text-amber-500' : ink}`}>
          {value}
        </span>
      </span>
    </div>
  )
}

/**
 * Hand a college its administrator.
 *
 * The only account the platform operator creates. From here the college adds
 * its own guides and trainers - a vendor staffing a customer's departments
 * would not know who joined this term or who left, and every change would
 * arrive as a support request.
 */
function HandoverDialog({ isDark, college, onClose, onSaved }: {
  isDark: boolean
  college: College
  onClose: () => void
  onSaved: (message: string) => void | Promise<void>
}) {
  const [form, setForm] = useState({ full_name: '', email: '', phone: '' })
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])

  const submit = async () => {
    setBusy(true)
    setProblem('')
    try {
      const result = await apiClient.post<{ message: string }>('/admin/staff', {
        ...form, role: 'admin', college_id: college.id,
      })
      await onSaved(result.message)
    } catch (err: any) {
      setProblem(err?.response?.data?.detail ?? 'That account could not be created.')
      setBusy(false)
    }
  }

  const field = isDark
    ? 'border-white/10 bg-[#0a0a0a] text-gray-100 placeholder:text-gray-600'
    : 'border-gray-200 bg-white text-gray-900 placeholder:text-gray-400'
  const label = isDark ? 'text-gray-400' : 'text-gray-500'
  const ready = form.email.includes('@') && form.full_name.trim().length > 1
  const domain = college.email_domains?.[0]

  return (
    <div role="dialog" aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className={`flex w-full max-w-[520px] flex-col rounded-xl border ${
        isDark ? 'border-white/10 bg-[#141414]' : 'border-gray-200 bg-white'}`}>
        <div className={`flex items-center justify-between border-b px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <h2 className={`text-sm font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
            Administrator for {college.name}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className={`flex h-7 w-7 items-center justify-center rounded ${
              isDark ? 'text-gray-400 hover:bg-white/5' : 'text-gray-500 hover:bg-gray-100'}`}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-2.5 px-4 py-3">
          {problem && (
            <p className="flex items-start gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {problem}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Full name *</span>
              <input value={form.full_name} placeholder="Prof Ravi Kumar"
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Email *</span>
              <input value={form.email} type="email"
                placeholder={domain ? `ravi@${domain}` : 'ravi@college.ac.in'}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className={`text-xs ${label}`}>Phone</span>
            <input value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
          </label>

          <p className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${
            isDark ? 'border-blue-500/30 bg-blue-500/10 text-blue-300' : 'border-blue-200 bg-blue-50 text-blue-800'}`}>
            <Mail className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              They administer {college.name} only — not the platform — and add
              their own guides and trainers from there. No password is set here;
              they are emailed a link to choose one.
            </span>
          </p>
        </div>

        <div className={`flex items-center justify-end gap-2 border-t px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <button type="button" onClick={onClose} disabled={busy}
            className={`h-9 rounded-lg border px-3.5 text-sm ${
              isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={!ready || busy}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            Create and invite
          </button>
        </div>
      </div>
    </div>
  )
}

/** Create or edit. The same fields either way, so the same form. */
function CollegeDialog({ isDark, college, projectTypes, onClose, onSaved }: {
  isDark: boolean
  college: College | null
  projectTypes: string[]
  onClose: () => void
  onSaved: (message: string) => void | Promise<void>
}) {
  const [form, setForm] = useState(() => college ? {
    name: college.name, code: college.code,
    email_domains: college.email_domains,
    default_project_fee: college.default_project_fee,
    project_types: college.project_types ?? [],
    project_fees: college.project_fees ?? {},
    city: college.city ?? '', state: college.state ?? '',
    email: college.email ?? '', phone: college.phone ?? '',
    website: college.website ?? '', is_active: college.is_active,
    github_org: college.github_org ?? '',
    github_installation_id: college.github_installation_id ?? '',
  } : { ...blank })
  const [domain, setDomain] = useState('')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])

  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }))

  const addDomain = () => {
    const value = domain.trim().toLowerCase().replace(/^@/, '')
    if (!value) return
    if (!form.email_domains.includes(value)) {
      set({ email_domains: [...form.email_domains, value] })
    }
    setDomain('')
  }

  const submit = async () => {
    setBusy(true)
    setProblem('')
    // A domain typed but not added is the easiest thing to lose on submit.
    const domains = domain.trim()
      ? [...form.email_domains, domain.trim().toLowerCase().replace(/^@/, '')]
      : form.email_domains
    try {
      const body = { ...form, email_domains: domains }
      if (college) await apiClient.put(`/admin/colleges/${college.id}`, body)
      else await apiClient.post('/admin/colleges', body)
      await onSaved(`${form.name} ${college ? 'updated' : 'onboarded'}.`)
    } catch (err: any) {
      setProblem(err?.response?.data?.detail ?? 'That could not be saved.')
      setBusy(false)
    }
  }

  const field = isDark
    ? 'border-white/10 bg-[#0a0a0a] text-gray-100 placeholder:text-gray-600'
    : 'border-gray-200 bg-white text-gray-900 placeholder:text-gray-400'
  const label = isDark ? 'text-gray-400' : 'text-gray-500'
  const ready = form.name.trim().length > 1 && form.code.trim().length > 1

  return (
    <div role="dialog" aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      {/*
        A column with its own height cap: the header and footer hold their
        place and only the fields scroll. Letting the overlay scroll instead
        pushed the title off the top and the buttons off the bottom, so the
        one control you need - Save - was the hardest to reach.
      */}
      <div className={`flex max-h-[calc(100vh-2rem)] w-full max-w-[680px] flex-col rounded-xl border ${
        isDark ? 'border-white/10 bg-[#141414]' : 'border-gray-200 bg-white'}`}>
        <div className={`flex shrink-0 items-center justify-between border-b px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <h2 className={`text-sm font-semibold ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
            {college ? `Edit ${college.name}` : 'Onboard a college'}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className={`flex h-7 w-7 items-center justify-center rounded ${
              isDark ? 'text-gray-400 hover:bg-white/5' : 'text-gray-500 hover:bg-gray-100'}`}>
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 space-y-2.5 overflow-y-auto px-4 py-3">
          {problem && (
            <p className="flex items-start gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {problem}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Name *</span>
              <input value={form.name} onChange={(e) => set({ name: e.target.value })}
                placeholder="Sri Guru Institute of Technology"
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Code *</span>
              <input value={form.code}
                onChange={(e) => set({ code: e.target.value.toUpperCase() })}
                placeholder="SGIT"
                className={`h-9 rounded-lg border px-3 font-mono text-sm outline-none ${field}`} />
            </label>
          </div>

          <div className="flex flex-col gap-1">
            <span className={`text-xs ${label}`}>
              Email domains
              <span className="ml-1.5 text-[11px] opacity-80">
                — signing up from one of these joins this college, so add only
                domains it owns
              </span>
            </span>
            <div className="mt-1 flex gap-2">
              <input value={domain} onChange={(e) => setDomain(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { e.preventDefault(); addDomain() }
                }}
                placeholder="sgit.ac.in"
                className={`h-9 flex-1 rounded-lg border px-3 font-mono text-sm outline-none ${field}`} />
              <button type="button" onClick={addDomain}
                className={`h-9 rounded-lg border px-3 text-sm ${
                  isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                Add
              </button>
            </div>
            {form.email_domains.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {form.email_domains.map((d) => (
                  <span key={d}
                    className="flex items-center gap-1 rounded border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 font-mono text-[11px] text-blue-400">
                    @{d}
                    <button type="button" aria-label={`Remove ${d}`}
                      onClick={() => set({
                        email_domains: form.email_domains.filter((x) => x !== d),
                      })}>
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            {form.email_domains.length === 0 && !domain.trim() && (
              <p className="mt-0.5 text-[11px] text-amber-500">
                No domain — students join by roster or batch code instead.
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <span className={`text-xs ${label}`}>
              Projects this college runs
              <span className="ml-1.5 text-[11px] opacity-80">
                — batches inherit the fee for their type
              </span>
            </span>
            {/* Two up: four full-width rows made the dialog taller than the
                screen for a choice that is really four checkboxes. */}
            <div className="mt-1 grid gap-x-4 gap-y-1 sm:grid-cols-2">
              {projectTypes.map((type) => {
                const on = form.project_types.includes(type)
                return (
                  <div key={type}
                    className={`flex items-center gap-2 rounded-lg px-1.5 py-1 ${
                      on ? (isDark ? 'bg-white/5' : 'bg-gray-50') : ''}`}>
                    <label className="flex min-w-0 flex-1 items-center gap-2">
                      <input type="checkbox" checked={on}
                        onChange={(e) => set({
                          project_types: e.target.checked
                            ? [...form.project_types, type]
                            : form.project_types.filter((t) => t !== type),
                        })} />
                      <span className={`truncate text-[13px] ${
                        on
                          ? (isDark ? 'text-gray-200' : 'text-gray-800')
                          : label}`}>
                        {type}
                      </span>
                    </label>
                    <span className="flex shrink-0 items-center gap-1">
                      <span className={`text-xs ${label}`}>₹</span>
                      <input type="number" min={0} disabled={!on}
                        // Blank means "use the default", which is different
                        // from zero - a free project.
                        value={form.project_fees[type] ?? ''}
                        placeholder={String(form.default_project_fee)}
                        onChange={(e) => {
                          const next = { ...form.project_fees }
                          if (e.target.value === '') delete next[type]
                          else next[type] = Number(e.target.value)
                          set({ project_fees: next })
                        }}
                        className={`h-7 w-24 rounded-lg border px-2 text-[13px] outline-none disabled:opacity-30 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none ${field}`} />
                    </span>
                  </div>
                )
              })}
            </div>
            {form.project_types.length === 0 && (
              <p className="mt-0.5 text-[11px] text-amber-500">
                None selected — any type may be created, at the default fee.
              </p>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Default fee (₹)</span>
              <input type="number" min={0} value={form.default_project_fee}
                onChange={(e) => set({ default_project_fee: Number(e.target.value) })}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>City</span>
              <input value={form.city} onChange={(e) => set({ city: e.target.value })}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>State</span>
              <input value={form.state} onChange={(e) => set({ state: e.target.value })}
                className={`h-9 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Contact email</span>
              <input value={form.email} onChange={(e) => set({ email: e.target.value })}
                className={`h-8 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Phone</span>
              <input value={form.phone} onChange={(e) => set({ phone: e.target.value })}
                className={`h-8 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>Website</span>
              <input value={form.website} onChange={(e) => set({ website: e.target.value })}
                className={`h-8 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
          </div>

          {/* Where this college's batches get their repositories. Both halves
              or neither - one on its own creates nothing, so the note says so
              rather than letting it look configured. */}
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>GitHub organisation</span>
              <input value={form.github_org} placeholder="sgit-projects"
                onChange={(e) => set({ github_org: e.target.value })}
                className={`h-8 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={`text-xs ${label}`}>App installation ID</span>
              <input value={form.github_installation_id} placeholder="12345678"
                onChange={(e) => set({ github_installation_id: e.target.value })}
                className={`h-8 rounded-lg border px-3 text-sm outline-none ${field}`} />
            </label>
          </div>
          <p className={`text-[11px] ${label}`}>
            With both, a batch opening its workspace gets a private repository
            created in this organisation, its team added, and the push webhook
            set. Without them the team connects one by hand — nothing else
            changes. The installation ID is in the URL after you install the
            BharatBuild app on the organisation.
          </p>

          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.is_active}
              onChange={(e) => set({ is_active: e.target.checked })} />
            <span className={`text-xs ${label}`}>
              Active — an inactive college takes no new signups
            </span>
          </label>
        </div>

        <div className={`flex shrink-0 items-center justify-end gap-2 border-t px-4 py-3 ${
          isDark ? 'border-white/10' : 'border-gray-200'}`}>
          <button type="button" onClick={onClose} disabled={busy}
            className={`h-9 rounded-lg border px-3.5 text-sm ${
              isDark ? 'border-white/10 text-gray-300 hover:bg-white/5' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={!ready || busy}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            {college ? 'Save changes' : 'Onboard college'}
          </button>
        </div>
      </div>
    </div>
  )
}
