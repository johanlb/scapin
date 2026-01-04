/**
 * Briefing Store
 * Manages morning briefing data from the API
 */
import { getMorningBriefing, getStats, ApiError } from '$lib/api';
import type { MorningBriefing, Stats, BriefingItem } from '$lib/api';

interface BriefingState {
	briefing: MorningBriefing | null;
	stats: Stats | null;
	loading: boolean;
	error: string | null;
	lastFetch: Date | null;
}

// Create reactive state
let state = $state<BriefingState>({
	briefing: null,
	stats: null,
	loading: false,
	error: null,
	lastFetch: null
});

// Computed values
const urgentItems = $derived(
	state.briefing?.urgent_items ?? []
);

const calendarToday = $derived(
	state.briefing?.calendar_today ?? []
);

const allPendingItems = $derived(
	state.briefing
		? [
				...state.briefing.urgent_items,
				...state.briefing.emails_pending,
				...state.briefing.teams_unread
			]
		: []
);

// Actions
async function fetchBriefing(): Promise<void> {
	state.loading = true;
	state.error = null;

	try {
		const [briefing, stats] = await Promise.all([
			getMorningBriefing(),
			getStats()
		]);

		state.briefing = briefing;
		state.stats = stats;
		state.lastFetch = new Date();
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 0) {
				state.error = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
			} else {
				state.error = `Erreur ${err.status}: ${err.message}`;
			}
		} else {
			state.error = 'Une erreur inattendue est survenue.';
		}
		console.error('Failed to fetch briefing:', err);
	} finally {
		state.loading = false;
	}
}

async function refresh(): Promise<void> {
	await fetchBriefing();
}

function clearError(): void {
	state.error = null;
}

// Export reactive getters and actions
export const briefingStore = {
	get state() { return state; },
	get briefing() { return state.briefing; },
	get stats() { return state.stats; },
	get loading() { return state.loading; },
	get error() { return state.error; },
	get lastFetch() { return state.lastFetch; },
	get urgentItems() { return urgentItems; },
	get calendarToday() { return calendarToday; },
	get allPendingItems() { return allPendingItems; },
	fetchBriefing,
	refresh,
	clearError
};

export type { BriefingItem };
