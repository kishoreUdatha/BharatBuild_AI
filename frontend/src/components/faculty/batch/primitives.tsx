'use client'

import { useEffect, useRef, useState, type ComponentType, type ReactNode } from 'react'
// `Check` is aliased: the icon name collides with the Check type from the API module.
import { AlertCircle, Check as CheckIcon, CheckCircle2, Copy, MoreHorizontal } from 'lucide-react'
import type { Check, TabKpi, TimelineStep } from '@/lib/faculty-batch-api'
import { cn } from '@/lib/utils'

export const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
export const CELL = 'px-2.5 py-2'

export function Card({ title, right, className, id, children }: {
  title?: string; right?: ReactNode; className?: string; id?: string; children: ReactNode
}) {
  return (
    <section id={id} className={cn(CARD, 'p-4', className)}>
      {(title || right) && (
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-[13.5px] font-semibold text-[#1B1B3A]">{title}</h2>}
          {right}
        </div>
      )}
      {children}
    </section>
  )
}

export function KpiRow({ kpis, tones }: { kpis: TabKpi[]; tones?: Record<string, string> }) {
  return (
    <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-5">
      {kpis.map((k) => (
        <div key={k.id} className={cn(CARD, 'p-3')}>
          <p className={cn('text-[18px] font-bold leading-none', tones?.[k.id] ?? 'text-[#1B1B3A]')}>{k.value}</p>
          <p className="mt-1 text-[11px] leading-tight text-[#5A5F7A]">{k.label}</p>
        </div>
      ))}
    </section>
  )
}

/** A pass/fail list with its own progress footer - used by five of the tabs. */
export function Checklist({ title, checks, passed, total, footer }: {
  title: string; checks: Check[]; passed: number; total: number; footer?: string
}) {
  return (
    <Card title={title}>
      <ul className="space-y-1">
        {checks.map((c) => (
          <li key={c.key} className="flex items-center gap-2 text-[11.5px]">
            {c.passed
              ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
              : <AlertCircle className="h-3.5 w-3.5 shrink-0 text-[#D97706]" />}
            <span className="flex-1 text-[#3A3F58]">{c.label}</span>
            <span className={cn('whitespace-nowrap text-[10.5px]', c.passed ? 'text-[#16A34A]' : 'text-[#D97706]')}>
              {c.detail ?? (c.passed ? 'Passed' : 'Pending')}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-2.5 border-t border-[#EEF0F7] pt-2">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-[#3A3F58]">{passed} / {total} checks passed</span>
          <span className="font-semibold text-[#1B1B3A]">{Math.round((passed / (total || 1)) * 100)}%</span>
        </div>
        <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-[#EEF0F7]">
          <span className="block h-full rounded-full bg-[#16A34A]"
            style={{ width: `${(passed / (total || 1)) * 100}%` }} />
        </span>
        {footer && <p className="mt-1.5 text-[10.5px] text-[#8A8FA8]">{footer}</p>}
      </div>
    </Card>
  )
}

export function Timeline({ steps }: { steps: TimelineStep[] }) {
  return (
    <ol className="flex flex-wrap gap-x-2 gap-y-3">
      {steps.map((s, i) => (
        <li key={`${s.step}-${i}`} className="flex min-w-[132px] flex-1 flex-col items-center text-center">
          <span className="flex w-full items-center">
            <span className={cn('h-[2px] flex-1', i === 0 ? 'bg-transparent' : s.done ? 'bg-[#16A34A]' : 'bg-[#DDE0EE]')} />
            <span className={cn('flex h-5 w-5 shrink-0 items-center justify-center rounded-full',
              s.done ? 'bg-[#16A34A] text-white' : 'border-2 border-[#C7CBDD] bg-white')}>
              {s.done && <CheckCircle2 className="h-3 w-3" />}
            </span>
            <span className={cn('h-[2px] flex-1', i === steps.length - 1 ? 'bg-transparent' : s.done ? 'bg-[#16A34A]' : 'bg-[#DDE0EE]')} />
          </span>
          <span className="mt-1.5 text-[10.5px] font-medium leading-tight text-[#1B1B3A]">{s.step}</span>
          {s.occurred_at && (
            <span className="text-[9.5px] text-[#8A8FA8]">
              {new Date(s.occurred_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
              {' '}
              {new Date(s.occurred_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          {s.actor && <span className="text-[9.5px] text-[#8A8FA8]">{s.actor}</span>}
        </li>
      ))}
    </ol>
  )
}

const TONE_CLASS: Record<string, string> = {
  green: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  amber: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  red: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  indigo: 'border-[#C7D2FE] bg-[#EEF2FF] text-[#4F46E5]',
  slate: 'border-[#E2E5F0] bg-[#F7F8FC] text-[#6B7280]',
}

export function Tag({ tone = 'slate', children }: { tone?: keyof typeof TONE_CLASS; children: ReactNode }) {
  return (
    <span className={cn('inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px]', TONE_CLASS[tone])}>
      {children}
    </span>
  )
}

/** Maps a backend status string onto a tag tone. */
export function statusTone(key: string): keyof typeof TONE_CLASS {
  if (['verified', 'approved', 'complete', 'success', 'passed'].some((k) => key.includes(k))) return 'green'
  if (['awaiting', 'pending', 'changes', 'warning', 'in_review', 'in_progress'].some((k) => key.includes(k))) return 'amber'
  if (['missing', 'rejected', 'critical', 'failed'].some((k) => key.includes(k))) return 'red'
  if (['submitted', 'resubmitted', 'uploaded', 'info'].some((k) => key.includes(k))) return 'indigo'
  return 'slate'
}

export function Field({ label, value, className }: { label: string; value: ReactNode; className?: string }) {
  return (
    <div className={className}>
      <p className="text-[10.5px] text-[#8A8FA8]">{label}</p>
      <div className="text-[11.5px] leading-snug text-[#1B1B3A]">{value ?? '—'}</div>
    </div>
  )
}

export function Bar({ value, tone = 'bg-[#4F46E5]' }: { value: number; tone?: string }) {
  return (
    <span className="block h-1.5 overflow-hidden rounded-full bg-[#EEF0F7]">
      <span className={cn('block h-full rounded-full', tone)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </span>
  )
}

export const fmtBytes = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : bytes > 0 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : '—'

export const fmtDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export const fmtDateTime = (iso: string | null | undefined) =>
  iso
    ? new Date(iso).toLocaleString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    : '—'

export function Initials({ name, size = 'h-7 w-7' }: { name: string | null; size?: string }) {
  const initials = (name ?? '?').split(' ').map((p) => p[0]).slice(-2).join('').toUpperCase()
  return (
    <span className={cn('flex shrink-0 items-center justify-center rounded-full bg-[#DDE3F7] text-[9.5px] font-semibold text-[#2C2A6B]', size)}>
      {initials}
    </span>
  )
}


// ------------------------------------------------------------------ controls

const BTN_TONE = {
  plain: 'border border-[#DDE0EE] bg-white text-[#3A3F58] hover:bg-[#F7F8FC]',
  primary: 'bg-[#4F46E5] text-white hover:bg-[#4338CA]',
  ghost: 'border border-[#C7BDF5] bg-white text-[#4F46E5] hover:bg-[#F5F3FF]',
  green: 'border border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D] hover:bg-[#DCFCE7]',
  amber: 'border border-[#FDE68A] bg-[#FFFBEB] text-[#B45309] hover:bg-[#FEF3C7]',
  red: 'border border-[#FECACA] bg-[#FEF2F2] text-[#DC2626] hover:bg-[#FEE2E2]',
}

/**
 * One button style for the whole detail screen. Every tab footer, card header
 * and row action goes through this so a change to spacing or focus ring lands
 * everywhere at once instead of in twenty near-identical class strings.
 */
export function Btn({ icon: Icon, tone = 'plain', size = 'sm', full, disabled, onClick, title, className, children }: {
  icon?: ComponentType<{ className?: string }>
  tone?: keyof typeof BTN_TONE
  size?: 'xs' | 'sm' | 'md'
  full?: boolean
  disabled?: boolean
  onClick?: () => void
  title?: string
  className?: string
  children: ReactNode
}) {
  const pad = size === 'xs' ? 'px-2 py-0.5 text-[10px] gap-1'
    : size === 'md' ? 'px-4 py-2 text-[12px] gap-2'
      : 'px-3 py-1.5 text-[11px] gap-1.5'
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={title}
      className={cn('inline-flex items-center justify-center whitespace-nowrap rounded-lg font-medium transition-colors disabled:opacity-40',
        pad, BTN_TONE[tone], full && 'w-full', className)}>
      {Icon && <Icon className={size === 'xs' ? 'h-3 w-3' : 'h-3.5 w-3.5'} />}
      {children}
    </button>
  )
}

/**
 * Copy-to-clipboard with its own confirmation. Falls back to a textarea +
 * execCommand because clipboard.writeText is unavailable over plain http,
 * which is exactly how this runs in local development.
 */
export function CopyButton({ text, label = 'Copy', size = 'sm', icon = true }: {
  text: string | null | undefined; label?: string; size?: 'xs' | 'sm'; icon?: boolean
}) {
  const [done, setDone] = useState(false)

  const legacyCopy = (value: string) => {
    const area = document.createElement('textarea')
    area.value = value
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    const ok = document.execCommand('copy')
    area.remove()
    return ok
  }

  const copy = async () => {
    const value = text ?? ''
    if (!value) return
    // The Clipboard API is missing over plain http and *rejects* without a user
    // gesture, so a failure has to fall through to the legacy path rather than
    // being swallowed - otherwise the button silently does nothing.
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value)
        setDone(true)
      } else {
        setDone(legacyCopy(value))
      }
    } catch {
      setDone(legacyCopy(value))
    }
    setTimeout(() => setDone(false), 1600)
  }

  return (
    <Btn size={size} onClick={copy} disabled={!text}
      icon={icon ? (done ? CheckIcon : Copy) : undefined}>
      {done ? 'Copied' : label}
    </Btn>
  )
}

/** The `…` overflow menu used by row-level secondary actions. */
export function Menu({ items, align = 'right' }: {
  items: { label: string; onClick: () => void; tone?: 'default' | 'danger' }[]
  align?: 'left' | 'right'
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  return (
    <div ref={ref} className="relative inline-block">
      <button type="button" aria-label="More actions" aria-expanded={open} onClick={() => setOpen((v) => !v)}
        className="flex h-6 w-6 items-center justify-center rounded-md border border-[#DDE0EE] text-[#5A5F7A] hover:bg-[#F7F8FC]">
        <MoreHorizontal className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div className={cn('absolute z-20 mt-1 min-w-[168px] overflow-hidden rounded-lg border border-[#DDE0EE] bg-white py-1 shadow-lg',
          align === 'right' ? 'right-0' : 'left-0')}>
          {items.map((item) => (
            <button key={item.label} type="button"
              onClick={() => { setOpen(false); item.onClick() }}
              className={cn('block w-full px-3 py-1.5 text-left text-[11px] hover:bg-[#F7F8FC]',
                item.tone === 'danger' ? 'text-[#DC2626]' : 'text-[#3A3F58]')}>
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/** A compact vertical log - the per-tab history strips read from the audit log. */
export function MiniLog({ entries, empty = 'No activity recorded yet.' }: {
  entries: { label: string; actor?: string | null; occurred_at?: string | null; severity?: string }[]
  empty?: string
}) {
  if (entries.length === 0) {
    return <p className="py-3 text-center text-[11px] text-[#8A8FA8]">{empty}</p>
  }
  return (
    <ol className="space-y-2">
      {entries.map((e, i) => (
        <li key={`${e.label}-${i}`} className="flex gap-2">
          <span className="flex flex-col items-center">
            <span className={cn('mt-1 h-2 w-2 shrink-0 rounded-full',
              e.severity === 'critical' ? 'bg-[#DC2626]'
                : e.severity === 'warning' ? 'bg-[#D97706]'
                  : e.severity === 'success' ? 'bg-[#16A34A]' : 'bg-[#4F46E5]')} />
            {i < entries.length - 1 && <span className="mt-1 w-px flex-1 bg-[#E8E9F2]" />}
          </span>
          <span className="min-w-0 flex-1 pb-0.5">
            <span className="block text-[11px] leading-snug text-[#1B1B3A]">{e.label}</span>
            <span className="block text-[9.5px] text-[#8A8FA8]">
              {[e.actor, e.occurred_at ? fmtDateTime(e.occurred_at) : null].filter(Boolean).join(' · ') || '—'}
            </span>
          </span>
        </li>
      ))}
    </ol>
  )
}

/** Renders hours as the "1d 4h" / "3h 20m" form the mocks use. */
export const fmtHours = (hours: number | null | undefined) => {
  if (hours == null) return '—'
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${Math.round(hours % 24)}h`
  if (hours >= 1) return `${Math.floor(hours)}h ${Math.round((hours % 1) * 60)}m`
  return `${Math.round(hours * 60)}m`
}
