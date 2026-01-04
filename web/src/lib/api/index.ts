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
	// Briefing
	getMorningBriefing,
	getPreMeetingBriefing,
	// Error
	ApiError
} from './client';

export type {
	ApiResponse,
	HealthStatus,
	Stats,
	BriefingItem,
	MorningBriefing,
	AttendeeContext,
	PreMeetingBriefing,
	TokenResponse,
	AuthCheckResponse
} from './client';
