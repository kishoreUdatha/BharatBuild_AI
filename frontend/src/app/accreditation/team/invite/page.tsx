'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Users,
  Mail,
  UserPlus,
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Plus
} from 'lucide-react'

interface Invitation {
  id: string
  email: string
  name: string
  role: string
  criterion?: number
}

const NAAC_ROLES = [
  { value: 'iqac_coordinator', label: 'IQAC Coordinator', description: 'Overall accreditation management' },
  { value: 'criterion_head', label: 'Criterion Head', description: 'Lead a specific criterion' },
  { value: 'data_entry', label: 'Data Entry Operator', description: 'Enter data for assigned criteria' },
  { value: 'hod', label: 'Head of Department', description: 'Department-level data management' },
  { value: 'faculty', label: 'Faculty Member', description: 'Contribute to specific indicators' },
]

const CRITERIA = [
  { number: 1, name: 'Curricular Aspects' },
  { number: 2, name: 'Teaching-Learning & Evaluation' },
  { number: 3, name: 'Research, Innovations & Extension' },
  { number: 4, name: 'Infrastructure & Learning Resources' },
  { number: 5, name: 'Student Support & Progression' },
  { number: 6, name: 'Governance, Leadership & Management' },
  { number: 7, name: 'Institutional Values & Best Practices' },
]

export default function TeamInvitePage() {
  const router = useRouter()
  const [invitations, setInvitations] = useState<Invitation[]>([
    { id: '1', email: '', name: '', role: 'faculty', criterion: undefined }
  ])
  const [isSending, setIsSending] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const addInvitation = () => {
    setInvitations([
      ...invitations,
      { id: Date.now().toString(), email: '', name: '', role: 'faculty', criterion: undefined }
    ])
  }

  const removeInvitation = (id: string) => {
    if (invitations.length > 1) {
      setInvitations(invitations.filter(inv => inv.id !== id))
    }
  }

  const updateInvitation = (id: string, field: keyof Invitation, value: any) => {
    setInvitations(invitations.map(inv =>
      inv.id === id ? { ...inv, [field]: value } : inv
    ))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // Validate
    const validInvitations = invitations.filter(inv => inv.email && inv.name)
    if (validInvitations.length === 0) {
      setError('Please add at least one valid invitation')
      return
    }

    // Check for criterion heads without criterion
    const invalidCriterionHeads = validInvitations.filter(
      inv => inv.role === 'criterion_head' && !inv.criterion
    )
    if (invalidCriterionHeads.length > 0) {
      setError('Please select a criterion for all Criterion Heads')
      return
    }

    setIsSending(true)
    try {
      // TODO: Replace with actual API call
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

      // For now, simulate API call
      await new Promise(r => setTimeout(r, 1500))

      setSuccess(true)
      setTimeout(() => {
        router.push('/accreditation/team')
      }, 2000)
    } catch (err: any) {
      setError(err.message || 'Failed to send invitations')
    } finally {
      setIsSending(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Invitations Sent!</h1>
          <p className="text-slate-400 mb-4">
            {invitations.filter(inv => inv.email).length} invitation(s) sent successfully
          </p>
          <p className="text-sm text-slate-500">Redirecting to team page...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-slate-800 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="font-bold text-lg">Invite Team Members</h1>
              <p className="text-sm text-slate-400">Add faculty to your NAAC accreditation team</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 bg-red-500/20 border border-red-500/50 rounded-lg p-4 flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Invitations List */}
          <div className="space-y-4 mb-6">
            {invitations.map((invitation, index) => (
              <div
                key={invitation.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium flex items-center gap-2">
                    <UserPlus className="w-5 h-5 text-orange-500" />
                    Invitation {index + 1}
                  </h3>
                  {invitations.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeInvitation(invitation.id)}
                      className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Name */}
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">Full Name *</label>
                    <input
                      type="text"
                      value={invitation.name}
                      onChange={(e) => updateInvitation(invitation.id, 'name', e.target.value)}
                      placeholder="Dr. John Doe"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-orange-500"
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">Email Address *</label>
                    <input
                      type="email"
                      value={invitation.email}
                      onChange={(e) => updateInvitation(invitation.id, 'email', e.target.value)}
                      placeholder="john.doe@college.edu"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-orange-500"
                    />
                  </div>

                  {/* Role */}
                  <div>
                    <label className="block text-sm text-slate-400 mb-1.5">Role *</label>
                    <select
                      value={invitation.role}
                      onChange={(e) => updateInvitation(invitation.id, 'role', e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-orange-500"
                    >
                      {NAAC_ROLES.map(role => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-slate-500 mt-1">
                      {NAAC_ROLES.find(r => r.value === invitation.role)?.description}
                    </p>
                  </div>

                  {/* Criterion (for criterion_head and data_entry) */}
                  {(invitation.role === 'criterion_head' || invitation.role === 'data_entry') && (
                    <div>
                      <label className="block text-sm text-slate-400 mb-1.5">
                        Assign to Criterion {invitation.role === 'criterion_head' && '*'}
                      </label>
                      <select
                        value={invitation.criterion || ''}
                        onChange={(e) => updateInvitation(invitation.id, 'criterion', e.target.value ? parseInt(e.target.value) : undefined)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 focus:outline-none focus:border-orange-500"
                      >
                        <option value="">Select Criterion</option>
                        {CRITERIA.map(c => (
                          <option key={c.number} value={c.number}>
                            Criterion {c.number}: {c.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Add More Button */}
          <button
            type="button"
            onClick={addInvitation}
            className="w-full flex items-center justify-center gap-2 p-4 border border-dashed border-slate-700 rounded-xl text-slate-400 hover:text-white hover:border-slate-500 transition-colors mb-6"
          >
            <Plus className="w-5 h-5" />
            Add Another Invitation
          </button>

          {/* Submit Button */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              {invitations.filter(inv => inv.email && inv.name).length} invitation(s) ready to send
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => router.back()}
                className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 rounded-lg font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSending}
                className="flex items-center gap-2 px-6 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 rounded-lg font-medium"
              >
                {isSending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Send Invitations
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Info Box */}
        <div className="mt-8 bg-slate-900/50 border border-slate-800 rounded-xl p-5">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <Mail className="w-5 h-5 text-orange-500" />
            How It Works
          </h3>
          <ul className="space-y-2 text-sm text-slate-400">
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 bg-slate-800 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">1</span>
              Invitees receive an email with a link to join
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 bg-slate-800 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">2</span>
              They create an account and set their password
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 bg-slate-800 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">3</span>
              They get access to their assigned criteria based on role
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 bg-slate-800 rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">4</span>
              You can manage their permissions from the Team page
            </li>
          </ul>
        </div>
      </main>
    </div>
  )
}
