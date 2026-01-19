import { test, expect } from '../fixtures/auth';

/**
 * Help Page E2E Tests
 *
 * Tests the help documentation interface:
 * - Section navigation
 * - Content display
 * - FAQ section
 * - Keyboard shortcuts documentation
 */

test.describe('Help Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/help');
  });

  test('should load help page', async ({ authenticatedPage: page }) => {
    await expect(page).toHaveURL('/help');
  });

  test('should display page title', async ({
    authenticatedPage: page,
  }) => {
    const title = page.locator('h1:has-text("Aide")');
    await expect(title).toBeVisible();
  });
});

test.describe('Help Sections', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/help');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display Getting Started section', async ({
    authenticatedPage: page,
  }) => {
    const section = page.locator('text=Démarrage Rapide');
    await expect(section).toBeVisible();
  });

  test('should display Briefing section', async ({
    authenticatedPage: page,
  }) => {
    const section = page.locator('h2:has-text("Briefing"), h3:has-text("Briefing")');
    await expect(section.first()).toBeVisible();
  });

  test('should display Flux section', async ({
    authenticatedPage: page,
  }) => {
    const section = page.locator('h2:has-text("Flux"), h3:has-text("Flux")');
    await expect(section.first()).toBeVisible();
  });

  test('should display Notes section', async ({
    authenticatedPage: page,
  }) => {
    const section = page.locator('h2:has-text("Notes"), h3:has-text("Notes")');
    await expect(section.first()).toBeVisible();
  });

  test('should display Journal section', async ({
    authenticatedPage: page,
  }) => {
    const section = page.locator('h2:has-text("Journal"), h3:has-text("Journal")');
    await expect(section.first()).toBeVisible();
  });

  test('should display Keyboard Shortcuts section', async ({
    authenticatedPage: page,
  }) => {
    const section = page.locator('text=Raccourcis Clavier');
    await expect(section).toBeVisible();
  });

  test('should display Architecture/Valets section', async ({
    authenticatedPage: page,
  }) => {
    // The section has title "Les Valets" and data-testid="help-section-architecture"
    const section = page.locator('[data-testid="help-section-architecture"], h2:has-text("Les Valets")');
    await expect(section.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Help Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/help');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display keyboard shortcuts info', async ({
    authenticatedPage: page,
  }) => {
    // Check for common shortcuts
    await expect(page.locator('text=Cmd+K')).toBeVisible();
    await expect(page.locator('text=Escape')).toBeVisible();
  });

  test('should display valet descriptions', async ({
    authenticatedPage: page,
  }) => {
    // Check for valet names
    const trivelin = page.locator('text=Trivelin');
    const sancho = page.locator('text=Sancho');
    const passepartout = page.locator('text=Passepartout');

    await expect(trivelin).toBeVisible();
    await expect(sancho).toBeVisible();
    await expect(passepartout).toBeVisible();
  });

  test('should display action instructions for Flux', async ({
    authenticatedPage: page,
  }) => {
    // Check for action instructions (use first() to avoid strict mode violations)
    await expect(page.locator('text=Approuver').first()).toBeVisible();
    await expect(page.locator('text=Rejeter').first()).toBeVisible();
  });
});

test.describe('FAQ Section', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/help');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display FAQ questions', async ({
    authenticatedPage: page,
  }) => {
    // Check for FAQ questions
    const faqQuestion = page.locator('text=/emails sont-ils traités automatiquement/');
    await expect(faqQuestion).toBeVisible();
  });

  test('should display FAQ about data security', async ({
    authenticatedPage: page,
  }) => {
    const securityQuestion = page.locator('text=/données sont-elles sécurisées/');
    await expect(securityQuestion).toBeVisible();
  });

  test('should display FAQ about undo', async ({
    authenticatedPage: page,
  }) => {
    const undoQuestion = page.locator('text=/annuler une action/');
    await expect(undoQuestion).toBeVisible();
  });
});

test.describe('Help Navigation', () => {
  test('should be accessible via direct navigation', async ({
    authenticatedPage: page,
  }) => {
    // Direct navigation to help page
    await page.goto('/help');
    await page.waitForLoadState('domcontentloaded');

    // Should show help content
    await expect(page.locator('h1:has-text("Aide")')).toBeVisible();
  });
});

test.describe('Help Accessibility', () => {
  test('should have main help sections', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/help');
    await page.waitForLoadState('domcontentloaded');

    // Check for main help sections (title-based, more stable than emoji)
    await expect(page.locator('text=Démarrage Rapide')).toBeVisible();
    await expect(page.locator('h2:has-text("Briefing"), h3:has-text("Briefing")').first()).toBeVisible();
    await expect(page.locator('h2:has-text("Flux"), h3:has-text("Flux")').first()).toBeVisible();
    await expect(page.locator('h2:has-text("Notes"), h3:has-text("Notes")').first()).toBeVisible();
  });
});
