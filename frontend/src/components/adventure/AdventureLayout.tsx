'use client'

import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAdventureStore } from '@/store/adventureStore'
import { ThemeSelector } from './ThemeSelector'
import { SmartQuestions } from './SmartQuestions'
import { FeatureSelector } from './FeatureSelector'
import { CollegeInfoForm } from './CollegeInfoForm'
import { BuildProgress } from './BuildProgress'
import { CelebrationScreen } from './CelebrationScreen'

const STAGES = [
  { id: 1, name: 'Theme & Difficulty', icon: '🎨' },
  { id: 2, name: 'Smart Questions', icon: '💬' },
  { id: 3, name: 'Features & Style', icon: '⚡' },
  { id: 4, name: 'College Info', icon: '🎓' },
  { id: 5, name: 'Building', icon: '🚀' },
]

export function AdventureLayout() {
  const {
    currentStage,
    isBuilding,
    isComplete,
    showCelebration,
    startAdventure,
    startBuild,
  } = useAdventureStore()

  // Initialize adventure on mount
  useEffect(() => {
    startAdventure()
  }, [])

  // Start build when reaching stage 5
  useEffect(() => {
    if (currentStage === 5 && !isBuilding && !isComplete) {
      startBuild()
    }
  }, [currentStage, isBuilding, isComplete])

  // Show celebration screen when complete
  if (showCelebration) {
    return <CelebrationScreen />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🎮</span>
              <div>
                <h1 className="text-xl font-bold text-white">Project Adventure</h1>
                <p className="text-xs text-gray-400">Create projects the fun way!</p>
              </div>
            </div>

            {/* Stage Indicator */}
            <div className="hidden md:flex items-center gap-2">
              {STAGES.slice(0, 4).map((stage, index) => (
                <div key={stage.id} className="flex items-center">
                  <div
                    className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all
                      ${currentStage > stage.id
                        ? 'bg-green-500 text-white'
                        : currentStage === stage.id
                          ? 'bg-cyan-500 text-white'
                          : 'bg-gray-700 text-gray-400'
                      }
                    `}
                  >
                    {currentStage > stage.id ? '✓' : stage.id}
                  </div>
                  {index < 3 && (
                    <div
                      className={`
                        w-8 h-1 mx-1 rounded
                        ${currentStage > stage.id ? 'bg-green-500' : 'bg-gray-700'}
                      `}
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Mobile Stage */}
            <div className="md:hidden">
              <span className="text-cyan-400 font-bold">Stage {Math.min(currentStage, 4)}/4</span>
            </div>
          </div>
        </div>
      </header>

      {/* Stage Title */}
      {currentStage <= 4 && (
        <div className="text-center py-8">
          <motion.div
            key={currentStage}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <span className="text-5xl mb-4 block">{STAGES[currentStage - 1]?.icon}</span>
            <h2 className="text-2xl font-bold text-white">
              Stage {currentStage}: {STAGES[currentStage - 1]?.name}
            </h2>
          </motion.div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 pb-12">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStage}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            {currentStage === 1 && <ThemeSelector />}
            {currentStage === 2 && <SmartQuestions />}
            {currentStage === 3 && <FeatureSelector />}
            {currentStage === 4 && <CollegeInfoForm />}
            {currentStage === 5 && <BuildProgress />}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-gray-900/80 backdrop-blur-sm border-t border-gray-800 py-3">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between text-sm">
          <div className="text-gray-500">
            Powered by <span className="text-cyan-400">BharatBuild AI</span>
          </div>
          <div className="flex items-center gap-4">
            <button className="text-gray-400 hover:text-white transition-colors">
              Need Help?
            </button>
            <a href="/surprise" className="text-yellow-400 hover:text-yellow-300 transition-colors flex items-center gap-1">
              <span>🎁</span> Surprise Me!
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
