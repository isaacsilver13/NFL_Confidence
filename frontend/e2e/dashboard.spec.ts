import { type Page } from '@playwright/test'
import { expect, expectComfortableTapTarget, expectNoHorizontalOverflow, test } from './fixtures'

async function openSection(page: Page, namePrefix: string) {
  const header = page.getByRole('button', { name: new RegExp(`^${namePrefix}`) })
  if ((await header.getAttribute('aria-expanded')) !== 'true') {
    await header.click()
  }
  await expect(header).toHaveAttribute('aria-expanded', 'true')
  return header
}

test.describe('dashboard sections (mobile)', () => {
  test.beforeEach(async ({ authedPage }) => {
    await authedPage.goto('/')
  })

  for (const namePrefix of [
    'Make Your Picks',
    'Weekly Leaderboard',
    'Season Standings',
    'My Picks',
  ]) {
    test(`${namePrefix} section opens without horizontal overflow`, async ({ authedPage }) => {
      await openSection(authedPage, namePrefix)
      await expectNoHorizontalOverflow(authedPage)
    })
  }

  test('Members page opens without horizontal overflow', async ({ authedPage }) => {
    await authedPage.getByRole('link', { name: 'Members' }).click()
    await expectNoHorizontalOverflow(authedPage)
  })

  test('pick and confidence buttons are comfortable tap targets', async ({ authedPage }) => {
    await openSection(authedPage, 'Make Your Picks')

    const pickButtons = authedPage
      .getByRole('group', { name: /^Winner for/ })
      .first()
      .getByRole('button')
    const confidenceButtons = authedPage
      .getByRole('group', { name: /^Confidence for/ })
      .first()
      .getByRole('button')

    for (const group of [pickButtons, confidenceButtons]) {
      await expect(group.first()).toBeVisible()
      const count = await group.count()
      expect(count).toBeGreaterThan(0)
      for (let index = 0; index < count; index += 1) {
        expectComfortableTapTarget(await group.nth(index).boundingBox())
      }
    }
  })

  test('sticky picks-progress bar does not overlap the sticky nav header', async ({
    authedPage,
  }) => {
    await openSection(authedPage, 'Make Your Picks')

    const header = authedPage.locator('header').first()
    const progressBar = authedPage.getByRole('progressbar', { name: 'Games picked' })
    await expect(progressBar).toBeVisible()

    await authedPage.mouse.wheel(0, 400)

    const headerBox = await header.boundingBox()
    const progressBox = await progressBar.boundingBox()
    expect(headerBox).not.toBeNull()
    expect(progressBox).not.toBeNull()
    expect(progressBox!.y).toBeGreaterThanOrEqual(headerBox!.y + headerBox!.height - 1)
  })

  test('accordion headers are comfortable tap targets', async ({ authedPage }) => {
    for (const namePrefix of ['Make Your Picks', 'Weekly Leaderboard', 'Season Standings']) {
      const header = authedPage.getByRole('button', { name: new RegExp(`^${namePrefix}`) })
      expectComfortableTapTarget(await header.boundingBox())
    }
  })
})
