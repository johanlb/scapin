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

interface IntegrationStatus {
	id: string;
	name: string;
	icon: string;
	status: 'connected' | 'disconnected' | 'syncing' | 'error';
	last_sync: string | null;
}

interface SystemConfig {
	email_accounts: { name: string; email: string; enabled: boolean }[];
	ai_model: string;
	teams_enabled: boolean;
	calendar_enabled: boolean;
	briefing_enabled: boolean;
	integrations: IntegrationStatus[];
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

export async function getConfig(): Promise<SystemConfig> {
	return fetchApi<SystemConfig>('/config');
}

// Briefing endpoints
export async function getMorningBriefing(): Promise<MorningBriefing> {
	return fetchApi<MorningBriefing>('/briefing/morning');
}

export async function getPreMeetingBriefing(eventId: string): Promise<PreMeetingBriefing> {
	return fetchApi<PreMeetingBriefing>(`/briefing/meeting/${encodeURIComponent(eventId)}`);
}

// ============================================================================
// JOURNAL TYPES
// ============================================================================

interface EmailSummary {
	email_id: string;
	from_address: string;
	from_name: string | null;
	subject: string;
	action: string;
	category: string;
	confidence: number;
	reasoning: string | null;
	processed_at: string;
}

interface TaskSummary {
	task_id: string;
	title: string;
	source_email_id: string | null;
	project: string | null;
	due_date: string | null;
	created_at: string;
}

interface TeamsSummary {
	message_id: string;
	chat_name: string;
	sender: string;
	preview: string;
	action: string;
	confidence: number;
	processed_at: string;
}

interface CalendarSummary {
	event_id: string;
	title: string;
	start_time: string;
	end_time: string;
	action: string;
	attendees: string[];
	location: string | null;
	is_online: boolean;
	notes: string | null;
}

interface OmniFocusSummary {
	task_id: string;
	title: string;
	project: string | null;
	status: string;
	tags: string[];
	completed_at: string | null;
	due_date: string | null;
	flagged: boolean;
	estimated_minutes: number | null;
}

interface JournalQuestion {
	question_id: string;
	category: string;
	question_text: string;
	context: string | null;
	options: string[];
	priority: number;
	related_email_id: string | null;
	related_entity: string | null;
	answer: string | null;
}

interface JournalCorrection {
	email_id: string;
	original_action: string;
	corrected_action: string | null;
	original_category: string | null;
	corrected_category: string | null;
	reason: string | null;
}

interface JournalEntry {
	entry_id: string;
	journal_date: string;
	created_at: string;
	status: string;
	emails_count: number;
	tasks_count: number;
	teams_count: number;
	calendar_count: number;
	omnifocus_count: number;
	questions_count: number;
	corrections_count: number;
	emails_processed: EmailSummary[];
	tasks_created: TaskSummary[];
	teams_messages: TeamsSummary[];
	calendar_events: CalendarSummary[];
	omnifocus_items: OmniFocusSummary[];
	questions: JournalQuestion[];
	corrections: JournalCorrection[];
	average_confidence: number;
	unanswered_questions: number;
}

interface JournalListItem {
	entry_id: string;
	journal_date: string;
	status: string;
	emails_count: number;
	questions_count: number;
	corrections_count: number;
	average_confidence: number;
	completed_at: string | null;
}

interface Pattern {
	pattern_type: string;
	description: string;
	frequency: number;
	confidence: number;
	examples: string[];
}

interface WeeklyReview {
	week_start: string;
	week_end: string;
	daily_entry_count: number;
	patterns_detected: Pattern[];
	productivity_score: number;
	top_categories: [string, number][];
	suggestions: string[];
	emails_total: number;
	tasks_total: number;
	corrections_total: number;
	accuracy_rate: number;
}

interface MonthlyReview {
	month: string;
	weekly_review_count: number;
	trends: string[];
	goals_progress: Record<string, number>;
	calibration_summary: Record<string, number>;
	productivity_average: number;
}

interface SourceCalibration {
	source: string;
	total_items: number;
	correct_decisions: number;
	incorrect_decisions: number;
	accuracy: number;
	correction_rate: number;
	average_confidence: number;
	last_updated: string;
}

interface Calibration {
	sources: Record<string, SourceCalibration>;
	overall_accuracy: number;
	recommended_threshold_adjustment: number;
	patterns_learned: number;
}

interface PaginatedResponse<T> {
	success: boolean;
	data: T;
	total: number;
	page: number;
	page_size: number;
	has_more: boolean;
}

// ============================================================================
// JOURNAL API FUNCTIONS
// ============================================================================

export async function getJournal(date: string, generate = false): Promise<JournalEntry> {
	const params = generate ? '?generate=true' : '';
	return fetchApi<JournalEntry>(`/journal/${date}${params}`);
}

export async function listJournals(
	page = 1,
	pageSize = 10,
	startDate?: string,
	endDate?: string
): Promise<PaginatedResponse<JournalListItem[]>> {
	const params = new URLSearchParams({
		page: String(page),
		page_size: String(pageSize)
	});
	if (startDate) params.set('start_date', startDate);
	if (endDate) params.set('end_date', endDate);

	const url = `${API_BASE}/journal/list?${params}`;
	const response = await fetch(url, {
		headers: {
			'Content-Type': 'application/json',
			...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {})
		}
	});
	return response.json();
}

export async function answerQuestion(
	date: string,
	questionId: string,
	answer: string
): Promise<JournalEntry> {
	return fetchApi<JournalEntry>(`/journal/${date}/answer`, {
		method: 'POST',
		body: JSON.stringify({ question_id: questionId, answer })
	});
}

export async function submitCorrection(
	date: string,
	emailId: string,
	correctedAction?: string,
	correctedCategory?: string,
	reason?: string
): Promise<JournalEntry> {
	return fetchApi<JournalEntry>(`/journal/${date}/correction`, {
		method: 'POST',
		body: JSON.stringify({
			email_id: emailId,
			corrected_action: correctedAction,
			corrected_category: correctedCategory,
			reason
		})
	});
}

export async function completeJournal(date: string): Promise<JournalEntry> {
	return fetchApi<JournalEntry>(`/journal/${date}/complete`, {
		method: 'POST'
	});
}

export async function getWeeklyReview(weekStart: string): Promise<WeeklyReview> {
	return fetchApi<WeeklyReview>(`/journal/weekly/${weekStart}`);
}

export async function getMonthlyReview(month: string): Promise<MonthlyReview> {
	return fetchApi<MonthlyReview>(`/journal/monthly/${month}`);
}

export async function getCalibration(): Promise<Calibration> {
	return fetchApi<Calibration>('/journal/calibration');
}

export async function exportJournal(
	date: string,
	format: 'markdown' | 'json' | 'html' = 'markdown'
): Promise<string> {
	return fetchApi<string>(`/journal/${date}/export`, {
		method: 'POST',
		body: JSON.stringify({ format })
	});
}

// ============================================================================
// QUEUE TYPES
// ============================================================================

interface QueueItemMetadata {
	id: string;
	subject: string;
	from_address: string;
	from_name: string;
	date: string | null;
	has_attachments: boolean;
	folder: string | null;
}

interface ActionOption {
	action: string;
	destination: string | null;
	confidence: number;
	reasoning: string;
	reasoning_detailed: string | null;
	is_recommended: boolean;
}

interface QueueItemAnalysis {
	action: string;
	confidence: number;
	category: string | null;
	reasoning: string;
	summary: string | null;
	options: ActionOption[];
}

interface QueueItem {
	id: string;
	account_id: string | null;
	queued_at: string;
	metadata: QueueItemMetadata;
	analysis: QueueItemAnalysis;
	content: { preview: string };
	status: string;
	reviewed_at: string | null;
	review_decision: string | null;
}

interface QueueStats {
	total: number;
	by_status: Record<string, number>;
	by_account: Record<string, number>;
	oldest_item: string | null;
	newest_item: string | null;
}

// ============================================================================
// QUEUE API FUNCTIONS
// ============================================================================

export async function listQueueItems(
	page = 1,
	pageSize = 20,
	status = 'pending',
	accountId?: string
): Promise<PaginatedResponse<QueueItem[]>> {
	const params = new URLSearchParams({
		page: String(page),
		page_size: String(pageSize),
		status
	});
	if (accountId) params.set('account_id', accountId);

	const url = `${API_BASE}/queue?${params}`;
	const response = await fetch(url, {
		headers: {
			'Content-Type': 'application/json',
			...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {})
		}
	});
	return response.json();
}

export async function getQueueItem(itemId: string): Promise<QueueItem> {
	return fetchApi<QueueItem>(`/queue/${itemId}`);
}

export async function getQueueStats(): Promise<QueueStats> {
	return fetchApi<QueueStats>('/queue/stats');
}

export async function approveQueueItem(
	itemId: string,
	modifiedAction?: string,
	modifiedCategory?: string,
	destination?: string | null
): Promise<QueueItem> {
	return fetchApi<QueueItem>(`/queue/${itemId}/approve`, {
		method: 'POST',
		body: JSON.stringify({
			modified_action: modifiedAction,
			modified_category: modifiedCategory,
			destination: destination
		})
	});
}

export async function modifyQueueItem(
	itemId: string,
	action: string,
	options?: {
		destination?: string;
		category?: string;
		reasoning?: string;
		selectedOptionIndex?: number;
		customInstruction?: string;
	}
): Promise<QueueItem> {
	return fetchApi<QueueItem>(`/queue/${itemId}/modify`, {
		method: 'POST',
		body: JSON.stringify({
			action,
			destination: options?.destination,
			category: options?.category,
			reasoning: options?.reasoning,
			selected_option_index: options?.selectedOptionIndex,
			custom_instruction: options?.customInstruction
		})
	});
}

export async function rejectQueueItem(itemId: string, reason?: string): Promise<QueueItem> {
	return fetchApi<QueueItem>(`/queue/${itemId}/reject`, {
		method: 'POST',
		body: JSON.stringify({ reason })
	});
}

export async function deleteQueueItem(itemId: string): Promise<{ deleted: string }> {
	return fetchApi<{ deleted: string }>(`/queue/${itemId}`, {
		method: 'DELETE'
	});
}

// ============================================================================
// EMAIL TYPES
// ============================================================================

interface EmailAccount {
	name: string;
	email: string;
	enabled: boolean;
	inbox_folder: string;
}

interface EmailStats {
	emails_processed: number;
	emails_auto_executed: number;
	emails_archived: number;
	emails_deleted: number;
	emails_queued: number;
	emails_skipped: number;
	tasks_created: number;
	average_confidence: number;
	processing_mode: string;
}

interface ProcessedEmail {
	metadata: QueueItemMetadata;
	analysis: QueueItemAnalysis;
	processed_at: string;
	executed: boolean;
}

interface ProcessInboxResult {
	total_processed: number;
	auto_executed: number;
	queued: number;
	skipped: number;
	emails: ProcessedEmail[];
}

// ============================================================================
// EMAIL API FUNCTIONS
// ============================================================================

export async function getEmailAccounts(): Promise<EmailAccount[]> {
	return fetchApi<EmailAccount[]>('/email/accounts');
}

export async function getEmailStats(): Promise<EmailStats> {
	return fetchApi<EmailStats>('/email/stats');
}

export async function processInbox(
	limit?: number,
	autoExecute = false,
	confidenceThreshold?: number,
	unreadOnly = false
): Promise<ProcessInboxResult> {
	return fetchApi<ProcessInboxResult>('/email/process', {
		method: 'POST',
		body: JSON.stringify({
			limit,
			auto_execute: autoExecute,
			confidence_threshold: confidenceThreshold,
			unread_only: unreadOnly
		})
	});
}

export async function analyzeEmail(emailId: string, folder = 'INBOX'): Promise<ProcessedEmail> {
	return fetchApi<ProcessedEmail>('/email/analyze', {
		method: 'POST',
		body: JSON.stringify({ email_id: emailId, folder })
	});
}

export async function executeEmailAction(
	emailId: string,
	action: string,
	destination?: string
): Promise<{ email_id: string; action: string; executed: boolean }> {
	return fetchApi<{ email_id: string; action: string; executed: boolean }>('/email/execute', {
		method: 'POST',
		body: JSON.stringify({ email_id: emailId, action, destination })
	});
}

// ============================================================================
// CALENDAR TYPES
// ============================================================================

interface CalendarAttendee {
	email: string;
	name: string | null;
	response_status: string;
	is_organizer: boolean;
}

interface CalendarEvent {
	id: string;
	title: string;
	start: string;
	end: string;
	location: string | null;
	is_online: boolean;
	meeting_url: string | null;
	organizer: string | null;
	attendees: CalendarAttendee[];
	is_all_day: boolean;
	is_recurring: boolean;
	description: string | null;
	status: string;
}

interface TodayEvents {
	date: string;
	total_events: number;
	meetings: number;
	all_day_events: number;
	events: CalendarEvent[];
}

interface CalendarPollResult {
	events_fetched: number;
	events_new: number;
	events_updated: number;
	polled_at: string;
}

// ============================================================================
// CALENDAR API FUNCTIONS
// ============================================================================

export async function listCalendarEvents(
	startDate?: string,
	endDate?: string,
	page = 1,
	pageSize = 20
): Promise<PaginatedResponse<CalendarEvent[]>> {
	const params = new URLSearchParams({
		page: String(page),
		page_size: String(pageSize)
	});
	if (startDate) params.set('start_date', startDate);
	if (endDate) params.set('end_date', endDate);

	const url = `${API_BASE}/calendar/events?${params}`;
	const response = await fetch(url, {
		headers: {
			'Content-Type': 'application/json',
			...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {})
		}
	});
	return response.json();
}

export async function getCalendarEvent(eventId: string): Promise<CalendarEvent> {
	return fetchApi<CalendarEvent>(`/calendar/events/${encodeURIComponent(eventId)}`);
}

export async function getTodayEvents(): Promise<TodayEvents> {
	return fetchApi<TodayEvents>('/calendar/today');
}

export async function respondToCalendarEvent(
	eventId: string,
	response: 'accept' | 'decline' | 'tentative',
	message?: string
): Promise<{ event_id: string; response: string; sent: boolean }> {
	return fetchApi<{ event_id: string; response: string; sent: boolean }>(
		`/calendar/events/${encodeURIComponent(eventId)}/respond`,
		{
			method: 'POST',
			body: JSON.stringify({ response, message })
		}
	);
}

export async function pollCalendar(): Promise<CalendarPollResult> {
	return fetchApi<CalendarPollResult>('/calendar/poll', { method: 'POST' });
}

// ============================================================================
// TEAMS TYPES
// ============================================================================

interface TeamsChat {
	id: string;
	topic: string | null;
	chat_type: string;
	created_at: string | null;
	last_message_at: string | null;
	member_count: number;
	unread_count: number;
}

interface TeamsSender {
	id: string;
	display_name: string;
	email: string | null;
}

interface TeamsMessage {
	id: string;
	chat_id: string;
	sender: TeamsSender;
	content: string;
	content_preview: string;
	created_at: string;
	is_read: boolean;
	importance: string;
	has_mentions: boolean;
	attachments_count: number;
}

interface TeamsStats {
	total_chats: number;
	unread_chats: number;
	messages_processed: number;
	messages_flagged: number;
	last_poll: string | null;
}

interface TeamsPollResult {
	messages_fetched: number;
	messages_new: number;
	chats_checked: number;
	polled_at: string;
}

// ============================================================================
// TEAMS API FUNCTIONS
// ============================================================================

export async function listTeamsChats(page = 1, pageSize = 20): Promise<PaginatedResponse<TeamsChat[]>> {
	const params = new URLSearchParams({
		page: String(page),
		page_size: String(pageSize)
	});

	const url = `${API_BASE}/teams/chats?${params}`;
	const response = await fetch(url, {
		headers: {
			'Content-Type': 'application/json',
			...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {})
		}
	});
	return response.json();
}

export async function listTeamsMessages(
	chatId: string,
	page = 1,
	pageSize = 20,
	since?: string
): Promise<PaginatedResponse<TeamsMessage[]>> {
	const params = new URLSearchParams({
		page: String(page),
		page_size: String(pageSize)
	});
	if (since) params.set('since', since);

	const url = `${API_BASE}/teams/chats/${encodeURIComponent(chatId)}/messages?${params}`;
	const response = await fetch(url, {
		headers: {
			'Content-Type': 'application/json',
			...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {})
		}
	});
	return response.json();
}

export async function replyToTeamsMessage(
	chatId: string,
	messageId: string,
	content: string
): Promise<{ chat_id: string; message_id: string; replied: boolean }> {
	return fetchApi<{ chat_id: string; message_id: string; replied: boolean }>(
		`/teams/chats/${encodeURIComponent(chatId)}/messages/${encodeURIComponent(messageId)}/reply`,
		{
			method: 'POST',
			body: JSON.stringify({ content })
		}
	);
}

export async function flagTeamsMessage(
	chatId: string,
	messageId: string,
	flag = true,
	reason?: string
): Promise<{ chat_id: string; message_id: string; flagged: boolean }> {
	return fetchApi<{ chat_id: string; message_id: string; flagged: boolean }>(
		`/teams/chats/${encodeURIComponent(chatId)}/messages/${encodeURIComponent(messageId)}/flag`,
		{
			method: 'POST',
			body: JSON.stringify({ flag, reason })
		}
	);
}

export async function pollTeams(): Promise<TeamsPollResult> {
	return fetchApi<TeamsPollResult>('/teams/poll', { method: 'POST' });
}

export async function getTeamsStats(): Promise<TeamsStats> {
	return fetchApi<TeamsStats>('/teams/stats');
}

// Export types for use in components
export type {
	ApiResponse,
	HealthCheck,
	HealthStatus,
	Stats,
	IntegrationStatus,
	SystemConfig,
	BriefingItem,
	MorningBriefing,
	AttendeeContext,
	PreMeetingBriefing,
	TokenResponse,
	AuthCheckResponse,
	// Journal types
	EmailSummary,
	TaskSummary,
	TeamsSummary,
	CalendarSummary,
	OmniFocusSummary,
	JournalQuestion,
	JournalCorrection,
	JournalEntry,
	JournalListItem,
	Pattern,
	WeeklyReview,
	MonthlyReview,
	SourceCalibration,
	Calibration,
	PaginatedResponse,
	// Queue types
	ActionOption,
	QueueItem,
	QueueItemMetadata,
	QueueItemAnalysis,
	QueueStats,
	// Email types
	EmailAccount,
	EmailStats,
	ProcessedEmail,
	ProcessInboxResult,
	// Calendar types
	CalendarAttendee,
	CalendarEvent,
	TodayEvents,
	CalendarPollResult,
	// Teams types
	TeamsChat,
	TeamsSender,
	TeamsMessage,
	TeamsStats,
	TeamsPollResult
};

export { ApiError };
