/**
 * WebSocket Store
 * Manages WebSocket connection for real-time events from Scapin
 */
import { getAuthToken } from '$lib/api';
import { browser } from '$app/environment';

// Event types from backend
type ProcessingEventType =
	| 'processing_started'
	| 'processing_completed'
	| 'account_started'
	| 'account_completed'
	| 'account_error'
	| 'email_started'
	| 'email_analyzing'
	| 'email_completed'
	| 'email_queued'
	| 'email_executed'
	| 'email_error'
	| 'batch_started'
	| 'batch_completed'
	| 'batch_progress'
	| 'system_ready'
	| 'system_error';

interface ProcessingEventData {
	event_type: ProcessingEventType;
	timestamp: string;
	account_id?: string;
	account_name?: string;
	email_id?: number;
	subject?: string;
	from_address?: string;
	email_date?: string;
	preview?: string;
	action?: string;
	confidence?: number;
	category?: string;
	reasoning?: string;
	current?: number;
	total?: number;
	error?: string;
	error_type?: string;
	metadata?: Record<string, unknown>;
}

interface WebSocketMessage {
	type: 'connected' | 'authenticated' | 'event' | 'pong';
	data?: ProcessingEventData;
	timestamp?: string;
	message?: string;
	user?: string;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface WebSocketState {
	status: ConnectionStatus;
	lastEvent: ProcessingEventData | null;
	recentEvents: ProcessingEventData[];
	error: string | null;
}

// Create reactive state
let state = $state<WebSocketState>({
	status: 'disconnected',
	lastEvent: null,
	recentEvents: [],
	error: null
});

// WebSocket instance
let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;

// Config
const MAX_RECENT_EVENTS = 50;
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 30000;

/**
 * Build WebSocket URL (no token in URL for security)
 */
function buildWsUrl(): string {
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	const host = window.location.host;
	return `${protocol}//${host}/ws/live`;
}

/**
 * Send authentication message after connection
 */
function sendAuthMessage(): void {
	const token = getAuthToken();
	if (token && ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify({ type: 'auth', token }));
		console.log('[WS] Sent auth message');
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
			console.log('[WS] Connected, sending auth...');
			state.status = 'connecting'; // Still connecting until authenticated
			state.error = null;

			// Send auth message (ping starts after authentication)
			sendAuthMessage();
		};

		ws.onmessage = (event) => {
			try {
				const message: WebSocketMessage = JSON.parse(event.data);
				handleMessage(message);
			} catch (err) {
				console.error('[WS] Failed to parse message:', err);
			}
		};

		ws.onclose = (event) => {
			console.log('[WS] Disconnected:', event.code, event.reason);
			state.status = 'disconnected';
			stopPing();

			// Auto-reconnect unless intentionally closed
			if (event.code !== 1000 && event.code !== 4001) {
				scheduleReconnect();
			}
		};

		ws.onerror = (event) => {
			console.error('[WS] Error:', event);
			state.status = 'error';
			state.error = 'Erreur de connexion WebSocket';
		};
	} catch (err) {
		console.error('[WS] Failed to create WebSocket:', err);
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
function handleMessage(message: WebSocketMessage): void {
	switch (message.type) {
		case 'authenticated':
			console.log('[WS] Authenticated as:', message.user);
			state.status = 'connected';
			state.error = null;
			// Start ping interval after successful auth
			startPing();
			break;

		case 'connected':
			console.log('[WS] Server confirmed connection:', message.message);
			// If auth is disabled on server, this comes instead of authenticated
			if (state.status === 'connecting') {
				state.status = 'connected';
				startPing();
			}
			break;

		case 'event':
			if (message.data) {
				state.lastEvent = message.data;
				state.recentEvents = [message.data, ...state.recentEvents].slice(0, MAX_RECENT_EVENTS);
				// Dispatch custom event for components to listen to
				if (browser) {
					window.dispatchEvent(new CustomEvent('scapin:event', { detail: message.data }));
				}
			}
			break;

		case 'pong':
			// Server responded to ping
			break;
	}
}

/**
 * Schedule reconnection attempt
 */
function scheduleReconnect(): void {
	if (reconnectTimeout) return;

	console.log(`[WS] Scheduling reconnect in ${RECONNECT_DELAY}ms`);
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

/**
 * Clear all recent events
 */
function clearEvents(): void {
	state.recentEvents = [];
	state.lastEvent = null;
}

// Computed values
const isConnected = $derived(state.status === 'connected');
const isConnecting = $derived(state.status === 'connecting');
const hasError = $derived(state.status === 'error');

// Export reactive getters and actions
export const wsStore = {
	get state() { return state; },
	get status() { return state.status; },
	get lastEvent() { return state.lastEvent; },
	get recentEvents() { return state.recentEvents; },
	get error() { return state.error; },
	get isConnected() { return isConnected; },
	get isConnecting() { return isConnecting; },
	get hasError() { return hasError; },
	connect,
	disconnect,
	clearEvents
};

export type { ProcessingEventData, ProcessingEventType, WebSocketMessage };
