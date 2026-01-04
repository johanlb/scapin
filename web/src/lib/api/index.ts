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
	PaginatedResponse
} from './client';
