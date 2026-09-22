import { expect, test } from '@playwright/test'
import { expectComfortableTapTarget, expectNoHorizontalOverflow } from './fixtures'

test.describe('login page (mobile)', () => {
  test('renders without horizontal overflow', async ({ page }) => {
    await page.goto('/login')
    await expectNoHorizontalOverflow(page)
  })

  test('shows both sign-in options, each a comfortable tap target', async ({ page }) => {
    await page.goto('/login')

    const googleButton = page.getByRole('button', { name: 'Continue with Google' })
    const devButton = page.getByRole('button', { name: 'Continue as Dev User' })

    await expect(googleButton).toBeVisible()
    await expect(devButton).toBeVisible()

    for (const button of [googleButton, devButton]) {
      expectComfortableTapTarget(await button.boundingBox())
    }
  })
})
