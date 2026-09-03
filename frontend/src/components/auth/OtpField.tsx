'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle, CheckCircle2, Loader2, Send } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

export type OtpChannel = 'email' | 'phone'

interface OtpResponse {
  channel: string
  destination: string
  expires_in: number
  resend_after: number
  delivered: boolean
  dev_code: string | null
  dev_mode: boolean
}

function detail(err: any, fallback: string): string {
  const d = err?.response?.data?.detail
  if (typeof d === 'string' && d.trim()) return d
  if (Array.isArray(d)) return d.map((x: any) => x?.msg).filter(Boolean).join('; ') || fallback
  return fallback
}

const valid = (channel: OtpChannel, value: string) =>
  channel === 'email'
    ? /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(value.trim())
    : /^[6-9]\d{9}$/.test(value.replace(/\D/g, ''))

/**
 * Proof-of-ownership for one contact field.
 *
 * Sends a code as soon as the field holds a plausible address or number and
 * the user moves on, then takes the code inline. The parent is told when the
 * destination is proven and blocks submission until then.
 */
export function OtpField({
  channel, value, verified, onVerified, disabled, required,
}: {
  channel: OtpChannel
  value: string
  verified: boolean
  /** Receives the proof token on success, or null when it is invalidated. */
  onVerified: (token: string | null) => void
  disabled?: boolean
  required?: boolean
}) {
  const [sending, setSending] = useState(false)
  const [checking, setChecking] = useState(false)
  const [sent, setSent] = useState<OtpResponse | null>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [cooldown, setCooldown] = useState(0)

  // Which destination the current code belongs to. Editing the field after a
  // code was sent must invalidate it, or the user could verify one address and
  // register another.
  const sentFor = useRef<string | null>(null)
  const label = channel === 'email' ? 'email' : 'mobile number'

  useEffect(() => {
    if (sentFor.current !== null && sentFor.current !== value.trim()) {
      setSent(null)
      setCode('')
      setError('')
      sentFor.current = null
      onVerified(null)
    }
  }, [value, onVerified])

  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  const send = useCallback(async () => {
    const destination = value.trim()
    if (!valid(channel, destination)) {
      setError(channel === 'email'
        ? 'Enter a valid email address first.'
        : 'Enter a valid 10-digit mobile number first.')
      return
    }
    setSending(true)
    setError('')
    try {
      const result = await apiClient.post<OtpResponse>('/auth/otp/request', {
        channel, destination,
      })
      setSent(result)
      sentFor.current = destination
      setCooldown(result.resend_after ?? 60)
    } catch (err: any) {
      setError(detail(err, `Could not send a code to your ${label}.`))
    } finally {
      setSending(false)
    }
  }, [channel, value, label])

  const check = useCallback(async (raw: string) => {
    setChecking(true)
    setError('')
    try {
      const result = await apiClient.post<{ verification_token?: string }>('/auth/otp/verify', {
        channel, destination: value.trim(), code: raw,
      })
      onVerified(result?.verification_token ?? null)
    } catch (err: any) {
      setError(detail(err, 'That code could not be verified.'))
      onVerified(null)
    } finally {
      setChecking(false)
    }
  }, [channel, value, onVerified])

  // Auto-submit once six digits are in - no reason to make the user click.
  const onCodeChange = (raw: string) => {
    const digits = raw.replace(/\D/g, '').slice(0, 6)
    setCode(digits)
    if (digits.length === 6) check(digits)
  }

  if (verified) {
    return (
      <p className="flex items-center gap-1.5 text-[11px] font-medium text-green-400">
        <CheckCircle2 className="h-3.5 w-3.5" /> {channel === 'email' ? 'Email' : 'Mobile'} verified
      </p>
    )
  }

  const ready = valid(channel, value)

  return (
    <div className="space-y-1.5">
      {!sent ? (
        <button type="button" onClick={send} disabled={disabled || sending || !ready}
          className={cn('inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium transition-colors',
            ready && !disabled
              ? 'text-blue-400 hover:bg-blue-500/10'
              : 'cursor-not-allowed text-gray-500')}>
          {sending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
          {sending ? 'Sending…' : `Verify ${channel === 'email' ? 'email' : 'mobile'}`}
          {required && <span className="text-red-400">*</span>}
        </button>
      ) : (
        <div className="space-y-1.5 rounded-lg border border-blue-500/25 bg-blue-500/5 p-2">
          <p className="text-[10.5px] text-gray-300">
            Code sent to <span className="font-medium text-white">{sent.destination}</span>
          </p>
          <div className="flex items-center gap-2">
            <input inputMode="numeric" autoComplete="one-time-code" value={code}
              onChange={(e) => onCodeChange(e.target.value)}
              placeholder="6-digit code" aria-label={`Verification code for your ${label}`}
              className="h-8 w-[128px] rounded-md border border-white/15 bg-white/5 px-2 text-[12px] tracking-[3px] text-white placeholder:tracking-normal placeholder:text-gray-500 focus:border-blue-500/60 focus:outline-none" />
            {checking && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />}
            <button type="button" onClick={send} disabled={cooldown > 0 || sending}
              className={cn('text-[10.5px] font-medium',
                cooldown > 0 ? 'cursor-not-allowed text-gray-500' : 'text-blue-400 hover:underline')}>
              {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend code'}
            </button>
          </div>

          {sent.dev_mode && sent.dev_code && (
            // Only ever returned outside production, and only when no provider
            // is configured. Labelled so nobody mistakes it for a real send.
            <p className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-[10px] text-amber-300">
              No {channel === 'email' ? 'email' : 'SMS'} provider is configured, so nothing was
              actually sent. Development code: <span className="font-mono font-bold">{sent.dev_code}</span>
            </p>
          )}
        </div>
      )}

      {error && (
        <p className="flex items-start gap-1.5 text-[10.5px] text-red-400">
          <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" /> {error}
        </p>
      )}
    </div>
  )
}
