/**
 * Gamification Store
 * Tracks streaks, badges, and XP for memory review engagement
 */
import type { StreakInfo, GamificationStats, ReviewBadge } from '$lib/api/types/memory-cycles';

// ============================================================================
// LOCAL STORAGE KEYS
// ============================================================================

const STORAGE_KEY = 'scapin_gamification';

// ============================================================================
// DEFAULT VALUES
// ============================================================================

const DEFAULT_STREAK: StreakInfo = {
	current_streak: 0,
	longest_streak: 0,
	last_review_date: null,
	streak_maintained: false
};

const DEFAULT_BADGES: ReviewBadge[] = [
	{
		badge_id: 'first_review',
		name: 'Premier pas',
		description: 'Complétez votre première révision',
		icon: '🌱',
		earned_at: null,
		progress: 0
	},
	{
		badge_id: 'week_streak',
		name: 'Semaine parfaite',
		description: 'Maintenez une série de 7 jours',
		icon: '🔥',
		earned_at: null,
		progress: 0
	},
	{
		badge_id: 'hundred_reviews',
		name: 'Centurion',
		description: 'Complétez 100 révisions',
		icon: '💯',
		earned_at: null,
		progress: 0
	},
	{
		badge_id: 'month_streak',
		name: 'Mois entier',
		description: 'Maintenez une série de 30 jours',
		icon: '🏆',
		earned_at: null,
		progress: 0
	},
	{
		badge_id: 'early_bird',
		name: 'Lève-tôt',
		description: 'Révisez avant 8h du matin',
		icon: '🌅',
		earned_at: null,
		progress: 0
	},
	{
		badge_id: 'perfect_score',
		name: 'Excellence',
		description: 'Obtenez un score de 5 sur 10 notes consécutives',
		icon: '⭐',
		earned_at: null,
		progress: 0
	}
];

const DEFAULT_STATS: GamificationStats = {
	streak: DEFAULT_STREAK,
	badges: DEFAULT_BADGES,
	total_reviews: 0,
	reviews_this_week: 0,
	xp_total: 0,
	level: 1
};

// ============================================================================
// STATE
// ============================================================================

interface GamificationState {
	stats: GamificationStats;
	loading: boolean;
	lastUpdated: Date | null;
}

let state = $state<GamificationState>({
	stats: DEFAULT_STATS,
	loading: false,
	lastUpdated: null
});

// ============================================================================
// PERSISTENCE
// ============================================================================

function loadFromStorage(): GamificationStats | null {
	if (typeof localStorage === 'undefined') return null;

	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored) {
			return JSON.parse(stored);
		}
	} catch (err) {
		console.error('Failed to load gamification data:', err);
	}
	return null;
}

function saveToStorage(stats: GamificationStats): void {
	if (typeof localStorage === 'undefined') return;

	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(stats));
	} catch (err) {
		console.error('Failed to save gamification data:', err);
	}
}

// ============================================================================
// COMPUTED VALUES
// ============================================================================

const level = $derived(Math.floor(state.stats.xp_total / 100) + 1);
const xpForNextLevel = $derived((level) * 100);
const xpProgress = $derived(state.stats.xp_total % 100);
const earnedBadges = $derived(state.stats.badges.filter((b) => b.earned_at !== null));
const pendingBadges = $derived(state.stats.badges.filter((b) => b.earned_at === null));

// ============================================================================
// ACTIONS
// ============================================================================

function initialize(): void {
	const stored = loadFromStorage();
	if (stored) {
		state.stats = stored;
		state.lastUpdated = new Date();
	}

	// Check if streak needs to be reset
	checkStreakStatus();
}

function checkStreakStatus(): void {
	const { streak } = state.stats;
	if (!streak.last_review_date) return;

	const lastReview = new Date(streak.last_review_date);
	const today = new Date();
	today.setHours(0, 0, 0, 0);
	lastReview.setHours(0, 0, 0, 0);

	const diffDays = Math.floor((today.getTime() - lastReview.getTime()) / (1000 * 60 * 60 * 24));

	// If more than 1 day since last review, streak is broken
	if (diffDays > 1) {
		state.stats = {
			...state.stats,
			streak: {
				...streak,
				current_streak: 0,
				streak_maintained: false
			}
		};
		saveToStorage(state.stats);
	} else if (diffDays === 1) {
		// Streak is at risk - need to review today
		state.stats = {
			...state.stats,
			streak: {
				...streak,
				streak_maintained: false
			}
		};
	}
}

function recordReview(quality: number): void {
	const today = new Date();
	const todayStr = today.toISOString().split('T')[0];
	const { streak } = state.stats;

	// Check if this is first review today
	let newStreak = streak.current_streak;
	let lastReviewDate = streak.last_review_date;

	if (lastReviewDate) {
		const lastDate = lastReviewDate.split('T')[0];
		if (lastDate !== todayStr) {
			// New day, increment streak
			newStreak++;
		}
	} else {
		// First ever review
		newStreak = 1;
	}

	// Update longest streak
	const newLongest = Math.max(streak.longest_streak, newStreak);

	// Calculate XP (base 10, bonus for quality)
	const baseXP = 10;
	const qualityBonus = quality >= 4 ? 5 : quality >= 3 ? 2 : 0;
	const streakBonus = Math.min(newStreak, 10); // Max 10 bonus for streak
	const totalXP = baseXP + qualityBonus + streakBonus;

	// Update stats
	state.stats = {
		...state.stats,
		streak: {
			current_streak: newStreak,
			longest_streak: newLongest,
			last_review_date: today.toISOString(),
			streak_maintained: true
		},
		total_reviews: state.stats.total_reviews + 1,
		reviews_this_week: state.stats.reviews_this_week + 1,
		xp_total: state.stats.xp_total + totalXP,
		level: Math.floor((state.stats.xp_total + totalXP) / 100) + 1
	};

	// Check for badge unlocks
	checkBadgeUnlocks(quality);

	// Save
	saveToStorage(state.stats);
	state.lastUpdated = new Date();
}

function checkBadgeUnlocks(quality: number): void {
	const now = new Date().toISOString();
	const badges = [...state.stats.badges];
	let updated = false;

	// First review badge
	const firstReview = badges.find((b) => b.badge_id === 'first_review');
	if (firstReview && !firstReview.earned_at && state.stats.total_reviews >= 1) {
		firstReview.earned_at = now;
		firstReview.progress = 100;
		updated = true;
	}

	// Week streak badge
	const weekStreak = badges.find((b) => b.badge_id === 'week_streak');
	if (weekStreak && !weekStreak.earned_at) {
		weekStreak.progress = Math.min(100, (state.stats.streak.current_streak / 7) * 100);
		if (state.stats.streak.current_streak >= 7) {
			weekStreak.earned_at = now;
			updated = true;
		}
	}

	// Hundred reviews badge
	const hundredReviews = badges.find((b) => b.badge_id === 'hundred_reviews');
	if (hundredReviews && !hundredReviews.earned_at) {
		hundredReviews.progress = Math.min(100, (state.stats.total_reviews / 100) * 100);
		if (state.stats.total_reviews >= 100) {
			hundredReviews.earned_at = now;
			updated = true;
		}
	}

	// Month streak badge
	const monthStreak = badges.find((b) => b.badge_id === 'month_streak');
	if (monthStreak && !monthStreak.earned_at) {
		monthStreak.progress = Math.min(100, (state.stats.streak.current_streak / 30) * 100);
		if (state.stats.streak.current_streak >= 30) {
			monthStreak.earned_at = now;
			updated = true;
		}
	}

	// Early bird badge
	const earlyBird = badges.find((b) => b.badge_id === 'early_bird');
	if (earlyBird && !earlyBird.earned_at) {
		const hour = new Date().getHours();
		if (hour < 8) {
			earlyBird.earned_at = now;
			earlyBird.progress = 100;
			updated = true;
		}
	}

	if (updated) {
		state.stats = { ...state.stats, badges };
	}
}

function resetStats(): void {
	state.stats = DEFAULT_STATS;
	saveToStorage(state.stats);
	state.lastUpdated = new Date();
}

// ============================================================================
// EXPORT STORE
// ============================================================================

export const gamificationStore = {
	// State getters
	get stats() {
		return state.stats;
	},
	get loading() {
		return state.loading;
	},
	get lastUpdated() {
		return state.lastUpdated;
	},

	// Streak getters
	get streak() {
		return state.stats.streak;
	},
	get currentStreak() {
		return state.stats.streak.current_streak;
	},
	get longestStreak() {
		return state.stats.streak.longest_streak;
	},

	// XP/Level getters
	get level() {
		return level;
	},
	get xpTotal() {
		return state.stats.xp_total;
	},
	get xpProgress() {
		return xpProgress;
	},
	get xpForNextLevel() {
		return xpForNextLevel;
	},

	// Badge getters
	get badges() {
		return state.stats.badges;
	},
	get earnedBadges() {
		return earnedBadges;
	},
	get pendingBadges() {
		return pendingBadges;
	},

	// Stats getters
	get totalReviews() {
		return state.stats.total_reviews;
	},
	get reviewsThisWeek() {
		return state.stats.reviews_this_week;
	},

	// Actions
	initialize,
	recordReview,
	checkStreakStatus,
	resetStats
};

export type { StreakInfo, GamificationStats, ReviewBadge };
