'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { useAdventureStore, THEMES, DIFFICULTIES, PERSONALITIES } from '@/store/adventureStore'
import Confetti from 'react-confetti'

export function CelebrationScreen() {
  const router = useRouter()
  const {
    projectName,
    selectedTheme,
    selectedDifficulty,
    selectedFeatures,
    selectedPersonality,
    achievements,
    isCollegeProject,
    resetAdventure,
  } = useAdventureStore()

  const [showConfetti, setShowConfetti] = useState(true)
  const [windowSize, setWindowSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    setWindowSize({ width: window.innerWidth, height: window.innerHeight })
    const timer = setTimeout(() => setShowConfetti(false), 5000)
    return () => clearTimeout(timer)
  }, [])

  const theme = THEMES.find(t => t.id === selectedTheme)
  const difficulty = DIFFICULTIES.find(d => d.id === selectedDifficulty)
  const personality = PERSONALITIES.find(p => p.id === selectedPersonality)
  const unlockedAchievements = achievements.filter(a => a.unlocked)

  const celebrationMessages = [
    "🎉 Your project is ready to conquer the world!",
    "🚀 Houston, we have a successful launch!",
    "✨ Magic complete! Your project awaits!",
    "🏆 Champion! You've built something amazing!",
  ]
  const celebrationMessage = celebrationMessages[Math.floor(Math.random() * celebrationMessages.length)]

  const handleAction = (action: string) => {
    switch (action) {
      case 'run':
        // Navigate to bolt page with project
        sessionStorage.setItem('adventureProject', JSON.stringify({
          name: projectName,
          theme: selectedTheme,
          features: selectedFeatures,
          personality: selectedPersonality,
        }))
        router.push('/bolt')
        break
      case 'download':
        // Trigger download (would need API integration)
        alert('Download feature coming soon!')
        break
      case 'docs':
        // Navigate to docs view
        router.push('/bolt')
        break
      case 'new':
        resetAdventure()
        break
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      {/* Confetti */}
      {showConfetti && (
        <Confetti
          width={windowSize.width}
          height={windowSize.height}
          recycle={false}
          numberOfPieces={500}
        />
      )}

      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="max-w-2xl w-full"
      >
        {/* Main Card */}
        <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-3xl border border-gray-700 p-8 shadow-2xl">
          {/* Celebration Header */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', bounce: 0.5 }}
              className="text-8xl mb-4"
            >
              🎮
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-cyan-400 mb-2"
            >
              {celebrationMessage}
            </motion.h1>
          </div>

          {/* Project Summary */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-gray-800/50 rounded-2xl p-6 mb-6"
          >
            <h2 className="text-2xl font-bold text-white mb-4">{projectName}</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{theme?.icon}</span>
                <div>
                  <div className="text-gray-400">Theme</div>
                  <div className="text-white font-medium">{theme?.name}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{difficulty?.icon}</span>
                <div>
                  <div className="text-gray-400">Difficulty</div>
                  <div className="text-white font-medium">{difficulty?.name}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{personality?.icon}</span>
                <div>
                  <div className="text-gray-400">UI Style</div>
                  <div className="text-white font-medium">{personality?.name}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">⚡</span>
                <div>
                  <div className="text-gray-400">Features</div>
                  <div className="text-white font-medium">{selectedFeatures.length} selected</div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Achievements */}
          {unlockedAchievements.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="mb-6"
            >
              <h3 className="text-sm text-gray-400 mb-3">Achievements Earned</h3>
              <div className="flex flex-wrap gap-2">
                {unlockedAchievements.map((achievement, index) => (
                  <motion.div
                    key={achievement.id}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.8 + index * 0.1 }}
                    className="bg-yellow-500/20 border border-yellow-500/50 rounded-full px-3 py-1 flex items-center gap-2"
                  >
                    <span>{achievement.icon}</span>
                    <span className="text-yellow-400 text-sm font-medium">{achievement.title}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Project Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.9 }}
            className="grid grid-cols-4 gap-4 mb-8"
          >
            <div className="text-center p-3 bg-gray-800/50 rounded-xl">
              <div className="text-2xl font-bold text-cyan-400">25+</div>
              <div className="text-xs text-gray-400">Files</div>
            </div>
            <div className="text-center p-3 bg-gray-800/50 rounded-xl">
              <div className="text-2xl font-bold text-green-400">2.5k</div>
              <div className="text-xs text-gray-400">Lines</div>
            </div>
            <div className="text-center p-3 bg-gray-800/50 rounded-xl">
              <div className="text-2xl font-bold text-purple-400">12</div>
              <div className="text-xs text-gray-400">APIs</div>
            </div>
            {isCollegeProject && (
              <div className="text-center p-3 bg-gray-800/50 rounded-xl">
                <div className="text-2xl font-bold text-orange-400">72</div>
                <div className="text-xs text-gray-400">Doc Pages</div>
              </div>
            )}
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1 }}
            className="grid grid-cols-2 gap-4"
          >
            <button
              onClick={() => handleAction('run')}
              className="p-4 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl font-bold text-white hover:shadow-lg hover:shadow-green-500/30 transition-all flex items-center justify-center gap-2"
            >
              <span>▶️</span> Run Project
            </button>
            <button
              onClick={() => handleAction('download')}
              className="p-4 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-bold text-white hover:shadow-lg hover:shadow-blue-500/30 transition-all flex items-center justify-center gap-2"
            >
              <span>📥</span> Download ZIP
            </button>
            <button
              onClick={() => handleAction('docs')}
              className="p-4 bg-gray-700 rounded-xl font-bold text-white hover:bg-gray-600 transition-all flex items-center justify-center gap-2"
            >
              <span>📄</span> View Docs
            </button>
            <button
              onClick={() => handleAction('new')}
              className="p-4 bg-gray-700 rounded-xl font-bold text-white hover:bg-gray-600 transition-all flex items-center justify-center gap-2"
            >
              <span>✨</span> New Adventure
            </button>
          </motion.div>
        </div>

        {/* Footer */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.3 }}
          className="text-center text-gray-500 mt-6"
        >
          Thanks for using Project Adventure! 🎮
        </motion.p>
      </motion.div>
    </div>
  )
}
