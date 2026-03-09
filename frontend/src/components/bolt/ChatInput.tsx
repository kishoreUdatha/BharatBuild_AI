'use client'

import { useState, useRef, useEffect, KeyboardEvent, ChangeEvent } from 'react'
import {
  Square,
  Paperclip,
  FileText,
  X,
  Plus,
  Sparkles
} from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string, fileContent?: string) => void
  onStop?: () => void
  isLoading?: boolean
  placeholder?: string
  disabled?: boolean
}

interface AttachedFile {
  name: string
  content: string
  type: string
  size: number
}

/**
 * Modern chat input component - ChatGPT/Bolt.new style
 * Clean, minimal design with smooth animations
 */
export function ChatInput({
  onSend,
  onStop,
  isLoading = false,
  placeholder,
  disabled = false
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [attachedFile, setAttachedFile] = useState<AttachedFile | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [showAttachMenu, setShowAttachMenu] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const attachMenuRef = useRef<HTMLDivElement>(null)

  // Close attach menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (attachMenuRef.current && !attachMenuRef.current.contains(event.target as Node)) {
        setShowAttachMenu(false)
      }
    }
    if (showAttachMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showAttachMenu])

  // Supported file types
  const SUPPORTED_TYPES = [
    'text/plain',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
  const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setFileError(null)

    if (!SUPPORTED_TYPES.includes(file.type) && !file.name.endsWith('.txt')) {
      setFileError('Please upload a TXT, PDF, or Word document')
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      setFileError('File size must be less than 5MB')
      return
    }

    try {
      let content = ''

      if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
        content = await file.text()
      } else if (file.type === 'application/pdf') {
        content = `[PDF File Uploaded: ${file.name}]\n\nPlease extract and use the content from this PDF for project generation.`
      } else {
        content = `[Document Uploaded: ${file.name}]\n\nPlease use the content from this document for project generation.`
      }

      setAttachedFile({
        name: file.name,
        content,
        type: file.type,
        size: file.size
      })
    } catch (err) {
      setFileError('Failed to read file. Please try again.')
      console.error('File read error:', err)
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeAttachedFile = () => {
    setAttachedFile(null)
    setFileError(null)
  }

  const handleSubmit = () => {
    const hasContent = message.trim() || attachedFile
    if (hasContent && !isLoading && !disabled) {
      let fullMessage = message.trim()

      if (attachedFile) {
        const filePrefix = fullMessage
          ? `${fullMessage}\n\n--- Project Abstract/Requirements ---\n\n`
          : 'Generate a project based on this abstract:\n\n--- Project Abstract/Requirements ---\n\n'
        fullMessage = filePrefix + attachedFile.content
      }

      onSend(fullMessage, attachedFile?.content)
      setMessage('')
      setAttachedFile(null)
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [message])

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const canSubmit = (message.trim().length > 0 || attachedFile) && !isLoading && !disabled

  return (
    <div className="p-3 md:p-4">
      <div className="max-w-4xl mx-auto">
        {/* Attached File Preview - Above input */}
        {attachedFile && (
          <div className="mb-3">
            <div className="inline-flex items-center gap-3 px-4 py-2.5 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-white truncate max-w-[250px]">{attachedFile.name}</p>
                <p className="text-xs text-gray-400">{(attachedFile.size / 1024).toFixed(1)} KB</p>
              </div>
              <button
                type="button"
                onClick={removeAttachedFile}
                className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors flex-shrink-0"
                title="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* File Error */}
        {fileError && (
          <div className="mb-3">
            <p className="text-sm text-red-400 bg-red-500/10 px-3 py-2 rounded-lg">{fileError}</p>
          </div>
        )}

        {/* Main Input Container */}
        <div
          className={`relative bg-[#1a1a2e] rounded-2xl border-2 transition-all duration-300 ${
            isFocused
              ? 'border-blue-500/50 shadow-lg shadow-blue-500/10'
              : 'border-gray-700/50 hover:border-gray-600/50'
          }`}
        >
          {/* Input Row */}
          <div className="flex items-end">
            {/* Plus Button - Small */}
            <div className="relative pl-3 pr-1 py-3" ref={attachMenuRef}>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.pdf,.doc,.docx"
                onChange={handleFileSelect}
                className="hidden"
              />

              <button
                type="button"
                onClick={() => setShowAttachMenu(!showAttachMenu)}
                disabled={isLoading || disabled}
                className={`w-6 h-6 rounded-full flex items-center justify-center transition-all duration-200 ${
                  showAttachMenu
                    ? 'bg-blue-500 text-white rotate-45'
                    : 'text-gray-500 hover:text-white hover:bg-gray-700'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
                title="Add attachment"
              >
                <Plus className="w-4 h-4 transition-transform duration-200" />
              </button>

              {/* Dropdown Menu */}
              {showAttachMenu && (
                <div className="absolute bottom-full left-0 mb-2 w-48 bg-[#1e1e32] border border-gray-700 rounded-lg shadow-2xl shadow-black/40 overflow-hidden z-50">
                  <button
                    type="button"
                    onClick={() => {
                      fileInputRef.current?.click()
                      setShowAttachMenu(false)
                    }}
                    className="flex items-center gap-2.5 w-full px-3 py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors"
                  >
                    <Paperclip className="w-4 h-4 text-blue-400" />
                    <span>Attach File</span>
                  </button>
                </div>
              )}
            </div>

            {/* Textarea */}
            <div className="flex-1 py-3 pr-2">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                placeholder={placeholder || "Describe your project idea..."}
                disabled={isLoading || disabled}
                rows={1}
                className="w-full bg-transparent text-white text-[15px] placeholder:text-gray-500 resize-none focus:outline-none max-h-[200px] scrollbar-thin disabled:opacity-50 leading-relaxed"
                style={{ minHeight: '28px' }}
              />
            </div>

            {/* Stop Button - Only show when loading */}
            {isLoading && (
              <div className="p-2">
                <button
                  type="button"
                  onClick={onStop}
                  className="w-8 h-8 rounded-lg bg-red-500 hover:bg-red-600 text-white flex items-center justify-center transition-all duration-200"
                  title="Stop generating"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Helper Text */}
        <div className="flex items-center justify-center mt-2.5">
          <p className="text-xs text-gray-500">
            {isLoading ? (
              <span className="flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
                <span>Generating your project...</span>
              </span>
            ) : attachedFile ? (
              <span className="text-blue-400">
                File attached - Press Enter or click send to generate
              </span>
            ) : (
              <span>
                <kbd className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-mono text-[10px] mr-1">Enter</kbd>
                to send
                <span className="mx-2 text-gray-600">|</span>
                <kbd className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-400 font-mono text-[10px] mr-1">Shift + Enter</kbd>
                for new line
              </span>
            )}
          </p>
        </div>
      </div>
    </div>
  )
}

export default ChatInput
