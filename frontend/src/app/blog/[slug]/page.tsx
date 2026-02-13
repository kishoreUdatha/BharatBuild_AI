import Link from 'next/link'
import { ArrowLeft, Clock, ArrowRight, Twitter, Linkedin, Copy } from 'lucide-react'
import { Metadata } from 'next'

const blogContent: Record<string, {
  title: string
  excerpt: string
  date: string
  readTime: string
  category: string
  content: string
}> = {
  'complete-final-year-project-with-ai': {
    title: 'How to Complete Your Final Year Project in 2 Days Using AI',
    excerpt: 'Learn how to generate complete final year projects with source code, documentation, PPT & viva Q&A using AI.',
    date: '2024-12-15',
    readTime: '8 min',
    category: 'Guide',
    content: `
The final year project is one of the most challenging aspects of engineering education. With AI tools, you can now complete quality projects much faster.

## Why Use AI for Your Final Year Project?

Traditional project development takes months. AI can accelerate this significantly:

- **Code Generation**: AI writes clean, documented code based on your requirements
- **Documentation**: Auto-generate IEEE format reports, SRS documents
- **Presentations**: Create professional PPTs with proper structure
- **Viva Prep**: Get Q&A preparation materials

## Step-by-Step Guide

### Step 1: Choose Your Project Idea

Select a project that solves a real problem. Popular domains include:

- Machine Learning & AI
- Web Applications
- Mobile Apps
- IoT Systems
- Blockchain

### Step 2: Use BharatBuild AI

BharatBuild AI can generate your entire project:

1. Describe your project requirements
2. Select your tech stack
3. AI generates complete source code
4. Get documentation automatically

### Step 3: Customize and Review

Always review and customize the generated code:

- Understand the code logic
- Add your unique features
- Test thoroughly
- Document your changes

### Step 4: Prepare Documentation

AI can generate:

- IEEE format project report
- System Requirements Specification (SRS)
- Database design documents
- User manuals

### Step 5: Create Presentation

Generate professional presentations:

- Problem statement
- Proposed solution
- Architecture diagrams
- Demo screenshots
- Future scope

## Best Practices

1. **Understand Your Code**: Don't just submit AI-generated code. Study it.
2. **Add Original Features**: Make your project unique
3. **Test Everything**: Ensure all features work correctly
4. **Prepare for Viva**: Know every aspect of your project

## Conclusion

AI tools like BharatBuild can significantly accelerate your final year project. Use them wisely as learning aids, not shortcuts.
    `,
  },
  'ieee-format-project-report-guide': {
    title: 'IEEE Format Project Report: Complete Guide with Free Template',
    excerpt: 'Complete guide to writing IEEE format project reports. Learn structure, formatting rules, and download free templates.',
    date: '2024-12-10',
    readTime: '12 min',
    category: 'Documentation',
    content: `
IEEE format is the standard for technical documentation in engineering projects. This guide covers everything you need to know.

## What is IEEE Format?

IEEE (Institute of Electrical and Electronics Engineers) format is a standardized documentation style used in technical and engineering fields.

## Document Structure

### 1. Title Page

Include:
- Project title
- Student names and roll numbers
- Guide name
- College name
- Year

### 2. Abstract

A 150-250 word summary covering:
- Problem statement
- Methodology
- Key results
- Conclusions

### 3. Table of Contents

List all sections with page numbers.

### 4. Introduction

Cover:
- Background
- Problem definition
- Objectives
- Scope

### 5. Literature Survey

Review existing solutions and research papers.

### 6. System Requirements

#### Hardware Requirements
- Processor specifications
- RAM requirements
- Storage needs

#### Software Requirements
- Operating system
- Programming languages
- Frameworks and libraries

### 7. System Design

Include:
- Architecture diagrams
- Data flow diagrams
- ER diagrams
- Use case diagrams

### 8. Implementation

Document:
- Code structure
- Key algorithms
- Screenshots

### 9. Testing

Cover:
- Test cases
- Results
- Bug fixes

### 10. Conclusion

Summarize:
- Achievements
- Limitations
- Future scope

### 11. References

Use IEEE citation format.

## Formatting Rules

- **Font**: Times New Roman, 12pt
- **Margins**: 1 inch all sides
- **Line Spacing**: 1.5
- **Page Numbers**: Bottom center

## Auto-Generate with AI

BharatBuild AI can generate IEEE format reports automatically based on your project details.
    `,
  },
  'ai-code-generators-compared': {
    title: 'AI Code Generators Compared: BharatBuild vs Bolt vs v0 vs Cursor',
    excerpt: 'Comprehensive comparison of AI code generators. Compare features, pricing, and capabilities.',
    date: '2024-12-05',
    readTime: '15 min',
    category: 'Comparison',
    content: `
The AI code generation landscape is evolving rapidly. Here's a detailed comparison of popular tools.

## Overview

| Tool | Focus | Best For |
|------|-------|----------|
| BharatBuild | Full Projects | Students, Startups |
| Bolt.new | Web Apps | Quick Prototypes |
| v0.dev | UI Components | Frontend Devs |
| Cursor | Code Editing | Developers |
| GitHub Copilot | Code Completion | All Developers |

## BharatBuild AI

**Strengths:**
- Complete project generation
- Documentation included
- 50+ tech stack support
- Student-focused pricing
- Indian market focus

**Best For:**
- Final year projects
- MVP development
- Learning programming

## Bolt.new

**Strengths:**
- Fast web app generation
- Real-time preview
- Simple interface

**Limitations:**
- Limited to web apps
- No documentation
- Expensive for regular use

## v0.dev

**Strengths:**
- Excellent UI generation
- Shadcn/ui integration
- Clean code output

**Limitations:**
- UI only, no backend
- Limited customization
- Waitlist access

## Cursor

**Strengths:**
- IDE integration
- Code editing focus
- Good context understanding

**Limitations:**
- Requires coding knowledge
- Not for complete projects
- Learning curve

## GitHub Copilot

**Strengths:**
- Wide IDE support
- Good suggestions
- Microsoft backing

**Limitations:**
- Subscription required
- Code completion only
- No project generation

## Pricing Comparison

| Tool | Free Tier | Paid Plans |
|------|-----------|------------|
| BharatBuild | 3 projects | ₹299/month |
| Bolt.new | Limited | $20/month |
| v0.dev | Limited | $20/month |
| Cursor | Trial | $20/month |
| Copilot | None | $10/month |

## Recommendation

- **Students**: BharatBuild AI for complete projects
- **Startups**: BharatBuild or Bolt for MVPs
- **Developers**: Cursor or Copilot for daily coding
- **Designers**: v0.dev for UI prototypes

## Conclusion

Choose based on your specific needs. BharatBuild excels for complete project generation, especially for the Indian market.
    `,
  },
  'build-mvp-without-coding': {
    title: 'Build Your MVP Without a Technical Co-founder',
    excerpt: 'Learn how to build your startup MVP without coding. Use AI tools to create production-ready products.',
    date: '2024-11-28',
    readTime: '10 min',
    category: 'Startup',
    content: `
Building an MVP without technical skills is now possible with AI tools. Here's your complete guide.

## What is an MVP?

Minimum Viable Product (MVP) is the simplest version of your product that delivers value to users.

## Why Build Without Coding?

1. **Speed**: Launch in days, not months
2. **Cost**: Save on developer hiring
3. **Validation**: Test ideas quickly
4. **Focus**: Concentrate on business, not code

## Step-by-Step Process

### 1. Define Your Idea

Write a clear problem statement:
- Who are your users?
- What problem do you solve?
- What's your unique value?

### 2. List Core Features

Focus on essential features only:
- User authentication
- Core functionality
- Basic UI
- Data storage

### 3. Choose Your Tools

**AI Code Generators:**
- BharatBuild AI for complete apps
- Bolt.new for web apps
- v0.dev for UI components

**No-Code Platforms:**
- Bubble for web apps
- Adalo for mobile apps
- Webflow for websites

### 4. Generate Your MVP

Using BharatBuild AI:

1. Describe your product
2. Select features
3. Choose tech stack
4. Generate code
5. Deploy

### 5. Launch and Iterate

- Get user feedback
- Track metrics
- Improve based on data

## Real Examples

**Example 1: SaaS Dashboard**
- Generated in 2 hours
- React + Node.js
- Includes auth, billing

**Example 2: Mobile App**
- Flutter cross-platform
- Backend included
- Ready for app stores

## Cost Comparison

| Method | Cost | Time |
|--------|------|------|
| Hire Developers | ₹5-10 lakhs | 3-6 months |
| AI Generation | ₹3,000 | 1-2 days |
| No-Code | ₹10,000/month | 2-4 weeks |

## Conclusion

AI tools have democratized software development. You can now build and validate your startup idea without writing code.
    `,
  },
  '50-final-year-project-ideas-cse': {
    title: '50 Final Year Project Ideas for CSE Students (2024)',
    excerpt: 'Top 50 final year project ideas for CSE, IT, and computer science students with tech stack details.',
    date: '2024-11-20',
    readTime: '20 min',
    category: 'Ideas',
    content: `
Finding the right project idea is crucial. Here are 50 innovative ideas for your final year project.

## Machine Learning Projects

1. **Sentiment Analysis System** - Tech: Python, NLTK, TensorFlow

2. **Disease Prediction System** - Tech: Python, Scikit-learn

3. **Fake News Detection** - Tech: Python, NLP, ML

4. **Stock Price Prediction** - Tech: Python, LSTM, Pandas

5. **Face Recognition Attendance** - Tech: Python, OpenCV, dlib

## Web Development Projects

6. **E-commerce Platform** - Tech: React, Node.js, MongoDB

7. **Learning Management System** - Tech: Next.js, PostgreSQL

8. **Job Portal** - Tech: MERN Stack

9. **Healthcare Management** - Tech: React, Express, MySQL

10. **Social Media Platform** - Tech: React, Firebase

## Mobile App Projects

11. **Fitness Tracking App** - Tech: Flutter, Firebase

12. **Food Delivery App** - Tech: React Native, Node.js

13. **Expense Tracker** - Tech: Flutter, SQLite

14. **Study Planner** - Tech: Kotlin, Room DB

15. **Emergency Services App** - Tech: Flutter, Google Maps

## IoT Projects

16. **Smart Home Automation** - Tech: Arduino, ESP32, MQTT

17. **Air Quality Monitor** - Tech: Raspberry Pi, Sensors

18. **Smart Agriculture** - Tech: Arduino, Sensors, Cloud

19. **Vehicle Tracking System** - Tech: GPS, GSM, Arduino

20. **Smart Parking System** - Tech: IoT Sensors, App

## Blockchain Projects

21. **Voting System** - Tech: Ethereum, Solidity

22. **Supply Chain Tracking** - Tech: Hyperledger

23. **Certificate Verification** - Tech: Ethereum, IPFS

24. **Crowdfunding Platform** - Tech: Solidity, React

25. **NFT Marketplace** - Tech: Ethereum, Web3.js

## How to Choose

Consider:
- Your interests
- Available time
- Resources needed
- Career goals

## Conclusion

Choose a project that excites you and aligns with your career goals. BharatBuild AI can help you build any of these projects quickly.
    `,
  },
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const post = blogContent[params.slug]
  if (!post) {
    return { title: 'Post Not Found | BharatBuild AI' }
  }
  return {
    title: `${post.title} | BharatBuild AI Blog`,
    description: post.excerpt,
  }
}

export default function BlogPost({ params }: { params: { slug: string } }) {
  const post = blogContent[params.slug]

  if (!post) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-white mb-2">Post not found</h1>
          <Link href="/blog" className="text-blue-400 hover:underline">Back to blog</Link>
        </div>
      </div>
    )
  }

  const relatedPosts = Object.entries(blogContent)
    .filter(([slug]) => slug !== params.slug)
    .slice(0, 3)

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Header */}
      <header className="border-b border-white/10 sticky top-0 bg-[#0a0a0f]/90 backdrop-blur-md z-50">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-white font-bold text-sm">B</span>
              </div>
              <span className="font-semibold text-white">BharatBuild</span>
            </Link>

            <nav className="flex items-center gap-6">
              <Link href="/blog" className="text-sm text-gray-400 hover:text-white transition-colors">Blog</Link>
              <Link href="/build" className="text-sm px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                Get Started
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6">
        {/* Back */}
        <div className="pt-8 pb-4">
          <Link href="/blog" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
            Back to blog
          </Link>
        </div>

        {/* Header */}
        <header className="pb-8 border-b border-white/10">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-medium text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-full border border-blue-500/20">
              {post.category}
            </span>
            <span className="text-sm text-gray-500 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {post.readTime} read
            </span>
          </div>

          <h1 className="text-2xl md:text-3xl font-semibold text-white mb-4 leading-tight">
            {post.title}
          </h1>

          <p className="text-gray-400 mb-6">{post.excerpt}</p>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-white font-semibold text-sm">BB</span>
              </div>
              <div>
                <p className="text-sm font-medium text-white">BharatBuild Team</p>
                <p className="text-xs text-gray-500">
                  {new Date(post.date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button className="p-2 text-gray-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                <Copy className="w-4 h-4" />
              </button>
              <button className="p-2 text-gray-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                <Twitter className="w-4 h-4" />
              </button>
              <button className="p-2 text-gray-500 hover:text-white hover:bg-white/5 rounded-lg transition-colors">
                <Linkedin className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Content */}
        <article className="py-10">
          <div className="space-y-4">
            {post.content.split('\n').map((line, idx) => {
              const trimmed = line.trim()
              if (!trimmed) return null

              if (trimmed.startsWith('## ')) {
                return <h2 key={idx} className="text-xl font-semibold text-white mt-10 mb-4 pt-6 border-t border-white/10">{trimmed.replace('## ', '')}</h2>
              }
              if (trimmed.startsWith('### ')) {
                return <h3 key={idx} className="text-lg font-medium text-white mt-8 mb-3">{trimmed.replace('### ', '')}</h3>
              }
              if (trimmed.startsWith('#### ')) {
                return <h4 key={idx} className="text-base font-medium text-gray-300 mt-6 mb-2">{trimmed.replace('#### ', '')}</h4>
              }
              if (trimmed.startsWith('- **')) {
                const match = trimmed.match(/- \*\*(.+?)\*\*:?\s*(.*)/)
                if (match) {
                  return (
                    <div key={idx} className="flex gap-3 py-1.5">
                      <span className="text-blue-400 mt-0.5">•</span>
                      <p className="text-gray-400"><span className="text-white font-medium">{match[1]}</span>{match[2] ? `: ${match[2]}` : ''}</p>
                    </div>
                  )
                }
              }
              if (trimmed.startsWith('- ')) {
                return (
                  <div key={idx} className="flex gap-3 py-1">
                    <span className="text-gray-600 mt-0.5">•</span>
                    <p className="text-gray-400">{trimmed.replace('- ', '')}</p>
                  </div>
                )
              }
              if (trimmed.match(/^\d+\.\s\*\*/)) {
                const match = trimmed.match(/^(\d+)\.\s\*\*(.+?)\*\*\s*[-–]?\s*(.*)/)
                if (match) {
                  return (
                    <div key={idx} className="flex gap-3 py-2">
                      <span className="text-sm font-medium text-blue-400 bg-blue-500/10 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">{match[1]}</span>
                      <p className="text-gray-400"><span className="text-white font-medium">{match[2]}</span>{match[3] ? ` — ${match[3]}` : ''}</p>
                    </div>
                  )
                }
              }
              if (trimmed.match(/^\d+\.\s/)) {
                return (
                  <div key={idx} className="flex gap-3 py-1">
                    <span className="text-gray-600 text-sm">{trimmed.match(/^\d+/)?.[0]}.</span>
                    <p className="text-gray-400">{trimmed.replace(/^\d+\.\s/, '')}</p>
                  </div>
                )
              }
              if (trimmed.startsWith('|')) return null

              return <p key={idx} className="text-gray-400 leading-relaxed">{trimmed}</p>
            })}
          </div>
        </article>

        {/* CTA */}
        <section className="py-8 border-t border-white/10">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-2">Ready to build your project?</h3>
            <p className="text-gray-500 text-sm mb-4">Generate complete projects with AI. Start free with 3 projects.</p>
            <Link href="/build" className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg hover:opacity-90 transition-opacity">
              Start Building <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </section>

        {/* Related */}
        <section className="py-8 border-t border-white/10">
          <h3 className="text-lg font-semibold text-white mb-6">Related articles</h3>
          <div className="space-y-4">
            {relatedPosts.map(([slug, relatedPost]) => (
              <Link href={`/blog/${slug}`} key={slug} className="group flex items-center justify-between py-3 border-b border-white/5 last:border-0">
                <div>
                  <span className="text-xs text-gray-600">{relatedPost.category}</span>
                  <h4 className="text-white font-medium group-hover:text-blue-400 transition-colors">{relatedPost.title}</h4>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors flex-shrink-0" />
              </Link>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-12">
        <div className="max-w-3xl mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <span className="text-white font-bold text-xs">B</span>
              </div>
              <span className="text-sm text-gray-500">© 2025 BharatBuild AI</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-500">
              <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
              <Link href="/terms" className="hover:text-white transition-colors">Terms</Link>
              <Link href="/" className="hover:text-white transition-colors">Home</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
