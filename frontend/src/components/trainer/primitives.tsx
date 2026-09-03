'use client'

import type { ReactNode } from 'react'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'

export function PageHeader({ title, subtitle, right }: {
  title: string; subtitle: string; right?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">{title}</h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">{subtitle}</p>
      </div>
      {right}
    </div>
  )
}

export interface Kpi { id: string; value: string; label: string }

/** Tones are semantic: what needs attention should read at a glance. */
const KPI_TONE: Record<string, string> = {
  overdue: 'bg-[#FEF2F2] text-[#DC2626]',
  outstanding: 'bg-[#FFF7ED] text-[#EA580C]',
  pending: 'bg-[#FFF7ED] text-[#EA580C]',
  required: 'bg-[#FEF2F2] text-[#DC2626]',
  stories: 'bg-[#F5F3FF] text-[#7C3AED]',
  verified: 'bg-[#F0FDF4] text-[#16A34A]',
  completed: 'bg-[#F0FDF4] text-[#16A34A]',
}

export function KpiRow({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {kpis.map((k) => (
        <div key={k.id} className={cn(CARD, 'p-3.5')}>
          <p className={cn('inline-block rounded-md px-1.5 py-0.5 text-[19px] font-bold leading-none',
            KPI_TONE[k.id] ?? 'bg-[#EFF6FF] text-[#2563EB]')}>{k.value}</p>
          <p className="mt-1.5 text-[11px] leading-tight text-[#6B7280]">{k.label}</p>
        </div>
      ))}
    </div>
  )
}

const CHIP_TONE: Record<string, string> = {
  green: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  amber: 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]',
  red: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  blue: 'border-[#DBEAFE] bg-[#EFF6FF] text-[#1D4ED8]',
  violet: 'border-[#DDD6FE] bg-[#F5F3FF] text-[#6D28D9]',
  grey: 'border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280]',
}

export function Chip({ tone = 'grey', children }: {
  tone?: keyof typeof CHIP_TONE; children: ReactNode
}) {
  return (
    <span className={cn('inline-block whitespace-nowrap rounded-md border px-2 py-0.5 text-[10.5px] font-medium',
      CHIP_TONE[tone])}>{children}</span>
  )
}

export function Bar({ value, tone = 'bg-[#2563EB]' }: { value: number; tone?: string }) {
  return (
    <span className="block h-1.5 overflow-hidden rounded-full bg-[#EEF0F7]">
      <span className={cn('block h-full rounded-full', tone)}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </span>
  )
}

export function Loading({ label }: { label: string }) {
  return (
    <div className={cn(CARD, 'flex h-[320px] flex-col items-center justify-center gap-3 text-[#6B7280]')}>
      <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
      <p className="text-[12.5px]">{label}</p>
    </div>
  )
}

export function Failed({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className={cn(CARD, 'flex h-[320px] flex-col items-center justify-center gap-3')}>
      <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
      <p className="text-[12.5px] text-[#6B7280]">{message}</p>
      <button type="button" onClick={onRetry}
        className="rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">Retry</button>
    </div>
  )
}

export function Empty({ message }: { message: string }) {
  return (
    <div className={cn(CARD, 'px-6 py-14 text-center text-[12.5px] text-[#9CA3AF]')}>{message}</div>
  )
}

export function FilterTabs({ options, value, onChange }: {
  options: { key: string; label: string }[]
  value: string
  onChange: (key: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button key={o.key} type="button" onClick={() => onChange(o.key)}
          className={cn('rounded-lg border px-3 py-1.5 text-[11.5px] font-medium transition-colors',
            value === o.key
              ? 'border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]'
              : 'border-[#E5E7EB] bg-white text-[#6B7280] hover:bg-[#F9FAFB]')}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export const fmtDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
