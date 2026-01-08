/**
 * Notification Center Store
 * Manages in-app notifications (fetched from API, not browser push)
 * Uses Svelte 5 runes for reactive state management
 */
import { browser } from '$app/environment';
import {
	listNotifications,
	getNotificationStats,
	markNotificationsRead,
	deleteNotification,
	type Notification,
	type NotificationStats,
	type NotificationPriority
} from '$lib/api/client';

interface NotificationCenterState {
	notifications: Notification[];
	stats: NotificationStats | null;
	isOpen: boolean;
	loading: boolean;
	error: string | null;
	hasMore: boolean;
	page: number;
	pageSize: number;
	isPaused: boolean; // Focus mode: suppress new notification sounds/toasts
}

// Initial state
const initialState: NotificationCenterState = {
	notifications: [],
	stats: null,
	isOpen: false,
	loading: false,
	error: null,
	hasMore: true,
	page: 1,
	pageSize: 20,
	isPaused: false
};

// Create reactive state
let state = $state<NotificationCenterState>({ ...initialState });

// Computed values
const unreadCount = $derived(state.stats?.unread ?? 0);
const hasUnread = $derived(unreadCount > 0);
const isEmpty = $derived(state.notifications.length === 0 && !state.loading);

/**
 * Toggle panel open/close
 */
function toggle(): void {
	state.isOpen = !state.isOpen;
	if (state.isOpen && state.notifications.length === 0) {
		fetchNotifications();
	}
}

/**
 * Open the panel
 */
function open(): void {
	state.isOpen = true;
	if (state.notifications.length === 0) {
		fetchNotifications();
	}
}

/**
 * Close the panel
 */
function close(): void {
	state.isOpen = false;
}

/**
 * Fetch notifications from API
 */
async function fetchNotifications(reset: boolean = false): Promise<void> {
	if (!browser) return;
	if (state.loading) return;

	state.loading = true;
	state.error = null;

	try {
		const page = reset ? 1 : state.page;
		const response = await listNotifications(page, state.pageSize);

		if (reset) {
			state.notifications = response.notifications;
		} else {
			// Append without duplicates
			const existingIds = new Set(state.notifications.map((n) => n.id));
			const newNotifications = response.notifications.filter((n) => !existingIds.has(n.id));
			state.notifications = [...state.notifications, ...newNotifications];
		}

		state.page = page + 1;
		state.hasMore = response.notifications.length === state.pageSize;
	} catch (err) {
		state.error = err instanceof Error ? err.message : 'Erreur lors du chargement';
		console.error('[NotificationCenter] Fetch error:', err);
	} finally {
		state.loading = false;
	}
}

/**
 * Refresh notifications (reset and refetch)
 */
async function refresh(): Promise<void> {
	await fetchNotifications(true);
	await fetchStats();
}

/**
 * Load more notifications (pagination)
 */
async function loadMore(): Promise<void> {
	if (state.hasMore && !state.loading) {
		await fetchNotifications(false);
	}
}

/**
 * Fetch notification stats
 */
async function fetchStats(): Promise<void> {
	if (!browser) return;

	try {
		state.stats = await getNotificationStats();
	} catch (err) {
		console.error('[NotificationCenter] Stats error:', err);
	}
}

/**
 * Mark a single notification as read
 */
async function markAsRead(notificationId: string): Promise<void> {
	if (!browser) return;

	try {
		await markNotificationsRead([notificationId]);

		// Update local state
		const notification = state.notifications.find((n) => n.id === notificationId);
		if (notification) {
			notification.is_read = true;
			notification.read_at = new Date().toISOString();
		}

		// Update stats
		if (state.stats && state.stats.unread > 0) {
			state.stats.unread--;
		}
	} catch (err) {
		console.error('[NotificationCenter] Mark read error:', err);
	}
}

/**
 * Mark all notifications as read
 */
async function markAllAsRead(): Promise<void> {
	if (!browser) return;

	try {
		await markNotificationsRead(undefined, true);

		// Update local state
		state.notifications = state.notifications.map((n) => ({
			...n,
			is_read: true,
			read_at: n.read_at || new Date().toISOString()
		}));

		// Update stats
		if (state.stats) {
			state.stats.unread = 0;
		}
	} catch (err) {
		console.error('[NotificationCenter] Mark all read error:', err);
	}
}

/**
 * Delete a notification
 */
async function remove(notificationId: string): Promise<void> {
	if (!browser) return;

	try {
		await deleteNotification(notificationId);

		// Update local state
		const notification = state.notifications.find((n) => n.id === notificationId);
		state.notifications = state.notifications.filter((n) => n.id !== notificationId);

		// Update stats
		if (state.stats) {
			state.stats.total--;
			if (notification && !notification.is_read) {
				state.stats.unread--;
			}
		}
	} catch (err) {
		console.error('[NotificationCenter] Delete error:', err);
	}
}

/**
 * Add a notification received via WebSocket
 */
function addFromWebSocket(notification: Notification): void {
	// Add to beginning of list
	state.notifications = [notification, ...state.notifications];

	// Update stats
	if (state.stats) {
		state.stats.total++;
		if (!notification.is_read) {
			state.stats.unread++;
		}
	}
}

/**
 * Get priority color class
 */
function getPriorityColor(priority: NotificationPriority): string {
	switch (priority) {
		case 'urgent':
			return 'text-red-400';
		case 'high':
			return 'text-orange-400';
		case 'normal':
			return 'text-[var(--color-text-secondary)]';
		case 'low':
			return 'text-[var(--color-text-tertiary)]';
		default:
			return 'text-[var(--color-text-secondary)]';
	}
}

/**
 * Get notification type icon
 */
function getTypeIcon(type: string): string {
	const icons: Record<string, string> = {
		email_received: '📧',
		email_processed: '✉️',
		teams_message: '💬',
		calendar_event: '📅',
		calendar_reminder: '⏰',
		task_created: '✅',
		task_due: '⚡',
		note_reminder: '📝',
		system_alert: '⚠️',
		queue_item: '📋'
	};
	return icons[type] || '🔔';
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string): string {
	const date = new Date(timestamp);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMs / 3600000);
	const diffDays = Math.floor(diffMs / 86400000);

	if (diffMins < 1) return "À l'instant";
	if (diffMins < 60) return `Il y a ${diffMins}min`;
	if (diffHours < 24) return `Il y a ${diffHours}h`;
	if (diffDays < 7) return `Il y a ${diffDays}j`;

	return date.toLocaleDateString('fr-FR', {
		day: 'numeric',
		month: 'short'
	});
}

/**
 * Clear error state
 */
function clearError(): void {
	state.error = null;
}

/**
 * Pause notifications (for focus mode)
 * New notifications will still be stored but won't trigger sounds/toasts
 */
function pauseNotifications(): void {
	state.isPaused = true;
}

/**
 * Resume notifications
 */
function resumeNotifications(): void {
	state.isPaused = false;
}

/**
 * Initialize the store (fetch initial data)
 */
async function initialize(): Promise<void> {
	await fetchStats();
}

// Export store with reactive getters and actions
export const notificationCenterStore = {
	// Reactive getters
	get notifications() {
		return state.notifications;
	},
	get stats() {
		return state.stats;
	},
	get isOpen() {
		return state.isOpen;
	},
	get loading() {
		return state.loading;
	},
	get error() {
		return state.error;
	},
	get hasMore() {
		return state.hasMore;
	},
	get unreadCount() {
		return unreadCount;
	},
	get hasUnread() {
		return hasUnread;
	},
	get isEmpty() {
		return isEmpty;
	},
	get isPaused() {
		return state.isPaused;
	},

	// Actions
	toggle,
	open,
	close,
	refresh,
	loadMore,
	fetchStats,
	markAsRead,
	markAllAsRead,
	remove,
	addFromWebSocket,
	clearError,
	initialize,
	pauseNotifications,
	resumeNotifications,

	// Utilities
	getPriorityColor,
	getTypeIcon,
	formatTimestamp
};
