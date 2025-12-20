'use client'

import { useEffect, useCallback, useState, useMemo } from 'react'
import Editor from '@monaco-editor/react'
import { useProject } from '@/hooks/useProject'
import { useAutoSave } from '@/hooks/useAutoSave'
import { usePlanStatus } from '@/hooks/usePlanStatus'
import { CodeTabs } from './CodeTabs'
import { monacoThemeDark, monacoThemeLight } from '@/utils/editorThemes'
import { Code2, Cloud, CloudOff, Loader2, Eye, EyeOff, Columns, FileText, Lock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Markdown preview view modes (like IntelliJ)
type MarkdownViewMode = 'editor' | 'split' | 'preview'

export function CodeEditor() {
  // Theme state
  const [editorTheme, setEditorTheme] = useState<'bharatbuild-dark' | 'bharatbuild-light'>('bharatbuild-dark')
  // Markdown preview mode - default to full preview for better readability
  const [markdownViewMode, setMarkdownViewMode] = useState<MarkdownViewMode>('preview')

  // Direct store access (like your example)
  const {
    selectedFile: activeFile,
    openTabs,
    activeTabPath,
    updateFile,
    setActiveTab,
    closeTab,
    currentProject
  } = useProject()

  // Check if user has premium features (for copy restriction)
  const { features, isPremium, isLoading: planLoading } = usePlanStatus()
  const canCopyCode = isPremium || features?.download_files === true

  // Check if current file is markdown
  const isMarkdownFile = useMemo(() => {
    if (!activeFile?.path) return false
    const ext = activeFile.path.split('.').pop()?.toLowerCase()
    return ext === 'md' || ext === 'markdown'
  }, [activeFile?.path])

  // Auto-save hook with 1.5 second debounce
  const {
    isSaving,
    lastSaved,
    hasPendingChanges,
    scheduleSync
  } = useAutoSave({ debounceMs: 1500, enabled: true })

  // Handle file content changes with auto-save
  const handleEditorChange = useCallback((value: string | undefined) => {
    if (!activeFile) return

    const content = value ?? ''

    // Update Zustand store immediately
    updateFile(activeFile.path, content)

    // Schedule debounced sync to backend
    if (currentProject?.id) {
      scheduleSync(activeFile.path, content)
    }
  }, [activeFile, updateFile, currentProject?.id, scheduleSync])

  // Load custom themes and configure copy restrictions
  const handleEditorWillMount = (monaco: any) => {
    monaco.editor.defineTheme('bharatbuild-dark', monacoThemeDark)
    monaco.editor.defineTheme('bharatbuild-light', monacoThemeLight)
  }

  // Handle editor mount - add copy/cut restrictions for non-premium users
  const handleEditorDidMount = useCallback((editor: any, monaco: any) => {
    if (!canCopyCode) {
      // Disable copy command
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyC, () => {
        // Show notification instead of copying
        console.log('[CodeEditor] Copy blocked - Premium feature')
      })

      // Disable cut command
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyX, () => {
        console.log('[CodeEditor] Cut blocked - Premium feature')
      })

      // Disable context menu copy/cut actions
      const contextmenu = editor.getContribution('editor.contrib.contextmenu')
      if (contextmenu) {
        const originalGetMenuActions = contextmenu._getMenuActions?.bind(contextmenu)
        if (originalGetMenuActions) {
          contextmenu._getMenuActions = () => {
            const actions = originalGetMenuActions()
            // Filter out copy, cut, paste actions
            return actions.filter((action: any) => {
              const id = action.id?.toLowerCase() || ''
              return !id.includes('copy') && !id.includes('cut')
            })
          }
        }
      }
    }
  }, [canCopyCode])

  // Watch for theme changes on document
  useEffect(() => {
    const updateTheme = () => {
      const isDark = document.documentElement.classList.contains('dark')
      setEditorTheme(isDark ? 'bharatbuild-dark' : 'bharatbuild-light')
    }

    // Initial check
    updateTheme()

    // Watch for class changes on documentElement
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          updateTheme()
        }
      })
    })

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    })

    return () => observer.disconnect()
  }, [])

  // Auto-detect language from file extension
  const getLanguage = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase()
    const languageMap: Record<string, string> = {
      // Web Development
      js: 'javascript',
      jsx: 'javascript',
      ts: 'typescript',
      tsx: 'typescript',
      html: 'html',
      css: 'css',
      scss: 'scss',
      sass: 'sass',
      less: 'less',
      php: 'php',

      // AI/ML & Data Science
      py: 'python',
      r: 'r',
      R: 'r',
      jl: 'julia',
      m: 'matlab',
      ipynb: 'json',  // Jupyter notebooks

      // Systems Programming
      java: 'java',
      cpp: 'cpp',
      c: 'c',
      cs: 'csharp',
      go: 'go',
      rs: 'rust',
      rb: 'ruby',
      kt: 'kotlin',
      scala: 'scala',
      swift: 'swift',

      // Data & Config
      json: 'json',
      xml: 'xml',
      yaml: 'yaml',
      yml: 'yaml',
      toml: 'toml',
      csv: 'plaintext',

      // Database
      sql: 'sql',

      // Shell & Scripts
      sh: 'shell',
      bash: 'shell',
      ps1: 'powershell',
      bat: 'bat',

      // Documentation
      md: 'markdown',
      rst: 'restructuredtext',
      tex: 'latex',

      // Other
      dockerfile: 'dockerfile',
      makefile: 'makefile',
      gradle: 'groovy',
    }
    return languageMap[ext || ''] || 'plaintext'
  }

  // Empty state when no file selected
  if (!activeFile) {
    return (
      <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
        {/* Tabs (empty state) */}
        <CodeTabs
          tabs={openTabs}
          activeTabPath={activeTabPath}
          onTabClick={(path) => setActiveTab(path)}
          onTabClose={(path, e) => {
            e.stopPropagation()
            closeTab(path)
          }}
        />

        {/* Empty state */}
        <div className="flex-1 flex items-center justify-center text-[hsl(var(--bolt-text-secondary))]">
          <div className="text-center">
            <Code2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Select a file to view code</p>
          </div>
        </div>
      </div>
    )
  }

  const language = getLanguage(activeFile.path)

  // Format last saved time
  const formatLastSaved = () => {
    if (!lastSaved) return null
    const now = new Date()
    const diff = Math.floor((now.getTime() - lastSaved.getTime()) / 1000)
    if (diff < 5) return 'Just saved'
    if (diff < 60) return `Saved ${diff}s ago`
    if (diff < 3600) return `Saved ${Math.floor(diff / 60)}m ago`
    return lastSaved.toLocaleTimeString()
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))] overflow-hidden">
      {/* TABS with Save Status */}
      <div className="flex items-center justify-between">
        <div className="flex-1 overflow-hidden">
          <CodeTabs
            tabs={openTabs}
            activeTabPath={activeTabPath}
            onTabClick={(path) => setActiveTab(path)}
            onTabClose={(path, e) => {
              e.stopPropagation()
              closeTab(path)
            }}
          />
        </div>

        {/* Copy Restriction Banner for Non-Premium Users */}
        {!canCopyCode && !planLoading && (
          <a
            href="/pricing"
            className="flex items-center gap-1.5 px-3 py-1 mr-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs hover:bg-amber-500/20 transition-colors"
            title="Upgrade to copy code"
          >
            <Lock className="w-3 h-3" />
            <span>Copy restricted</span>
          </a>
        )}

        {/* Save Status Indicator */}
        {currentProject?.id && (
          <div className="flex items-center gap-1.5 px-3 text-xs text-[hsl(var(--bolt-text-tertiary))]">
            {isSaving ? (
              <>
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Saving...</span>
              </>
            ) : hasPendingChanges ? (
              <>
                <CloudOff className="w-3 h-3 text-yellow-500" />
                <span className="text-yellow-500">Unsaved</span>
              </>
            ) : lastSaved ? (
              <>
                <Cloud className="w-3 h-3 text-green-500" />
                <span className="text-green-500">{formatLastSaved()}</span>
              </>
            ) : null}
          </div>
        )}
      </div>

      {/* Markdown View Mode Toggle (like IntelliJ) */}
      {isMarkdownFile && (
        <div className="flex items-center justify-end gap-1 px-2 py-1 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
          <span className="text-xs text-[hsl(var(--bolt-text-tertiary))] mr-2">Preview:</span>
          <button
            onClick={() => setMarkdownViewMode('editor')}
            className={`p-1.5 rounded transition-colors ${
              markdownViewMode === 'editor'
                ? 'bg-blue-500/20 text-blue-400'
                : 'hover:bg-white/10 text-gray-400'
            }`}
            title="Editor Only"
          >
            <Code2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setMarkdownViewMode('split')}
            className={`p-1.5 rounded transition-colors ${
              markdownViewMode === 'split'
                ? 'bg-blue-500/20 text-blue-400'
                : 'hover:bg-white/10 text-gray-400'
            }`}
            title="Split View (Editor + Preview)"
          >
            <Columns className="w-4 h-4" />
          </button>
          <button
            onClick={() => setMarkdownViewMode('preview')}
            className={`p-1.5 rounded transition-colors ${
              markdownViewMode === 'preview'
                ? 'bg-blue-500/20 text-blue-400'
                : 'hover:bg-white/10 text-gray-400'
            }`}
            title="Preview Only"
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* EDITOR - with flex-1 to fill remaining space and proper overflow */}
      <div className="flex-1 overflow-hidden flex">
        {/* Editor Panel */}
        {(!isMarkdownFile || markdownViewMode !== 'preview') && (
          <div className={`overflow-hidden ${isMarkdownFile && markdownViewMode === 'split' ? 'w-1/2 border-r border-[hsl(var(--bolt-border))]' : 'w-full'}`}>
            <Editor
              height="100%"
              theme={editorTheme}
              language={language}
              value={activeFile.content}
              beforeMount={handleEditorWillMount}
              onMount={handleEditorDidMount}
              onChange={handleEditorChange}
              options={{
                fontSize: 14,
                minimap: { enabled: !isMarkdownFile || markdownViewMode === 'editor', maxColumn: 80 },
                smoothScrolling: true,
                padding: { top: 10 },
                renderLineHighlight: 'line',
                scrollBeyondLastLine: true,
                lineNumbers: 'on',
                roundedSelection: false,
                automaticLayout: true,
                tabSize: 2,
                wordWrap: isMarkdownFile ? 'on' : 'off',
                folding: true,
                lineDecorationsWidth: 10,
                lineNumbersMinChars: 3,
                scrollbar: {
                  vertical: 'visible',
                  horizontal: 'visible',
                  useShadows: true,
                  verticalScrollbarSize: 14,
                  horizontalScrollbarSize: 14,
                  verticalHasArrows: false,
                  horizontalHasArrows: false,
                  arrowSize: 30,
                },
                overviewRulerBorder: true,
                overviewRulerLanes: 3,
                bracketPairColorization: {
                  enabled: true,
                },
                guides: {
                  indentation: true,
                  bracketPairs: true,
                },
                suggest: {
                  showKeywords: true,
                  showSnippets: true,
                },
                quickSuggestions: {
                  other: true,
                  comments: false,
                  strings: false,
                },
              }}
            />
          </div>
        )}

        {/* Markdown Preview Panel (like IntelliJ) */}
        {isMarkdownFile && markdownViewMode !== 'editor' && (
          <div className={`overflow-auto bg-[hsl(var(--bolt-bg-primary))] ${markdownViewMode === 'split' ? 'w-1/2' : 'w-full'}`}>
            <div className="p-6 prose prose-invert prose-sm max-w-none
              prose-headings:text-white prose-headings:font-semibold prose-headings:border-b prose-headings:border-gray-700 prose-headings:pb-2
              prose-h1:text-2xl prose-h1:mt-0
              prose-h2:text-xl
              prose-h3:text-lg
              prose-p:text-gray-300 prose-p:leading-relaxed
              prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
              prose-strong:text-white prose-strong:font-semibold
              prose-code:text-cyan-400 prose-code:bg-gray-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
              prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-700 prose-pre:rounded-lg
              prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-500/10 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r
              prose-ul:text-gray-300 prose-ol:text-gray-300
              prose-li:marker:text-gray-500
              prose-table:border-collapse
              prose-th:bg-gray-800 prose-th:text-white prose-th:border prose-th:border-gray-700 prose-th:px-3 prose-th:py-2
              prose-td:border prose-td:border-gray-700 prose-td:px-3 prose-td:py-2
              prose-hr:border-gray-700
              prose-img:rounded-lg prose-img:shadow-lg
            ">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeFile.content || ''}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
