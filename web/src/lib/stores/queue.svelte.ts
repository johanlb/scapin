/**
 * Queue Store
 * Manages email review queue from the API
 */
import {
	listQueueItems,
	getQueueStats,
	approveQueueItem,
	rejectQueueItem,
	ApiError
} from '$lib/api';
import type { QueueItem, QueueStats } from '$lib/api';

interface QueueState {
	items: QueueItem[];
	stats: QueueStats | null;
	loading: boolean;
	error: string | null;
	lastFetch: Date | null;
	currentPage: number;
	hasMore: boolean;
	total: number;
	statusFilter: string;
}

// Create reactive state
let state = $state<QueueState>({
	items: [],
	stats: null,
	loading: false,
	error: null,
	lastFetch: null,
	currentPage: 1,
	hasMore: false,
	total: 0,
	statusFilter: 'pending'
});

// Computed values
const pendingItems = $derived(state.items.filter((item) => item.status === 'pending'));

const approvedItems = $derived(state.items.filter((item) => item.status === 'approved'));

const rejectedItems = $derived(state.items.filter((item) => item.status === 'rejected'));

const pendingCount = $derived(state.stats?.by_status?.pending ?? 0);

// Actions
async function fetchQueue(status = 'pending', page = 1): Promise<void> {
	state.loading = true;
	state.error = null;
	state.statusFilter = status;

	try {
		const [response, stats] = await Promise.all([
			listQueueItems(page, 20, status),
			getQueueStats()
		]);

		if (page === 1) {
			state.items = response.data;
		} else {
			state.items = [...state.items, ...response.data];
		}

		state.stats = stats;
		state.currentPage = response.page;
		state.hasMore = response.has_more;
		state.total = response.total;
		state.lastFetch = new Date();
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 0) {
				state.error = 'Impossible de contacter le serveur.';
			} else {
				state.error = `Erreur ${err.status}: ${err.message}`;
			}
		} else {
			state.error = 'Une erreur inattendue est survenue.';
		}
		console.error('Failed to fetch queue:', err);
	} finally {
		state.loading = false;
	}
}

async function loadMore(): Promise<void> {
	if (state.hasMore && !state.loading) {
		await fetchQueue(state.statusFilter, state.currentPage + 1);
	}
}

async function approve(
	itemId: string,
	modifiedAction?: string,
	modifiedCategory?: string
): Promise<boolean> {
	try {
		const updated = await approveQueueItem(itemId, modifiedAction, modifiedCategory);
		// Update the item in state
		state.items = state.items.map((item) => (item.id === itemId ? updated : item));
		// Refresh stats
		state.stats = await getQueueStats();
		return true;
	} catch (err) {
		console.error('Failed to approve item:', err);
		return false;
	}
}

async function reject(itemId: string, reason?: string): Promise<boolean> {
	try {
		const updated = await rejectQueueItem(itemId, reason);
		// Update the item in state
		state.items = state.items.map((item) => (item.id === itemId ? updated : item));
		// Refresh stats
		state.stats = await getQueueStats();
		return true;
	} catch (err) {
		console.error('Failed to reject item:', err);
		return false;
	}
}

function removeFromList(itemId: string): void {
	state.items = state.items.filter((item) => item.id !== itemId);
	state.total = Math.max(0, state.total - 1);
}

function moveToEnd(itemId: string): void {
	const idx = state.items.findIndex((item) => item.id === itemId);
	if (idx >= 0 && idx < state.items.length - 1) {
		const item = state.items[idx];
		state.items = [...state.items.slice(0, idx), ...state.items.slice(idx + 1), item];
	}
}

// Bug #53 fix: Restore an item to the list (for optimistic update rollback)
// Modified: Add to END of list to not disrupt user's current focus
function restoreItem(item: QueueItem): void {
	// Only restore if not already in list
	if (!state.items.some((i) => i.id === item.id)) {
		// Add at the END of the list so it doesn't interrupt the current item
		state.items = [...state.items, item];
		state.total = state.total + 1;
	}
}

// Bug #55 fix: Update an item's analysis after reanalysis
function updateItemAnalysis(itemId: string, newAnalysis: QueueItem['analysis']): void {
	state.items = state.items.map((item) =>
		item.id === itemId
			? { ...item, analysis: newAnalysis }
			: item
	);
}

async function fetchStats(): Promise<void> {
	try {
		state.stats = await getQueueStats();
	} catch (err) {
		console.error('Failed to fetch stats:', err);
	}
}

async function refresh(): Promise<void> {
	await fetchQueue(state.statusFilter, 1);
}

function clearError(): void {
	state.error = null;
}

// Export reactive getters and actions
export const queueStore = {
	get state() {
		return state;
	},
	get items() {
		return state.items;
	},
	get stats() {
		return state.stats;
	},
	get loading() {
		return state.loading;
	},
	get error() {
		return state.error;
	},
	get lastFetch() {
		return state.lastFetch;
	},
	get hasMore() {
		return state.hasMore;
	},
	get total() {
		return state.total;
	},
	get pendingItems() {
		return pendingItems;
	},
	get approvedItems() {
		return approvedItems;
	},
	get rejectedItems() {
		return rejectedItems;
	},
	get pendingCount() {
		return pendingCount;
	},
	fetchQueue,
	fetchStats,
	loadMore,
	approve,
	reject,
	removeFromList,
	restoreItem,
	updateItemAnalysis,
	moveToEnd,
	refresh,
	clearError
};

export type { QueueItem, QueueStats };
