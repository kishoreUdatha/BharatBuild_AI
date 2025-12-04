'use client'

import { motion } from 'framer-motion'
import { useAdventureStore, THEMES, DIFFICULTIES, ThemeConfig, DifficultyConfig } from '@/store/adventureStore'

export function ThemeSelector() {
  const { selectedTheme, selectedDifficulty, setTheme, setDifficulty, nextStage } = useAdventureStore()

  const canProceed = selectedTheme && selectedDifficulty

  return (
    <div className="space-y-8">
      {/* Theme Selection */}
      <div>
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">🎨</span> Pick Your Project Theme
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {THEMES.map((theme, index) => (
            <motion.button
              key={theme.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => setTheme(theme.id)}
              className={`
                relative p-4 rounded-xl border-2 transition-all duration-300
                ${selectedTheme === theme.id
                  ? 'border-cyan-500 bg-cyan-500/20 shadow-lg shadow-cyan-500/20'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
                }
              `}
            >
              <div className="text-4xl mb-2">{theme.icon}</div>
              <div className="font-semibold text-white text-sm">{theme.name}</div>
              <div className="text-xs text-gray-400 mt-1">{theme.description}</div>
              {selectedTheme === theme.id && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-cyan-500 rounded-full flex items-center justify-center"
                >
                  <span className="text-white text-xs">✓</span>
                </motion.div>
              )}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Difficulty Selection */}
      <div>
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">📊</span> Choose Difficulty Level
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {DIFFICULTIES.map((diff, index) => (
            <motion.button
              key={diff.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + index * 0.1 }}
              onClick={() => setDifficulty(diff.id)}
              className={`
                relative p-6 rounded-xl border-2 transition-all duration-300 text-left
                ${selectedDifficulty === diff.id
                  ? 'border-green-500 bg-green-500/20 shadow-lg shadow-green-500/20'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
                }
              `}
            >
              <div className="flex items-center gap-3 mb-3">
                <span className="text-3xl">{diff.icon}</span>
                <span className="font-bold text-white text-lg">{diff.name}</span>
              </div>
              <p className="text-gray-400 text-sm mb-3">{diff.description}</p>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Files:</span>
                  <span className="text-gray-300">{diff.fileCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Complexity:</span>
                  <span className="text-gray-300">{diff.complexity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Time:</span>
                  <span className="text-gray-300">{diff.estimatedTime}</span>
                </div>
              </div>
              {selectedDifficulty === diff.id && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center"
                >
                  <span className="text-white text-xs">✓</span>
                </motion.div>
              )}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Continue Button */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: canProceed ? 1 : 0.5 }}
        className="flex justify-center"
      >
        <button
          onClick={() => canProceed && nextStage()}
          disabled={!canProceed}
          className={`
            px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300
            ${canProceed
              ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:shadow-lg hover:shadow-cyan-500/30 hover:scale-105'
              : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          Continue to Questions →
        </button>
      </motion.div>
    </div>
  )
}
