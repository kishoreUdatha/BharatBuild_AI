'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageSquare, X, ArrowUp, Bot } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: "Hi there! How can I help you today?"
      }])
    }
    if (isOpen) inputRef.current?.focus()
  }, [isOpen])

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return
    const text = inputValue.trim()
    setMessages(prev => [...prev, { id: `u-${Date.now()}`, role: 'user', content: text }])
    setInputValue('')
    setIsLoading(true)

    try {
      const res = await fetch(`${API_URL}/chatbot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          conversation_history: messages.slice(-10).map(m => ({ role: m.role, content: m.content })),
          user_context: { is_logged_in: !!localStorage.getItem('access_token') }
        })
      })
      const data = await res.json()
      setMessages(prev => [...prev, { id: `a-${Date.now()}`, role: 'assistant', content: data.response }])
    } catch {
      setMessages(prev => [...prev, { id: `e-${Date.now()}`, role: 'assistant', content: "Sorry, something went wrong. Please try again." }])
    } finally {
      setIsLoading(false)
    }
  }

  const formatContent = (text: string) => {
    if (!text) return null
    return text.split('\n').map((line, i) => {
      if (!line.trim()) return <br key={i} />

      // Bullet points
      if (/^[-•*]\s/.test(line)) {
        return (
          <div key={i} className="flex gap-2 ml-1 my-1">
            <span className="text-emerald-400">•</span>
            <span>{formatBold(line.replace(/^[-•*]\s/, ''))}</span>
          </div>
        )
      }

      // Numbered list
      if (/^\d+\.\s/.test(line)) {
        const num = line.match(/^(\d+)\./)?.[1]
        return (
          <div key={i} className="flex gap-2 ml-1 my-1">
            <span className="text-emerald-400 font-medium">{num}.</span>
            <span>{formatBold(line.replace(/^\d+\.\s/, ''))}</span>
          </div>
        )
      }

      return <p key={i} className="my-1">{formatBold(line)}</p>
    })
  }

  const formatBold = (text: string) => {
    return text.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
      part.startsWith('**') ? <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong> : part
    )
  }

  return (
    <>
      {/* Chat Button - Only show when closed */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 hover:scale-105 bg-gradient-to-br from-cyan-500 to-emerald-500"
        >
          <MessageSquare className="w-6 h-6 text-white" />
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div
          className="fixed bottom-24 right-5 z-50 w-[360px] h-[500px] flex flex-col rounded-2xl overflow-hidden shadow-2xl bg-[#1a1a1a] border border-[#333] isolate"
          onWheel={(e) => e.stopPropagation()}
        >

          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[#333] bg-[#1a1a1a]">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <div className="font-medium text-white text-[15px]">BharatBuild AI</div>
              <div className="text-emerald-400 text-xs flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                Online
              </div>
            </div>
            <button
              onClick={() => {
                setIsOpen(false)
                setMessages([])  // Clear conversation history on close
              }}
              className="w-8 h-8 rounded-full hover:bg-[#333] flex items-center justify-center transition-colors"
            >
              <X className="w-5 h-5 text-gray-400 hover:text-white" />
            </button>
          </div>

          {/* Messages */}
          <div
            className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#111] scrollbar-hide overscroll-contain"
            onWheel={(e) => e.stopPropagation()}
          >
            {messages.map((msg) => (
              <div key={msg.id} className={msg.role === 'user' ? 'flex justify-end' : ''}>
                {msg.role === 'user' ? (
                  <div className="max-w-[80%] bg-gradient-to-r from-cyan-600 to-emerald-600 text-white px-4 py-2.5 rounded-2xl rounded-br-md text-[14px]">
                    {msg.content}
                  </div>
                ) : (
                  <div className="text-[14px] text-[#e0e0e0] leading-relaxed">
                    {formatContent(msg.content)}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-[#333] bg-[#1a1a1a]">
            <div className="flex items-end gap-2 bg-[#2a2a2a] rounded-xl p-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }}}
                placeholder="Message..."
                rows={1}
                disabled={isLoading}
                className="flex-1 bg-transparent text-white text-[14px] placeholder-[#666] outline-none resize-none max-h-24 px-2 py-1"
              />
              <button
                onClick={sendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="w-8 h-8 rounded-lg bg-gradient-to-r from-cyan-500 to-emerald-500 flex items-center justify-center disabled:opacity-30 transition-opacity"
              >
                <ArrowUp className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
