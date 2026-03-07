'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Users,
  UserPlus,
  Mail,
  Shield,
  Edit2,
  Trash2,
  MoreVertical,
  CheckCircle2,
  Clock,
  XCircle,
  Search,
  Filter,
  Loader2
} from 'lucide-react'

interface TeamMember {
  id: string
  name: string
  email: string
  role: string
  roleLabel: string
  criterion?: number
  status: 'active' | 'pending' | 'inactive'
  joinedAt?: string
  lastActive?: string
}

const MOCK_TEAM: TeamMember[] = [
  {
    id: '1',
    name: 'Dr. Priya Sharma',
    email: 'priya.sharma@college.edu',
    role: 'iqac_coordinator',
    roleLabel: 'IQAC Coordinator',
    status: 'active',
    joinedAt: '2024-01-15',
    lastActive: '2 hours ago'
  },
  {
    id: '2',
    name: 'Prof. Anil Kumar',
    email: 'anil.kumar@college.edu',
    role: 'criterion_head',
    roleLabel: 'Criterion 1 Head',
    criterion: 1,
    status: 'active',
    joinedAt: '2024-01-20',
    lastActive: '1 day ago'
  },
  {
    id: '3',
    name: 'Dr. Sunita Rao',
    email: 'sunita.rao@college.edu',
    role: 'criterion_head',
    roleLabel: 'Criterion 2 Head',
    criterion: 2,
    status: 'active',
    joinedAt: '2024-01-20',
    lastActive: '3 hours ago'
  },
  {
    id: '4',
    name: 'Mr. Venkat Reddy',
    email: 'venkat@college.edu',
    role: 'data_entry',
    roleLabel: 'Data Entry',
    status: 'pending',
  },
  {
    id: '5',
    name: 'Dr. Meera Patel',
    email: 'meera@college.edu',
    role: 'faculty',
    roleLabel: 'Faculty',
    status: 'pending',
  },
]

export default function TeamPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [team, setTeam] = useState<TeamMember[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')

  useEffect(() => {
    loadTeam()
  }, [])

  const loadTeam = async () => {
    setIsLoading(true)
    try {
      // TODO: Replace with API call
      await new Promise(r => setTimeout(r, 500))
      setTeam(MOCK_TEAM)
    } finally {
      setIsLoading(false)
    }
  }

  const filteredTeam = team.filter(member => {
    const matchesSearch = member.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      member.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = filterStatus === 'all' || member.status === filterStatus
    return matchesSearch && matchesStatus
  })

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <span className="flex items-center gap-1 text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Active
          </span>
        )
      case 'pending':
        return (
          <span className="flex items-center gap-1 text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-full">
            <Clock className="w-3 h-3" />
            Pending
          </span>
        )
      default:
        return (
          <span className="flex items-center gap-1 text-xs bg-slate-500/20 text-slate-400 px-2 py-1 rounded-full">
            <XCircle className="w-3 h-3" />
            Inactive
          </span>
        )
    }
  }

  const activeCount = team.filter(m => m.status === 'active').length
  const pendingCount = team.filter(m => m.status === 'pending').length

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/accreditation/dashboard')}
                className="p-2 hover:bg-slate-800 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="font-bold text-lg">Team Management</h1>
                <p className="text-sm text-slate-400">Manage your NAAC accreditation team</p>
              </div>
            </div>

            <Link
              href="/accreditation/team/invite"
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg font-medium"
            >
              <UserPlus className="w-4 h-4" />
              Invite Member
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-2xl font-bold">{team.length}</div>
            <div className="text-sm text-slate-400">Total Members</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-2xl font-bold text-green-500">{activeCount}</div>
            <div className="text-sm text-slate-400">Active</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="text-2xl font-bold text-yellow-500">{pendingCount}</div>
            <div className="text-sm text-slate-400">Pending Invites</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:border-orange-500"
            />
          </div>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 focus:outline-none focus:border-orange-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        {/* Team List */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="text-left text-sm font-medium text-slate-400 px-4 py-3">Member</th>
                <th className="text-left text-sm font-medium text-slate-400 px-4 py-3">Role</th>
                <th className="text-left text-sm font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-left text-sm font-medium text-slate-400 px-4 py-3">Last Active</th>
                <th className="text-right text-sm font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTeam.map((member) => (
                <tr key={member.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/50">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center text-sm font-medium">
                        {member.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <div className="font-medium">{member.name}</div>
                        <div className="text-sm text-slate-400">{member.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-slate-400" />
                      <span>{member.roleLabel}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    {getStatusBadge(member.status)}
                  </td>
                  <td className="px-4 py-4 text-sm text-slate-400">
                    {member.lastActive || 'Never'}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {member.status === 'pending' && (
                        <button className="p-2 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white">
                          <Mail className="w-4 h-4" />
                        </button>
                      )}
                      <button className="p-2 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button className="p-2 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-red-400">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {filteredTeam.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No team members found</p>
            </div>
          )}
        </div>

        {/* Role Legend */}
        <div className="mt-6 bg-slate-900/50 border border-slate-800 rounded-xl p-5">
          <h3 className="font-medium mb-3">Role Permissions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
            <div className="flex items-start gap-2">
              <div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5" />
              <div>
                <span className="font-medium">IQAC Coordinator</span>
                <p className="text-slate-400 text-xs">Full access to all criteria and settings</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-1.5" />
              <div>
                <span className="font-medium">Criterion Head</span>
                <p className="text-slate-400 text-xs">Manage assigned criterion and approve data</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full mt-1.5" />
              <div>
                <span className="font-medium">Data Entry</span>
                <p className="text-slate-400 text-xs">Enter data for assigned indicators</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
