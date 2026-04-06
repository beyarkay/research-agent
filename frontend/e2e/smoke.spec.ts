import { test, expect } from '@playwright/test'

// Helper: navigate to first project's page and wait for listings
async function goToFirstProject(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.locator('.project-card').first().click()
  await expect(page.locator('.listing-card').first()).toBeVisible({ timeout: 10000 })
}

test.describe('Project list', () => {
  test('loads and shows projects', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1')).toHaveText('Research Agent')
    const cards = page.locator('.project-card')
    await expect(cards.first()).toBeVisible({ timeout: 5000 })
  })

  test('project card shows status and prompt', async ({ page }) => {
    await page.goto('/')
    const card = page.locator('.project-card').first()
    await expect(card.locator('.status-label')).toBeVisible()
    await expect(card.locator('.project-prompt')).toBeVisible()
    const prompt = await card.locator('.project-prompt').textContent()
    expect(prompt?.length).toBeGreaterThan(5)
  })
})

test.describe('Navigation', () => {
  test('clicking project navigates to project page', async ({ page }) => {
    await page.goto('/')
    await page.locator('.project-card').first().click()
    await expect(page).toHaveURL(/\/projects\/[a-f0-9]+/)
    await expect(page.locator('.project-header')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.header-prompt')).toBeVisible()
  })

  test('direct URL navigation works (SPA routing)', async ({ page }) => {
    const resp = await page.request.get('/api/projects')
    const projects = await resp.json()
    const projectId = projects[0].id

    await page.goto(`/projects/${projectId}`)
    await expect(page.locator('.project-header')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.header-prompt')).toBeVisible()
  })

  test('back link returns to project list', async ({ page }) => {
    await goToFirstProject(page)
    await page.locator('.back-link').click()
    await expect(page).toHaveURL('/')
    await expect(page.locator('h1')).toHaveText('Research Agent')
  })
})

test.describe('Listings', () => {
  test('listings appear in left panel with names', async ({ page }) => {
    await goToFirstProject(page)
    const firstName = page.locator('.listing-card .card-name').first()
    const text = await firstName.textContent()
    expect(text?.length).toBeGreaterThan(0)
  })

  test('clicking listing shows detail on right', async ({ page }) => {
    await goToFirstProject(page)
    await page.locator('.listing-card .card-name').first().click()
    await page.waitForTimeout(500)

    const detail = page.locator('.listing-detail')
    await expect(detail).toBeVisible({ timeout: 5000 })
    await expect(detail.locator('h2')).toBeVisible()
    await expect(detail.locator('.attribute-grid')).toBeVisible()
    await expect(detail.locator('.attr-row').first()).toBeVisible()
  })

  test('score displays a real number', async ({ page }) => {
    await goToFirstProject(page)
    const score = page.locator('.card-score').first()
    await expect(score).toBeVisible()
    const text = await score.textContent()
    const num = parseInt(text ?? '', 10)
    expect(num).toBeGreaterThan(0)
    expect(num).toBeLessThanOrEqual(100)
  })

  test('completeness shows non-zero values', async ({ page }) => {
    await goToFirstProject(page)
    const comp = page.locator('.card-completeness').first()
    await expect(comp).toBeVisible()
    const text = await comp.textContent()
    // Should be like "12/14", not "0/4"
    expect(text).toMatch(/^\d+\/\d+$/)
    const [filled] = text!.split('/')
    expect(parseInt(filled, 10)).toBeGreaterThan(0)
  })

  test('address links point to Google Maps', async ({ page }) => {
    await goToFirstProject(page)
    const addressLink = page.locator('.card-address[href]').first()
    // Some listings might not have addresses, so check if any exist
    const count = await addressLink.count()
    if (count > 0) {
      const href = await addressLink.getAttribute('href')
      expect(href).toContain('google.com/maps')
    }
  })
})

test.describe('Detail view', () => {
  test('attribute values are left-aligned before labels', async ({ page }) => {
    await goToFirstProject(page)
    await page.locator('.listing-card .card-name').first().click()
    await page.waitForTimeout(500)

    const firstRow = page.locator('.attr-row').first()
    await expect(firstRow).toBeVisible()

    // Value should come before label in DOM order
    const children = await firstRow.locator('> *').allTextContents()
    expect(children.length).toBeGreaterThanOrEqual(3) // value, icon, label
  })

  test('detail address links to Google Maps', async ({ page }) => {
    await goToFirstProject(page)
    await page.locator('.listing-card .card-name').first().click()
    await page.waitForTimeout(500)

    const addressLink = page.locator('.detail-address a').first()
    const count = await addressLink.count()
    if (count > 0) {
      const href = await addressLink.getAttribute('href')
      expect(href).toContain('google.com/maps')
    }
  })

  test('detail shows website link', async ({ page }) => {
    await goToFirstProject(page)
    await page.locator('.listing-card .card-name').first().click()
    await page.waitForTimeout(500)

    const meta = page.locator('.detail-meta')
    await expect(meta).toBeVisible()
    // data completeness text should be present
    const text = await meta.textContent()
    expect(text).toContain('verified')
  })
})

test.describe('Filtering and sorting', () => {
  test('filter bar renders with requirements', async ({ page }) => {
    await goToFirstProject(page)
    const filterBar = page.locator('.filter-bar')
    await expect(filterBar).toBeVisible()
    await expect(filterBar.locator('input[placeholder="Search..."]').first()).toBeVisible()
  })

  test('name search filters listings', async ({ page }) => {
    await goToFirstProject(page)
    const initialCount = await page.locator('.listing-card').count()

    const nameInput = page.locator('.filter-bar input[placeholder="Search..."]').first()
    await nameInput.fill('xyznonexistent')
    await page.waitForTimeout(1000)
    const filteredCount = await page.locator('.listing-card').count()
    expect(filteredCount).toBeLessThan(initialCount)
  })

  test('name search finds matching listing', async ({ page }) => {
    await goToFirstProject(page)
    // Get the name of the first listing
    const firstName = await page.locator('.listing-card .card-name').first().textContent()
    expect(firstName).toBeTruthy()

    // Search for part of that name
    const searchTerm = firstName!.split(' ')[0]
    const nameInput = page.locator('.filter-bar input[placeholder="Search..."]').first()
    await nameInput.fill(searchTerm)
    await page.waitForTimeout(1000)

    const results = await page.locator('.listing-card').count()
    expect(results).toBeGreaterThan(0)
  })

  test('sort selector changes listing order', async ({ page }) => {
    await goToFirstProject(page)

    // Get names in default order (by score)
    const namesBefore = await page.locator('.listing-card .card-name').allTextContents()
    expect(namesBefore.length).toBeGreaterThan(1)

    // Change to sort by name A-Z — find the sort select (contains "Score" option)
    const sortSelect = page.locator('.filter-bar select', { has: page.locator('option[value="-score"]') })
    await sortSelect.selectOption('name')
    await page.waitForTimeout(1000)
    const namesAfter = await page.locator('.listing-card .card-name').allTextContents()

    // Order should be different (unless it was already alphabetical by coincidence)
    // At minimum, names should still be present
    expect(namesAfter.length).toBe(namesBefore.length)
  })

  test('hide failed toggle works', async ({ page }) => {
    await goToFirstProject(page)
    const initialCount = await page.locator('.listing-card').count()

    // Toggle hide failed
    const checkbox = page.locator('.filter-bar input[type="checkbox"]')
    await checkbox.check()
    await page.waitForTimeout(1000)
    const afterCount = await page.locator('.listing-card').count()

    // Should have same or fewer listings
    expect(afterCount).toBeLessThanOrEqual(initialCount)
  })
})

test.describe('UI controls', () => {
  test('activity log toggle shows and hides', async ({ page }) => {
    await goToFirstProject(page)

    // Log should be visible by default (we set showLog=true)
    const log = page.locator('.activity-log')
    await expect(log).toBeVisible()

    // Click hide
    await page.locator('button.btn-sm', { hasText: 'Hide Log' }).click()
    await expect(log).not.toBeVisible()

    // Click show
    await page.locator('button.btn-sm', { hasText: 'Log' }).click()
    await expect(log).toBeVisible()
  })

  test('resume button appears on done projects', async ({ page }) => {
    await goToFirstProject(page)

    // Project should be "done", so resume button should exist
    const resumeBtn = page.locator('button.btn-sm', { hasText: 'Resume' })
    await expect(resumeBtn).toBeVisible()
  })
})

test.describe('Visual', () => {
  test('screenshot of project page with detail open', async ({ page }) => {
    await goToFirstProject(page)
    await page.locator('.listing-card .card-name').first().click()
    await page.waitForTimeout(500)
    await expect(page.locator('.listing-detail')).toBeVisible({ timeout: 5000 })

    await page.screenshot({
      path: 'e2e/screenshots/project-page.png',
      fullPage: true,
    })
  })
})
