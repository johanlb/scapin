/**
 * Core types for Scapin Web Interface
 */

// Event types matching backend
export type EventSource = 'email' | 'teams' | 'calendar' | 'omnifocus';
export type EventStatus = 'pending' | 'processed' | 'rejected' | 'snoozed';
export type UrgencyLevel = 'urgent' | 'high' | 'medium' | 'low';
export type ConfidenceLevel = 'high' | 'medium' | 'low';

// Calendar conflict types (mirror of API types)
export interface CalendarConflict {
	conflict_type: 'overlap_full' | 'overlap_partial' | 'travel_time';
	severity: 'high' | 'medium' | 'low';
	conflicting_event_id: string;
	conflicting_title: string;
	conflicting_start: string;
	conflicting_end: string;
	overlap_minutes: number;
	gap_minutes: number;
	message: string;
}

export interface ScapinEvent {
	id: string;
	source: EventSource;
	title: string;
	summary: string;
	sender?: string;
	occurred_at: string;
	status: EventStatus;
	urgency: UrgencyLevel;
	confidence: ConfidenceLevel;
	suggested_actions: SuggestedAction[];
	metadata?: Record<string, unknown>;
	// Calendar conflict fields
	has_conflicts?: boolean;
	conflicts?: CalendarConflict[];
}

export interface SuggestedAction {
	id: string;
	type: string;
	label: string;
	description?: string;
	confidence: number;
}

// Briefing types
export interface BriefingItem {
	event: ScapinEvent;
	reason: string;
	priority: number;
}

export interface MorningBriefing {
	date: string;
	generated_at: string;
	urgent_items: BriefingItem[];
	calendar_today: BriefingItem[];
	emails_pending: number;
	teams_unread: number;
	summary: string;
}

// Notes PKM types
export interface Note {
	path: string;
	title: string;
	content: string;
	backlinks: string[];
	forward_links: string[];
	updated_at: string;
}

// Chat/Discussion types
export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
}

export interface Discussion {
	id: string;
	title: string;
	messages: ChatMessage[];
	created_at: string;
	updated_at: string;
}

// API Response wrapper
export interface ApiResponse<T> {
	success: boolean;
	data?: T;
	error?: string;
	meta?: {
		timestamp: string;
		request_id?: string;
	};
}
