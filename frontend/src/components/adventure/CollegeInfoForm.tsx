'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAdventureStore, CollegeInfo } from '@/store/adventureStore'

export function CollegeInfoForm() {
  const { isCollegeProject, setCollegeInfo, nextStage, previousStage } = useAdventureStore()

  const [formData, setFormData] = useState<CollegeInfo>({
    studentName: '',
    rollNumber: '',
    collegeName: '',
    department: 'Computer Science and Engineering',
    guideName: '',
    hodName: '',
    principalName: '',
    academicYear: '2024-2025',
    teamMembers: [],
  })

  const [showTeamForm, setShowTeamForm] = useState(false)
  const [newMember, setNewMember] = useState({ name: '', roll: '' })

  // Skip if not a college project
  if (!isCollegeProject) {
    return (
      <div className="text-center py-12">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-6xl mb-4"
        >
          💼
        </motion.div>
        <h3 className="text-xl font-bold text-white mb-2">Personal/Commercial Project</h3>
        <p className="text-gray-400 mb-8">No college info needed. Let's build!</p>
        <div className="flex justify-center gap-4">
          <button
            onClick={previousStage}
            className="px-6 py-3 rounded-xl font-semibold text-gray-400 hover:text-white transition-colors"
          >
            ← Back
          </button>
          <button
            onClick={nextStage}
            className="px-8 py-4 rounded-xl font-bold bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:shadow-lg hover:shadow-cyan-500/30"
          >
            Start Building! 🚀
          </button>
        </div>
      </div>
    )
  }

  const handleChange = (field: keyof CollegeInfo, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const addTeamMember = () => {
    if (newMember.name.trim()) {
      setFormData(prev => ({
        ...prev,
        teamMembers: [...(prev.teamMembers || []), newMember]
      }))
      setNewMember({ name: '', roll: '' })
    }
  }

  const removeTeamMember = (index: number) => {
    setFormData(prev => ({
      ...prev,
      teamMembers: prev.teamMembers?.filter((_, i) => i !== index)
    }))
  }

  const handleSubmit = () => {
    setCollegeInfo(formData)
    nextStage()
  }

  const canProceed = formData.studentName && formData.rollNumber && formData.collegeName && formData.guideName

  const inputClass = "w-full p-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors"

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold text-white mb-2 flex items-center justify-center gap-2">
          <span className="text-3xl">🎓</span> College Info
          <span className="text-sm text-gray-400 font-normal">(30 seconds!)</span>
        </h3>
        <p className="text-gray-400">Quick details for your official IEEE documents</p>
      </div>

      <div className="space-y-6">
        {/* Personal Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">👤 Your Name *</label>
            <input
              type="text"
              value={formData.studentName}
              onChange={(e) => handleChange('studentName', e.target.value)}
              placeholder="Enter your name"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">🔢 Roll Number *</label>
            <input
              type="text"
              value={formData.rollNumber}
              onChange={(e) => handleChange('rollNumber', e.target.value)}
              placeholder="e.g., 20CS001"
              className={inputClass}
            />
          </div>
        </div>

        {/* College Info */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">🏫 College Name *</label>
          <input
            type="text"
            value={formData.collegeName}
            onChange={(e) => handleChange('collegeName', e.target.value)}
            placeholder="e.g., XYZ University of Technology"
            className={inputClass}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">📚 Department *</label>
            <input
              type="text"
              value={formData.department}
              onChange={(e) => handleChange('department', e.target.value)}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">📅 Academic Year</label>
            <input
              type="text"
              value={formData.academicYear}
              onChange={(e) => handleChange('academicYear', e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        {/* Guide Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">👨‍🏫 Guide Name *</label>
            <input
              type="text"
              value={formData.guideName}
              onChange={(e) => handleChange('guideName', e.target.value)}
              placeholder="Dr. Guide Name"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">👔 HOD Name</label>
            <input
              type="text"
              value={formData.hodName}
              onChange={(e) => handleChange('hodName', e.target.value)}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">🎖️ Principal Name</label>
            <input
              type="text"
              value={formData.principalName}
              onChange={(e) => handleChange('principalName', e.target.value)}
              placeholder="Optional"
              className={inputClass}
            />
          </div>
        </div>

        {/* Team Members */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm text-gray-400">👥 Team Members</label>
            <button
              onClick={() => setShowTeamForm(!showTeamForm)}
              className="text-cyan-400 text-sm hover:text-cyan-300"
            >
              {showTeamForm ? 'Hide' : '+ Add Members'}
            </button>
          </div>

          {/* Existing Members */}
          {formData.teamMembers && formData.teamMembers.length > 0 && (
            <div className="space-y-2 mb-3">
              {formData.teamMembers.map((member, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center justify-between bg-gray-800 p-3 rounded-lg"
                >
                  <span className="text-white">
                    {member.name} {member.roll && `(${member.roll})`}
                  </span>
                  <button
                    onClick={() => removeTeamMember(index)}
                    className="text-red-400 hover:text-red-300"
                  >
                    ✕
                  </button>
                </motion.div>
              ))}
            </div>
          )}

          {/* Add Member Form */}
          {showTeamForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={newMember.name}
                onChange={(e) => setNewMember(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Member name"
                className={`${inputClass} flex-1`}
              />
              <input
                type="text"
                value={newMember.roll}
                onChange={(e) => setNewMember(prev => ({ ...prev, roll: e.target.value }))}
                placeholder="Roll no."
                className={`${inputClass} w-32`}
              />
              <button
                onClick={addTeamMember}
                className="px-4 py-3 bg-cyan-500 text-white rounded-xl hover:bg-cyan-600"
              >
                Add
              </button>
            </motion.div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={previousStage}
          className="px-6 py-3 rounded-xl font-semibold text-gray-400 hover:text-white transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={handleSubmit}
          disabled={!canProceed}
          className={`
            px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300
            ${canProceed
              ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:shadow-lg hover:shadow-cyan-500/30 hover:scale-105'
              : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          Start Building! 🚀
        </button>
      </div>
    </div>
  )
}
