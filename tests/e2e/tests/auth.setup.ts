/**
 * Global Authentication Setup
 * Logs in once and saves auth state for all tests to reuse
 */
import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  // Go to login page
  await page.goto('/login');

  // Fill login form - using dedicated E2E test user
  await page.fill('#email', process.env.TEST_USER_EMAIL || 'e2e_test_user@example.com');
  await page.fill('#password', process.env.TEST_USER_PASSWORD || 'E2ETestPass123!');

  // Submit
  await page.click('button[type="submit"]');

  // Wait for redirect or error
  await page.waitForTimeout(5000);

  // Check if login succeeded
  const currentUrl = page.url();
  const isLoggedIn = /\/(dashboard|build|admin)/.test(currentUrl);

  if (isLoggedIn) {
    // Save authentication state
    await page.context().storageState({ path: authFile });
    console.log('Authentication successful - state saved');
  } else {
    // Check for rate limiting
    const rateLimitError = await page.locator('text=/rate|limit|too many|per.*minute/i').isVisible();
    if (rateLimitError) {
      console.log('Rate limited during auth setup - waiting 60 seconds...');
      await page.waitForTimeout(60000);

      // Retry login
      await page.goto('/login');
      await page.fill('#email', process.env.TEST_USER_EMAIL || 'e2e_test_user@example.com');
      await page.fill('#password', process.env.TEST_USER_PASSWORD || 'E2ETestPass123!');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(5000);

      const retryUrl = page.url();
      if (/\/(dashboard|build|admin)/.test(retryUrl)) {
        await page.context().storageState({ path: authFile });
        console.log('Authentication successful after retry - state saved');
      } else {
        throw new Error('Authentication failed after retry');
      }
    } else {
      throw new Error(`Authentication failed - stayed on ${currentUrl}`);
    }
  }
});
