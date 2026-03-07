'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import { RoleDashboardRouter } from '@/components/naac/dashboards'
import { Loader2, AlertTriangle } from 'lucide-react'

export default function NAACDashboardPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const { roles, isLoading: rolesLoading, highestRole } = useNAACRole()

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  if (authLoading || rolesLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  // Check if user has any NAAC role
  if (roles.length === 0) {
    // Fallback for admin/faculty without specific NAAC role
    if (user?.role === 'admin' || user?.role === 'faculty') {
      return (
        <div className="p-8">
          <div className="max-w-4xl mx-auto">
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-6 mb-8">
              <div className="flex items-start gap-4">
                <AlertTriangle className="w-6 h-6 text-yellow-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-yellow-400 mb-2">No NAAC Role Assigned</h3>
                  <p className="text-slate-300 text-sm mb-4">
                    You don't have a specific NAAC role assigned yet. As an {user?.role}, you can still access
                    the accreditation features, but for a personalized dashboard, please contact your administrator
                    to assign you an appropriate NAAC role.
                  </p>
                  <div className="flex gap-3">
                    <a
                      href="/admin/accreditation/roles/manage"
                      className="bg-yellow-500 hover:bg-yellow-600 text-black px-4 py-2 rounded-lg text-sm font-medium"
                    >
                      Manage Roles
                    </a>
                    <a
                      href="/admin/accreditation/criterion1"
                      className="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm"
                    >
                      Browse Criteria
                    </a>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Links for Admin */}
            <h2 className="text-xl font-bold mb-4">Quick Access</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <a
                href="/admin/accreditation/ssr"
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-orange-500/50 transition-colors"
              >
                <h3 className="font-semibold mb-1">SSR Generation</h3>
                <p className="text-sm text-slate-400">Generate Self Study Report</p>
              </a>
              <a
                href="/admin/accreditation/documents"
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-orange-500/50 transition-colors"
              >
                <h3 className="font-semibold mb-1">Documents</h3>
                <p className="text-sm text-slate-400">Manage generated documents</p>
              </a>
              <a
                href="/admin/accreditation/settings"
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-orange-500/50 transition-colors"
              >
                <h3 className="font-semibold mb-1">Institution Settings</h3>
                <p className="text-sm text-slate-400">Configure institution profile</p>
              </a>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">Access Restricted</h2>
          <p className="text-slate-400 mb-6">
            You don't have permission to access the NAAC dashboard. Please contact your IQAC Coordinator
            to get assigned an appropriate role.
          </p>
          <button
            onClick={() => router.push('/accreditation')}
            className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-2 rounded-lg"
          >
            Go to Student Portal
          </button>
        </div>
      </div>
    )
  }

  // Render role-specific dashboard
  return <RoleDashboardRouter />
}
