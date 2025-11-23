'use client'

import { useState } from 'react'
import {
  ChevronRight,
  ChevronDown,
  File,
  Folder,
  FolderOpen,
  FileCode,
  FileJson,
  FileText,
} from 'lucide-react'

interface FileNode {
  name: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

interface FileExplorerProps {
  files: FileNode[]
  onFileSelect?: (file: FileNode) => void
  selectedFile?: string
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

function FileTreeNode({
  node,
  level = 0,
  onSelect,
  selectedFile,
}: {
  node: FileNode
  level?: number
  onSelect?: (node: FileNode) => void
  selectedFile?: string
}) {
  const [isExpanded, setIsExpanded] = useState(level === 0)
  const isSelected = selectedFile === node.name

  const handleClick = () => {
    if (node.type === 'folder') {
      setIsExpanded(!isExpanded)
    } else {
      onSelect?.(node)
    }
  }

  const Icon = node.type === 'folder'
    ? (isExpanded ? FolderOpen : Folder)
    : getFileIcon(node.name)

  return (
    <div>
      <div
        onClick={handleClick}
        className={`
          flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors
          hover:bg-[hsl(var(--bolt-bg-tertiary))]
          ${isSelected ? 'bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-accent))]' : 'text-[hsl(var(--bolt-text-primary))]'}
        `}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        {node.type === 'folder' && (
          <span className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </span>
        )}
        {node.type === 'file' && <span className="w-4" />}

        <Icon className="w-4 h-4 flex-shrink-0" />

        <span className="text-sm truncate">{node.name}</span>
      </div>

      {node.type === 'folder' && isExpanded && node.children && (
        <div>
          {node.children.map((child, index) => (
            <FileTreeNode
              key={`${child.name}-${index}`}
              node={child}
              level={level + 1}
              onSelect={onSelect}
              selectedFile={selectedFile}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function FileExplorer({ files, onFileSelect, selectedFile }: FileExplorerProps) {
  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-secondary))] border-r border-[hsl(var(--bolt-border))]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[hsl(var(--bolt-border))]">
        <h3 className="text-sm font-semibold text-[hsl(var(--bolt-text-primary))]">
          Files
        </h3>
      </div>

      {/* File Tree */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-2">
        {files.length > 0 ? (
          files.map((file, index) => (
            <FileTreeNode
              key={`${file.name}-${index}`}
              node={file}
              onSelect={onFileSelect}
              selectedFile={selectedFile}
            />
          ))
        ) : (
          <div className="flex items-center justify-center h-32 text-[hsl(var(--bolt-text-secondary))] text-sm">
            No files yet
          </div>
        )}
      </div>
    </div>
  )
}
