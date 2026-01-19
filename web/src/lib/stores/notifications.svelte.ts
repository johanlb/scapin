/**
 * Notifications Store
 * Manages push notification permissions and system notifications via Service Worker
 */
import { browser } from '$app/environment';
import type { ProcessingEventData } from './websocket.svelte';

type PermissionStatus = 'default' | 'granted' | 'denied' | 'unsupported';

interface NotificationState {
	permission: PermissionStatus;
	isSupported: boolean;
	serviceWorkerReady: boolean;
	pushSubscription: PushSubscription | null;
}

// Create reactive state
let state = $state<NotificationState>({
	permission: 'default',
	isSupported: false,
	serviceWorkerReady: false,
	pushSubscription: null
});

/**
 * Initialize notification support
 */
async function initialize(): Promise<void> {
	if (!browser) return;

	// Check browser support
	state.isSupported = 'Notification' in window && 'serviceWorker' in navigator;

	if (!state.isSupported) {
		state.permission = 'unsupported';
		return;
	}

	// Get current permission
	state.permission = Notification.permission as PermissionStatus;

	// Check service worker registration
	try {
		const registration = await navigator.serviceWorker.ready;
		state.serviceWorkerReady = true;

		// Check for existing push subscription
		const subscription = await registration.pushManager.getSubscription();
		state.pushSubscription = subscription;
	} catch (err) {
		console.error('[Notifications] Service worker not ready:', err);
	}
}

/**
 * Request notification permission
 */
async function requestPermission(): Promise<boolean> {
	if (!browser || !state.isSupported) return false;

	try {
		const result = await Notification.requestPermission();
		state.permission = result as PermissionStatus;
		return result === 'granted';
	} catch (err) {
		console.error('[Notifications] Permission request failed:', err);
		return false;
	}
}

/**
 * Show a notification for a processing event
 */
function showEventNotification(event: ProcessingEventData): void {
	if (!browser || state.permission !== 'granted') return;

	// Determine notification content based on event type
	const notification = getNotificationContent(event);
	if (!notification) return;

	// Try to use service worker for notification (better experience)
	if (state.serviceWorkerReady) {
		navigator.serviceWorker.ready.then((registration) => {
			// Use extended options for service worker notifications
			const options: NotificationOptions & { vibrate?: number[]; requireInteraction?: boolean } = {
				body: notification.body,
				icon: '/icons/icon-192.png',
				badge: '/icons/favicon-32.png',
				tag: `scapin-${event.event_type}-${Date.now()}`,
				data: {
					url: notification.url || '/',
					eventType: event.event_type
				}
			};

			// Add urgency-specific options (supported in service worker context)
			if (notification.urgency === 'high') {
				options.vibrate = [100, 50, 100];
				options.requireInteraction = true;
			}

			registration.showNotification(notification.title, options);
		});
	} else {
		// Fallback to basic notification
		new Notification(notification.title, {
			body: notification.body,
			icon: '/icons/icon-192.png',
			tag: `scapin-${event.event_type}-${Date.now()}`
		});
	}
}

/**
 * Get notification content for a processing event
 */
function getNotificationContent(event: ProcessingEventData): {
	title: string;
	body: string;
	url?: string;
	urgency?: 'high' | 'normal';
} | null {
	switch (event.event_type) {
		case 'email_completed':
			if (event.action === 'urgent' || event.category === 'urgent') {
				return {
					title: 'Péripétie urgente',
					body: event.subject || 'Nouvelle péripétie urgente',
					url: '/peripeties',
					urgency: 'high'
				};
			}
			// Don't notify for non-urgent emails
			return null;

		case 'email_error':
			return {
				title: 'Erreur de traitement',
				body: event.error || 'Erreur lors du traitement',
				url: '/peripeties',
				urgency: 'normal'
			};

		case 'batch_completed':
			return {
				title: 'Traitement terminé',
				body: `${event.total || 0} péripéties traitées`,
				url: '/peripeties',
				urgency: 'normal'
			};

		case 'system_error':
			return {
				title: 'Erreur systeme',
				body: event.error || 'Une erreur est survenue',
				url: '/',
				urgency: 'high'
			};

		default:
			// Don't notify for other event types
			return null;
	}
}

/**
 * Setup listener for WebSocket events to trigger notifications
 */
function setupEventListener(): void {
	if (!browser) return;

	window.addEventListener('scapin:event', ((e: CustomEvent<ProcessingEventData>) => {
		showEventNotification(e.detail);
	}) as EventListener);
}

/**
 * Check if notifications are enabled
 */
function isEnabled(): boolean {
	return state.isSupported && state.permission === 'granted';
}

// Computed values
const canRequestPermission = $derived(
	state.isSupported && state.permission === 'default'
);
const isGranted = $derived(state.permission === 'granted');
const isDenied = $derived(state.permission === 'denied');

// Export reactive getters and actions
export const notificationStore = {
	get state() { return state; },
	get permission() { return state.permission; },
	get isSupported() { return state.isSupported; },
	get serviceWorkerReady() { return state.serviceWorkerReady; },
	get canRequestPermission() { return canRequestPermission; },
	get isGranted() { return isGranted; },
	get isDenied() { return isDenied; },
	initialize,
	requestPermission,
	showEventNotification,
	setupEventListener,
	isEnabled
};
