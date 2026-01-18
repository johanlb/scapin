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
  pinInput: '[data-testid="pin-input"]',
  loginSubmit: '[data-testid="login-submit"]',
  pinPad: '[data-testid="pin-pad"]',
  pinDigit: (digit: string) => `[data-testid="pin-${digit}"]`,

  // Briefing
  briefingContent: '[data-testid="briefing-content"]',
  urgentItems: '[data-testid="urgent-items"]',
  notesReviewWidget: '[data-testid="notes-review-widget"]',

  // Flux
  fluxList: '[data-testid="flux-list"]',
  fluxItem: (id: string) => `[data-testid="flux-item-${id}"]`,
  approveButton: '[data-testid="approve-button"]',
  rejectButton: '[data-testid="reject-button"]',
  snoozeButton: '[data-testid="snooze-button"]',
  undoToast: '[data-testid^="undo-toast-"]',

  // Flux Tabs
  fluxTabPending: '[data-testid="flux-tab-pending"]',
  fluxTabApproved: '[data-testid="flux-tab-approved"]',
  fluxTabRejected: '[data-testid="flux-tab-rejected"]',
  fluxTabError: '[data-testid="flux-tab-error"]',

  // Flux Filters (SC-15)
  fluxFilterAll: '[data-testid="flux-filter-all"]',
  fluxFilterAuto: '[data-testid="flux-filter-auto"]',
  fluxFilterUser: '[data-testid="flux-filter-user"]',

  // Flux Error Actions (SC-16)
  retryButton: '[data-testid="retry-button"]',
  dismissButton: '[data-testid="dismiss-button"]',
  moveToReviewButton: '[data-testid="move-to-review-button"]',
  errorBadge: '[data-testid="error-badge"]',
  errorMessage: '[data-testid="error-message"]',
  attemptCount: '[data-testid="attempt-count"]',

  // Flux Re-analyze (SC-18)
  reanalyzeButton: '[data-testid="reanalyze-button"]',

  // Flux Detail - Multi-Pass Analysis (v2.3)
  multiPassSection: '[data-testid="multipass-section"]',
  multiPassSummary: '[data-testid="multipass-summary"]',
  multiPassPassesCount: '[data-testid="multipass-passes-count"]',
  multiPassModels: '[data-testid="multipass-models"]',
  multiPassDuration: '[data-testid="multipass-duration"]',
  multiPassEscalated: '[data-testid="multipass-escalated"]',
  multiPassHighStakes: '[data-testid="multipass-high-stakes"]',
  multiPassStopReason: '[data-testid="multipass-stop-reason"]',
  multiPassDetails: '[data-testid="multipass-details"]',
  multiPassPassHistory: '[data-testid="multipass-pass-history"]',
  multiPassLegacy: '[data-testid="multipass-legacy"]',

  // Pass Timeline (v2.3.1)
  passTimeline: '[data-testid="pass-timeline"]',
  timelinePass: (n: number) => `[data-testid="timeline-pass-${n}"]`,
  timelineContextBadge: '[data-testid="timeline-context-badge"]',
  timelineEscalationBadge: '[data-testid="timeline-escalation-badge"]',
  timelineThinkingBadge: '[data-testid="timeline-thinking-badge"]',
  timelineQuestions: '[data-testid="timeline-questions"]',

  // Confidence Sparkline (v2.3.1)
  confidenceSparkline: '[data-testid="confidence-sparkline"]',

  // Flux List - Complexity Badges (v2.3)
  badgesLegend: '[data-testid="badges-legend"]',
  badgeQuick: '[data-testid="badge-quick"]',
  badgeContext: '[data-testid="badge-context"]',
  badgeComplex: '[data-testid="badge-complex"]',
  badgeOpus: '[data-testid="badge-opus"]',

  // Folder Picker (SC-19)
  folderPath: '[data-testid="folder-path"]',
  folderAutocomplete: '[data-testid="folder-autocomplete"]',
  folderSearchInput: '[data-testid="folder-search-input"]',
  folderSuggestion: '[data-testid="folder-suggestion"]',
  folderCreateOption: '[data-testid="folder-create-option"]',

  // Auto-execution indicators (SC-14, SC-15)
  autoExecutedBadge: '[data-testid="auto-executed-badge"]',
  confidenceScore: '[data-testid="confidence-score"]',
  processingIndicator: '[data-testid="processing-indicator"]',
  queueFullMessage: '[data-testid="queue-full-message"]',

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
