'use client'

import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import {
  Home,
  FileText,
  Code,
  Award,
  User,
  Bell,
  LogOut,
  Settings,
  BookOpen,
  BarChart3,
  Beaker,
  Target
} from 'lucide-react'

const navItems = [
  { id: 'dashboard', title: 'Dashboard', icon: Home, href: '/student' },
  { id: 'assignments', title: 'Assignments', icon: FileText, href: '/student/assignments' },
  { id: 'project', title: 'My Project', icon: Target, href: '/student/projects' },
  { id: 'labs', title: 'Lab Practice', icon: Beaker, href: '/lab' },
  { id: 'playground', title: 'Code Playground', icon: Code, href: '/playground' },
  { id: 'progress', title: 'My Progress', icon: BarChart3, href: '/student/progress' },
  { id: 'achievements', title: 'Achievements', icon: Award, href: '/student/achievements' },
  { id: 'profile', title: 'Profile', icon: User, href: '/student/profile' },
]

export default function StudentLayout({
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

  const getPageTitle = () => {
    const item = navItems.find(item =>
      item.href === '/student'
        ? pathname === '/student'
        : pathname.startsWith(item.href)
    )
    return item?.title || 'Student Portal'
  }

  return (
    <div className="h-screen bg-gray-900 flex overflow-hidden">
      {/* Left Sidebar */}
      <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-4 border-b border-gray-700">
          <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-blue-600 rounded-xl flex items-center justify-center text-white font-bold">B</div>
          <div>
            <h1 className="text-white font-semibold">BharatBuild</h1>
            <p className="text-gray-500 text-xs">Student Portal</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 overflow-y-auto scrollbar-hide">
          {navItems.map((item) => {
            const isActive = item.href === '/student'
              ? pathname === '/student'
              : pathname.startsWith(item.href)
            return (
              <Link key={item.id} href={item.href}>
                <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-all ${
                  isActive
                    ? 'bg-green-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}>
                  <item.icon className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm font-medium">{item.title}</span>
                </div>
              </Link>
            )
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-green-400 font-semibold text-sm">ST</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">Student User</p>
              <p className="text-gray-500 text-xs truncate">CSE - 3rd Year</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg text-sm transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
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
