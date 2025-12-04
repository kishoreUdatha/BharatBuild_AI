'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAdventureStore, FEATURES, PERSONALITIES, Feature } from '@/store/adventureStore'

export function FeatureSelector() {
  const {
    selectedFeatures,
    toggleFeature,
    selectedPersonality,
    setPersonality,
    projectName,
    setProjectName,
    selectedTheme,
    selectedDifficulty,
    nextStage,
    previousStage,
  } = useAdventureStore()

  // Group features by category
  const featuresByCategory = FEATURES.reduce((acc, feature) => {
    if (!acc[feature.category]) acc[feature.category] = []
    // Filter by difficulty
    const difficultyOrder = { beginner: 1, intermediate: 2, expert: 3 }
    const selectedDiffLevel = difficultyOrder[selectedDifficulty || 'intermediate']
    const featureDiffLevel = difficultyOrder[feature.difficulty]
    if (featureDiffLevel <= selectedDiffLevel) {
      acc[feature.category].push(feature)
    }
    return acc
  }, {} as Record<string, Feature[]>)

  const categoryNames: Record<string, { name: string; icon: string }> = {
    authentication: { name: 'Authentication', icon: '🔐' },
    ui: { name: 'UI Features', icon: '🎨' },
    data: { name: 'Data Features', icon: '📊' },
    ai: { name: 'AI Features', icon: '🤖' },
    communication: { name: 'Communication', icon: '💬' },
  }

  const canProceed = selectedFeatures.length > 0 && selectedPersonality && projectName.trim()

  return (
    <div className="space-y-8">
      {/* Features Selection */}
      <div>
        <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
          <span className="text-2xl">⚡</span> Choose Your Superpowers
        </h3>
        <p className="text-gray-400 text-sm mb-4">
          Selected: {selectedFeatures.length} features
          {selectedFeatures.length >= 5 && <span className="text-yellow-400 ml-2">🏆 Feature Hunter!</span>}
          {selectedFeatures.length >= 10 && <span className="text-yellow-400 ml-2">💎 Feature King!</span>}
        </p>

        <div className="space-y-6">
          {Object.entries(featuresByCategory).map(([category, features]) => (
            <div key={category}>
              <h4 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
                {categoryNames[category]?.icon} {categoryNames[category]?.name}
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {features.map((feature, index) => (
                  <motion.button
                    key={feature.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.03 }}
                    onClick={() => toggleFeature(feature.id)}
                    className={`
                      p-3 rounded-xl border-2 text-left transition-all duration-200
                      ${selectedFeatures.includes(feature.id)
                        ? 'border-cyan-500 bg-cyan-500/20'
                        : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                      }
                    `}
                  >
                    <span className="text-lg mr-2">{feature.icon}</span>
                    <span className="text-white text-sm">{feature.name}</span>
                  </motion.button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* UI Personality */}
      <div>
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">🎭</span> Choose UI Personality
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {PERSONALITIES.map((personality, index) => (
            <motion.button
              key={personality.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              onClick={() => setPersonality(personality.id)}
              className={`
                relative p-4 rounded-xl border-2 text-left transition-all duration-300
                ${selectedPersonality === personality.id
                  ? 'border-purple-500 bg-purple-500/20 shadow-lg shadow-purple-500/20'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                }
              `}
            >
              <div className="text-3xl mb-2">{personality.icon}</div>
              <div className="font-semibold text-white text-sm">{personality.name}</div>
              <div className="text-xs text-gray-400 mt-1">{personality.style}</div>
              {/* Color Preview */}
              <div className="flex gap-1 mt-2">
                <div
                  className="w-4 h-4 rounded-full border border-gray-600"
                  style={{ backgroundColor: personality.colors.primary }}
                />
                <div
                  className="w-4 h-4 rounded-full border border-gray-600"
                  style={{ backgroundColor: personality.colors.bg }}
                />
              </div>
              {selectedPersonality === personality.id && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center"
                >
                  <span className="text-white text-xs">✓</span>
                </motion.div>
              )}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Project Name */}
      <div>
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">📝</span> Name Your Project
        </h3>
        <input
          type="text"
          value={projectName}
          onChange={(e) => setProjectName(e.target.value)}
          placeholder="e.g., MyAwesomeProject"
          className="w-full max-w-md p-4 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors"
        />
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <button
          onClick={previousStage}
          className="px-6 py-3 rounded-xl font-semibold text-gray-400 hover:text-white transition-colors"
        >
          ← Back
        </button>
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
          Continue →
        </button>
      </div>
    </div>
  )
}
