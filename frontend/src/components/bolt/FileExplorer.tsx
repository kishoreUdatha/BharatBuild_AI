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
  FileType,
  BookOpen,
  FileSpreadsheet,
  Presentation,
  Download,
} from 'lucide-react'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

interface FileExplorerProps {
  files: FileNode[]
  onFileSelect?: (file: FileNode) => void
  selectedFile?: string
}

const getFileIcon = (fileName: string, path?: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase()

  // Special icons for documentation files in docs/ folder
  if (path?.startsWith('docs/') || path?.includes('/docs/')) {
    if (ext === 'md') {
      // Use BookOpen for documentation markdown files
      return BookOpen
    }
  }

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
      return FileText
    case 'txt':
      return FileText
    // Academic/Student document types
    case 'pdf':
      return FileType  // PDF icon
    case 'docx':
    case 'doc':
      return FileSpreadsheet  // Word document icon
    case 'pptx':
    case 'ppt':
      return Presentation  // PowerPoint icon
    case 'xlsx':
    case 'xls':
      return FileSpreadsheet  // Excel icon
    default:
      return File
  }
}

// Check if file is a binary/downloadable type
const isBinaryFile = (fileName: string): boolean => {
  const ext = fileName.split('.').pop()?.toLowerCase()
  return ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls', 'zip', 'rar'].includes(ext || '')
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
  const isBinary = node.type === 'file' && isBinaryFile(node.name)

  const handleClick = () => {
    if (node.type === 'folder') {
      setIsExpanded(!isExpanded)
    } else {
      onSelect?.(node)
    }
  }

  const Icon = node.type === 'folder'
    ? (isExpanded ? FolderOpen : Folder)
    : getFileIcon(node.name, node.path)

  // Get color class based on file type
  const getFileColor = () => {
    if (node.type === 'folder') return ''
    const ext = node.name.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf':
        return 'text-red-400'  // Red for PDF
      case 'docx':
      case 'doc':
        return 'text-blue-400'  // Blue for Word
      case 'pptx':
      case 'ppt':
        return 'text-orange-400'  // Orange for PPT
      case 'xlsx':
      case 'xls':
        return 'text-green-400'  // Green for Excel
      default:
        return ''
    }
  }

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

        <Icon className={`w-4 h-4 flex-shrink-0 ${getFileColor()}`} />

        <span className="text-sm truncate flex-1">{node.name}</span>

        {/* Show download icon for binary files */}
        {isBinary && (
          <Download className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))] opacity-60" />
        )}
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
