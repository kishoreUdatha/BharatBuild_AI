/**
 * Auth utilities for managing access tokens in both localStorage and cookies.
 *
 * Cookies are needed for iframe preview access where Authorization headers
 * cannot be set by the browser.
 */

/**
 * Set access token in both localStorage and cookie.
 * Cookie is needed for iframe preview access.
 */
export function setAccessToken(token: string): void {
  if (typeof window === 'undefined') return

  // Set in localStorage (for API calls with Authorization header)
  localStorage.setItem('access_token', token)

  // Set as cookie (for iframe preview access)
  // SameSite=Lax allows cookie to be sent with same-site requests including iframes
  // Path=/ ensures cookie is sent for all paths
  // Secure flag should be set in production (HTTPS)
  const isSecure = window.location.protocol === 'https:'
  const cookieOptions = `path=/; ${isSecure ? 'secure; ' : ''}SameSite=Lax; max-age=${7 * 24 * 60 * 60}` // 7 days
  document.cookie = `access_token=${token}; ${cookieOptions}`
}

/**
 * Remove access token from both localStorage and cookie.
 */
export function removeAccessToken(): void {
  if (typeof window === 'undefined') return

  // Remove from localStorage
  localStorage.removeItem('access_token')

  // Remove cookie by setting expired date
  document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
}

/**
 * Get access token from localStorage.
 */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}
