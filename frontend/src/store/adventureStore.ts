'use client'

import { create } from 'zustand'

// Types
export type ProjectTheme = 'ai_ml' | 'web_dev' | 'mobile_app' | 'cloud' | 'iot' | 'cyber_security' | 'blockchain' | 'data_science'
export type Difficulty = 'beginner' | 'intermediate' | 'expert'
export type UIPersonality = 'elegant_simple' | 'dark_developer' | 'soft_fairy' | 'robotic_tech' | 'colorful_student' | 'minimal_clean' | 'glassmorphism'

export interface ThemeConfig {
  id: ProjectTheme
  icon: string
  name: string
  description: string
  suggestedFeatures: string[]
}

export interface DifficultyConfig {
  id: Difficulty
  icon: string
  name: string
  description: string
  fileCount: string
  complexity: string
  estimatedTime: string
}

export interface PersonalityConfig {
  id: UIPersonality
  icon: string
  name: string
  colors: { primary: string; bg: string; text: string }
  style: string
}

export interface Feature {
  id: string
  name: string
  icon: string
  category: string
  difficulty: Difficulty
}

export interface SmartQuestion {
  id: string
  question: string
  type: 'text' | 'choice' | 'multi_choice'
  options?: { value: string | boolean; label: string; icon: string; description?: string }[]
  placeholder?: string
  required: boolean
}

export interface CollegeInfo {
  studentName: string
  rollNumber: string
  collegeName: string
  department: string
  guideName: string
  hodName?: string
  principalName?: string
  academicYear: string
  teamMembers?: { name: string; roll: string }[]
}

export interface Achievement {
  id: string
  icon: string
  title: string
  description: string
  unlocked: boolean
}

export interface BuildPhase {
  id: string
  name: string
  messages: string[]
  status: 'pending' | 'in_progress' | 'complete'
  progress: number
}

export interface AdventureState {
  // Session
  sessionId: string | null
  currentStage: number

  // Stage 1: Theme & Difficulty
  selectedTheme: ProjectTheme | null
  selectedDifficulty: Difficulty | null

  // Stage 2: Smart Questions
  answers: Record<string, any>
  isCollegeProject: boolean

  // Stage 3: Features & Personality
  selectedFeatures: string[]
  selectedPersonality: UIPersonality | null
  projectName: string

  // Stage 4: College Info
  collegeInfo: CollegeInfo | null

  // Build Phase
  buildPhases: BuildPhase[]
  currentBuildPhase: string | null
  currentBuildMessage: string

  // Achievements
  achievements: Achievement[]

  // UI State
  isBuilding: boolean
  isComplete: boolean
  showCelebration: boolean
}

export interface AdventureActions {
  // Session
  startAdventure: () => void
  resetAdventure: () => void

  // Stage Navigation
  setStage: (stage: number) => void
  nextStage: () => void
  previousStage: () => void

  // Stage 1
  setTheme: (theme: ProjectTheme) => void
  setDifficulty: (difficulty: Difficulty) => void

  // Stage 2
  setAnswer: (questionId: string, value: any) => void
  setIsCollegeProject: (isCollege: boolean) => void

  // Stage 3
  toggleFeature: (featureId: string) => void
  setSelectedFeatures: (features: string[]) => void
  setPersonality: (personality: UIPersonality) => void
  setProjectName: (name: string) => void

  // Stage 4
  setCollegeInfo: (info: CollegeInfo) => void

  // Build Phase
  startBuild: () => void
  updateBuildPhase: (phaseId: string, status: BuildPhase['status'], progress: number) => void
  setBuildMessage: (message: string) => void
  completeBuild: () => void

  // Achievements
  unlockAchievement: (achievementId: string) => void

  // UI
  setShowCelebration: (show: boolean) => void
}

// Theme configurations
export const THEMES: ThemeConfig[] = [
  { id: 'ai_ml', icon: '🤖', name: 'AI / Machine Learning', description: 'Build intelligent systems that learn and predict', suggestedFeatures: ['ML Model', 'Data Visualization', 'Prediction API'] },
  { id: 'web_dev', icon: '🌐', name: 'Web Development', description: 'Create stunning web applications', suggestedFeatures: ['Authentication', 'Dashboard', 'REST API'] },
  { id: 'mobile_app', icon: '📱', name: 'Mobile Application', description: 'Build apps for iOS and Android', suggestedFeatures: ['Push Notifications', 'Offline Mode', 'Camera'] },
  { id: 'cloud', icon: '☁️', name: 'Cloud Computing', description: 'Harness the power of cloud infrastructure', suggestedFeatures: ['Auto Scaling', 'Serverless', 'Containers'] },
  { id: 'iot', icon: '🔌', name: 'Internet of Things', description: 'Connect devices and sensors', suggestedFeatures: ['Sensor Dashboard', 'Real-time Monitoring', 'Alerts'] },
  { id: 'cyber_security', icon: '🔐', name: 'Cyber Security', description: 'Protect systems and data', suggestedFeatures: ['Vulnerability Scanner', 'Log Analysis', 'Threat Detection'] },
  { id: 'blockchain', icon: '⛓️', name: 'Blockchain', description: 'Build decentralized applications', suggestedFeatures: ['Smart Contracts', 'Wallet Integration', 'Token System'] },
  { id: 'data_science', icon: '📊', name: 'Data Science', description: 'Analyze and visualize data', suggestedFeatures: ['Data Pipeline', 'Interactive Charts', 'Report Generation'] },
]

// Difficulty configurations
export const DIFFICULTIES: DifficultyConfig[] = [
  { id: 'beginner', icon: '🌱', name: 'Beginner', description: 'Simple project with basic features', fileCount: '8-12 files', complexity: 'Basic CRUD operations', estimatedTime: '2-3 days learning' },
  { id: 'intermediate', icon: '🌿', name: 'Intermediate', description: 'Moderate complexity with advanced features', fileCount: '15-25 files', complexity: 'Authentication, APIs, Database relations', estimatedTime: '1-2 weeks' },
  { id: 'expert', icon: '🌳', name: 'Expert', description: 'Production-ready with enterprise features', fileCount: '30-50 files', complexity: 'Microservices, Caching, Testing, CI/CD', estimatedTime: '3-4 weeks' },
]

// Personality configurations
export const PERSONALITIES: PersonalityConfig[] = [
  { id: 'elegant_simple', icon: '🌈', name: 'Elegant & Simple', colors: { primary: '#6366f1', bg: '#ffffff', text: '#1f2937' }, style: 'Clean, minimalist, lots of whitespace' },
  { id: 'dark_developer', icon: '🔥', name: 'Dark Mode Developer', colors: { primary: '#22d3ee', bg: '#0f172a', text: '#e2e8f0' }, style: 'Dark theme, neon accents, developer-focused' },
  { id: 'soft_fairy', icon: '🧚', name: 'Soft Fairy Theme', colors: { primary: '#ec4899', bg: '#fdf2f8', text: '#831843' }, style: 'Soft pastels, rounded corners, playful' },
  { id: 'robotic_tech', icon: '🦾', name: 'Robotic Tech UI', colors: { primary: '#10b981', bg: '#111827', text: '#d1fae5' }, style: 'Futuristic, grid-based, tech-inspired' },
  { id: 'colorful_student', icon: '🎨', name: 'Colorful Student', colors: { primary: '#f59e0b', bg: '#fffbeb', text: '#78350f' }, style: 'Vibrant colors, fun gradients, engaging' },
  { id: 'minimal_clean', icon: '⬜', name: 'Minimal Clean', colors: { primary: '#000000', bg: '#ffffff', text: '#000000' }, style: 'Black and white, typography-focused' },
  { id: 'glassmorphism', icon: '💎', name: 'Glassmorphism', colors: { primary: '#8b5cf6', bg: '#1e1b4b', text: '#e0e7ff' }, style: 'Glass effects, blur, transparency' },
]

// Feature configurations
export const FEATURES: Feature[] = [
  // Authentication
  { id: 'email_login', name: 'Email/Password Login', icon: '🔐', category: 'authentication', difficulty: 'beginner' },
  { id: 'oauth', name: 'Google/GitHub OAuth', icon: '🔐', category: 'authentication', difficulty: 'intermediate' },
  { id: 'otp', name: 'OTP Verification', icon: '🔐', category: 'authentication', difficulty: 'intermediate' },
  { id: '2fa', name: 'Two-Factor Auth', icon: '🔐', category: 'authentication', difficulty: 'expert' },
  // UI Features
  { id: 'dark_mode', name: 'Dark Mode Toggle', icon: '🎨', category: 'ui', difficulty: 'beginner' },
  { id: 'responsive', name: 'Mobile Responsive', icon: '🎨', category: 'ui', difficulty: 'beginner' },
  { id: 'animations', name: 'Smooth Animations', icon: '🎨', category: 'ui', difficulty: 'intermediate' },
  { id: 'themes', name: 'Multiple Themes', icon: '🎨', category: 'ui', difficulty: 'intermediate' },
  // Data Features
  { id: 'crud', name: 'CRUD Operations', icon: '📊', category: 'data', difficulty: 'beginner' },
  { id: 'search', name: 'Search & Filter', icon: '📊', category: 'data', difficulty: 'beginner' },
  { id: 'pagination', name: 'Pagination', icon: '📊', category: 'data', difficulty: 'beginner' },
  { id: 'export', name: 'Export to CSV/PDF', icon: '📊', category: 'data', difficulty: 'intermediate' },
  { id: 'charts', name: 'Interactive Charts', icon: '📊', category: 'data', difficulty: 'intermediate' },
  { id: 'realtime', name: 'Real-time Updates', icon: '📊', category: 'data', difficulty: 'expert' },
  // AI Features
  { id: 'chatbot', name: 'AI Chatbot', icon: '🤖', category: 'ai', difficulty: 'intermediate' },
  { id: 'recommendations', name: 'Smart Recommendations', icon: '🤖', category: 'ai', difficulty: 'intermediate' },
  { id: 'image_recognition', name: 'Image Recognition', icon: '🤖', category: 'ai', difficulty: 'expert' },
  // Communication
  { id: 'notifications', name: 'Push Notifications', icon: '💬', category: 'communication', difficulty: 'intermediate' },
  { id: 'email_notif', name: 'Email Integration', icon: '💬', category: 'communication', difficulty: 'intermediate' },
  { id: 'chat', name: 'Real-time Chat', icon: '💬', category: 'communication', difficulty: 'expert' },
]

// Smart Questions
export const SMART_QUESTIONS: SmartQuestion[] = [
  { id: 'purpose', question: 'What should your project do? 🎯', type: 'text', placeholder: 'e.g., Help students manage their tasks and deadlines', required: true },
  { id: 'is_college', question: 'Is this for college/university? 🎓', type: 'choice', options: [{ value: true, label: 'Yes, it\'s a college project', icon: '🎓' }, { value: false, label: 'No, personal/commercial', icon: '💼' }], required: true },
  { id: 'platform', question: 'Where will it run? 💻', type: 'choice', options: [{ value: 'web', label: 'Web Browser', icon: '🌐' }, { value: 'mobile', label: 'Mobile App', icon: '📱' }, { value: 'desktop', label: 'Desktop App', icon: '🖥️' }, { value: 'all', label: 'All Platforms', icon: '🚀' }], required: true },
  { id: 'users', question: 'Who will use it? 👥', type: 'multi_choice', options: [{ value: 'students', label: 'Students', icon: '👨‍🎓' }, { value: 'teachers', label: 'Teachers', icon: '👨‍🏫' }, { value: 'admins', label: 'Admins', icon: '👨‍💼' }, { value: 'public', label: 'General Public', icon: '👥' }, { value: 'businesses', label: 'Businesses', icon: '🏢' }], required: true },
  { id: 'ui_style', question: 'Pick your UI vibe! 🎨', type: 'choice', options: [{ value: 'modern', label: 'Modern & Sleek', icon: '✨' }, { value: 'playful', label: 'Fun & Colorful', icon: '🎨' }, { value: 'professional', label: 'Professional & Clean', icon: '💼' }, { value: 'dark', label: 'Dark Mode', icon: '🌙' }], required: true },
]

// Initial achievements
const INITIAL_ACHIEVEMENTS: Achievement[] = [
  { id: 'first_choice', icon: '🎯', title: 'Decision Maker', description: 'Made your first choice!', unlocked: false },
  { id: 'theme_selected', icon: '🎨', title: 'Style Guru', description: 'Selected a project theme!', unlocked: false },
  { id: 'features_selected', icon: '⚡', title: 'Feature Hunter', description: 'Picked awesome features!', unlocked: false },
  { id: 'halfway', icon: '🌟', title: 'Halfway Hero', description: '50% complete!', unlocked: false },
  { id: 'backend_done', icon: '⚙️', title: 'Backend Boss', description: 'Backend is ready!', unlocked: false },
  { id: 'frontend_done', icon: '🎨', title: 'UI Master', description: 'Frontend looks amazing!', unlocked: false },
  { id: 'docs_done', icon: '📚', title: 'Documentation Pro', description: '72 pages generated!', unlocked: false },
  { id: 'project_complete', icon: '🏆', title: 'Project Champion', description: 'Your project is complete!', unlocked: false },
  { id: 'speed_demon', icon: '⚡', title: 'Speed Demon', description: 'Completed in record time!', unlocked: false },
  { id: 'feature_rich', icon: '💎', title: 'Feature King', description: 'Added 10+ features!', unlocked: false },
]

// Initial build phases
const INITIAL_BUILD_PHASES: BuildPhase[] = [
  { id: 'planning', name: 'Planning', messages: ['🧠 Analyzing your vision...', '📋 Creating the master plan...', '✨ Sprinkling magic dust...'], status: 'pending', progress: 0 },
  { id: 'backend', name: 'Backend', messages: ['⚙️ Forging backend engines...', '🔧 Crafting API endpoints...', '🗄️ Summoning database tables...'], status: 'pending', progress: 0 },
  { id: 'frontend', name: 'Frontend', messages: ['🎨 Painting beautiful interfaces...', '📱 Making it mobile-friendly...', '🌈 Applying your chosen style...'], status: 'pending', progress: 0 },
  { id: 'features', name: 'Features', messages: ['🚀 Activating superpowers...', '💫 Installing cool features...', '⚡ Charging up modules...'], status: 'pending', progress: 0 },
  { id: 'testing', name: 'Testing', messages: ['🧪 Running quality checks...', '🔍 Hunting for bugs...', '✅ Verifying everything works...'], status: 'pending', progress: 0 },
  { id: 'docs', name: 'Documentation', messages: ['📚 Writing documentation...', '📄 Generating IEEE reports...', '📊 Creating UML diagrams...'], status: 'pending', progress: 0 },
]

// Create the store
export const useAdventureStore = create<AdventureState & AdventureActions>((set, get) => ({
  // Initial State
  sessionId: null,
  currentStage: 1,
  selectedTheme: null,
  selectedDifficulty: null,
  answers: {},
  isCollegeProject: true,
  selectedFeatures: [],
  selectedPersonality: null,
  projectName: '',
  collegeInfo: null,
  buildPhases: INITIAL_BUILD_PHASES,
  currentBuildPhase: null,
  currentBuildMessage: '',
  achievements: INITIAL_ACHIEVEMENTS,
  isBuilding: false,
  isComplete: false,
  showCelebration: false,

  // Actions
  startAdventure: () => {
    const sessionId = `adventure-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    set({
      sessionId,
      currentStage: 1,
      selectedTheme: null,
      selectedDifficulty: null,
      answers: {},
      isCollegeProject: true,
      selectedFeatures: [],
      selectedPersonality: null,
      projectName: '',
      collegeInfo: null,
      buildPhases: INITIAL_BUILD_PHASES.map(p => ({ ...p, status: 'pending' as const, progress: 0 })),
      currentBuildPhase: null,
      currentBuildMessage: '',
      achievements: INITIAL_ACHIEVEMENTS.map(a => ({ ...a, unlocked: false })),
      isBuilding: false,
      isComplete: false,
      showCelebration: false,
    })
  },

  resetAdventure: () => {
    set({
      sessionId: null,
      currentStage: 1,
      selectedTheme: null,
      selectedDifficulty: null,
      answers: {},
      isCollegeProject: true,
      selectedFeatures: [],
      selectedPersonality: null,
      projectName: '',
      collegeInfo: null,
      buildPhases: INITIAL_BUILD_PHASES.map(p => ({ ...p, status: 'pending' as const, progress: 0 })),
      currentBuildPhase: null,
      currentBuildMessage: '',
      achievements: INITIAL_ACHIEVEMENTS.map(a => ({ ...a, unlocked: false })),
      isBuilding: false,
      isComplete: false,
      showCelebration: false,
    })
  },

  setStage: (stage) => set({ currentStage: stage }),

  nextStage: () => set((state) => ({ currentStage: state.currentStage + 1 })),

  previousStage: () => set((state) => ({ currentStage: Math.max(1, state.currentStage - 1) })),

  setTheme: (theme) => {
    set({ selectedTheme: theme })
    get().unlockAchievement('first_choice')
    get().unlockAchievement('theme_selected')
  },

  setDifficulty: (difficulty) => set({ selectedDifficulty: difficulty }),

  setAnswer: (questionId, value) => set((state) => ({
    answers: { ...state.answers, [questionId]: value }
  })),

  setIsCollegeProject: (isCollege) => set({ isCollegeProject: isCollege }),

  toggleFeature: (featureId) => set((state) => {
    const features = state.selectedFeatures.includes(featureId)
      ? state.selectedFeatures.filter(f => f !== featureId)
      : [...state.selectedFeatures, featureId]

    // Check achievements
    if (features.length >= 5) {
      get().unlockAchievement('features_selected')
    }
    if (features.length >= 10) {
      get().unlockAchievement('feature_rich')
    }

    return { selectedFeatures: features }
  }),

  setSelectedFeatures: (features) => set({ selectedFeatures: features }),

  setPersonality: (personality) => set({ selectedPersonality: personality }),

  setProjectName: (name) => set({ projectName: name }),

  setCollegeInfo: (info) => set({ collegeInfo: info }),

  startBuild: () => set({ isBuilding: true, currentBuildPhase: 'planning' }),

  updateBuildPhase: (phaseId, status, progress) => set((state) => ({
    buildPhases: state.buildPhases.map(p =>
      p.id === phaseId ? { ...p, status, progress } : p
    ),
    currentBuildPhase: phaseId,
  })),

  setBuildMessage: (message) => set({ currentBuildMessage: message }),

  completeBuild: () => {
    set({ isBuilding: false, isComplete: true })
    get().unlockAchievement('project_complete')
  },

  unlockAchievement: (achievementId) => set((state) => ({
    achievements: state.achievements.map(a =>
      a.id === achievementId ? { ...a, unlocked: true } : a
    )
  })),

  setShowCelebration: (show) => set({ showCelebration: show }),
}))

// Surprise Projects
export const SURPRISE_PROJECTS = [
  { name: 'StudyBuddy AI', icon: '🤖', description: 'AI-powered study companion with flashcards, quizzes, and progress tracking', theme: 'ai_ml' as ProjectTheme, features: ['chatbot', 'charts', 'dark_mode'], difficulty: 'intermediate' as Difficulty },
  { name: 'CampusConnect', icon: '🌐', description: 'Social platform for students to find study groups and share notes', theme: 'web_dev' as ProjectTheme, features: ['oauth', 'chat', 'notifications'], difficulty: 'intermediate' as Difficulty },
  { name: 'HealthMate', icon: '📱', description: 'Personal health tracker with medication reminders and fitness goals', theme: 'mobile_app' as ProjectTheme, features: ['notifications', 'charts', 'export'], difficulty: 'intermediate' as Difficulty },
  { name: 'SmartAttendance', icon: '🤖', description: 'Face recognition-based attendance system with analytics dashboard', theme: 'ai_ml' as ProjectTheme, features: ['image_recognition', 'charts', 'export'], difficulty: 'expert' as Difficulty },
  { name: 'BudgetWise', icon: '💰', description: 'Personal finance manager with expense tracking and insights', theme: 'web_dev' as ProjectTheme, features: ['charts', 'export', 'dark_mode'], difficulty: 'beginner' as Difficulty },
  { name: 'EventHub', icon: '🎉', description: 'College event management platform for organizing campus events', theme: 'web_dev' as ProjectTheme, features: ['email_notif', 'search', 'responsive'], difficulty: 'intermediate' as Difficulty },
  { name: 'CodeReview AI', icon: '🤖', description: 'AI-powered code review tool that analyzes quality and suggests fixes', theme: 'ai_ml' as ProjectTheme, features: ['chatbot', 'recommendations', 'dark_mode'], difficulty: 'expert' as Difficulty },
  { name: 'PlantCare IoT', icon: '🔌', description: 'Smart plant monitoring with soil sensors and automated watering', theme: 'iot' as ProjectTheme, features: ['realtime', 'charts', 'notifications'], difficulty: 'intermediate' as Difficulty },
]
