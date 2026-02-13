'use client'

import { useState, useEffect } from 'react'
import {
  Brain,
  Image,
  MessageSquare,
  TrendingUp,
  Sparkles,
  TreeDeciduous,
  Zap,
  Eye,
  Clock,
  Loader2,
  ChevronRight,
  Check,
  Settings,
  Play,
  FileSpreadsheet,
  Upload
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { CSVUpload } from './CSVUpload'
import { ImageUpload } from './ImageUpload'

interface MLModel {
  id: string
  name: string
  category: string
  framework: string
  description: string
  use_cases: string[]
}

interface MLConfig {
  num_classes?: number
  input_size?: number
  max_length?: number
  hidden_dim?: number
  batch_size?: number
  epochs?: number
  learning_rate?: number
}

// Tabular models that support CSV datasets
const TABULAR_MODELS = [
  'random_forest',
  'xgboost',
  'logistic_regression',
  'svm',
  'gradient_boosting',
  'decision_tree',
  'knn',
  'naive_bayes',
]

// Vision models that support image datasets
const VISION_MODELS = [
  'cnn',
  'resnet',
  'vgg',
  'efficientnet',
  'yolo',
  'unet',
  'mobilenet',
  'inception',
  'densenet',
]

const isTabularModel = (modelId: string): boolean => {
  return TABULAR_MODELS.includes(modelId.toLowerCase())
}

const isVisionModel = (modelId: string): boolean => {
  return VISION_MODELS.includes(modelId.toLowerCase())
}

interface MLModelSelectorProps {
  onProjectCreated?: (projectId: string) => void
}

const categoryIcons: Record<string, any> = {
  computer_vision: Image,
  nlp: MessageSquare,
  classification: TreeDeciduous,
  regression: TrendingUp,
  time_series: Clock,
  generative: Sparkles,
  recommendation: Zap,
  clustering: Brain,
}

const categoryColors: Record<string, string> = {
  computer_vision: 'text-purple-400 bg-purple-500/20',
  nlp: 'text-blue-400 bg-blue-500/20',
  classification: 'text-green-400 bg-green-500/20',
  regression: 'text-orange-400 bg-orange-500/20',
  time_series: 'text-cyan-400 bg-cyan-500/20',
  generative: 'text-pink-400 bg-pink-500/20',
  recommendation: 'text-yellow-400 bg-yellow-500/20',
  clustering: 'text-indigo-400 bg-indigo-500/20',
}

const frameworkBadges: Record<string, string> = {
  pytorch: 'bg-orange-500/20 text-orange-400',
  tensorflow: 'bg-yellow-500/20 text-yellow-400',
  sklearn: 'bg-blue-500/20 text-blue-400',
  huggingface: 'bg-purple-500/20 text-purple-400',
}

export function MLModelSelector({ onProjectCreated }: MLModelSelectorProps) {
  const [models, setModels] = useState<MLModel[]>([])
  const [selectedModel, setSelectedModel] = useState<MLModel | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [step, setStep] = useState<'select' | 'configure' | 'dataset' | 'customize'>('select')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  // Configuration
  const [projectName, setProjectName] = useState('')
  const [config, setConfig] = useState<MLConfig>({})
  const [customPrompt, setCustomPrompt] = useState('')
  const [useAICustomization, setUseAICustomization] = useState(false)

  // Dataset state for tabular models (CSV)
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [targetColumn, setTargetColumn] = useState<string>('')
  const [featureColumns, setFeatureColumns] = useState<string[]>([])
  const [useDataset, setUseDataset] = useState(false)

  // Image dataset state for vision models
  const [imageDatasetId, setImageDatasetId] = useState<string | null>(null)
  const [imageNumClasses, setImageNumClasses] = useState<number>(0)
  const [imageInputSize, setImageInputSize] = useState<number>(224)
  const [useImageDataset, setUseImageDataset] = useState(false)

  // Fetch models on mount
  useEffect(() => {
    fetchModels()
  }, [])

  const fetchModels = async () => {
    try {
      setIsLoading(true)
      const data = await apiClient.get('/ml/models')
      setModels(data.models)
    } catch (err) {
      console.error('Failed to fetch ML models:', err)
      setError('Failed to load ML models')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectModel = (model: MLModel) => {
    setSelectedModel(model)
    setProjectName(`${model.id}_project`)
    setConfig({
      num_classes: 10,
      batch_size: 32,
      epochs: 50,
      learning_rate: 0.001,
    })
    // Reset dataset states
    setDatasetId(null)
    setTargetColumn('')
    setFeatureColumns([])
    setImageDatasetId(null)
    setImageNumClasses(0)
    setImageInputSize(224)

    const isTabular = isTabularModel(model.id)
    const isVision = isVisionModel(model.id)
    setUseDataset(isTabular)
    setUseImageDataset(isVision)

    // Go to dataset step for tabular/vision models, configure for others
    if (isTabular || isVision) {
      setStep('dataset')
    } else {
      setStep('configure')
    }
  }

  const handleDatasetReady = (dsId: string, target: string, features: string[]) => {
    setDatasetId(dsId)
    setTargetColumn(target)
    setFeatureColumns(features)
    setStep('configure')
  }

  const handleImageDatasetReady = (dsId: string, numClasses: number, inputSize: number) => {
    setImageDatasetId(dsId)
    setImageNumClasses(numClasses)
    setImageInputSize(inputSize)
    // Update config with detected num_classes
    setConfig(prev => ({ ...prev, num_classes: numClasses, input_size: inputSize }))
    setStep('configure')
  }

  const handleCreateProject = async () => {
    if (!selectedModel || !projectName) return

    setIsCreating(true)
    setError(null)

    try {
      let data: any

      // Use image dataset endpoint for vision models
      if (imageDatasetId && isVisionModel(selectedModel.id)) {
        data = await apiClient.generateMLProjectWithImageDataset({
          model_type: selectedModel.id,
          project_name: projectName,
          dataset_id: imageDatasetId,
          input_size: imageInputSize,
          num_classes: imageNumClasses,
          batch_size: config.batch_size,
          epochs: config.epochs,
          learning_rate: config.learning_rate,
        })
      }
      // Use CSV dataset endpoint for tabular models
      else if (datasetId && isTabularModel(selectedModel.id)) {
        data = await apiClient.generateMLProjectWithDataset({
          model_type: selectedModel.id,
          project_name: projectName,
          dataset_id: datasetId,
          target_column: targetColumn,
          feature_columns: featureColumns.length > 0 ? featureColumns : undefined,
          ...config,
        })
      } else if (useAICustomization) {
        data = await apiClient.post('/ml/customize', {
          model_type: selectedModel.id,
          project_name: projectName,
          base_template: true,
          prompt: customPrompt,
          config,
        })
      } else {
        data = await apiClient.post('/ml/generate', {
          config: {
            model_type: selectedModel.id,
            project_name: projectName,
            ...config,
            customization_prompt: customPrompt || undefined,
          },
        })
      }

      if (onProjectCreated) {
        onProjectCreated(data.project_id)
      }

      // Reset
      setStep('select')
      setSelectedModel(null)
      setProjectName('')
      setConfig({})
      setCustomPrompt('')
      setDatasetId(null)
      setTargetColumn('')
      setFeatureColumns([])
      setUseDataset(false)
      setImageDatasetId(null)
      setImageNumClasses(0)
      setImageInputSize(224)
      setUseImageDataset(false)

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create ML project')
    } finally {
      setIsCreating(false)
    }
  }

  const categories = [...new Set(models.map(m => m.category))]
  const filteredModels = selectedCategory
    ? models.filter(m => m.category === selectedCategory)
    : models

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--bolt-accent))]" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="p-4 border-b border-[hsl(var(--bolt-border))]">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-[hsl(var(--bolt-accent))]" />
          <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
            ML Project Generator
          </h2>
        </div>
        <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">
          {step === 'select' && 'Select a machine learning model to start'}
          {step === 'configure' && 'Configure your ML project'}
          {step === 'dataset' && useImageDataset && 'Upload training images (ZIP)'}
          {step === 'dataset' && useDataset && 'Upload training data (CSV)'}
          {step === 'customize' && 'Add AI customization (optional)'}
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[hsl(var(--bolt-border))]">
        {(() => {
          // Dynamic steps based on model type
          const steps: Array<'select' | 'dataset' | 'configure' | 'customize'> = (useDataset || useImageDataset)
            ? ['select', 'dataset', 'configure', 'customize']
            : ['select', 'configure', 'customize']

          const currentStepIndex = steps.indexOf(step)

          return steps.map((s, idx) => (
            <div key={s} className="flex items-center">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                  step === s
                    ? 'bg-[hsl(var(--bolt-accent))] text-white'
                    : idx < currentStepIndex
                    ? 'bg-green-500 text-white'
                    : 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-tertiary))]'
                }`}
              >
                {idx < currentStepIndex ? (
                  <Check className="w-3 h-3" />
                ) : (
                  idx + 1
                )}
              </div>
              {idx < steps.length - 1 && (
                <ChevronRight className="w-4 h-4 mx-1 text-[hsl(var(--bolt-text-tertiary))]" />
              )}
            </div>
          ))
        })()}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Step 1: Model Selection */}
        {step === 'select' && (
          <div className="space-y-4">
            {/* Category Filter */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                  !selectedCategory
                    ? 'bg-[hsl(var(--bolt-accent))] text-white'
                    : 'bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
                }`}
              >
                All
              </button>
              {categories.map(cat => {
                const Icon = categoryIcons[cat] || Brain
                return (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
                      selectedCategory === cat
                        ? 'bg-[hsl(var(--bolt-accent))] text-white'
                        : 'bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
                    }`}
                  >
                    <Icon className="w-3 h-3" />
                    {cat.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </button>
                )
              })}
            </div>

            {/* Model Cards */}
            <div className="grid gap-3">
              {filteredModels.map(model => {
                const Icon = categoryIcons[model.category] || Brain
                const colorClass = categoryColors[model.category] || 'text-gray-400 bg-gray-500/20'
                const frameworkClass = frameworkBadges[model.framework] || 'bg-gray-500/20 text-gray-400'

                return (
                  <button
                    key={model.id}
                    onClick={() => handleSelectModel(model)}
                    className="w-full p-4 rounded-lg border border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] hover:border-[hsl(var(--bolt-accent))] transition-colors text-left"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${colorClass.split(' ')[1]}`}>
                        <Icon className={`w-5 h-5 ${colorClass.split(' ')[0]}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-[hsl(var(--bolt-text-primary))] truncate">
                            {model.name}
                          </h3>
                          <span className={`px-2 py-0.5 rounded text-xs ${frameworkClass}`}>
                            {model.framework}
                          </span>
                        </div>
                        <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mb-2">
                          {model.description}
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {model.use_cases.slice(0, 3).map(useCase => (
                            <span
                              key={useCase}
                              className="px-2 py-0.5 rounded bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-tertiary))] text-xs"
                            >
                              {useCase}
                            </span>
                          ))}
                        </div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-[hsl(var(--bolt-text-tertiary))]" />
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Dataset Upload Step (for tabular models - CSV) */}
        {step === 'dataset' && selectedModel && useDataset && (
          <div className="space-y-4">
            {/* Info Banner */}
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <div className="flex items-center gap-2 mb-1">
                <FileSpreadsheet className="w-4 h-4 text-blue-400" />
                <span className="font-medium text-blue-400">Training Data (Optional)</span>
              </div>
              <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                Upload a CSV file with your training data, or skip to use sample data.
              </p>
            </div>

            {/* CSV Upload Component */}
            <div className="border border-[hsl(var(--bolt-border))] rounded-lg overflow-hidden">
              <CSVUpload
                onDatasetReady={handleDatasetReady}
                modelType={selectedModel.id}
              />
            </div>

            {/* Skip Option */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setStep('select')}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => {
                  setDatasetId(null)
                  setStep('configure')
                }}
                className="flex-1 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors flex items-center justify-center gap-2"
              >
                Skip & Use Sample Data
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Dataset Upload Step (for vision models - Images) */}
        {step === 'dataset' && selectedModel && useImageDataset && (
          <div className="space-y-4">
            {/* Info Banner */}
            <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <div className="flex items-center gap-2 mb-1">
                <Image className="w-4 h-4 text-purple-400" />
                <span className="font-medium text-purple-400">Image Dataset (Optional)</span>
              </div>
              <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                Upload a ZIP file with image folders for training, or skip to use sample data.
              </p>
            </div>

            {/* Image Upload Component */}
            <div className="border border-[hsl(var(--bolt-border))] rounded-lg overflow-hidden">
              <ImageUpload
                onDatasetReady={handleImageDatasetReady}
                modelType={selectedModel.id}
              />
            </div>

            {/* Skip Option */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setStep('select')}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => {
                  setImageDatasetId(null)
                  setStep('configure')
                }}
                className="flex-1 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors flex items-center justify-center gap-2"
              >
                Skip & Use Sample Data
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2/3: Configuration */}
        {step === 'configure' && selectedModel && (
          <div className="space-y-4">
            {/* Selected Model Info */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <div className="flex items-center gap-2 mb-1">
                <Eye className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {selectedModel.name}
                </span>
              </div>
              <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                {selectedModel.description}
              </p>
            </div>

            {/* CSV Dataset Info (if uploaded) */}
            {datasetId && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="w-4 h-4 text-green-400" />
                    <span className="font-medium text-green-400">Training Data Ready</span>
                  </div>
                  <button
                    onClick={() => setStep('dataset')}
                    className="text-xs text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-accent))]"
                  >
                    Change
                  </button>
                </div>
                <div className="mt-1 text-xs text-[hsl(var(--bolt-text-secondary))]">
                  Target: <span className="font-medium text-[hsl(var(--bolt-text-primary))]">{targetColumn}</span>
                  {featureColumns.length > 0 && (
                    <span className="ml-2">
                      Features: <span className="font-medium text-[hsl(var(--bolt-text-primary))]">{featureColumns.length} columns</span>
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Image Dataset Info (if uploaded) */}
            {imageDatasetId && (
              <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Image className="w-4 h-4 text-purple-400" />
                    <span className="font-medium text-purple-400">Image Dataset Ready</span>
                  </div>
                  <button
                    onClick={() => setStep('dataset')}
                    className="text-xs text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-accent))]"
                  >
                    Change
                  </button>
                </div>
                <div className="mt-1 text-xs text-[hsl(var(--bolt-text-secondary))]">
                  Classes: <span className="font-medium text-[hsl(var(--bolt-text-primary))]">{imageNumClasses}</span>
                  <span className="ml-2">
                    Input Size: <span className="font-medium text-[hsl(var(--bolt-text-primary))]">{imageInputSize}x{imageInputSize}</span>
                  </span>
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

            {/* Configuration Options */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                <Settings className="w-4 h-4" />
                Model Configuration
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-[hsl(var(--bolt-text-secondary))] mb-1">
                    Num Classes
                  </label>
                  <input
                    type="number"
                    min="2"
                    value={config.num_classes || ''}
                    onChange={(e) => setConfig({ ...config, num_classes: parseInt(e.target.value) || undefined })}
                    className="w-full px-2 py-1.5 rounded bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] text-sm focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[hsl(var(--bolt-text-secondary))] mb-1">
                    Batch Size
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={config.batch_size || ''}
                    onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) || undefined })}
                    className="w-full px-2 py-1.5 rounded bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] text-sm focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[hsl(var(--bolt-text-secondary))] mb-1">
                    Epochs
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={config.epochs || ''}
                    onChange={(e) => setConfig({ ...config, epochs: parseInt(e.target.value) || undefined })}
                    className="w-full px-2 py-1.5 rounded bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] text-sm focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[hsl(var(--bolt-text-secondary))] mb-1">
                    Learning Rate
                  </label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    value={config.learning_rate || ''}
                    onChange={(e) => setConfig({ ...config, learning_rate: parseFloat(e.target.value) || undefined })}
                    className="w-full px-2 py-1.5 rounded bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] text-sm focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                  />
                </div>
              </div>
            </div>

            {/* AI Customization Toggle */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <input
                type="checkbox"
                id="ai-customize"
                checked={useAICustomization}
                onChange={(e) => setUseAICustomization(e.target.checked)}
                className="w-4 h-4 rounded"
              />
              <label htmlFor="ai-customize" className="flex-1">
                <span className="font-medium text-[hsl(var(--bolt-text-primary))] flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  Enable AI Customization
                </span>
                <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                  Let AI enhance the template based on your specific requirements
                </p>
              </label>
            </div>

            {/* Navigation Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setStep((useDataset || useImageDataset) ? 'dataset' : 'select')}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => useAICustomization ? setStep('customize') : handleCreateProject()}
                disabled={!projectName}
                className="flex-1 py-2 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {useAICustomization ? (
                  <>Next <ChevronRight className="w-4 h-4" /></>
                ) : isCreating ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</>
                ) : (
                  <><Play className="w-4 h-4" /> Create Project</>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: AI Customization */}
        {step === 'customize' && selectedModel && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="font-medium text-purple-400">AI Customization</span>
              </div>
              <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                Describe your specific requirements and AI will customize the template accordingly.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-1">
                Customization Requirements
              </label>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="E.g., 'Add data augmentation for medical images, include ROC curve plotting, save checkpoints every 10 epochs, add early stopping...'"
                rows={6}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))] resize-none"
              />
            </div>

            {/* Quick Suggestions */}
            <div>
              <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mb-2">Quick suggestions:</p>
              <div className="flex flex-wrap gap-2">
                {[
                  'Add data augmentation',
                  'Include early stopping',
                  'Add TensorBoard logging',
                  'Include confusion matrix',
                  'Add model export to ONNX',
                ].map(suggestion => (
                  <button
                    key={suggestion}
                    onClick={() => setCustomPrompt(prev => prev ? `${prev}, ${suggestion.toLowerCase()}` : suggestion)}
                    className="px-2 py-1 rounded bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] text-xs hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
                  >
                    + {suggestion}
                  </button>
                ))}
              </div>
            </div>

            {/* Navigation Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setStep('configure')}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleCreateProject}
                disabled={isCreating}
                className="flex-1 py-2 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isCreating ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</>
                ) : (
                  <><Sparkles className="w-4 h-4" /> Create with AI</>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
