'use client'

import { useState, useRef, useEffect } from 'react'
import {
  Send,
  Paperclip,
  Smile,
  MoreVertical,
  Reply,
  Trash2,
  Edit2,
  AtSign,
  Loader2
} from 'lucide-react'
import { useTeamChat, useTeamActions, useTeamWebSocket } from '@/hooks/useTeam'
import { useAuth } from '@/hooks/useAuth'
import type { TeamMember, TeamChatMessage } from '@/types/team'

interface TeamChatProps {
  teamId: string
  members: TeamMember[]
}

export function TeamChat({ teamId, members }: TeamChatProps) {
  const [message, setMessage] = useState('')
  const [showMentions, setShowMentions] = useState(false)
  const [mentionFilter, setMentionFilter] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const { user } = useAuth()
  const { messages, isLoading, refresh } = useTeamChat(teamId, { limit: 100 })
  const { sendChatMessage, isLoading: isSending } = useTeamActions()

  // WebSocket for real-time messages
  const { isConnected, sendTypingIndicator } = useTeamWebSocket(teamId, {
    onMessage: (msg) => {
      if (msg.type === 'chat_message') {
        refresh()
      }
    }
  })

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!message.trim()) return

    // Extract mentions from message
    const mentionRegex = /@(\w+)/g
    const mentions: string[] = []
    let match: RegExpExecArray | null
    while ((match = mentionRegex.exec(message)) !== null) {
      const matchedText = match[1]
      const mentionedMember = members.find(
        m => m.user_name?.toLowerCase().includes(matchedText.toLowerCase())
      )
      if (mentionedMember) {
        mentions.push(mentionedMember.user_id)
      }
    }

    try {
      await sendChatMessage(teamId, {
        content: message,
        mentions: mentions.length > 0 ? mentions : undefined
      })
      setMessage('')
      refresh()
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }

    // Handle @ mentions
    if (e.key === '@' || (message.endsWith('@') && e.key !== 'Backspace')) {
      setShowMentions(true)
    }

    // Send typing indicator
    sendTypingIndicator(true)
    setTimeout(() => sendTypingIndicator(false), 2000)
  }

  const handleMentionSelect = (member: TeamMember) => {
    const beforeAt = message.substring(0, message.lastIndexOf('@'))
    setMessage(`${beforeAt}@${member.user_name?.split(' ')[0] || 'user'} `)
    setShowMentions(false)
    inputRef.current?.focus()
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) +
      ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  // Group messages by date
  const groupedMessages: { date: string; messages: TeamChatMessage[] }[] = []
  let currentDate = ''

  messages.forEach((msg) => {
    const msgDate = new Date(msg.created_at).toDateString()
    if (msgDate !== currentDate) {
      currentDate = msgDate
      groupedMessages.push({ date: msgDate, messages: [msg] })
    } else {
      groupedMessages[groupedMessages.length - 1].messages.push(msg)
    }
  })

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-[hsl(var(--bolt-text-primary))]">
              Team Chat
            </h2>
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              {members.length} members &bull;{' '}
              {isConnected ? (
                <span className="text-green-400">Connected</span>
              ) : (
                <span className="text-yellow-400">Connecting...</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Online members avatars */}
            <div className="flex -space-x-2">
              {members.slice(0, 4).map((member) => (
                <div
                  key={member.id}
                  className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold border-2 border-[hsl(var(--bolt-bg-secondary))]"
                  title={member.user_name}
                >
                  {member.user_name?.charAt(0) || 'U'}
                </div>
              ))}
              {members.length > 4 && (
                <div className="w-8 h-8 rounded-full bg-[hsl(var(--bolt-bg-tertiary))] flex items-center justify-center text-xs text-[hsl(var(--bolt-text-secondary))] border-2 border-[hsl(var(--bolt-bg-secondary))]">
                  +{members.length - 4}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--bolt-accent))]" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-full bg-[hsl(var(--bolt-bg-tertiary))] flex items-center justify-center mb-4">
              <Send className="w-8 h-8 text-[hsl(var(--bolt-text-secondary))]" />
            </div>
            <h3 className="text-lg font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
              No messages yet
            </h3>
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              Start the conversation with your team!
            </p>
          </div>
        ) : (
          groupedMessages.map((group, groupIndex) => (
            <div key={groupIndex}>
              {/* Date Separator */}
              <div className="flex items-center gap-4 my-4">
                <div className="flex-1 h-px bg-[hsl(var(--bolt-border))]" />
                <span className="text-xs text-[hsl(var(--bolt-text-secondary))] px-2">
                  {new Date(group.date).toLocaleDateString([], {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric'
                  })}
                </span>
                <div className="flex-1 h-px bg-[hsl(var(--bolt-border))]" />
              </div>

              {/* Messages for this date */}
              <div className="space-y-4">
                {group.messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    isOwn={msg.sender_id === user?.id}
                    formatTime={formatTime}
                  />
                ))}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Mention Popup */}
      {showMentions && (
        <div className="absolute bottom-24 left-6 right-6 bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-lg shadow-xl p-2 max-h-48 overflow-y-auto">
          <div className="text-xs text-[hsl(var(--bolt-text-secondary))] px-2 py-1 mb-1">
            Mention someone
          </div>
          {members
            .filter(m =>
              m.user_name?.toLowerCase().includes(mentionFilter.toLowerCase()) ||
              m.user_email?.toLowerCase().includes(mentionFilter.toLowerCase())
            )
            .map((member) => (
              <button
                key={member.id}
                onClick={() => handleMentionSelect(member)}
                className="flex items-center gap-3 w-full p-2 rounded-lg hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-sm font-bold">
                  {member.user_name?.charAt(0) || 'U'}
                </div>
                <div className="text-left">
                  <div className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                    {member.user_name || 'Unknown'}
                  </div>
                  <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                    {member.user_email}
                  </div>
                </div>
              </button>
            ))}
        </div>
      )}

      {/* Input */}
      <div className="flex-shrink-0 p-4 border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center gap-3">
          <button className="p-2 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg transition-colors">
            <Paperclip className="w-5 h-5 text-[hsl(var(--bolt-text-secondary))]" />
          </button>

          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={(e) => {
                setMessage(e.target.value)
                // Check for @ mentions
                const lastAt = e.target.value.lastIndexOf('@')
                if (lastAt !== -1) {
                  const afterAt = e.target.value.substring(lastAt + 1)
                  if (!afterAt.includes(' ')) {
                    setShowMentions(true)
                    setMentionFilter(afterAt)
                  } else {
                    setShowMentions(false)
                  }
                } else {
                  setShowMentions(false)
                }
              }}
              onKeyDown={handleKeyDown}
              placeholder="Type a message... Use @ to mention"
              className="w-full px-4 py-3 bg-[hsl(var(--bolt-bg-primary))] border border-[hsl(var(--bolt-border))] rounded-xl text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--bolt-accent))]"
            />
            <button
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg transition-colors"
              onClick={() => setShowMentions(!showMentions)}
            >
              <AtSign className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
            </button>
          </div>

          <button
            onClick={handleSend}
            disabled={!message.trim() || isSending}
            className="p-3 bg-[hsl(var(--bolt-accent))] text-white rounded-xl hover:bg-[hsl(var(--bolt-accent-hover))] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// Message Bubble Component
function MessageBubble({
  message,
  isOwn,
  formatTime
}: {
  message: TeamChatMessage
  isOwn: boolean
  formatTime: (date: string) => string
}) {
  const [showMenu, setShowMenu] = useState(false)

  // Highlight @mentions in message
  const highlightMentions = (content: string) => {
    return content.split(/(@\w+)/g).map((part, index) => {
      if (part.startsWith('@')) {
        return (
          <span key={index} className="text-[hsl(var(--bolt-accent))] font-medium">
            {part}
          </span>
        )
      }
      return part
    })
  }

  if (message.message_type === 'system') {
    return (
      <div className="flex justify-center">
        <span className="px-3 py-1 bg-[hsl(var(--bolt-bg-tertiary))] rounded-full text-xs text-[hsl(var(--bolt-text-secondary))]">
          {message.content}
        </span>
      </div>
    )
  }

  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex gap-3 max-w-[70%] ${isOwn ? 'flex-row-reverse' : ''}`}>
        {/* Avatar */}
        {!isOwn && (
          <div className="flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-sm font-bold">
              {message.sender_name?.charAt(0) || 'U'}
            </div>
          </div>
        )}

        {/* Message */}
        <div className="group relative">
          {/* Sender name */}
          {!isOwn && (
            <div className="text-xs text-[hsl(var(--bolt-text-secondary))] mb-1">
              {message.sender_name || 'Unknown'}
            </div>
          )}

          <div
            className={`px-4 py-2 rounded-2xl ${
              isOwn
                ? 'bg-[hsl(var(--bolt-accent))] text-white rounded-br-sm'
                : 'bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-primary))] rounded-bl-sm'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap break-words">
              {highlightMentions(message.content)}
            </p>

            {/* Attachment */}
            {message.attachment_url && (
              <div className="mt-2 p-2 bg-black/10 rounded-lg">
                <a
                  href={message.attachment_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm underline"
                >
                  <Paperclip className="w-4 h-4" />
                  {message.attachment_name || 'Attachment'}
                </a>
              </div>
            )}
          </div>

          {/* Time & Edit status */}
          <div className={`flex items-center gap-2 mt-1 text-xs text-[hsl(var(--bolt-text-secondary))] ${isOwn ? 'justify-end' : ''}`}>
            <span>{formatTime(message.created_at)}</span>
            {message.is_edited && <span>(edited)</span>}
          </div>

          {/* Hover Menu */}
          <div
            className={`absolute top-0 ${isOwn ? 'left-0 -translate-x-full' : 'right-0 translate-x-full'} px-2 opacity-0 group-hover:opacity-100 transition-opacity`}
          >
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
            >
              <MoreVertical className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
