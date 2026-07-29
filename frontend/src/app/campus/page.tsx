'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  BookOpen,
  Code2,
  Trophy,
  GraduationCap,
  FileText,
  Play,
  ChevronRight,
  Sparkles,
  Users,
  Building2,
  CheckCircle2
} from 'lucide-react'

// Syllabus topics by semester
const SYLLABUS = {
  'Semester 1-2': [
    { name: 'C Programming Basics', topics: ['Variables', 'Loops', 'Functions', 'Arrays', 'Pointers'] },
    { name: 'Python Fundamentals', topics: ['Syntax', 'Lists', 'Dictionaries', 'File I/O'] },
  ],
  'Semester 3-4': [
    { name: 'Data Structures', topics: ['Linked Lists', 'Stacks', 'Queues', 'Trees', 'Graphs'] },
    { name: 'Database Management', topics: ['SQL Queries', 'Normalization', 'ER Diagrams', 'Joins'] },
    { name: 'Object-Oriented Programming', topics: ['Classes', 'Inheritance', 'Polymorphism', 'Abstraction'] },
  ],
  'Semester 5-6': [
    { name: 'Web Development', topics: ['HTML/CSS', 'JavaScript', 'React', 'Node.js', 'APIs'] },
    { name: 'Software Engineering', topics: ['SDLC', 'Agile', 'UML Diagrams', 'Testing'] },
    { name: 'Operating Systems', topics: ['Process Scheduling', 'Memory Management', 'File Systems'] },
  ],
  'Semester 7-8': [
    { name: 'Advanced Web/Mobile', topics: ['React Advanced', 'Flutter', 'Cloud Deployment'] },
    { name: 'Machine Learning', topics: ['Regression', 'Classification', 'Neural Networks'] },
    { name: 'Final Year Project', topics: ['Full Stack App', 'Documentation', 'Presentation'] },
  ],
}

// Quick project templates for students
const PROJECT_TEMPLATES = [
  {
    name: 'E-Commerce Website',
    tech: 'React + Node.js',
    difficulty: 'Medium',
    semester: '5-6',
    description: 'Complete shopping cart with payment integration'
  },
  {
    name: 'Hospital Management',
    tech: 'React + Python',
    difficulty: 'Hard',
    semester: '7-8',
    description: 'Patient records, appointments, billing system'
  },
  {
    name: 'Student Portal',
    tech: 'React + Firebase',
    difficulty: 'Easy',
    semester: '5-6',
    description: 'Attendance, grades, announcements'
  },
  {
    name: 'Chat Application',
    tech: 'React + Socket.io',
    difficulty: 'Medium',
    semester: '5-6',
    description: 'Real-time messaging with rooms'
  },
  {
    name: 'Library Management',
    tech: 'Java + MySQL',
    difficulty: 'Medium',
    semester: '3-4',
    description: 'Book catalog, issue/return system'
  },
  {
    name: 'Weather App',
    tech: 'React + API',
    difficulty: 'Easy',
    semester: '5-6',
    description: 'Fetch and display weather data'
  },
]

// Coding practice categories
const PRACTICE_CATEGORIES = [
  { name: 'Arrays & Strings', count: 50, difficulty: 'Easy-Medium' },
  { name: 'Linked Lists', count: 30, difficulty: 'Medium' },
  { name: 'Trees & Graphs', count: 40, difficulty: 'Medium-Hard' },
  { name: 'Dynamic Programming', count: 35, difficulty: 'Hard' },
  { name: 'SQL Queries', count: 40, difficulty: 'Easy-Medium' },
  { name: 'Company Questions', count: 100, difficulty: 'Mixed' },
]

export default function CampusPage() {
  const [activeTab, setActiveTab] = useState<'learn' | 'build' | 'practice'>('learn')
  const [selectedSemester, setSelectedSemester] = useState('Semester 5-6')

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-900 to-black text-white">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/20 to-purple-600/20" />
        <div className="relative max-w-7xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <GraduationCap className="w-10 h-10 text-blue-400" />
              <span className="text-blue-400 font-semibold text-lg">Campus Edition</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              <span className="bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                BharatBuild AI
              </span>
              <br />
              <span className="text-white text-3xl md:text-4xl">for Engineering Colleges</span>
            </h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto mb-8">
              Learn coding by building real projects. Generate complete applications with documentation.
              Practice for placements with 500+ coding challenges.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link
                href="/bolt"
                className="px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:opacity-90 transition flex items-center gap-2"
              >
                <Sparkles className="w-5 h-5" />
                Start Building
              </Link>
              <Link
                href="/playground"
                className="px-8 py-3 bg-gray-800 border border-gray-700 rounded-lg font-semibold hover:bg-gray-700 transition flex items-center gap-2"
              >
                <Code2 className="w-5 h-5" />
                Practice Coding
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: 'Programming Languages', value: '60+' },
            { label: 'Project Templates', value: '100+' },
            { label: 'Coding Problems', value: '500+' },
            { label: 'Students Helped', value: '10,000+' },
          ].map((stat) => (
            <div key={stat.label} className="bg-gray-800/50 rounded-xl p-6 text-center border border-gray-700">
              <div className="text-3xl font-bold text-blue-400 mb-2">{stat.value}</div>
              <div className="text-gray-400 text-sm">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Three Pillars */}
      <div className="max-w-7xl mx-auto px-4 py-12">
        <h2 className="text-3xl font-bold text-center mb-12">Three Pillars of Learning</h2>

        {/* Tabs */}
        <div className="flex justify-center gap-4 mb-8">
          {[
            { id: 'learn', label: 'Learn', icon: BookOpen, color: 'blue' },
            { id: 'build', label: 'Build', icon: Code2, color: 'purple' },
            { id: 'practice', label: 'Practice', icon: Trophy, color: 'green' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as 'learn' | 'build' | 'practice')}
              className={`px-6 py-3 rounded-lg font-semibold flex items-center gap-2 transition ${
                activeTab === tab.id
                  ? `bg-${tab.color}-500/20 text-${tab.color}-400 border border-${tab.color}-500/50`
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
              style={{
                backgroundColor: activeTab === tab.id ? `rgba(var(--${tab.color}-500), 0.2)` : undefined,
                borderColor: activeTab === tab.id ? `rgba(var(--${tab.color}-500), 0.5)` : undefined,
              }}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-gray-800/50 rounded-2xl border border-gray-700 p-8">
          {activeTab === 'learn' && (
            <div>
              <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <BookOpen className="w-6 h-6 text-blue-400" />
                Learn by Semester
              </h3>

              {/* Semester Selector */}
              <div className="flex flex-wrap gap-2 mb-6">
                {Object.keys(SYLLABUS).map((sem) => (
                  <button
                    key={sem}
                    onClick={() => setSelectedSemester(sem)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                      selectedSemester === sem
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {sem}
                  </button>
                ))}
              </div>

              {/* Topics */}
              <div className="grid md:grid-cols-2 gap-4">
                {SYLLABUS[selectedSemester as keyof typeof SYLLABUS]?.map((subject) => (
                  <div key={subject.name} className="bg-gray-900/50 rounded-xl p-6 border border-gray-700">
                    <h4 className="text-lg font-semibold text-white mb-3">{subject.name}</h4>
                    <div className="flex flex-wrap gap-2">
                      {subject.topics.map((topic) => (
                        <Link
                          key={topic}
                          href={`/bolt?prompt=Explain ${topic} with code examples`}
                          className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm hover:bg-blue-500/30 transition"
                        >
                          {topic}
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'build' && (
            <div>
              <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Code2 className="w-6 h-6 text-purple-400" />
                Project Templates
              </h3>
              <p className="text-gray-400 mb-6">
                Click any project to generate complete source code + SRS + Report + PPT
              </p>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {PROJECT_TEMPLATES.map((project) => (
                  <Link
                    key={project.name}
                    href={`/bolt?prompt=Build a ${project.name} using ${project.tech}. Include user authentication, dashboard, and all CRUD operations.`}
                    className="bg-gray-900/50 rounded-xl p-6 border border-gray-700 hover:border-purple-500/50 transition group"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="text-lg font-semibold text-white group-hover:text-purple-400 transition">
                        {project.name}
                      </h4>
                      <span className={`px-2 py-1 rounded text-xs ${
                        project.difficulty === 'Easy' ? 'bg-green-500/20 text-green-400' :
                        project.difficulty === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {project.difficulty}
                      </span>
                    </div>
                    <p className="text-gray-400 text-sm mb-3">{project.description}</p>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-purple-400">{project.tech}</span>
                      <span className="text-gray-500">Sem {project.semester}</span>
                    </div>
                  </Link>
                ))}
              </div>

              <div className="mt-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
                <h4 className="font-semibold text-purple-400 mb-2 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  What You Get:
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-300">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    Complete Source Code
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    SRS Document
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    Project Report
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    PowerPoint
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'practice' && (
            <div>
              <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
                <Trophy className="w-6 h-6 text-green-400" />
                Placement Preparation
              </h3>
              <p className="text-gray-400 mb-6">
                Practice coding problems like HackerRank. Prepare for TCS, Infosys, Wipro, and more.
              </p>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {PRACTICE_CATEGORIES.map((category) => (
                  <Link
                    key={category.name}
                    href="/playground"
                    className="bg-gray-900/50 rounded-xl p-6 border border-gray-700 hover:border-green-500/50 transition group"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="text-lg font-semibold text-white group-hover:text-green-400 transition">
                        {category.name}
                      </h4>
                      <span className="text-green-400 font-mono">{category.count}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-gray-400">{category.difficulty}</span>
                      <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-green-400 transition" />
                    </div>
                  </Link>
                ))}
              </div>

              <div className="mt-6 grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                  <h4 className="font-semibold text-green-400 mb-2">Company-wise Practice</h4>
                  <div className="flex flex-wrap gap-2">
                    {['TCS', 'Infosys', 'Wipro', 'Cognizant', 'Accenture', 'Google', 'Amazon'].map((company) => (
                      <span key={company} className="px-3 py-1 bg-gray-800 rounded-full text-sm text-gray-300">
                        {company}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                  <h4 className="font-semibold text-blue-400 mb-2">Languages Supported</h4>
                  <div className="flex flex-wrap gap-2">
                    {['C', 'C++', 'Java', 'Python', 'JavaScript', 'SQL'].map((lang) => (
                      <span key={lang} className="px-3 py-1 bg-gray-800 rounded-full text-sm text-gray-300">
                        {lang}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* For Colleges Section */}
      <div className="max-w-7xl mx-auto px-4 py-16">
        <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-2xl border border-gray-700 p-8 md:p-12">
          <div className="flex items-center gap-3 mb-6">
            <Building2 className="w-8 h-8 text-blue-400" />
            <h2 className="text-3xl font-bold">For Colleges & Institutions</h2>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-semibold mb-4">Faculty Benefits</h3>
              <ul className="space-y-3">
                {[
                  'Create and manage assignments',
                  'Auto-grade student submissions',
                  'Track student progress',
                  'Plagiarism detection',
                  'Generate performance reports',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4">Institution Benefits</h3>
              <ul className="space-y-3">
                {[
                  'Improve placement rates',
                  'Modern teaching methodology',
                  'Reduce faculty workload',
                  'Custom branding option',
                  'Dedicated support team',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-2 text-gray-300">
                    <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-8 flex flex-wrap gap-4">
            <a
              href="mailto:contact@bharatbuild.ai"
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold hover:opacity-90 transition"
            >
              Request Campus Demo
            </a>
            <a
              href="/docs/BharatBuild_Campus_Solution.md"
              className="px-6 py-3 bg-gray-800 border border-gray-700 rounded-lg font-semibold hover:bg-gray-700 transition"
            >
              Download Brochure
            </a>
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to Transform Learning?</h2>
        <p className="text-gray-400 mb-8 max-w-2xl mx-auto">
          Join thousands of students who are learning to code by building real projects.
        </p>
        <Link
          href="/bolt"
          className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg font-semibold text-lg hover:opacity-90 transition"
        >
          <Play className="w-5 h-5" />
          Start Building Now - It's Free
        </Link>
      </div>
    </div>
  )
}
