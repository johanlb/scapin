/**
 * Queue WebSocket Store (v2.4)
 *
 * Manages WebSocket connection for real-time queue events.
 * Connects to /ws/queue endpoint and updates the queue store on events.
 *
 * Events handled:
 *   - item_added: New item added to queue
 *   - item_updated: Item state/resolution changed
 *   - item_removed: Item removed from queue
 *   - stats_updated: Queue statistics changed
 */
import { getAuthToken } from '$lib/api';
import { browser } from '$app/environment';
import { queueStore } from './queue.svelte';

// Queue event types from backend
type QueueEventType = 'item_added' | 'item_updated' | 'item_removed' | 'stats_updated';

interface QueueItemSummary {
	id: string;
	account_id: string | null;
	state: string;
	status: string;
	resolution: unknown | null;
	snooze: unknown | null;
	error: unknown | null;
	timestamps: unknown | null;
	queued_at: string;
	reviewed_at: string | null;
	metadata: {
		subject: string | null;
		from_address: string | null;
		from_name: string | null;
		date: string | null;
		has_attachments: boolean;
	};
	analysis: {
		action: string;
		confidence: number;
		summary: string | null;
	};
}

interface QueueWebSocketMessage {
	type: 'connected' | 'authenticated' | 'subscribed' | 'item_added' | 'item_updated' | 'item_removed' | 'stats_updated' | 'pong' | 'error';
	channel?: string;
	item?: QueueItemSummary;
	item_id?: string;
	changes?: string[];
	previous_state?: string;
	reason?: string;
	stats?: {
		total: number;
		by_status: Record<string, number>;
		by_state?: Record<string, number>;
		by_tab?: Record<string, number>;
		by_resolution?: Record<string, number>;
	};
	timestamp?: string;
	message?: string;
	user?: string;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface QueueWebSocketState {
	status: ConnectionStatus;
	error: string | null;
	lastEventTime: Date | null;
}

// Create reactive state
let state = $state<QueueWebSocketState>({
	status: 'disconnected',
	error: null,
	lastEventTime: null
});

// WebSocket instance
let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;

// Config
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 30000;

/**
 * Build WebSocket URL for queue endpoint
 */
function buildWsUrl(): string {
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	const host = window.location.host;
	return `${protocol}//${host}/ws/queue`;
}

/**
 * Send authentication message after connection
 */
function sendAuthMessage(): void {
	const token = getAuthToken();
	if (token && ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify({ type: 'auth', token }));
		console.log('[QueueWS] Sent auth message');
	}
}

/**
 * Connect to WebSocket server
 */
function connect(): void {
	if (!browser) return;
	if (ws?.readyState === WebSocket.OPEN) return;

	// Clear any existing reconnect timeout
	if (reconnectTimeout) {
		clearTimeout(reconnectTimeout);
		reconnectTimeout = null;
	}

	state.status = 'connecting';
	state.error = null;

	try {
		ws = new WebSocket(buildWsUrl());

		ws.onopen = () => {
			console.log('[QueueWS] Connected, sending auth...');
			state.status = 'connecting';
			state.error = null;
			sendAuthMessage();
		};

		ws.onmessage = (event) => {
			try {
				const message: QueueWebSocketMessage = JSON.parse(event.data);
				handleMessage(message);
			} catch (err) {
				console.error('[QueueWS] Failed to parse message:', err);
			}
		};

		ws.onclose = (event) => {
			console.log('[QueueWS] Disconnected:', event.code, event.reason);
			state.status = 'disconnected';
			stopPing();

			// Auto-reconnect unless intentionally closed
			if (event.code !== 1000 && event.code !== 4001) {
				scheduleReconnect();
			}
		};

		ws.onerror = (event) => {
			console.error('[QueueWS] Error:', event);
			state.status = 'error';
			state.error = 'Erreur de connexion WebSocket';
		};
	} catch (err) {
		console.error('[QueueWS] Failed to create WebSocket:', err);
		state.status = 'error';
		state.error = 'Impossible de se connecter';
	}
}

/**
 * Disconnect from WebSocket server
 */
function disconnect(): void {
	if (reconnectTimeout) {
		clearTimeout(reconnectTimeout);
		reconnectTimeout = null;
	}

	stopPing();

	if (ws) {
		ws.close(1000, 'Client disconnect');
		ws = null;
	}

	state.status = 'disconnected';
}

/**
 * Handle incoming WebSocket message
 */
function handleMessage(message: QueueWebSocketMessage): void {
	// Update last event time
	state.lastEventTime = new Date();

	switch (message.type) {
		case 'authenticated':
			console.log('[QueueWS] Authenticated as:', message.user);
			state.status = 'connected';
			state.error = null;
			startPing();
			break;

		case 'connected':
			console.log('[QueueWS] Server confirmed connection:', message.message);
			if (state.status === 'connecting') {
				state.status = 'connected';
				startPing();
			}
			break;

		case 'subscribed':
			console.log('[QueueWS] Subscribed to channel:', message.channel);
			break;

		case 'item_added':
			handleItemAdded(message);
			break;

		case 'item_updated':
			handleItemUpdated(message);
			break;

		case 'item_removed':
			handleItemRemoved(message);
			break;

		case 'stats_updated':
			handleStatsUpdated(message);
			break;

		case 'pong':
			// Server responded to ping
			break;

		case 'error':
			console.error('[QueueWS] Server error:', message.message);
			break;
	}
}

/**
 * Handle item_added event
 */
function handleItemAdded(message: QueueWebSocketMessage): void {
	if (!message.item) return;

	console.log('[QueueWS] Item added:', message.item.id);

	// Dispatch custom event for components to handle
	if (browser) {
		window.dispatchEvent(new CustomEvent('scapin:queue:item_added', {
			detail: message.item
		}));
	}

	// Refresh the queue to include the new item
	// This is a simple approach - a more sophisticated implementation
	// would add the item directly if it matches the current filter
	queueStore.fetchStats();
}

/**
 * Handle item_updated event
 */
function handleItemUpdated(message: QueueWebSocketMessage): void {
	if (!message.item) return;

	console.log('[QueueWS] Item updated:', message.item.id, 'changes:', message.changes);

	// Dispatch custom event for components to handle
	if (browser) {
		window.dispatchEvent(new CustomEvent('scapin:queue:item_updated', {
			detail: {
				item: message.item,
				changes: message.changes,
				previousState: message.previous_state
			}
		}));
	}

	// Update the item in the store if it exists
	// The store's items list uses the full QueueItem type, but we only have summary
	// So we just refresh stats and let components decide what to do
	queueStore.fetchStats();
}

/**
 * Handle item_removed event
 */
function handleItemRemoved(message: QueueWebSocketMessage): void {
	if (!message.item_id) return;

	console.log('[QueueWS] Item removed:', message.item_id);

	// Remove from the local store
	queueStore.removeFromList(message.item_id);

	// Dispatch custom event
	if (browser) {
		window.dispatchEvent(new CustomEvent('scapin:queue:item_removed', {
			detail: {
				itemId: message.item_id,
				reason: message.reason
			}
		}));
	}
}

/**
 * Handle stats_updated event
 */
function handleStatsUpdated(message: QueueWebSocketMessage): void {
	if (!message.stats) return;

	console.log('[QueueWS] Stats updated:', message.stats.total, 'items');

	// Dispatch custom event
	if (browser) {
		window.dispatchEvent(new CustomEvent('scapin:queue:stats_updated', {
			detail: message.stats
		}));
	}

	// The queue store will be refreshed on the next fetch
	// For now we just rely on the existing refresh mechanism
}

/**
 * Schedule reconnection attempt
 */
function scheduleReconnect(): void {
	if (reconnectTimeout) return;

	console.log(`[QueueWS] Scheduling reconnect in ${RECONNECT_DELAY}ms`);
	reconnectTimeout = setTimeout(() => {
		reconnectTimeout = null;
		connect();
	}, RECONNECT_DELAY);
}

/**
 * Start ping interval to keep connection alive
 */
function startPing(): void {
	stopPing();
	pingInterval = setInterval(() => {
		if (ws?.readyState === WebSocket.OPEN) {
			ws.send('ping');
		}
	}, PING_INTERVAL);
}

/**
 * Stop ping interval
 */
function stopPing(): void {
	if (pingInterval) {
		clearInterval(pingInterval);
		pingInterval = null;
	}
}

// Computed values
const isConnected = $derived(state.status === 'connected');
const isConnecting = $derived(state.status === 'connecting');
const hasError = $derived(state.status === 'error');

// Export reactive getters and actions
export const queueWsStore = {
	get state() {
		return state;
	},
	get status() {
		return state.status;
	},
	get error() {
		return state.error;
	},
	get lastEventTime() {
		return state.lastEventTime;
	},
	get isConnected() {
		return isConnected;
	},
	get isConnecting() {
		return isConnecting;
	},
	get hasError() {
		return hasError;
	},
	connect,
	disconnect
};

export type { QueueWebSocketMessage, QueueEventType, QueueItemSummary };
