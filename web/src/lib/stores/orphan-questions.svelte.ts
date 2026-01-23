/**
 * Orphan Questions Store
 * Manages strategic questions that don't have a target note
 *
 * v3.2: Initial implementation
 */
import {
	ApiError,
	listOrphanQuestions as apiListOrphanQuestions,
	resolveOrphanQuestion as apiResolveOrphanQuestion,
	deleteOrphanQuestion as apiDeleteOrphanQuestion
} from '$lib/api/client';
import type { OrphanQuestion } from '$lib/api/client';

// ============================================================================
// STORE STATE
// ============================================================================

interface OrphanQuestionsState {
	questions: OrphanQuestion[];
	loading: boolean;
	error: string | null;
	includeResolved: boolean;
	pendingCount: number;
	totalCount: number;
}

// Create reactive state
let state = $state<OrphanQuestionsState>({
	questions: [],
	loading: false,
	error: null,
	includeResolved: false,
	pendingCount: 0,
	totalCount: 0
});

// ============================================================================
// DERIVED VALUES
// ============================================================================

const pendingQuestions = $derived(state.questions.filter((q) => !q.resolved));

const resolvedQuestions = $derived(state.questions.filter((q) => q.resolved));

const byCategory = $derived.by(() => {
	const groups: Record<string, OrphanQuestion[]> = {};

	for (const question of state.questions) {
		const category = question.category || 'autre';
		if (!groups[category]) {
			groups[category] = [];
		}
		groups[category].push(question);
	}

	return groups;
});

const isEmpty = $derived(state.questions.length === 0 && !state.loading);

// ============================================================================
// ACTIONS
// ============================================================================

async function fetchQuestions(includeResolved = false): Promise<void> {
	state.loading = true;
	state.error = null;
	state.includeResolved = includeResolved;

	try {
		const response = await apiListOrphanQuestions(includeResolved);
		state.questions = response.questions;
		state.pendingCount = response.pending_count;
		state.totalCount = response.total_count;
	} catch (err) {
		handleError(err, 'Impossible de charger les questions orphelines');
	} finally {
		state.loading = false;
	}
}

async function resolveQuestion(
	questionId: string,
	resolution?: string
): Promise<boolean> {
	try {
		await apiResolveOrphanQuestion(questionId, resolution);

		// Update local state
		state.questions = state.questions.map((q) =>
			q.question_id === questionId
				? { ...q, resolved: true, resolution, resolved_at: new Date().toISOString() }
				: q
		);
		state.pendingCount = Math.max(0, state.pendingCount - 1);

		return true;
	} catch (err) {
		handleError(err, 'Impossible de résoudre la question');
		return false;
	}
}

async function deleteQuestion(questionId: string): Promise<boolean> {
	try {
		await apiDeleteOrphanQuestion(questionId);

		// Update local state
		const wasResolved = state.questions.find((q) => q.question_id === questionId)?.resolved;
		state.questions = state.questions.filter((q) => q.question_id !== questionId);
		state.totalCount = Math.max(0, state.totalCount - 1);
		if (!wasResolved) {
			state.pendingCount = Math.max(0, state.pendingCount - 1);
		}

		return true;
	} catch (err) {
		handleError(err, 'Impossible de supprimer la question');
		return false;
	}
}

function clearError(): void {
	state.error = null;
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

export const orphanQuestionsStore = {
	// State getters
	get questions() {
		return state.questions;
	},
	get loading() {
		return state.loading;
	},
	get error() {
		return state.error;
	},
	get includeResolved() {
		return state.includeResolved;
	},
	get pendingCount() {
		return state.pendingCount;
	},
	get totalCount() {
		return state.totalCount;
	},

	// Derived getters
	get pendingQuestions() {
		return pendingQuestions;
	},
	get resolvedQuestions() {
		return resolvedQuestions;
	},
	get byCategory() {
		return byCategory;
	},
	get isEmpty() {
		return isEmpty;
	},

	// Actions
	fetchQuestions,
	resolveQuestion,
	deleteQuestion,
	clearError
};

export type { OrphanQuestion };
