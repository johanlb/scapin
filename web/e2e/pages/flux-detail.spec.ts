import { test, expect } from '../fixtures/auth';
import { SELECTORS } from '../fixtures/test-data';

/**
 * Flux Detail Page E2E Tests
 *
 * Tests the flux item detail page, including the multi-pass analysis section (v2.3).
 * These tests require actual queue items in the database.
 */

test.describe('Flux Detail Page', () => {
  test.describe('Multi-Pass Analysis Section', () => {
    test('should display multi-pass section or legacy fallback', async ({ authenticatedPage: page }) => {
      // Navigate to flux list first
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });

      // Wait for the list to load
      await page.waitForTimeout(2000);

      // Try to find and click on a flux item to navigate to detail
      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        // Click the first item
        await fluxItems.first().click();

        // Wait for detail page to load
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });

        // Wait for content to render
        await page.waitForTimeout(1500);

        // Should display either multi-pass section or legacy fallback
        const multiPassSection = page.locator(SELECTORS.multiPassSection);
        const legacySection = page.locator(SELECTORS.multiPassLegacy);

        const hasMultiPass = await multiPassSection.isVisible();
        const hasLegacy = await legacySection.isVisible();

        // One of these should be visible
        expect(hasMultiPass || hasLegacy).toBeTruthy();
      } else {
        // No items in queue, skip test
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should display multi-pass summary with passes count and models', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          // Check summary elements
          const summary = page.locator(SELECTORS.multiPassSummary);
          await expect(summary).toBeVisible();

          // Passes count should be visible
          const passesCount = page.locator(SELECTORS.multiPassPassesCount);
          await expect(passesCount).toBeVisible();
          const passesText = await passesCount.textContent();
          expect(passesText).toMatch(/\d+ pass(es)?/);

          // Models should be visible
          const models = page.locator(SELECTORS.multiPassModels);
          await expect(models).toBeVisible();
          const modelsText = await models.textContent();
          // Should contain model names (haiku, sonnet, or opus)
          expect(modelsText?.toLowerCase()).toMatch(/haiku|sonnet|opus/);

          // Duration should be visible
          const duration = page.locator(SELECTORS.multiPassDuration);
          await expect(duration).toBeVisible();
          const durationText = await duration.textContent();
          expect(durationText).toMatch(/\d+(\.\d+)?s/);
        } else {
          // Legacy item, skip detailed checks
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should expand details section to show pass history', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          // Find the details element
          const details = page.locator(SELECTORS.multiPassDetails);
          await expect(details).toBeVisible();

          // Click to expand
          const summary = details.locator('summary');
          await summary.click();

          // Wait for expansion
          await page.waitForTimeout(300);

          // Pass history should now be visible
          const passHistory = page.locator(SELECTORS.multiPassPassHistory);
          await expect(passHistory).toBeVisible();

          // Should contain at least one pass entry
          const passEntries = passHistory.locator('[data-testid^="multipass-pass-"]');
          const passCount = await passEntries.count();
          expect(passCount).toBeGreaterThanOrEqual(1);
        } else {
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should have proper tooltips on multi-pass elements', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          // Check tooltips (title attributes)
          const passesCount = page.locator(SELECTORS.multiPassPassesCount);
          const passesTooltip = await passesCount.getAttribute('title');
          expect(passesTooltip).toBeTruthy();
          expect(passesTooltip).toContain('passe');

          const models = page.locator(SELECTORS.multiPassModels);
          const modelsTooltip = await models.getAttribute('title');
          expect(modelsTooltip).toBeTruthy();
          expect(modelsTooltip).toContain('modèle');

          const duration = page.locator(SELECTORS.multiPassDuration);
          const durationTooltip = await duration.getAttribute('title');
          expect(durationTooltip).toBeTruthy();
        } else {
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should display stop reason when available', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          const stopReason = page.locator(SELECTORS.multiPassStopReason);

          if (await stopReason.isVisible()) {
            const stopReasonText = await stopReason.textContent();
            expect(stopReasonText).toContain('Arrêt');
            // Should display a translated reason
            expect(stopReasonText).toMatch(/Confiance suffisante|Maximum de passes|Pas de changement|confidence/i);
          }
          // Stop reason is optional, so we don't fail if not present
        } else {
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should display escalation badge when escalated', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      // Look for any flux item that might have been escalated
      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      // Test all items to find one with escalation
      let foundEscalated = false;
      for (let i = 0; i < Math.min(itemCount, 5); i++) {
        await page.goto('/flux', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1000);

        const items = page.locator('[data-testid^="flux-item-"]');
        await items.nth(i).click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1000);

        const escalatedBadge = page.locator(SELECTORS.multiPassEscalated);
        if (await escalatedBadge.isVisible()) {
          foundEscalated = true;
          const badgeText = await escalatedBadge.textContent();
          expect(badgeText).toContain('Escalade');
          break;
        }
      }

      // This test passes even if no escalated items found (behavior is correct)
      // We just want to verify the badge works when present
    });

    test('should display legacy fallback for old items', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      // Look for any item without multi-pass metadata
      for (let i = 0; i < Math.min(itemCount, 5); i++) {
        await page.goto('/flux', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1000);

        const items = page.locator('[data-testid^="flux-item-"]');
        await items.nth(i).click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1000);

        const legacySection = page.locator(SELECTORS.multiPassLegacy);
        if (await legacySection.isVisible()) {
          const legacyText = await legacySection.textContent();
          expect(legacyText).toContain('legacy');

          // Should have tooltip
          const tooltip = await legacySection.locator('span').getAttribute('title');
          expect(tooltip).toBeTruthy();
          expect(tooltip).toContain('version antérieure');
          return;
        }
      }

      // No legacy items found is also valid (all items have multi-pass)
    });
  });

  test.describe('Pass Timeline (v2.3.1)', () => {
    test('should display timeline with passes when expanded', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          // Expand the details
          const details = page.locator(SELECTORS.multiPassDetails);
          const summary = details.locator('summary');
          await summary.click();
          await page.waitForTimeout(300);

          // Timeline should be visible
          const timeline = page.locator(SELECTORS.passTimeline);
          await expect(timeline).toBeVisible();

          // Should have at least one pass entry
          const passEntries = timeline.locator('[data-testid^="timeline-pass-"]');
          const passCount = await passEntries.count();
          expect(passCount).toBeGreaterThanOrEqual(1);
        } else {
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should display proper badges in timeline passes', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          // Expand the details
          const details = page.locator(SELECTORS.multiPassDetails);
          const summary = details.locator('summary');
          await summary.click();
          await page.waitForTimeout(300);

          // Check for context badges
          const contextBadges = page.locator(SELECTORS.timelineContextBadge);
          const contextCount = await contextBadges.count();

          // If context badges exist, verify they have tooltips
          if (contextCount > 0) {
            const tooltip = await contextBadges.first().getAttribute('title');
            expect(tooltip).toBeTruthy();
            expect(tooltip).toContain('contexte');
          }

          // Check for escalation badges
          const escalationBadges = page.locator(SELECTORS.timelineEscalationBadge);
          const escalationCount = await escalationBadges.count();

          if (escalationCount > 0) {
            const tooltip = await escalationBadges.first().getAttribute('title');
            expect(tooltip).toBeTruthy();
            expect(tooltip).toContain('escalade');
          }
        } else {
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });

    test('should display Thinking Bubbles when AI had questions', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      // Check multiple items to find one with questions
      for (let i = 0; i < Math.min(itemCount, 5); i++) {
        await page.goto('/flux', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1000);

        const items = page.locator('[data-testid^="flux-item-"]');
        await items.nth(i).click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1000);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);
        if (!(await multiPassSection.isVisible())) continue;

        // Expand the details
        const details = page.locator(SELECTORS.multiPassDetails);
        const summary = details.locator('summary');
        await summary.click();
        await page.waitForTimeout(300);

        // Look for thinking badges
        const thinkingBadges = page.locator(SELECTORS.timelineThinkingBadge);
        if ((await thinkingBadges.count()) > 0) {
          // Verify badge has proper tooltip
          const tooltip = await thinkingBadges.first().getAttribute('title');
          expect(tooltip).toBeTruthy();
          expect(tooltip).toContain('question');

          // Check for questions section
          const questionsSection = page.locator(SELECTORS.timelineQuestions);
          if (await questionsSection.isVisible()) {
            // Should display questions list
            const questionItems = questionsSection.locator('li');
            const questionCount = await questionItems.count();
            expect(questionCount).toBeGreaterThanOrEqual(1);
          }
          return; // Found one, test passes
        }
      }

      // No items with questions is also valid (depends on data)
    });

    test('should display confidence sparkline in summary', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      if (itemCount > 0) {
        await fluxItems.first().click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1500);

        const multiPassSection = page.locator(SELECTORS.multiPassSection);

        if (await multiPassSection.isVisible()) {
          // Sparkline should be visible in summary
          const sparkline = page.locator(SELECTORS.confidenceSparkline);
          await expect(sparkline).toBeVisible();

          // Should be an SVG element
          const tagName = await sparkline.evaluate(el => el.tagName.toLowerCase());
          expect(tagName).toBe('svg');

          // Should have accessible title
          const title = sparkline.locator('title');
          await expect(title).toHaveText(/Confiance.*→/);
        } else {
          test.skip(true, 'Item does not have multi-pass metadata');
        }
      } else {
        test.skip(true, 'No flux items available for testing');
      }
    });
  });

  test.describe('Why Not Section (v2.3.1)', () => {
    test('should display rejection reasons on non-recommended options', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      // Check multiple items to find one with rejection reasons
      for (let i = 0; i < Math.min(itemCount, 5); i++) {
        await page.goto('/flux', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1000);

        const items = page.locator('[data-testid^="flux-item-"]');
        await items.nth(i).click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1000);

        // Look for rejection reasons inline
        const rejectionReasons = page.locator(SELECTORS.optionRejectionReason);
        if ((await rejectionReasons.count()) > 0) {
          // Verify tooltip
          const tooltip = await rejectionReasons.first().getAttribute('title');
          expect(tooltip).toBeTruthy();
          expect(tooltip).toContain('recommand');
          return; // Found one, test passes
        }
      }

      // No items with rejection reasons is valid (depends on AI responses)
    });

    test('should display Why Not collapsible section when available', async ({ authenticatedPage: page }) => {
      await page.goto('/flux', { waitUntil: 'domcontentloaded' });
      await expect(page).toHaveURL('/flux', { timeout: 45000 });
      await page.waitForTimeout(2000);

      const fluxItems = page.locator('[data-testid^="flux-item-"]');
      const itemCount = await fluxItems.count();

      // Check multiple items to find one with Why Not section
      for (let i = 0; i < Math.min(itemCount, 5); i++) {
        await page.goto('/flux', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(1000);

        const items = page.locator('[data-testid^="flux-item-"]');
        await items.nth(i).click();
        await page.waitForURL(/\/flux\/[^/]+/, { timeout: 10000 });
        await page.waitForTimeout(1000);

        // Look for Why Not section
        const whyNotSection = page.locator(SELECTORS.whyNotSection);
        if (await whyNotSection.isVisible()) {
          // Expand the section
          const summary = whyNotSection.locator('summary');
          await expect(summary).toContainText('Pourquoi pas');
          await summary.click();
          await page.waitForTimeout(300);

          // Should have items listed
          const whyNotItems = page.locator(SELECTORS.whyNotItem);
          const count = await whyNotItems.count();
          expect(count).toBeGreaterThanOrEqual(1);
          return; // Found one, test passes
        }
      }

      // No items with Why Not section is valid (depends on AI responses)
    });
  });
});
