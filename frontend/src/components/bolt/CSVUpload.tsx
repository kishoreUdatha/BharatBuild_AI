'use client'

import { useState, useRef, useCallback } from 'react'
import {
  Upload,
  FileSpreadsheet,
  X,
  Check,
  AlertCircle,
  Loader2,
  Database,
  Target,
  Columns,
  Hash,
  Type,
  ToggleLeft,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'

// ==================== Types ====================

interface ColumnInfo {
  name: string
  dtype: string
  sample_values: any[]
  null_count: number
  unique_count: number
  is_numeric: boolean
  is_categorical: boolean
  suggested_encoding?: string
}

interface DatasetUploadResponse {
  id: string
  name: string
  original_filename: string
  size_bytes: number
  row_count: number
  column_count: number
  columns: ColumnInfo[]
  preview_rows: Record<string, any>[]
  status: string
  message: string
}

interface CSVUploadProps {
  onDatasetReady?: (datasetId: string, targetColumn: string, featureColumns: string[]) => void
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

const getTypeIcon = (dtype: string) => {
  switch (dtype) {
    case 'int':
    case 'float':
      return Hash
    case 'string':
      return Type
    case 'bool':
      return ToggleLeft
    default:
      return Database
  }
}

const getTypeColor = (dtype: string): string => {
  switch (dtype) {
    case 'int':
      return 'text-blue-400'
    case 'float':
      return 'text-green-400'
    case 'string':
      return 'text-yellow-400'
    case 'bool':
      return 'text-purple-400'
    default:
      return 'text-gray-400'
  }
}

// ==================== Component ====================

export function CSVUpload({ onDatasetReady, onCancel, modelType }: CSVUploadProps) {
  // State
  const [step, setStep] = useState<UploadStep>('upload')
  const [isUploading, setIsUploading] = useState(false)
  const [isConfiguring, setIsConfiguring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  // Dataset state
  const [dataset, setDataset] = useState<DatasetUploadResponse | null>(null)
  const [targetColumn, setTargetColumn] = useState<string>('')
  const [featureColumns, setFeatureColumns] = useState<string[]>([])
  const [showPreviewTable, setShowPreviewTable] = useState(true)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // ==================== File Upload ====================

  const handleFileSelect = useCallback(async (file: File) => {
    // Validate file
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Only CSV files are supported')
      return
    }

    const maxSize = 10 * 1024 * 1024 // 10MB
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 10MB')
      return
    }

    setError(null)
    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', file.name.replace('.csv', ''))

      const response = await apiClient.uploadDataset(formData)
      setDataset(response)

      // Auto-select numeric columns as features
      const numericCols = response.columns
        .filter((c: ColumnInfo) => c.is_numeric)
        .map((c: ColumnInfo) => c.name)

      // Try to find a good target column (last column or one with few unique values)
      const lastCol = response.columns[response.columns.length - 1]
      const suggestedTarget = response.columns.find(
        (c: ColumnInfo) => c.is_categorical && c.unique_count <= 10
      ) || lastCol

      setTargetColumn(suggestedTarget?.name || '')
      setFeatureColumns(
        numericCols.filter((name: string) => name !== suggestedTarget?.name)
      )

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

  const toggleFeatureColumn = (colName: string) => {
    if (colName === targetColumn) return // Can't toggle target column

    setFeatureColumns(prev =>
      prev.includes(colName)
        ? prev.filter(c => c !== colName)
        : [...prev, colName]
    )
  }

  const handleSelectTarget = (colName: string) => {
    setTargetColumn(colName)
    // Remove from features if it was selected
    setFeatureColumns(prev => prev.filter(c => c !== colName))
  }

  const selectAllFeatures = () => {
    if (!dataset) return
    setFeatureColumns(
      dataset.columns
        .map(c => c.name)
        .filter(name => name !== targetColumn)
    )
  }

  const deselectAllFeatures = () => {
    setFeatureColumns([])
  }

  const handleUseDataset = async () => {
    if (!dataset || !targetColumn) return

    setIsConfiguring(true)
    setError(null)

    try {
      // Configure the dataset
      await apiClient.configureDataset({
        dataset_id: dataset.id,
        target_column: targetColumn,
        feature_columns: featureColumns.length > 0 ? featureColumns : undefined
      })

      // Notify parent
      if (onDatasetReady) {
        onDatasetReady(dataset.id, targetColumn, featureColumns)
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
            <FileSpreadsheet className="w-5 h-5 text-[hsl(var(--bolt-accent))]" />
            <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))]">
              Upload Training Data
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
          {step === 'upload' && 'Upload a CSV file for model training (max 10MB)'}
          {step === 'preview' && 'Review your data and select target column'}
          {step === 'configure' && 'Configure features for training'}
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
              accept=".csv"
              onChange={handleInputChange}
              className="hidden"
            />

            {isUploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-[hsl(var(--bolt-accent))] animate-spin" />
                <p className="text-[hsl(var(--bolt-text-secondary))]">
                  Uploading and analyzing...
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <Upload className="w-10 h-10 text-[hsl(var(--bolt-text-tertiary))]" />
                <div>
                  <p className="text-[hsl(var(--bolt-text-primary))] font-medium">
                    Drag & drop your CSV file here
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
                  Maximum file size: 10MB
                </p>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Preview */}
        {step === 'preview' && dataset && (
          <div className="space-y-4">
            {/* Dataset Info */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                  <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                    {dataset.original_filename}
                  </span>
                </div>
                <span className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
                  {formatFileSize(dataset.size_bytes)}
                </span>
              </div>
              <div className="flex gap-4 text-sm text-[hsl(var(--bolt-text-secondary))]">
                <span>{dataset.row_count.toLocaleString()} rows</span>
                <span>{dataset.column_count} columns</span>
              </div>
            </div>

            {/* Columns Detected */}
            <div>
              <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2 flex items-center gap-2">
                <Columns className="w-4 h-4" />
                Columns Detected
              </h3>
              <div className="flex flex-wrap gap-2">
                {dataset.columns.map(col => {
                  const TypeIcon = getTypeIcon(col.dtype)
                  return (
                    <div
                      key={col.name}
                      className="flex items-center gap-1.5 px-2 py-1 rounded bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]"
                    >
                      <TypeIcon className={`w-3 h-3 ${getTypeColor(col.dtype)}`} />
                      <span className="text-xs text-[hsl(var(--bolt-text-primary))]">
                        {col.name}
                      </span>
                      <span className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
                        [{col.dtype}]
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Preview Table */}
            <div>
              <button
                onClick={() => setShowPreviewTable(!showPreviewTable)}
                className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2 flex items-center gap-2"
              >
                {showPreviewTable ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                Preview Data
              </button>
              {showPreviewTable && dataset.preview_rows.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-[hsl(var(--bolt-border))]">
                  <table className="w-full text-xs">
                    <thead className="bg-[hsl(var(--bolt-bg-secondary))]">
                      <tr>
                        {dataset.columns.map(col => (
                          <th
                            key={col.name}
                            className="px-2 py-1.5 text-left font-medium text-[hsl(var(--bolt-text-secondary))] whitespace-nowrap"
                          >
                            {col.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dataset.preview_rows.slice(0, 3).map((row, idx) => (
                        <tr
                          key={idx}
                          className="border-t border-[hsl(var(--bolt-border))]"
                        >
                          {dataset.columns.map(col => (
                            <td
                              key={col.name}
                              className="px-2 py-1.5 text-[hsl(var(--bolt-text-primary))] whitespace-nowrap max-w-[150px] truncate"
                            >
                              {String(row[col.name] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Target Column Selection */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2 flex items-center gap-2">
                <Target className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                Select Target Column (what to predict)
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {dataset.columns.map(col => (
                  <button
                    key={col.name}
                    onClick={() => handleSelectTarget(col.name)}
                    className={`px-3 py-2 rounded text-sm text-left transition-colors ${
                      targetColumn === col.name
                        ? 'bg-[hsl(var(--bolt-accent))] text-white'
                        : 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-primary))]'
                    }`}
                  >
                    <div className="font-medium truncate">{col.name}</div>
                    <div className="text-xs opacity-75">
                      {col.unique_count} unique values
                    </div>
                  </button>
                ))}
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
                disabled={!targetColumn}
                className="flex-1 py-2 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Configure Features */}
        {step === 'configure' && dataset && (
          <div className="space-y-4">
            {/* Summary */}
            <div className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                <span className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Target:
                </span>
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {targetColumn}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Columns className="w-4 h-4 text-green-400" />
                <span className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                  Features:
                </span>
                <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {featureColumns.length} selected
                </span>
              </div>
            </div>

            {/* Feature Selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] flex items-center gap-2">
                  <Columns className="w-4 h-4" />
                  Select Feature Columns (inputs)
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllFeatures}
                    className="text-xs text-[hsl(var(--bolt-accent))] hover:underline"
                  >
                    Select all
                  </button>
                  <span className="text-[hsl(var(--bolt-text-tertiary))]">|</span>
                  <button
                    onClick={deselectAllFeatures}
                    className="text-xs text-[hsl(var(--bolt-text-secondary))] hover:underline"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                {dataset.columns
                  .filter(col => col.name !== targetColumn)
                  .map(col => {
                    const TypeIcon = getTypeIcon(col.dtype)
                    const isSelected = featureColumns.includes(col.name)

                    return (
                      <button
                        key={col.name}
                        onClick={() => toggleFeatureColumn(col.name)}
                        className={`w-full p-3 rounded-lg border text-left transition-colors ${
                          isSelected
                            ? 'border-[hsl(var(--bolt-accent))] bg-[hsl(var(--bolt-accent))]/10'
                            : 'border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] hover:border-[hsl(var(--bolt-accent))]/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div
                              className={`w-4 h-4 rounded border flex items-center justify-center ${
                                isSelected
                                  ? 'bg-[hsl(var(--bolt-accent))] border-[hsl(var(--bolt-accent))]'
                                  : 'border-[hsl(var(--bolt-text-tertiary))]'
                              }`}
                            >
                              {isSelected && <Check className="w-3 h-3 text-white" />}
                            </div>
                            <TypeIcon className={`w-4 h-4 ${getTypeColor(col.dtype)}`} />
                            <span className="font-medium text-[hsl(var(--bolt-text-primary))]">
                              {col.name}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-[hsl(var(--bolt-text-tertiary))]">
                            <span>{col.dtype}</span>
                            {col.is_numeric && (
                              <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">
                                numeric
                              </span>
                            )}
                            {col.is_categorical && (
                              <span className="px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400">
                                categorical
                              </span>
                            )}
                          </div>
                        </div>
                        {col.null_count > 0 && (
                          <div className="mt-1 text-xs text-yellow-400 flex items-center gap-1">
                            <Info className="w-3 h-3" />
                            {col.null_count} missing values
                          </div>
                        )}
                      </button>
                    )
                  })}
              </div>
            </div>

            {/* Info */}
            {featureColumns.length === 0 && (
              <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm flex items-center gap-2">
                <Info className="w-4 h-4 flex-shrink-0" />
                Select at least one feature column, or all columns (except target) will be used.
              </div>
            )}

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
