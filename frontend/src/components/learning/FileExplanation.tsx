'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileCode,
  CheckCircle2,
  Circle,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  BookOpen,
  Code2,
  AlertTriangle,
  ExternalLink,
  Loader2,
} from 'lucide-react'

export interface FileExplanationData {
  filePath: string
  simpleExplanation?: string
  technicalExplanation?: string
  keyConcepts: string[]
  analogies: string[]
  bestPractices: string[]
}

interface FileExplanationProps {
  file: {
    path: string
    content?: string
    language?: string
  }
  explanation?: FileExplanationData | null
  isUnderstood: boolean
  onMarkUnderstood: () => void
  loading?: boolean
}

export function FileExplanation({
  file,
  explanation,
  isUnderstood,
  onMarkUnderstood,
  loading = false,
}: FileExplanationProps) {
  const [expanded, setExpanded] = useState(false)
  const [showTechnical, setShowTechnical] = useState(false)

  // Get file icon based on extension
  const getFileIcon = (path: string) => {
    const ext = path.split('.').pop()?.toLowerCase()
    const iconClass = 'w-4 h-4'

    switch (ext) {
      case 'tsx':
      case 'jsx':
      case 'ts':
      case 'js':
        return <Code2 className={`${iconClass} text-blue-400`} />
      case 'py':
        return <FileCode className={`${iconClass} text-yellow-400`} />
      case 'css':
      case 'scss':
        return <FileCode className={`${iconClass} text-pink-400`} />
      default:
        return <FileCode className={`${iconClass} text-gray-400`} />
    }
  }

  // Get file name from path
  const fileName = file.path.split('/').pop() || file.path

  return (
    <div
      className={`rounded-xl border transition-all duration-300 ${
        isUnderstood
          ? 'border-green-500/50 bg-green-500/5'
          : expanded
          ? 'border-blue-500/50 bg-blue-500/5'
          : 'border-gray-700/50 bg-gray-800/30'
      }`}
    >
      {/* File Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors rounded-t-xl"
      >
        <div className="flex items-center gap-3">
          {getFileIcon(file.path)}
          <span
            className={`text-sm font-mono ${
              isUnderstood ? 'text-green-400' : 'text-gray-300'
            }`}
          >
            {fileName}
          </span>
          {isUnderstood && (
            <span className="px-2 py-0.5 text-[10px] rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
              Understood
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isUnderstood ? (
            <CheckCircle2 className="w-5 h-5 text-green-500" />
          ) : (
            <Circle className="w-5 h-5 text-gray-600" />
          )}
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-white/10 space-y-4">
              {/* Loading state */}
              {loading && (
                <div className="py-6 text-center">
                  <Loader2 className="w-6 h-6 text-blue-500 animate-spin mx-auto mb-2" />
                  <p className="text-sm text-gray-400">Generating explanation...</p>
                </div>
              )}

              {/* No explanation yet */}
              {!loading && !explanation && (
                <div className="py-4 text-center text-gray-500 text-sm">
                  <p>Explanation will be available when file is loaded.</p>
                </div>
              )}

              {/* Explanation content */}
              {!loading && explanation && (
                <>
                  {/* Simple Explanation */}
                  {explanation.simpleExplanation && (
                    <div className="pt-3">
                      <div className="flex items-center gap-2 text-sm font-medium text-blue-400 mb-2">
                        <Lightbulb className="w-4 h-4" />
                        <span>What This File Does</span>
                      </div>
                      <p className="text-sm text-gray-300 leading-relaxed">
                        {explanation.simpleExplanation}
                      </p>
                    </div>
                  )}

                  {/* Key Concepts */}
                  {explanation.keyConcepts.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 text-sm font-medium text-purple-400 mb-2">
                        <BookOpen className="w-4 h-4" />
                        <span>Key Concepts</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {explanation.keyConcepts.map((concept, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 text-xs rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          >
                            {concept}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Analogies */}
                  {explanation.analogies.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 text-sm font-medium text-yellow-400 mb-2">
                        <Lightbulb className="w-4 h-4" />
                        <span>Think of it like...</span>
                      </div>
                      <ul className="space-y-1">
                        {explanation.analogies.map((analogy, idx) => (
                          <li
                            key={idx}
                            className="text-sm text-gray-300 flex items-start gap-2"
                          >
                            <span className="text-yellow-500 mt-1">•</span>
                            <span>{analogy}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Best Practices */}
                  {explanation.bestPractices.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 text-sm font-medium text-green-400 mb-2">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Best Practices Used</span>
                      </div>
                      <ul className="space-y-1">
                        {explanation.bestPractices.map((practice, idx) => (
                          <li
                            key={idx}
                            className="text-sm text-gray-300 flex items-start gap-2"
                          >
                            <CheckCircle2 className="w-3 h-3 text-green-500 mt-1 flex-shrink-0" />
                            <span>{practice}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Technical Details Toggle */}
                  {explanation.technicalExplanation && (
                    <div>
                      <button
                        onClick={() => setShowTechnical(!showTechnical)}
                        className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      >
                        <Code2 className="w-4 h-4" />
                        <span>
                          {showTechnical ? 'Hide' : 'Show'} Technical Details
                        </span>
                        {showTechnical ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>

                      <AnimatePresence>
                        {showTechnical && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-2 p-3 rounded-lg bg-gray-900/50 border border-gray-700/50">
                              <p className="text-sm text-gray-400 leading-relaxed">
                                {explanation.technicalExplanation}
                              </p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )}
                </>
              )}

              {/* Mark as Understood Button */}
              {!isUnderstood && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onMarkUnderstood()
                  }}
                  className="w-full mt-4 py-2.5 px-4 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 text-white text-sm font-medium hover:from-green-600 hover:to-emerald-700 transition-all flex items-center justify-center gap-2"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  I Understand This File
                </button>
              )}

              {isUnderstood && (
                <div className="flex items-center justify-center gap-2 py-2 text-green-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Marked as understood</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

interface FileExplanationListProps {
  files: Array<{
    path: string
    content?: string
    language?: string
  }>
  explanations: Map<string, FileExplanationData>
  understoodFiles: string[]
  onMarkUnderstood: (filePath: string) => void
  onFetchExplanation?: (filePath: string) => void
  loadingFiles?: string[]
}

export function FileExplanationList({
  files,
  explanations,
  understoodFiles,
  onMarkUnderstood,
  onFetchExplanation,
  loadingFiles = [],
}: FileExplanationListProps) {
  // Filter to important files (skip configs, tests, etc.)
  const importantFiles = files.filter((f) => {
    const path = f.path.toLowerCase()
    const skipPatterns = [
      'node_modules',
      '__pycache__',
      '.git',
      'package-lock',
      'yarn.lock',
      '.env',
      'readme',
      'license',
      '.md',
      '.txt',
      '.json',
      '.yml',
      '.yaml',
      'test',
      'spec',
      '.d.ts',
    ]
    return !skipPatterns.some((pattern) => path.includes(pattern))
  })

  const understoodCount = understoodFiles.length
  const totalCount = Math.max(importantFiles.length, 5)
  const progress = Math.min(100, (understoodCount / totalCount) * 100)

  return (
    <div className="space-y-4">
      {/* Progress Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-400" />
          <span className="text-sm font-medium text-white">
            Code Understanding
          </span>
        </div>
        <span className="text-sm text-gray-400">
          {understoodCount} / {totalCount} files
        </span>
      </div>

      {/* Progress Bar */}
      <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Checkpoint Status */}
      {understoodCount >= 5 && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
          <CheckCircle2 className="w-5 h-5 text-green-500" />
          <span className="text-sm text-green-400">
            Checkpoint 1 Complete! You can now take the concept quiz.
          </span>
        </div>
      )}

      {/* Files List */}
      <div className="space-y-2">
        {importantFiles.slice(0, 15).map((file) => (
          <FileExplanation
            key={file.path}
            file={file}
            explanation={explanations.get(file.path)}
            isUnderstood={understoodFiles.includes(file.path)}
            onMarkUnderstood={() => onMarkUnderstood(file.path)}
            loading={loadingFiles.includes(file.path)}
          />
        ))}

        {importantFiles.length > 15 && (
          <p className="text-xs text-gray-500 text-center pt-2">
            +{importantFiles.length - 15} more files
          </p>
        )}

        {importantFiles.length === 0 && (
          <div className="py-8 text-center text-gray-500">
            <FileCode className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No code files to review yet</p>
          </div>
        )}
      </div>
    </div>
  )
}
