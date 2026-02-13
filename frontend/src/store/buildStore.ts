import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export type BuildPlatform = 'android' | 'ios'

export type BuildStatus =
  | 'pending'
  | 'configuring'
  | 'queued'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface Build {
  id: string
  project_id: string
  platform: BuildPlatform
  status: BuildStatus
  progress: number
  phase?: string
  eas_build_id?: string
  artifact_url?: string
  artifact_filename?: string
  artifact_size_mb?: number
  error_message?: string
  started_at?: string
  completed_at?: string
  created_at?: string
}

export interface BuildQuota {
  builds_this_month: number
  builds_limit: number
  builds_remaining: number
  can_build: boolean
  plan_type: string
}

export interface BuildHistory {
  builds: Build[]
  total: number
}

interface BuildState {
  // Current build being tracked
  currentBuild: Build | null

  // Build history for the current project
  buildHistory: BuildHistory | null

  // UI state
  isBuilding: boolean
  error: string | null

  // Quota information
  quota: BuildQuota | null

  // Actions
  setCurrentBuild: (build: Build | null) => void
  updateCurrentBuild: (updates: Partial<Build>) => void
  setIsBuilding: (isBuilding: boolean) => void
  setError: (error: string | null) => void
  setQuota: (quota: BuildQuota | null) => void
  setBuildHistory: (history: BuildHistory | null) => void
  addToBuildHistory: (build: Build) => void
  clearBuild: () => void
  reset: () => void
}

const initialState = {
  currentBuild: null,
  buildHistory: null,
  isBuilding: false,
  error: null,
  quota: null,
}

export const useBuildStore = create<BuildState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setCurrentBuild: (build) => set({ currentBuild: build }),

      updateCurrentBuild: (updates) => {
        const current = get().currentBuild
        if (current) {
          set({ currentBuild: { ...current, ...updates } })
        }
      },

      setIsBuilding: (isBuilding) => set({ isBuilding }),

      setError: (error) => set({ error }),

      setQuota: (quota) => set({ quota }),

      setBuildHistory: (history) => set({ buildHistory: history }),

      addToBuildHistory: (build) => {
        const current = get().buildHistory
        if (current) {
          set({
            buildHistory: {
              builds: [build, ...current.builds],
              total: current.total + 1,
            },
          })
        } else {
          set({
            buildHistory: {
              builds: [build],
              total: 1,
            },
          })
        }
      },

      clearBuild: () => {
        set({
          currentBuild: null,
          isBuilding: false,
          error: null,
        })
      },

      reset: () => set(initialState),
    }),
    {
      name: 'bharatbuild-build-store',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        currentBuild: state.currentBuild,
        quota: state.quota,
      }),
    }
  )
)
