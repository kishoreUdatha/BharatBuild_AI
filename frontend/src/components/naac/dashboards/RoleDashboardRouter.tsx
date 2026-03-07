'use client'

import React from 'react'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import HeadOfInstitutionDashboard from './HeadOfInstitutionDashboard'
import IQACCoordinatorDashboard from './IQACCoordinatorDashboard'
import CriterionCoordinatorDashboard from './CriterionCoordinatorDashboard'
import DepartmentCoordinatorDashboard from './DepartmentCoordinatorDashboard'
import DocumentationTeamDashboard from './DocumentationTeamDashboard'
import { Loader2, UserCircle, Shield } from 'lucide-react'
import Link from 'next/link'

// Role hierarchy for determining which dashboard to show
const ROLE_PRIORITY: Record<string, number> = {
  head_of_institution: 1,
  iqac_coordinator: 2,
  criterion_coordinator: 3,
  department_coordinator: 4,
  documentation_team: 5,
  it_data_analytics: 5,
  ssr_drafting_committee: 5,
  administrative_officer: 5,
  alumni_coordinator: 5,
  placement_officer: 5,
  student_representative: 6,
}

// Map role types to dashboard components
const DASHBOARD_MAP: Record<string, React.ComponentType> = {
  head_of_institution: HeadOfInstitutionDashboard,
  iqac_coordinator: IQACCoordinatorDashboard,
  criterion_coordinator: CriterionCoordinatorDashboard,
  department_coordinator: DepartmentCoordinatorDashboard,
  documentation_team: DocumentationTeamDashboard,
  it_data_analytics: DocumentationTeamDashboard,
  ssr_drafting_committee: DocumentationTeamDashboard,
  administrative_officer: DepartmentCoordinatorDashboard,
  alumni_coordinator: DepartmentCoordinatorDashboard,
  placement_officer: DepartmentCoordinatorDashboard,
  student_representative: DocumentationTeamDashboard,
}

interface RoleDashboardRouterProps {
  // Force a specific dashboard instead of auto-detecting
  forceDashboard?: string
}

export default function RoleDashboardRouter({ forceDashboard }: RoleDashboardRouterProps) {
  const { roles, isLoading, error, highestRole } = useNAACRole()

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-slate-400">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // No roles assigned
  if (roles.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-8 max-w-md text-center">
          <div className="w-20 h-20 bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <UserCircle className="w-10 h-10 text-slate-500" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No NAAC Role Assigned</h3>
          <p className="text-slate-400 mb-6">
            You don't have any NAAC roles assigned yet. Please contact your administrator
            to get the appropriate role assignment for accessing the accreditation system.
          </p>
          <div className="flex gap-3 justify-center">
            <Link
              href="/admin/accreditation/roles"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
            >
              View Roles Info
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Determine which dashboard to show
  let dashboardType = forceDashboard

  if (!dashboardType && highestRole) {
    dashboardType = highestRole.role_type
  }

  // Fallback to first role if no highest role found
  if (!dashboardType && roles.length > 0) {
    // Sort by priority and get highest
    const sortedRoles = [...roles].sort(
      (a, b) => (ROLE_PRIORITY[a.role_type] || 99) - (ROLE_PRIORITY[b.role_type] || 99)
    )
    dashboardType = sortedRoles[0].role_type
  }

  // Get the dashboard component
  const DashboardComponent = dashboardType ? DASHBOARD_MAP[dashboardType] : null

  if (!DashboardComponent) {
    // Show generic dashboard for unknown roles
    return (
      <div className="space-y-6">
        {/* Role Badge */}
        <div className="bg-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-blue-500" />
            <span className="text-white">
              Your role: <strong>{highestRole?.role_display_name || dashboardType}</strong>
            </span>
          </div>
        </div>

        {/* Generic content */}
        <div className="bg-slate-800 rounded-xl p-6 text-center">
          <p className="text-slate-400">
            Dashboard for this role type is being developed.
          </p>
          <div className="mt-4 flex gap-3 justify-center">
            <Link
              href="/admin/accreditation"
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
            >
              Go to Overview
            </Link>
            <Link
              href="/admin/accreditation/tasks"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
            >
              View Tasks
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Role indicator (optional - can be shown/hidden) */}
      {roles.length > 1 && (
        <div className="mb-4 flex items-center gap-2 text-sm text-slate-400">
          <Shield className="w-4 h-4" />
          <span>
            Viewing as: <strong className="text-white">{highestRole?.role_display_name}</strong>
          </span>
          {roles.length > 1 && (
            <span className="text-slate-500">
              ({roles.length} roles assigned)
            </span>
          )}
        </div>
      )}

      {/* Render the appropriate dashboard */}
      <DashboardComponent />
    </div>
  )
}
