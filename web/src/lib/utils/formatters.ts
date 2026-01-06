/**
 * Time formatting utilities
 */

export function formatRelativeTime(isoString: string): string {
	const date = new Date(isoString);
	const now = new Date();
	const diffMs = date.getTime() - now.getTime();
	const diffMins = Math.round(diffMs / (1000 * 60));

	if (diffMins < 0) {
		const absMins = Math.abs(diffMins);
		if (absMins < 2) return "à l'instant";
		if (absMins < 60) return `il y a ${absMins} min`;
		const hours = Math.round(absMins / 60);
		if (hours < 24) return `il y a ${hours}h`;
		const days = Math.round(hours / 24);
		if (days < 7) return `il y a ${days}j`;
		if (days < 30) {
			const weeks = Math.round(days / 7);
			return `il y a ${weeks} sem`;
		}
		if (days < 365) {
			const months = Math.round(days / 30);
			return `il y a ${months} mois`;
		}
		const years = Math.round(days / 365);
		return years === 1 ? 'il y a 1 an' : `il y a ${years} ans`;
	}
	if (diffMins < 2) return 'maintenant';
	if (diffMins < 60) return `dans ${diffMins} min`;
	const futureHours = Math.round(diffMins / 60);
	if (futureHours < 24) return `dans ${futureHours}h`;
	const futureDays = Math.round(futureHours / 24);
	if (futureDays < 7) return `dans ${futureDays}j`;
	if (futureDays < 30) {
		const weeks = Math.round(futureDays / 7);
		return `dans ${weeks} sem`;
	}
	const months = Math.round(futureDays / 30);
	return `dans ${months} mois`;
}

export function formatDate(isoString: string, locale = 'fr-FR'): string {
	return new Date(isoString).toLocaleDateString(locale, {
		weekday: 'long',
		day: 'numeric',
		month: 'long'
	});
}

export function formatDateTime(isoString: string, locale = 'fr-FR'): string {
	return new Date(isoString).toLocaleString(locale, {
		weekday: 'short',
		day: 'numeric',
		month: 'short',
		hour: '2-digit',
		minute: '2-digit'
	});
}
