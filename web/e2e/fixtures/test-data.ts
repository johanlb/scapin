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
  // v2.4: New state/resolution model
  state?: 'queued' | 'analyzing' | 'awaiting_review' | 'processed' | 'error';
  resolution?: 'auto_applied' | 'manual_approved' | 'manual_modified' | 'manual_rejected' | 'manual_skipped' | null;
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

  // Péripéties
  peripetiesList: '[data-testid="peripeties-list"]',
  peripetiesItem: (id: string) => `[data-testid="peripeties-item-${id}"]`,
  approveButton: '[data-testid="approve-button"]',
  rejectButton: '[data-testid="reject-button"]',
  snoozeButton: '[data-testid="snooze-button"]',
  undoToast: '[data-testid^="undo-toast-"]',

  // Péripéties Tabs (v2.4)
  peripetiesTabToProcess: '[data-testid="peripeties-tab-to-process"]',
  peripetiesTabInProgress: '[data-testid="peripeties-tab-in-progress"]',
  peripetiesTabSnoozed: '[data-testid="peripeties-tab-snoozed"]',
  peripetiesTabHistory: '[data-testid="peripeties-tab-history"]',
  peripetiesTabErrors: '[data-testid="peripeties-tab-errors"]',
  // Legacy aliases (deprecated)
  peripetiesTabPending: '[data-testid="peripeties-tab-to-process"]',
  peripetiesTabApproved: '[data-testid="peripeties-tab-history"]',
  peripetiesTabRejected: '[data-testid="peripeties-tab-history"]',

  // Péripéties Filters (SC-15)
  peripetiesFilterAll: '[data-testid="peripeties-filter-all"]',
  peripetiesFilterAuto: '[data-testid="peripeties-filter-auto"]',
  peripetiesFilterUser: '[data-testid="peripeties-filter-user"]',

  // Péripéties Re-analyze (SC-18)
  reanalyzeButton: '[data-testid="reanalyze-button"]',

  // Péripéties Detail - Multi-Pass Analysis (v2.3)
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

  // Why Not Section (v2.3.1)
  whyNotSection: '[data-testid="why-not-section"]',
  whyNotItem: '[data-testid="why-not-item"]',
  optionRejectionReason: '[data-testid="option-rejection-reason"]',

  // Flux List - Complexity Badges (v2.3)
  badgesLegend: '[data-testid="badges-legend"]',
  badgeQuick: '[data-testid="badge-quick"]',
  badgeContext: '[data-testid="badge-context"]',
  badgeComplex: '[data-testid="badge-complex"]',
  badgeOpus: '[data-testid="badge-opus"]',

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

  // Drafts
  draftsList: '[data-testid="drafts-list"]',
  draftItem: (id: string) => `[data-testid="draft-item-${id}"]`,
  draftFilterPending: '[data-testid="draft-filter-pending"]',
  draftFilterSent: '[data-testid="draft-filter-sent"]',
  draftFilterDiscarded: '[data-testid="draft-filter-discarded"]',
  draftFilterAll: '[data-testid="draft-filter-all"]',

  // Valets (System Status)
  valetsContent: '[data-testid="valets-content"]',
  valetStatus: '[data-testid="valet-status"]',
  activeWorkers: '[data-testid="active-workers"]',
  avgConfidence: '[data-testid="avg-confidence"]',

  // Help
  helpContent: '[data-testid="help-content"]',
  helpSection: (section: string) => `[data-testid="help-section-${section}"]`,

  // Notes Review (SM-2)
  notesReviewContent: '[data-testid="notes-review-content"]',
  reviewCard: '[data-testid="review-card"]',
  reviewAnswer: '[data-testid="review-answer"]',
  reviewRating: (rating: number) => `[data-testid="review-rating-${rating}"]`,

  // Journal
  journalContent: '[data-testid="journal-content"]',
  journalDatePicker: '[data-testid="journal-date-picker"]',
  journalTabs: '[data-testid="journal-tabs"]',
  journalTab: (tab: string) => `[data-testid="journal-tab-${tab}"]`,
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
