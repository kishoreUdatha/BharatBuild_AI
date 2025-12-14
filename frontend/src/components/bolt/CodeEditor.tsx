'use client'

import { useEffect, useCallback, useState } from 'react'
import Editor from '@monaco-editor/react'
import { useProject } from '@/hooks/useProject'
import { useAutoSave } from '@/hooks/useAutoSave'
import { CodeTabs } from './CodeTabs'
import { monacoThemeDark, monacoThemeLight } from '@/utils/editorThemes'
import { Code2, Cloud, CloudOff, Loader2 } from 'lucide-react'

export function CodeEditor() {
  // Theme state
  const [editorTheme, setEditorTheme] = useState<'bharatbuild-dark' | 'bharatbuild-light'>('bharatbuild-dark')
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

  // Load custom themes
  const handleEditorWillMount = (monaco: any) => {
    monaco.editor.defineTheme('bharatbuild-dark', monacoThemeDark)
    monaco.editor.defineTheme('bharatbuild-light', monacoThemeLight)
  }

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

      {/* EDITOR - with flex-1 to fill remaining space and proper overflow */}
      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          theme={editorTheme}
          language={language}
          value={activeFile.content}
          beforeMount={handleEditorWillMount}
          onChange={handleEditorChange}
          options={{
            fontSize: 14,
            minimap: { enabled: true, maxColumn: 80 },
            smoothScrolling: true,
            padding: { top: 10 },
            renderLineHighlight: 'line',
            scrollBeyondLastLine: true,
            lineNumbers: 'on',
            roundedSelection: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: 'off',
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
    </div>
  )
}
