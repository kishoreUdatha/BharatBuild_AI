'use client'

import { useState } from 'react'
import { X, Star, Send, MessageSquare, Bug, Lightbulb, ThumbsUp } from 'lucide-react'

interface FeedbackModalProps {
  isOpen: boolean
  onClose: () => void
}

type FeedbackType = 'general' | 'bug' | 'feature' | 'praise'

const feedbackTypes = [
  { id: 'general' as FeedbackType, label: 'General', icon: MessageSquare, color: 'text-blue-400' },
  { id: 'bug' as FeedbackType, label: 'Bug Report', icon: Bug, color: 'text-red-400' },
  { id: 'feature' as FeedbackType, label: 'Feature Request', icon: Lightbulb, color: 'text-yellow-400' },
  { id: 'praise' as FeedbackType, label: 'Praise', icon: ThumbsUp, color: 'text-green-400' },
]

export function FeedbackModal({ isOpen, onClose }: FeedbackModalProps) {
  const [feedbackType, setFeedbackType] = useState<FeedbackType>('general')
  const [rating, setRating] = useState(0)
  const [hoveredRating, setHoveredRating] = useState(0)
  const [message, setMessage] = useState('')
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!message.trim()) {
      setError('Please enter your feedback message')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({
          type: feedbackType,
          rating: rating > 0 ? rating : undefined,
          message: message.trim(),
          email: email.trim() || undefined,
          page_url: window.location.href,
          user_agent: navigator.userAgent,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit feedback')
      }

      setSubmitted(true)
      setTimeout(() => {
        onClose()
        // Reset form after closing
        setTimeout(() => {
          setSubmitted(false)
          setFeedbackType('general')
          setRating(0)
          setMessage('')
          setEmail('')
        }, 300)
      }, 2000)
    } catch (err) {
      console.error('Failed to submit feedback:', err)
      setError('Failed to submit feedback. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-[#1e1e1e] border border-[#333] rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#333]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Send Feedback</h2>
              <p className="text-sm text-gray-400">Help us improve BharatBuild AI</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-[#333] rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {submitted ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Thank you!</h3>
            <p className="text-gray-400">Your feedback has been submitted successfully.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            {/* Feedback Type */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                What type of feedback?
              </label>
              <div className="grid grid-cols-2 gap-2">
                {feedbackTypes.map((type) => {
                  const Icon = type.icon
                  return (
                    <button
                      key={type.id}
                      type="button"
                      onClick={() => setFeedbackType(type.id)}
                      className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border transition-all ${
                        feedbackType === type.id
                          ? 'border-blue-500 bg-blue-500/10 text-white'
                          : 'border-[#444] bg-[#252525] text-gray-400 hover:border-[#555] hover:text-white'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${feedbackType === type.id ? type.color : ''}`} />
                      <span className="text-sm">{type.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Star Rating */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                How would you rate your experience? (optional)
              </label>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHoveredRating(star)}
                    onMouseLeave={() => setHoveredRating(0)}
                    className="p-1 transition-transform hover:scale-110"
                  >
                    <Star
                      className={`w-7 h-7 transition-colors ${
                        star <= (hoveredRating || rating)
                          ? 'text-yellow-400 fill-yellow-400'
                          : 'text-gray-600'
                      }`}
                    />
                  </button>
                ))}
                {rating > 0 && (
                  <span className="ml-2 text-sm text-gray-400">
                    {rating === 1 && 'Poor'}
                    {rating === 2 && 'Fair'}
                    {rating === 3 && 'Good'}
                    {rating === 4 && 'Great'}
                    {rating === 5 && 'Excellent!'}
                  </span>
                )}
              </div>
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Your feedback *
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={
                  feedbackType === 'bug'
                    ? 'Please describe the bug you encountered...'
                    : feedbackType === 'feature'
                    ? 'What feature would you like to see?'
                    : feedbackType === 'praise'
                    ? 'What did you like about BharatBuild AI?'
                    : 'Share your thoughts with us...'
                }
                rows={4}
                className="w-full bg-[#252525] border border-[#444] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>

            {/* Email (optional) */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email (optional - for follow-up)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full bg-[#252525] border border-[#444] rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !message.trim()}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
              >
                {isSubmitting ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Sending...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Send Feedback</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
