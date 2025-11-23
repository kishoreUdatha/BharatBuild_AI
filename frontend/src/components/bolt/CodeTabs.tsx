'use client'

import { X } from 'lucide-react'
import { ProjectFile } from '@/store/projectStore'
import {
  FileCode,
  FileJson,
  FileText,
  File,
} from 'lucide-react'

interface CodeTabsProps {
  tabs: ProjectFile[]
  activeTabPath: string | null
  onTabClick: (path: string) => void
  onTabClose: (path: string, e: React.MouseEvent) => void
}

const getFileIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase()

  switch (ext) {
    case 'js':
    case 'jsx':
    case 'ts':
    case 'tsx':
    case 'py':
      return FileCode
    case 'json':
      return FileJson
    case 'md':
    case 'txt':
      return FileText
    default:
      return File
  }
}

const getFileName = (path: string): string => {
  return path.split('/').pop() || path
}

export function CodeTabs({ tabs, activeTabPath, onTabClick, onTabClose }: CodeTabsProps) {
  if (tabs.length === 0) {
    return null
  }

  return (
    <div className="flex items-center gap-0.5 bg-[hsl(var(--bolt-bg-secondary))] border-b border-[hsl(var(--bolt-border))] overflow-x-auto scrollbar-thin">
      {tabs.map((tab) => {
        const isActive = activeTabPath === tab.path
        const Icon = getFileIcon(tab.path)
        const fileName = getFileName(tab.path)

        return (
          <div
            key={tab.path}
            onClick={() => onTabClick(tab.path)}
            className={`
              group flex items-center gap-2 px-3 py-2 min-w-[120px] max-w-[200px] cursor-pointer
              border-r border-[hsl(var(--bolt-border))]
              transition-colors relative
              ${
                isActive
                  ? 'bg-[hsl(var(--bolt-bg-primary))] text-[hsl(var(--bolt-text-primary))]'
                  : 'bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
              }
            `}
          >
            {/* Active indicator */}
            {isActive && (
              <div className="absolute top-0 left-0 right-0 h-[2px] bg-[hsl(var(--bolt-accent))]" />
            )}

            {/* File Icon */}
            <Icon className="w-4 h-4 flex-shrink-0" />

            {/* File Name */}
            <span className="text-sm truncate flex-1">
              {fileName}
            </span>

            {/* Close Button */}
            <button
              onClick={(e) => onTabClose(tab.path, e)}
              className={`
                flex-shrink-0 p-0.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))]
                transition-opacity
                ${isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}
              `}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
