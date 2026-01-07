/**
 * Discussions Store
 * Manages conversation threads with Scapin
 */
import {
	listDiscussions,
	getDiscussion,
	createDiscussion,
	addMessage,
	updateDiscussion,
	deleteDiscussion,
	quickChat,
	ApiError
} from '$lib/api';
import type {
	Discussion,
	DiscussionDetail,
	DiscussionType,
	DiscussionListResponse,
	DiscussionCreateRequest,
	MessageCreateRequest,
	QuickChatRequest,
	QuickChatResponse
} from '$lib/api';

interface DiscussionsState {
	discussions: Discussion[];
	currentDiscussion: DiscussionDetail | null;
	total: number;
	page: number;
	pageSize: number;
	loading: boolean;
	loadingDetail: boolean;
	creating: boolean;
	sending: boolean;
	error: string | null;
	lastFetch: Date | null;
	filter: {
		type: DiscussionType | null;
		attachedToId: string | null;
	};
}

// Create reactive state
let state = $state<DiscussionsState>({
	discussions: [],
	currentDiscussion: null,
	total: 0,
	page: 1,
	pageSize: 20,
	loading: false,
	loadingDetail: false,
	creating: false,
	sending: false,
	error: null,
	lastFetch: null,
	filter: {
		type: null,
		attachedToId: null
	}
});

// Computed values
const hasMore = $derived(state.discussions.length < state.total);

const isEmpty = $derived(state.discussions.length === 0 && !state.loading);

const freeDiscussions = $derived(
	state.discussions.filter((d) => d.discussion_type === 'free')
);

const attachedDiscussions = $derived(
	state.discussions.filter((d) => d.discussion_type !== 'free')
);

const currentMessages = $derived(state.currentDiscussion?.messages ?? []);

const currentSuggestions = $derived(state.currentDiscussion?.suggestions ?? []);

// Actions
async function fetchDiscussions(resetPage = false): Promise<void> {
	if (resetPage) {
		state.page = 1;
		state.discussions = [];
	}

	state.loading = true;
	state.error = null;

	try {
		const response: DiscussionListResponse = await listDiscussions({
			type: state.filter.type ?? undefined,
			attached_to_id: state.filter.attachedToId ?? undefined,
			page: state.page,
			page_size: state.pageSize
		});

		if (resetPage) {
			state.discussions = response.discussions;
		} else {
			state.discussions = [...state.discussions, ...response.discussions];
		}
		state.total = response.total;
		state.lastFetch = new Date();
	} catch (err) {
		handleError(err, 'Impossible de charger les discussions');
	} finally {
		state.loading = false;
	}
}

async function loadMore(): Promise<void> {
	if (!hasMore || state.loading) return;
	state.page += 1;
	await fetchDiscussions(false);
}

async function fetchDiscussionDetail(discussionId: string): Promise<void> {
	state.loadingDetail = true;
	state.error = null;

	try {
		const discussion = await getDiscussion(discussionId);
		state.currentDiscussion = discussion;
	} catch (err) {
		handleError(err, 'Impossible de charger la discussion');
		state.currentDiscussion = null;
	} finally {
		state.loadingDetail = false;
	}
}

async function create(request: DiscussionCreateRequest): Promise<DiscussionDetail | null> {
	state.creating = true;
	state.error = null;

	try {
		const discussion = await createDiscussion(request);
		// Add to list at beginning
		state.discussions = [
			{
				id: discussion.id,
				title: discussion.title,
				discussion_type: discussion.discussion_type,
				attached_to_id: discussion.attached_to_id,
				attached_to_type: discussion.attached_to_type,
				created_at: discussion.created_at,
				updated_at: discussion.updated_at,
				message_count: discussion.message_count,
				last_message_preview: discussion.last_message_preview,
				metadata: discussion.metadata
			},
			...state.discussions
		];
		state.total += 1;
		state.currentDiscussion = discussion;
		return discussion;
	} catch (err) {
		handleError(err, 'Impossible de créer la discussion');
		return null;
	} finally {
		state.creating = false;
	}
}

async function sendMessage(
	discussionId: string,
	content: string
): Promise<DiscussionDetail | null> {
	state.sending = true;
	state.error = null;

	const request: MessageCreateRequest = {
		role: 'user',
		content
	};

	try {
		const updated = await addMessage(discussionId, request);
		state.currentDiscussion = updated;

		// Update the discussion in the list
		const idx = state.discussions.findIndex((d) => d.id === discussionId);
		if (idx !== -1) {
			state.discussions[idx] = {
				...state.discussions[idx],
				updated_at: updated.updated_at,
				message_count: updated.message_count,
				last_message_preview: updated.last_message_preview
			};
		}

		return updated;
	} catch (err) {
		handleError(err, "Impossible d'envoyer le message");
		return null;
	} finally {
		state.sending = false;
	}
}

async function update(
	discussionId: string,
	updates: { title?: string; metadata?: Record<string, unknown> }
): Promise<Discussion | null> {
	state.error = null;

	try {
		const updated = await updateDiscussion(discussionId, updates);

		// Update in list
		const idx = state.discussions.findIndex((d) => d.id === discussionId);
		if (idx !== -1) {
			state.discussions[idx] = updated;
		}

		// Update current if matching
		if (state.currentDiscussion?.id === discussionId) {
			state.currentDiscussion = {
				...state.currentDiscussion,
				...updated
			};
		}

		return updated;
	} catch (err) {
		handleError(err, 'Impossible de modifier la discussion');
		return null;
	}
}

async function remove(discussionId: string): Promise<boolean> {
	state.error = null;

	try {
		await deleteDiscussion(discussionId);

		// Remove from list
		state.discussions = state.discussions.filter((d) => d.id !== discussionId);
		state.total -= 1;

		// Clear current if matching
		if (state.currentDiscussion?.id === discussionId) {
			state.currentDiscussion = null;
		}

		return true;
	} catch (err) {
		handleError(err, 'Impossible de supprimer la discussion');
		return false;
	}
}

async function sendQuickMessage(
	message: string,
	options?: {
		contextType?: string;
		contextId?: string;
		includeSuggestions?: boolean;
	}
): Promise<QuickChatResponse | null> {
	state.sending = true;
	state.error = null;

	const request: QuickChatRequest = {
		message,
		context_type: options?.contextType,
		context_id: options?.contextId,
		include_suggestions: options?.includeSuggestions ?? true
	};

	try {
		const response = await quickChat(request);
		return response;
	} catch (err) {
		handleError(err, 'Impossible de traiter le message');
		return null;
	} finally {
		state.sending = false;
	}
}

function setFilter(filter: { type?: DiscussionType | null; attachedToId?: string | null }): void {
	if (filter.type !== undefined) {
		state.filter.type = filter.type;
	}
	if (filter.attachedToId !== undefined) {
		state.filter.attachedToId = filter.attachedToId;
	}
}

function selectDiscussion(discussion: Discussion | null): void {
	if (discussion) {
		fetchDiscussionDetail(discussion.id);
	} else {
		state.currentDiscussion = null;
	}
}

function clearCurrent(): void {
	state.currentDiscussion = null;
}

function clearError(): void {
	state.error = null;
}

function handleError(err: unknown, defaultMessage: string): void {
	if (err instanceof ApiError) {
		if (err.status === 0) {
			state.error = 'Impossible de contacter le serveur. Vérifiez votre connexion.';
		} else if (err.status === 404) {
			state.error = 'Discussion introuvable.';
		} else {
			state.error = `Erreur ${err.status}: ${err.message}`;
		}
	} else {
		state.error = defaultMessage;
	}
	console.error(defaultMessage, err);
}

// Export reactive getters and actions
export const discussionsStore = {
	// State getters
	get state() {
		return state;
	},
	get discussions() {
		return state.discussions;
	},
	get currentDiscussion() {
		return state.currentDiscussion;
	},
	get total() {
		return state.total;
	},
	get page() {
		return state.page;
	},
	get loading() {
		return state.loading;
	},
	get loadingDetail() {
		return state.loadingDetail;
	},
	get creating() {
		return state.creating;
	},
	get sending() {
		return state.sending;
	},
	get error() {
		return state.error;
	},
	get lastFetch() {
		return state.lastFetch;
	},
	get filter() {
		return state.filter;
	},

	// Computed getters
	get hasMore() {
		return hasMore;
	},
	get isEmpty() {
		return isEmpty;
	},
	get freeDiscussions() {
		return freeDiscussions;
	},
	get attachedDiscussions() {
		return attachedDiscussions;
	},
	get currentMessages() {
		return currentMessages;
	},
	get currentSuggestions() {
		return currentSuggestions;
	},

	// Actions
	fetchDiscussions,
	loadMore,
	fetchDiscussionDetail,
	create,
	sendMessage,
	update,
	remove,
	sendQuickMessage,
	setFilter,
	selectDiscussion,
	clearCurrent,
	clearError
};

export type { Discussion, DiscussionDetail, DiscussionType };
