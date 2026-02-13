'use client'

import { useState } from 'react'
import {
  Brain,
  Sparkles,
  Loader2,
  ChevronRight,
  Check,
  AlertCircle,
  Lightbulb,
  Settings,
  Play,
  RefreshCw,
  Image,
  FileSpreadsheet,
  MessageSquare,
  Clock,
  Zap
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'

// ==================== Types ====================

interface PromptAnalysis {
  detected_model_type: string
  detected_category: string
  confidence: number
  extracted_config: Record<string, any>
  extracted_features: string[]
  suggested_models: string[]
  data_type: string
  problem_type: string
}

interface AnalyzeResponse {
  analysis: PromptAnalysis
  suggested_prompt_improvements: string[]
  ready_to_generate: boolean
}

interface GenerateResponse {
  project_id: string
  project_name: string
  model_type: string
  category: string
  framework: string
  files_created: number
  prompt_analysis: PromptAnalysis
  message: string
}

interface MLPromptGeneratorProps {
  onProjectCreated?: (projectId: string) => void
}

// ==================== Constants ====================

const EXAMPLE_PROMPTS = [
  {
    icon: Image,
    category: "Image Classification",
    prompt: "Create a CNN to classify 5 types of flowers with data augmentation and early stopping",
    color: "text-purple-400"
  },
  {
    icon: FileSpreadsheet,
    category: "Tabular Prediction",
    prompt: "Build an XGBoost model to predict house prices from CSV data with cross validation",
    color: "text-green-400"
  },
  {
    icon: MessageSquare,
    category: "Text Analysis",
    prompt: "Create a BERT sentiment classifier with 3 classes for product reviews",
    color: "text-blue-400"
  },
  {
    icon: Clock,
    category: "Time Series",
    prompt: "Build an LSTM model to forecast stock prices with 30 days of historical data",
    color: "text-cyan-400"
  },
  {
    icon: Zap,
    category: "Object Detection",
    prompt: "I need a YOLO model to detect vehicles in traffic camera images",
    color: "text-orange-400"
  }
]

const categoryColors: Record<string, string> = {
  computer_vision: 'bg-purple-500/20 text-purple-400',
  nlp: 'bg-blue-500/20 text-blue-400',
  classification: 'bg-green-500/20 text-green-400',
  regression: 'bg-orange-500/20 text-orange-400',
  time_series: 'bg-cyan-500/20 text-cyan-400',
  generative: 'bg-pink-500/20 text-pink-400',
  recommendation: 'bg-yellow-500/20 text-yellow-400',
  clustering: 'bg-indigo-500/20 text-indigo-400',
}

const dataTypeIcons: Record<string, any> = {
  image: Image,
  tabular: FileSpreadsheet,
  text: MessageSquare,
  time_series: Clock,
  unknown: Brain,
}

// ==================== Component ====================

export function MLPromptGenerator({ onProjectCreated }: MLPromptGeneratorProps) {
  // State
  const [prompt, setPrompt] = useState('')
  const [projectName, setProjectName] = useState('')
  const [analysis, setAnalysis] = useState<PromptAnalysis | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'input' | 'review' | 'done'>('input')
  const [generatedProject, setGeneratedProject] = useState<GenerateResponse | null>(null)

  // Override options
  const [showOverrides, setShowOverrides] = useState(false)
  const [overrideModel, setOverrideModel] = useState('')
  const [overrideClasses, setOverrideClasses] = useState<number | undefined>()
  const [overrideInputSize, setOverrideInputSize] = useState<number | undefined>()

  // ==================== Handlers ====================

  const handleAnalyze = async () => {
    if (!prompt.trim() || prompt.length < 10) {
      setError('Please enter a more detailed description (at least 10 characters)')
      return
    }

    setIsAnalyzing(true)
    setError(null)

    try {
      const response: AnalyzeResponse = await apiClient.post('/ml/analyze-prompt', { prompt })
      setAnalysis(response.analysis)
      setSuggestions(response.suggested_prompt_improvements)
      setStep('review')

      // Auto-set project name from model type
      if (!projectName) {
        setProjectName(`${response.analysis.detected_model_type}_project`)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to analyze prompt')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleGenerate = async () => {
    if (!analysis) return

    setIsGenerating(true)
    setError(null)

    try {
      const response: GenerateResponse = await apiClient.post('/ml/generate-from-prompt', {
        prompt,
        project_name: projectName || undefined,
        model_type: overrideModel || undefined,
        num_classes: overrideClasses || undefined,
        input_size: overrideInputSize || undefined,
      })

      setGeneratedProject(response)
      setStep('done')

      if (onProjectCreated) {
        onProjectCreated(response.project_id)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate project')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleReset = () => {
    setPrompt('')
    setProjectName('')
    setAnalysis(null)
    setSuggestions([])
    setError(null)
    setStep('input')
    setGeneratedProject(null)
    setShowOverrides(false)
    setOverrideModel('')
    setOverrideClasses(undefined)
    setOverrideInputSize(undefined)
  }

  const handleUseExample = (examplePrompt: string) => {
    setPrompt(examplePrompt)
  }

  // ==================== Render ====================

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="p-4 border-b border-[hsl(var(--bolt-border))]">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-[hsl(var(--bolt-accent))]" />
          <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
            AI ML Project Generator
          </h2>
        </div>
        <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">
          {step === 'input' && 'Describe your ML project in plain English'}
          {step === 'review' && 'Review the detected configuration'}
          {step === 'done' && 'Your project is ready!'}
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[hsl(var(--bolt-border))]">
        {(['input', 'review', 'done'] as const).map((s, idx) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                step === s
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : idx < ['input', 'review', 'done'].indexOf(step)
                  ? 'bg-green-500 text-white'
                  : 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-tertiary))]'
              }`}
            >
              {idx < ['input', 'review', 'done'].indexOf(step) ? (
                <Check className="w-3 h-3" />
              ) : (
                idx + 1
              )}
            </div>
            {idx < 2 && (
              <ChevronRight className="w-4 h-4 mx-1 text-[hsl(var(--bolt-text-tertiary))]" />
            )}
          </div>
        ))}
        <span className="ml-2 text-xs text-[hsl(var(--bolt-text-tertiary))]">
          {step === 'input' && 'Describe'}
          {step === 'review' && 'Review'}
          {step === 'done' && 'Complete'}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Step 1: Input */}
        {step === 'input' && (
          <div className="space-y-4">
            {/* Prompt Input */}
            <div>
              <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
                Describe your ML project
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="E.g., 'Create a CNN to classify plant diseases with 4 classes, include data augmentation and early stopping'"
                rows={4}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))] resize-none"
              />
              <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mt-1">
                {prompt.length}/2000 characters
              </p>
            </div>

            {/* Example Prompts */}
            <div>
              <p className="text-xs font-medium text-[hsl(var(--bolt-text-secondary))] mb-2 flex items-center gap-1">
                <Lightbulb className="w-3 h-3" />
                Try an example:
              </p>
              <div className="space-y-2">
                {EXAMPLE_PROMPTS.map((example, idx) => {
                  const Icon = example.icon
                  return (
                    <button
                      key={idx}
                      onClick={() => handleUseExample(example.prompt)}
                      className="w-full p-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))]/50 transition-colors text-left"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className={`w-4 h-4 ${example.color}`} />
                        <span className="text-xs font-medium text-[hsl(var(--bolt-text-secondary))]">
                          {example.category}
                        </span>
                      </div>
                      <p className="text-sm text-[hsl(var(--bolt-text-primary))] line-clamp-1">
                        {example.prompt}
                      </p>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Analyze Button */}
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || prompt.length < 10}
              className="w-full py-3 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Brain className="w-4 h-4" />
                  Analyze & Continue
                </>
              )}
            </button>
          </div>
        )}

        {/* Step 2: Review */}
        {step === 'review' && analysis && (
          <div className="space-y-4">
            {/* Detected Configuration */}
            <div className="p-4 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-3 flex items-center gap-2">
                <Brain className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                Detected Configuration
              </h3>

              <div className="grid grid-cols-2 gap-3">
                {/* Model Type */}
                <div className="p-2 rounded bg-[hsl(var(--bolt-bg-tertiary))]">
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">Model Type</p>
                  <p className="font-medium text-[hsl(var(--bolt-text-primary))]">
                    {analysis.detected_model_type.toUpperCase()}
                  </p>
                </div>

                {/* Category */}
                <div className="p-2 rounded bg-[hsl(var(--bolt-bg-tertiary))]">
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">Category</p>
                  <span className={`px-2 py-0.5 rounded text-xs ${categoryColors[analysis.detected_category] || 'bg-gray-500/20 text-gray-400'}`}>
                    {analysis.detected_category.replace('_', ' ')}
                  </span>
                </div>

                {/* Data Type */}
                <div className="p-2 rounded bg-[hsl(var(--bolt-bg-tertiary))]">
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">Data Type</p>
                  <div className="flex items-center gap-1">
                    {(() => {
                      const Icon = dataTypeIcons[analysis.data_type] || Brain
                      return <Icon className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                    })()}
                    <span className="text-[hsl(var(--bolt-text-primary))]">
                      {analysis.data_type.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {/* Confidence */}
                <div className="p-2 rounded bg-[hsl(var(--bolt-bg-tertiary))]">
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">Confidence</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-[hsl(var(--bolt-bg-primary))] overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          analysis.confidence >= 0.7 ? 'bg-green-500' :
                          analysis.confidence >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${analysis.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-[hsl(var(--bolt-text-primary))]">
                      {Math.round(analysis.confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Extracted Config */}
              {Object.keys(analysis.extracted_config).length > 0 && (
                <div className="mt-3 pt-3 border-t border-[hsl(var(--bolt-border))]">
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mb-2">Extracted Settings:</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(analysis.extracted_config).map(([key, value]) => (
                      <span
                        key={key}
                        className="px-2 py-1 rounded bg-[hsl(var(--bolt-accent))]/20 text-[hsl(var(--bolt-accent))] text-xs"
                      >
                        {key}: {value}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Features */}
              {analysis.extracted_features.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[hsl(var(--bolt-border))]">
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mb-2">Requested Features:</p>
                  <div className="flex flex-wrap gap-2">
                    {analysis.extracted_features.map((feature) => (
                      <span
                        key={feature}
                        className="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs flex items-center gap-1"
                      >
                        <Check className="w-3 h-3" />
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && (
              <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="w-4 h-4 text-yellow-400" />
                  <span className="font-medium text-yellow-400 text-sm">Suggestions</span>
                </div>
                <ul className="text-xs text-[hsl(var(--bolt-text-secondary))] space-y-1">
                  {suggestions.map((suggestion, idx) => (
                    <li key={idx}>• {suggestion}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Alternative Models */}
            {analysis.suggested_models.length > 0 && (
              <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
                <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mb-2">Alternative models:</p>
                <div className="flex flex-wrap gap-2">
                  {analysis.suggested_models.map((model) => (
                    <button
                      key={model}
                      onClick={() => setOverrideModel(model)}
                      className={`px-2 py-1 rounded text-xs transition-colors ${
                        overrideModel === model
                          ? 'bg-[hsl(var(--bolt-accent))] text-white'
                          : 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-primary))]'
                      }`}
                    >
                      {model.toUpperCase()}
                    </button>
                  ))}
                  {overrideModel && (
                    <button
                      onClick={() => setOverrideModel('')}
                      className="px-2 py-1 rounded bg-red-500/20 text-red-400 text-xs"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Project Name */}
            <div>
              <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-1">
                Project Name
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="my_ml_project"
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
              />
            </div>

            {/* Override Options */}
            <div>
              <button
                onClick={() => setShowOverrides(!showOverrides)}
                className="text-sm text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-accent))] flex items-center gap-1"
              >
                <Settings className="w-4 h-4" />
                {showOverrides ? 'Hide' : 'Show'} advanced options
              </button>

              {showOverrides && (
                <div className="mt-3 p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-[hsl(var(--bolt-text-tertiary))] mb-1">
                      Override Classes
                    </label>
                    <input
                      type="number"
                      min="2"
                      value={overrideClasses || ''}
                      onChange={(e) => setOverrideClasses(e.target.value ? parseInt(e.target.value) : undefined)}
                      placeholder="Auto"
                      className="w-full px-2 py-1.5 rounded bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] text-sm focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[hsl(var(--bolt-text-tertiary))] mb-1">
                      Override Input Size
                    </label>
                    <input
                      type="number"
                      min="32"
                      value={overrideInputSize || ''}
                      onChange={(e) => setOverrideInputSize(e.target.value ? parseInt(e.target.value) : undefined)}
                      placeholder="Auto"
                      className="w-full px-2 py-1.5 rounded bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] text-sm focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Navigation */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setStep('input')}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="flex-1 py-2 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Generate Project
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Done */}
        {step === 'done' && generatedProject && (
          <div className="space-y-4">
            {/* Success Banner */}
            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-center">
              <Check className="w-10 h-10 text-green-400 mx-auto mb-2" />
              <h3 className="font-medium text-green-400 mb-1">Project Created!</h3>
              <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                {generatedProject.message}
              </p>
            </div>

            {/* Project Info */}
            <div className="p-4 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <h3 className="font-medium text-[hsl(var(--bolt-text-primary))] mb-3">
                {generatedProject.project_name}
              </h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-[hsl(var(--bolt-text-tertiary))]">Model:</span>
                  <span className="ml-2 text-[hsl(var(--bolt-text-primary))]">
                    {generatedProject.model_type.toUpperCase()}
                  </span>
                </div>
                <div>
                  <span className="text-[hsl(var(--bolt-text-tertiary))]">Category:</span>
                  <span className="ml-2 text-[hsl(var(--bolt-text-primary))]">
                    {generatedProject.category}
                  </span>
                </div>
                <div>
                  <span className="text-[hsl(var(--bolt-text-tertiary))]">Framework:</span>
                  <span className="ml-2 text-[hsl(var(--bolt-text-primary))]">
                    {generatedProject.framework}
                  </span>
                </div>
                <div>
                  <span className="text-[hsl(var(--bolt-text-tertiary))]">Files:</span>
                  <span className="ml-2 text-[hsl(var(--bolt-text-primary))]">
                    {generatedProject.files_created}
                  </span>
                </div>
              </div>
            </div>

            {/* Create Another */}
            <button
              onClick={handleReset}
              className="w-full py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Create Another Project
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
