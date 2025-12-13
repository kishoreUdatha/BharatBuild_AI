'use client'

import * as React from 'react'
import { createContext, useContext, useState, useCallback } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle, Info, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// Toast types
type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading'

interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
  success: (title: string, message?: string) => string
  error: (title: string, message?: string) => string
  warning: (title: string, message?: string) => string
  info: (title: string, message?: string) => string
  loading: (title: string, message?: string) => string
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

// Toast Provider
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(7)
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? (toast.type === 'loading' ? 0 : 5000)
    }

    setToasts(prev => [...prev, newToast])

    // Auto remove after duration (unless loading or duration is 0)
    if (newToast.duration && newToast.duration > 0) {
      setTimeout(() => {
        removeToast(id)
      }, newToast.duration)
    }

    return id
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const success = useCallback((title: string, message?: string) =>
    addToast({ type: 'success', title, message }), [addToast])

  const error = useCallback((title: string, message?: string) =>
    addToast({ type: 'error', title, message, duration: 8000 }), [addToast])

  const warning = useCallback((title: string, message?: string) =>
    addToast({ type: 'warning', title, message }), [addToast])

  const info = useCallback((title: string, message?: string) =>
    addToast({ type: 'info', title, message }), [addToast])

  const loading = useCallback((title: string, message?: string) =>
    addToast({ type: 'loading', title, message }), [addToast])

  return (
    <ToastContext.Provider value={{
      toasts,
      addToast,
      removeToast,
      success,
      error,
      warning,
      info,
      loading,
      dismiss: removeToast
    }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  )
}

// Toast Container
function ToastContainer({
  toasts,
  onDismiss
}: {
  toasts: Toast[]
  onDismiss: (id: string) => void
}) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map(toast => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  )
}

// Individual Toast
function ToastItem({
  toast,
  onDismiss
}: {
  toast: Toast
  onDismiss: (id: string) => void
}) {
  const icons: Record<ToastType, React.ReactNode> = {
    success: <CheckCircle className="w-5 h-5 text-green-400" />,
    error: <AlertCircle className="w-5 h-5 text-red-400" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-400" />,
    info: <Info className="w-5 h-5 text-blue-400" />,
    loading: <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
  }

  const bgColors: Record<ToastType, string> = {
    success: 'bg-green-500/10 border-green-500/30',
    error: 'bg-red-500/10 border-red-500/30',
    warning: 'bg-yellow-500/10 border-yellow-500/30',
    info: 'bg-blue-500/10 border-blue-500/30',
    loading: 'bg-blue-500/10 border-blue-500/30'
  }

  return (
    <div
      className={cn(
        'pointer-events-auto flex items-start gap-3 p-4 rounded-lg border shadow-lg backdrop-blur-sm',
        'animate-in slide-in-from-right-full duration-300',
        'bg-[hsl(var(--bolt-bg-secondary))]',
        bgColors[toast.type]
      )}
    >
      {icons[toast.type]}

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
          {toast.title}
        </p>
        {toast.message && (
          <p className="mt-1 text-xs text-[hsl(var(--bolt-text-secondary))]">
            {toast.message}
          </p>
        )}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className="mt-2 text-xs font-medium text-blue-400 hover:text-blue-300"
          >
            {toast.action.label}
          </button>
        )}
      </div>

      {toast.type !== 'loading' && (
        <button
          onClick={() => onDismiss(toast.id)}
          className="text-[hsl(var(--bolt-text-tertiary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

// API Error Handler Utility
export function getErrorMessage(error: any): { title: string; message: string } {
  // Rate limit error
  if (error?.status === 429 || error?.response?.status === 429) {
    const retryAfter = error?.retry_after_seconds || error?.response?.data?.retry_after_seconds || 60
    return {
      title: 'Too Many Requests',
      message: `Please wait ${retryAfter} seconds before trying again.`
    }
  }

  // Authentication errors
  if (error?.status === 401 || error?.response?.status === 401) {
    return {
      title: 'Session Expired',
      message: 'Please log in again to continue.'
    }
  }

  // Permission errors
  if (error?.status === 403 || error?.response?.status === 403) {
    return {
      title: 'Access Denied',
      message: 'You don\'t have permission to perform this action.'
    }
  }

  // Not found
  if (error?.status === 404 || error?.response?.status === 404) {
    return {
      title: 'Not Found',
      message: 'The requested resource could not be found.'
    }
  }

  // Validation errors
  if (error?.status === 422 || error?.response?.status === 422) {
    const detail = error?.response?.data?.detail || error?.detail
    if (Array.isArray(detail)) {
      const messages = detail.map((d: any) => d.msg || d.message).join(', ')
      return {
        title: 'Validation Error',
        message: messages || 'Please check your input and try again.'
      }
    }
    return {
      title: 'Validation Error',
      message: typeof detail === 'string' ? detail : 'Please check your input and try again.'
    }
  }

  // Server errors
  if (error?.status >= 500 || error?.response?.status >= 500) {
    return {
      title: 'Server Error',
      message: 'Something went wrong on our end. Please try again later.'
    }
  }

  // Network errors
  if (error?.message?.includes('Network') || error?.message?.includes('fetch')) {
    return {
      title: 'Connection Error',
      message: 'Unable to connect to server. Please check your internet connection.'
    }
  }

  // Generic error with message
  if (error?.message) {
    return {
      title: 'Error',
      message: error.message
    }
  }

  // Response data error
  if (error?.response?.data?.detail) {
    return {
      title: 'Error',
      message: error.response.data.detail
    }
  }

  // Default
  return {
    title: 'Error',
    message: 'An unexpected error occurred. Please try again.'
  }
}

export default ToastProvider
