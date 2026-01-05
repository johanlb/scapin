/**
 * Notes Review Store
 * Manages SM-2 spaced repetition review state
 */
import {
	getNotesDue,
	getReviewStats,
	getReviewWorkload,
	recordReview,
	postponeReview,
	ApiError
} from '$lib/api';
import type {
	NoteReviewMetadata,
	NotesDueResponse,
	ReviewStatsResponse,
	ReviewWorkloadResponse,
	RecordReviewResponse
} from '$lib/api';

interface NotesReviewState {
	dueNotes: NoteReviewMetadata[];
	stats: ReviewStatsResponse | null;
	workload: ReviewWorkloadResponse | null;
	currentIndex: number;
	loading: boolean;
	error: string | null;
	lastFetch: Date | null;
	reviewedThisSession: number;
}

// Create reactive state
let state = $state<NotesReviewState>({
	dueNotes: [],
	stats: null,
	workload: null,
	currentIndex: 0,
	loading: false,
	error: null,
	lastFetch: null,
	reviewedThisSession: 0
});

// Derived values
const currentNote = $derived(state.dueNotes[state.currentIndex] ?? null);

const hasNext = $derived(state.currentIndex < state.dueNotes.length - 1);

const hasPrevious = $derived(state.currentIndex > 0);

const totalDue = $derived(state.dueNotes.length);

const progress = $derived({
	current: state.currentIndex + 1,
	total: state.dueNotes.length,
	percent: state.dueNotes.length > 0 ? Math.round(((state.currentIndex + 1) / state.dueNotes.length) * 100) : 0,
	reviewed: state.reviewedThisSession
});

const isEmpty = $derived(state.dueNotes.length === 0 && !state.loading);

// Actions
async function fetchDueNotes(limit = 50, noteType?: string): Promise<void> {
	state.loading = true;
	state.error = null;

	try {
		const response = await getNotesDue(limit, noteType);
		state.dueNotes = response.notes;
		state.currentIndex = 0;
		state.lastFetch = new Date();
	} catch (err) {
		handleError(err, 'Impossible de charger les notes');
	} finally {
		state.loading = false;
	}
}

async function fetchStats(): Promise<void> {
	try {
		state.stats = await getReviewStats();
	} catch (err) {
		console.error('Failed to fetch review stats:', err);
	}
}

async function fetchWorkload(days = 7): Promise<void> {
	try {
		state.workload = await getReviewWorkload(days);
	} catch (err) {
		console.error('Failed to fetch workload:', err);
	}
}

async function fetchAll(): Promise<void> {
	state.loading = true;
	state.error = null;

	try {
		const [dueResponse, stats, workload] = await Promise.all([
			getNotesDue(50),
			getReviewStats(),
			getReviewWorkload(7)
		]);

		state.dueNotes = dueResponse.notes;
		state.stats = stats;
		state.workload = workload;
		state.currentIndex = 0;
		state.lastFetch = new Date();
	} catch (err) {
		handleError(err, 'Impossible de charger les données');
	} finally {
		state.loading = false;
	}
}

async function submitReview(quality: number): Promise<RecordReviewResponse | null> {
	const note = currentNote;
	if (!note) return null;

	state.loading = true;
	state.error = null;

	try {
		const result = await recordReview(note.note_id, quality);

		// Remove note from due list
		state.dueNotes = state.dueNotes.filter((n) => n.note_id !== note.note_id);
		state.reviewedThisSession++;

		// Adjust index if needed
		if (state.currentIndex >= state.dueNotes.length && state.dueNotes.length > 0) {
			state.currentIndex = state.dueNotes.length - 1;
		}

		// Refresh stats
		await fetchStats();

		return result;
	} catch (err) {
		handleError(err, 'Impossible d\'enregistrer la révision');
		return null;
	} finally {
		state.loading = false;
	}
}

async function postponeCurrentNote(hours = 24): Promise<boolean> {
	const note = currentNote;
	if (!note) return false;

	state.loading = true;
	state.error = null;

	try {
		await postponeReview(note.note_id, hours);

		// Remove note from due list
		state.dueNotes = state.dueNotes.filter((n) => n.note_id !== note.note_id);

		// Adjust index if needed
		if (state.currentIndex >= state.dueNotes.length && state.dueNotes.length > 0) {
			state.currentIndex = state.dueNotes.length - 1;
		}

		return true;
	} catch (err) {
		handleError(err, 'Impossible de reporter la note');
		return false;
	} finally {
		state.loading = false;
	}
}

function nextNote(): void {
	if (hasNext) {
		state.currentIndex++;
	}
}

function previousNote(): void {
	if (hasPrevious) {
		state.currentIndex--;
	}
}

function skipNote(): void {
	// Move to next without reviewing
	if (hasNext) {
		state.currentIndex++;
	}
}

function goToNote(index: number): void {
	if (index >= 0 && index < state.dueNotes.length) {
		state.currentIndex = index;
	}
}

function resetSession(): void {
	state.currentIndex = 0;
	state.reviewedThisSession = 0;
}

function clearError(): void {
	state.error = null;
}

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

// Export reactive getters and actions
export const notesReviewStore = {
	// State getters
	get state() {
		return state;
	},
	get dueNotes() {
		return state.dueNotes;
	},
	get stats() {
		return state.stats;
	},
	get workload() {
		return state.workload;
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
	get currentNote() {
		return currentNote;
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
	get totalDue() {
		return totalDue;
	},
	get progress() {
		return progress;
	},
	get isEmpty() {
		return isEmpty;
	},
	get reviewedThisSession() {
		return state.reviewedThisSession;
	},

	// Actions
	fetchDueNotes,
	fetchStats,
	fetchWorkload,
	fetchAll,
	submitReview,
	postponeCurrentNote,
	nextNote,
	previousNote,
	skipNote,
	goToNote,
	resetSession,
	clearError
};

export type { NoteReviewMetadata, ReviewStatsResponse, ReviewWorkloadResponse };
