'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  Zap, ChevronRight, ChevronLeft, BookOpen, Target,
  Rocket, CheckCircle2, Copy, Check, ArrowRight,
  GraduationCap, Play, Lightbulb, FileText, Home
} from 'lucide-react'

const LESSONS = [
  {
    id: 1,
    module: 'Basics',
    title: 'What is a Prompt?',
    content: `A prompt is the instruction you give to AI to build your application.

Think of it like explaining your idea to a skilled developer - the clearer you explain, the better result you get.

Simple example:
• Bad: "Give me food" (vague)
• Good: "Vegetable biryani with raita" (specific)

Same with prompts - be specific about what you want!`,
    tip: 'Start with WHAT you want, then add HOW it should work.',
    bad: 'Make me a website',
    good: 'Create a restaurant website with online menu, table reservations, and photo gallery'
  },
  {
    id: 2,
    module: 'Basics',
    title: 'The 5 Key Elements',
    content: `Every great prompt has 5 parts:

1. Project Type — "A fitness tracking app..."
2. Core Features — "...that tracks workouts..."
3. Target Users — "...for gym beginners..."
4. Design Style — "...with orange/black colors..."
5. Special Needs — "...with Hindi support"

Put them together for a complete prompt!`,
    tip: 'Formula: [Type] + [Features] + [Users] + [Design] + [Special]',
    bad: 'Fitness app',
    good: 'A fitness app for gym beginners that tracks workouts, counts calories, shows progress charts, with orange/black theme and Hindi support'
  },
  {
    id: 3,
    module: 'Basics',
    title: 'Be Specific',
    content: `Replace vague words with details:

• "nice" → "professional" or "minimal"
• "good" → "fast-loading" or "user-friendly"
• "some" → exact numbers like "5 categories"
• "basic" → list the actual features

Checklist before submitting:
✓ Named specific features?
✓ Mentioned colors/style?
✓ Described pages needed?`,
    tip: 'If two people could interpret it differently, add more detail.',
    bad: 'Create a nice portfolio with some projects',
    good: 'Create a dark portfolio with 6 project cards, skills bars, testimonials section, and contact form'
  },
  {
    id: 4,
    module: 'Techniques',
    title: 'Use App References',
    content: `Mention popular apps to explain your vision:

• "Similar to Trello" — overall style
• "Swiggy-like tracking" — specific feature
• "Inspired by Notion" — design direction

Common references:
• E-commerce → "Like Amazon"
• Dashboard → "Like Notion"
• Chat → "Like WhatsApp"
• Social → "Like Instagram"`,
    tip: 'Combine references: "Trello boards + Notion notes + Slack chat"',
    bad: 'Build a project management tool',
    good: 'Build a project tool with Trello-style boards, Notion-like notes, and Slack-style team chat'
  },
  {
    id: 5,
    module: 'Techniques',
    title: 'Know Your Users',
    content: `Who will use your app? This shapes everything.

Include:
• Age group (students, professionals, seniors)
• Tech level (beginners vs experts)
• Use case (work, personal, education)
• Special needs (accessibility, language)

How it helps:
• Students → Simple UI, budget features
• Seniors → Large text, easy navigation
• Rural users → Offline mode, local language`,
    tip: 'Describe in one line: "For [who] who need [what]"',
    bad: 'Create a learning app',
    good: 'Learning app for rural students (10-15 yrs) with limited internet - offline mode, Hindi/English toggle, large buttons'
  },
  {
    id: 6,
    module: 'Techniques',
    title: 'Design & Colors',
    content: `Guide the visual design:

By Industry:
• Healthcare → Blue/green, clean
• Finance → Blue/gold, professional
• Food → Red/orange, warm
• Tech → Blue/purple, modern

By Mood:
• Professional → Navy, gray, white
• Playful → Bright, rounded corners
• Luxury → Black, gold, elegant`,
    tip: 'Always mention: primary color + accent + mood',
    bad: 'Make it look good',
    good: 'Navy blue with gold accents, white backgrounds, modern fonts - professional banking feel'
  },
  {
    id: 7,
    module: 'Advanced',
    title: 'Describe Features',
    content: `Don't just name features - explain them:

Template: [Feature] + [How it works] + [Result]

Example - Registration:
❌ "Add registration"
✅ "Registration with email or Google. Email verification. After signup, go to profile setup."

Example - Search:
❌ "Add search"
✅ "Search with suggestions, filters for category/price, 'no results' message with alternatives"`,
    tip: 'Ask: What triggers it? What does user do? What happens after?',
    bad: 'Add shopping cart',
    good: 'Cart with thumbnails, quantity buttons, live total with tax, coupon field, saves if user leaves'
  },
  {
    id: 8,
    module: 'Advanced',
    title: 'User Flows',
    content: `Describe the user journey step by step:

Format: Step 1 → Step 2 → Step 3 → Done

E-commerce:
"Browse → Add to cart → Enter address → Pay → Success page → Email"

Booking:
"Select doctor → Pick date → Enter details → Confirm → Get booking ID"

Tips:
• Start from entry point
• Include decision points
• End with success state`,
    tip: 'Walk through as a user, write each step.',
    bad: 'Users should book appointments',
    good: 'Booking: Select doctor → View calendar → Pick slot → Enter symptoms → Confirm → Get SMS with details'
  },
  {
    id: 9,
    module: 'Advanced',
    title: 'Handle Edge Cases',
    content: `Good apps handle problems gracefully:

Empty States:
• No search results
• Empty cart
• New user, no data

Error States:
• Payment failed
• No internet
• Invalid input

Include in prompt:
"If cart empty, show illustration + 'Browse Products' button"
"If payment fails, show retry + other payment options"`,
    tip: 'Think: "What if something goes wrong?"',
    bad: 'Add search feature',
    good: 'Search with suggestions, spell-check, filters. If no results: friendly message + show popular items'
  },
  {
    id: 10,
    module: 'Templates',
    title: 'E-Commerce',
    content: `Ready template - customize the [BRACKETS]:

"Online store for [NAME] selling [PRODUCTS].

Pages: Home (hero, 8 products), Category (grid, filters), Product (gallery, reviews), Cart, Checkout, Success

Features: Search, wishlist, stock indicator

Design: [COLORS], clean product focus"`,
    tip: 'Replace [BRACKETS] with your details.',
    bad: 'Make an online store',
    good: 'Store for "StyleHub" selling fashion. Hero + 8 featured items. Filters on category page. Product pages with 5 images. Cart with coupons. Navy/white theme.'
  },
  {
    id: 11,
    module: 'Templates',
    title: 'Dashboard',
    content: `Ready template:

"Admin dashboard for [BUSINESS].

Layout: Sidebar nav, top bar with search/notifications

Dashboard: Metric cards [YOUR METRICS], line chart (trends), bar chart (top items), activity feed

Data pages: List with filters, Add/Edit forms, Delete confirm, CSV export

Features: Dark/Light mode, date picker"`,
    tip: 'List your metrics: "Sales, Users, Orders"',
    bad: 'Create a dashboard',
    good: 'Restaurant dashboard. Metrics: orders, revenue, tables. Sales chart. Pages for menu, orders, reservations. Dark sidebar.'
  },
  {
    id: 12,
    module: 'Templates',
    title: 'Booking System',
    content: `Ready template:

"Booking for [SERVICE TYPE].

Flow: Browse [providers] → View profile → Select service → Pick date/time → Enter details → Pay → Confirmation

Admin: Today's list, calendar view, manage services, reports

Features: SMS confirm, 24hr reminder, reschedule, reviews"`,
    tip: 'Works for doctors, salons, tutors, consultants.',
    bad: 'Make a booking system',
    good: 'Booking for "Glow Salon". Browse stylists. Select service (haircut/spa). Calendar slots. Collect phone. SMS confirmation.'
  }
]

const MODULES = [
  { name: 'Basics', icon: BookOpen, color: 'from-blue-500 to-blue-600', lessons: [1, 2, 3] },
  { name: 'Techniques', icon: Target, color: 'from-purple-500 to-purple-600', lessons: [4, 5, 6] },
  { name: 'Advanced', icon: Rocket, color: 'from-orange-500 to-orange-600', lessons: [7, 8, 9] },
  { name: 'Templates', icon: FileText, color: 'from-green-500 to-green-600', lessons: [10, 11, 12] },
]

export default function LearnPage() {
  const [current, setCurrent] = useState(1)
  const [completed, setCompleted] = useState<number[]>([])
  const [copied, setCopied] = useState<string | null>(null)

  const lesson = LESSONS.find(l => l.id === current)!
  const progress = Math.round((completed.length / 12) * 100)

  const copyText = (text: string, type: string) => {
    navigator.clipboard.writeText(text)
    setCopied(type)
    setTimeout(() => setCopied(null), 2000)
  }

  const nextLesson = () => {
    if (!completed.includes(current)) {
      setCompleted([...completed, current])
    }
    if (current < 12) setCurrent(current + 1)
  }

  const prevLesson = () => {
    if (current > 1) setCurrent(current - 1)
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Top Progress Bar */}
      <div className="bg-slate-900 border-b border-slate-800">
        <div className="h-1 bg-slate-800">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
            <Home className="w-4 h-4" />
            <span className="text-sm">Back to Home</span>
          </Link>
          <div className="flex items-center gap-3">
            <GraduationCap className="w-5 h-5 text-blue-400" />
            <span className="text-white font-medium">Prompt Engineering Course</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">{completed.length}/12 completed</span>
            <span className="text-sm font-medium text-white">{progress}%</span>
          </div>
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Left Sidebar - Index */}
        <aside className="w-72 bg-slate-900/50 border-r border-slate-800 overflow-y-auto">
          <div className="p-4">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">Course Index</h2>

            {MODULES.map((mod) => {
              const Icon = mod.icon
              return (
                <div key={mod.name} className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`w-7 h-7 rounded-lg bg-gradient-to-br ${mod.color} flex items-center justify-center`}>
                      <Icon className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-sm font-semibold text-white">{mod.name}</span>
                  </div>

                  <div className="space-y-1 ml-1">
                    {mod.lessons.map((id) => {
                      const l = LESSONS.find(x => x.id === id)!
                      const isActive = current === id
                      const isDone = completed.includes(id)

                      return (
                        <button
                          key={id}
                          onClick={() => setCurrent(id)}
                          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                            isActive
                              ? 'bg-blue-500/20 text-white'
                              : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                          }`}
                        >
                          {isDone ? (
                            <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                          ) : (
                            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs flex-shrink-0 ${
                              isActive ? 'border-blue-400 text-blue-400' : 'border-slate-600'
                            }`}>
                              {id}
                            </div>
                          )}
                          <span className="text-sm truncate">{l.title}</span>
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })}

            {/* Start Building CTA */}
            <div className="mt-8 p-4 bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl">
              <p className="text-sm text-slate-300 mb-3">Ready to apply what you learned?</p>
              <Link href="/build">
                <Button size="sm" className="w-full bg-gradient-to-r from-blue-500 to-cyan-500">
                  <Play className="w-4 h-4 mr-2" /> Start Building
                </Button>
              </Link>
            </div>
          </div>
        </aside>

        {/* Right Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-8 py-10">
            {/* Lesson Header */}
            <div className="mb-8">
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                <span className="text-blue-400">{lesson.module}</span>
                <ChevronRight className="w-4 h-4" />
                <span>Lesson {lesson.id} of 12</span>
              </div>
              <h1 className="text-3xl font-bold text-white">{lesson.title}</h1>
            </div>

            {/* Lesson Content */}
            <div className="prose prose-invert max-w-none mb-8">
              {lesson.content.split('\n\n').map((para, i) => (
                <p key={i} className="text-slate-300 text-lg leading-relaxed whitespace-pre-line mb-6">
                  {para}
                </p>
              ))}
            </div>

            {/* Pro Tip */}
            <div className="flex gap-4 p-5 bg-amber-500/10 border border-amber-500/30 rounded-2xl mb-8">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
                <Lightbulb className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="font-semibold text-amber-400 mb-1">Pro Tip</p>
                <p className="text-slate-300">{lesson.tip}</p>
              </div>
            </div>

            {/* Examples */}
            <div className="space-y-4 mb-10">
              <h3 className="text-xl font-semibold text-white">Compare Examples</h3>

              {/* Bad Example */}
              <div className="bg-slate-900 border border-red-500/30 rounded-2xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 bg-red-500/10 border-b border-red-500/20">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-red-500/20 flex items-center justify-center text-red-400 text-sm">✗</span>
                    <span className="font-medium text-red-400">Weak Prompt</span>
                  </div>
                  <button
                    onClick={() => copyText(lesson.bad, 'bad')}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    {copied === 'bad' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                  </button>
                </div>
                <p className="px-5 py-4 text-slate-300 font-mono">{lesson.bad}</p>
              </div>

              {/* Good Example */}
              <div className="bg-slate-900 border border-green-500/30 rounded-2xl overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 bg-green-500/10 border-b border-green-500/20">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 text-sm">✓</span>
                    <span className="font-medium text-green-400">Strong Prompt</span>
                  </div>
                  <button
                    onClick={() => copyText(lesson.good, 'good')}
                    className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    {copied === 'good' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-slate-400" />}
                  </button>
                </div>
                <p className="px-5 py-4 text-slate-300 font-mono">{lesson.good}</p>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between pt-6 border-t border-slate-800">
              <button
                onClick={prevLesson}
                disabled={current === 1}
                className="flex items-center gap-2 px-5 py-3 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
                Previous
              </button>

              <button
                onClick={nextLesson}
                className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl text-white font-medium hover:opacity-90 transition-opacity"
              >
                {completed.includes(current) ? (
                  current === 12 ? 'Complete!' : 'Next Lesson'
                ) : (
                  'Mark Complete'
                )}
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
