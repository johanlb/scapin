/**
 * Valets Dashboard Store
 * Manages the status and metrics of all valet workers
 */
import { browser } from '$app/environment';
import {
	getValetsDashboard,
	getValetsMetrics,
	type ValetsDashboardResponse,
	type ValetsMetricsResponse,
	type ValetInfo,
	type ValetStatus
} from '$lib/api/client';

interface ValetsState {
	dashboard: ValetsDashboardResponse | null;
	metrics: ValetsMetricsResponse | null;
	loading: boolean;
	error: string | null;
	selectedPeriod: 'today' | '7d' | '30d';
	lastUpdated: Date | null;
}

// Initial state
const initialState: ValetsState = {
	dashboard: null,
	metrics: null,
	loading: false,
	error: null,
	selectedPeriod: 'today',
	lastUpdated: null
};

// Create reactive state
let state = $state<ValetsState>({ ...initialState });

// Computed values
const valets = $derived(state.dashboard?.valets ?? []);
const systemStatus = $derived(state.dashboard?.system_status ?? 'unknown');
const activeWorkers = $derived(state.dashboard?.active_workers ?? 0);
const totalTasksToday = $derived(state.dashboard?.total_tasks_today ?? 0);
const avgConfidence = $derived(state.dashboard?.avg_confidence ?? 0);

/**
 * Fetch dashboard data
 */
async function fetchDashboard(): Promise<void> {
	if (!browser) return;
	if (state.loading) return;

	state.loading = true;
	state.error = null;

	try {
		state.dashboard = await getValetsDashboard();
		state.lastUpdated = new Date();
	} catch (err) {
		state.error = err instanceof Error ? err.message : 'Erreur lors du chargement';
		console.error('[Valets] Dashboard fetch error:', err);
	} finally {
		state.loading = false;
	}
}

/**
 * Fetch metrics data
 */
async function fetchMetrics(period?: 'today' | '7d' | '30d'): Promise<void> {
	if (!browser) return;

	const targetPeriod = period ?? state.selectedPeriod;
	state.selectedPeriod = targetPeriod;

	try {
		state.metrics = await getValetsMetrics(targetPeriod);
	} catch (err) {
		console.error('[Valets] Metrics fetch error:', err);
	}
}

/**
 * Refresh all data
 */
async function refresh(): Promise<void> {
	await Promise.all([fetchDashboard(), fetchMetrics()]);
}

/**
 * Initialize store
 */
async function initialize(): Promise<void> {
	await refresh();
}

/**
 * Get status color
 */
function getStatusColor(status: ValetStatus): string {
	switch (status) {
		case 'running':
			return 'text-green-400';
		case 'idle':
			return 'text-[var(--color-text-tertiary)]';
		case 'paused':
			return 'text-yellow-400';
		case 'error':
			return 'text-red-400';
		default:
			return 'text-[var(--color-text-secondary)]';
	}
}

/**
 * Get status background color
 */
function getStatusBgColor(status: ValetStatus): string {
	switch (status) {
		case 'running':
			return 'bg-green-500/20';
		case 'idle':
			return 'bg-[var(--glass-tint)]';
		case 'paused':
			return 'bg-yellow-500/20';
		case 'error':
			return 'bg-red-500/20';
		default:
			return 'bg-[var(--glass-tint)]';
	}
}

/**
 * Get status label in French
 */
function getStatusLabel(status: ValetStatus): string {
	switch (status) {
		case 'running':
			return 'Actif';
		case 'idle':
			return 'En attente';
		case 'paused':
			return 'En pause';
		case 'error':
			return 'Erreur';
		default:
			return status;
	}
}

/**
 * Get system status color
 */
function getSystemStatusColor(status: string): string {
	switch (status) {
		case 'healthy':
			return 'text-green-400';
		case 'degraded':
			return 'text-yellow-400';
		case 'error':
			return 'text-red-400';
		default:
			return 'text-[var(--color-text-secondary)]';
	}
}

/**
 * Get valet icon
 */
function getValetIcon(name: string): string {
	const icons: Record<string, string> = {
		trivelin: '👁️',
		sancho: '🧠',
		passepartout: '📚',
		planchet: '📋',
		figaro: '⚡',
		sganarelle: '🎓',
		frontin: '🎭'
	};
	return icons[name] || '🤖';
}

/**
 * Format relative time
 */
function formatRelativeTime(timestamp: string | null): string {
	if (!timestamp) return 'Jamais';

	const date = new Date(timestamp);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMs / 3600000);

	if (diffMins < 1) return "À l'instant";
	if (diffMins < 60) return `Il y a ${diffMins}min`;
	if (diffHours < 24) return `Il y a ${diffHours}h`;

	return date.toLocaleDateString('fr-FR', {
		day: 'numeric',
		month: 'short',
		hour: '2-digit',
		minute: '2-digit'
	});
}

/**
 * Clear error
 */
function clearError(): void {
	state.error = null;
}

// Export store with reactive getters and actions
export const valetsStore = {
	// Reactive getters
	get dashboard() {
		return state.dashboard;
	},
	get metrics() {
		return state.metrics;
	},
	get loading() {
		return state.loading;
	},
	get error() {
		return state.error;
	},
	get selectedPeriod() {
		return state.selectedPeriod;
	},
	get lastUpdated() {
		return state.lastUpdated;
	},
	get valets() {
		return valets;
	},
	get systemStatus() {
		return systemStatus;
	},
	get activeWorkers() {
		return activeWorkers;
	},
	get totalTasksToday() {
		return totalTasksToday;
	},
	get avgConfidence() {
		return avgConfidence;
	},

	// Actions
	fetchDashboard,
	fetchMetrics,
	refresh,
	initialize,
	clearError,

	// Utilities
	getStatusColor,
	getStatusBgColor,
	getStatusLabel,
	getSystemStatusColor,
	getValetIcon,
	formatRelativeTime
};
