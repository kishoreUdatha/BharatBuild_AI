import axios, { AxiosInstance } from 'axios'
import { setAccessToken, removeAccessToken } from './auth-utils'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

/**
 * Extended API Client with all BharatBuild methods
 */
class ApiClient {
  private axiosInstance: AxiosInstance

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 180000, // 3 minutes - SDK Fixer Agent needs more time for complex fixes
    })

    // Add auth token to requests
    this.axiosInstance.interceptors.request.use(
      (config) => {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Handle response errors
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          if (typeof window !== 'undefined') {
            // Don't redirect if already on login page
            if (window.location.pathname === '/login') {
              return Promise.reject(error)
            }

            // Try to refresh token first before logging out
            const refreshToken = localStorage.getItem('refresh_token')
            if (refreshToken && !error.config._retry) {
              error.config._retry = true
              try {
                const response = await axios.post(
                  `${API_BASE_URL}/auth/refresh`,
                  { refresh_token: refreshToken },
                  { headers: { 'Content-Type': 'application/json' } }
                )
                if (response.data?.access_token) {
                  // Update token in both localStorage and cookie
                  setAccessToken(response.data.access_token)
                  // Retry the original request with new token
                  error.config.headers.Authorization = `Bearer ${response.data.access_token}`
                  return this.axiosInstance.request(error.config)
                }
              } catch (refreshError) {
                // Refresh failed, just reject - let pages handle gracefully
                console.log('Token refresh failed')
              }
            }

            // Don't auto-redirect to login - let pages handle 401 gracefully
            // Pages can show mock data or handle auth errors as needed
            // Only clear tokens if refresh failed
            if (error.config._retry) {
              removeAccessToken()
              localStorage.removeItem('refresh_token')
            }
          }
        }

        // Handle feature restriction errors (403 with feature_not_available)
        if (error.response?.status === 403) {
          const detail = error.response?.data?.detail
          if (detail?.error === 'feature_not_available' && typeof window !== 'undefined') {
            // Emit custom event for UpgradeContext to catch
            const event = new CustomEvent('feature-restricted', {
              detail: {
                feature: detail.feature,
                currentPlan: detail.current_plan,
                upgradeTo: detail.upgrade_to,
                message: detail.message
              }
            })
            window.dispatchEvent(event)
          }
        }

        return Promise.reject(error)
      }
    )
  }

  // ==================== Auth ====================
  async login(email: string, password: string) {
    const response = await this.axiosInstance.post('/auth/login', { email, password })
    return response.data
  }

  async register(data: {
    email: string;
    password: string;
    full_name: string;
    role?: string;
    phone?: string;
    // Student Academic Details
    roll_number?: string;
    college_name?: string;
    university_name?: string;
    department?: string;
    course?: string;
    year_semester?: string;
    batch?: string;
    // Guide Details
    guide_name?: string;
    guide_designation?: string;
    hod_name?: string;
    // Legacy fields
    college?: string;
    year_of_study?: string;
    faculty_id?: string;
    designation?: string;
  }) {
    const response = await this.axiosInstance.post('/auth/register', data)
    return response.data
  }

  async logout() {
    const response = await this.axiosInstance.post('/auth/logout')
    return response.data
  }

  async getMe() {
    const response = await this.axiosInstance.get('/auth/me')
    return response.data
  }

  async initiateOAuth(provider: 'google' | 'github', role?: string) {
    const response = await this.axiosInstance.get(`/auth/${provider}/authorize`, {
      params: { role }
    })
    if (response.data?.authorization_url) {
      window.location.href = response.data.authorization_url
    }
    return response.data
  }

  async googleCallback(code: string, role?: string) {
    const response = await this.axiosInstance.post('/auth/google/callback', { code, role })
    return response.data
  }

  async githubCallback(code: string, role?: string) {
    const response = await this.axiosInstance.post('/auth/github/callback', { code, role })
    return response.data
  }

  // ==================== Health ====================
  async healthCheck() {
    try {
      const response = await this.axiosInstance.get('/health', { baseURL: API_BASE_URL.replace('/api/v1', '') })
      return response.data?.status === 'healthy'
    } catch {
      return false
    }
  }

  // ==================== Projects ====================
  async getProjects(params?: { page?: number; limit?: number }) {
    // Backend expects page_size, not limit
    const queryParams = params ? { page: params.page, page_size: params.limit } : undefined
    const response = await this.axiosInstance.get('/projects', { params: queryParams })
    return response.data
  }

  async getProject(id: string) {
    const response = await this.axiosInstance.get(`/projects/${id}`)
    return response.data
  }

  async createProject(data: {
    name?: string;
    title?: string;
    description?: string;
    type?: string;
    prompt?: string;
    mode?: string;
    tech_stack?: string;
    features?: string[];
  }) {
    const response = await this.axiosInstance.post('/projects', data)
    return response.data
  }

  async updateProject(id: string, data: Partial<{ name: string; description: string }>) {
    const response = await this.axiosInstance.patch(`/projects/${id}`, data)
    return response.data
  }

  async deleteProject(id: string) {
    const response = await this.axiosInstance.delete(`/projects/${id}`)
    return response.data
  }

  async executeProject(id: string) {
    const response = await this.axiosInstance.post(`/execution/${id}/start`)
    return response.data
  }

  async getProjectStatus(id: string) {
    const response = await this.axiosInstance.get(`/execution/${id}/status`)
    return response.data
  }

  async getProjectFiles(id: string) {
    const response = await this.axiosInstance.get(`/projects/${id}/files`)
    return response.data
  }

  async getFileContent(projectId: string, filePath: string) {
    const response = await this.axiosInstance.get(`/projects/${projectId}/files/${encodeURIComponent(filePath)}`)
    return response.data
  }

  async loadProjectWithFiles(projectId: string) {
    // Uses the /load endpoint which returns project + all files with content
    const response = await this.axiosInstance.get(`/projects/${projectId}/load`)
    return response.data
  }

  async saveFile(projectId: string, file: { path: string; content: string }) {
    const response = await this.axiosInstance.post('/sync/file', {
      project_id: projectId,
      path: file.path,
      content: file.content,
    })
    return response.data
  }

  async saveFilesBulk(projectId: string, files: Array<{ path: string; content: string }>) {
    const response = await this.axiosInstance.post(`/sync/files/${projectId}`, { files })
    return response.data
  }

  // ==================== Documents ====================
  async downloadDocument(projectId: string, docType: string) {
    const response = await this.axiosInstance.get(`/documents/${projectId}/${docType}`, {
      responseType: 'blob'
    })
    return response.data
  }

  // ==================== Plan Status ====================
  async getPlanStatus() {
    const response = await this.axiosInstance.get('/billing/status')
    return response.data
  }

  // ==================== Tokens ====================
  async getTokenBalance() {
    const response = await this.axiosInstance.get('/tokens/balance')
    return response.data
  }

  async getTokenPackages() {
    const response = await this.axiosInstance.get('/tokens/packages')
    return response.data
  }

  async purchaseTokens(packageId: string) {
    const response = await this.axiosInstance.post('/tokens/purchase', { package_id: packageId })
    return response.data
  }

  async redeemPromoCode(code: string) {
    const response = await this.axiosInstance.post('/tokens/redeem', { code })
    return response.data
  }

  async getTokenAnalytics() {
    const response = await this.axiosInstance.get('/tokens/analytics')
    return response.data
  }

  async getTokenHistory(params?: { page?: number; limit?: number }) {
    const response = await this.axiosInstance.get('/tokens/history', { params })
    return response.data
  }

  // ==================== Orchestrator ====================
  /**
   * Cancel an ongoing project generation
   * Stops file generation on the backend and frees up resources
   */
  async cancelGeneration(projectId: string) {
    const response = await this.axiosInstance.post('/orchestrator/cancel', { project_id: projectId })
    return response.data
  }

  /**
   * Get project generation status (for polling when SSE disconnects)
   */
  async getGenerationStatus(projectId: string) {
    const response = await this.axiosInstance.get(`/orchestrator/project/${projectId}/status`)
    return response.data
  }

  /**
   * Get detailed generation progress with file statuses
   */
  async getGenerationProgress(projectId: string) {
    const response = await this.axiosInstance.get(`/orchestrator/project/${projectId}/progress`)
    return response.data
  }

  /**
   * Resume an interrupted project generation
   */
  async resumeGeneration(projectId: string, continueMessage?: string) {
    const response = await this.axiosInstance.post('/orchestrator/resume', {
      project_id: projectId,
      continue_message: continueMessage || 'Continue generating the remaining files'
    })
    return response.data
  }

  // ==================== APK Downloads (Flutter/Mobile) ====================

  /**
   * Get APK availability info for a project
   * Returns whether APK is available and download URL
   */
  async getApkInfo(projectId: string) {
    const response = await this.axiosInstance.get(`/projects/${projectId}/download/apk/info`)
    return response.data
  }

  /**
   * Get APK info for a session-based project (ephemeral storage)
   */
  async getSessionApkInfo(sessionId: string) {
    const response = await this.axiosInstance.get(`/download/session/${sessionId}/apk/info`)
    return response.data
  }

  /**
   * Download APK file for a project
   * Returns blob for download
   */
  async downloadApk(projectId: string, buildType: 'release' | 'debug' = 'release') {
    const response = await this.axiosInstance.get(`/projects/${projectId}/download/apk`, {
      params: { build_type: buildType },
      responseType: 'blob'
    })
    return response.data
  }

  /**
   * Download APK file for a session-based project
   */
  async downloadSessionApk(sessionId: string, buildType: 'release' | 'debug' = 'release') {
    const response = await this.axiosInstance.get(`/download/session/${sessionId}/apk`, {
      params: { build_type: buildType },
      responseType: 'blob'
    })
    return response.data
  }

  /**
   * Trigger APK build for a Flutter project
   */
  async triggerApkBuild(sessionId: string, buildType: 'release' | 'debug' = 'debug') {
    const response = await this.axiosInstance.post(`/download/session/${sessionId}/build-apk`, null, {
      params: { build_type: buildType }
    })
    return response.data
  }

  // ==================== Generic request methods ====================
  async get<T = any>(url: string, config?: any): Promise<T> {
    const response = await this.axiosInstance.get(url, config)
    return response.data
  }

  async post<T = any>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.axiosInstance.post(url, data, config)
    return response.data
  }

  async put<T = any>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.axiosInstance.put(url, data, config)
    return response.data
  }

  async patch<T = any>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.axiosInstance.patch(url, data, config)
    return response.data
  }

  async delete<T = any>(url: string, config?: any): Promise<T> {
    const response = await this.axiosInstance.delete(url, config)
    return response.data
  }

  // ==================== Lab Management (Faculty) ====================

  // Get faculty's labs
  async getFacultyLabs() {
    const response = await this.axiosInstance.get('/faculty/labs')
    return response.data
  }

  // Get lab details
  async getLab(labId: string) {
    const response = await this.axiosInstance.get(`/lab/labs/${labId}`)
    return response.data
  }

  // Get lab topics (experiments)
  async getLabTopics(labId: string) {
    const response = await this.axiosInstance.get(`/lab/labs/${labId}/topics`)
    return response.data
  }

  // Create lab topic (experiment)
  async createLabTopic(labId: string, data: {
    title: string
    description?: string
    week_number?: number
    concept_content?: string
    prerequisites?: string[]
  }) {
    const response = await this.axiosInstance.post(`/lab/labs/${labId}/topics`, data)
    return response.data
  }

  // Update lab topic
  async updateLabTopic(topicId: string, data: any) {
    const response = await this.axiosInstance.put(`/lab/topics/${topicId}`, data)
    return response.data
  }

  // Get topic MCQs
  async getTopicMCQs(topicId: string) {
    const response = await this.axiosInstance.get(`/lab/topics/${topicId}/mcqs`)
    return response.data
  }

  // Create MCQ
  async createMCQ(topicId: string, data: {
    question_text: string
    options: string[]
    correct_option: number
    explanation?: string
    difficulty?: string
    marks?: number
  }) {
    const response = await this.axiosInstance.post(`/lab/topics/${topicId}/mcqs`, data)
    return response.data
  }

  // Get topic coding problems
  async getTopicProblems(topicId: string) {
    const response = await this.axiosInstance.get(`/lab/topics/${topicId}/problems`)
    return response.data
  }

  // Create coding problem
  async createCodingProblem(topicId: string, data: {
    title: string
    description: string
    difficulty?: string
    max_score?: number
    supported_languages?: string[]
    starter_code?: Record<string, string>
    test_cases?: Array<{ input: string; expected_output: string; is_hidden?: boolean }>
  }) {
    const response = await this.axiosInstance.post(`/lab/topics/${topicId}/problems`, data)
    return response.data
  }

  // Get lab students with progress
  async getLabStudents(labId: string) {
    const response = await this.axiosInstance.get(`/lab/labs/${labId}/students`)
    return response.data
  }

  // Get lab analytics
  async getLabAnalytics(labId: string) {
    const response = await this.axiosInstance.get(`/lab/labs/${labId}/analytics`)
    return response.data
  }

  // Get faculty classes/sections
  async getFacultyClasses() {
    const response = await this.axiosInstance.get('/faculty/classes')
    return response.data
  }

  // Assign topic to class/batch
  async assignTopicToClass(data: {
    topic_id: string
    lab_id: string
    class_id?: string
    batch_id?: string
    student_ids?: string[]
    deadline: string
    deadline_type: 'soft' | 'hard'
  }) {
    const response = await this.axiosInstance.post('/faculty/lab-assignments', data)
    return response.data
  }

  // Get lab assignments
  async getLabAssignments(labId: string) {
    const response = await this.axiosInstance.get(`/faculty/lab-assignments/${labId}`)
    return response.data
  }

  // Update lab assignment
  async updateLabAssignment(assignmentId: string, data: any) {
    const response = await this.axiosInstance.put(`/faculty/lab-assignments/${assignmentId}`, data)
    return response.data
  }

  // Get student progress for a specific topic
  async getTopicStudentProgress(topicId: string) {
    const response = await this.axiosInstance.get(`/lab/topics/${topicId}/student-progress`)
    return response.data
  }
}

export const apiClient = new ApiClient()
export default apiClient
