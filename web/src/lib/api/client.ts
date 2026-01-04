/**
 * Scapin API Client
 * Typed fetch wrappers for the FastAPI backend
 */

const API_BASE = '/api';

// Auth token storage
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
	authToken = token;
	if (token) {
		localStorage.setItem('scapin_token', token);
	} else {
		localStorage.removeItem('scapin_token');
	}
}

export function getAuthToken(): string | null {
	if (authToken) return authToken;
	if (typeof localStorage !== 'undefined') {
		authToken = localStorage.getItem('scapin_token');
	}
	return authToken;
}

export function clearAuthToken(): void {
	authToken = null;
	if (typeof localStorage !== 'undefined') {
		localStorage.removeItem('scapin_token');
	}
}

interface ApiResponse<T> {
	success: boolean;
	data: T | null;
	error: string | null;
	timestamp: string;
}

// Auth types
interface LoginRequest {
	pin: string;
}

interface TokenResponse {
	access_token: string;
	token_type: string;
	expires_in: number;
}

interface AuthCheckResponse {
	authenticated: boolean;
	user: string;
	auth_required: boolean;
}

interface HealthCheck {
	name: string;
	status: 'ok' | 'error' | 'warning';
	message?: string;
	latency_ms?: number | null;
}

interface HealthStatus {
	status: 'healthy' | 'degraded' | 'unhealthy';
	version: string;
	checks: HealthCheck[];
	uptime_seconds: number;
}

interface Stats {
	emails_processed: number;
	teams_messages: number;
	calendar_events: number;
	queue_size: number;
	uptime_seconds: number;
	last_activity: string | null;
}

interface BriefingItem {
	id: string;
	type: 'email' | 'teams' | 'calendar' | 'task';
	title: string;
	summary: string;
	urgency: 'high' | 'medium' | 'low';
	source: string;
	timestamp: string;
	metadata?: Record<string, unknown>;
}

interface MorningBriefing {
	date: string;
	generated_at: string;
	urgent_count: number;
	meetings_today: number;
	total_items: number;
	urgent_items: BriefingItem[];
	calendar_today: BriefingItem[];
	emails_pending: BriefingItem[];
	teams_unread: BriefingItem[];
	ai_summary: string | null;
	key_decisions: string[];
}

interface AttendeeContext {
	name: string;
	email: string;
	role?: string;
	recent_interactions: string[];
	notes?: string;
}

interface PreMeetingBriefing {
	event_id: string;
	title: string;
	start_time: string;
	end_time: string;
	attendees: AttendeeContext[];
	agenda?: string;
	related_emails: BriefingItem[];
	related_notes: string[];
	suggested_talking_points: string[];
}

class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
	const url = `${API_BASE}${endpoint}`;

	// Build headers with optional auth token
	const headers: HeadersInit = {
		'Content-Type': 'application/json',
		...options?.headers
	};

	const token = getAuthToken();
	if (token) {
		(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
	}

	try {
		const response = await fetch(url, {
			...options,
			headers
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new ApiError(response.status, errorData.detail || `HTTP ${response.status}`);
		}

		const data: ApiResponse<T> = await response.json();

		if (!data.success) {
			throw new ApiError(500, data.error || 'Unknown error');
		}

		if (data.data === null) {
			throw new ApiError(500, 'API returned null data');
		}

		return data.data;
	} catch (error) {
		if (error instanceof ApiError) {
			throw error;
		}
		// Network error or other fetch failure
		throw new ApiError(0, error instanceof Error ? error.message : 'Network error');
	}
}

// Auth endpoints
export async function login(pin: string): Promise<TokenResponse> {
	const response = await fetchApi<TokenResponse>('/auth/login', {
		method: 'POST',
		body: JSON.stringify({ pin })
	});
	// Store the token
	setAuthToken(response.access_token);
	return response;
}

export async function checkAuth(): Promise<AuthCheckResponse> {
	return fetchApi<AuthCheckResponse>('/auth/check');
}

export function logout(): void {
	clearAuthToken();
}

// System endpoints
export async function getHealth(): Promise<HealthStatus> {
	return fetchApi<HealthStatus>('/health');
}

export async function getStats(): Promise<Stats> {
	return fetchApi<Stats>('/stats');
}

// Briefing endpoints
export async function getMorningBriefing(): Promise<MorningBriefing> {
	return fetchApi<MorningBriefing>('/briefing/morning');
}

export async function getPreMeetingBriefing(eventId: string): Promise<PreMeetingBriefing> {
	return fetchApi<PreMeetingBriefing>(`/briefing/meeting/${encodeURIComponent(eventId)}`);
}

// Export types for use in components
export type {
	ApiResponse,
	HealthCheck,
	HealthStatus,
	Stats,
	BriefingItem,
	MorningBriefing,
	AttendeeContext,
	PreMeetingBriefing,
	TokenResponse,
	AuthCheckResponse
};

export { ApiError };
