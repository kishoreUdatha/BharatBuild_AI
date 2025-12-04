'use client'

import { useState, useCallback } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface PaymentOrder {
  order_id: string
  amount: number
  currency: string
  key_id: string
  package_name: string
  tokens: number
}

interface PaymentResult {
  success: boolean
  message: string
  tokens_credited?: number
  new_balance?: number
}

declare global {
  interface Window {
    Razorpay: any
  }
}

export function usePayment() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadRazorpayScript = useCallback((): Promise<boolean> => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true)
        return
      }

      const script = document.createElement('script')
      script.src = 'https://checkout.razorpay.com/v1/checkout.js'
      script.onload = () => resolve(true)
      script.onerror = () => resolve(false)
      document.body.appendChild(script)
    })
  }, [])

  const createOrder = async (packageId: string): Promise<PaymentOrder | null> => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setError('Please login to purchase')
      return null
    }

    try {
      const response = await fetch(`${API_URL}/payments/create-order`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ package: packageId })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create order')
      }

      return await response.json()
    } catch (err: any) {
      setError(err.message)
      return null
    }
  }

  const verifyPayment = async (
    orderId: string,
    paymentId: string,
    signature: string
  ): Promise<PaymentResult> => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      return { success: false, message: 'Not authenticated' }
    }

    try {
      const response = await fetch(`${API_URL}/payments/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          razorpay_order_id: orderId,
          razorpay_payment_id: paymentId,
          razorpay_signature: signature
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Payment verification failed')
      }

      return await response.json()
    } catch (err: any) {
      return { success: false, message: err.message }
    }
  }

  const initiatePayment = useCallback(async (
    packageId: string,
    onSuccess?: (result: PaymentResult) => void,
    onFailure?: (error: string) => void
  ) => {
    setLoading(true)
    setError(null)

    try {
      // Load Razorpay script
      const scriptLoaded = await loadRazorpayScript()
      if (!scriptLoaded) {
        throw new Error('Failed to load payment gateway')
      }

      // Create order
      const order = await createOrder(packageId)
      if (!order) {
        throw new Error(error || 'Failed to create order')
      }

      // Get user info for prefill
      const userEmail = localStorage.getItem('user_email') || ''
      const userName = localStorage.getItem('user_name') || ''

      // Configure Razorpay options
      const options = {
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: 'BharatBuild AI',
        description: `${order.package_name} - ${order.tokens.toLocaleString()} tokens`,
        order_id: order.order_id,
        prefill: {
          email: userEmail,
          name: userName
        },
        theme: {
          color: '#3B82F6'
        },
        handler: async (response: any) => {
          // Verify payment
          const result = await verifyPayment(
            response.razorpay_order_id,
            response.razorpay_payment_id,
            response.razorpay_signature
          )

          if (result.success) {
            onSuccess?.(result)
          } else {
            onFailure?.(result.message)
          }
          setLoading(false)
        },
        modal: {
          ondismiss: () => {
            setLoading(false)
            onFailure?.('Payment cancelled')
          }
        }
      }

      // Open Razorpay checkout
      const razorpay = new window.Razorpay(options)
      razorpay.on('payment.failed', (response: any) => {
        setLoading(false)
        onFailure?.(response.error.description || 'Payment failed')
      })
      razorpay.open()

    } catch (err: any) {
      setLoading(false)
      setError(err.message)
      onFailure?.(err.message)
    }
  }, [loadRazorpayScript, error])

  return {
    initiatePayment,
    loading,
    error,
    clearError: () => setError(null)
  }
}
