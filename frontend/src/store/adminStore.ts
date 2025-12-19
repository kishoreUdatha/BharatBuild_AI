import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface DashboardStats {
  total_users: number
  active_users: number
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
  total_projects: number
  active_projects: number
  total_revenue: number
  revenue_this_month: number
  total_subscriptions: number
  active_subscriptions: number
  total_tokens_used: number
  tokens_used_today: number
  total_api_calls: number
  api_calls_today: number
}

interface LiveStats {
  total_users: number
  active_users: number
  total_projects: number
  active_subscriptions: number
  today_revenue: number
  timestamp: string
}

interface ActivityItem {
  id: string
  action: string
  target_type: string
  target_id: string | null
  admin_email: string
  admin_name: string | null
  details: any
  created_at: string
}

interface Notification {
  title: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
  timestamp?: string
}

interface UserFilters {
  search: string
  role: string
  is_active: boolean | null
  is_verified: boolean | null
}

interface ProjectFilters {
  search: string
  status: string
  user_id: string
}

interface AdminState {
  // Sidebar
  sidebarCollapsed: boolean
  activeSection: string

  // Dashboard
  dashboardStats: DashboardStats | null
  isLoadingStats: boolean

  // Selection for bulk operations
  selectedUsers: string[]
  selectedProjects: string[]

  // Filters
  userFilters: UserFilters
  projectFilters: ProjectFilters

  // WebSocket
  isConnected: boolean
  lastUpdate: Date | null

  // Live data from WebSocket
  liveStats: LiveStats | null
  recentActivities: ActivityItem[]
  notifications: Notification[]

  // Actions
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setActiveSection: (section: string) => void

  setDashboardStats: (stats: DashboardStats) => void
  setLoadingStats: (loading: boolean) => void

  selectUser: (id: string) => void
  deselectUser: (id: string) => void
  toggleUserSelection: (id: string) => void
  selectAllUsers: (ids: string[]) => void
  clearSelectedUsers: () => void

  selectProject: (id: string) => void
  deselectProject: (id: string) => void
  clearSelectedProjects: () => void

  setUserFilters: (filters: Partial<UserFilters>) => void
  resetUserFilters: () => void
  setProjectFilters: (filters: Partial<ProjectFilters>) => void
  resetProjectFilters: () => void

  setConnected: (connected: boolean) => void
  setLastUpdate: (date: Date) => void

  // Live data actions
  setLiveStats: (stats: LiveStats) => void
  addActivity: (activity: ActivityItem) => void
  setActivities: (activities: ActivityItem[]) => void
  addNotification: (notification: Notification) => void
  clearNotifications: () => void
}

const defaultUserFilters: UserFilters = {
  search: '',
  role: '',
  is_active: null,
  is_verified: null,
}

const defaultProjectFilters: ProjectFilters = {
  search: '',
  status: '',
  user_id: '',
}

export const useAdminStore = create<AdminState>()(
  persist(
    (set) => ({
      // Initial state
      sidebarCollapsed: false,
      activeSection: 'dashboard',
      dashboardStats: null,
      isLoadingStats: false,
      selectedUsers: [],
      selectedProjects: [],
      userFilters: defaultUserFilters,
      projectFilters: defaultProjectFilters,
      isConnected: false,
      lastUpdate: null,
      liveStats: null,
      recentActivities: [],
      notifications: [],

      // Sidebar actions
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setActiveSection: (section) => set({ activeSection: section }),

      // Dashboard actions
      setDashboardStats: (stats) => set({ dashboardStats: stats, isLoadingStats: false }),
      setLoadingStats: (loading) => set({ isLoadingStats: loading }),

      // User selection actions
      selectUser: (id) => set((state) => ({
        selectedUsers: state.selectedUsers.includes(id)
          ? state.selectedUsers
          : [...state.selectedUsers, id]
      })),
      deselectUser: (id) => set((state) => ({
        selectedUsers: state.selectedUsers.filter((uid) => uid !== id)
      })),
      toggleUserSelection: (id) => set((state) => ({
        selectedUsers: state.selectedUsers.includes(id)
          ? state.selectedUsers.filter((uid) => uid !== id)
          : [...state.selectedUsers, id]
      })),
      selectAllUsers: (ids) => set({ selectedUsers: ids }),
      clearSelectedUsers: () => set({ selectedUsers: [] }),

      // Project selection actions
      selectProject: (id) => set((state) => ({
        selectedProjects: state.selectedProjects.includes(id)
          ? state.selectedProjects
          : [...state.selectedProjects, id]
      })),
      deselectProject: (id) => set((state) => ({
        selectedProjects: state.selectedProjects.filter((pid) => pid !== id)
      })),
      clearSelectedProjects: () => set({ selectedProjects: [] }),

      // Filter actions
      setUserFilters: (filters) => set((state) => ({
        userFilters: { ...state.userFilters, ...filters }
      })),
      resetUserFilters: () => set({ userFilters: defaultUserFilters }),
      setProjectFilters: (filters) => set((state) => ({
        projectFilters: { ...state.projectFilters, ...filters }
      })),
      resetProjectFilters: () => set({ projectFilters: defaultProjectFilters }),

      // WebSocket actions
      setConnected: (connected) => set({ isConnected: connected }),
      setLastUpdate: (date) => set({ lastUpdate: date }),

      // Live data actions
      setLiveStats: (stats) => set({ liveStats: stats, lastUpdate: new Date() }),
      addActivity: (activity) => set((state) => ({
        recentActivities: [activity, ...state.recentActivities.filter(a => a.id !== activity.id)].slice(0, 50)
      })),
      setActivities: (activities) => set({ recentActivities: activities }),
      addNotification: (notification) => set((state) => ({
        notifications: [{ ...notification, timestamp: new Date().toISOString() }, ...state.notifications].slice(0, 100)
      })),
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'admin-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        userFilters: state.userFilters,
        projectFilters: state.projectFilters,
      }),
    }
  )
)
