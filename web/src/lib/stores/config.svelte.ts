/**
 * Config Store
 * Manages system configuration from the API for Settings page
 */
import { getConfig, ApiError } from '$lib/api';
import type { IntegrationStatus, SystemConfig } from '$lib/api';

interface ConfigState {
	config: SystemConfig | null;
	loading: boolean;
	error: string | null;
	lastFetch: Date | null;
}

// Create reactive state
let state = $state<ConfigState>({
	config: null,
	loading: false,
	error: null,
	lastFetch: null
});

// Computed values
const integrations = $derived(state.config?.integrations ?? []);

const emailAccounts = $derived(state.config?.email_accounts ?? []);

const teamsEnabled = $derived(state.config?.teams_enabled ?? false);

const calendarEnabled = $derived(state.config?.calendar_enabled ?? false);

// Actions
async function fetchConfig(): Promise<void> {
	state.loading = true;
	state.error = null;

	try {
		const config = await getConfig();
		state.config = config;
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
		console.error('Failed to fetch config:', err);
	} finally {
		state.loading = false;
	}
}

async function refresh(): Promise<void> {
	await fetchConfig();
}

function clearError(): void {
	state.error = null;
}

// Export reactive getters and actions
export const configStore = {
	get state() {
		return state;
	},
	get config() {
		return state.config;
	},
	get integrations() {
		return integrations;
	},
	get emailAccounts() {
		return emailAccounts;
	},
	get teamsEnabled() {
		return teamsEnabled;
	},
	get calendarEnabled() {
		return calendarEnabled;
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
	fetchConfig,
	refresh,
	clearError
};

export type { IntegrationStatus };
