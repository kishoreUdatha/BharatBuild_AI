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
                // Refresh failed, logout
                console.log('Token refresh failed, logging out')
              }
            }
            // No refresh token or refresh failed - logout
            removeAccessToken()
            localStorage.removeItem('refresh_token')
            window.location.href = '/login'
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

  // ==================== NAAC/NBA Accreditation ====================

  /**
   * Get NAAC criteria overview
   */
  async getAccreditationOverview() {
    const response = await this.axiosInstance.get('/accreditation/overview')
    return response.data
  }

  /**
   * Get all NAAC criteria details
   */
  async getAccreditationCriteria() {
    const response = await this.axiosInstance.get('/accreditation/criteria')
    return response.data
  }

  /**
   * Get supported document types
   */
  async getAccreditationDocumentTypes() {
    const response = await this.axiosInstance.get('/accreditation/document-types')
    return response.data
  }

  /**
   * Generate complete SSR (Self Study Report)
   */
  async generateSSR(data: {
    institution: {
      name: string
      type: string
      location: string
      state: string
      established_year: number
      naac_cycle?: number
      previous_grade?: string
      programs_offered?: string[]
      total_students?: number
      total_faculty?: number
    }
    academic_year?: string
    naac_cycle?: number
  }) {
    const response = await this.axiosInstance.post('/accreditation/ssr/generate', data)
    return response.data
  }

  /**
   * Generate criterion-specific documents (1-7)
   */
  async generateCriterionDocuments(criterionNumber: number, data: {
    institution: {
      name: string
      type: string
      location: string
      state: string
      established_year: number
    }
    criterion: string
    academic_year?: string
    additional_context?: string
  }) {
    const response = await this.axiosInstance.post(`/accreditation/criterion/${criterionNumber}`, data)
    return response.data
  }

  /**
   * Generate Course Outcomes with Bloom's Taxonomy
   */
  async generateCourseOutcomes(data: {
    course_info: {
      course_name: string
      course_code: string
      department: string
      semester: number
      credits: number
      program_name?: string
    }
    project_description: string
  }) {
    const response = await this.axiosInstance.post('/accreditation/obe/course-outcomes', data)
    return response.data
  }

  /**
   * Generate CO-PO Mapping Matrix
   */
  async generateCOPOMapping(data: {
    course_info: {
      course_name: string
      course_code: string
      department: string
      semester: number
      credits: number
    }
    course_outcomes: string[]
  }) {
    const response = await this.axiosInstance.post('/accreditation/obe/co-po-mapping', data)
    return response.data
  }

  /**
   * Generate Assessment Rubrics
   */
  async generateRubrics(data: {
    course_info: {
      course_name: string
      course_code: string
      department: string
      semester: number
      credits: number
    }
    assessment_type?: string
    criteria_count?: number
  }) {
    const response = await this.axiosInstance.post('/accreditation/obe/rubrics', data)
    return response.data
  }

  /**
   * Generate Attainment Calculation Template
   */
  async generateAttainment(data: {
    course_info: {
      course_name: string
      course_code: string
      department: string
      semester: number
      credits: number
    }
    project_description: string
  }) {
    const response = await this.axiosInstance.post('/accreditation/obe/attainment', data)
    return response.data
  }

  /**
   * Generate IQAC Documentation
   */
  async generateIQACReport(data: {
    institution: {
      name: string
      type: string
      location: string
      state: string
      established_year: number
    }
    academic_year?: string
  }) {
    const response = await this.axiosInstance.post('/accreditation/iqac/report', data)
    return response.data
  }

  /**
   * Generate Best Practices Documentation
   */
  async generateBestPractices(data: {
    institution: {
      name: string
      type: string
      location: string
      state: string
      established_year: number
    }
    focus_areas?: string[]
  }) {
    const response = await this.axiosInstance.post('/accreditation/best-practices', data)
    return response.data
  }

  /**
   * Generate Green/Environmental Audit
   */
  async generateGreenAudit(data: {
    institution: {
      name: string
      type: string
      location: string
      state: string
      established_year: number
    }
    audit_year?: string
  }) {
    const response = await this.axiosInstance.post('/accreditation/green-audit', data)
    return response.data
  }

  /**
   * Get NBA Program Outcomes (12 POs)
   */
  async getProgramOutcomes() {
    const response = await this.axiosInstance.get('/accreditation/program-outcomes')
    return response.data
  }

  /**
   * Get Bloom's Taxonomy levels
   */
  async getBloomsTaxonomy() {
    const response = await this.axiosInstance.get('/accreditation/blooms-taxonomy')
    return response.data
  }

  // ==================== Criterion 1: Curricular Aspects ====================

  /**
   * Get Criterion 1 dashboard statistics
   */
  async getCriterion1Dashboard(academicYear?: string) {
    const params = academicYear ? `?academic_year=${academicYear}` : ''
    const response = await this.axiosInstance.get(`/accreditation/criterion1/dashboard${params}`)
    return response.data
  }

  /**
   * Generate Criterion 1 report
   */
  async generateCriterion1Report(data: {
    institution_name: string
    academic_year: string
    include_sections?: string[]
    format?: 'docx' | 'pdf'
    include_evidence_list?: boolean
    include_analytics?: boolean
  }) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/generate-report', data)
    return response.data
  }

  // Feedback Management
  async createFeedback(data: {
    feedback_type: string
    department: string
    academic_year: string
    feedback_content: string
    respondent_name?: string
    respondent_email?: string
    program?: string
    rating?: number
    suggestions?: string
  }) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/feedback', data)
    return response.data
  }

  async listFeedback(params?: {
    feedback_type?: string
    status?: string
    department?: string
    academic_year?: string
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/accreditation/criterion1/feedback?${queryParams.toString()}`)
    return response.data
  }

  async updateFeedbackAction(feedbackId: string, data: {
    action_taken: string
    action_evidence?: string
  }) {
    const response = await this.axiosInstance.put(`/accreditation/criterion1/feedback/${feedbackId}/action`, data)
    return response.data
  }

  async generateFeedbackReport(data: {
    academic_year: string
    department?: string
    feedback_types?: string[]
    include_pending?: boolean
  }) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/feedback/generate-report', data)
    return response.data
  }

  // Evidence Management
  async uploadEvidence(formData: FormData) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/evidence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }

  async listEvidence(params?: {
    key_indicator?: string
    evidence_type?: string
    academic_year?: string
    is_verified?: boolean
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/accreditation/criterion1/evidence?${queryParams.toString()}`)
    return response.data
  }

  async verifyEvidence(evidenceId: string, data: {
    verified_by: string
    verification_remarks?: string
  }) {
    const response = await this.axiosInstance.post(`/accreditation/criterion1/evidence/${evidenceId}/verify`, data)
    return response.data
  }

  async deleteEvidence(evidenceId: string) {
    const response = await this.axiosInstance.delete(`/accreditation/criterion1/evidence/${evidenceId}`)
    return response.data
  }

  // Industry Partners
  async createIndustryPartner(data: {
    name: string
    partner_type: string
    industry_sector?: string
    website?: string
    contact_person?: string
    contact_email?: string
    department?: string
    collaboration_areas?: string[]
  }) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/industry-partners', data)
    return response.data
  }

  async listIndustryPartners(params?: {
    partner_type?: string
    mou_status?: string
    department?: string
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/accreditation/criterion1/industry-partners?${queryParams.toString()}`)
    return response.data
  }

  async updateIndustryPartner(partnerId: string, data: any) {
    const response = await this.axiosInstance.put(`/accreditation/criterion1/industry-partners/${partnerId}`, data)
    return response.data
  }

  // Value-Added Courses
  async createValueAddedCourse(data: {
    course_name: string
    course_type: string
    department: string
    academic_year: string
    duration_hours: number
    course_code?: string
    course_mode?: string
    description?: string
    instructor_name?: string
    certification_provided?: boolean
  }) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/value-added-courses', data)
    return response.data
  }

  async listValueAddedCourses(params?: {
    course_type?: string
    department?: string
    academic_year?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/accreditation/criterion1/value-added-courses?${queryParams.toString()}`)
    return response.data
  }

  async recordCourseEnrollment(courseId: string, data: {
    student_id: string
    student_name: string
    enrollment_date: string
    student_email?: string
    department?: string
    batch?: string
  }) {
    const response = await this.axiosInstance.post(`/accreditation/criterion1/value-added-courses/${courseId}/enrollments`, data)
    return response.data
  }

  // Internships
  async recordInternship(data: {
    student_id: string
    student_name: string
    department: string
    academic_year: string
    internship_type: string
    company_name: string
    start_date: string
    student_email?: string
    industry_sector?: string
    location?: string
    is_remote?: boolean
    end_date?: string
    duration_weeks?: number
    role_title?: string
    is_paid?: boolean
    stipend_amount?: number
  }) {
    const response = await this.axiosInstance.post('/accreditation/criterion1/internships', data)
    return response.data
  }

  async listInternships(params?: {
    internship_type?: string
    status?: string
    department?: string
    academic_year?: string
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/accreditation/criterion1/internships?${queryParams.toString()}`)
    return response.data
  }

  async getInternshipAnalytics(academicYear?: string) {
    const params = academicYear ? `?academic_year=${academicYear}` : ''
    const response = await this.axiosInstance.get(`/accreditation/criterion1/internships/analytics${params}`)
    return response.data
  }

  // ==================== NAAC RBAC System ====================

  /**
   * Get available NAAC roles
   */
  async getNAACRoles() {
    const response = await this.axiosInstance.get('/naac/rbac/roles')
    return response.data
  }

  /**
   * Get current user's NAAC roles
   */
  async getMyNAACRoles() {
    const response = await this.axiosInstance.get('/naac/rbac/my-roles')
    return response.data
  }

  /**
   * Assign NAAC role to user
   */
  async assignNAACRole(data: {
    user_id: string
    role_type: string
    criterion_number?: number
    department?: string
    valid_from?: string
    valid_until?: string
    assignment_notes?: string
  }) {
    const response = await this.axiosInstance.post('/naac/rbac/assign-role', data)
    return response.data
  }

  /**
   * Revoke NAAC role assignment
   */
  async revokeNAACRole(assignmentId: string) {
    const response = await this.axiosInstance.delete(`/naac/rbac/revoke-role/${assignmentId}`)
    return response.data
  }

  /**
   * Get users with NAAC roles
   */
  async getUsersWithNAACRoles(params?: {
    role_type?: string
    criterion?: number
    department?: string
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/naac/rbac/users-with-roles?${queryParams.toString()}`)
    return response.data
  }

  /**
   * Check NAAC permission
   */
  async checkNAACPermission(data: {
    resource: string
    action: string
    criterion_number?: number
    department?: string
  }) {
    const response = await this.axiosInstance.post('/naac/rbac/check-permission', data)
    return response.data
  }

  /**
   * Get accessible scope for current user
   */
  async getAccessibleScope() {
    const response = await this.axiosInstance.get('/naac/rbac/accessible-scope')
    return response.data
  }

  /**
   * Create NAAC task
   */
  async createNAACTask(data: {
    title: string
    description?: string
    task_type?: string
    criterion_number?: number
    key_indicator?: string
    department?: string
    academic_year?: string
    assigned_to?: string
    priority?: string
    due_date?: string
    related_record_type?: string
    related_record_id?: string
    attachments?: string[]
    extra_data?: Record<string, any>
  }) {
    const response = await this.axiosInstance.post('/naac/rbac/tasks', data)
    return response.data
  }

  /**
   * Get NAAC tasks
   */
  async getNAACTasks(params?: {
    status_filter?: string
    priority?: string
    criterion?: number
    department?: string
    assigned_to_me?: boolean
    created_by_me?: boolean
    page?: number
    page_size?: number
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/naac/rbac/tasks?${queryParams.toString()}`)
    return response.data
  }

  /**
   * Get NAAC task by ID
   */
  async getNAACTask(taskId: string) {
    const response = await this.axiosInstance.get(`/naac/rbac/tasks/${taskId}`)
    return response.data
  }

  /**
   * Update NAAC task
   */
  async updateNAACTask(taskId: string, data: {
    title?: string
    description?: string
    task_type?: string
    assigned_to?: string
    status?: string
    priority?: string
    due_date?: string
    progress_percentage?: number
    attachments?: string[]
    extra_data?: Record<string, any>
  }) {
    const response = await this.axiosInstance.put(`/naac/rbac/tasks/${taskId}`, data)
    return response.data
  }

  /**
   * Add comment to NAAC task
   */
  async addNAACTaskComment(taskId: string, data: {
    content: string
    attachments?: string[]
  }) {
    const response = await this.axiosInstance.post(`/naac/rbac/tasks/${taskId}/comments`, data)
    return response.data
  }

  /**
   * Get NAAC task comments
   */
  async getNAACTaskComments(taskId: string) {
    const response = await this.axiosInstance.get(`/naac/rbac/tasks/${taskId}/comments`)
    return response.data
  }

  /**
   * Submit record for approval
   */
  async submitForApproval(data: {
    record_type: string
    record_id: string
    criterion_number?: number
    department?: string
    academic_year?: string
    remarks?: string
  }) {
    const response = await this.axiosInstance.post('/naac/rbac/approval/submit', data)
    return response.data
  }

  /**
   * Perform approval action
   */
  async performApprovalAction(workflowId: string, data: {
    action: 'approve' | 'reject' | 'revision'
    remarks?: string
  }) {
    const response = await this.axiosInstance.post(`/naac/rbac/approval/${workflowId}/action`, data)
    return response.data
  }

  /**
   * Get pending approvals
   */
  async getPendingApprovals() {
    const response = await this.axiosInstance.get('/naac/rbac/approval/pending')
    return response.data
  }

  /**
   * Get approval workflow details
   */
  async getApprovalWorkflow(workflowId: string) {
    const response = await this.axiosInstance.get(`/naac/rbac/approval/${workflowId}`)
    return response.data
  }

  /**
   * Get NAAC notifications
   */
  async getNAACNotifications(params?: { unread_only?: boolean; limit?: number }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) queryParams.append(key, String(value))
      })
    }
    const response = await this.axiosInstance.get(`/naac/rbac/notifications?${queryParams.toString()}`)
    return response.data
  }

  /**
   * Mark notifications as read
   */
  async markNAACNotificationsRead(notificationIds: string[]) {
    const response = await this.axiosInstance.post('/naac/rbac/notifications/mark-read', {
      notification_ids: notificationIds
    })
    return response.data
  }

  /**
   * Mark all notifications as read
   */
  async markAllNAACNotificationsRead() {
    const response = await this.axiosInstance.post('/naac/rbac/notifications/mark-all-read')
    return response.data
  }

  /**
   * Get NAAC dashboard data
   */
  async getNAACDashboard() {
    const response = await this.axiosInstance.get('/naac/rbac/dashboard')
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
}

export const apiClient = new ApiClient()
export default apiClient
