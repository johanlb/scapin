/**
 * Canevas Store
 * Manages the permanent user context (Canevas) status
 */
import { getCanevasStatus, ApiError } from '$lib/api';
import type { CanevasStatus } from '$lib/api';

interface CanevasState {
	status: CanevasStatus | null;
	loading: boolean;
	error: string | null;
	lastFetch: Date | null;
}

// Create reactive state
let state = $state<CanevasState>({
	status: null,
	loading: false,
	error: null,
	lastFetch: null
});

// Derived values
const isComplete = $derived(state.status?.completeness === 'complete');
const isPartial = $derived(state.status?.completeness === 'partial');
const isIncomplete = $derived(state.status?.completeness === 'incomplete');
const hasStatus = $derived(state.status !== null);

const completenessLabel = $derived(() => {
	if (!state.status) return 'Inconnu';
	switch (state.status.completeness) {
		case 'complete':
			return 'Complet';
		case 'partial':
			return 'Partiel';
		case 'incomplete':
			return 'Incomplet';
		default:
			return 'Inconnu';
	}
});

const completenessColor = $derived(() => {
	if (!state.status) return 'var(--color-text-tertiary)';
	switch (state.status.completeness) {
		case 'complete':
			return 'var(--color-success)';
		case 'partial':
			return 'var(--color-warning)';
		case 'incomplete':
			return 'var(--color-error)';
		default:
			return 'var(--color-text-tertiary)';
	}
});

// Actions
async function fetch(): Promise<void> {
	state.loading = true;
	state.error = null;

	try {
		state.status = await getCanevasStatus();
		state.lastFetch = new Date();
	} catch (err) {
		handleError(err, 'Impossible de charger le statut du Canevas');
	} finally {
		state.loading = false;
	}
}

function clearError(): void {
	state.error = null;
}

function handleError(err: unknown, defaultMessage: string): void {
	if (err instanceof ApiError) {
		if (err.status === 0) {
			state.error = 'Impossible de contacter le serveur.';
		} else {
			state.error = `Erreur ${err.status}: ${err.message}`;
		}
	} else {
		state.error = defaultMessage;
	}
}

// Export reactive getters and actions
export const canevasStore = {
	// State getters
	get status() {
		return state.status;
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

	// Derived getters
	get isComplete() {
		return isComplete;
	},
	get isPartial() {
		return isPartial;
	},
	get isIncomplete() {
		return isIncomplete;
	},
	get hasStatus() {
		return hasStatus;
	},
	get completenessLabel() {
		return completenessLabel();
	},
	get completenessColor() {
		return completenessColor();
	},

	// Actions
	fetch,
	clearError
};

export type { CanevasStatus };
