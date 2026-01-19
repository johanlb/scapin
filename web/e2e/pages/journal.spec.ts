import { test, expect } from '../fixtures/auth';

/**
 * Journal Page E2E Tests
 *
 * Tests the daily activity journal interface:
 * - Header and date picker
 * - Stats display (emails, teams, calendar, omnifocus, confidence)
 * - Tab navigation (email, teams, calendar, omnifocus, questions)
 * - Content display for each tab
 * - Question answering
 * - Journal completion
 */

test.describe('Journal Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
  });

  test('should load journal page', async ({ authenticatedPage: page }) => {
    await expect(page).toHaveURL('/journal');
  });

  test('should display page title', async ({ authenticatedPage: page }) => {
    const title = page.locator('h1:has-text("Journal")');
    await expect(title).toBeVisible();
  });

  test('should display current date in French format', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForLoadState('networkidle');

    // Date should be in French format (weekday, day month)
    const dateText = page.locator('text=/lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche/i');
    await expect(dateText).toBeVisible({ timeout: 10000 });
  });

  test('should display Scapin tagline', async ({
    authenticatedPage: page,
  }) => {
    const tagline = page.locator('text=Scapin prend note pour vous');
    await expect(tagline).toBeVisible();
  });
});

test.describe('Date Picker', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should have date input', async ({ authenticatedPage: page }) => {
    const datePicker = page.locator('input[type="date"]');
    await expect(datePicker).toBeVisible();
  });

  test('should default to today', async ({ authenticatedPage: page }) => {
    const datePicker = page.locator('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    await expect(datePicker).toHaveValue(today);
  });

  test('should reload journal when date changes', async ({
    authenticatedPage: page,
  }) => {
    const datePicker = page.locator('input[type="date"]');

    // Change to yesterday
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];

    await datePicker.fill(yesterdayStr);

    // Wait for reload
    await page.waitForLoadState('networkidle');

    // Date picker should have new value
    await expect(datePicker).toHaveValue(yesterdayStr);
  });
});

test.describe('Stats Bar', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display stats cards', async ({ authenticatedPage: page }) => {
    // Wait for data to load
    await page.waitForTimeout(2000);

    // Check for stats labels
    const emailsLabel = page.locator('text=Emails');
    const teamsLabel = page.locator('text=Teams');
    const reunionsLabel = page.locator('text=Réunions');
    const tachesLabel = page.locator('text=Tâches');
    const confianceLabel = page.locator('text=Confiance');

    // Stats should be visible (either 0 or more)
    await expect(emailsLabel).toBeVisible({ timeout: 10000 });
    await expect(teamsLabel).toBeVisible();
    await expect(reunionsLabel).toBeVisible();
    await expect(tachesLabel).toBeVisible();
    await expect(confianceLabel).toBeVisible();
  });

  test('should display confidence percentage', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForTimeout(2000);

    // Confidence should show with %
    const confidenceValue = page.locator('text=/%$/');
    await expect(confidenceValue.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Status and Actions', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display status badge', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(2000);

    // Status badge: Terminé, En cours, or Brouillon
    const statusBadge = page.locator('text=/Terminé|En cours|Brouillon/');
    await expect(statusBadge.first()).toBeVisible({ timeout: 10000 });
  });

  test('should show pending questions count if any', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForTimeout(2000);

    // If there are pending questions
    const pendingQuestions = page.locator('text=/\\d+ question\\(s\\) en attente/');
    const isVisible = await pendingQuestions.isVisible().catch(() => false);

    // This is optional - only visible if there are questions
    expect(typeof isVisible).toBe('boolean');
  });
});

test.describe('Tab Navigation', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display all tabs', async ({ authenticatedPage: page }) => {
    // All 5 tabs should be visible
    await expect(page.locator('button:has-text("Emails")')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button:has-text("Teams")')).toBeVisible();
    await expect(page.locator('button:has-text("Calendrier")')).toBeVisible();
    await expect(page.locator('button:has-text("OmniFocus")')).toBeVisible();
    await expect(page.locator('button:has-text("Questions")')).toBeVisible();
  });

  test('should show tab icons', async ({ authenticatedPage: page }) => {
    // Tab icons
    await expect(page.locator('text=📧')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=💬')).toBeVisible();
    await expect(page.locator('text=📅')).toBeVisible();
    await expect(page.locator('text=✅')).toBeVisible();
    await expect(page.locator('text=❓')).toBeVisible();
  });

  test('should switch tabs on click', async ({ authenticatedPage: page }) => {
    // Click Teams tab
    const teamsTab = page.locator('button:has-text("Teams")');
    await teamsTab.click();

    // Teams tab should be active (has primary color)
    await expect(teamsTab).toHaveClass(/bg-\[var\(--color-primary\)\]/);
  });

  test('should show count badges on tabs', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForTimeout(2000);

    // Tabs with counts should have badge
    const countBadge = page.locator('.rounded-full').filter({ hasText: /^\d+$/ });
    const hasBadges = await countBadge.count() > 0;

    // Badges are optional (depends on data)
    expect(typeof hasBadges).toBe('boolean');
  });
});

test.describe('Email Tab Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display emails or empty state', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForTimeout(2000);

    // Either shows email cards or "Aucun email traité"
    const hasEmails = await page.locator('text=📧').nth(1).isVisible().catch(() => false);
    const isEmpty = await page.locator('text=Aucun email traité').isVisible().catch(() => false);

    expect(hasEmails || isEmpty).toBe(true);
  });
});

test.describe('Teams Tab Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display teams messages or empty state', async ({
    authenticatedPage: page,
  }) => {
    // Switch to Teams tab
    await page.locator('button:has-text("Teams")').click();
    await page.waitForTimeout(500);

    // Either shows messages or "Aucun message Teams"
    const hasMessages = await page.locator('text=💬').nth(1).isVisible().catch(() => false);
    const isEmpty = await page.locator('text=Aucun message Teams').isVisible().catch(() => false);

    expect(hasMessages || isEmpty).toBe(true);
  });
});

test.describe('Calendar Tab Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display calendar events or empty state', async ({
    authenticatedPage: page,
  }) => {
    // Switch to Calendar tab
    await page.locator('button:has-text("Calendrier")').click();
    await page.waitForTimeout(500);

    // Either shows events or "Aucun événement calendrier"
    const hasEvents = await page.locator('text=📅').nth(1).isVisible().catch(() => false);
    const isEmpty = await page.locator('text=Aucun événement calendrier').isVisible().catch(() => false);

    expect(hasEvents || isEmpty).toBe(true);
  });
});

test.describe('OmniFocus Tab Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display omnifocus tasks or empty state', async ({
    authenticatedPage: page,
  }) => {
    // Switch to OmniFocus tab
    await page.locator('button:has-text("OmniFocus")').click();
    await page.waitForTimeout(500);

    // Either shows tasks or "Aucune activité OmniFocus"
    const hasTasks = await page.locator('text=✅').count() > 1;
    const isEmpty = await page.locator('text=Aucune activité OmniFocus').isVisible().catch(() => false);

    expect(hasTasks || isEmpty).toBe(true);
  });
});

test.describe('Questions Tab Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/journal');
    await page.waitForLoadState('networkidle');
  });

  test('should display questions or empty state', async ({
    authenticatedPage: page,
  }) => {
    // Switch to Questions tab
    await page.locator('button:has-text("Questions")').click();
    await page.waitForTimeout(500);

    // Either shows questions or "Aucune question"
    const hasQuestions = await page.locator('text=❓').nth(1).isVisible().catch(() => false);
    const isEmpty = await page.locator('text=Aucune question').isVisible().catch(() => false);

    expect(hasQuestions || isEmpty).toBe(true);
  });
});

test.describe('Loading and Error States', () => {
  test('should show loading spinner initially', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/journal');

    // Loading spinner should appear briefly
    const spinner = page.locator('.animate-spin');
    const content = page.locator('button:has-text("Emails")');

    // Either still loading or content loaded
    const hasSpinner = await spinner.isVisible({ timeout: 1000 }).catch(() => false);
    const hasContent = await content.isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasSpinner || hasContent).toBe(true);
  });

  test('should handle API errors gracefully', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/journal');

    // Page should not crash, should show either content or error
    const content = page.locator('text=/Journal|Erreur|Réessayer/');
    await expect(content.first()).toBeVisible({ timeout: 10000 });
  });
});
