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
	retryCount: number;
}

// Retry configuration
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 1000; // Start with 1 second, will double each retry

// Create reactive state
let state = $state<AuthState>({
	isAuthenticated: false,
	user: null,
	authRequired: true,
	loading: false,
	error: null,
	initialized: false,
	backendAvailable: true,
	retryCount: 0
});

// Computed values
const needsLogin = $derived(state.authRequired && !state.isAuthenticated);

/**
 * Helper to delay execution
 */
function delay(ms: number): Promise<void> {
	return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Make an API call with automatic retry on network errors
 */
async function withRetry<T>(
	fn: () => Promise<T>,
	maxAttempts: number = MAX_RETRY_ATTEMPTS
): Promise<T> {
	let lastError: unknown;

	for (let attempt = 0; attempt < maxAttempts; attempt++) {
		try {
			state.retryCount = attempt;
			const result = await fn();
			state.retryCount = 0;
			state.backendAvailable = true;
			return result;
		} catch (err) {
			lastError = err;

			// Only retry on network errors (status 0 or 503)
			const isNetworkError = err instanceof ApiError && (err.status === 0 || err.status === 503);

			if (!isNetworkError || attempt >= maxAttempts - 1) {
				// Not a network error or last attempt - throw
				throw err;
			}

			// Wait before retrying with exponential backoff
			const delayMs = RETRY_DELAY_MS * Math.pow(2, attempt);
			console.log(`[Auth] Network error, retrying in ${delayMs}ms (attempt ${attempt + 1}/${maxAttempts})`);
			await delay(delayMs);
		}
	}

	throw lastError;
}

/**
 * Initialize auth state from stored token
 * Call this once on app startup
 * Includes automatic retry on network errors
 */
async function initialize(): Promise<void> {
	console.log('[Auth] initialize() called, already initialized:', state.initialized);
	if (state.initialized) return;

	state.loading = true;
	state.backendAvailable = true; // Assume available initially

	try {
		// Check if we have a stored token
		const token = getAuthToken();
		console.log('[Auth] Token found:', token ? 'yes' : 'no');

		// Use retry wrapper for checkAuth
		const result = await withRetry(() => checkAuth());
		console.log('[Auth] checkAuth result:', result);

		state.authRequired = result.auth_required;
		state.isAuthenticated = result.authenticated;
		state.user = result.authenticated ? result.user : null;
		state.backendAvailable = true;
	} catch (err) {
		console.error('[Auth] initialize() error after retries:', err);
		if (err instanceof ApiError && err.status === 401) {
			// Token is invalid or missing - auth is required
			apiLogout();
			state.isAuthenticated = false;
			state.user = null;
			state.authRequired = true;
			state.backendAvailable = true; // 401 means backend IS available
		} else if (err instanceof ApiError && (err.status === 0 || err.status === 503)) {
			// Network error - server unreachable after retries
			console.error('Server unreachable after retries:', err);
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
		state.retryCount = 0;
		console.log('[Auth] initialize() complete, final state:', {
			isAuthenticated: state.isAuthenticated,
			authRequired: state.authRequired,
			backendAvailable: state.backendAvailable,
			initialized: state.initialized
		});
	}
}

/**
 * Login with PIN code
 * Includes automatic retry on network errors
 */
async function login(pin: string): Promise<boolean> {
	state.loading = true;
	state.error = null;
	state.backendAvailable = true; // Reset to assume available

	try {
		console.log('[Auth] Starting login...');

		// Use retry wrapper for the login API call
		await withRetry(() => apiLogin(pin));
		console.log('[Auth] Token obtained, verifying...');

		// Verify the login worked (also with retry)
		const result = await withRetry(() => checkAuth());
		console.log('[Auth] checkAuth result:', result);
		state.isAuthenticated = result.authenticated;
		state.user = result.user;
		state.backendAvailable = true;
		console.log('[Auth] State updated:', { isAuthenticated: state.isAuthenticated, user: state.user, needsLogin });
		return true;
	} catch (err) {
		console.error('[Auth] Login error after retries:', err);
		if (err instanceof ApiError) {
			if (err.status === 0 || err.status === 503) {
				state.backendAvailable = false;
				state.error = 'Backend non disponible après plusieurs tentatives. Vérifiez que le serveur est lancé.';
			} else if (err.status === 401) {
				state.error = 'PIN incorrect';
				state.backendAvailable = true; // 401 means backend IS available
			} else if (err.status === 422) {
				state.error = 'PIN invalide (4-6 chiffres)';
				state.backendAvailable = true; // 422 means backend IS available
			} else {
				state.error = `Erreur: ${err.message}`;
				state.backendAvailable = true; // Other errors mean backend responded
			}
		} else {
			state.error = 'Erreur de connexion au serveur';
		}
		return false;
	} finally {
		state.loading = false;
		state.retryCount = 0;
	}
}

/**
 * Retry connection to backend
 * Uses automatic retry with exponential backoff
 */
async function retryConnection(): Promise<boolean> {
	state.loading = true;
	state.error = null;
	state.backendAvailable = true; // Reset assumption

	try {
		const result = await withRetry(() => checkAuth());
		state.backendAvailable = true;
		state.authRequired = result.auth_required;
		state.isAuthenticated = result.authenticated;
		state.user = result.authenticated ? result.user : null;
		return true;
	} catch (err) {
		if (err instanceof ApiError && (err.status === 0 || err.status === 503)) {
			state.backendAvailable = false;
			state.error = 'Backend toujours non disponible après plusieurs tentatives';
		}
		return false;
	} finally {
		state.loading = false;
		state.retryCount = 0;
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

/**
 * Reset state to allow re-initialization
 * Useful when backend becomes available after being unavailable
 */
function resetState(): void {
	state.initialized = false;
	state.backendAvailable = true;
	state.error = null;
	state.retryCount = 0;
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
	get retryCount() { return state.retryCount; },
	initialize,
	login,
	logout,
	clearError,
	retryConnection,
	resetState
};
