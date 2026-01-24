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

// v2.4: Tab-based filtering
type TabFilter = 'to_process' | 'in_progress' | 'snoozed' | 'history' | 'errors';

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
	tabFilter: TabFilter;
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
	statusFilter: 'pending',
	tabFilter: 'to_process'
});

// Request counter to handle race conditions when switching tabs quickly
let fetchRequestId = 0;

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

// Page sizes per tab - history loads less initially for performance
const TAB_PAGE_SIZES: Record<TabFilter, number> = {
	to_process: 50,
	in_progress: 50,
	snoozed: 50,
	history: 10,  // Load less initially, use infinite scroll
	errors: 50
};

// v2.4: Fetch queue by tab (new method)
async function fetchQueueByTab(tab: TabFilter, page = 1): Promise<void> {
	// Increment request ID to track this specific request
	const thisRequestId = ++fetchRequestId;

	state.loading = true;
	state.error = null;
	state.tabFilter = tab;

	const pageSize = TAB_PAGE_SIZES[tab];

	try {
		const [response, stats] = await Promise.all([
			listQueueItems(page, pageSize, 'pending', undefined, tab),
			getQueueStats()
		]);

		// Check if a newer request was made while we were waiting
		// If so, discard this response to avoid race conditions
		if (thisRequestId !== fetchRequestId) {
			return;
		}

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
		// Only update error state if this is still the current request
		if (thisRequestId !== fetchRequestId) {
			return;
		}

		if (err instanceof ApiError) {
			if (err.status === 0) {
				state.error = 'Impossible de contacter le serveur.';
			} else {
				state.error = `Erreur ${err.status}: ${err.message}`;
			}
		} else {
			state.error = 'Une erreur inattendue est survenue.';
		}
		console.error('Failed to fetch queue by tab:', err);
	} finally {
		// Only clear loading if this is still the current request
		if (thisRequestId === fetchRequestId) {
			state.loading = false;
		}
	}
}

async function loadMore(): Promise<void> {
	if (state.hasMore && !state.loading) {
		await fetchQueue(state.statusFilter, state.currentPage + 1);
	}
}

// Load more items for current tab (infinite scroll)
async function loadMoreByTab(): Promise<void> {
	if (state.hasMore && !state.loading) {
		await fetchQueueByTab(state.tabFilter, state.currentPage + 1);
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

// Toggle manually_approved for a proposed note
function toggleNoteApproval(itemId: string, noteIndex: number): void {
	state.items = state.items.map((item) => {
		if (item.id !== itemId) return item;

		const notes = [...item.analysis.proposed_notes];
		if (noteIndex < 0 || noteIndex >= notes.length) return item;

		const note = notes[noteIndex];
		// Cycle: null -> false -> true -> null (or just toggle based on current checked state)
		const currentlyChecked = note.manually_approved === true ||
			(note.manually_approved === null && note.confidence >= 0.9);
		notes[noteIndex] = { ...note, manually_approved: currentlyChecked ? false : true };

		return { ...item, analysis: { ...item.analysis, proposed_notes: notes } };
	});
}

// Toggle manually_approved for a proposed task
function toggleTaskApproval(itemId: string, taskIndex: number): void {
	state.items = state.items.map((item) => {
		if (item.id !== itemId) return item;

		const tasks = [...item.analysis.proposed_tasks];
		if (taskIndex < 0 || taskIndex >= tasks.length) return item;

		const task = tasks[taskIndex];
		// Cycle based on current checked state
		const currentlyChecked = task.manually_approved === true ||
			(task.manually_approved === null && task.confidence >= 0.9);
		tasks[taskIndex] = { ...task, manually_approved: currentlyChecked ? false : true };

		return { ...item, analysis: { ...item.analysis, proposed_tasks: tasks } };
	});
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
	fetchQueueByTab,
	fetchStats,
	loadMore,
	loadMoreByTab,
	approve,
	reject,
	removeFromList,
	restoreItem,
	updateItemAnalysis,
	toggleNoteApproval,
	toggleTaskApproval,
	moveToEnd,
	refresh,
	clearError
};

export type { QueueItem, QueueStats };
