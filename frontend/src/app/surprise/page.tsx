'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { SURPRISE_PROJECTS, THEMES, DIFFICULTIES, useAdventureStore } from '@/store/adventureStore'

export default function SurprisePage() {
  const router = useRouter()
  const [currentProject, setCurrentProject] = useState(SURPRISE_PROJECTS[0])
  const [isSpinning, setIsSpinning] = useState(false)
  const { startAdventure, setTheme, setDifficulty, setProjectName, setSelectedFeatures } = useAdventureStore()

  const spinAndSelect = () => {
    setIsSpinning(true)

    // Rapid cycling effect
    let count = 0
    const interval = setInterval(() => {
      const randomIndex = Math.floor(Math.random() * SURPRISE_PROJECTS.length)
      setCurrentProject(SURPRISE_PROJECTS[randomIndex])
      count++

      if (count > 15) {
        clearInterval(interval)
        setIsSpinning(false)
        // Final random selection
        const finalIndex = Math.floor(Math.random() * SURPRISE_PROJECTS.length)
        setCurrentProject(SURPRISE_PROJECTS[finalIndex])
      }
    }, 100)
  }

  const acceptProject = () => {
    // Pre-configure the adventure store with surprise project
    startAdventure()
    setTheme(currentProject.theme)
    setDifficulty(currentProject.difficulty)
    setProjectName(currentProject.name)
    setSelectedFeatures(currentProject.features)

    // Navigate to adventure page (will skip to features stage)
    router.push('/adventure')
  }

  const theme = THEMES.find(t => t.id === currentProject.theme)
  const difficulty = DIFFICULTIES.find(d => d.id === currentProject.difficulty)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-gray-900 flex items-center justify-center p-8">
      <div className="max-w-lg w-full">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <motion.div
            animate={isSpinning ? { rotate: 360 } : {}}
            transition={{ duration: 0.5, repeat: isSpinning ? Infinity : 0 }}
            className="text-7xl mb-4 inline-block"
          >
            🎁
          </motion.div>
          <h1 className="text-3xl font-bold text-white mb-2">Surprise Project!</h1>
          <p className="text-gray-400">Let fate decide your next project</p>
        </motion.div>

        {/* Project Card */}
        <motion.div
          key={currentProject.name}
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className={`
            bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl border-2 p-6
            ${isSpinning ? 'border-purple-500/50 shadow-lg shadow-purple-500/20' : 'border-yellow-500/50 shadow-lg shadow-yellow-500/20'}
            transition-all duration-300
          `}
        >
          {/* Project Icon & Name */}
          <div className="flex items-center gap-4 mb-4">
            <span className="text-5xl">{currentProject.icon}</span>
            <div>
              <h2 className="text-2xl font-bold text-white">{currentProject.name}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-lg">{theme?.icon}</span>
                <span className="text-gray-400 text-sm">{theme?.name}</span>
              </div>
            </div>
          </div>

          {/* Description */}
          <p className="text-gray-300 mb-6">{currentProject.description}</p>

          {/* Details */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-800/50 rounded-xl p-3">
              <div className="text-gray-400 text-xs mb-1">Difficulty</div>
              <div className="flex items-center gap-2">
                <span>{difficulty?.icon}</span>
                <span className="text-white font-medium">{difficulty?.name}</span>
              </div>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3">
              <div className="text-gray-400 text-xs mb-1">Features</div>
              <div className="text-white font-medium">{currentProject.features.length} included</div>
            </div>
          </div>

          {/* Features Preview */}
          <div className="flex flex-wrap gap-2 mb-6">
            {currentProject.features.map(feature => (
              <span
                key={feature}
                className="px-3 py-1 bg-cyan-500/20 border border-cyan-500/30 rounded-full text-cyan-400 text-xs"
              >
                {feature.replace('_', ' ')}
              </span>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={spinAndSelect}
              disabled={isSpinning}
              className={`
                flex-1 py-3 rounded-xl font-bold transition-all
                ${isSpinning
                  ? 'bg-purple-500/50 text-purple-300 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:shadow-lg hover:shadow-purple-500/30'
                }
              `}
            >
              {isSpinning ? '🎰 Spinning...' : '🎲 Spin Again'}
            </button>
            <button
              onClick={acceptProject}
              disabled={isSpinning}
              className="flex-1 py-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl font-bold text-white hover:shadow-lg hover:shadow-green-500/30 transition-all disabled:opacity-50"
            >
              ✨ Build This!
            </button>
          </div>
        </motion.div>

        {/* Back Link */}
        <div className="text-center mt-6">
          <button
            onClick={() => router.push('/adventure')}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ← Back to Adventure
          </button>
        </div>
      </div>
    </div>
  )
}
