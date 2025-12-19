import { defineConfig, devices } from '@playwright/test';
import path from 'path';

/**
 * BharatBuild AI - Playwright E2E Test Configuration
 * Uses shared authentication to avoid rate limiting
 */

const authFile = path.join(__dirname, 'tests/.auth/user.json');

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // Run sequentially to avoid rate limits
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1, // Single worker to avoid rate limits
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list']
  ],
  timeout: 60000, // 60 second timeout per test

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // Setup project - runs first to authenticate
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Auth tests - don't need pre-auth (they test auth flow)
    {
      name: 'auth-tests',
      testMatch: /auth\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Authenticated tests - depend on setup (excludes auth.spec.ts)
    {
      name: 'chromium',
      testMatch: /^(?!.*auth\.spec).*\.spec\.ts$/,
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: authFile,
      },
    },

    // Other browsers (commented out to reduce rate limiting)
    // {
    //   name: 'firefox',
    //   testMatch: /(?!auth\.spec).*\.spec\.ts/,
    //   dependencies: ['setup'],
    //   use: {
    //     ...devices['Desktop Firefox'],
    //     storageState: authFile,
    //   },
    // },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true, // Always reuse existing server
    timeout: 120 * 1000,
  },
});
