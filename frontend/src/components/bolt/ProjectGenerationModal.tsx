'use client'

import { useState } from 'react'
import { useProjectGeneration } from '@/hooks/useProjectGeneration'

interface ProjectGenerationModalProps {
  isOpen: boolean
  onClose: () => void
}

export const ProjectGenerationModal = ({ isOpen, onClose }: ProjectGenerationModalProps) => {
  const [description, setDescription] = useState('')
  const [projectName, setProjectName] = useState('')
  const { generateProject, isGenerating, progress, error } = useProjectGeneration()

  if (!isOpen) return null

  const handleGenerate = async () => {
    if (!description.trim()) {
      alert('Please enter a project description')
      return
    }

    await generateProject(description, projectName || undefined)
  }

  const handleClose = () => {
    if (!isGenerating) {
      setDescription('')
      setProjectName('')
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">
              Generate Project
            </h2>
            {!isGenerating && (
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {!isGenerating ? (
            <>
              {/* Project Name Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project Name (Optional)
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="my-awesome-project"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Description Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project Description *
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe your project... (e.g., 'Build a todo app with Next.js and FastAPI')"
                  rows={6}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>

              {/* Examples */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm font-medium text-blue-900 mb-2">
                  💡 Examples:
                </p>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• "Build a todo app with authentication using Next.js and FastAPI"</li>
                  <li>• "Create a blog website with admin panel and markdown support"</li>
                  <li>• "Build a real-time chat application with WebSocket support"</li>
                </ul>
              </div>
            </>
          ) : (
            <>
              {/* Progress Bar */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">Progress</span>
                  <span className="text-blue-600 font-semibold">{progress.percent}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${progress.percent}%` }}
                  />
                </div>
              </div>

              {/* Current Status */}
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Status:</p>
                <p className="text-base font-medium text-gray-900">{progress.message}</p>
                {progress.currentStep && (
                  <p className="text-sm text-gray-500 mt-1">
                    Current step: {progress.currentStep}
                  </p>
                )}
              </div>

              {/* Statistics */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <p className="text-sm text-green-600 mb-1">Files Created</p>
                  <p className="text-2xl font-bold text-green-900">{progress.filesCreated}</p>
                </div>
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <p className="text-sm text-purple-600 mb-1">Commands Executed</p>
                  <p className="text-2xl font-bold text-purple-900">{progress.commandsExecuted}</p>
                </div>
              </div>

              {/* Loading Animation */}
              <div className="flex items-center justify-center py-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
            </>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-red-900">Error</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
          {!isGenerating ? (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={!description.trim()}
                className="px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Generate Project
              </button>
            </>
          ) : (
            <button
              disabled
              className="px-6 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed"
            >
              Generating...
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
