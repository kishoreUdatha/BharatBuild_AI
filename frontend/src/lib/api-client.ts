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

  // ==================== ML Projects ====================
  async getMLModels() {
    const response = await this.axiosInstance.get('/ml/models')
    return response.data
  }

  async getMLModelDetails(modelType: string) {
    const response = await this.axiosInstance.get(`/ml/models/${modelType}`)
    return response.data
  }

  async getMLTemplate(modelType: string, projectName: string = 'my_ml_project') {
    const response = await this.axiosInstance.get(`/ml/template/${modelType}`, {
      params: { project_name: projectName }
    })
    return response.data
  }

  async generateMLProject(config: {
    model_type: string;
    project_name: string;
    num_classes?: number;
    input_size?: number;
    max_length?: number;
    hidden_dim?: number;
    batch_size?: number;
    epochs?: number;
    learning_rate?: number;
    customization_prompt?: string;
  }) {
    const response = await this.axiosInstance.post('/ml/generate', { config })
    return response.data
  }

  async customizeMLProject(params: {
    model_type: string;
    project_name: string;
    prompt: string;
    base_template?: boolean;
    config?: Record<string, any>;
  }) {
    const response = await this.axiosInstance.post('/ml/customize', params)
    return response.data
  }

  async getMLCategories() {
    const response = await this.axiosInstance.get('/ml/categories')
    return response.data
  }

  async getMLFrameworks() {
    const response = await this.axiosInstance.get('/ml/frameworks')
    return response.data
  }

  async getTabularModels() {
    const response = await this.axiosInstance.get('/ml/tabular-models')
    return response.data
  }

  async generateMLProjectWithDataset(params: {
    model_type: string;
    project_name: string;
    dataset_id: string;
    target_column: string;
    feature_columns?: string[];
    num_classes?: number;
    batch_size?: number;
    epochs?: number;
    learning_rate?: number;
    test_size?: number;
    workspace_id?: string;
  }) {
    const response = await this.axiosInstance.post('/ml/generate-with-dataset', params)
    return response.data
  }

  // ==================== Datasets ====================
  async uploadDataset(formData: FormData) {
    const response = await this.axiosInstance.post('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  async configureDataset(params: {
    dataset_id: string;
    target_column: string;
    feature_columns?: string[];
    project_id?: string;
  }) {
    const response = await this.axiosInstance.post('/datasets/configure', params)
    return response.data
  }

  async getDataset(datasetId: string) {
    const response = await this.axiosInstance.get(`/datasets/${datasetId}`)
    return response.data
  }

  async listDatasets(params?: { page?: number; page_size?: number; status_filter?: string }) {
    const response = await this.axiosInstance.get('/datasets', { params })
    return response.data
  }

  async deleteDataset(datasetId: string) {
    const response = await this.axiosInstance.delete(`/datasets/${datasetId}`)
    return response.data
  }

  async getDatasetPreview(datasetId: string, rows: number = 10) {
    const response = await this.axiosInstance.get(`/datasets/${datasetId}/preview`, {
      params: { rows }
    })
    return response.data
  }

  // ==================== Image Datasets ====================
  async uploadImageDataset(formData: FormData) {
    const response = await this.axiosInstance.post('/datasets/upload-images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 300000, // 5 minutes for large image uploads
    })
    return response.data
  }

  async configureImageDataset(params: {
    dataset_id: string;
    input_size?: number;
    augmentation?: boolean;
    normalize?: boolean;
    project_id?: string;
  }) {
    const response = await this.axiosInstance.post('/datasets/configure-images', params)
    return response.data
  }

  async getVisionModels() {
    const response = await this.axiosInstance.get('/ml/vision-models')
    return response.data
  }

  async generateMLProjectWithImageDataset(params: {
    model_type: string;
    project_name: string;
    dataset_id: string;
    input_size?: number;
    augmentation?: boolean;
    num_classes?: number;
    batch_size?: number;
    epochs?: number;
    learning_rate?: number;
    pretrained?: boolean;
    freeze_layers?: boolean;
    workspace_id?: string;
  }) {
    const response = await this.axiosInstance.post('/ml/generate-with-image-dataset', params)
    return response.data
  }

  // ==================== Prompt-Based ML Generation ====================
  async analyzeMLPrompt(prompt: string) {
    const response = await this.axiosInstance.post('/ml/analyze-prompt', { prompt })
    return response.data
  }

  async generateMLProjectFromPrompt(params: {
    prompt: string;
    project_name?: string;
    workspace_id?: string;
    model_type?: string;
    num_classes?: number;
    input_size?: number;
  }) {
    const response = await this.axiosInstance.post('/ml/generate-from-prompt', params)
    return response.data
  }

  // ==================== Mobile Builds ====================
  async getBuildQuota() {
    const response = await this.axiosInstance.get('/builds/quota')
    return response.data
  }

  async startAPKBuild(projectId: string, config: {
    app_name?: string;
    version?: string;
    build_number?: number;
    bundle_id?: string;
  }) {
    const response = await this.axiosInstance.post(`/builds/${projectId}/apk`, config)
    return response.data
  }

  async startIPABuild(projectId: string, config: {
    app_name?: string;
    version?: string;
    build_number?: number;
    bundle_id?: string;
  }) {
    const response = await this.axiosInstance.post(`/builds/${projectId}/ipa`, config)
    return response.data
  }

  async getBuildStatus(projectId: string, buildId?: string) {
    const url = buildId
      ? `/builds/${projectId}/status?build_id=${buildId}`
      : `/builds/${projectId}/status`
    const response = await this.axiosInstance.get(url)
    return response.data
  }

  async getBuildDownloadUrl(projectId: string, buildId?: string) {
    const url = buildId
      ? `/builds/${projectId}/download?build_id=${buildId}`
      : `/builds/${projectId}/download`
    const response = await this.axiosInstance.get(url)
    return response.data
  }

  async cancelBuild(projectId: string, reason?: string) {
    const response = await this.axiosInstance.delete(`/builds/${projectId}/cancel`, {
      data: reason ? { reason } : undefined
    })
    return response.data
  }

  async getBuildHistory(projectId: string, params?: { platform?: string; limit?: number }) {
    const response = await this.axiosInstance.get(`/builds/${projectId}/history`, { params })
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
