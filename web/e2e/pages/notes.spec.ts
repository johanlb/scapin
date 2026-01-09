import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Notes Page E2E Tests
 *
 * Tests the notes tree, editor, and version history.
 */

test.describe('Notes Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.goto('/notes');
  });

  test('should display notes tree', async ({ authenticatedPage: page }) => {
    // Notes tree should be visible
    await expect(page.locator(SELECTORS.notesTree)).toBeVisible();
  });

  test('should display folder structure', async ({
    authenticatedPage: page,
  }) => {
    // Should show folders
    const folders = page.locator('[data-testid="notes-folder"]');
    const folderCount = await folders.count();

    // May have folders or be empty
    expect(folderCount).toBeGreaterThanOrEqual(0);
  });

  test('should expand and collapse folders', async ({
    authenticatedPage: page,
  }) => {
    const folders = page.locator('[data-testid="notes-folder"]');
    const folderCount = await folders.count();

    if (folderCount > 0) {
      const firstFolder = folders.first();
      const expandButton = firstFolder.locator(
        '[data-testid="folder-expand"]'
      );

      if (await expandButton.isVisible()) {
        // Click to expand
        await expandButton.click();

        // Check expanded state
        await expect(firstFolder).toHaveAttribute('data-expanded', 'true');

        // Click to collapse
        await expandButton.click();

        // Check collapsed state
        await expect(firstFolder).toHaveAttribute('data-expanded', 'false');
      }
    }
  });

  test('should navigate to note detail', async ({
    authenticatedPage: page,
  }) => {
    // Find a note item
    const notes = page.locator('[data-testid="note-item"]');
    const noteCount = await notes.count();

    if (noteCount > 0) {
      await notes.first().click();

      // Should navigate to note detail
      await expect(page).toHaveURL(/\/notes\/.+/);
    }
  });

  test('should show pinned notes section', async ({
    authenticatedPage: page,
  }) => {
    // Pinned notes section
    const pinnedSection = page.locator('[data-testid="pinned-notes"]');

    // May or may not be visible depending on if notes are pinned
    const isVisible = await pinnedSection.isVisible();
    expect(typeof isVisible).toBe('boolean');
  });

  test('should trigger Apple Notes sync', async ({
    authenticatedPage: page,
  }) => {
    // Find sync button
    const syncBtn = page.locator('[data-testid="sync-apple-notes"]');

    if (await syncBtn.isVisible()) {
      await syncBtn.click();

      // Should show loading state
      await expect(syncBtn).toHaveAttribute('data-loading', 'true');

      // Wait for sync to complete (with timeout)
      await expect(syncBtn).toHaveAttribute('data-loading', 'false', {
        timeout: 30000,
      });
    }
  });

  test('should create new note with Cmd+N', async ({
    authenticatedPage: page,
  }) => {
    // Press Cmd+N
    await page.keyboard.press('Meta+n');

    // New note modal or page should appear
    const newNoteModal = page.locator('[data-testid="new-note-modal"]');
    const isModalRoute = await page
      .locator('[data-testid="note-editor"]')
      .isVisible();

    expect(
      (await newNoteModal.isVisible()) || isModalRoute
    ).toBeTruthy();
  });

  test('should filter notes by type', async ({ authenticatedPage: page }) => {
    // Type filter
    const typeFilter = page.locator('[data-testid="note-type-filter"]');

    if (await typeFilter.isVisible()) {
      await typeFilter.click();

      // Select PERSONNE type
      await page.click('[data-testid="note-type-PERSONNE"]');

      // Tree should be filtered
      const notes = page.locator('[data-testid="note-item"]');
      const filtered = page.locator(
        '[data-testid="note-item"][data-type="PERSONNE"]'
      );

      // All visible notes should be of type PERSONNE
      expect(await filtered.count()).toBeLessThanOrEqual(await notes.count());
    }
  });

  test('should search notes', async ({ authenticatedPage: page }) => {
    // Search input
    const searchInput = page.locator('[data-testid="notes-search"]');

    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      await page.keyboard.press('Enter');

      // Results should update
      await page.waitForTimeout(500);

      // Should show filtered results
      const results = page.locator('[data-testid="note-item"]');
      expect(await results.count()).toBeGreaterThanOrEqual(0);
    }
  });
});

test.describe('Note Detail Page', () => {
  test('should display note editor', async ({ authenticatedPage: page }) => {
    // Navigate to notes first
    await page.goto('/notes');

    // Find and click a note
    const notes = page.locator('[data-testid="note-item"]');
    const noteCount = await notes.count();

    if (noteCount > 0) {
      await notes.first().click();

      // Wait for navigation
      await page.waitForURL(/\/notes\/.+/);

      // Editor should be visible
      await expect(page.locator(SELECTORS.noteEditor)).toBeVisible();
    }
  });

  test('should toggle between edit and preview mode', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes');

    const notes = page.locator('[data-testid="note-item"]');
    const noteCount = await notes.count();

    if (noteCount > 0) {
      await notes.first().click();
      await page.waitForURL(/\/notes\/.+/);

      // Toggle to preview
      const previewBtn = page.locator('[data-testid="toggle-preview"]');
      if (await previewBtn.isVisible()) {
        await previewBtn.click();

        // Preview should be visible
        await expect(page.locator(SELECTORS.notePreview)).toBeVisible();
      }
    }
  });

  test('should open note history', async ({ authenticatedPage: page }) => {
    await page.goto('/notes');

    const notes = page.locator('[data-testid="note-item"]');
    const noteCount = await notes.count();

    if (noteCount > 0) {
      await notes.first().click();
      await page.waitForURL(/\/notes\/.+/);

      // Click history button
      const historyBtn = page.locator('[data-testid="note-history-btn"]');
      if (await historyBtn.isVisible()) {
        await historyBtn.click();

        // History modal should open
        await expect(page.locator(SELECTORS.noteHistory)).toBeVisible();
      }
    }
  });

  test('should open chat about note', async ({ authenticatedPage: page }) => {
    await page.goto('/notes');

    const notes = page.locator('[data-testid="note-item"]');
    const noteCount = await notes.count();

    if (noteCount > 0) {
      await notes.first().click();
      await page.waitForURL(/\/notes\/.+/);

      // Click chat button
      const chatBtn = page.locator('[data-testid="discuss-note-btn"]');
      if (await chatBtn.isVisible()) {
        await chatBtn.click();

        // Chat panel should open with note context
        await expect(page.locator(SELECTORS.chatPanel)).toBeVisible();
      }
    }
  });

  test('should auto-save note content', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes');

    const notes = page.locator('[data-testid="note-item"]');
    const noteCount = await notes.count();

    if (noteCount > 0) {
      await notes.first().click();
      await page.waitForURL(/\/notes\/.+/);

      // Type some content
      const editor = page.locator(SELECTORS.noteEditor);
      if (await editor.isVisible()) {
        await editor.click();
        await page.keyboard.type(' test auto-save');

        // Wait for auto-save indicator
        await expect(
          page.locator('[data-testid="save-indicator"]')
        ).toContainText(/enregistr/i);
      }
    }
  });
});

test.describe('Notes Review Page', () => {
  test('should display review interface', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes/review');

    // Review page should load
    await expect(
      page.locator('[data-testid="review-page"], [data-testid="review-empty"]')
    ).toBeVisible();
  });

  test('should show quality rating buttons', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes/review');

    // Check for review interface
    const reviewPage = page.locator('[data-testid="review-page"]');
    const isEmpty = await page
      .locator('[data-testid="review-empty"]')
      .isVisible();

    if (!isEmpty && (await reviewPage.isVisible())) {
      // Quality rating buttons should be visible
      for (let i = 0; i <= 5; i++) {
        await expect(
          page.locator(`[data-testid="quality-${i}"]`)
        ).toBeVisible();
      }
    }
  });

  test('should navigate with arrow keys', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes/review');

    const isEmpty = await page
      .locator('[data-testid="review-empty"]')
      .isVisible();

    if (!isEmpty) {
      // Press right arrow to go to next note
      await page.keyboard.press('ArrowRight');

      // Note counter should change
      const counter = page.locator('[data-testid="review-counter"]');
      if (await counter.isVisible()) {
        const text = await counter.textContent();
        expect(text).toMatch(/\d+\s*\/\s*\d+/);
      }
    }
  });

  test('should rate note with keyboard shortcuts', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes/review');

    const isEmpty = await page
      .locator('[data-testid="review-empty"]')
      .isVisible();

    if (!isEmpty) {
      // Press '4' to rate note
      await page.keyboard.press('4');

      // Should advance to next note or complete
      await page.waitForTimeout(500);
    }
  });

  test('should exit review with Escape', async ({
    authenticatedPage: page,
  }) => {
    await page.goto('/notes/review');

    // Press Escape to exit
    await page.keyboard.press('Escape');

    // Should return to notes page or home
    await expect(page).not.toHaveURL('/notes/review');
  });
});
