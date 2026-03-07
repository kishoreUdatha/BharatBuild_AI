'use client'

import React from 'react'
import { useNAACRole } from '@/contexts/NAACRoleContext'
import { AlertCircle, Lock, Loader2 } from 'lucide-react'
import Link from 'next/link'

interface ProtectedNAACRouteProps {
  children: React.ReactNode
  // Role requirements (any of these roles grants access)
  requiredRoles?: string[]
  // Criterion access requirement
  requiredCriterion?: number
  // Department access requirement
  requiredDepartment?: string
  // Approval level requirement
  requireApprovalLevel?: 'department' | 'criterion' | 'iqac' | 'head'
  // Custom access check function
  customCheck?: () => boolean
  // Fallback content when access is denied
  fallback?: React.ReactNode
  // Show loading state
  showLoading?: boolean
}

export default function ProtectedNAACRoute({
  children,
  requiredRoles,
  requiredCriterion,
  requiredDepartment,
  requireApprovalLevel,
  customCheck,
  fallback,
  showLoading = true,
}: ProtectedNAACRouteProps) {
  const {
    roles,
    isLoading,
    error,
    hasAnyRole,
    hasCriterionAccess,
    hasDepartmentAccess,
    canApprove,
  } = useNAACRole()

  // Show loading state
  if (isLoading && showLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-slate-400">Checking permissions...</p>
        </div>
      </div>
    )
  }

  // Handle error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Error Loading Permissions</h3>
          <p className="text-slate-400 mb-4">{error}</p>
          <Link
            href="/admin/accreditation"
            className="inline-block px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  // Check access
  let hasAccess = true
  let deniedReason = ''

  // Check roles
  if (requiredRoles && requiredRoles.length > 0) {
    if (!hasAnyRole(requiredRoles)) {
      hasAccess = false
      deniedReason = `Required role: ${requiredRoles.join(' or ')}`
    }
  }

  // Check criterion access
  if (hasAccess && requiredCriterion) {
    if (!hasCriterionAccess(requiredCriterion)) {
      hasAccess = false
      deniedReason = `Access to Criterion ${requiredCriterion} is required`
    }
  }

  // Check department access
  if (hasAccess && requiredDepartment) {
    if (!hasDepartmentAccess(requiredDepartment)) {
      hasAccess = false
      deniedReason = `Access to ${requiredDepartment} department is required`
    }
  }

  // Check approval level
  if (hasAccess && requireApprovalLevel) {
    if (!canApprove(requireApprovalLevel)) {
      hasAccess = false
      deniedReason = `${requireApprovalLevel.charAt(0).toUpperCase() + requireApprovalLevel.slice(1)} approval permission required`
    }
  }

  // Custom check
  if (hasAccess && customCheck) {
    if (!customCheck()) {
      hasAccess = false
      deniedReason = 'Access denied'
    }
  }

  // If no roles at all, check if any requirements were specified
  if (roles.length === 0 && (requiredRoles || requiredCriterion || requiredDepartment || requireApprovalLevel)) {
    hasAccess = false
    deniedReason = 'No NAAC role assigned. Please contact the administrator.'
  }

  // Render access denied
  if (!hasAccess) {
    if (fallback) {
      return <>{fallback}</>
    }

    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 max-w-md text-center">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">Access Denied</h3>
          <p className="text-slate-400 mb-6">{deniedReason}</p>
          <div className="flex gap-3 justify-center">
            <Link
              href="/admin/accreditation"
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white transition-colors"
            >
              Go to Dashboard
            </Link>
            <Link
              href="/admin/accreditation/roles"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
            >
              View My Roles
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

// Higher-order component version
export function withNAACProtection<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  options: Omit<ProtectedNAACRouteProps, 'children'>
) {
  return function WithNAACProtection(props: P) {
    return (
      <ProtectedNAACRoute {...options}>
        <WrappedComponent {...props} />
      </ProtectedNAACRoute>
    )
  }
}

// Utility components for common protection patterns

export function RequireIQACCoordinator({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedNAACRoute
      requiredRoles={['iqac_coordinator', 'head_of_institution']}
    >
      {children}
    </ProtectedNAACRoute>
  )
}

export function RequireCriterionCoordinator({
  children,
  criterion,
}: {
  children: React.ReactNode
  criterion: number
}) {
  return (
    <ProtectedNAACRoute
      requiredRoles={['criterion_coordinator', 'iqac_coordinator', 'head_of_institution']}
      requiredCriterion={criterion}
    >
      {children}
    </ProtectedNAACRoute>
  )
}

export function RequireDepartmentCoordinator({
  children,
  department,
}: {
  children: React.ReactNode
  department: string
}) {
  return (
    <ProtectedNAACRoute
      requiredRoles={['department_coordinator', 'criterion_coordinator', 'iqac_coordinator', 'head_of_institution']}
      requiredDepartment={department}
    >
      {children}
    </ProtectedNAACRoute>
  )
}

export function RequireApprover({
  children,
  level,
}: {
  children: React.ReactNode
  level: 'department' | 'criterion' | 'iqac' | 'head'
}) {
  return (
    <ProtectedNAACRoute requireApprovalLevel={level}>
      {children}
    </ProtectedNAACRoute>
  )
}
