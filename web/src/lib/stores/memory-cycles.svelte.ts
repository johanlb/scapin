/**
 * Memory Cycles Store
 * Manages Filage (daily briefing) and Lecture (review sessions) state
 */
import { ApiError } from '$lib/api';
import type {
	Filage,
	FilageLecture,
	LectureSession,
	LectureResult,
	PendingQuestion,
	QuestionsListResponse
} from '$lib/api/types/memory-cycles';

// ============================================================================
// API FUNCTIONS (will be imported from client.ts once added)
// ============================================================================

const API_BASE = '/api';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
	const url = `${API_BASE}${endpoint}`;
	const headers: HeadersInit = {
		'Content-Type': 'application/json',
		...options?.headers
	};

	// Get auth token from localStorage
	const token = typeof localStorage !== 'undefined' ? localStorage.getItem('scapin_token') : null;
	if (token) {
		(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(url, { ...options, headers });

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({}));
		throw new ApiError(response.status, errorData.detail || `HTTP ${response.status}`);
	}

	const data = await response.json();
	if (!data.success) {
		throw new ApiError(500, data.error || 'Unknown error');
	}

	return data.data as T;
}

// API functions for Memory Cycles
async function apiGetFilage(maxLectures = 20): Promise<Filage> {
	return fetchApi<Filage>(`/briefing/filage?max_lectures=${maxLectures}`);
}

async function apiStartLecture(noteId: string): Promise<LectureSession> {
	return fetchApi<LectureSession>(`/briefing/lecture/${encodeURIComponent(noteId)}/start`, {
		method: 'POST'
	});
}

async function apiCompleteLecture(
	noteId: string,
	quality: number,
	answers?: Record<string, string>
): Promise<LectureResult> {
	return fetchApi<LectureResult>(`/briefing/lecture/${encodeURIComponent(noteId)}/complete`, {
		method: 'POST',
		body: JSON.stringify({ quality, answers })
	});
}

async function apiGetPendingQuestions(limit = 50): Promise<QuestionsListResponse> {
	return fetchApi<QuestionsListResponse>(`/notes/questions/pending?limit=${limit}`);
}

async function apiAnswerQuestion(
	questionId: string,
	answer: string
): Promise<{ success: boolean }> {
	return fetchApi<{ success: boolean }>(`/notes/questions/${encodeURIComponent(questionId)}/answer`, {
		method: 'POST',
		body: JSON.stringify({ answer })
	});
}

// ============================================================================
// STORE STATE
// ============================================================================

interface MemoryCyclesState {
	filage: Filage | null;
	currentSession: LectureSession | null;
	currentIndex: number;
	completedToday: number;
	loading: boolean;
	error: string | null;
	lastFetch: Date | null;
	// Questions state
	pendingQuestions: PendingQuestion[];
	questionsLoading: boolean;
}

// Create reactive state
let state = $state<MemoryCyclesState>({
	filage: null,
	currentSession: null,
	currentIndex: 0,
	completedToday: 0,
	loading: false,
	error: null,
	lastFetch: null,
	pendingQuestions: [],
	questionsLoading: false
});

// ============================================================================
// DERIVED VALUES
// ============================================================================

const currentLecture = $derived(
	state.filage?.lectures[state.currentIndex] ?? null
);

const hasNext = $derived(
	state.filage !== null && state.currentIndex < state.filage.lectures.length - 1
);

const hasPrevious = $derived(state.currentIndex > 0);

const totalLectures = $derived(state.filage?.total_lectures ?? 0);

const progress = $derived({
	current: state.currentIndex + 1,
	total: state.filage?.lectures.length ?? 0,
	percent: state.filage?.lectures.length
		? Math.round(((state.currentIndex + 1) / state.filage.lectures.length) * 100)
		: 0,
	completed: state.completedToday
});

const isEmpty = $derived(
	state.filage !== null && state.filage.lectures.length === 0 && !state.loading
);

const pendingQuestionsCount = $derived(
	state.filage?.notes_with_questions ?? state.pendingQuestions.length
);

// Group lectures by reason category
const lecturesByCategory = $derived.by(() => {
	if (!state.filage) return {};

	const groups: Record<string, FilageLecture[]> = {
		questions_pending: [],
		event_related: [],
		sm2_due: [],
		recently_improved: []
	};

	for (const lecture of state.filage.lectures) {
		if (lecture.questions_pending) {
			groups.questions_pending.push(lecture);
		} else if (lecture.related_event_id) {
			groups.event_related.push(lecture);
		} else if (lecture.reason.includes('SM-2') || lecture.reason.includes('révision')) {
			groups.sm2_due.push(lecture);
		} else if (lecture.reason.includes('Améliorée') || lecture.reason.includes('✨')) {
			groups.recently_improved.push(lecture);
		} else {
			// Default to SM-2 due
			groups.sm2_due.push(lecture);
		}
	}

	return groups;
});

// ============================================================================
// ACTIONS
// ============================================================================

async function fetchFilage(maxLectures = 20): Promise<void> {
	state.loading = true;
	state.error = null;

	try {
		state.filage = await apiGetFilage(maxLectures);
		state.currentIndex = 0;
		state.lastFetch = new Date();
	} catch (err) {
		handleError(err, 'Impossible de charger le filage');
	} finally {
		state.loading = false;
	}
}

async function startSession(noteId: string): Promise<LectureSession | null> {
	state.loading = true;
	state.error = null;

	try {
		state.currentSession = await apiStartLecture(noteId);
		return state.currentSession;
	} catch (err) {
		handleError(err, 'Impossible de démarrer la session');
		return null;
	} finally {
		state.loading = false;
	}
}

async function completeSession(
	quality: number,
	answers?: Record<string, string>
): Promise<LectureResult | null> {
	if (!state.currentSession) return null;

	state.loading = true;
	state.error = null;

	try {
		const result = await apiCompleteLecture(
			state.currentSession.note_id,
			quality,
			answers
		);

		if (result.success) {
			// Remove completed lecture from filage
			if (state.filage) {
				state.filage = {
					...state.filage,
					lectures: state.filage.lectures.filter(
						(l) => l.note_id !== state.currentSession?.note_id
					),
					total_lectures: state.filage.total_lectures - 1
				};
			}

			state.completedToday++;
			state.currentSession = null;

			// Adjust index if needed
			if (state.filage && state.currentIndex >= state.filage.lectures.length) {
				state.currentIndex = Math.max(0, state.filage.lectures.length - 1);
			}
		}

		return result;
	} catch (err) {
		handleError(err, 'Impossible de terminer la session');
		return null;
	} finally {
		state.loading = false;
	}
}

function nextLecture(): void {
	if (hasNext) {
		state.currentIndex++;
		state.currentSession = null;
	}
}

function previousLecture(): void {
	if (hasPrevious) {
		state.currentIndex--;
		state.currentSession = null;
	}
}

function skipLecture(): void {
	// Move to next without starting session
	if (hasNext) {
		state.currentIndex++;
	}
	state.currentSession = null;
}

function goToLecture(index: number): void {
	if (state.filage && index >= 0 && index < state.filage.lectures.length) {
		state.currentIndex = index;
		state.currentSession = null;
	}
}

function resetSession(): void {
	state.currentIndex = 0;
	state.currentSession = null;
	state.completedToday = 0;
}

function clearError(): void {
	state.error = null;
}

// Questions management
async function fetchPendingQuestions(limit = 50): Promise<void> {
	state.questionsLoading = true;

	try {
		const response = await apiGetPendingQuestions(limit);
		state.pendingQuestions = response.questions;
	} catch (err) {
		console.error('Failed to fetch pending questions:', err);
	} finally {
		state.questionsLoading = false;
	}
}

async function answerQuestion(
	questionId: string,
	answer: string
): Promise<boolean> {
	try {
		await apiAnswerQuestion(questionId, answer);
		// Remove answered question from list
		state.pendingQuestions = state.pendingQuestions.filter(
			(q) => q.question_id !== questionId
		);
		return true;
	} catch (err) {
		console.error('Failed to answer question:', err);
		return false;
	}
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

function handleError(err: unknown, defaultMessage: string): void {
	if (err instanceof ApiError) {
		if (err.status === 0) {
			state.error = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
		} else {
			state.error = `Erreur ${err.status}: ${err.message}`;
		}
	} else {
		state.error = defaultMessage;
	}
	console.error(defaultMessage, err);
}

// ============================================================================
// EXPORT STORE
// ============================================================================

export const memoryCyclesStore = {
	// State getters
	get state() {
		return state;
	},
	get filage() {
		return state.filage;
	},
	get currentSession() {
		return state.currentSession;
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
	get pendingQuestions() {
		return state.pendingQuestions;
	},
	get questionsLoading() {
		return state.questionsLoading;
	},

	// Derived getters
	get currentLecture() {
		return currentLecture;
	},
	get currentIndex() {
		return state.currentIndex;
	},
	get hasNext() {
		return hasNext;
	},
	get hasPrevious() {
		return hasPrevious;
	},
	get totalLectures() {
		return totalLectures;
	},
	get progress() {
		return progress;
	},
	get isEmpty() {
		return isEmpty;
	},
	get pendingQuestionsCount() {
		return pendingQuestionsCount;
	},
	get completedToday() {
		return state.completedToday;
	},
	get lecturesByCategory() {
		return lecturesByCategory;
	},

	// Actions
	fetchFilage,
	startSession,
	completeSession,
	nextLecture,
	previousLecture,
	skipLecture,
	goToLecture,
	resetSession,
	clearError,
	fetchPendingQuestions,
	answerQuestion
};

export type {
	Filage,
	FilageLecture,
	LectureSession,
	LectureResult,
	PendingQuestion
};
