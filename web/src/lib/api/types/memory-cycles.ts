/**
 * Memory Cycles Types
 * Types for Filage (daily briefing) and Lecture (review sessions)
 */

// ============================================================================
// FILAGE TYPES (Briefing matinal)
// ============================================================================

export interface FilageLecture {
	note_id: string;
	note_title: string;
	note_type: string;
	priority: number;
	reason: string; // "Questions en attente", "Lié à: {event}", "SM-2 due", "Améliorée"
	quality_score: number | null;
	questions_pending: boolean;
	questions_count: number;
	related_event_id?: string;
}

export interface Filage {
	date: string;
	generated_at: string;
	lectures: FilageLecture[];
	total_lectures: number;
	events_today: number;
	notes_with_questions: number;
}

// ============================================================================
// LECTURE SESSION TYPES (Review sessions)
// ============================================================================

export interface LectureSession {
	session_id: string;
	note_id: string;
	note_title: string;
	note_content: string;
	started_at: string;
	quality_score: number | null;
	questions: string[];
}

export interface LectureResult {
	note_id: string;
	quality_rating: number;
	next_lecture: string;
	interval_hours: number;
	answers_recorded: number;
	questions_remaining: number;
	success: boolean;
}

// ============================================================================
// QUESTIONS TYPES
// ============================================================================

export interface PendingQuestion {
	question_id: string;
	note_id: string;
	note_title: string;
	question_text: string;
	created_at: string;
	answered: boolean;
	answer?: string;
}

export interface QuestionsListResponse {
	questions: PendingQuestion[];
	total: number;
	by_note: Record<string, number>;
}

// ============================================================================
// RETOUCHE (AI Improvements) TYPES
// ============================================================================

export interface RetoucheEntry {
	retouche_id: string;
	note_id: string;
	timestamp: string;
	model_used: 'haiku' | 'sonnet' | 'opus';
	quality_before: number | null;
	quality_after: number | null;
	changes_summary: string;
	confidence: number;
}

export interface RetoucheTimeline {
	note_id: string;
	retouches: RetoucheEntry[];
	total_improvements: number;
	quality_trend: number[]; // Array of quality scores over time
}

// ============================================================================
// GAMIFICATION TYPES
// ============================================================================

export interface StreakInfo {
	current_streak: number;
	longest_streak: number;
	last_review_date: string | null;
	streak_maintained: boolean;
}

export interface ReviewBadge {
	badge_id: string;
	name: string;
	description: string;
	icon: string;
	earned_at: string | null;
	progress: number; // 0-100
}

export interface GamificationStats {
	streak: StreakInfo;
	badges: ReviewBadge[];
	total_reviews: number;
	reviews_this_week: number;
	xp_total: number;
	level: number;
}

// ============================================================================
// LECTURE STATS TYPES
// ============================================================================

export interface LectureStats {
	note_id: string;
	total_lectures: number;
	average_quality: number;
	last_lecture: string | null;
	next_lecture: string | null;
	easiness_factor: number;
	interval_hours: number;
}

// ============================================================================
// REASON CATEGORIES
// ============================================================================

export type FilageReasonCategory =
	| 'questions_pending'
	| 'event_related'
	| 'sm2_due'
	| 'recently_improved'
	| 'low_quality'
	| 'manual';

export const REASON_LABELS: Record<FilageReasonCategory, string> = {
	questions_pending: 'Questions en attente',
	event_related: 'Lié aux événements',
	sm2_due: 'Révision SM-2 due',
	recently_improved: 'Récemment améliorée',
	low_quality: 'Qualité à améliorer',
	manual: 'Ajouté manuellement'
};

export const REASON_ICONS: Record<FilageReasonCategory, string> = {
	questions_pending: '❓',
	event_related: '📅',
	sm2_due: '📚',
	recently_improved: '✨',
	low_quality: '⚠️',
	manual: '📌'
};
