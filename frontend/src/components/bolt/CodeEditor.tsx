'use client'

import { useEffect } from 'react'
import Editor from '@monaco-editor/react'
import { useProject } from '@/hooks/useProject'
import { CodeTabs } from './CodeTabs'
import { monacoTheme } from '@/utils/editorThemes'
import { Code2 } from 'lucide-react'

export function CodeEditor() {
  // Direct store access (like your example)
  const {
    selectedFile: activeFile,
    openTabs,
    activeTabPath,
    updateFile,
    setActiveTab,
    closeTab
  } = useProject()

  // Load custom theme
  const handleEditorWillMount = (monaco: any) => {
    monaco.editor.defineTheme('bharatbuild', monacoTheme)
  }

  // Auto-detect language from file extension
  const getLanguage = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase()
    const languageMap: Record<string, string> = {
      js: 'javascript',
      jsx: 'javascript',
      ts: 'typescript',
      tsx: 'typescript',
      py: 'python',
      java: 'java',
      cpp: 'cpp',
      c: 'c',
      cs: 'csharp',
      rb: 'ruby',
      go: 'go',
      rs: 'rust',
      php: 'php',
      html: 'html',
      css: 'css',
      scss: 'scss',
      sass: 'sass',
      less: 'less',
      json: 'json',
      xml: 'xml',
      yaml: 'yaml',
      yml: 'yaml',
      md: 'markdown',
      sql: 'sql',
      sh: 'shell',
      bash: 'shell',
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

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* TABS - Integrated inside CodeEditor */}
      <CodeTabs
        tabs={openTabs}
        activeTabPath={activeTabPath}
        onTabClick={(path) => setActiveTab(path)}
        onTabClose={(path, e) => {
          e.stopPropagation()
          closeTab(path)
        }}
      />

      {/* EDITOR */}
      <Editor
        height="100%"
        theme="bharatbuild"
        language={language}
        value={activeFile.content}
        beforeMount={handleEditorWillMount}
        onChange={(value) => {
          // Update file content in Zustand store
          updateFile(activeFile.path, value ?? '')
        }}
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          smoothScrolling: true,
          padding: { top: 10 },
          renderLineHighlight: 'line',
          scrollBeyondLastLine: false,
          lineNumbers: 'on',
          roundedSelection: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          folding: true,
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 3,
          scrollbar: {
            vertical: 'auto',
            horizontal: 'auto',
            useShadows: false,
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
          },
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
  )
}
