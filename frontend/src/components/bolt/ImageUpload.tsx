'use client'

import { useState, useRef, useCallback } from 'react'
import {
  Upload,
  Image as ImageIcon,
  X,
  Check,
  AlertCircle,
  Loader2,
  FolderOpen,
  Layers,
  Settings,
  ChevronDown,
  ChevronRight,
  Info,
  Archive
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'

// ==================== Types ====================

interface ImageClassInfo {
  name: string
  image_count: number
  sample_images: string[]
}

interface ImageInfo {
  formats: string[]
  avg_width?: number
  avg_height?: number
  min_width?: number
  min_height?: number
  max_width?: number
  max_height?: number
}

interface SplitInfo {
  train_count: number
  test_count: number
  val_count: number
  has_split: boolean
}

interface ImageDatasetUploadResponse {
  id: string
  name: string
  original_filename: string
  size_bytes: number
  dataset_type: string
  total_images: number
  num_classes: number
  classes: ImageClassInfo[]
  image_info?: ImageInfo
  split_info?: SplitInfo
  recommended_input_size: number
  status: string
  message: string
}

interface ImageUploadProps {
  onDatasetReady?: (datasetId: string, numClasses: number, inputSize: number) => void
  onCancel?: () => void
  modelType?: string
}

type UploadStep = 'upload' | 'preview' | 'configure'

// ==================== Helper Functions ====================

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// ==================== Component ====================

export function ImageUpload({ onDatasetReady, onCancel, modelType }: ImageUploadProps) {
  // State
  const [step, setStep] = useState<UploadStep>('upload')
  const [isUploading, setIsUploading] = useState(false)
  const [isConfiguring, setIsConfiguring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  // Dataset state
  const [dataset, setDataset] = useState<ImageDatasetUploadResponse | null>(null)
  const [inputSize, setInputSize] = useState<number>(224)
  const [enableAugmentation, setEnableAugmentation] = useState(true)
  const [normalize, setNormalize] = useState(true)
  const [showClassList, setShowClassList] = useState(true)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // ==================== File Upload ====================

  const handleFileSelect = useCallback(async (file: File) => {
    // Validate file
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Only ZIP files are supported. Please upload a ZIP archive containing image folders.')
      return
    }

    const maxSize = 100 * 1024 * 1024 // 100MB
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 100MB')
      return
    }

    setError(null)
    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', file.name.replace('.zip', ''))

      const response = await apiClient.uploadImageDataset(formData)
      setDataset(response)
      setInputSize(response.recommended_input_size || 224)

      setStep('preview')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file')
    } finally {
      setIsUploading(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [handleFileSelect])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }, [handleFileSelect])

  // ==================== Configuration ====================

  const handleUseDataset = async () => {
    if (!dataset) return

    setIsConfiguring(true)
    setError(null)

    try {
      // Configure the image dataset
      await apiClient.configureImageDataset({
        dataset_id: dataset.id,
        input_size: inputSize,
        augmentation: enableAugmentation,
        normalize: normalize
      })

      // Notify parent
      if (onDatasetReady) {
        onDatasetReady(dataset.id, dataset.num_classes, inputSize)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to configure dataset')
    } finally {
      setIsConfiguring(false)
    }
  }

  // ==================== Render ====================

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="p-4 border-b border-[hsl(var(--bolt-border))]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-[hsl(var(--bolt-accent))]" />
            <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
              Upload Image Dataset
            </h2>
          </div>
          {onCancel && (
            <button
              onClick={onCancel}
              className="p-1 rounded hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
            >
              <X className="w-5 h-5 text-[hsl(var(--bolt-text-secondary))]" />
            </button>
          )}
        </div>
        <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">
          {step === 'upload' && 'Upload a ZIP file with image folders (max 100MB)'}
          {step === 'preview' && 'Review detected classes and images'}
          {step === 'configure' && 'Configure image preprocessing options'}
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[hsl(var(--bolt-border))]">
        {(['upload', 'preview', 'configure'] as UploadStep[]).map((s, idx) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                step === s
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : idx < ['upload', 'preview', 'configure'].indexOf(step)
                  ? 'bg-green-500 text-white'
                  : 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-tertiary))]'
              }`}
            >
              {idx < ['upload', 'preview', 'configure'].indexOf(step) ? (
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
          {step === 'upload' && 'Upload'}
          {step === 'preview' && 'Preview'}
          {step === 'configure' && 'Configure'}
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

        {/* Step 1: Upload */}
        {step === 'upload' && (
          <div className="space-y-4">
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                isDragging
                  ? 'border-[hsl(var(--bolt-accent))] bg-[hsl(var(--bolt-accent))]/10'
                  : 'border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))]/50'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleInputChange}
                className="hidden"
              />

              {isUploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="w-10 h-10 text-[hsl(var(--bolt-accent))] animate-spin" />
                  <p className="text-[hsl(var(--bolt-text-secondary))]">
                    Uploading and analyzing images...
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Archive className="w-10 h-10 text-[hsl(var(--bolt-text-tertiary))]" />
                  <div>
                    <p className="text-[hsl(var(--bolt-text-primary))] font-medium">
                      Drag & drop your ZIP file here
                    </p>
                    <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">
                      or{' '}
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="text-[hsl(var(--bolt-accent))] hover:underline"
                      >
                        browse
                      </button>{' '}
                      to select
                    </p>
                  </div>
                  <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
                    Maximum file size: 100MB
                  </p>
                </div>
              )}
            </div>

            {/* Expected Format */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <div className="flex items-center gap-2 mb-2">
                <Info className="w-4 h-4 text-blue-400" />
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">Expected Format</span>
              </div>
              <div className="text-xs text-[hsl(var(--bolt-text-secondary))] space-y-1 font-mono">
                <p>dataset.zip/</p>
                <p className="pl-4">class_1/</p>
                <p className="pl-8">image1.jpg</p>
                <p className="pl-8">image2.png</p>
                <p className="pl-4">class_2/</p>
                <p className="pl-8">image1.jpg</p>
                <p className="pl-8">...</p>
              </div>
              <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mt-2">
                Each folder name becomes a class label. Supports JPG, PNG, JPEG, BMP, GIF.
              </p>
            </div>
          </div>
        )}

        {/* Step 2: Preview */}
        {step === 'preview' && dataset && (
          <div className="space-y-4">
            {/* Dataset Info */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Archive className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                  <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                    {dataset.original_filename}
                  </span>
                </div>
                <span className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
                  {formatFileSize(dataset.size_bytes)}
                </span>
              </div>
              <div className="flex gap-4 text-sm text-[hsl(var(--bolt-text-secondary))]">
                <span className="flex items-center gap-1">
                  <ImageIcon className="w-4 h-4" />
                  {dataset.total_images.toLocaleString()} images
                </span>
                <span className="flex items-center gap-1">
                  <Layers className="w-4 h-4" />
                  {dataset.num_classes} classes
                </span>
              </div>
            </div>

            {/* Image Info */}
            {dataset.image_info && (
              <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
                <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
                  Image Statistics
                </h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="text-[hsl(var(--bolt-text-secondary))]">
                    Formats: <span className="text-[hsl(var(--bolt-text-primary))]">
                      {dataset.image_info.formats.join(', ')}
                    </span>
                  </div>
                  {dataset.image_info.avg_width && dataset.image_info.avg_height && (
                    <div className="text-[hsl(var(--bolt-text-secondary))]">
                      Avg Size: <span className="text-[hsl(var(--bolt-text-primary))]">
                        {dataset.image_info.avg_width}x{dataset.image_info.avg_height}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Split Info */}
            {dataset.split_info?.has_split && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <div className="flex items-center gap-2 mb-1">
                  <Check className="w-4 h-4 text-green-400" />
                  <span className="font-medium text-green-400">Pre-defined Splits Detected</span>
                </div>
                <div className="flex gap-4 text-xs text-[hsl(var(--bolt-text-secondary))]">
                  <span>Train: {dataset.split_info.train_count}</span>
                  {dataset.split_info.val_count > 0 && <span>Val: {dataset.split_info.val_count}</span>}
                  {dataset.split_info.test_count > 0 && <span>Test: {dataset.split_info.test_count}</span>}
                </div>
              </div>
            )}

            {/* Classes Detected */}
            <div>
              <button
                onClick={() => setShowClassList(!showClassList)}
                className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2 flex items-center gap-2"
              >
                {showClassList ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <FolderOpen className="w-4 h-4" />
                Classes Detected ({dataset.num_classes})
              </button>
              {showClassList && (
                <div className="space-y-2 max-h-[200px] overflow-y-auto">
                  {dataset.classes.map((cls, idx) => (
                    <div
                      key={cls.name}
                      className="flex items-center justify-between p-2 rounded bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded bg-[hsl(var(--bolt-accent))]/20 text-[hsl(var(--bolt-accent))] flex items-center justify-center text-xs font-medium">
                          {idx + 1}
                        </span>
                        <span className="text-sm text-[hsl(var(--bolt-text-primary))]">
                          {cls.name}
                        </span>
                      </div>
                      <span className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
                        {cls.image_count} images
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recommended Input Size */}
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Recommended input size:{' '}
                  <span className="font-medium text-blue-400">
                    {dataset.recommended_input_size}x{dataset.recommended_input_size}
                  </span>
                </span>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  setStep('upload')
                  setDataset(null)
                }}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => setStep('configure')}
                className="flex-1 py-2 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Configure */}
        {step === 'configure' && dataset && (
          <div className="space-y-4">
            {/* Summary */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <div className="flex items-center gap-2 mb-2">
                <Layers className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                <span className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Classes:
                </span>
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {dataset.num_classes}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-green-400" />
                <span className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Total Images:
                </span>
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {dataset.total_images.toLocaleString()}
                </span>
              </div>
            </div>

            {/* Input Size */}
            <div>
              <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-1">
                Input Size (px)
              </label>
              <select
                value={inputSize}
                onChange={(e) => setInputSize(parseInt(e.target.value))}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
              >
                <option value="32">32x32 (CIFAR-style)</option>
                <option value="64">64x64</option>
                <option value="128">128x128</option>
                <option value="224">224x224 (ImageNet-style)</option>
                <option value="256">256x256</option>
                <option value="299">299x299 (Inception-style)</option>
                <option value="384">384x384</option>
                <option value="512">512x512</option>
              </select>
              <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mt-1">
                Images will be resized to this dimension for training
              </p>
            </div>

            {/* Augmentation Toggle */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <input
                type="checkbox"
                id="augmentation"
                checked={enableAugmentation}
                onChange={(e) => setEnableAugmentation(e.target.checked)}
                className="w-4 h-4 rounded"
              />
              <label htmlFor="augmentation" className="flex-1">
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  Enable Data Augmentation
                </span>
                <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                  Random flips, rotations, and color adjustments to improve generalization
                </p>
              </label>
            </div>

            {/* Normalize Toggle */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <input
                type="checkbox"
                id="normalize"
                checked={normalize}
                onChange={(e) => setNormalize(e.target.checked)}
                className="w-4 h-4 rounded"
              />
              <label htmlFor="normalize" className="flex-1">
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  Normalize Images
                </span>
                <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                  Apply ImageNet normalization (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                </p>
              </label>
            </div>

            {/* Navigation */}
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setStep('preview')}
                className="px-4 py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleUseDataset}
                disabled={isConfiguring}
                className="flex-1 py-2 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isConfiguring ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Configuring...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Use Dataset
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
