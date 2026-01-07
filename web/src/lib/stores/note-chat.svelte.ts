/**
 * Note Chat Store
 * Manages chat context when discussing a specific note
 */
import { createDiscussion, addMessage, quickChat, ApiError } from '$lib/api';
import type {
	DiscussionDetail,
	DiscussionMessage,
	DiscussionSuggestion,
	QuickChatResponse
} from '$lib/api';

// Note types matching backend NoteType enum
export type NoteType =
	| 'personne'
	| 'projet'
	| 'concept'
	| 'souvenir'
	| 'reference'
	| 'meeting'
	| 'default';

export interface NoteContext {
	id: string;
	title: string;
	type: NoteType;
	content: string;
	tags: string[];
	linkedNotes?: string[]; // Titles of linked notes
}

interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
}

interface NoteChatState {
	// Current note context
	noteContext: NoteContext | null;
	isOpen: boolean;

	// Conversation
	messages: ChatMessage[];
	suggestions: DiscussionSuggestion[];

	// Loading states
	sending: boolean;
	saving: boolean;
	error: string | null;

	// Persistence
	discussionId: string | null; // If saved as discussion
}

// Contextual suggestions by note type
const suggestionsByNoteType: Record<NoteType, Array<{ label: string; query: string }>> = {
	personne: [
		{ label: 'Prépare ma prochaine interaction', query: 'Prépare ma prochaine interaction avec cette personne' },
		{ label: 'Résume nos derniers échanges', query: 'Résume mes derniers échanges avec cette personne' },
		{ label: 'Quels sujets aborder ?', query: 'Quels sujets dois-je aborder avec cette personne ?' }
	],
	projet: [
		{ label: "État d'avancement", query: "Quel est l'état d'avancement de ce projet ?" },
		{ label: 'Prochains jalons', query: 'Quels sont les prochains jalons de ce projet ?' },
		{ label: 'Points bloquants', query: 'Y a-t-il des points bloquants sur ce projet ?' }
	],
	concept: [
		{ label: 'Explique simplement', query: 'Explique-moi ce concept simplement' },
		{ label: 'Exemples concrets', query: 'Donne-moi des exemples concrets de ce concept' },
		{ label: 'Comment appliquer ?', query: 'Comment puis-je appliquer ce concept dans mon contexte ?' }
	],
	souvenir: [
		{ label: "Leçons apprises", query: "Qu'ai-je appris de cette expérience ?" },
		{ label: 'Actions de suivi', query: 'Y a-t-il des actions de suivi pour cette expérience ?' }
	],
	reference: [
		{ label: 'Points clés', query: 'Résume les points clés de cette référence' },
		{ label: 'Comment utiliser ?', query: 'Comment utiliser cette ressource efficacement ?' }
	],
	meeting: [
		{ label: 'Points à préparer', query: 'Quels points dois-je préparer pour cette réunion ?' },
		{ label: 'Contexte participants', query: 'Donne-moi le contexte sur les participants' },
		{ label: 'Actions en suspens', query: 'Y a-t-il des actions en suspens liées à cette réunion ?' }
	],
	default: [
		{ label: 'Résume cette note', query: 'Résume les points essentiels de cette note' },
		{ label: 'Que retenir ?', query: 'Que dois-je retenir de cette note ?' },
		{ label: 'Questions liées', query: 'Quelles questions pourrais-je explorer en lien avec cette note ?' }
	]
};

// LocalStorage key prefix for conversation persistence
const STORAGE_KEY_PREFIX = 'scapin_note_chat_';

// Create reactive state
let state = $state<NoteChatState>({
	noteContext: null,
	isOpen: false,
	messages: [],
	suggestions: [],
	sending: false,
	saving: false,
	error: null,
	discussionId: null
});

// Computed values
const hasMessages = $derived(state.messages.length > 0);

const contextualSuggestions = $derived(() => {
	if (!state.noteContext) return suggestionsByNoteType.default;
	return suggestionsByNoteType[state.noteContext.type] || suggestionsByNoteType.default;
});

const canSaveAsDiscussion = $derived(state.messages.length > 0 && !state.discussionId);

// Build context string for API
function buildContextString(note: NoteContext): string {
	const parts: string[] = [];

	parts.push(`# ${note.title}`);
	parts.push(`Type: ${note.type}`);

	if (note.tags.length > 0) {
		parts.push(`Tags: ${note.tags.join(', ')}`);
	}

	if (note.linkedNotes && note.linkedNotes.length > 0) {
		parts.push(`Notes liées: ${note.linkedNotes.join(', ')}`);
	}

	// Include content (truncated if too long)
	const maxContentLength = 2000;
	if (note.content.length > maxContentLength) {
		parts.push(`\nContenu (résumé):\n${note.content.slice(0, maxContentLength)}...`);
	} else {
		parts.push(`\nContenu:\n${note.content}`);
	}

	return parts.join('\n');
}

// Load conversation from localStorage
function loadConversation(noteId: string): void {
	try {
		const stored = localStorage.getItem(STORAGE_KEY_PREFIX + noteId);
		if (stored) {
			const data = JSON.parse(stored);
			state.messages = data.messages || [];
			state.discussionId = data.discussionId || null;
		} else {
			state.messages = [];
			state.discussionId = null;
		}
	} catch {
		state.messages = [];
		state.discussionId = null;
	}
}

// Save conversation to localStorage
function saveConversation(): void {
	if (!state.noteContext) return;

	try {
		const data = {
			messages: state.messages,
			discussionId: state.discussionId,
			lastUpdated: new Date().toISOString()
		};
		localStorage.setItem(STORAGE_KEY_PREFIX + state.noteContext.id, JSON.stringify(data));
	} catch (err) {
		console.error('Failed to save conversation:', err);
	}
}

// Actions
function openForNote(note: NoteContext): void {
	state.noteContext = note;
	state.isOpen = true;
	state.error = null;

	// Load existing conversation for this note
	loadConversation(note.id);

	// Set initial suggestions based on note type
	state.suggestions = [];
}

function close(): void {
	state.isOpen = false;
	// Keep the context and messages in case user reopens
}

function clearContext(): void {
	state.noteContext = null;
	state.isOpen = false;
	state.messages = [];
	state.suggestions = [];
	state.discussionId = null;
	state.error = null;
}

async function sendMessage(content: string): Promise<void> {
	if (!state.noteContext || !content.trim()) return;

	state.sending = true;
	state.error = null;

	// Add user message immediately
	const userMessage: ChatMessage = {
		id: `msg_${Date.now()}`,
		role: 'user',
		content: content.trim(),
		timestamp: new Date().toISOString()
	};
	state.messages = [...state.messages, userMessage];
	saveConversation();

	try {
		// If we have a discussion ID, use addMessage, otherwise use quickChat
		if (state.discussionId) {
			const updated = await addMessage(state.discussionId, {
				role: 'user',
				content: content.trim()
			});

			// Find the assistant's response (last message)
			const lastMessage = updated.messages[updated.messages.length - 1];
			if (lastMessage && lastMessage.role === 'assistant') {
				const assistantMessage: ChatMessage = {
					id: lastMessage.id,
					role: 'assistant',
					content: lastMessage.content,
					timestamp: lastMessage.created_at
				};
				state.messages = [...state.messages, assistantMessage];
			}

			state.suggestions = updated.suggestions || [];
		} else {
			// Use quick chat with note context
			const contextString = buildContextString(state.noteContext);
			const response: QuickChatResponse | null = await quickChat({
				message: content.trim(),
				context_type: 'note',
				context_id: state.noteContext.id,
				include_suggestions: true
			});

			if (response) {
				const assistantMessage: ChatMessage = {
					id: `msg_${Date.now()}_assistant`,
					role: 'assistant',
					content: response.response,
					timestamp: new Date().toISOString()
				};
				state.messages = [...state.messages, assistantMessage];

				// Update suggestions
				if (response.suggestions) {
					state.suggestions = response.suggestions;
				}
			}
		}

		saveConversation();
	} catch (err) {
		handleError(err, "Impossible d'envoyer le message");
		// Remove the user message on error
		state.messages = state.messages.filter((m) => m.id !== userMessage.id);
		saveConversation();
	} finally {
		state.sending = false;
	}
}

async function saveAsDiscussion(): Promise<DiscussionDetail | null> {
	if (!state.noteContext || state.messages.length === 0) return null;

	state.saving = true;
	state.error = null;

	try {
		// Create discussion attached to this note
		const discussion = await createDiscussion({
			title: `Discussion: ${state.noteContext.title}`,
			discussion_type: 'note',
			attached_to_id: state.noteContext.id,
			attached_to_type: 'note',
			initial_message: state.messages[0].content,
			context: {
				note_title: state.noteContext.title,
				note_type: state.noteContext.type
			}
		});

		// Add remaining messages
		for (let i = 1; i < state.messages.length; i++) {
			const msg = state.messages[i];
			await addMessage(discussion.id, {
				role: msg.role,
				content: msg.content
			});
		}

		state.discussionId = discussion.id;
		saveConversation();

		return discussion;
	} catch (err) {
		handleError(err, 'Impossible de sauvegarder la discussion');
		return null;
	} finally {
		state.saving = false;
	}
}

function clearConversation(): void {
	if (!state.noteContext) return;

	state.messages = [];
	state.suggestions = [];
	state.discussionId = null;

	// Clear from localStorage
	try {
		localStorage.removeItem(STORAGE_KEY_PREFIX + state.noteContext.id);
	} catch {
		// Ignore
	}
}

function handleError(err: unknown, defaultMessage: string): void {
	if (err instanceof ApiError) {
		if (err.status === 0) {
			state.error = 'Impossible de contacter le serveur.';
		} else {
			state.error = `Erreur ${err.status}: ${err.message}`;
		}
	} else {
		state.error = defaultMessage;
	}
	console.error(defaultMessage, err);
}

function clearError(): void {
	state.error = null;
}

// Detect note type from tags or title
export function detectNoteType(note: { title: string; tags: string[] }): NoteType {
	const lowerTags = note.tags.map((t) => t.toLowerCase());
	const lowerTitle = note.title.toLowerCase();

	if (lowerTags.includes('personne') || lowerTags.includes('contact')) {
		return 'personne';
	}
	if (lowerTags.includes('projet') || lowerTags.includes('project')) {
		return 'projet';
	}
	if (lowerTags.includes('concept') || lowerTags.includes('idée')) {
		return 'concept';
	}
	if (lowerTags.includes('souvenir') || lowerTags.includes('expérience')) {
		return 'souvenir';
	}
	if (lowerTags.includes('référence') || lowerTags.includes('reference') || lowerTags.includes('doc')) {
		return 'reference';
	}
	if (lowerTags.includes('réunion') || lowerTags.includes('meeting') || lowerTitle.includes('réunion')) {
		return 'meeting';
	}

	return 'default';
}

// Export reactive getters and actions
export const noteChatStore = {
	// State getters
	get noteContext() {
		return state.noteContext;
	},
	get isOpen() {
		return state.isOpen;
	},
	get messages() {
		return state.messages;
	},
	get suggestions() {
		return state.suggestions;
	},
	get sending() {
		return state.sending;
	},
	get saving() {
		return state.saving;
	},
	get error() {
		return state.error;
	},
	get discussionId() {
		return state.discussionId;
	},

	// Computed getters
	get hasMessages() {
		return hasMessages;
	},
	get contextualSuggestions() {
		return contextualSuggestions();
	},
	get canSaveAsDiscussion() {
		return canSaveAsDiscussion;
	},

	// Actions
	openForNote,
	close,
	clearContext,
	sendMessage,
	saveAsDiscussion,
	clearConversation,
	clearError,

	// Utilities
	getSuggestionsByType: (type: NoteType) => suggestionsByNoteType[type] || suggestionsByNoteType.default
};

export type { ChatMessage };
