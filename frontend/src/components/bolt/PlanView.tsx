'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle2, Loader2, Circle, FileText, FileCode, Folder, ChevronRight, ChevronDown,
  Sparkles, Zap, Code2, Layers, Box, Rocket, Shield, Database,
  Palette, Settings, TestTube, BookOpen, Star, Clock, ArrowRight
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useProjectStore, ProjectFile } from '@/store/projectStore'

interface PlanViewProps {
  messageId?: string
}

interface TaskDetailsModalProps {
  task: {
    label: string
    status: 'pending' | 'active' | 'complete'
    description?: string
    details?: string
    taskNumber?: number
    icon?: string
    category?: string
    deliverables?: string
  }
  onClose: () => void
}

// Category colors and icons
const categoryConfig: Record<string, { color: string; bgColor: string; icon: any }> = {
  'Setup': { color: 'text-purple-500', bgColor: 'bg-purple-500/10', icon: Settings },
  'UI': { color: 'text-pink-500', bgColor: 'bg-pink-500/10', icon: Palette },
  'Features': { color: 'text-yellow-500', bgColor: 'bg-yellow-500/10', icon: Zap },
  'Backend': { color: 'text-blue-500', bgColor: 'bg-blue-500/10', icon: Database },
  'Auth': { color: 'text-green-500', bgColor: 'bg-green-500/10', icon: Shield },
  'Data': { color: 'text-cyan-500', bgColor: 'bg-cyan-500/10', icon: Layers },
  'Polish': { color: 'text-orange-500', bgColor: 'bg-orange-500/10', icon: Sparkles },
  'Testing': { color: 'text-red-500', bgColor: 'bg-red-500/10', icon: TestTube },
  'Finalize': { color: 'text-emerald-500', bgColor: 'bg-emerald-500/10', icon: Rocket },
  'Docs': { color: 'text-indigo-500', bgColor: 'bg-indigo-500/10', icon: BookOpen },
}

const getCategoryConfig = (category?: string) => {
  if (!category) return categoryConfig['Features']
  return categoryConfig[category] || categoryConfig['Features']
}

// Task Details Modal - Beautiful and Educational
function TaskDetailsModal({ task, onClose }: TaskDetailsModalProps) {
  const config = getCategoryConfig(task.category)
  const CategoryIcon = config.icon

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9, y: 20 }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-[#1a1a2e] rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-white/10"
      >
        {/* Header with gradient */}
        <div className="relative px-6 py-5 bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-cyan-600/20">
          <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent" />
          <div className="relative flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-xl ${config.bgColor} flex items-center justify-center`}>
                {task.icon ? (
                  <span className="text-2xl">{task.icon}</span>
                ) : (
                  <CategoryIcon className={`w-7 h-7 ${config.color}`} />
                )}
              </div>
              <div>
                <div className={`text-xs font-medium ${config.color} uppercase tracking-wider mb-1`}>
                  {task.category || 'Task'}
                </div>
                <h2 className="text-xl font-bold text-white">
                  {task.label}
                </h2>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
            >
              <svg className="w-4 h-4 text-white/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-5">
          {/* Status Badge */}
          <div className="flex items-center gap-3">
            <div className={`px-3 py-1.5 rounded-full text-sm font-medium flex items-center gap-2 ${
              task.status === 'complete'
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : task.status === 'active'
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
            }`}>
              {task.status === 'complete' ? (
                <><CheckCircle2 className="w-4 h-4" /> Completed</>
              ) : task.status === 'active' ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> In Progress</>
              ) : (
                <><Circle className="w-4 h-4" /> Pending</>
              )}
            </div>
            {task.taskNumber && (
              <span className="text-xs text-gray-500">Step {task.taskNumber}</span>
            )}
          </div>

          {/* Description */}
          {task.description && (
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-300 mb-2">
                <FileText className="w-4 h-4" />
                Description
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                {task.description}
              </p>
            </div>
          )}

          {/* Deliverables */}
          {task.deliverables && (
            <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/20">
              <div className="flex items-center gap-2 text-sm font-medium text-purple-300 mb-3">
                <Box className="w-4 h-4" />
                Deliverables
              </div>
              <div className="flex flex-wrap gap-2">
                {task.deliverables.split(',').map((item, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1.5 rounded-lg bg-white/10 text-xs text-gray-300 font-mono"
                  >
                    {item.trim()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Details (from completion) */}
          {task.details && (
            <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20">
              <div className="flex items-center gap-2 text-sm font-medium text-green-300 mb-2">
                <CheckCircle2 className="w-4 h-4" />
                Completion Details
              </div>
              <div className="text-sm text-gray-300 prose prose-sm prose-invert max-w-none">
                <div dangerouslySetInnerHTML={{ __html: task.details.replace(/\n/g, '<br/>') }} />
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 bg-white/5">
          <div className="flex items-center justify-between">
            <div className={`flex items-center gap-2 text-sm ${
              task.status === 'complete' ? 'text-green-400' :
              task.status === 'active' ? 'text-blue-400' :
              'text-gray-500'
            }`}>
              {task.status === 'complete' ? (
                <><Sparkles className="w-4 h-4" /> Task completed successfully!</>
              ) : task.status === 'active' ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
              ) : (
                <><Clock className="w-4 h-4" /> Waiting to start</>
              )}
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// Project Overview Card Component
function ProjectOverviewCard({
  projectName,
  projectDescription,
  projectType,
  complexity,
  estimatedFiles,
  techStack,
  features
}: {
  projectName?: string
  projectDescription?: string
  projectType?: string
  complexity?: string
  estimatedFiles?: string
  techStack?: { name: string; items: string }[]
  features?: { icon: string; name: string; description: string }[]
}) {
  if (!projectName) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 p-5 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-white/10 shadow-xl"
    >
      {/* Project Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <Rocket className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">{projectName}</h2>
            {projectType && (
              <span className="text-xs text-purple-400 font-medium">{projectType}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {complexity && (
            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
              complexity === 'Simple' ? 'bg-green-500/20 text-green-400' :
              complexity === 'Intermediate' ? 'bg-yellow-500/20 text-yellow-400' :
              complexity === 'Advanced' ? 'bg-orange-500/20 text-orange-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {complexity}
            </span>
          )}
          {estimatedFiles && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400">
              ~{estimatedFiles} files
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      {projectDescription && (
        <p className="text-sm text-gray-400 mb-4 leading-relaxed">
          {projectDescription}
        </p>
      )}

      {/* Tech Stack */}
      {techStack && techStack.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Tech Stack</div>
          <div className="flex flex-wrap gap-2">
            {techStack.map((tech, idx) => (
              <div key={idx} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 border border-white/10">
                <Code2 className="w-3 h-3 text-gray-400" />
                <span className="text-xs text-gray-300">{tech.name}:</span>
                <span className="text-xs text-gray-400">{tech.items}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Features */}
      {features && features.length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Features</div>
          <div className="grid grid-cols-2 gap-2">
            {features.map((feature, idx) => (
              <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-white/5">
                <span className="text-base">{feature.icon}</span>
                <div>
                  <div className="text-xs font-medium text-gray-300">{feature.name}</div>
                  <div className="text-[10px] text-gray-500">{feature.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}

export function PlanView({ messageId }: PlanViewProps) {
  const messages = useChatStore((state) => state.messages)
  const [selectedTask, setSelectedTask] = useState<any>(null)
  const [isCodeGenExpanded, setIsCodeGenExpanded] = useState(true)

  // Get project store functions for file navigation
  const { openTab, currentProject } = useProjectStore()

  // Helper function to find file content from project
  const findFileInProject = (path: string): ProjectFile | null => {
    if (!currentProject?.files) return null

    const searchInFiles = (files: ProjectFile[]): ProjectFile | null => {
      for (const file of files) {
        if (file.path === path) return file
        if (file.children) {
          const found = searchInFiles(file.children)
          if (found) return found
        }
      }
      return null
    }

    return searchInFiles(currentProject.files)
  }

  // Handle file click to navigate to editor
  const handleFileClick = (filePath: string) => {
    const file = findFileInProject(filePath)
    if (file && file.type === 'file') {
      openTab(file)
    }
  }

  // Find the message to display plan for
  const targetMessage = messageId
    ? messages.find(m => m.id === messageId)
    : messages.filter(m => m.type === 'assistant').slice(-1)[0]

  if (!targetMessage || targetMessage.type !== 'assistant') {
    return null
  }

  const { thinkingSteps = [], fileOperations = [], planData } = targetMessage

  // Calculate progress
  const completedTasks = thinkingSteps.filter(s => s.status === 'complete').length
  const totalTasks = thinkingSteps.length
  const progressPercent = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 space-y-4">
        {/* Project Overview Card */}
        {planData && (
          <ProjectOverviewCard
            projectName={planData.projectName}
            projectDescription={planData.projectDescription}
            projectType={planData.projectType}
            complexity={planData.complexity}
            estimatedFiles={planData.estimatedFiles}
            techStack={planData.techStack}
            features={planData.features}
          />
        )}

        {/* Progress Bar */}
        {thinkingSteps.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-4"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-400">Progress</span>
              <span className="text-xs text-gray-500">{completedTasks}/{totalTasks} tasks</span>
            </div>
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="h-full rounded-full bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500"
              />
            </div>
          </motion.div>
        )}

        {/* Tasks Section */}
        {thinkingSteps.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
              <Layers className="w-4 h-4 text-purple-500" />
              Implementation Steps
            </h3>

            <AnimatePresence mode="popLayout">
              {thinkingSteps.map((step, idx) => {
                const config = getCategoryConfig(step.category)
                const CategoryIcon = config.icon

                return (
                  <motion.div
                    key={`step-${idx}-${step.label}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.3, delay: idx * 0.05 }}
                    onClick={() => setSelectedTask({ ...step, taskNumber: idx + 1 })}
                    className={`group p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                      step.status === 'complete'
                        ? 'bg-green-500/10 border-green-500/30 hover:bg-green-500/15'
                        : step.status === 'active'
                        ? 'bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/15'
                        : 'bg-white/5 border-white/10 hover:bg-white/10'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      {/* Step number with icon */}
                      <div className={`relative w-10 h-10 rounded-xl ${config.bgColor} flex items-center justify-center flex-shrink-0`}>
                        {step.icon ? (
                          <span className="text-lg">{step.icon}</span>
                        ) : (
                          <CategoryIcon className={`w-5 h-5 ${config.color}`} />
                        )}
                        {/* Step number badge */}
                        <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#1a1a2e] border border-white/20 flex items-center justify-center">
                          <span className="text-[10px] font-bold text-white">{idx + 1}</span>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {step.category && (
                            <span className={`text-[10px] font-medium ${config.color} uppercase tracking-wider`}>
                              {step.category}
                            </span>
                          )}
                        </div>
                        <h4 className={`text-sm font-semibold truncate ${
                          step.status === 'complete' ? 'text-green-400' :
                          step.status === 'active' ? 'text-blue-400' :
                          'text-white'
                        }`}>
                          {step.label}
                        </h4>
                        {step.description && (
                          <p className="text-xs text-gray-500 mt-0.5 truncate">
                            {step.description}
                          </p>
                        )}
                      </div>

                      {/* Status */}
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {step.status === 'complete' ? (
                          <CheckCircle2 className="w-5 h-5 text-green-500" />
                        ) : step.status === 'active' ? (
                          <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                        ) : (
                          <Circle className="w-5 h-5 text-gray-600" />
                        )}
                        <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
                      </div>
                    </div>

                    {/* Deliverables preview */}
                    {step.deliverables && step.status !== 'pending' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="mt-3 pt-3 border-t border-white/10"
                      >
                        <div className="flex flex-wrap gap-1.5">
                          {step.deliverables.split(',').slice(0, 4).map((item: string, i: number) => (
                            <span key={i} className="px-2 py-0.5 rounded text-[10px] bg-white/10 text-gray-400 font-mono">
                              {item.trim()}
                            </span>
                          ))}
                          {step.deliverables.split(',').length > 4 && (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-white/10 text-gray-500">
                              +{step.deliverables.split(',').length - 4} more
                            </span>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        )}

        {/* Code Generation Section - Collapsible Task Step */}
        {fileOperations.length > 0 && (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="mt-2"
          >
            {/* Collapsible Header - Looks like a task step */}
            <div
              onClick={() => setIsCodeGenExpanded(!isCodeGenExpanded)}
              className={`group p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                fileOperations.every(f => f.status === 'complete')
                  ? 'bg-green-500/10 border-green-500/30 hover:bg-green-500/15'
                  : fileOperations.some(f => f.status === 'in-progress')
                  ? 'bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/15'
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center gap-4">
                {/* Icon with step number */}
                <div className="relative w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
                  <Code2 className="w-5 h-5 text-cyan-500" />
                  <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#1a1a2e] border border-white/20 flex items-center justify-center">
                    <span className="text-[10px] font-bold text-white">{thinkingSteps.length + 1}</span>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-medium text-cyan-500 uppercase tracking-wider">
                      Code Generation
                    </span>
                  </div>
                  <h4 className={`text-sm font-semibold ${
                    fileOperations.every(f => f.status === 'complete') ? 'text-green-400' :
                    fileOperations.some(f => f.status === 'in-progress') ? 'text-blue-400' :
                    'text-white'
                  }`}>
                    Generated Files
                  </h4>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {fileOperations.filter(f => f.status === 'complete').length}/{fileOperations.length} files completed
                  </p>
                </div>

                {/* Status & Expand/Collapse */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {fileOperations.every(f => f.status === 'complete') ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  ) : fileOperations.some(f => f.status === 'in-progress') ? (
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  ) : (
                    <Circle className="w-5 h-5 text-gray-600" />
                  )}
                  {isCodeGenExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400 transition-colors" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
                  )}
                </div>
              </div>
            </div>

            {/* Collapsible Files List */}
            <AnimatePresence>
              {isCodeGenExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="ml-6 mt-2 space-y-1.5 border-l-2 border-cyan-500/20 pl-4"
                >
                  {fileOperations.map((op, idx) => (
                    <motion.div
                      key={`file-${idx}-${op.path}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.2, delay: idx * 0.02 }}
                      onClick={() => op.status === 'complete' && handleFileClick(op.path)}
                      className={`flex items-center gap-3 p-2.5 rounded-lg border transition-all ${
                        op.status === 'complete'
                          ? 'bg-green-500/5 border-green-500/20 cursor-pointer hover:bg-green-500/10 hover:border-green-500/30'
                          : op.status === 'in-progress'
                          ? 'bg-blue-500/5 border-blue-500/20'
                          : op.status === 'error'
                          ? 'bg-red-500/5 border-red-500/20'
                          : 'bg-white/5 border-white/10'
                      }`}
                    >
                      {/* File icon */}
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        op.status === 'complete' ? 'bg-green-500/20' :
                        op.status === 'in-progress' ? 'bg-blue-500/20' :
                        'bg-white/10'
                      }`}>
                        {op.path.endsWith('.tsx') || op.path.endsWith('.jsx') ? (
                          <Code2 className={`w-4 h-4 ${
                            op.status === 'complete' ? 'text-green-400' :
                            op.status === 'in-progress' ? 'text-blue-400' :
                            'text-gray-400'
                          }`} />
                        ) : op.path.endsWith('.css') ? (
                          <Palette className={`w-4 h-4 ${
                            op.status === 'complete' ? 'text-green-400' :
                            op.status === 'in-progress' ? 'text-blue-400' :
                            'text-gray-400'
                          }`} />
                        ) : op.path.includes('/') ? (
                          <Folder className={`w-4 h-4 ${
                            op.status === 'complete' ? 'text-green-400' :
                            op.status === 'in-progress' ? 'text-blue-400' :
                            'text-gray-400'
                          }`} />
                        ) : (
                          <FileText className={`w-4 h-4 ${
                            op.status === 'complete' ? 'text-green-400' :
                            op.status === 'in-progress' ? 'text-blue-400' :
                            'text-gray-400'
                          }`} />
                        )}
                      </div>

                      {/* File path */}
                      <div className="flex-1 min-w-0">
                        <span className={`text-xs font-mono truncate block ${
                          op.status === 'complete' ? 'text-gray-300 hover:text-cyan-400' : 'text-gray-300'
                        }`}>
                          {op.path}
                        </span>
                        {op.description && (
                          <span className="text-[10px] text-gray-500 truncate block">
                            {op.description}
                          </span>
                        )}
                      </div>

                      {/* Status indicator & click hint */}
                      <div className="flex items-center gap-2">
                        {op.status === 'complete' && (
                          <span className="text-[10px] text-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity">
                            Click to edit
                          </span>
                        )}
                        {op.status === 'complete' ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                        ) : op.status === 'in-progress' ? (
                          <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
                        ) : op.status === 'error' ? (
                          <Circle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        ) : (
                          <Circle className="w-4 h-4 text-gray-600 flex-shrink-0" />
                        )}
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

        {/* Empty State - Simple and clear */}
        {thinkingSteps.length === 0 && fileOperations.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-8"
          >
            <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mx-auto mb-3">
              <Sparkles className="w-6 h-6 text-gray-500" />
            </div>
            <p className="text-sm text-gray-500">
              No tasks yet. Start by describing your project.
            </p>
          </motion.div>
        )}

        {/* Task Details Modal */}
        <AnimatePresence>
          {selectedTask && (
            <TaskDetailsModal
              task={selectedTask}
              onClose={() => setSelectedTask(null)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
