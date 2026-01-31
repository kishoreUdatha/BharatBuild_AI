'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface FacultyProfile {
  id: string
  email: string
  full_name: string
  role: string
  avatar_url: string | null
  phone: string | null
  bio: string | null
  created_at: string
  last_login: string | null
  assignment: {
    id: string
    department_id: string
    department_name: string
    department_code: string
    designation: string
    specialization: string
    is_guide: boolean
    max_students: number
    current_students: number
    joined_at: string
  } | null
  assigned_labs: {
    id: string
    name: string
    code: string
    branch: string
    semester: string
  }[]
  panel_memberships: number
  is_guide: boolean
  max_students: number
  current_students: number
}

export default function FacultyProfilePage() {
  const router = useRouter()
  const [profile, setProfile] = useState<FacultyProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    bio: '',
    designation: '',
    specialization: ''
  })

  useEffect(() => {
    fetchProfile()
  }, [])

  const fetchProfile = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/faculty/profile`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setProfile(data)
        setFormData({
          full_name: data.full_name || '',
          phone: data.phone || '',
          bio: data.bio || '',
          designation: data.assignment?.designation || '',
          specialization: data.assignment?.specialization || ''
        })
      }
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/faculty/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      })
      if (res.ok) {
        const data = await res.json()
        setProfile(data)
        setEditing(false)
      }
    } catch (e) {
      console.error(e)
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="h-full">
      <div className="max-w-6xl mx-auto px-6 py-6">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-white font-semibold text-lg">Faculty Profile</h1>
            <p className="text-gray-500 text-xs">Manage your profile and view assignments</p>
          </div>
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Edit Profile
            </button>
          )}
        </div>
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Profile Card */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <div className="text-center">
                <div className="w-24 h-24 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-white text-3xl font-bold">
                    {profile?.full_name?.charAt(0) || profile?.email?.charAt(0) || 'F'}
                  </span>
                </div>
                {editing ? (
                  <input
                    type="text"
                    value={formData.full_name}
                    onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-center mb-2"
                    placeholder="Full Name"
                  />
                ) : (
                  <h2 className="text-white text-xl font-semibold">{profile?.full_name || 'Faculty Member'}</h2>
                )}
                <p className="text-gray-400 text-sm">{profile?.email}</p>
                <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${
                  profile?.role === 'hod' ? 'bg-purple-500/20 text-purple-400' :
                  profile?.role === 'principal' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-indigo-500/20 text-indigo-400'
                }`}>
                  {profile?.role?.toUpperCase()}
                </span>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-800 space-y-4">
                <div>
                  <label className="text-gray-500 text-xs">Phone</label>
                  {editing ? (
                    <input
                      type="text"
                      value={formData.phone}
                      onChange={(e) => setFormData({...formData, phone: e.target.value})}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mt-1"
                      placeholder="Phone number"
                    />
                  ) : (
                    <p className="text-white text-sm">{profile?.phone || 'Not set'}</p>
                  )}
                </div>
                <div>
                  <label className="text-gray-500 text-xs">Member Since</label>
                  <p className="text-white text-sm">
                    {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
                <div>
                  <label className="text-gray-500 text-xs">Last Login</label>
                  <p className="text-white text-sm">
                    {profile?.last_login ? new Date(profile.last_login).toLocaleString() : 'N/A'}
                  </p>
                </div>
              </div>

              {editing && (
                <div className="mt-6 flex gap-2">
                  <button
                    onClick={() => setEditing(false)}
                    className="flex-1 px-4 py-2 border border-gray-700 text-gray-400 hover:text-white rounded-lg text-sm"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center justify-center gap-2"
                  >
                    {saving && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                    Save
                  </button>
                </div>
              )}
            </div>

            {/* Quick Stats */}
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 text-center">
                <p className="text-3xl font-bold text-white">{profile?.assigned_labs?.length || 0}</p>
                <p className="text-gray-400 text-sm">Labs Assigned</p>
              </div>
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 text-center">
                <p className="text-3xl font-bold text-white">{profile?.current_students || 0}</p>
                <p className="text-gray-400 text-sm">Students Guided</p>
              </div>
            </div>
          </div>

          {/* Details Section */}
          <div className="lg:col-span-2 space-y-6">
            {/* Department & Assignment */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                Department Assignment
              </h3>
              {profile?.assignment ? (
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-gray-500 text-xs">Department</label>
                    <p className="text-white">{profile.assignment.department_name}</p>
                    <p className="text-gray-400 text-xs">Code: {profile.assignment.department_code}</p>
                  </div>
                  <div>
                    <label className="text-gray-500 text-xs">Designation</label>
                    {editing ? (
                      <input
                        type="text"
                        value={formData.designation}
                        onChange={(e) => setFormData({...formData, designation: e.target.value})}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mt-1"
                        placeholder="e.g., Assistant Professor"
                      />
                    ) : (
                      <p className="text-white">{profile.assignment.designation || 'Not set'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-gray-500 text-xs">Specialization</label>
                    {editing ? (
                      <input
                        type="text"
                        value={formData.specialization}
                        onChange={(e) => setFormData({...formData, specialization: e.target.value})}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mt-1"
                        placeholder="e.g., Machine Learning"
                      />
                    ) : (
                      <p className="text-white">{profile.assignment.specialization || 'Not set'}</p>
                    )}
                  </div>
                  <div>
                    <label className="text-gray-500 text-xs">Joined Department</label>
                    <p className="text-white">
                      {profile.assignment.joined_at ? new Date(profile.assignment.joined_at).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-400">No department assignment found</p>
              )}
            </div>

            {/* Roles */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
                Roles & Responsibilities
              </h3>
              <div className="flex flex-wrap gap-3">
                <span className="px-3 py-2 bg-indigo-500/20 text-indigo-400 rounded-lg text-sm">
                  Lecturer
                </span>
                {profile?.is_guide && (
                  <span className="px-3 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm">
                    Project Guide ({profile.current_students}/{profile.max_students} students)
                  </span>
                )}
                {(profile?.panel_memberships ?? 0) > 0 && (
                  <span className="px-3 py-2 bg-amber-500/20 text-amber-400 rounded-lg text-sm">
                    Review Panel Member ({profile?.panel_memberships} panels)
                  </span>
                )}
                {profile?.role === 'hod' && (
                  <span className="px-3 py-2 bg-purple-500/20 text-purple-400 rounded-lg text-sm">
                    Head of Department
                  </span>
                )}
              </div>
            </div>

            {/* Assigned Labs */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                Assigned Labs & Subjects
              </h3>
              {profile?.assigned_labs && profile.assigned_labs.length > 0 ? (
                <div className="grid md:grid-cols-2 gap-4">
                  {profile.assigned_labs.map((lab) => (
                    <div key={lab.id} className="bg-gray-800/50 rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-white font-medium">{lab.name}</h4>
                          <p className="text-gray-400 text-sm">Code: {lab.code}</p>
                        </div>
                        <span className="px-2 py-1 bg-cyan-500/20 text-cyan-400 rounded text-xs">
                          Sem {lab.semester?.replace('sem_', '')}
                        </span>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-gray-500 text-xs">{lab.branch?.toUpperCase()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400">No labs assigned yet</p>
              )}
            </div>

            {/* Bio */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
              <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Bio
              </h3>
              {editing ? (
                <textarea
                  value={formData.bio}
                  onChange={(e) => setFormData({...formData, bio: e.target.value})}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm h-32 resize-none"
                  placeholder="Write a brief bio about yourself..."
                />
              ) : (
                <p className="text-gray-300 whitespace-pre-wrap">
                  {profile?.bio || 'No bio added yet. Click Edit Profile to add one.'}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
