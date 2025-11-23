'use client'

import { useState, useRef, useEffect } from 'react'
import { Terminal as TerminalIcon, X, Minimize2, Maximize2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface TerminalProps {
  commands?: string[]
  output?: string[]
}

export function Terminal({ commands = [], output = [] }: TerminalProps) {
  const [isMinimized, setIsMinimized] = useState(false)
  const [localOutput, setLocalOutput] = useState<string[]>(output)
  const terminalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setLocalOutput(output)
  }, [output])

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [localOutput])

  if (commands.length === 0 && output.length === 0) {
    return null
  }

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 bg-[hsl(var(--bolt-bg-secondary))] border-t border-[hsl(var(--bolt-border))] transition-all ${
        isMinimized ? 'h-12' : 'h-64'
      }`}
      style={{ zIndex: 50 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[hsl(var(--bolt-border))]">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
          <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
            Terminal
          </span>
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMinimized(!isMinimized)}
            className="h-6 w-6 p-0 text-[hsl(var(--bolt-text-secondary))]"
          >
            {isMinimized ? (
              <Maximize2 className="w-3 h-3" />
            ) : (
              <Minimize2 className="w-3 h-3" />
            )}
          </Button>
        </div>
      </div>

      {/* Terminal Content */}
      {!isMinimized && (
        <div
          ref={terminalRef}
          className="p-4 overflow-y-auto scrollbar-thin h-[calc(100%-3rem)] font-mono text-sm bg-[hsl(var(--bolt-bg-primary))]"
        >
          {/* Commands */}
          {commands.map((cmd, index) => (
            <div key={`cmd-${index}`} className="mb-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-green-400">$</span>
                <span className="text-[hsl(var(--bolt-text-primary))]">{cmd}</span>
              </div>
            </div>
          ))}

          {/* Output */}
          {localOutput.map((line, index) => (
            <div
              key={`output-${index}`}
              className="text-[hsl(var(--bolt-text-secondary))] mb-1"
            >
              {line}
            </div>
          ))}

          {/* Cursor */}
          <div className="flex items-center gap-2 mt-2">
            <span className="text-green-400">$</span>
            <span className="inline-block w-2 h-4 bg-green-400 animate-pulse" />
          </div>
        </div>
      )}
    </div>
  )
}
