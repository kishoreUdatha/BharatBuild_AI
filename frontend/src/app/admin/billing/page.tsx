'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import StatCard from '@/components/admin/StatCard'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import {
  CreditCard,
  TrendingUp,
  Users,
  DollarSign,
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  ChevronUp,
  ChevronDown
} from 'lucide-react'

export default function AdminBillingPage() {
  const { theme } = useAdminTheme()
  const [stats, setStats] = useState<any>(null)
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const isDark = theme === 'dark'

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <div className="w-4 h-4" />
    return sortOrder === 'asc' ? (
      <ChevronUp className="w-4 h-4 text-blue-400" />
    ) : (
      <ChevronDown className="w-4 h-4 text-blue-400" />
    )
  }

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient.get<any>('/admin/billing/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch billing stats:', err)
    }
  }, [])

  const fetchTransactions = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      if (statusFilter) params.append('status', statusFilter)

      const data = await apiClient.get<any>(`/admin/billing/transactions?${params.toString()}`)
      setTransactions(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch transactions:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter, sortBy, sortOrder])

  useEffect(() => {
    fetchStats()
    fetchTransactions()
  }, [fetchStats, fetchTransactions])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount / 100)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-400" />
      case 'refunded':
        return <CreditCard className="w-4 h-4 text-purple-400" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      success: 'bg-green-500/20 text-green-400',
      failed: 'bg-red-500/20 text-red-400',
      pending: 'bg-yellow-500/20 text-yellow-400',
      refunded: 'bg-purple-500/20 text-purple-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Billing & Revenue"
        subtitle="Payment analytics and transactions"
        onRefresh={() => { fetchStats(); fetchTransactions(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Revenue"
            value={formatCurrency((stats?.total_revenue || 0) * 100)}
            icon={DollarSign}
            color="green"
            loading={!stats}
          />
          <StatCard
            title="This Month"
            value={formatCurrency((stats?.revenue_this_month || 0) * 100)}
            icon={TrendingUp}
            color="blue"
            loading={!stats}
          />
          <StatCard
            title="Active Subscriptions"
            value={stats?.active_subscriptions || 0}
            subtitle={`${stats?.total_subscriptions || 0} total`}
            icon={Users}
            color="purple"
            loading={!stats}
          />
          <StatCard
            title="Success Rate"
            value={`${stats?.successful_transactions && stats?.total_transactions
              ? Math.round((stats.successful_transactions / stats.total_transactions) * 100)
              : 0}%`}
            subtitle={`${stats?.successful_transactions || 0} successful`}
            icon={CheckCircle}
            color="cyan"
            loading={!stats}
          />
        </div>

        {/* Transactions Table */}
        <div className={`rounded-xl border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
          <div className={`px-6 py-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
            <div className="flex items-center justify-between">
              <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Recent Transactions
              </h2>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg border text-sm ${
                  isDark
                    ? 'bg-[#252525] border-[#333] text-white'
                    : 'bg-gray-50 border-gray-200 text-gray-900'
                }`}
              >
                <option value="">All Status</option>
                <option value="success">Success</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
                  <th className={`px-6 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Transaction
                  </th>
                  <th className={`px-6 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    User
                  </th>
                  <th
                    className={`px-6 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('amount')}
                  >
                    <div className="flex items-center gap-1">
                      Amount
                      <SortIcon field="amount" />
                    </div>
                  </th>
                  <th
                    className={`px-6 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('status')}
                  >
                    <div className="flex items-center gap-1">
                      Status
                      <SortIcon field="status" />
                    </div>
                  </th>
                  <th
                    className={`px-6 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('created_at')}
                  >
                    <div className="flex items-center gap-1">
                      Date
                      <SortIcon field="created_at" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={5} className="px-6 py-4">
                        <div className="animate-pulse h-6 rounded bg-gray-700" />
                      </td>
                    </tr>
                  ))
                ) : transactions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className={`px-6 py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No transactions found
                    </td>
                  </tr>
                ) : (
                  transactions.map((txn) => (
                    <tr key={txn.id} className={isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          {getStatusIcon(txn.status)}
                          <div>
                            <div className={`font-mono text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {txn.razorpay_payment_id || txn.id.slice(0, 8)}
                            </div>
                            <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                              {txn.description || 'Payment'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                          {txn.user_name || txn.user_email}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                          {formatCurrency(txn.amount)}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(txn.status)}`}>
                          {txn.status}
                        </span>
                      </td>
                      <td className={`px-6 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(txn.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className={`px-6 py-3 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                pageSize={pageSize}
                total={total}
                onPageChange={setPage}
                onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
