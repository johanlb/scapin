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

// ============================================================================
// STATS OVERVIEW & BY-SOURCE TYPES
// ============================================================================

interface StatsOverview {
	total_processed: number;
	total_pending: number;
	sources_active: number;
	uptime_seconds: number;
	last_activity: string | null;
	email_processed: number;
	email_queued: number;
	teams_messages: number;
	teams_unread: number;
	calendar_events_today: number;
	calendar_events_week: number;
	notes_due: number;
	notes_reviewed_today: number;
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

interface TeamsStats {
	total_chats: number;
	unread_chats: number;
	messages_processed: number;
	messages_flagged: number;
	last_poll: string | null;
}

interface CalendarStats {
	events_today: number;
	events_week: number;
	meetings_online: number;
	meetings_in_person: number;
	last_poll: string | null;
}

interface QueueStats {
	total: number;
	by_status: Record<string, number>;
	by_account: Record<string, number>;
	oldest_item: string | null;
	newest_item: string | null;
}

interface NotesReviewStats {
	total_notes: number;
	by_type: Record<string, number>;
	by_importance: Record<string, number>;
	total_due: number;
	reviewed_today: number;
	avg_easiness_factor: number;
}

interface StatsBySource {
	email: EmailStats | null;
	teams: TeamsStats | null;
	calendar: CalendarStats | null;
	queue: QueueStats | null;
	notes: NotesReviewStats | null;
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

export async function getStatsOverview(): Promise<StatsOverview> {
	return fetchApi<StatsOverview>('/stats/overview');
}

export async function getStatsBySource(): Promise<StatsBySource> {
	return fetchApi<StatsBySource>('/stats/by-source');
}

export async function getConfig(): Promise<SystemConfig> {
	return fetchApi<SystemConfig>('/config');
}

// Briefing endpoints
export async function getMorningBriefing(): Promise<MorningBriefing> {
	return fetchApi<MorningBriefing>('/briefing/morning');
}

export async function getPreMeetingBriefing(
	eventId: string,
	signal?: AbortSignal
): Promise<PreMeetingBriefing> {
	return fetchApi<PreMeetingBriefing>(`/briefing/meeting/${encodeURIComponent(eventId)}`, {
		signal
	});
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

// ============================================================================
// NOTES TYPES
// ============================================================================

interface NoteEntity {
	type: string;
	value: string;
	confidence: number;
}

interface Note {
	note_id: string;
	title: string;
	content: string;
	excerpt: string;
	path: string;
	tags: string[];
	entities: NoteEntity[];
	created_at: string;
	updated_at: string;
	pinned: boolean;
	metadata: Record<string, unknown>;
}

interface FolderNode {
	name: string;
	path: string;
	note_count: number;
	children: FolderNode[];
}

interface NotesTree {
	folders: FolderNode[];
	pinned: Note[];
	recent: Note[];
	total_notes: number;
}

interface NoteSearchResult {
	note: Note;
	score: number;
	highlights: string[];
}

interface NoteSearchResponse {
	query: string;
	results: NoteSearchResult[];
	total: number;
}

interface WikilinkInfo {
	text: string;
	target_id: string | null;
	target_title: string | null;
	exists: boolean;
}

interface NoteLinks {
	note_id: string;
	outgoing: WikilinkInfo[];
	incoming: WikilinkInfo[];
}

interface NoteSyncStatus {
	last_sync: string | null;
	syncing: boolean;
	notes_synced: number;
	errors: string[];
}

// ============================================================================
// NOTES REVIEW TYPES (SM-2 Spaced Repetition)
// ============================================================================

interface NoteReviewMetadata {
	note_id: string;
	note_type: string;
	easiness_factor: number;
	repetition_number: number;
	interval_hours: number;
	next_review: string | null;
	last_quality: number | null;
	review_count: number;
	auto_enrich: boolean;
	importance: string;
}

interface NotesDueResponse {
	notes: NoteReviewMetadata[];
	total: number;
}

interface ReviewStatsResponse {
	total_notes: number;
	by_type: Record<string, number>;
	by_importance: Record<string, number>;
	total_due: number;
	reviewed_today: number;
	avg_easiness_factor: number;
}

interface ReviewWorkloadResponse {
	workload: Record<string, number>;
	total_upcoming: number;
}

interface RecordReviewResponse {
	note_id: string;
	quality: number;
	new_easiness_factor: number;
	new_interval_hours: number;
	new_repetition_number: number;
	next_review: string;
	quality_assessment: string;
}

interface PostponeReviewResponse {
	note_id: string;
	hours_postponed: number;
	new_next_review: string;
}

interface TriggerReviewResponse {
	note_id: string;
	triggered: boolean;
	next_review: string;
}

// ============================================================================
// NOTES API FUNCTIONS
// ============================================================================

export async function getNotesTree(recentLimit = 10): Promise<NotesTree> {
	return fetchApi<NotesTree>(`/notes/tree?recent_limit=${recentLimit}`);
}

export async function listNotes(
	page = 1,
	pageSize = 20,
	path?: string,
	tags?: string[],
	pinnedOnly = false
): Promise<PaginatedResponse<Note[]>> {
	const params = new URLSearchParams({
		page: String(page),
		page_size: String(pageSize)
	});
	if (path) params.set('path', path);
	if (tags?.length) params.set('tags', tags.join(','));
	if (pinnedOnly) params.set('pinned', 'true');

	const url = `${API_BASE}/notes?${params}`;
	const response = await fetch(url, {
		headers: {
			'Content-Type': 'application/json',
			...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {})
		}
	});
	return response.json();
}

export async function getNote(noteId: string): Promise<Note> {
	return fetchApi<Note>(`/notes/${encodeURIComponent(noteId)}`);
}

export async function getNoteLinks(noteId: string): Promise<NoteLinks> {
	return fetchApi<NoteLinks>(`/notes/${encodeURIComponent(noteId)}/links`);
}

export async function createNote(
	title: string,
	content: string,
	path = '',
	tags: string[] = [],
	pinned = false
): Promise<Note> {
	return fetchApi<Note>('/notes', {
		method: 'POST',
		body: JSON.stringify({ title, content, path, tags, pinned })
	});
}

export async function updateNote(
	noteId: string,
	updates: {
		title?: string;
		content?: string;
		path?: string;
		tags?: string[];
		pinned?: boolean;
	}
): Promise<Note> {
	return fetchApi<Note>(`/notes/${encodeURIComponent(noteId)}`, {
		method: 'PATCH',
		body: JSON.stringify(updates)
	});
}

export async function toggleNotePin(noteId: string): Promise<Note> {
	return fetchApi<Note>(`/notes/${encodeURIComponent(noteId)}/pin`, {
		method: 'POST'
	});
}

export async function deleteNote(noteId: string): Promise<void> {
	await fetchApi<null>(`/notes/${encodeURIComponent(noteId)}`, {
		method: 'DELETE'
	});
}

export async function searchNotes(
	query: string,
	tags?: string[],
	limit = 20
): Promise<NoteSearchResponse> {
	const params = new URLSearchParams({
		q: query,
		limit: String(limit)
	});
	if (tags?.length) params.set('tags', tags.join(','));

	return fetchApi<NoteSearchResponse>(`/notes/search?${params}`);
}

export async function getNoteSyncStatus(): Promise<NoteSyncStatus> {
	return fetchApi<NoteSyncStatus>('/notes/sync/status');
}

export async function syncAppleNotes(): Promise<NoteSyncStatus> {
	return fetchApi<NoteSyncStatus>('/notes/sync', { method: 'POST' });
}

// ============================================================================
// NOTES VERSION TYPES (Git Versioning)
// ============================================================================

interface NoteVersion {
	version_id: string;
	full_hash: string;
	message: string;
	timestamp: string;
	author: string;
}

interface NoteVersionsResponse {
	note_id: string;
	versions: NoteVersion[];
	total: number;
}

interface NoteVersionContent {
	note_id: string;
	version_id: string;
	content: string;
	timestamp: string;
}

interface NoteDiff {
	note_id: string;
	from_version: string;
	to_version: string;
	additions: number;
	deletions: number;
	diff_text: string;
}

// ============================================================================
// NOTES VERSION API FUNCTIONS (Git Versioning)
// ============================================================================

export async function getNoteVersions(noteId: string, limit = 50): Promise<NoteVersionsResponse> {
	return fetchApi<NoteVersionsResponse>(
		`/notes/${encodeURIComponent(noteId)}/versions?limit=${limit}`
	);
}

export async function getNoteVersionContent(
	noteId: string,
	versionId: string
): Promise<NoteVersionContent> {
	return fetchApi<NoteVersionContent>(
		`/notes/${encodeURIComponent(noteId)}/versions/${encodeURIComponent(versionId)}`
	);
}

export async function diffNoteVersions(
	noteId: string,
	v1: string,
	v2: string
): Promise<NoteDiff> {
	const params = new URLSearchParams({ v1, v2 });
	return fetchApi<NoteDiff>(`/notes/${encodeURIComponent(noteId)}/diff?${params}`);
}

export async function restoreNoteVersion(noteId: string, versionId: string): Promise<Note> {
	return fetchApi<Note>(
		`/notes/${encodeURIComponent(noteId)}/restore/${encodeURIComponent(versionId)}`,
		{ method: 'POST' }
	);
}

// ============================================================================
// GLOBAL SEARCH TYPES
// ============================================================================

type SearchResultType = 'note' | 'email' | 'calendar' | 'teams';

interface SearchResultBase {
	id: string;
	type: SearchResultType;
	title: string;
	excerpt: string;
	score: number;
	timestamp: string;
	metadata: Record<string, unknown>;
}

interface GlobalNoteSearchResult extends SearchResultBase {
	type: 'note';
	path: string;
	tags: string[];
}

interface GlobalEmailSearchResult extends SearchResultBase {
	type: 'email';
	from_address: string;
	from_name: string;
	status: string;
}

interface GlobalCalendarSearchResult extends SearchResultBase {
	type: 'calendar';
	start: string;
	end: string;
	location: string;
	organizer: string;
}

interface GlobalTeamsSearchResult extends SearchResultBase {
	type: 'teams';
	chat_id: string;
	sender: string;
}

interface SearchResultsByType {
	notes: GlobalNoteSearchResult[];
	emails: GlobalEmailSearchResult[];
	calendar: GlobalCalendarSearchResult[];
	teams: GlobalTeamsSearchResult[];
}

interface SearchResultCounts {
	notes: number;
	emails: number;
	calendar: number;
	teams: number;
}

interface GlobalSearchResponse {
	query: string;
	results: SearchResultsByType;
	total: number;
	counts: SearchResultCounts;
	search_time_ms: number;
}

interface RecentSearchItem {
	query: string;
	timestamp: string;
	result_count: number;
}

interface RecentSearchesResponse {
	searches: RecentSearchItem[];
	total: number;
}

// ============================================================================
// GLOBAL SEARCH API FUNCTIONS
// ============================================================================

export async function globalSearch(
	query: string,
	options?: {
		types?: SearchResultType[];
		limit?: number;
		dateFrom?: string;
		dateTo?: string;
	}
): Promise<GlobalSearchResponse> {
	const params = new URLSearchParams({ q: query });
	if (options?.types?.length) params.set('types', options.types.join(','));
	if (options?.limit) params.set('limit', String(options.limit));
	if (options?.dateFrom) params.set('date_from', options.dateFrom);
	if (options?.dateTo) params.set('date_to', options.dateTo);
	return fetchApi<GlobalSearchResponse>(`/search?${params}`);
}

export async function getRecentSearches(limit = 20): Promise<RecentSearchesResponse> {
	return fetchApi<RecentSearchesResponse>(`/search/recent?limit=${limit}`);
}

// ============================================================================
// NOTES REVIEW API FUNCTIONS (SM-2 Spaced Repetition)
// ============================================================================

export async function getNotesDue(limit = 50, noteType?: string): Promise<NotesDueResponse> {
	const params = new URLSearchParams({ limit: String(limit) });
	if (noteType) params.set('note_type', noteType);
	return fetchApi<NotesDueResponse>(`/notes/reviews/due?${params}`);
}

export async function getReviewStats(): Promise<ReviewStatsResponse> {
	return fetchApi<ReviewStatsResponse>('/notes/reviews/stats');
}

export async function getReviewWorkload(days = 7): Promise<ReviewWorkloadResponse> {
	return fetchApi<ReviewWorkloadResponse>(`/notes/reviews/workload?days=${days}`);
}

export async function getNoteReviewMetadata(noteId: string): Promise<NoteReviewMetadata> {
	return fetchApi<NoteReviewMetadata>(`/notes/${encodeURIComponent(noteId)}/metadata`);
}

export async function recordReview(noteId: string, quality: number): Promise<RecordReviewResponse> {
	return fetchApi<RecordReviewResponse>(`/notes/${encodeURIComponent(noteId)}/review`, {
		method: 'POST',
		body: JSON.stringify({ quality })
	});
}

export async function postponeReview(
	noteId: string,
	hours: number
): Promise<PostponeReviewResponse> {
	return fetchApi<PostponeReviewResponse>(`/notes/${encodeURIComponent(noteId)}/postpone`, {
		method: 'POST',
		body: JSON.stringify({ hours })
	});
}

export async function triggerReview(noteId: string): Promise<TriggerReviewResponse> {
	return fetchApi<TriggerReviewResponse>(`/notes/${encodeURIComponent(noteId)}/trigger`, {
		method: 'POST'
	});
}

// Export types for use in components
export type {
	ApiResponse,
	HealthCheck,
	HealthStatus,
	Stats,
	StatsOverview,
	StatsBySource,
	CalendarStats,
	NotesReviewStats,
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
	TeamsPollResult,
	// Notes types
	Note,
	NoteEntity,
	FolderNode,
	NotesTree,
	NoteSearchResult,
	NoteSearchResponse,
	WikilinkInfo,
	NoteLinks,
	NoteSyncStatus,
	// Notes Review types (SM-2)
	NoteReviewMetadata,
	NotesDueResponse,
	ReviewStatsResponse,
	ReviewWorkloadResponse,
	RecordReviewResponse,
	PostponeReviewResponse,
	TriggerReviewResponse,
	// Notes Version types (Git)
	NoteVersion,
	NoteVersionsResponse,
	NoteVersionContent,
	NoteDiff,
	// Global Search types
	SearchResultType,
	SearchResultBase,
	GlobalNoteSearchResult,
	GlobalEmailSearchResult,
	GlobalCalendarSearchResult,
	GlobalTeamsSearchResult,
	SearchResultsByType,
	SearchResultCounts,
	GlobalSearchResponse,
	RecentSearchItem,
	RecentSearchesResponse
};

export { ApiError };
