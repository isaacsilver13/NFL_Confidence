import { test as base, expect, type Page } from '@playwright/test'

async function signInAsDevUser(page: Page): Promise<void> {
  await page.goto('/login')
  await page.getByRole('button', { name: 'Continue as Dev User' }).click()
  await page.waitForURL('/')
}

interface WorkerFixtures {
  authedPage: Page
}

/**
 * Signs in once per worker process and reuses that browser context (with the project's
 * configured viewport/baseURL) for every test the worker runs. The backend's refresh
 * token is single-use and rotates on every call, so a fresh sign-in per test would both
 * blow through the 30/hour dev-login rate limit and fight over rotating cookies if
 * shared via storageState across parallel contexts.
 */
export const test = base.extend<object, WorkerFixtures>({
  authedPage: [
    async ({ browser }, use, workerInfo) => {
      const { viewport, baseURL } = workerInfo.project.use
      const context = await browser.newContext({ viewport, baseURL })
      const page = await context.newPage()
      await signInAsDevUser(page)
      await use(page)
      await context.close()
    },
    { scope: 'worker' },
  ],
})

export { expect }

export async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)
}

/** Rounded to absorb sub-pixel layout rounding (e.g. 43.999969...) around the 44px minimum. */
export function expectComfortableTapTarget(box: { height: number } | null): void {
  expect(Math.round(box?.height ?? 0)).toBeGreaterThanOrEqual(44)
}
