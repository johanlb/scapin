// API Client exports
export {
	// Auth
	login,
	checkAuth,
	logout,
	setAuthToken,
	getAuthToken,
	clearAuthToken,
	// System
	getHealth,
	getStats,
	getConfig,
	// Briefing
	getMorningBriefing,
	getPreMeetingBriefing,
	// Queue
	listQueueItems,
	getQueueItem,
	getQueueStats,
	approveQueueItem,
	modifyQueueItem,
	rejectQueueItem,
	deleteQueueItem,
	snoozeQueueItem,
	unsnoozeQueueItem,
	undoQueueItem,
	canUndoQueueItem,
	// Notes Review
	getNotesDue,
	getReviewStats,
	getReviewWorkload,
	getNoteReviewMetadata,
	recordReview,
	postponeReview,
	triggerReview,
	// Discussions
	listDiscussions,
	getDiscussion,
	createDiscussion,
	addMessage,
	updateDiscussion,
	deleteDiscussion,
	quickChat,
	// Notes
	syncAppleNotes,
	// Teams
	listTeamsChats,
	listTeamsMessages,
	replyToTeamsMessage,
	flagTeamsMessage,
	pollTeams,
	getTeamsStats,
	markChatAsRead,
	markChatAsUnread,
	listRecentTeamsMessages,
	// Error
	ApiError
} from './client';

export type {
	ApiResponse,
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
	// Queue types
	ActionOption,
	QueueItem,
	QueueItemMetadata,
	QueueItemAnalysis,
	QueueStats,
	PaginatedResponse,
	// Snooze types
	SnoozeOption,
	SnoozeResponse,
	// Undo types
	CanUndoResponse,
	// Notes Review types
	NoteReviewMetadata,
	NotesDueResponse,
	ReviewStatsResponse,
	ReviewWorkloadResponse,
	RecordReviewResponse,
	PostponeReviewResponse,
	TriggerReviewResponse,
	// Discussion types
	DiscussionType,
	MessageRole,
	SuggestionType,
	DiscussionMessage,
	DiscussionSuggestion,
	Discussion,
	DiscussionDetail,
	DiscussionListResponse,
	DiscussionCreateRequest,
	MessageCreateRequest,
	QuickChatRequest,
	QuickChatResponse,
	// Teams types
	TeamsChat,
	TeamsSender,
	TeamsMessage,
	TeamsStats,
	TeamsPollResult
} from './client';
