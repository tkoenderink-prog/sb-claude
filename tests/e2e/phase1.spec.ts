import { test, expect } from '@playwright/test';

test.describe('Phase 1: Walking Skeleton', () => {
  // Verify we're hitting the correct app before all tests
  test.beforeAll(async ({ request }) => {
    const response = await request.get('http://localhost:3000/api/identity');
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.app).toBe('second-brain-dashboard');
  });

  test('dashboard loads and shows health status', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Wait for the dashboard to load
    await expect(page.locator('h1')).toContainText('Second Brain Dashboard');

    // Check health indicator shows healthy
    await expect(page.locator('text=Healthy')).toBeVisible({ timeout: 10000 });
  });

  test('can trigger a job and see streamed logs', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Wait for dashboard to load and health check to complete
    await expect(page.locator('h1')).toContainText('Second Brain Dashboard');
    await expect(page.locator('text=Healthy')).toBeVisible({ timeout: 10000 });

    // Click the Run Job button
    await page.click('button:has-text("Run Job")');

    // Wait for log viewer section to appear (after mutation completes and activeJobId is set)
    await expect(page.locator('h2:has-text("Live Job Logs")')).toBeVisible({ timeout: 10000 });

    // Wait for log message to appear (note: backend sends "Initializing job..." with ellipsis)
    await expect(page.locator('text=Initializing job')).toBeVisible({ timeout: 10000 });

    // Wait for completion (use first() as there may be multiple elements)
    await expect(page.locator('text=Job completed successfully').first()).toBeVisible({ timeout: 15000 });
  });

  test('job history persists (jobs visible in list)', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Wait for dashboard to load and health check to complete
    await expect(page.locator('h1')).toContainText('Second Brain Dashboard');
    await expect(page.locator('text=Healthy')).toBeVisible({ timeout: 10000 });

    // Wait for job list to load - should show jobs from database
    await expect(page.locator('h2:has-text("Recent Jobs")')).toBeVisible();

    // Wait for jobs to load from API (need to wait for React Query to fetch)
    // At least one job should be visible with "processor" type
    await expect(page.locator('text=processor').first()).toBeVisible({ timeout: 15000 });

    // Job should show "succeeded" status from persistence
    await expect(page.locator('text=succeeded').first()).toBeVisible({ timeout: 10000 });
  });
});
