/**
 * Test Data for Scapin E2E Tests
 *
 * These are mock data structures used in tests.
 * For Sprint 5, we use the real backend (no mocking),
 * but these types help with type safety in tests.
 */

export interface TestEmail {
  id: string;
  subject: string;
  from: string;
  preview: string;
  date: string;
  status: 'pending' | 'approved' | 'rejected';
}

export interface TestNote {
  path: string;
  title: string;
  content: string;
  type: 'PERSONNE' | 'PROJET' | 'CONCEPT' | 'SOUVENIR' | 'REFERENCE';
}

export interface TestDiscussion {
  id: string;
  title: string;
  messages: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
}

/**
 * Test selectors used across multiple tests
 */
export const SELECTORS = {
  // Layout
  sidebar: '[data-testid="sidebar"]',
  mobileNav: '[data-testid="mobile-nav"]',
  chatPanel: '[data-testid="chat-panel"]',

  // Auth
  pinPad: '[data-testid="pin-pad"]',
  pinDigit: (digit: string) => `[data-testid="pin-${digit}"]`,

  // Briefing
  briefingContent: '[data-testid="briefing-content"]',
  urgentItems: '[data-testid="urgent-items"]',
  quickActions: '[data-testid="quick-actions"]',

  // Flux
  fluxList: '[data-testid="flux-list"]',
  fluxItem: (id: string) => `[data-testid="flux-item-${id}"]`,
  approveButton: '[data-testid="approve-button"]',
  rejectButton: '[data-testid="reject-button"]',
  snoozeButton: '[data-testid="snooze-button"]',
  undoToast: '[data-testid^="undo-toast-"]',

  // Notes
  notesTree: '[data-testid="notes-tree"]',
  noteEditor: '[data-testid="note-editor"]',
  notePreview: '[data-testid="note-preview"]',
  noteHistory: '[data-testid="note-history"]',

  // Search
  commandPalette: '[data-testid="command-palette"]',
  searchInput: '[data-testid="search-input"]',
  searchResults: '[data-testid="search-results"]',

  // Notifications
  notificationsPanel: '[data-testid="notifications-panel"]',
  notificationBadge: '[data-testid="notification-badge"]',

  // Settings
  settingsTabs: '[data-testid="settings-tabs"]',
  settingsContent: '[data-testid="settings-content"]',
};

/**
 * Keyboard shortcuts for testing
 */
export const SHORTCUTS = {
  search: 'Meta+k',
  newNote: 'Meta+n',
  focus: 'Meta+f',
  help: '?',
  nextItem: 'j',
  prevItem: 'k',
  approve: 'a',
  reject: 'r',
  snooze: 's',
  edit: 'e',
  escape: 'Escape',
  enter: 'Enter',
};

/**
 * Wait for API response helper
 */
export async function waitForApiResponse(
  page: import('@playwright/test').Page,
  urlPattern: string | RegExp,
  timeout = 10000
): Promise<import('@playwright/test').Response> {
  return page.waitForResponse(
    (response) => {
      const url = response.url();
      if (typeof urlPattern === 'string') {
        return url.includes(urlPattern);
      }
      return urlPattern.test(url);
    },
    { timeout }
  );
}
