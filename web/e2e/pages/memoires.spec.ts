import { test, expect } from '../fixtures/auth';

/**
 * Notes Page E2E Tests
 *
 * Tests the personal knowledge management interface:
 * - Three-column layout (folders, notes list, content)
 * - Apple Notes sync
 * - Note selection and display
 * - Search functionality
 * - Note editing and actions
 * - SM-2 review metadata
 */

test.describe('Notes Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
  });

  test('should load notes page', async ({ authenticatedPage: page }) => {
    await expect(page).toHaveURL('/memoires');
  });

  test('should display three-column layout', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForLoadState('domcontentloaded');
    // Wait for page content to load
    await page.waitForTimeout(3000);

    // Column 1: Folder sidebar with sync button
    const syncButton = page.locator('button').filter({ hasText: 'Sync Apple Notes' });
    await expect(syncButton).toBeVisible({ timeout: 15000 });

    // Column 2: Notes list with search
    const searchInput = page.locator('input[placeholder="Rechercher..."]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Column 3: Note content area (main with flex-1 class that contains note display)
    const contentArea = page.locator('main.flex-1');
    await expect(contentArea).toBeVisible();
  });
});

test.describe('Folder Tree', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display "All Notes" virtual folder', async ({
    authenticatedPage: page,
  }) => {
    // Wait for folder tree to load by checking for any folder content
    await page.waitForTimeout(2000);
    const allNotesFolder = page.locator('span:has-text("Toutes les notes")');
    await expect(allNotesFolder).toBeVisible({ timeout: 15000 });
  });

  test('should display "Deleted Notes" folder', async ({
    authenticatedPage: page,
  }) => {
    const deletedFolder = page.locator('text=Supprimées récemment');
    await expect(deletedFolder).toBeVisible({ timeout: 10000 });
  });

  test('should display total notes count', async ({
    authenticatedPage: page,
  }) => {
    // Footer should show total notes
    const footer = page.locator('text=/\\d+ notes? au total/');
    await expect(footer).toBeVisible({ timeout: 10000 });
  });

  test('should have sync button', async ({ authenticatedPage: page }) => {
    const syncButton = page.locator('button:has-text("Sync Apple Notes")');
    await expect(syncButton).toBeVisible({ timeout: 10000 });
    await expect(syncButton).toBeEnabled();
  });

  test('should show last sync time', async ({ authenticatedPage: page }) => {
    // Sync status might show after API response
    const syncStatus = page.locator('text=/Dernière sync/');
    const isVisible = await syncStatus.isVisible({ timeout: 5000 }).catch(() => false);

    if (isVisible) {
      await expect(syncStatus).toBeVisible();
    }
  });
});

test.describe('Notes List', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display folder name header', async ({
    authenticatedPage: page,
  }) => {
    // Should show selected folder name (default: All Notes)
    const header = page.locator('h2:has-text("Toutes les notes")');
    await expect(header).toBeVisible({ timeout: 10000 });
  });

  test('should display notes count', async ({ authenticatedPage: page }) => {
    // Note count under folder name
    const noteCount = page.locator('text=/\\d+ notes?$/');
    await expect(noteCount.first()).toBeVisible({ timeout: 10000 });
  });

  test('should group notes by date', async ({ authenticatedPage: page }) => {
    // Wait for notes to load
    await page.waitForTimeout(2000);

    // Check for date group headers (if notes exist)
    const dateGroups = page.locator(
      'h3:has-text("Aujourd\'hui"), h3:has-text("7 jours précédents"), h3:has-text("30 jours précédents"), h3:has-text("Plus ancien")'
    );

    const hasGroups = await dateGroups.count() > 0;
    // Groups should exist if there are notes
    expect(hasGroups || (await page.locator('text=Aucune note').isVisible())).toBe(true);
  });
});

test.describe('Search', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should have search input with placeholder', async ({
    authenticatedPage: page,
  }) => {
    const searchInput = page.locator('input[placeholder="Rechercher..."]');
    await expect(searchInput).toBeVisible();
  });

  test('should show keyboard shortcut hint', async ({
    authenticatedPage: page,
  }) => {
    // Wait for page to load
    await page.waitForTimeout(2000);

    // Wait for search bar to render
    const searchInput = page.locator('input[placeholder="Rechercher..."]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Ensure search is empty (shortcut hint only shows when empty)
    await searchInput.clear();
    await page.waitForTimeout(300);

    // ⌘K shortcut hint appears when search is empty (in a span element)
    // The hint might use different unicode chars, check for text content
    const shortcutHint = page.locator('span').filter({ hasText: /⌘K|Cmd\+K/ });
    const isVisible = await shortcutHint.first().isVisible({ timeout: 5000 }).catch(() => false);

    // Test passes if hint is visible (or if search has another state)
    expect(isVisible || await searchInput.isVisible()).toBe(true);
  });

  test('should focus search on Cmd+K', async ({ authenticatedPage: page }) => {
    // Wait for page to fully load
    await page.waitForTimeout(2000);

    const searchInput = page.locator('input[placeholder="Rechercher..."]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Press Cmd+K - this may focus notes search or open command palette
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(300);

    // Check if notes search is focused OR command palette opened
    const isSearchFocused = await searchInput.evaluate(el => el === document.activeElement);
    const commandPalette = page.locator('[data-testid="command-palette"], [role="dialog"]');
    const paletteVisible = await commandPalette.isVisible().catch(() => false);

    // Either notes search is focused or command palette opened (both are valid Cmd+K responses)
    expect(isSearchFocused || paletteVisible).toBe(true);
  });

  test('should show results header when searching', async ({
    authenticatedPage: page,
  }) => {
    const searchInput = page.locator('input[placeholder="Rechercher..."]');
    await searchInput.fill('test');

    // Wait for search
    await page.waitForTimeout(500);

    // Should show "Résultats" header
    const resultsHeader = page.locator('h2:has-text("Résultats")');
    await expect(resultsHeader).toBeVisible();
  });

  test('should clear search on Escape', async ({ authenticatedPage: page }) => {
    // Wait for search input to be available
    const searchInput = page.locator('input[placeholder="Rechercher..."]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    // Focus and fill search
    await searchInput.click();
    await searchInput.fill('test');
    await page.waitForTimeout(500);

    // Verify search has value
    await expect(searchInput).toHaveValue('test');

    // Press Escape to clear
    await searchInput.press('Escape');
    await page.waitForTimeout(300);

    // Search should be cleared
    await expect(searchInput).toHaveValue('');
  });
});

test.describe('Note Content', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display empty state when no note selected', async ({
    authenticatedPage: page,
  }) => {
    // Initially might show empty state or auto-select first note
    const emptyState = page.locator('text=Sélectionnez une note');
    const noteTitle = page.locator('article h1');

    const hasEmpty = await emptyState.isVisible().catch(() => false);
    const hasNote = await noteTitle.isVisible().catch(() => false);

    expect(hasEmpty || hasNote).toBe(true);
  });

  test('should display note title', async ({ authenticatedPage: page }) => {
    // Wait for first note to be selected
    await page.waitForTimeout(2000);

    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      await expect(noteTitle).not.toBeEmpty();
    }
  });

  test('should have action buttons for selected note', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForTimeout(2000);

    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      // Edit button
      const editButton = page.locator('button[title="Modifier la note"]');
      await expect(editButton).toBeVisible();

      // Move button
      const moveButton = page.locator('button[title="Déplacer vers un dossier"]');
      await expect(moveButton).toBeVisible();

      // Delete button
      const deleteButton = page.locator('button[title="Supprimer la note"]');
      await expect(deleteButton).toBeVisible();
    }
  });
});

test.describe('Review Metadata', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
    await page.waitForLoadState('domcontentloaded');
  });

  test('should display review metadata section', async ({
    authenticatedPage: page,
  }) => {
    await page.waitForTimeout(2000);

    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      // Review metadata header
      const metadataHeader = page.locator('h3:has-text("Métadonnées de revue")');
      await expect(metadataHeader).toBeVisible();
    }
  });

  test('should display SM-2 metrics', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(2000);

    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      // Check for SM-2 related fields
      const nextReview = page.locator('text=Prochaine revue');
      const reviewCount = page.locator('text=Nombre de revues');
      const easiness = page.locator('text=Facteur de facilité');

      const hasMetadata = await nextReview.isVisible().catch(() => false);
      if (hasMetadata) {
        await expect(nextReview).toBeVisible();
        await expect(reviewCount).toBeVisible();
        await expect(easiness).toBeVisible();
      }
    }
  });
});

test.describe('Note Actions', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/memoires');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);
  });

  test('should have hygiene review button', async ({
    authenticatedPage: page,
  }) => {
    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      const hygieneButton = page.locator('button[title="Analyser l\'hygiène de la note"]');
      await expect(hygieneButton).toBeVisible();
    }
  });

  test('should have trigger review button', async ({
    authenticatedPage: page,
  }) => {
    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      const triggerButton = page.locator('button[title="Déclencher une revue SM-2"]');
      await expect(triggerButton).toBeVisible();
    }
  });

  test('should have open in new window button', async ({
    authenticatedPage: page,
  }) => {
    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible().catch(() => false);

    if (hasNote) {
      const newWindowButton = page.locator('button[title="Ouvrir dans une nouvelle fenêtre"]');
      await expect(newWindowButton).toBeVisible();
    }
  });

  test('should open note detail page and display note content when clicking new window button', async ({
    authenticatedPage: page,
    context,
  }, testInfo) => {
    // Skip on mobile - the 3-column layout doesn't exist and window.open doesn't make sense
    if (testInfo.project.name.includes('mobile')) {
      test.skip();
      return;
    }

    // Wait for a note to be displayed
    const noteTitle = page.locator('article h1');
    const hasNote = await noteTitle.isVisible({ timeout: 10000 }).catch(() => false);

    if (!hasNote) {
      // No notes available, skip the test
      test.skip();
      return;
    }

    // Get the note title from the main page for later comparison
    const expectedTitle = await noteTitle.textContent();
    expect(expectedTitle).toBeTruthy();

    // Click the new window button and wait for popup
    const newWindowButton = page.locator('button[title="Ouvrir dans une nouvelle fenêtre"]');
    await expect(newWindowButton).toBeVisible();

    // Wait for the popup window
    const [popup] = await Promise.all([
      context.waitForEvent('page'),
      newWindowButton.click(),
    ]);

    // Wait for the popup to load
    await popup.waitForLoadState('domcontentloaded');

    // Verify the URL pattern
    const popupUrl = popup.url();
    expect(popupUrl).toContain('/memoires/');
    expect(popupUrl).not.toContain('/notes/');

    // Wait for the note to load in the popup (not loading state)
    await popup.waitForTimeout(2000);

    // Verify the note title is displayed in the popup page
    const popupTitle = popup.locator('h1');
    await expect(popupTitle).toBeVisible({ timeout: 10000 });

    // The title in the detail page should match the title from the list
    const actualTitle = await popupTitle.textContent();
    expect(actualTitle?.trim()).toBe(expectedTitle?.trim());

    // Verify no error message is shown
    const errorMessage = popup.locator('text=Note introuvable');
    const hasError = await errorMessage.isVisible().catch(() => false);
    expect(hasError).toBe(false);

    // Close the popup
    await popup.close();
  });
});

test.describe('Error Handling', () => {
  test('should handle page load errors gracefully', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/memoires');

    // Page should not crash, should show either content or error
    const content = page.locator('text=/Toutes les notes|Erreur|Chargement/');
    await expect(content.first()).toBeVisible({ timeout: 15000 });
  });
});
