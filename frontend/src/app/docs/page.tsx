'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  Zap, ArrowRight, Copy, Check, Lightbulb, Code, Rocket, FileText,
  MessageSquare, Sparkles, ChevronDown, ChevronRight, Play, BookOpen,
  Terminal, Layers, Palette, Database, Globe, Shield, Clock, Target,
  CheckCircle, XCircle, AlertCircle, Settings, Download, Upload,
  Monitor, Smartphone, Tablet, Server, Cloud, GitBranch, Package,
  Cpu, HardDrive, Wifi, Lock, Eye, Edit, Trash2, Plus, Minus,
  Search, Filter, SortAsc, BarChart3, PieChart, TrendingUp,
  Users, ShoppingCart, CreditCard, Mail, Bell, Calendar, Image,
  Video, Music, Map, Navigation, Heart, Star, Award, Zap as Lightning,
  GraduationCap, Brain
} from 'lucide-react'

// ============ PROMPT EXAMPLES ============
const PROMPT_EXAMPLES = [
  {
    category: 'E-Commerce',
    icon: '🛒',
    prompts: [
      {
        title: 'Complete Online Store',
        prompt: 'Build a full e-commerce website for selling electronics with: product catalog with grid/list view, advanced filters (category, price, brand, rating), product detail page with image gallery, shopping cart with quantity controls, wishlist functionality, user authentication (login/register), checkout with address and payment forms, order history page, and admin dashboard for managing products.',
        tags: ['React', 'Node.js', 'MongoDB', 'Stripe']
      },
      {
        title: 'Food Delivery Platform',
        prompt: 'Create a Swiggy/Zomato clone with: restaurant listings with ratings and delivery time, menu display with categories, add to cart functionality, real-time order tracking with map, user reviews and ratings, search with filters (cuisine, price, rating), promotional banners, and delivery address management.',
        tags: ['Next.js', 'Firebase', 'Google Maps', 'Tailwind']
      },
      {
        title: 'Grocery App',
        prompt: 'Build a grocery shopping app with product categories, search functionality, cart management, delivery slot selection, payment integration, order tracking, and recurring order feature for essentials.',
        tags: ['React', 'Redux', 'Node.js']
      }
    ]
  },
  {
    category: 'Business & Admin',
    icon: '📊',
    prompts: [
      {
        title: 'Admin Dashboard',
        prompt: 'Build a comprehensive admin dashboard with: sidebar navigation, header with notifications and profile, overview cards showing KPIs, interactive charts (line, bar, pie, area), data tables with sorting/filtering/pagination, user management CRUD, settings page, dark/light theme toggle, and responsive design for all devices.',
        tags: ['React', 'Chart.js', 'Tailwind', 'shadcn/ui']
      },
      {
        title: 'Project Management Tool',
        prompt: 'Create a Trello/Asana-like project management app with: kanban boards with drag-and-drop, task cards with labels/due dates/assignees, board/list/calendar views, team member management, project progress tracking, comments and attachments on tasks, activity timeline, and notification system.',
        tags: ['React', 'DnD Kit', 'Node.js', 'Socket.io']
      },
      {
        title: 'CRM System',
        prompt: 'Build a customer relationship management system with contact management, lead tracking pipeline, deal stages, email integration, activity logging, reporting dashboard, and team collaboration features.',
        tags: ['Next.js', 'PostgreSQL', 'Prisma']
      },
      {
        title: 'Inventory Management',
        prompt: 'Create an inventory management system with product catalog, stock tracking, low stock alerts, supplier management, purchase orders, sales tracking, barcode scanning, and reporting.',
        tags: ['React', 'Node.js', 'MongoDB']
      }
    ]
  },
  {
    category: 'Landing Pages',
    icon: '🚀',
    prompts: [
      {
        title: 'SaaS Landing Page',
        prompt: 'Design a modern SaaS landing page with: animated hero section with gradient background, floating elements, features grid with icons, how it works section with steps, pricing table with 3 tiers and toggle for monthly/yearly, testimonials carousel with avatars, FAQ accordion, newsletter signup, footer with links, and smooth scroll animations throughout.',
        tags: ['Next.js', 'Framer Motion', 'Tailwind']
      },
      {
        title: 'Portfolio Website',
        prompt: 'Build a developer portfolio with: hero section with animated text, about me with skills progress bars, project gallery with category filters and modal preview, blog section with cards, testimonials, contact form with validation, social links, and dark theme with accent color.',
        tags: ['React', 'GSAP', 'EmailJS']
      },
      {
        title: 'Agency Website',
        prompt: 'Create a digital agency website with services showcase, case studies with before/after, team section, client logos, testimonials, blog, and contact with office locations map.',
        tags: ['Next.js', 'Sanity CMS', 'Tailwind']
      },
      {
        title: 'Restaurant Website',
        prompt: 'Build a restaurant website with hero with food images, menu with categories and prices, online reservation system, gallery, chef profiles, customer reviews, location map, and opening hours.',
        tags: ['React', 'Google Maps', 'Tailwind']
      }
    ]
  },
  {
    category: 'Social & Communication',
    icon: '💬',
    prompts: [
      {
        title: 'Chat Application',
        prompt: 'Create a WhatsApp-like chat application with: contact list with search, one-on-one messaging, group chats, real-time message updates, online/offline status, typing indicators, read receipts, emoji picker, image/file sharing, voice message recording, and message reactions.',
        tags: ['React', 'Socket.io', 'Node.js', 'MongoDB']
      },
      {
        title: 'Social Media Platform',
        prompt: 'Build a Twitter/Instagram clone with: user profiles with follow system, post creation with images/videos, news feed with infinite scroll, likes/comments/shares, hashtags and mentions, explore/discover page, notifications, direct messaging, and stories feature.',
        tags: ['Next.js', 'Firebase', 'Cloudinary']
      },
      {
        title: 'Forum/Community',
        prompt: 'Create a Reddit-like community platform with categories, post creation with rich text, upvote/downvote system, nested comments, user reputation, moderator tools, and search functionality.',
        tags: ['Next.js', 'PostgreSQL', 'Redis']
      }
    ]
  },
  {
    category: 'Education & Learning',
    icon: '📚',
    prompts: [
      {
        title: 'Online Learning Platform',
        prompt: 'Build a Udemy-like learning platform with: course catalog with filters, course detail page with curriculum, video player with progress tracking, quizzes and assignments, certificate generation, instructor dashboard, student progress analytics, and discussion forums.',
        tags: ['Next.js', 'Video.js', 'PostgreSQL']
      },
      {
        title: 'Quiz Application',
        prompt: 'Create an interactive quiz app with multiple question types (MCQ, true/false, fill blanks), timer, score tracking, leaderboard, category selection, difficulty levels, and detailed result analysis.',
        tags: ['React', 'Node.js', 'MongoDB']
      },
      {
        title: 'School Management System',
        prompt: 'Build a school ERP with student/teacher management, attendance tracking, grade management, timetable, fee management, parent portal, and announcements.',
        tags: ['Next.js', 'PostgreSQL', 'Prisma']
      }
    ]
  },
  {
    category: 'Healthcare',
    icon: '🏥',
    prompts: [
      {
        title: 'Hospital Management System',
        prompt: 'Create a hospital management system with: patient registration, doctor profiles and schedules, appointment booking, medical records, prescription management, billing, lab reports, pharmacy inventory, and admin dashboard with analytics.',
        tags: ['React', 'Node.js', 'PostgreSQL']
      },
      {
        title: 'Telemedicine App',
        prompt: 'Build a telemedicine platform with doctor search, appointment scheduling, video consultation, prescription upload, medical history, payment integration, and follow-up reminders.',
        tags: ['Next.js', 'WebRTC', 'Stripe']
      }
    ]
  },
  {
    category: 'Finance & Payments',
    icon: '💰',
    prompts: [
      {
        title: 'Expense Tracker',
        prompt: 'Build a personal finance app with: income/expense tracking, category management, budget setting with alerts, visual reports (pie charts, bar graphs, trends), recurring transactions, multiple accounts, export to CSV/PDF, and monthly/yearly summaries.',
        tags: ['React', 'Chart.js', 'IndexedDB']
      },
      {
        title: 'Invoice Generator',
        prompt: 'Create an invoicing app with client management, customizable invoice templates, tax calculations, payment tracking, recurring invoices, PDF generation, email sending, and payment reminders.',
        tags: ['Next.js', 'PDFKit', 'Nodemailer']
      },
      {
        title: 'Banking Dashboard',
        prompt: 'Build a banking dashboard with account overview, transaction history with filters, fund transfers, bill payments, spending analytics, and security settings.',
        tags: ['React', 'D3.js', 'Node.js']
      }
    ]
  },
  {
    category: 'Productivity',
    icon: '✅',
    prompts: [
      {
        title: 'Task Management App',
        prompt: 'Create a comprehensive todo app with: task creation with title/description/due date, priority levels (high/medium/low), categories/labels, subtasks, recurring tasks, calendar view, reminders, search and filters, drag-and-drop reordering, and progress statistics.',
        tags: ['React', 'DnD Kit', 'LocalStorage']
      },
      {
        title: 'Note Taking App',
        prompt: 'Build a Notion-like note app with rich text editor, markdown support, nested pages, tags, search, favorites, trash/restore, sharing, and export options.',
        tags: ['Next.js', 'TipTap', 'PostgreSQL']
      },
      {
        title: 'Calendar App',
        prompt: 'Create a Google Calendar clone with day/week/month views, event creation with reminders, recurring events, color coding, drag to reschedule, and Google Calendar sync.',
        tags: ['React', 'FullCalendar', 'Node.js']
      }
    ]
  },
  {
    category: 'Media & Entertainment',
    icon: '🎬',
    prompts: [
      {
        title: 'Music Streaming App',
        prompt: 'Build a Spotify-like music player with: song library, playlist creation, album/artist pages, audio player with controls, queue management, shuffle/repeat, search, recently played, liked songs, and visualizer.',
        tags: ['React', 'Web Audio API', 'Node.js']
      },
      {
        title: 'Video Streaming Platform',
        prompt: 'Create a YouTube-like platform with video upload, processing, playback with quality options, comments, likes, subscriptions, playlists, watch history, and recommendations.',
        tags: ['Next.js', 'FFmpeg', 'AWS S3']
      },
      {
        title: 'Photo Gallery',
        prompt: 'Build a photo gallery with albums, image upload with compression, lightbox view, slideshow, tagging, search, sharing, and download options.',
        tags: ['React', 'Cloudinary', 'Masonry']
      }
    ]
  },
  {
    category: 'Real Estate & Travel',
    icon: '🏠',
    prompts: [
      {
        title: 'Property Listing Platform',
        prompt: 'Create an Airbnb/Zillow clone with: property listings with images, advanced search filters (location, price, amenities), map view with markers, property detail page, booking system, host dashboard, reviews, and favorites.',
        tags: ['Next.js', 'Mapbox', 'PostgreSQL']
      },
      {
        title: 'Travel Booking App',
        prompt: 'Build a travel booking platform with flight/hotel search, date selection, price comparison, booking flow, itinerary management, and travel guides.',
        tags: ['React', 'Node.js', 'External APIs']
      }
    ]
  }
]

// ============ TIPS ============
const TIPS = [
  {
    icon: Target,
    title: 'Be Specific & Detailed',
    description: 'Instead of "build a website", describe exactly what pages, features, and functionality you need. More details = better results.'
  },
  {
    icon: Layers,
    title: 'List UI Components',
    description: 'Mention specific components: navbar, sidebar, cards, modals, tables, forms, charts. This ensures complete interfaces.'
  },
  {
    icon: Palette,
    title: 'Describe Design Style',
    description: 'Specify: "modern", "minimalist", "dark theme", "glassmorphism", "gradients", "rounded corners", "shadows".'
  },
  {
    icon: Database,
    title: 'Define Data Structure',
    description: 'Mention what data entities you need: users, products, orders, messages. Include relationships between them.'
  },
  {
    icon: Globe,
    title: 'Reference Known Apps',
    description: 'Say "like Airbnb" or "similar to Slack" to convey complex requirements quickly. We understand popular apps.'
  },
  {
    icon: Shield,
    title: 'Specify Requirements',
    description: 'Include: authentication, responsive design, animations, accessibility, SEO, performance optimization.'
  },
  {
    icon: Monitor,
    title: 'Mention Responsive Design',
    description: 'Specify if you need mobile, tablet, and desktop layouts. Describe how the UI should adapt.'
  },
  {
    icon: Sparkles,
    title: 'Request Animations',
    description: 'Ask for "smooth transitions", "hover effects", "loading states", "skeleton screens" for polished UX.'
  }
]

// ============ WHAT YOU CAN BUILD ============
const CAPABILITIES = [
  {
    title: 'Full-Stack Web Apps',
    description: 'Complete applications with frontend, backend APIs, and database integration.',
    icon: Globe,
    examples: ['E-commerce stores', 'Social platforms', 'SaaS applications', 'Admin dashboards']
  },
  {
    title: 'Landing Pages',
    description: 'Beautiful, conversion-optimized pages with animations and modern design.',
    icon: Rocket,
    examples: ['Product launches', 'SaaS websites', 'Portfolio sites', 'Event pages']
  },
  {
    title: 'Mobile-Responsive UIs',
    description: 'Interfaces that work perfectly on all devices from phones to desktops.',
    icon: Smartphone,
    examples: ['Progressive web apps', 'Mobile-first designs', 'Tablet optimized']
  },
  {
    title: 'Real-time Applications',
    description: 'Apps with live updates, notifications, and instant communication.',
    icon: Wifi,
    examples: ['Chat apps', 'Live dashboards', 'Collaboration tools', 'Gaming']
  },
  {
    title: 'Data Visualization',
    description: 'Interactive charts, graphs, and analytics dashboards.',
    icon: BarChart3,
    examples: ['Analytics dashboards', 'Reports', 'Financial charts', 'Monitoring']
  },
  {
    title: 'CRUD Applications',
    description: 'Complete systems for creating, reading, updating, and deleting data.',
    icon: Database,
    examples: ['CMS systems', 'Inventory management', 'User management', 'Booking systems']
  }
]

// ============ COMMON MISTAKES ============
const MISTAKES = [
  {
    wrong: 'Build me an app',
    right: 'Build a task management app with projects, tasks with due dates, priority levels, and a kanban board view',
    tip: 'Be specific about what type of app and its features'
  },
  {
    wrong: 'Make it look good',
    right: 'Use a dark theme with blue accent colors, rounded corners, subtle shadows, and smooth hover animations',
    tip: 'Describe the exact design style you want'
  },
  {
    wrong: 'Add user stuff',
    right: 'Add user authentication with login, register, forgot password, email verification, and profile management',
    tip: 'List all the user-related features explicitly'
  },
  {
    wrong: 'Make a dashboard',
    right: 'Create an admin dashboard with sidebar navigation, stats cards showing revenue/users/orders, line chart for trends, recent orders table, and notification dropdown',
    tip: 'Describe every component the dashboard should have'
  }
]

// ============ FAQ ============
const FAQ = [
  {
    question: 'What technologies does BharatBuild use?',
    answer: 'BharatBuild generates code using modern technologies including React, Next.js, Node.js, Tailwind CSS, TypeScript, and various databases like MongoDB and PostgreSQL. The AI selects the best stack based on your requirements.'
  },
  {
    question: 'Can I customize the generated code?',
    answer: 'Yes! The generated code is fully yours. You can download it, modify it, and deploy it anywhere. The code is clean, well-structured, and follows best practices.'
  },
  {
    question: 'How detailed should my prompt be?',
    answer: 'The more detailed, the better. Include specific features, UI components, design preferences, and functionality. A 2-3 sentence prompt will give basic results; a detailed paragraph will give comprehensive results.'
  },
  {
    question: 'Can BharatBuild create backend APIs?',
    answer: 'Yes! BharatBuild can generate complete backend code with REST APIs, database schemas, authentication, and more. Just specify your backend requirements in the prompt.'
  },
  {
    question: 'What if the generated code has bugs?',
    answer: 'You can iterate on the code by providing feedback. Tell BharatBuild what needs to be fixed, and it will update the code accordingly. You can also manually fix issues in the downloaded code.'
  },
  {
    question: 'Can I use the code commercially?',
    answer: 'Yes! All code generated by BharatBuild is yours to use for any purpose, including commercial projects. There are no licensing restrictions.'
  },
  {
    question: 'Does BharatBuild create responsive designs?',
    answer: 'Yes, by default all generated UIs are responsive. You can also specifically request mobile-first design or specify breakpoints for different screen sizes.'
  },
  {
    question: 'Can I integrate external APIs?',
    answer: 'Yes! Mention the APIs you want to integrate (Stripe, Google Maps, etc.) in your prompt, and BharatBuild will generate the integration code with proper error handling.'
  }
]

// ============ STEPS ============
const STEPS = [
  {
    step: 1,
    title: 'Describe Your Project',
    description: 'Write a detailed prompt describing what you want to build. Include features, design preferences, and functionality requirements.',
    icon: MessageSquare,
    details: ['Be specific about features', 'Mention UI components', 'Describe the design style', 'List data requirements']
  },
  {
    step: 2,
    title: 'AI Analyzes & Plans',
    description: 'BharatBuild AI understands your requirements, creates a project structure, and plans the implementation.',
    icon: Cpu,
    details: ['Analyzes requirements', 'Selects best technologies', 'Plans file structure', 'Designs database schema']
  },
  {
    step: 3,
    title: 'Code Generation',
    description: 'Watch as the AI generates complete, production-ready code for your entire application.',
    icon: Code,
    details: ['Frontend components', 'Backend APIs', 'Database models', 'Styling & animations']
  },
  {
    step: 4,
    title: 'Live Preview',
    description: 'See your project running in real-time. Test all features and interactions in the preview window.',
    icon: Eye,
    details: ['Interactive preview', 'Test functionality', 'Check responsiveness', 'Verify features']
  },
  {
    step: 5,
    title: 'Download & Deploy',
    description: 'Download the complete source code. Deploy to Vercel, Netlify, AWS, or any hosting platform.',
    icon: Download,
    details: ['Get all source files', 'Includes documentation', 'Ready to deploy', 'Easy to customize']
  }
]

// ============ TECH STACK ============
const TECH_STACK = [
  { name: 'React', icon: '⚛️', description: 'UI components' },
  { name: 'Next.js', icon: '▲', description: 'Full-stack framework' },
  { name: 'TypeScript', icon: '📘', description: 'Type safety' },
  { name: 'Tailwind CSS', icon: '🎨', description: 'Styling' },
  { name: 'Node.js', icon: '💚', description: 'Backend runtime' },
  { name: 'MongoDB', icon: '🍃', description: 'NoSQL database' },
  { name: 'PostgreSQL', icon: '🐘', description: 'SQL database' },
  { name: 'Prisma', icon: '◮', description: 'ORM' },
  { name: 'Socket.io', icon: '🔌', description: 'Real-time' },
  { name: 'Stripe', icon: '💳', description: 'Payments' },
  { name: 'Firebase', icon: '🔥', description: 'BaaS' },
  { name: 'AWS', icon: '☁️', description: 'Cloud services' },
]

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
      title="Copy prompt"
    >
      {copied ? (
        <Check className="w-4 h-4 text-green-400" />
      ) : (
        <Copy className="w-4 h-4 text-slate-400" />
      )}
    </button>
  )
}

export default function DocsPage() {
  const [expandedCategory, setExpandedCategory] = useState<string | null>('E-Commerce')
  const [expandedFaq, setExpandedFaq] = useState<number | null>(0)

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-white">BharatBuild</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/learn" className="text-purple-400 hover:text-purple-300 transition-colors font-medium">
              Prompt Course
            </Link>
            <Link href="/showcase" className="text-slate-400 hover:text-white transition-colors font-medium">
              Showcase
            </Link>
            <Link href="/login" className="text-slate-400 hover:text-white transition-colors font-medium">
              Sign In
            </Link>
            <Link href="/build">
              <Button className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:opacity-90 shadow-lg shadow-blue-500/20">
                Start Building
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative py-16 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-600/10 via-transparent to-transparent" />
        <div className="absolute top-20 left-1/4 w-72 h-72 bg-blue-500/20 rounded-full blur-[100px]" />
        <div className="absolute top-40 right-1/4 w-72 h-72 bg-cyan-500/20 rounded-full blur-[100px]" />

        <div className="relative max-w-4xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-full text-blue-400 text-sm mb-6">
            <BookOpen className="w-4 h-4" />
            <span>Complete Documentation & Guide</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            How to Use <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">BharatBuild</span>
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto mb-8">
            Learn how to write effective prompts and build amazing projects with AI. From simple websites to complex full-stack applications.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <a href="#how-it-works" className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-white font-medium transition-colors">
              How It Works
            </a>
            <a href="#examples" className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-white font-medium transition-colors">
              Prompt Examples
            </a>
            <a href="#tips" className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-white font-medium transition-colors">
              Writing Tips
            </a>
            <a href="#faq" className="px-6 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl text-white font-medium transition-colors">
              FAQ
            </a>
          </div>
        </div>
      </section>

      {/* Course CTA Banner */}
      <section className="max-w-4xl mx-auto px-6 py-8">
        <Link href="/learn">
          <div className="relative overflow-hidden bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-cyan-600/20 border border-purple-500/30 rounded-2xl p-6 hover:border-purple-500/50 transition-all group cursor-pointer">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 to-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative flex flex-col md:flex-row items-center gap-6">
              <div className="p-4 bg-purple-500/20 rounded-2xl">
                <GraduationCap className="w-10 h-10 text-purple-400" />
              </div>
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-xl font-bold text-white mb-2">
                  New: Free Prompt Engineering Course
                </h3>
                <p className="text-slate-400">
                  Learn to write perfect prompts from basics to advanced. Interactive lessons, practice exercises, and real-world examples.
                </p>
              </div>
              <div className="flex items-center gap-2 px-6 py-3 bg-purple-500/20 rounded-xl text-purple-400 font-medium group-hover:bg-purple-500/30 transition-colors">
                Start Learning <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </div>
        </Link>
      </section>

      {/* What You Can Build */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">What You Can Build</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          BharatBuild can generate any type of web application. Here are some categories:
        </p>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {CAPABILITIES.map((cap, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-slate-700 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center mb-4">
                <cap.icon className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">{cap.title}</h3>
              <p className="text-sm text-slate-400 mb-4">{cap.description}</p>
              <div className="flex flex-wrap gap-2">
                {cap.examples.map((ex, j) => (
                  <span key={j} className="px-2 py-1 bg-slate-800 text-slate-500 text-xs rounded-lg">{ex}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Technologies We Use</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          BharatBuild generates code using modern, industry-standard technologies.
        </p>

        <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {TECH_STACK.map((tech, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-center hover:border-slate-700 transition-colors">
              <div className="text-3xl mb-2">{tech.icon}</div>
              <h4 className="font-medium text-white text-sm">{tech.name}</h4>
              <p className="text-xs text-slate-500">{tech.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">How It Works</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          BharatBuild uses advanced AI to turn your ideas into working code in 5 simple steps.
        </p>

        <div className="space-y-6">
          {STEPS.map((step, i) => (
            <div key={i} className="flex gap-6 items-start">
              <div className="flex-shrink-0">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg">
                  <step.icon className="w-7 h-7 text-white" />
                </div>
              </div>
              <div className="flex-1 bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-2">
                  <span className="px-3 py-1 bg-blue-500/20 text-blue-400 text-sm rounded-full font-medium">Step {step.step}</span>
                  <h3 className="text-xl font-semibold text-white">{step.title}</h3>
                </div>
                <p className="text-slate-400 mb-4">{step.description}</p>
                <div className="flex flex-wrap gap-2">
                  {step.details.map((detail, j) => (
                    <span key={j} className="flex items-center gap-1 text-sm text-slate-500">
                      <CheckCircle className="w-4 h-4 text-green-500" /> {detail}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Writing Good Prompts */}
      <section id="tips" className="max-w-6xl mx-auto px-6 py-16">
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-3xl p-8 md:p-12">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
              <Lightbulb className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Tips for Writing Great Prompts</h2>
              <p className="text-slate-400">Follow these guidelines for best results</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {TIPS.map((tip, i) => (
              <div key={i} className="bg-slate-800/50 rounded-xl p-5 hover:bg-slate-800 transition-colors">
                <div className="flex items-center gap-3 mb-3">
                  <tip.icon className="w-5 h-5 text-blue-400" />
                  <h3 className="font-semibold text-white">{tip.title}</h3>
                </div>
                <p className="text-sm text-slate-400">{tip.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Common Mistakes */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Common Mistakes to Avoid</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          Learn from these examples to write better prompts.
        </p>

        <div className="grid md:grid-cols-2 gap-6">
          {MISTAKES.map((mistake, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <div className="space-y-4">
                <div>
                  <div className="flex items-center gap-2 text-red-400 text-sm font-medium mb-2">
                    <XCircle className="w-4 h-4" /> Don't write this
                  </div>
                  <p className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-300 text-sm">
                    "{mistake.wrong}"
                  </p>
                </div>
                <div>
                  <div className="flex items-center gap-2 text-green-400 text-sm font-medium mb-2">
                    <CheckCircle className="w-4 h-4" /> Write this instead
                  </div>
                  <p className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-green-300 text-sm">
                    "{mistake.right}"
                  </p>
                </div>
                <div className="flex items-start gap-2 text-slate-400 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{mistake.tip}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Prompt Structure */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Prompt Structure Template</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          Follow this structure to write comprehensive prompts that generate the best results.
        </p>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8">
          <div className="space-y-6">
            {[
              { num: 1, title: 'Project Type', desc: 'What are you building?', example: '"Build an e-commerce website..."' },
              { num: 2, title: 'Core Features', desc: 'What functionality do you need?', example: '"...with product catalog, shopping cart, user authentication, checkout..."' },
              { num: 3, title: 'UI Components', desc: 'What interface elements?', example: '"...Include navbar with search, sidebar filters, product cards, modal quick view..."' },
              { num: 4, title: 'Design Style', desc: 'How should it look?', example: '"...Use dark theme, gradient accents, rounded corners, smooth animations..."' },
              { num: 5, title: 'Technical Requirements', desc: 'Any specific needs?', example: '"...Make it responsive, add loading states, include form validation..."' },
            ].map((item) => (
              <div key={item.num} className="flex gap-4">
                <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center text-white font-bold flex-shrink-0">
                  {item.num}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-white">{item.title}</h3>
                    <span className="text-slate-500 text-sm">— {item.desc}</span>
                  </div>
                  <code className="block text-sm bg-slate-800 text-cyan-400 px-4 py-2 rounded-lg">
                    {item.example}
                  </code>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 p-6 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/20 rounded-xl">
            <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-400" /> Complete Example Prompt
            </h4>
            <p className="text-slate-300 text-sm leading-relaxed mb-4">
              "Build an e-commerce website for selling electronics with product catalog showing items in a grid with images/prices/ratings, advanced filters for category/price/brand, product detail page with image gallery and reviews, shopping cart with quantity controls and price calculation, user authentication with login/register/profile, checkout flow with shipping address and payment form, and order confirmation with email. Use a modern dark theme with blue gradient accents, rounded corners, hover animations on cards, and a responsive design that works on mobile. Include loading skeletons, form validation, and error handling."
            </p>
            <CopyButton text="Build an e-commerce website for selling electronics with product catalog showing items in a grid with images/prices/ratings, advanced filters for category/price/brand, product detail page with image gallery and reviews, shopping cart with quantity controls and price calculation, user authentication with login/register/profile, checkout flow with shipping address and payment form, and order confirmation with email. Use a modern dark theme with blue gradient accents, rounded corners, hover animations on cards, and a responsive design that works on mobile. Include loading skeletons, form validation, and error handling." />
          </div>
        </div>
      </section>

      {/* Prompt Examples */}
      <section id="examples" className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Ready-to-Use Prompt Examples</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          Copy these prompts directly or customize them for your needs. Click on a category to expand.
        </p>

        <div className="space-y-4">
          {PROMPT_EXAMPLES.map((category) => (
            <div key={category.category} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
              <button
                onClick={() => setExpandedCategory(expandedCategory === category.category ? null : category.category)}
                className="w-full px-6 py-5 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <span className="text-3xl">{category.icon}</span>
                  <div className="text-left">
                    <span className="text-lg font-semibold text-white block">{category.category}</span>
                    <span className="text-sm text-slate-500">{category.prompts.length} example prompts</span>
                  </div>
                </div>
                {expandedCategory === category.category ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </button>

              {expandedCategory === category.category && (
                <div className="px-6 pb-6 space-y-4">
                  {category.prompts.map((example, i) => (
                    <div key={i} className="bg-slate-800 rounded-xl p-5">
                      <div className="flex items-start justify-between mb-3">
                        <h4 className="font-semibold text-white text-lg">{example.title}</h4>
                        <CopyButton text={example.prompt} />
                      </div>
                      <p className="text-slate-300 text-sm mb-4 leading-relaxed bg-slate-900 p-4 rounded-lg border border-slate-700">
                        "{example.prompt}"
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {example.tags.map((tag, j) => (
                          <span key={j} className="px-3 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-lg font-medium">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="max-w-4xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-4">Frequently Asked Questions</h2>
        <p className="text-slate-400 text-center mb-12 max-w-2xl mx-auto">
          Got questions? We've got answers.
        </p>

        <div className="space-y-4">
          {FAQ.map((item, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedFaq(expandedFaq === i ? null : i)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
              >
                <span className="font-medium text-white text-left">{item.question}</span>
                {expandedFaq === i ? (
                  <Minus className="w-5 h-5 text-slate-400 flex-shrink-0" />
                ) : (
                  <Plus className="w-5 h-5 text-slate-400 flex-shrink-0" />
                )}
              </button>
              {expandedFaq === i && (
                <div className="px-6 pb-4">
                  <p className="text-slate-400">{item.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 border border-blue-500/30 rounded-3xl p-12">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to Build Something Amazing?</h2>
          <p className="text-slate-400 mb-8 max-w-lg mx-auto">
            Now that you know how to write effective prompts, start creating your project. Turn your ideas into reality with BharatBuild.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/build">
              <Button size="lg" className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:opacity-90 shadow-lg shadow-blue-500/25 text-lg px-8 py-6">
                Start Building Now <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
            <Link href="/showcase">
              <Button size="lg" variant="outline" className="border-slate-600 text-white hover:bg-slate-800 text-lg px-8 py-6">
                View Showcase <Eye className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-white">BharatBuild</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-slate-400">
            <Link href="/showcase" className="hover:text-white transition-colors">Showcase</Link>
            <Link href="/docs" className="hover:text-white transition-colors">Documentation</Link>
            <Link href="/build" className="hover:text-white transition-colors">Build</Link>
          </div>
          <p className="text-sm text-slate-500">© 2024 BharatBuild. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
