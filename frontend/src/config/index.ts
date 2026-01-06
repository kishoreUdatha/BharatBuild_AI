/**
 * Frontend Configuration
 *
 * Centralized configuration management for the frontend.
 * All values are loaded from environment variables with sensible defaults.
 *
 * Usage:
 *   import { config } from '@/config'
 *   const apiUrl = config.api.baseUrl
 */

// ==========================================
// API Configuration
// ==========================================
export const apiConfig = {
  /** Backend API base URL */
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',

  /** WebSocket URL for real-time updates */
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',

  /** Request timeout in milliseconds (3 min for SDK Fixer Agent) */
  timeout: parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '180000', 10),

  /** Maximum retry attempts for failed requests */
  maxRetries: parseInt(process.env.NEXT_PUBLIC_MAX_RETRIES || '3', 10),

  /** Base delay for retry backoff in milliseconds */
  retryDelayBase: parseInt(process.env.NEXT_PUBLIC_RETRY_DELAY_BASE || '1000', 10),

  /** Maximum retry delay in milliseconds */
  maxRetryDelay: parseInt(process.env.NEXT_PUBLIC_MAX_RETRY_DELAY || '30000', 10),

  /** HTTP status codes that should trigger a retry */
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
}

// ==========================================
// Application Settings
// ==========================================
export const appConfig = {
  /** Application name */
  name: process.env.NEXT_PUBLIC_APP_NAME || 'BharatBuild AI',

  /** Application domain */
  domain: process.env.NEXT_PUBLIC_APP_DOMAIN || 'bharatbuild.ai',

  /** Base URL for share links */
  shareUrlBase: process.env.NEXT_PUBLIC_SHARE_URL_BASE || 'https://bharatbuild.ai/share',

  /** Check if running in development mode */
  isDevelopment: process.env.NODE_ENV === 'development',

  /** Check if running in production mode */
  isProduction: process.env.NODE_ENV === 'production',
}

// ==========================================
// Reconnection Settings
// ==========================================
export const reconnectionConfig = {
  /** Maximum reconnection attempts */
  maxRetries: parseInt(process.env.NEXT_PUBLIC_RECONNECTION_MAX_RETRIES || '5', 10),

  /** Base delay for reconnection backoff in milliseconds */
  baseDelay: parseInt(process.env.NEXT_PUBLIC_RECONNECTION_BASE_DELAY || '1000', 10),

  /** Heartbeat interval in milliseconds */
  heartbeatInterval: parseInt(process.env.NEXT_PUBLIC_HEARTBEAT_INTERVAL || '30000', 10),

  /** Health check interval in milliseconds */
  healthCheckInterval: parseInt(process.env.NEXT_PUBLIC_HEALTH_CHECK_INTERVAL || '30000', 10),

  /** Health check timeout in milliseconds */
  healthCheckTimeout: parseInt(process.env.NEXT_PUBLIC_HEALTH_CHECK_TIMEOUT || '5000', 10),
}

// ==========================================
// Token System
// ==========================================
export const tokenConfig = {
  /** Default token balance for demo/development */
  defaultBalance: parseInt(process.env.NEXT_PUBLIC_DEFAULT_TOKEN_BALANCE || '10000', 10),

  /** Usage percentage threshold for warning */
  warningThreshold: parseInt(process.env.NEXT_PUBLIC_TOKEN_WARNING_THRESHOLD || '80', 10),
}

// ==========================================
// Project Settings
// ==========================================
export const projectConfig = {
  /** Default estimated tokens for new projects */
  defaultTokens: parseInt(process.env.NEXT_PUBLIC_DEFAULT_PROJECT_TOKENS || '15000', 10),

  /** Default container port for previews */
  defaultContainerPort: parseInt(process.env.NEXT_PUBLIC_DEFAULT_CONTAINER_PORT || '3000', 10),

  /** Command execution timeout in seconds */
  commandTimeout: parseInt(process.env.NEXT_PUBLIC_COMMAND_TIMEOUT || '300', 10),

  /** Project status polling interval in milliseconds */
  statusPollingInterval: parseInt(process.env.NEXT_PUBLIC_PROJECT_STATUS_INTERVAL || '3000', 10),
}

// ==========================================
// AI Context Settings
// ==========================================
export const aiConfig = {
  /** Maximum tokens for AI context */
  maxContextTokens: parseInt(process.env.NEXT_PUBLIC_MAX_CONTEXT_TOKENS || '50000', 10),
}

// ==========================================
// Container Settings
// ==========================================
export const containerConfig = {
  /** Container check interval in milliseconds */
  checkInterval: parseInt(process.env.NEXT_PUBLIC_CONTAINER_CHECK_INTERVAL || '30000', 10),

  /** Default container port */
  defaultPort: parseInt(process.env.NEXT_PUBLIC_DEFAULT_CONTAINER_PORT || '3000', 10),
}

// ==========================================
// Feature Flags
// ==========================================
export const featureFlags = {
  /** Enable OAuth authentication */
  enableOAuth: process.env.NEXT_PUBLIC_ENABLE_OAUTH !== 'false',

  /** Enable container execution */
  enableContainerExecution: process.env.NEXT_PUBLIC_ENABLE_CONTAINER_EXECUTION !== 'false',

  /** Enable live preview */
  enableLivePreview: process.env.NEXT_PUBLIC_ENABLE_LIVE_PREVIEW !== 'false',
}

// ==========================================
// OAuth Configuration
// ==========================================
export const oauthConfig = {
  google: {
    clientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
  },
  github: {
    clientId: process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || '',
  },
}

// ==========================================
// Image Configuration
// ==========================================
export const imageConfig = {
  /** Allowed image domains */
  domains: (process.env.NEXT_PUBLIC_IMAGE_DOMAINS || 'localhost').split(',').map(d => d.trim()),
}

// ==========================================
// Helper Functions
// ==========================================

/**
 * Get the full API URL for an endpoint
 */
export function getApiUrl(endpoint: string): string {
  const baseUrl = apiConfig.baseUrl.replace(/\/$/, '')
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${baseUrl}${path}`
}

/**
 * Get the health check URL (without /api/v1)
 */
export function getHealthUrl(): string {
  return apiConfig.baseUrl.replace('/api/v1', '/health')
}

/**
 * Get the share URL for a project
 */
export function getShareUrl(projectId: string): string {
  return `${appConfig.shareUrlBase}/${projectId}`
}

/**
 * Get preview URL for a project
 * Uses path-based routing: https://bharatbuild.ai/api/v1/preview/{projectId}/
 */
export function getPreviewUrl(projectId: string): string {
  // Always use path-based preview URL (works with CloudFront, no wildcard DNS needed)
  return `${apiConfig.baseUrl}/preview/${projectId}/`
}

/**
 * Calculate retry delay with exponential backoff and jitter
 */
export function getRetryDelay(retryCount: number): number {
  const exponentialDelay = apiConfig.retryDelayBase * Math.pow(2, retryCount - 1)
  const jitter = Math.random() * 1000
  return Math.min(exponentialDelay + jitter, apiConfig.maxRetryDelay)
}

/**
 * Calculate reconnection delay with exponential backoff
 */
export function getReconnectionDelay(attempt: number): number {
  return Math.min(
    reconnectionConfig.baseDelay * Math.pow(2, attempt),
    reconnectionConfig.baseDelay * 30 // Max 30x base delay
  )
}

// ==========================================
// Combined Config Export
// ==========================================
export const config = {
  api: apiConfig,
  app: appConfig,
  reconnection: reconnectionConfig,
  token: tokenConfig,
  project: projectConfig,
  ai: aiConfig,
  container: containerConfig,
  features: featureFlags,
  oauth: oauthConfig,
  image: imageConfig,
}

export default config
