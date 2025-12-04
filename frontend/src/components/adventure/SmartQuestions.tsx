'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAdventureStore, SMART_QUESTIONS } from '@/store/adventureStore'

export function SmartQuestions() {
  const { answers, setAnswer, setIsCollegeProject, nextStage, previousStage } = useAdventureStore()
  const [currentQuestion, setCurrentQuestion] = useState(0)

  const question = SMART_QUESTIONS[currentQuestion]
  const isLastQuestion = currentQuestion === SMART_QUESTIONS.length - 1
  const currentAnswer = answers[question.id]

  const handleAnswer = (value: any) => {
    setAnswer(question.id, value)
    if (question.id === 'is_college') {
      setIsCollegeProject(value === true)
    }
  }

  const handleNext = () => {
    if (isLastQuestion) {
      nextStage()
    } else {
      setCurrentQuestion(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1)
    } else {
      previousStage()
    }
  }

  const canProceed = currentAnswer !== undefined && currentAnswer !== '' &&
    (question.type !== 'multi_choice' || (Array.isArray(currentAnswer) && currentAnswer.length > 0))

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex justify-between text-sm text-gray-400 mb-2">
          <span>Question {currentQuestion + 1} of {SMART_QUESTIONS.length}</span>
          <span>{Math.round(((currentQuestion + 1) / SMART_QUESTIONS.length) * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${((currentQuestion + 1) / SMART_QUESTIONS.length) * 100}%` }}
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
          />
        </div>
      </div>

      {/* Question */}
      <motion.div
        key={question.id}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="space-y-6"
      >
        <h3 className="text-2xl font-bold text-white">{question.question}</h3>

        {/* Text Input */}
        {question.type === 'text' && (
          <input
            type="text"
            value={currentAnswer || ''}
            onChange={(e) => handleAnswer(e.target.value)}
            placeholder={question.placeholder}
            className="w-full p-4 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 transition-colors"
          />
        )}

        {/* Single Choice */}
        {question.type === 'choice' && question.options && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {question.options.map((option, index) => (
              <motion.button
                key={String(option.value)}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onClick={() => handleAnswer(option.value)}
                className={`
                  p-4 rounded-xl border-2 text-left transition-all duration-300
                  ${currentAnswer === option.value
                    ? 'border-cyan-500 bg-cyan-500/20'
                    : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{option.icon}</span>
                  <div>
                    <div className="font-semibold text-white">{option.label}</div>
                    {option.description && (
                      <div className="text-sm text-gray-400">{option.description}</div>
                    )}
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        )}

        {/* Multi Choice */}
        {question.type === 'multi_choice' && question.options && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {question.options.map((option, index) => {
              const selectedValues = Array.isArray(currentAnswer) ? currentAnswer : []
              const isSelected = selectedValues.includes(option.value)

              return (
                <motion.button
                  key={String(option.value)}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => {
                    const newValues = isSelected
                      ? selectedValues.filter((v: any) => v !== option.value)
                      : [...selectedValues, option.value]
                    handleAnswer(newValues)
                  }}
                  className={`
                    p-3 rounded-xl border-2 transition-all duration-300
                    ${isSelected
                      ? 'border-cyan-500 bg-cyan-500/20'
                      : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
                    }
                  `}
                >
                  <span className="text-xl mr-2">{option.icon}</span>
                  <span className="text-white text-sm">{option.label}</span>
                </motion.button>
              )
            })}
          </div>
        )}
      </motion.div>

      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={handlePrev}
          className="px-6 py-3 rounded-xl font-semibold text-gray-400 hover:text-white transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={handleNext}
          disabled={!canProceed}
          className={`
            px-8 py-3 rounded-xl font-bold transition-all duration-300
            ${canProceed
              ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:shadow-lg hover:shadow-cyan-500/30'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }
          `}
        >
          {isLastQuestion ? 'Continue to Features →' : 'Next →'}
        </button>
      </div>
    </div>
  )
}
