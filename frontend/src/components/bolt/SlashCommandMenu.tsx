'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Sparkles, Code, FileText, Play, Wrench, Compass,
  Plus, Wand2, Bug, MessageCircleQuestion, RefreshCw,
  FlaskConical, Files, BookOpen, GraduationCap, GitBranch,
  Square, Hammer, Terminal, Download, Upload, Search,
  Share2, FolderPlus, Folder, HelpCircle, Trash2,
  ListChecks, Presentation, Command,
} from 'lucide-react'
import {
  SlashCommand,
  CommandCategory,
  COMMAND_CATEGORIES,
  filterCommands,
  getCommandsByCategory,
} from '@/config/slashCommands'

// Icon mapping
const ICON_MAP: Record<string, React.ComponentType<any>> = {
  Sparkles, Code, FileText, Play, Wrench, Compass,
  Plus, Wand2, Bug, MessageCircleQuestion, RefreshCw,
  FlaskConical, Files, BookOpen, GraduationCap, GitBranch,
  Square, Hammer, Terminal, Download, Upload, Search,
  Share2, FolderPlus, Folder, HelpCircle, Trash2,
  ListChecks, Presentation, Command,
}

interface SlashCommandMenuProps {
  query: string              // Current text after "/" (for filtering)
  isVisible: boolean         // Whether the menu is shown
  hasProject: boolean        // Whether a project is currently open
  onSelect: (command: SlashCommand) => void  // Called when user picks a command
  onClose: () => void        // Called when menu should close
  position?: 'above' | 'below'  // Menu position relative to input
}

/**
 * Slash Command Menu - Kiro-style command palette
 * 
 * Shows categorized commands when user types "/" in chat input.
 * Supports:
 * - Keyboard navigation (↑↓ arrows + Enter)
 * - Real-time filtering as user types
 * - Category headers
 * - Command descriptions
 * - Visual icons
 */
export function SlashCommandMenu({
  query,
  isVisible,
  hasProject,
  onSelect,
  onClose,
  position = 'above',
}: SlashCommandMenuProps) {
  const [selectedIndex, setSelectedIndex] = useState(0)
  const menuRef = useRef<HTMLDivElement>(null)
  const selectedRef = useRef<HTMLButtonElement>(null)

  // Filter commands based on query
  const filteredCommands = useMemo(
    () => filterCommands(query, { hasProject }),
    [query, hasProject]
  )

  // Group by category
  const groupedCommands = useMemo(
    () => getCommandsByCategory(filteredCommands),
    [filteredCommands]
  )

  // Flat list for keyboard navigation
  const flatList = useMemo(() => filteredCommands, [filteredCommands])

  // Reset selection when filter changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Scroll selected item into view
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!isVisible) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev < flatList.length - 1 ? prev + 1 : 0
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : flatList.length - 1
        )
        break
      case 'Enter':
      case 'Tab':
        e.preventDefault()
        if (flatList[selectedIndex]) {
          onSelect(flatList[selectedIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
    }
  }, [isVisible, flatList, selectedIndex, onSelect, onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Don't render if not visible or no commands match
  if (!isVisible || flatList.length === 0) return null

  // Render icon component
  const renderIcon = (iconName: string, className: string = "w-4 h-4") => {
    const IconComponent = ICON_MAP[iconName]
    if (!IconComponent) return null
    return <IconComponent className={className} />
  }

  // Category colors
  const categoryColors: Record<CommandCategory, string> = {
    generation: 'text-purple-400',
    code: 'text-blue-400',
    documents: 'text-green-400',
    execution: 'text-orange-400',
    tools: 'text-cyan-400',
    navigation: 'text-gray-400',
  }

  let itemIndex = -1

  return (
    <div
      ref={menuRef}
      className={`absolute left-0 right-0 z-50 ${
        position === 'above' ? 'bottom-full mb-2' : 'top-full mt-2'
      }`}
    >
      <div className="bg-[#1a1a2e] border border-gray-700/50 rounded-xl shadow-2xl shadow-black/50 overflow-hidden max-h-[360px] flex flex-col">
        {/* Header */}
        <div className="px-3 py-2 border-b border-gray-700/50 flex items-center gap-2">
          <Command className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-xs text-gray-500 font-medium">
            {query ? `Commands matching "${query}"` : 'Commands'}
          </span>
          <span className="ml-auto text-[10px] text-gray-600">
            {flatList.length} {flatList.length === 1 ? 'command' : 'commands'}
          </span>
        </div>

        {/* Scrollable command list */}
        <div className="overflow-y-auto scrollbar-thin max-h-[320px]">
          {Array.from(groupedCommands.entries()).map(([category, commands]) => {
            const categoryInfo = COMMAND_CATEGORIES.find(c => c.id === category)
            
            return (
              <div key={category}>
                {/* Category Header */}
                <div className="px-3 py-1.5 flex items-center gap-2 sticky top-0 bg-[#1a1a2e]/95 backdrop-blur-sm">
                  <span className={`${categoryColors[category]}`}>
                    {renderIcon(categoryInfo?.icon || 'Folder', 'w-3 h-3')}
                  </span>
                  <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                    {categoryInfo?.label || category}
                  </span>
                </div>

                {/* Commands in this category */}
                {commands.map(cmd => {
                  itemIndex++
                  const isSelected = itemIndex === selectedIndex
                  const currentIndex = itemIndex

                  return (
                    <button
                      key={cmd.id}
                      ref={isSelected ? selectedRef : undefined}
                      onClick={() => onSelect(cmd)}
                      onMouseEnter={() => setSelectedIndex(currentIndex)}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                        isSelected
                          ? 'bg-blue-500/10 border-l-2 border-blue-500'
                          : 'border-l-2 border-transparent hover:bg-white/5'
                      }`}
                    >
                      {/* Icon */}
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        isSelected
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-gray-800 text-gray-400'
                      }`}>
                        {renderIcon(cmd.icon, 'w-3.5 h-3.5')}
                      </div>

                      {/* Label & Description */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-medium ${
                            isSelected ? 'text-white' : 'text-gray-300'
                          }`}>
                            {cmd.label}
                          </span>
                          <code className="text-[10px] text-gray-500 bg-gray-800/50 px-1.5 py-0.5 rounded font-mono">
                            {cmd.command}
                          </code>
                        </div>
                        <p className="text-xs text-gray-500 truncate mt-0.5">
                          {cmd.description}
                        </p>
                      </div>

                      {/* Shortcut hint */}
                      {cmd.shortcut && (
                        <kbd className="text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-3 py-1.5 border-t border-gray-700/50 flex items-center gap-3">
          <span className="text-[10px] text-gray-600">
            <kbd className="px-1 py-0.5 bg-gray-800 rounded text-gray-500">↑↓</kbd> navigate
          </span>
          <span className="text-[10px] text-gray-600">
            <kbd className="px-1 py-0.5 bg-gray-800 rounded text-gray-500">Enter</kbd> select
          </span>
          <span className="text-[10px] text-gray-600">
            <kbd className="px-1 py-0.5 bg-gray-800 rounded text-gray-500">Esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  )
}

export default SlashCommandMenu
