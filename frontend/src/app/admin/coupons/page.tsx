'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import apiClient from '@/lib/api-client'
import {
  Ticket,
  Users,
  TrendingUp,
  DollarSign,
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  BarChart2,
  Copy,
  Check
} from 'lucide-react'

interface Coupon {
  id: string
  code: string
  owner_id: string
  owner_name: string | null
  owner_email: string | null
  owner_phone: string | null
  category: 'student' | 'faculty' | 'college' | 'media'
  name: string | null
  description: string | null
  discount_amount: number
  discount_amount_inr: number
  reward_amount: number
  reward_amount_inr: number
  total_uses: number
  total_discount_given: number
  total_reward_earned: number
  status: 'active' | 'inactive' | 'expired'
  is_active: boolean
  valid_from: string
  valid_until: string | null
  created_at: string
}

interface CouponAnalytics {
  total_coupons: number
  active_coupons: number
  total_uses: number
  total_discount_given: number
  total_discount_given_inr: number
  total_rewards_paid: number
  total_rewards_paid_inr: number
  coupons_by_category: Record<string, number>
}

export default function AdminCouponsPage() {
  const { theme } = useAdminTheme()
  const isDark = theme === 'dark'

  const [coupons, setCoupons] = useState<Coupon[]>([])
  const [analytics, setAnalytics] = useState<CouponAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize] = useState(10)

  // Filters
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedCoupon, setSelectedCoupon] = useState<Coupon | null>(null)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState({
    code: '',
    owner_name: '',
    owner_email: '',
    owner_phone: '',
    category: 'student',
    name: '',
    description: '',
    discount_amount: 10000,
    reward_amount: 10000,
    valid_until: ''
  })
  const [formError, setFormError] = useState('')
  const [formLoading, setFormLoading] = useState(false)

  // Edit form state
  const [editFormData, setEditFormData] = useState({
    name: '',
    description: '',
    owner_name: '',
    owner_email: '',
    owner_phone: '',
    category: 'student',
    discount_amount: 10000,
    reward_amount: 10000,
    is_active: true,
    valid_until: ''
  })
  const [editFormError, setEditFormError] = useState('')
  const [editFormLoading, setEditFormLoading] = useState(false)

  const fetchCoupons = useCallback(async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      })
      if (search) params.append('search', search)
      if (statusFilter) params.append('status', statusFilter)
      if (categoryFilter) params.append('category', categoryFilter)

      const response = await apiClient.get<any>(`/admin/coupons?${params.toString()}`)
      setCoupons(response.coupons || [])
      setTotal(response.total || 0)
    } catch (error) {
      console.error('Failed to fetch coupons:', error)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, statusFilter, categoryFilter])

  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await apiClient.get<CouponAnalytics>('/admin/coupons/analytics')
      setAnalytics(response)
    } catch (error) {
      console.error('Failed to fetch analytics:', error)
    }
  }, [])

  useEffect(() => {
    fetchCoupons()
  }, [fetchCoupons])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  const handleCreateCoupon = async () => {
    if (!formData.code || !formData.owner_name || !formData.owner_email || !formData.owner_phone) {
      setFormError('Code, Owner Name, Email and Phone are required')
      return
    }

    try {
      setFormLoading(true)
      setFormError('')

      await apiClient.post('/admin/coupons', {
        code: formData.code.toUpperCase(),
        owner_name: formData.owner_name,
        owner_email: formData.owner_email,
        owner_phone: formData.owner_phone,
        category: formData.category,
        name: formData.name || null,
        description: formData.description || null,
        discount_amount: formData.discount_amount,
        reward_amount: formData.reward_amount,
        valid_until: formData.valid_until || null
      })

      setShowCreateModal(false)
      setFormData({
        code: '',
        owner_name: '',
        owner_email: '',
        owner_phone: '',
        category: 'student',
        name: '',
        description: '',
        discount_amount: 10000,
        reward_amount: 10000,
        valid_until: ''
      })
      fetchCoupons()
      fetchAnalytics()
    } catch (error: any) {
      setFormError(error.response?.data?.detail || 'Failed to create coupon')
    } finally {
      setFormLoading(false)
    }
  }

  const handleDeactivate = async (couponId: string) => {
    if (!confirm('Are you sure you want to deactivate this coupon?')) return

    try {
      await apiClient.delete(`/admin/coupons/${couponId}`)
      fetchCoupons()
      fetchAnalytics()
    } catch (error) {
      console.error('Failed to deactivate coupon:', error)
    }
  }

  const openEditModal = (coupon: Coupon) => {
    setSelectedCoupon(coupon)
    setEditFormData({
      name: coupon.name || '',
      description: coupon.description || '',
      owner_name: coupon.owner_name || '',
      owner_email: coupon.owner_email || '',
      owner_phone: coupon.owner_phone || '',
      category: coupon.category,
      discount_amount: coupon.discount_amount,
      reward_amount: coupon.reward_amount,
      is_active: coupon.is_active,
      valid_until: coupon.valid_until ? new Date(coupon.valid_until).toISOString().split('T')[0] : ''
    })
    setEditFormError('')
    setShowEditModal(true)
  }

  const handleUpdateCoupon = async () => {
    if (!selectedCoupon) return

    try {
      setEditFormLoading(true)
      setEditFormError('')

      await apiClient.put(`/admin/coupons/${selectedCoupon.id}`, {
        name: editFormData.name || null,
        description: editFormData.description || null,
        owner_name: editFormData.owner_name || null,
        owner_email: editFormData.owner_email || null,
        owner_phone: editFormData.owner_phone || null,
        category: editFormData.category,
        discount_amount: editFormData.discount_amount,
        reward_amount: editFormData.reward_amount,
        is_active: editFormData.is_active,
        valid_until: editFormData.valid_until || null
      })

      setShowEditModal(false)
      setSelectedCoupon(null)
      fetchCoupons()
      fetchAnalytics()
    } catch (error: any) {
      setEditFormError(error.response?.data?.detail || 'Failed to update coupon')
    } finally {
      setEditFormLoading(false)
    }
  }

  const copyToClipboard = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      active: 'bg-green-500/20 text-green-400',
      inactive: 'bg-gray-500/20 text-gray-400',
      expired: 'bg-red-500/20 text-red-400'
    }
    return colors[status as keyof typeof colors] || colors.inactive
  }

  const getCategoryBadge = (category: string) => {
    const colors = {
      student: 'bg-blue-500/20 text-blue-400',
      faculty: 'bg-purple-500/20 text-purple-400',
      college: 'bg-orange-500/20 text-orange-400',
      media: 'bg-pink-500/20 text-pink-400'
    }
    return colors[category as keyof typeof colors] || 'bg-gray-500/20 text-gray-400'
  }

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN')}`
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#0a0a0a]' : 'bg-gray-50'}`}>
      <AdminHeader
        onRefresh={() => { fetchCoupons(); fetchAnalytics(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Page Title */}
        <div className="mb-6">
          <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Coupon Management
          </h1>
          <p className={`mt-1 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            Create and manage referral coupons. When someone uses a coupon, they get a discount and the coupon owner earns a reward.
          </p>
        </div>

        {/* Stats - Compact */}
        <div className="flex flex-wrap gap-3 mb-6">
          <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
            <Ticket className="w-4 h-4 text-blue-500" />
            <div>
              <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Total</span>
              <p className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{analytics?.total_coupons || 0}</p>
            </div>
          </div>
          <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
            <Check className="w-4 h-4 text-green-500" />
            <div>
              <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Active</span>
              <p className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{analytics?.active_coupons || 0}</p>
            </div>
          </div>
          <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
            <Users className="w-4 h-4 text-purple-500" />
            <div>
              <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Uses</span>
              <p className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{analytics?.total_uses || 0}</p>
            </div>
          </div>
          <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
            <DollarSign className="w-4 h-4 text-orange-500" />
            <div>
              <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>Rewards Paid</span>
              <p className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatCurrency(analytics?.total_rewards_paid || 0)}</p>
            </div>
          </div>
        </div>

      {/* Filters and Actions */}
      <div className={`p-4 rounded-lg border mb-6 ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex flex-wrap gap-3 items-center">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by code or name..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                className={`pl-10 pr-4 py-2 rounded-lg border text-sm w-64 ${
                  isDark
                    ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                    : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
                } outline-none focus:border-blue-500`}
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className={`px-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white'
                  : 'bg-gray-50 border-gray-200 text-gray-900'
              } outline-none focus:border-blue-500`}
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="expired">Expired</option>
            </select>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
              className={`px-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white'
                  : 'bg-gray-50 border-gray-200 text-gray-900'
              } outline-none focus:border-blue-500`}
            >
              <option value="">All Categories</option>
              <option value="student">Student</option>
              <option value="faculty">Faculty</option>
              <option value="college">College</option>
              <option value="media">Media</option>
            </select>
          </div>

          {/* Create Button */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Coupon
          </button>
        </div>
      </div>

      {/* Table */}
      <div className={`rounded-lg border overflow-hidden ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
              <tr>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Code</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Owner</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Category</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Discount</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Reward</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Uses</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Status</th>
                <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Actions</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className={isDark ? 'bg-[#1a1a1a]' : 'bg-white'}>
                    {[...Array(8)].map((_, j) => (
                      <td key={j} className="px-4 py-4">
                        <div className={`h-4 rounded animate-pulse ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`}></div>
                      </td>
                    ))}
                  </tr>
                ))
              ) : coupons.length === 0 ? (
                <tr>
                  <td colSpan={8} className={`px-4 py-8 text-center ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    No coupons found. Create your first coupon to get started.
                  </td>
                </tr>
              ) : (
                coupons.map((coupon) => (
                  <tr
                    key={coupon.id}
                    className={`${isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'} transition-colors`}
                  >
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <code className={`px-2 py-1 rounded text-sm font-mono ${isDark ? 'bg-[#333] text-white' : 'bg-gray-100 text-gray-900'}`}>
                          {coupon.code}
                        </code>
                        <button
                          onClick={() => copyToClipboard(coupon.code)}
                          className={`p-1 rounded hover:bg-opacity-20 ${isDark ? 'hover:bg-white' : 'hover:bg-gray-500'}`}
                        >
                          {copiedCode === coupon.code ? (
                            <Check className="w-4 h-4 text-green-500" />
                          ) : (
                            <Copy className="w-4 h-4 text-gray-400" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <div>
                        <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                          {coupon.owner_name || 'Unknown'}
                        </p>
                        <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          {coupon.owner_email}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getCategoryBadge(coupon.category)}`}>
                        {coupon.category}
                      </span>
                    </td>
                    <td className={`px-4 py-4 text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {formatCurrency(coupon.discount_amount)}
                    </td>
                    <td className={`px-4 py-4 text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      {formatCurrency(coupon.reward_amount)}
                    </td>
                    <td className="px-4 py-4">
                      <div>
                        <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                          {coupon.total_uses}
                        </p>
                        <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          Earned: {formatCurrency(coupon.total_reward_earned)}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${getStatusBadge(coupon.status)}`}>
                        {coupon.status}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEditModal(coupon)}
                          className={`p-2 rounded-lg transition-colors ${
                            isDark
                              ? 'hover:bg-blue-500/20 text-gray-400 hover:text-blue-400'
                              : 'hover:bg-blue-50 text-gray-500 hover:text-blue-500'
                          }`}
                          title="Edit"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeactivate(coupon.id)}
                          className={`p-2 rounded-lg transition-colors ${
                            isDark
                              ? 'hover:bg-red-500/20 text-gray-400 hover:text-red-400'
                              : 'hover:bg-red-50 text-gray-500 hover:text-red-500'
                          }`}
                          title="Deactivate"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className={`px-4 py-3 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className={`w-full max-w-xl rounded-lg p-6 ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <h2 className={`text-xl font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Create New Coupon
            </h2>

            {formError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/20 text-red-400 text-sm">
                {formError}
              </div>
            )}

            <div className="space-y-4">
              {/* Row 1: Code & Category */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Coupon Code *
                  </label>
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                    placeholder="e.g., RAVI2024"
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Category *
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  >
                    <option value="student">Student</option>
                    <option value="faculty">Faculty</option>
                    <option value="college">College</option>
                    <option value="media">Media</option>
                  </select>
                </div>
              </div>

              {/* Row 2: Owner Name & Phone */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Owner Name *
                  </label>
                  <input
                    type="text"
                    value={formData.owner_name}
                    onChange={(e) => setFormData({ ...formData, owner_name: e.target.value })}
                    placeholder="e.g., Ravi Kumar"
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Owner Phone *
                  </label>
                  <input
                    type="tel"
                    value={formData.owner_phone}
                    onChange={(e) => setFormData({ ...formData, owner_phone: e.target.value })}
                    placeholder="e.g., 9876543210"
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
              </div>

              {/* Row 3: Owner Email (full width) */}
              <div>
                <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Owner Email *
                </label>
                <input
                  type="email"
                  value={formData.owner_email}
                  onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
                  placeholder="e.g., ravi@example.com"
                  className={`w-full px-4 py-2 rounded-lg border text-sm ${
                    isDark
                      ? 'bg-[#252525] border-[#333] text-white'
                      : 'bg-gray-50 border-gray-200 text-gray-900'
                  } outline-none focus:border-blue-500`}
                />
              </div>

              {/* Row 4: Discount & Reward */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Discount (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.discount_amount / 100}
                    onChange={(e) => setFormData({ ...formData, discount_amount: parseInt(e.target.value) * 100 || 0 })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Reward (₹)
                  </label>
                  <input
                    type="number"
                    value={formData.reward_amount / 100}
                    onChange={(e) => setFormData({ ...formData, reward_amount: parseInt(e.target.value) * 100 || 0 })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
              </div>

              {/* Row 5: Display Name (full width) */}
              <div>
                <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Display Name (Optional)
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Ravi's Referral Code"
                  className={`w-full px-4 py-2 rounded-lg border text-sm ${
                    isDark
                      ? 'bg-[#252525] border-[#333] text-white'
                      : 'bg-gray-50 border-gray-200 text-gray-900'
                  } outline-none focus:border-blue-500`}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  isDark
                    ? 'bg-[#333] text-white hover:bg-[#444]'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCoupon}
                disabled={formLoading}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium disabled:opacity-50"
              >
                {formLoading ? 'Creating...' : 'Create Coupon'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedCoupon && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className={`w-full max-w-xl rounded-lg p-6 ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <h2 className={`text-xl font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Edit Coupon: {selectedCoupon.code}
            </h2>

            {editFormError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/20 text-red-400 text-sm">
                {editFormError}
              </div>
            )}

            <div className="space-y-4">
              {/* Row 1: Owner Name & Phone */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Owner Name
                  </label>
                  <input
                    type="text"
                    value={editFormData.owner_name}
                    onChange={(e) => setEditFormData({ ...editFormData, owner_name: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Owner Phone
                  </label>
                  <input
                    type="tel"
                    value={editFormData.owner_phone}
                    onChange={(e) => setEditFormData({ ...editFormData, owner_phone: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
              </div>

              {/* Row 2: Owner Email & Category */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Owner Email
                  </label>
                  <input
                    type="email"
                    value={editFormData.owner_email}
                    onChange={(e) => setEditFormData({ ...editFormData, owner_email: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Category
                  </label>
                  <select
                    value={editFormData.category}
                    onChange={(e) => setEditFormData({ ...editFormData, category: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  >
                    <option value="student">Student</option>
                    <option value="faculty">Faculty</option>
                    <option value="college">College</option>
                    <option value="media">Media</option>
                  </select>
                </div>
              </div>

              {/* Row 3: Discount & Reward */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Discount Amount (₹)
                  </label>
                  <input
                    type="number"
                    value={editFormData.discount_amount / 100}
                    onChange={(e) => setEditFormData({ ...editFormData, discount_amount: parseInt(e.target.value) * 100 || 0 })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Reward Amount (₹)
                  </label>
                  <input
                    type="number"
                    value={editFormData.reward_amount / 100}
                    onChange={(e) => setEditFormData({ ...editFormData, reward_amount: parseInt(e.target.value) * 100 || 0 })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
              </div>

              {/* Row 4: Display Name */}
              <div>
                <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Display Name
                </label>
                <input
                  type="text"
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  placeholder="Optional display name"
                  className={`w-full px-4 py-2 rounded-lg border text-sm ${
                    isDark
                      ? 'bg-[#252525] border-[#333] text-white'
                      : 'bg-gray-50 border-gray-200 text-gray-900'
                  } outline-none focus:border-blue-500`}
                />
              </div>

              {/* Row 5: Valid Until & Active Status */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    Valid Until
                  </label>
                  <input
                    type="date"
                    value={editFormData.valid_until}
                    onChange={(e) => setEditFormData({ ...editFormData, valid_until: e.target.value })}
                    className={`w-full px-4 py-2 rounded-lg border text-sm ${
                      isDark
                        ? 'bg-[#252525] border-[#333] text-white'
                        : 'bg-gray-50 border-gray-200 text-gray-900'
                    } outline-none focus:border-blue-500`}
                  />
                </div>
                <div className="flex items-center">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editFormData.is_active}
                      onChange={(e) => setEditFormData({ ...editFormData, is_active: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                      Active
                    </span>
                  </label>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => { setShowEditModal(false); setSelectedCoupon(null); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  isDark
                    ? 'bg-[#333] text-white hover:bg-[#444]'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateCoupon}
                disabled={editFormLoading}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium disabled:opacity-50"
              >
                {editFormLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  )
}
