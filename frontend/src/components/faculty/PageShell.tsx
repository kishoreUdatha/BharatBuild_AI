'use client'

import { useCallback, useEffect, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertTriangle, ArrowLeft, Loader2, RefreshCw } from 'lucide-react'
import { errorMessage } from '@/lib/faculty-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'

/**
 * Shared chrome for every faculty sub-page: title row, back link, and the
 * load / error / empty states, so each screen only has to render its rows.
 */
export function PageShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href="/faculty"
            className="mb-1 inline-flex items-center gap-1 text-[11px] text-[#5A5F7A] hover:text-[#4F46E5]"
          >
            <ArrowLeft className="h-3 w-3" /> Dashboard
          </Link>
          <h1 className="text-[19px] font-bold leading-tight text-[#1B1B3A]">{title}</h1>
          {subtitle && <p className="mt-0.5 text-[12px] text-[#5A5F7A]">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  )
}

/** Load a list endpoint and render one of loading / error / empty / rows. */
export function useFacultyResource<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const router = useRouter()
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const run = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await load())
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 401) {
        router.push('/login?next=/faculty')
        return
      }
      setError(
        status === 403
          ? 'This area is for faculty accounts. Ask an admin to update your role.'
          : errorMessage(err, 'Could not load this page. Please try again.')
      )
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    run()
  }, [run])

  return { data, loading, error, reload: run }
}

export function ResourceState({
  loading,
  error,
  empty,
  emptyMessage = 'Nothing to show yet.',
  onRetry,
  children,
}: {
  loading: boolean
  error: string
  empty: boolean
  emptyMessage?: string
  onRetry: () => void
  children: ReactNode
}) {
  if (loading) {
    return (
      <div className={cn(CARD, 'flex h-[300px] flex-col items-center justify-center gap-3 text-[#5A5F7A]')}>
        <Loader2 className="h-5 w-5 animate-spin text-[#4F46E5]" />
        <p className="text-[12px]">Loading…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div className={cn(CARD, 'flex h-[300px] flex-col items-center justify-center gap-3')}>
        <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
        <p className="max-w-md text-center text-[12px] text-[#5A5F7A]">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </button>
      </div>
    )
  }
  if (empty) {
    return (
      <div className={cn(CARD, 'flex h-[220px] items-center justify-center')}>
        <p className="text-[12px] text-[#8A8FA8]">{emptyMessage}</p>
      </div>
    )
  }
  return <>{children}</>
}

/** A plain data table matching the dashboard's card styling. */
export function DataTable({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className={cn(CARD, 'p-4')}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="whitespace-nowrap border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
              {head.map((h, i) => (
                <th key={h} className={cn('px-3 py-2 font-medium', i === 0 ? 'text-left' : 'text-center')}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
    </div>
  )
}

export const TD = 'px-3 py-2 text-center text-[#3A3F58]'
export const TD_LEFT = 'px-3 py-2 text-left text-[#1B1B3A]'

export function Pill({ tone, children }: { tone: 'green' | 'amber' | 'red' | 'slate'; children: ReactNode }) {
  const styles = {
    green: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
    amber: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
    red: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
    slate: 'border-[#E2E5F0] bg-[#F7F8FC] text-[#6B7280]',
  }
  return (
    <span className={cn('inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px]', styles[tone])}>
      {children}
    </span>
  )
}

/** For screens whose backend work is not built yet - says so plainly. */
export function NotBuiltYet({ what, needs }: { what: string; needs: string }) {
  return (
    <div className={cn(CARD, 'flex h-[300px] flex-col items-center justify-center gap-2 px-6 text-center')}>
      <p className="text-[14px] font-semibold text-[#1B1B3A]">{what} is not built yet</p>
      <p className="max-w-lg text-[12px] leading-relaxed text-[#5A5F7A]">{needs}</p>
      <Link
        href="/faculty"
        className="mt-2 rounded-lg border border-[#DDE0EE] px-4 py-2 text-[12px] font-medium text-[#3A3F58] hover:bg-[#F7F8FC]"
      >
        Back to dashboard
      </Link>
    </div>
  )
}
