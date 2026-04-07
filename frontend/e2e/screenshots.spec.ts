import { test, expect } from '@playwright/test'

const SHOTS = '../docs/screenshots'

test('project list page', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.project-card').first()).toBeVisible({ timeout: 5000 })
  await page.screenshot({ path: `${SHOTS}/01-project-list.png`, fullPage: true })
})

test('project page - listing selected', async ({ page }) => {
  await page.goto('/')
  await page.locator('.project-card').first().click()
  await expect(page.locator('.listing-card').first()).toBeVisible({ timeout: 10000 })

  // Select a listing with a good score
  const cards = page.locator('.listing-card')
  const count = await cards.count()
  for (let i = 0; i < Math.min(count, 5); i++) {
    const score = await cards.nth(i).locator('.card-score').textContent()
    if (score && parseInt(score) > 80) {
      await cards.nth(i).locator('.card-name').click()
      break
    }
  }
  await page.waitForTimeout(500)
  await expect(page.locator('.listing-detail')).toBeVisible({ timeout: 5000 })
  await page.screenshot({ path: `${SHOTS}/02-project-detail.png`, fullPage: false })
})

test('project page - filters active', async ({ page }) => {
  await page.goto('/')
  await page.locator('.project-card').first().click()
  await expect(page.locator('.listing-card').first()).toBeVisible({ timeout: 10000 })

  // Apply a filter
  const hideLabel = page.locator('.filter-bar label', { hasText: 'Hide failed' })
  await hideLabel.click()
  await page.waitForTimeout(500)

  // Select first listing
  await page.locator('.listing-card .card-name').first().click()
  await page.waitForTimeout(500)
  await page.screenshot({ path: `${SHOTS}/03-filters.png`, fullPage: false })
})

test('activity log', async ({ page }) => {
  await page.goto('/')
  await page.locator('.project-card').first().click()
  await expect(page.locator('.activity-log')).toBeVisible({ timeout: 5000 })

  // Scroll log to show some entries
  await page.screenshot({ path: `${SHOTS}/04-activity-log.png`, fullPage: true })
})

test('detail view - attributes and histogram', async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 900 })
  await page.goto('/')
  await page.locator('.project-card').first().click()
  await expect(page.locator('.listing-card').first()).toBeVisible({ timeout: 10000 })
  await page.locator('.listing-card .card-name').first().click()
  await page.waitForTimeout(500)

  // Crop to just the detail pane
  const detail = page.locator('.split-right')
  await detail.screenshot({ path: `${SHOTS}/05-detail-attributes.png` })
})
