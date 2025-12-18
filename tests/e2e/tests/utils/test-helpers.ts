import { Page, expect } from '@playwright/test';

/**
 * BharatBuild AI - Test Helper Utilities
 */

// Test user credentials
export const TEST_USERS = {
  free: {
    email: process.env.FREE_USER_EMAIL || 'freeuser@test.com',
    password: process.env.FREE_USER_PASSWORD || 'TestPassword123!',
  },
  premium: {
    email: process.env.PREMIUM_USER_EMAIL || 'premiumuser@test.com',
    password: process.env.PREMIUM_USER_PASSWORD || 'TestPassword123!',
  },
  admin: {
    email: process.env.ADMIN_USER_EMAIL || 'admin@test.com',
    password: process.env.ADMIN_USER_PASSWORD || 'AdminPassword123!',
  },
};

/**
 * Login helper function
 */
export async function login(page: Page, userType: 'free' | 'premium' | 'admin' = 'free') {
  const user = TEST_USERS[userType];

  await page.goto('/login');
  await page.fill('input[name="email"]', user.email);
  await page.fill('input[name="password"]', user.password);
  await page.click('button[type="submit"]');

  // Wait for redirect
  await page.waitForURL(/\/(dashboard|build)/, { timeout: 10000 });

  // Verify login succeeded
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  expect(token).toBeTruthy();

  return token;
}

/**
 * Logout helper function
 */
export async function logout(page: Page) {
  await page.click('[data-testid="user-menu"]');
  await page.click('text=Logout');
  await page.waitForURL(/\/login/);
}

/**
 * Navigate to build page and wait for load
 */
export async function navigateToBuild(page: Page) {
  await page.goto('/build');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000); // Extra time for dynamic content
}

/**
 * Navigate to dashboard and wait for load
 */
export async function navigateToDashboard(page: Page) {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
}

/**
 * Check if element is visible with retry
 */
export async function isVisibleWithRetry(
  page: Page,
  selector: string,
  retries: number = 3,
  delay: number = 1000
): Promise<boolean> {
  for (let i = 0; i < retries; i++) {
    try {
      const element = page.locator(selector);
      if (await element.isVisible()) {
        return true;
      }
    } catch {
      // Element not found, retry
    }
    await page.waitForTimeout(delay);
  }
  return false;
}

/**
 * Wait for API response
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  timeout: number = 10000
) {
  return page.waitForResponse(
    (response) =>
      (typeof urlPattern === 'string'
        ? response.url().includes(urlPattern)
        : urlPattern.test(response.url())) && response.status() === 200,
    { timeout }
  );
}

/**
 * Generate unique email for testing
 */
export function generateTestEmail(): string {
  return `test_${Date.now()}_${Math.random().toString(36).substring(7)}@test.com`;
}

/**
 * Check premium feature locked state
 */
export async function checkPremiumLocked(page: Page, featureName: string): Promise<boolean> {
  // Check for lock icon
  const lockIcon = page.locator(`[data-testid="${featureName}"] svg.lucide-lock`);
  if (await lockIcon.isVisible()) {
    return true;
  }

  // Check for "(Premium)" text
  const premiumText = page.locator(`text=${featureName} (Premium)`);
  if (await premiumText.isVisible()) {
    return true;
  }

  // Check for amber color (locked feature indicator)
  const amberElement = page.locator(`.text-amber-400:has-text("${featureName}")`);
  if (await amberElement.isVisible()) {
    return true;
  }

  return false;
}

/**
 * Take screenshot with timestamp
 */
export async function takeScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({
    path: `./screenshots/${name}_${timestamp}.png`,
    fullPage: true,
  });
}

/**
 * Measure page load time
 */
export async function measurePageLoad(page: Page, url: string): Promise<number> {
  const startTime = Date.now();
  await page.goto(url);
  await page.waitForLoadState('networkidle');
  return Date.now() - startTime;
}

/**
 * Clear local storage and cookies
 */
export async function clearSession(page: Page) {
  await page.evaluate(() => localStorage.clear());
  await page.context().clearCookies();
}

/**
 * Assert element has specific CSS class
 */
export async function hasClass(page: Page, selector: string, className: string): Promise<boolean> {
  const element = page.locator(selector);
  const classes = await element.getAttribute('class');
  return classes?.includes(className) || false;
}

/**
 * Wait for toast/notification
 */
export async function waitForToast(page: Page, text: string, timeout: number = 5000) {
  const toast = page.locator(`.toast:has-text("${text}"), [role="alert"]:has-text("${text}")`);
  await expect(toast).toBeVisible({ timeout });
}

/**
 * Fill form fields from object
 */
export async function fillForm(page: Page, fields: Record<string, string>) {
  for (const [name, value] of Object.entries(fields)) {
    await page.fill(`input[name="${name}"], textarea[name="${name}"]`, value);
  }
}

/**
 * Get API response body
 */
export async function getApiResponse(page: Page, urlPattern: string): Promise<any> {
  const response = await page.waitForResponse((r) => r.url().includes(urlPattern));
  return response.json();
}
