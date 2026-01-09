/**
 * Auth Store
 * Manages authentication state using Svelte 5 runes
 */
import { login as apiLogin, checkAuth, logout as apiLogout, getAuthToken, ApiError } from '$lib/api';
import type { AuthCheckResponse } from '$lib/api';

interface AuthState {
	isAuthenticated: boolean;
	user: string | null;
	authRequired: boolean;
	loading: boolean;
	error: string | null;
	initialized: boolean;
	backendAvailable: boolean;
}

// Create reactive state
let state = $state<AuthState>({
	isAuthenticated: false,
	user: null,
	authRequired: true,
	loading: false,
	error: null,
	initialized: false,
	backendAvailable: true
});

// Computed values
const needsLogin = $derived(state.authRequired && !state.isAuthenticated);

/**
 * Initialize auth state from stored token
 * Call this once on app startup
 */
async function initialize(): Promise<void> {
	if (state.initialized) return;

	state.loading = true;

	try {
		// Check if we have a stored token
		const token = getAuthToken();
		if (!token) {
			// No token, check if auth is required
			const result = await checkAuth();
			state.authRequired = result.auth_required;
			state.isAuthenticated = result.authenticated;
			state.user = result.authenticated ? result.user : null;
		} else {
			// Have token, verify it's still valid
			const result = await checkAuth();
			state.isAuthenticated = result.authenticated;
			state.user = result.authenticated ? result.user : null;
			state.authRequired = result.auth_required;
		}
	} catch (err) {
		if (err instanceof ApiError && err.status === 401) {
			// Token is invalid or missing - auth is required
			apiLogout();
			state.isAuthenticated = false;
			state.user = null;
			state.authRequired = true;
			state.backendAvailable = true;
		} else if (err instanceof ApiError && err.status === 0) {
			// Network error - server unreachable
			console.error('Server unreachable:', err);
			state.backendAvailable = false;
			state.authRequired = true;
			state.error = 'Backend non disponible. Lancez: ./scripts/dev.sh';
		} else {
			// Other error - assume auth is required
			console.error('Failed to check auth status:', err);
			state.authRequired = true;
			state.backendAvailable = true;
		}
	} finally {
		state.loading = false;
		state.initialized = true;
	}
}

/**
 * Login with PIN code
 */
async function login(pin: string): Promise<boolean> {
	state.loading = true;
	state.error = null;

	try {
		await apiLogin(pin);
		// Verify the login worked
		const result = await checkAuth();
		state.isAuthenticated = result.authenticated;
		state.user = result.user;
		return true;
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 0) {
				state.backendAvailable = false;
				state.error = 'Backend non disponible. Lancez: ./scripts/dev.sh';
			} else if (err.status === 401) {
				state.error = 'PIN incorrect';
			} else if (err.status === 422) {
				state.error = 'PIN invalide (4-6 chiffres)';
			} else {
				state.error = `Erreur: ${err.message}`;
			}
		} else {
			state.error = 'Erreur de connexion au serveur';
		}
		return false;
	} finally {
		state.loading = false;
	}
}

/**
 * Retry connection to backend
 */
async function retryConnection(): Promise<boolean> {
	state.loading = true;
	state.error = null;

	try {
		const result = await checkAuth();
		state.backendAvailable = true;
		state.authRequired = result.auth_required;
		state.isAuthenticated = result.authenticated;
		state.user = result.authenticated ? result.user : null;
		return true;
	} catch (err) {
		if (err instanceof ApiError && err.status === 0) {
			state.backendAvailable = false;
			state.error = 'Backend toujours non disponible';
		}
		return false;
	} finally {
		state.loading = false;
	}
}

/**
 * Logout and clear auth state
 */
function logout(): void {
	apiLogout();
	state.isAuthenticated = false;
	state.user = null;
	state.error = null;
}

/**
 * Clear error message
 */
function clearError(): void {
	state.error = null;
}

// Export reactive getters and actions
export const authStore = {
	get state() { return state; },
	get isAuthenticated() { return state.isAuthenticated; },
	get user() { return state.user; },
	get authRequired() { return state.authRequired; },
	get loading() { return state.loading; },
	get error() { return state.error; },
	get initialized() { return state.initialized; },
	get needsLogin() { return needsLogin; },
	get backendAvailable() { return state.backendAvailable; },
	initialize,
	login,
	logout,
	clearError,
	retryConnection
};
