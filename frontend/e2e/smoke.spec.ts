import { test, expect } from '@playwright/test'

test.describe('Smoke tests against running server', () => {
  test('project list page loads and shows projects', async ({ page }) => {
    await page.goto('/')
    // Should see the page header
    await expect(page.locator('h1')).toHaveText('Research Agent')
    // Should see at least one project card (we have data in the DB)
    const cards = page.locator('.project-card')
    await expect(cards.first()).toBeVisible({ timeout: 5000 })
  })

  test('clicking a project navigates to project page', async ({ page }) => {
    await page.goto('/')
    // Click the first project card
    const firstCard = page.locator('.project-card').first()
    await expect(firstCard).toBeVisible({ timeout: 5000 })
    await firstCard.click()

    // URL should change to /projects/<id>
    await expect(page).toHaveURL(/\/projects\/[a-f0-9]+/)

    // Project header should be visible with status and prompt
    await expect(page.locator('.project-header')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.header-prompt')).toBeVisible()
  })

  test('project page shows listings in left panel', async ({ page }) => {
    await page.goto('/')
    await page.locator('.project-card').first().click()
    await expect(page).toHaveURL(/\/projects\//)

    // Left panel should have listing cards
    const listingCards = page.locator('.listing-card')
    await expect(listingCards.first()).toBeVisible({ timeout: 10000 })

    // Should show at least one listing name
    const firstName = page.locator('.listing-card .card-name').first()
    await expect(firstName).toBeVisible()
    const nameText = await firstName.textContent()
    expect(nameText?.length).toBeGreaterThan(0)
  })

  test('clicking a listing shows detail on the right', async ({ page }) => {
    await page.goto('/')
    await page.locator('.project-card').first().click()

    // Wait for listings to load
    const firstCardName = page.locator('.listing-card .card-name').first()
    await expect(firstCardName).toBeVisible({ timeout: 10000 })

    // Click the card name to trigger selection
    await firstCardName.click()
    await page.waitForTimeout(500)

    // Right panel should now show detail
    const detail = page.locator('.listing-detail')
    await expect(detail).toBeVisible({ timeout: 5000 })

    // Should show the listing name as h2
    const detailName = detail.locator('h2')
    await expect(detailName).toBeVisible()
    const detailText = await detailName.textContent()
    expect(detailText?.length).toBeGreaterThan(0)

    // Should show the attribute grid
    await expect(detail.locator('.attribute-grid')).toBeVisible()

    // Should have at least one attribute row
    const attrRows = detail.locator('.attr-row')
    await expect(attrRows.first()).toBeVisible()
  })

  test('filter bar is visible with requirements', async ({ page }) => {
    await page.goto('/')
    await page.locator('.project-card').first().click()

    const filterBar = page.locator('.filter-bar')
    await expect(filterBar).toBeVisible({ timeout: 5000 })

    // Should have the name search input
    const nameInput = filterBar.locator('input[placeholder="Search..."]').first()
    await expect(nameInput).toBeVisible()
  })

  test('name search filters listings', async ({ page }) => {
    await page.goto('/')
    await page.locator('.project-card').first().click()

    // Wait for listings
    await expect(page.locator('.listing-card').first()).toBeVisible({ timeout: 10000 })
    const initialCount = await page.locator('.listing-card').count()

    // Type a search term that should filter
    const nameInput = page.locator('.filter-bar input[placeholder="Search..."]').first()
    await nameInput.fill('xyznonexistent')

    // Wait for the list to update
    await page.waitForTimeout(1000)
    const filteredCount = await page.locator('.listing-card').count()

    // Should have fewer (probably 0) results
    expect(filteredCount).toBeLessThan(initialCount)
  })

  test('direct navigation to project URL works (SPA routing)', async ({ page }) => {
    // First get a real project ID
    const response = await page.request.get('/api/projects')
    const projects = await response.json()
    expect(projects.length).toBeGreaterThan(0)
    const projectId = projects[0].id

    // Navigate directly to the project URL
    await page.goto(`/projects/${projectId}`)

    // Should render the project page, not a 404 or blank
    await expect(page.locator('.project-header')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.header-prompt')).toBeVisible()
  })

  test('take screenshot of project page for visual check', async ({ page }) => {
    await page.goto('/')
    await page.locator('.project-card').first().click()

    // Wait for full load
    await expect(page.locator('.listing-card .card-name').first()).toBeVisible({ timeout: 10000 })
    await page.locator('.listing-card .card-name').first().click()
    await page.waitForTimeout(500)
    await expect(page.locator('.listing-detail')).toBeVisible({ timeout: 5000 })

    // Screenshot for manual review
    await page.screenshot({
      path: 'e2e/screenshots/project-page.png',
      fullPage: true,
    })
  })
})
