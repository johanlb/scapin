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
	// Canevas
	getCanevasStatus,
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
	reanalyzeQueueItem,
	reanalyzeAllPending,
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
	// Email
	processInbox,
	// Folders
	listFolders,
	getFolderTree,
	getFolderSuggestions,
	createFolder,
	recordArchive,
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
	// Canevas types
	CanevasStatus,
	CanevasFileStatus,
	// Queue types
	Attachment,
	ActionOption,
	QueueItem,
	QueueItemMetadata,
	QueueItemAnalysis,
	QueueStats,
	PaginatedResponse,
	// Sprint 2: Entity types
	Entity,
	ProposedNote,
	ProposedTask,
	// Snooze types
	SnoozeOption,
	SnoozeResponse,
	// Undo types
	CanUndoResponse,
	// Reanalyze types
	ReanalyzeResponse,
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
	TeamsPollResult,
	// Folder types
	EmailFolder,
	FolderTreeNode,
	FolderSuggestion,
	FolderSuggestions,
	CreateFolderResult
} from './client';
