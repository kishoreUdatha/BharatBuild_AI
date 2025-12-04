'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAdventureStore } from '@/store/adventureStore'

export function BuildProgress() {
  const {
    buildPhases,
    currentBuildMessage,
    achievements,
    updateBuildPhase,
    setBuildMessage,
    completeBuild,
    setShowCelebration,
  } = useAdventureStore()

  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0)
  const [messageIndex, setMessageIndex] = useState(0)

  // Simulate build progress
  useEffect(() => {
    const runBuild = async () => {
      for (let i = 0; i < buildPhases.length; i++) {
        const phase = buildPhases[i]
        setCurrentPhaseIndex(i)
        updateBuildPhase(phase.id, 'in_progress', 0)

        // Show each message in the phase
        for (let j = 0; j < phase.messages.length; j++) {
          setBuildMessage(phase.messages[j])
          setMessageIndex(j)

          // Update progress
          const progress = ((j + 1) / phase.messages.length) * 100
          updateBuildPhase(phase.id, 'in_progress', progress)

          // Wait between messages
          await new Promise(resolve => setTimeout(resolve, 800))
        }

        // Mark phase complete
        updateBuildPhase(phase.id, 'complete', 100)
        await new Promise(resolve => setTimeout(resolve, 300))
      }

      // Build complete!
      completeBuild()
      await new Promise(resolve => setTimeout(resolve, 500))
      setShowCelebration(true)
    }

    runBuild()
  }, [])

  const totalProgress = buildPhases.reduce((acc, phase) => {
    if (phase.status === 'complete') return acc + (100 / buildPhases.length)
    if (phase.status === 'in_progress') return acc + (phase.progress / buildPhases.length)
    return acc
  }, 0)

  // Get recently unlocked achievements
  const unlockedAchievements = achievements.filter(a => a.unlocked)

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          className="text-6xl inline-block mb-4"
        >
          🚀
        </motion.div>
        <h2 className="text-3xl font-bold text-white mb-2">Building Your Project</h2>
        <p className="text-gray-400">Watch the magic happen!</p>
      </div>

      {/* Overall Progress */}
      <div className="mb-8">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-400">Overall Progress</span>
          <span className="text-cyan-400 font-bold">{Math.round(totalProgress)}%</span>
        </div>
        <div className="h-4 bg-gray-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${totalProgress}%` }}
            className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500"
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Current Message */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentBuildMessage}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="text-center py-8"
        >
          <p className="text-2xl text-white font-medium">{currentBuildMessage}</p>
        </motion.div>
      </AnimatePresence>

      {/* Phase Progress */}
      <div className="space-y-4">
        {buildPhases.map((phase, index) => (
          <motion.div
            key={phase.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`
              p-4 rounded-xl border transition-all duration-300
              ${phase.status === 'complete'
                ? 'bg-green-500/10 border-green-500/50'
                : phase.status === 'in_progress'
                  ? 'bg-cyan-500/10 border-cyan-500/50'
                  : 'bg-gray-800/50 border-gray-700'
              }
            `}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3">
                <span className="text-2xl">
                  {phase.status === 'complete' ? '✅' :
                   phase.status === 'in_progress' ? '⚡' : '⏳'}
                </span>
                <span className={`font-semibold ${
                  phase.status === 'complete' ? 'text-green-400' :
                  phase.status === 'in_progress' ? 'text-cyan-400' : 'text-gray-400'
                }`}>
                  {phase.name}
                </span>
              </div>
              <span className="text-sm text-gray-400">
                {phase.status === 'complete' ? '100%' :
                 phase.status === 'in_progress' ? `${Math.round(phase.progress)}%` : 'Waiting...'}
              </span>
            </div>
            {phase.status === 'in_progress' && (
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${phase.progress}%` }}
                  className="h-full bg-cyan-500"
                />
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Achievement Toasts */}
      <div className="fixed bottom-8 right-8 space-y-2">
        <AnimatePresence>
          {unlockedAchievements.slice(-3).map((achievement, index) => (
            <motion.div
              key={achievement.id}
              initial={{ opacity: 0, x: 100, scale: 0.8 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.8 }}
              transition={{ delay: index * 0.2 }}
              className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/50 p-4 rounded-xl flex items-center gap-3"
            >
              <span className="text-3xl">{achievement.icon}</span>
              <div>
                <div className="text-yellow-400 font-bold text-sm">Achievement Unlocked!</div>
                <div className="text-white">{achievement.title}</div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
