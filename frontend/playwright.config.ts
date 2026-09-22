import { defineConfig, devices } from '@playwright/test'
import { BASE_URL } from './e2e/constants'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  // Serial: the dev sign-in is rate-limited (30/hour) and each worker process signs in
  // once (see e2e/fixtures.ts), so more/rotating workers burn through that budget fast
  // across repeated local runs.
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'mobile-390',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } },
    },
    {
      name: 'mobile-375',
      use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 667 } },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
  },
})
