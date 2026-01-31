'use client'

import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import {
  Users, FileText, Code, BarChart3, Shield,
  MessageSquare, ClipboardList, Activity, User,
  Bell, Home, BookOpen, LogOut, Settings, Beaker,
  GraduationCap, Target, Database
} from 'lucide-react'

const navItems = [
  { id: 'dashboard', title: 'Dashboard', icon: Home, href: '/faculty' },
  { id: 'students', title: 'Students', icon: Users, href: '/faculty/students' },
  { id: 'subjects', title: 'Subjects', icon: BookOpen, href: '/faculty/subjects' },
  { id: 'labs', title: 'Lab Management', icon: Beaker, href: '/faculty/labs/management' },
  { id: 'tests', title: 'Tests & Exams', icon: Target, href: '/faculty/tests' },
  { id: 'marks', title: 'Marks Management', icon: Database, href: '/faculty/marks' },
  { id: 'project-guidance', title: 'Project Guidance', icon: GraduationCap, href: '/faculty/project-guidance' },
  { id: 'assignments', title: 'Assignments', icon: FileText, href: '/faculty/assignments' },
  { id: 'activity', title: 'Activity', icon: Activity, href: '/faculty/activity' },
  { id: 'integrity', title: 'Integrity', icon: Shield, href: '/faculty/integrity' },
  { id: 'code-review', title: 'Code Review', icon: Code, href: '/faculty/code-review' },
  { id: 'reports', title: 'Reports', icon: BarChart3, href: '/faculty/reports' },
  { id: 'communication', title: 'Messages', icon: MessageSquare, href: '/faculty/communication' },
  { id: 'profile', title: 'Profile', icon: User, href: '/faculty/profile' },
]

export default function FacultyLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()

  const handleLogout = () => {
    localStorage.clear()
    router.push('/login')
  }

  // Get page title from pathname
  const getPageTitle = () => {
    // Find matching nav item (exact or starts-with for nested routes)
    const item = navItems.find(item =>
      item.href === '/faculty'
        ? pathname === '/faculty'
        : pathname.startsWith(item.href)
    )
    return item?.title || 'Faculty'
  }

  return (
    <div className="h-screen bg-gray-900 flex overflow-hidden">
      {/* Left Sidebar - Fixed */}
      <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-4 border-b border-gray-700">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold">B</div>
          <div>
            <h1 className="text-white font-semibold">BharatBuild</h1>
            <p className="text-gray-500 text-xs">Faculty Portal</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 overflow-y-auto scrollbar-hide">
          {navItems.map((item) => {
            // Handle exact match for dashboard, starts-with for others
            const isActive = item.href === '/faculty'
              ? pathname === '/faculty'
              : pathname.startsWith(item.href)
            return (
              <Link key={item.id} href={item.href}>
                <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}>
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm font-medium">{item.title}</span>
                </div>
              </Link>
            )
          })}
        </nav>

      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6 flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-white">{getPageTitle()}</h2>
          </div>
          <div className="flex items-center gap-4">
            <button className="relative p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
            <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg">
              <Settings className="w-5 h-5" />
            </button>
            <div className="h-8 w-px bg-gray-700"></div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-white text-sm font-medium">Dr. Faculty</p>
                <p className="text-gray-500 text-xs">Professor</p>
              </div>
              <div className="w-9 h-9 bg-blue-500/20 rounded-full flex items-center justify-center">
                <span className="text-blue-400 font-semibold text-sm">DR</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg text-sm transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto scrollbar-hide">
          {children}
        </main>
      </div>
    </div>
  )
}
