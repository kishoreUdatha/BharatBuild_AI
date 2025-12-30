'use client'

import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  ListChecks,
  Hammer,
  FileStack,
  CheckCircle2,
  Loader2,
  Circle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Code2,
  BookOpen,
  BarChart3,
  Cpu,
  Database,
  Layout,
  Shield,
  Zap,
  Download,
  ExternalLink,
} from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { useProjectStore } from '@/store/projectStore'

// Stage status types
type StageStatus = 'pending' | 'active' | 'completed' | 'error'

// Stage data interface
interface StageData {
  id: string
  title: string
  icon: any
  status: StageStatus
  content?: any
  progress?: number
  summary?: string
}

// Abstract stage content
interface AbstractContent {
  projectName: string
  description: string
  techStack: string[]
  features: string[]
  complexity: string
  estimatedFiles: number
}

// Plan stage content
interface PlanContent {
  steps: {
    id: string
    label: string
    status: StageStatus
    category?: string
  }[]
}

// Build stage content
interface BuildContent {
  files: {
    path: string
    status: 'pending' | 'generating' | 'completed' | 'error'
  }[]
  currentFile?: string
  progress: number
  totalFiles: number
  completedFiles: number
}

// Documents stage content
interface DocumentsContent {
  documents: {
    type: string
    name: string
    status: StageStatus
    downloadUrl?: string
  }[]
  generationMessage?: string | null
}

// Summary stage content
interface SummaryContent {
  totalFiles: number
  totalDocuments: number
  techStack: string[]
  completedAt?: string
  downloadUrl?: string
}

export function ProjectStagesPanel() {
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const stageRefs = useRef<{ [key: string]: HTMLDivElement | null }>({})

  // Get data from stores
  const messages = useChatStore((state) => state.messages)
  const { currentProject, openTab } = useProjectStore()

  // Find file in project tree and open in editor
  const handleFileClick = (filePath: string) => {
    if (!currentProject?.files) return

    const findFile = (files: any[], path: string): any => {
      for (const file of files) {
        if (file.path === path) return file
        if (file.children) {
          const found = findFile(file.children, path)
          if (found) return found
        }
      }
      return null
    }

    const file = findFile(currentProject.files, filePath)
    if (file && file.type === 'file') {
      openTab(file)
    }
  }

  // Expanded stages state
  const [expandedStages, setExpandedStages] = useState<{ [key: string]: boolean }>({
    abstract: true,
    plan: true,
    build: true,
    documents: true,
    summary: true,
  })

  // Get the first user message (the project prompt)
  const userPrompt = messages.find(m => m.type === 'user')?.content || ''

  // Get the latest assistant message for stage data
  const lastAssistantMessage = messages.filter(m => m.type === 'assistant').slice(-1)[0]
  const thinkingSteps = (lastAssistantMessage as any)?.thinkingSteps || []
  const fileOperations = (lastAssistantMessage as any)?.fileOperations || []
  const planData = (lastAssistantMessage as any)?.planData

  // Check if this is a loaded project (has files but no live generation data)
  const isLoadedProject = currentProject?.files && currentProject.files.length > 0 &&
                          thinkingSteps.length === 0 && fileOperations.length === 0

  // Helper to flatten file tree and count files
  const flattenFiles = (files: any[]): any[] => {
    const result: any[] = []
    for (const f of files) {
      if (f.type === 'file') result.push(f)
      if (f.children) result.push(...flattenFiles(f.children))
    }
    return result
  }

  // Get all files from loaded project
  const loadedFiles = isLoadedProject ? flattenFiles(currentProject?.files || []) : []

  // Detect tech stack from loaded files
  const detectTechStackFromFiles = (files: any[]): string[] => {
    const tech: string[] = []
    const paths = files.map(f => f.path?.toLowerCase() || '')

    if (paths.some(p => p.includes('package.json'))) tech.push('Node.js')
    if (paths.some(p => p.includes('.tsx') || p.includes('.jsx'))) tech.push('React')
    if (paths.some(p => p.includes('next.config'))) tech.push('Next.js')
    if (paths.some(p => p.includes('vite.config'))) tech.push('Vite')
    if (paths.some(p => p.includes('tailwind.config'))) tech.push('Tailwind CSS')
    if (paths.some(p => p.includes('requirements.txt') || p.includes('.py'))) tech.push('Python')
    if (paths.some(p => p.includes('pom.xml') || p.includes('build.gradle'))) tech.push('Java')

    return tech.length > 0 ? tech : ['Full Stack']
  }

  // Check if project has documents
  const hasDocuments = loadedFiles.some(f =>
    f.path?.includes('.docx') || f.path?.includes('.pdf') || f.path?.includes('.pptx')
  )
  const documentFiles = loadedFiles.filter(f =>
    f.path?.includes('.docx') || f.path?.includes('.pdf') || f.path?.includes('.pptx')
  )

  // Track document generation progress from thinkingSteps
  const documentGenerationStep = thinkingSteps.find((step: any) =>
    step.label === 'Generating Documents' || step.label?.includes('Document')
  )

  // Parse document generation status from step details
  const getDocumentGenerationStatus = () => {
    if (!documentGenerationStep) return null

    const details = documentGenerationStep.details || ''
    const status = documentGenerationStep.status

    // Determine individual document statuses
    const docStatuses: Record<string, StageStatus> = {
      'srs': 'pending',
      'report': 'pending',
      'ppt': 'pending',
      'viva': 'pending'
    }

    // Check if generation is complete
    if (status === 'complete') {
      return {
        srs: 'completed' as StageStatus,
        report: 'completed' as StageStatus,
        ppt: 'completed' as StageStatus,
        viva: 'completed' as StageStatus,
        isGenerating: false,
        currentDoc: null
      }
    }

    // Parse details to find current document and completed ones
    const detailsLower = details.toLowerCase()

    // Check for completed documents
    if (detailsLower.includes('srs') && detailsLower.includes('completed')) docStatuses.srs = 'completed'
    if ((detailsLower.includes('report') || detailsLower.includes('project report')) && detailsLower.includes('completed')) docStatuses.report = 'completed'
    if ((detailsLower.includes('ppt') || detailsLower.includes('presentation')) && detailsLower.includes('completed')) docStatuses.ppt = 'completed'
    if (detailsLower.includes('viva') && detailsLower.includes('completed')) docStatuses.viva = 'completed'

    // Find currently generating document
    let currentDoc: string | null = null
    if (detailsLower.includes('generating')) {
      if (detailsLower.includes('srs') && docStatuses.srs !== 'completed') {
        currentDoc = 'srs'
        docStatuses.srs = 'active'
      } else if ((detailsLower.includes('report') || detailsLower.includes('project report')) && docStatuses.report !== 'completed') {
        currentDoc = 'report'
        docStatuses.report = 'active'
      } else if ((detailsLower.includes('ppt') || detailsLower.includes('presentation')) && docStatuses.ppt !== 'completed') {
        currentDoc = 'ppt'
        docStatuses.ppt = 'active'
      } else if (detailsLower.includes('viva') && docStatuses.viva !== 'completed') {
        currentDoc = 'viva'
        docStatuses.viva = 'active'
      } else if (detailsLower.includes('all documents') || detailsLower.includes('parallel')) {
        // Parallel generation - all are active
        if (docStatuses.srs === 'pending') docStatuses.srs = 'active'
        if (docStatuses.report === 'pending') docStatuses.report = 'active'
        if (docStatuses.ppt === 'pending') docStatuses.ppt = 'active'
        if (docStatuses.viva === 'pending') docStatuses.viva = 'active'
        currentDoc = 'all'
      }
    }

    return {
      ...docStatuses,
      isGenerating: status === 'active',
      currentDoc
    }
  }

  const docGenStatus = getDocumentGenerationStatus()

  // Extract tech stack from user prompt or planData
  const extractTechFromPrompt = (prompt: string): string[] => {
    const techKeywords = ['react', 'vue', 'angular', 'next.js', 'node', 'express', 'fastapi', 'django', 'flask',
      'python', 'javascript', 'typescript', 'java', 'spring', 'mongodb', 'postgresql', 'mysql', 'redis',
      'tailwind', 'bootstrap', 'material-ui', 'firebase', 'aws', 'docker']
    const found: string[] = []
    const lowerPrompt = prompt.toLowerCase()
    techKeywords.forEach(tech => {
      if (lowerPrompt.includes(tech)) {
        found.push(tech.charAt(0).toUpperCase() + tech.slice(1))
      }
    })
    return found.length > 0 ? found : ['Full Stack']
  }

  // Extract features from user prompt
  const extractFeaturesFromPrompt = (prompt: string): string[] => {
    const featureKeywords = ['login', 'authentication', 'dashboard', 'crud', 'api', 'database',
      'payment', 'cart', 'checkout', 'search', 'filter', 'upload', 'notification', 'chat', 'admin']
    const found: string[] = []
    const lowerPrompt = prompt.toLowerCase()
    featureKeywords.forEach(feature => {
      if (lowerPrompt.includes(feature)) {
        found.push(feature.charAt(0).toUpperCase() + feature.slice(1))
      }
    })
    return found.slice(0, 5)
  }

  // Determine stage statuses based on message data
  const getStageStatus = (stageId: string): StageStatus => {
    const hasUserMessage = messages.some(m => m.type === 'user')
    const hasThinkingSteps = thinkingSteps.length > 0
    const hasFileOps = fileOperations.length > 0
    const allFilesComplete = fileOperations.length > 0 && fileOperations.every((f: any) => f.status === 'complete')
    const allStepsComplete = thinkingSteps.length > 0 && thinkingSteps.every((s: any) => s.status === 'complete')

    switch (stageId) {
      case 'abstract':
        // If project is already loaded with files (not live generation), mark as completed
        if (isLoadedProject) return 'completed'
        if (planData?.projectName) return 'completed'
        if (hasUserMessage && !hasThinkingSteps) return 'active'
        if (hasUserMessage) return 'completed'
        return 'pending'

      case 'plan':
        // If project is already loaded with files, mark as completed
        if (isLoadedProject) return 'completed'
        if (allStepsComplete) return 'completed'
        if (hasThinkingSteps) return 'active'
        if (planData?.projectName) return 'active'
        return 'pending'

      case 'build':
        // If project is already loaded with files, mark as completed
        if (isLoadedProject) return 'completed'
        if (allFilesComplete) return 'completed'
        if (hasFileOps) return 'active'
        if (allStepsComplete) return 'active'
        return 'pending'

      case 'documents':
        // Check if documents are being generated (from thinkingSteps)
        if (docGenStatus?.isGenerating) return 'active'
        // Check if document generation is complete
        if (docGenStatus && !docGenStatus.isGenerating && documentGenerationStep?.status === 'complete') return 'completed'
        // Check if project has documents (already generated)
        if (hasDocuments) return 'completed'
        // If project is loaded but no docs, show as completed (generation done)
        if (isLoadedProject) return 'completed'
        if (allFilesComplete) return 'active'
        return 'pending'

      case 'summary':
        // For loaded projects, show as completed
        if (isLoadedProject) return 'completed'
        if (hasDocuments) return 'completed'
        return 'pending'

      default:
        return 'pending'
    }
  }

  // Build abstract content from planData, user prompt, or loaded project
  const abstractContent: AbstractContent | null = (() => {
    // For loaded projects, derive from project files
    if (isLoadedProject && currentProject) {
      return {
        projectName: currentProject.name || 'Project',
        description: currentProject.description || userPrompt || 'Loaded project',
        techStack: detectTechStackFromFiles(loadedFiles),
        features: [], // Can't determine from files
        complexity: 'Intermediate',
        estimatedFiles: loadedFiles.length,
      }
    }
    // For live generation, use planData or prompt
    if (userPrompt) {
      return {
        projectName: planData?.projectName || currentProject?.name || 'Project',
        description: planData?.projectDescription || userPrompt,
        techStack: planData?.techStack?.map((t: any) => t.name || t.items || t) || extractTechFromPrompt(userPrompt),
        features: planData?.features?.map((f: any) => f.name || f) || extractFeaturesFromPrompt(userPrompt),
        complexity: planData?.complexity || 'Intermediate',
        estimatedFiles: parseInt(planData?.estimatedFiles) || fileOperations.length || 15,
      }
    }
    return null
  })()

  // Build plan steps - use thinkingSteps if available, create from fileOperations, or show completed for loaded projects
  const planSteps = (() => {
    if (thinkingSteps.length > 0) {
      return thinkingSteps.map((step: any, idx: number) => ({
        id: `step-${idx}`,
        label: step.label,
        status: step.status === 'complete' ? 'completed' as StageStatus : step.status === 'active' ? 'active' as StageStatus : 'pending' as StageStatus,
        category: step.category,
      }))
    }
    if (fileOperations.length > 0) {
      return [
        { id: 'step-1', label: 'Analyzing requirements', status: 'completed' as StageStatus, category: 'Setup' },
        { id: 'step-2', label: 'Creating project structure', status: 'completed' as StageStatus, category: 'Setup' },
        { id: 'step-3', label: 'Generating code files', status: fileOperations.every((f: any) => f.status === 'complete') ? 'completed' as StageStatus : 'active' as StageStatus, category: 'Build' },
      ]
    }
    // For loaded projects, show completed steps
    if (isLoadedProject) {
      return [
        { id: 'step-1', label: 'Requirements analyzed', status: 'completed' as StageStatus, category: 'Setup' },
        { id: 'step-2', label: 'Project structure created', status: 'completed' as StageStatus, category: 'Setup' },
        { id: 'step-3', label: 'Code files generated', status: 'completed' as StageStatus, category: 'Build' },
        { id: 'step-4', label: 'Project completed', status: 'completed' as StageStatus, category: 'Complete' },
      ]
    }
    return []
  })()

  // Build stages data
  const stages: StageData[] = [
    {
      id: 'abstract',
      title: 'ABSTRACT',
      icon: FileText,
      status: getStageStatus('abstract'),
      content: abstractContent,
    },
    {
      id: 'plan',
      title: 'PLAN',
      icon: ListChecks,
      status: getStageStatus('plan'),
      content: {
        steps: planSteps,
      },
      progress: planSteps.length > 0
        ? (planSteps.filter((s: any) => s.status === 'completed').length / planSteps.length) * 100
        : 0,
    },
    {
      id: 'build',
      title: 'BUILD',
      icon: Hammer,
      status: getStageStatus('build'),
      content: isLoadedProject ? {
        // For loaded projects, show files from project
        files: loadedFiles.slice(0, 20).map((f: any) => ({
          path: f.path,
          status: 'completed' as const,
        })),
        currentFile: undefined,
        progress: 100,
        totalFiles: loadedFiles.length,
        completedFiles: loadedFiles.length,
      } : {
        // For live generation, use fileOperations
        files: fileOperations.map((op: any) => ({
          path: op.path,
          status: op.status === 'complete' ? 'completed' : op.status === 'in-progress' ? 'generating' : 'pending',
        })),
        currentFile: fileOperations.find((f: any) => f.status === 'in-progress')?.path,
        progress: fileOperations.length > 0
          ? (fileOperations.filter((f: any) => f.status === 'complete').length / fileOperations.length) * 100
          : 0,
        totalFiles: fileOperations.length,
        completedFiles: fileOperations.filter((f: any) => f.status === 'complete').length,
      },
    },
    {
      id: 'documents',
      title: 'DOCUMENTS',
      icon: FileStack,
      status: getStageStatus('documents'),
      content: {
        documents: hasDocuments ? [
          // Show actual documents from project
          ...documentFiles.map((f: any) => {
            const name = f.path?.split('/').pop() || f.name || 'Document'
            const type = name.includes('SRS') ? 'srs' :
                        name.includes('Report') ? 'report' :
                        name.includes('.pptx') ? 'ppt' :
                        name.includes('Viva') ? 'viva' : 'doc'
            return { type, name, status: 'completed' as StageStatus, downloadUrl: f.path }
          })
        ] : docGenStatus ? [
          // Show document generation progress from thinkingSteps
          { type: 'srs', name: 'SRS Document', status: docGenStatus.srs as StageStatus },
          { type: 'report', name: 'Project Report', status: docGenStatus.report as StageStatus },
          { type: 'ppt', name: 'Presentation', status: docGenStatus.ppt as StageStatus },
          { type: 'viva', name: 'Viva Q&A', status: docGenStatus.viva as StageStatus },
        ] : [
          // Default pending documents
          { type: 'srs', name: 'SRS Document', status: 'pending' as StageStatus },
          { type: 'report', name: 'Project Report', status: 'pending' as StageStatus },
          { type: 'ppt', name: 'Presentation', status: 'pending' as StageStatus },
          { type: 'viva', name: 'Viva Q&A', status: 'pending' as StageStatus },
        ],
        // Include generation message for context
        generationMessage: docGenStatus?.isGenerating ? documentGenerationStep?.details : null,
      },
    },
    {
      id: 'summary',
      title: 'SUMMARY',
      icon: BarChart3,
      status: getStageStatus('summary'),
      content: {
        totalFiles: isLoadedProject ? loadedFiles.length : fileOperations.length,
        totalDocuments: hasDocuments ? documentFiles.length : 4,
        techStack: isLoadedProject ? detectTechStackFromFiles(loadedFiles) : (planData?.techStack?.map((t: any) => t.name) || []),
      },
    },
  ]

  // Find active stage for auto-scroll
  const activeStageIndex = stages.findIndex(s => s.status === 'active')
  const activeStageId = activeStageIndex >= 0 ? stages[activeStageIndex].id : null

  // Auto-scroll to active stage
  useEffect(() => {
    if (activeStageId && stageRefs.current[activeStageId]) {
      stageRefs.current[activeStageId]?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [activeStageId])

  // Auto-expand active stage, collapse completed
  useEffect(() => {
    const newExpanded: { [key: string]: boolean } = {}
    stages.forEach(stage => {
      if (stage.status === 'active') {
        newExpanded[stage.id] = true
      } else if (stage.status === 'completed') {
        newExpanded[stage.id] = false
      } else {
        newExpanded[stage.id] = expandedStages[stage.id] ?? false
      }
    })
    setExpandedStages(newExpanded)
  }, [activeStageId])

  // Toggle stage expansion
  const toggleStage = (stageId: string) => {
    setExpandedStages(prev => ({
      ...prev,
      [stageId]: !prev[stageId],
    }))
  }

  // Get status icon
  const getStatusIcon = (status: StageStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'active':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'error':
        return <Circle className="w-5 h-5 text-red-500" />
      default:
        return <Circle className="w-5 h-5 text-gray-600" />
    }
  }

  // Get stage border color
  const getStageBorderColor = (status: StageStatus) => {
    switch (status) {
      case 'completed':
        return 'border-green-500/50 bg-green-500/5'
      case 'active':
        return 'border-blue-500/50 bg-blue-500/5 shadow-lg shadow-blue-500/10'
      case 'error':
        return 'border-red-500/50 bg-red-500/5'
      default:
        return 'border-gray-700/50 bg-gray-800/30 opacity-60'
    }
  }

  // Get timeline line color
  const getTimelineColor = (status: StageStatus) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500'
      case 'active':
        return 'bg-blue-500'
      default:
        return 'bg-gray-700'
    }
  }

  // If no messages, show empty state
  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center px-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4">
          <Zap className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">Start Building</h2>
        <p className="text-sm text-gray-400 max-w-xs">
          Describe your project and watch the AI build it step by step
        </p>
      </div>
    )
  }

  return (
    <div
      ref={messagesContainerRef}
      className="h-full overflow-y-auto scrollbar-thin px-4 py-4"
    >
      {/* User Prompt - Right aligned bubble */}
      {userPrompt && (
        <div className="flex justify-end mb-4">
          <div className="max-w-[85%] px-4 py-2.5 rounded-2xl rounded-tr-sm bg-violet-600 text-white">
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-left">
              {userPrompt}
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-500" />
          PROJECT STAGES
        </h2>
        <div className="mt-2 h-1 rounded-full bg-gray-800 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
            initial={{ width: 0 }}
            animate={{
              width: `${(stages.filter(s => s.status === 'completed').length / stages.length) * 100}%`
            }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical Timeline Line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-800">
          {stages.map((stage, idx) => (
            <motion.div
              key={`line-${stage.id}`}
              className={`absolute left-0 w-full ${getTimelineColor(stage.status)}`}
              style={{
                top: `${(idx / stages.length) * 100}%`,
                height: `${100 / stages.length}%`,
              }}
              initial={{ scaleY: 0 }}
              animate={{ scaleY: stage.status !== 'pending' ? 1 : 0 }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
            />
          ))}
        </div>

        {/* Stages */}
        <div className="space-y-3">
          {stages.map((stage, idx) => (
            <motion.div
              key={stage.id}
              ref={(el) => { stageRefs.current[stage.id] = el }}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: idx * 0.1 }}
              className="relative pl-10"
            >
              {/* Timeline Node */}
              <div
                className={`absolute left-0 w-8 h-8 rounded-full flex items-center justify-center z-10 ${
                  stage.status === 'completed' ? 'bg-green-500/20 border-2 border-green-500' :
                  stage.status === 'active' ? 'bg-blue-500/20 border-2 border-blue-500 animate-pulse' :
                  'bg-gray-800 border-2 border-gray-700'
                }`}
              >
                <span className="text-xs font-bold text-white">{idx + 1}</span>
              </div>

              {/* Stage Card */}
              <div
                className={`rounded-xl border transition-all duration-300 ${getStageBorderColor(stage.status)}`}
              >
                {/* Stage Header */}
                <button
                  onClick={() => toggleStage(stage.id)}
                  className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors rounded-t-xl"
                >
                  <div className="flex items-center gap-3">
                    <stage.icon className={`w-4 h-4 ${
                      stage.status === 'completed' ? 'text-green-400' :
                      stage.status === 'active' ? 'text-blue-400' :
                      'text-gray-500'
                    }`} />
                    <span className={`text-sm font-semibold ${
                      stage.status === 'completed' ? 'text-green-400' :
                      stage.status === 'active' ? 'text-blue-400' :
                      'text-gray-500'
                    }`}>
                      {stage.title}
                    </span>
                    {stage.progress !== undefined && stage.status === 'active' && (
                      <span className="text-xs text-gray-500">
                        {Math.round(stage.progress)}%
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(stage.status)}
                    {expandedStages[stage.id] ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                  </div>
                </button>

                {/* Stage Content */}
                <AnimatePresence>
                  {expandedStages[stage.id] && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-3 pb-3 border-t border-white/10">
                        {/* Abstract Content */}
                        {stage.id === 'abstract' && (
                          stage.content ? (
                            <AbstractStageContent content={stage.content} />
                          ) : stage.status === 'active' ? (
                            <div className="py-4 text-center">
                              <Loader2 className="w-4 h-4 animate-spin text-blue-500 mx-auto mb-2" />
                              <p className="text-xs text-gray-500">Analyzing your request...</p>
                            </div>
                          ) : null
                        )}

                        {/* Plan Content */}
                        {stage.id === 'plan' && (
                          <PlanStageContent content={stage.content} />
                        )}

                        {/* Build Content */}
                        {stage.id === 'build' && (
                          stage.content?.files?.length > 0 ? (
                            <BuildStageContent content={stage.content} onFileClick={handleFileClick} />
                          ) : stage.status === 'active' ? (
                            <div className="py-4 text-center">
                              <Loader2 className="w-4 h-4 animate-spin text-blue-500 mx-auto mb-2" />
                              <p className="text-xs text-gray-500">Preparing to generate files...</p>
                            </div>
                          ) : (
                            <div className="py-4 text-center">
                              <p className="text-xs text-gray-600">Waiting for plan completion...</p>
                            </div>
                          )
                        )}

                        {/* Documents Content */}
                        {stage.id === 'documents' && (
                          <DocumentsStageContent content={stage.content} />
                        )}

                        {/* Summary Content */}
                        {stage.id === 'summary' && (
                          stage.status === 'completed' ? (
                            <SummaryStageContent content={stage.content} />
                          ) : (
                            <div className="py-4 text-center">
                              <p className="text-xs text-gray-600">Will show summary after completion</p>
                            </div>
                          )
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Abstract Stage Content Component
function AbstractStageContent({ content }: { content: AbstractContent }) {
  if (!content) return null

  return (
    <div className="pt-3 space-y-3">
      {/* Project Name */}
      <div>
        <h3 className="text-base font-semibold text-white">{content.projectName}</h3>
        {content.description && (
          <p className="text-xs text-gray-400 mt-1 line-clamp-3">{content.description}</p>
        )}
      </div>

      {/* Tech Stack */}
      {content.techStack?.length > 0 && (
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Tech Stack</p>
          <div className="flex flex-wrap gap-1">
            {content.techStack.slice(0, 6).map((tech, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 text-[10px] rounded bg-blue-500/20 text-blue-400 border border-blue-500/30"
              >
                {typeof tech === 'string' ? tech : (tech as any)?.name || 'Tech'}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Features */}
      {content.features?.length > 0 && (
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Features</p>
          <div className="flex flex-wrap gap-1">
            {content.features.slice(0, 4).map((feature, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 text-[10px] rounded bg-purple-500/20 text-purple-400 border border-purple-500/30"
              >
                {typeof feature === 'string' ? feature : (feature as any)?.name || 'Feature'}
              </span>
            ))}
            {content.features.length > 4 && (
              <span className="px-2 py-0.5 text-[10px] rounded bg-gray-500/20 text-gray-400">
                +{content.features.length - 4} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center gap-4 text-[10px] text-gray-500">
        <span className="flex items-center gap-1">
          <Cpu className="w-3 h-3" />
          {content.complexity}
        </span>
        <span className="flex items-center gap-1">
          <Code2 className="w-3 h-3" />
          ~{content.estimatedFiles} files
        </span>
      </div>
    </div>
  )
}

// Plan Stage Content Component
function PlanStageContent({ content }: { content: PlanContent }) {
  if (!content?.steps || content.steps.length === 0) {
    return (
      <div className="pt-3 py-4 text-center">
        <p className="text-xs text-gray-600">Analyzing project requirements...</p>
      </div>
    )
  }

  return (
    <div className="pt-3 space-y-1.5">
      {content.steps.map((step, idx) => (
        <div
          key={step.id}
          className={`flex items-center gap-2 p-2 rounded-lg ${
            step.status === 'completed' ? 'bg-green-500/10' :
            step.status === 'active' ? 'bg-blue-500/10' :
            'bg-gray-800/50'
          }`}
        >
          {step.status === 'completed' ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
          ) : step.status === 'active' ? (
            <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />
          ) : (
            <Circle className="w-3.5 h-3.5 text-gray-600 flex-shrink-0" />
          )}
          <span className={`text-xs ${
            step.status === 'completed' ? 'text-green-400' :
            step.status === 'active' ? 'text-blue-400' :
            'text-gray-500'
          }`}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  )
}

// Build Stage Content Component
function BuildStageContent({ content, onFileClick }: { content: BuildContent; onFileClick?: (path: string) => void }) {
  const [showAllFiles, setShowAllFiles] = useState(false)
  const visibleFiles = showAllFiles ? content.files : content.files.slice(0, 5)

  const handleFileClick = (file: { path: string; status: string }) => {
    if (file.status === 'completed' && onFileClick) {
      onFileClick(file.path)
    }
  }

  return (
    <div className="pt-3 space-y-3">
      {/* Progress Bar */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-gray-500">Progress</span>
          <span className="text-[10px] text-gray-400">
            {content.completedFiles}/{content.totalFiles} files
          </span>
        </div>
        <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
            initial={{ width: 0 }}
            animate={{ width: `${content.progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Current File */}
      {content.currentFile && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
          <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />
          <span className="text-xs text-blue-400 font-mono truncate">
            {content.currentFile}
          </span>
        </div>
      )}

      {/* File List */}
      <div className="space-y-1">
        {visibleFiles.map((file, idx) => (
          <div
            key={idx}
            onClick={() => handleFileClick(file)}
            className={`flex items-center gap-2 p-1.5 rounded text-xs transition-all ${
              file.status === 'completed'
                ? 'text-green-400 cursor-pointer hover:bg-green-500/10 hover:pl-3'
                : file.status === 'generating' ? 'text-blue-400' :
              'text-gray-600'
            }`}
          >
            {file.status === 'completed' ? (
              <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
            ) : file.status === 'generating' ? (
              <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" />
            ) : (
              <Circle className="w-3 h-3 flex-shrink-0" />
            )}
            <span className="font-mono truncate">{file.path}</span>
          </div>
        ))}
      </div>

      {/* Show More/Less */}
      {content.files.length > 5 && (
        <button
          onClick={() => setShowAllFiles(!showAllFiles)}
          className="text-[10px] text-blue-500 hover:text-blue-400 transition-colors"
        >
          {showAllFiles ? 'Show less' : `+${content.files.length - 5} more files`}
        </button>
      )}
    </div>
  )
}

// Documents Stage Content Component
function DocumentsStageContent({ content }: { content: DocumentsContent }) {
  return (
    <div className="pt-3 space-y-1.5">
      {/* Generation progress message */}
      {content.generationMessage && (
        <div className="flex items-center gap-2 p-2 rounded-lg bg-blue-500/10 border border-blue-500/30 mb-2">
          <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin flex-shrink-0" />
          <span className="text-xs text-blue-400 truncate">
            {content.generationMessage}
          </span>
        </div>
      )}

      {content.documents.map((doc, idx) => (
        <div
          key={idx}
          className={`flex items-center justify-between p-2 rounded-lg ${
            doc.status === 'completed' ? 'bg-green-500/10' :
            doc.status === 'active' ? 'bg-blue-500/10' :
            'bg-gray-800/50'
          }`}
        >
          <div className="flex items-center gap-2">
            {doc.status === 'completed' ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            ) : doc.status === 'active' ? (
              <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />
            ) : (
              <Circle className="w-3.5 h-3.5 text-gray-600" />
            )}
            <span className={`text-xs ${
              doc.status === 'completed' ? 'text-green-400' :
              doc.status === 'active' ? 'text-blue-400' :
              'text-gray-500'
            }`}>
              {doc.name}
            </span>
          </div>
          {doc.status === 'completed' && doc.downloadUrl && (
            <button className="p-1 hover:bg-white/10 rounded transition-colors">
              <Download className="w-3 h-3 text-green-400" />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}

// Summary Stage Content Component
function SummaryStageContent({ content }: { content: SummaryContent }) {
  return (
    <div className="pt-3 space-y-3">
      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/30">
          <p className="text-[10px] text-gray-500">Files</p>
          <p className="text-lg font-bold text-green-400">{content.totalFiles}</p>
        </div>
        <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
          <p className="text-[10px] text-gray-500">Documents</p>
          <p className="text-lg font-bold text-blue-400">{content.totalDocuments}</p>
        </div>
      </div>

      {/* Tech Stack */}
      {content.techStack?.length > 0 && (
        <div>
          <p className="text-[10px] text-gray-500 mb-1">Technologies Used</p>
          <div className="flex flex-wrap gap-1">
            {content.techStack.map((tech, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 text-[10px] rounded bg-purple-500/20 text-purple-400"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Download Button */}
      <button className="w-full flex items-center justify-center gap-2 p-2 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-xs font-medium hover:from-blue-600 hover:to-cyan-600 transition-colors">
        <Download className="w-3.5 h-3.5" />
        Download Project
      </button>
    </div>
  )
}
