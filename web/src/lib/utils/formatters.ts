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
		if (absMins < 2) return 'à l\'instant';
		if (absMins < 60) return `il y a ${absMins} min`;
		const hours = Math.round(absMins / 60);
		if (hours < 24) return `il y a ${hours}h`;
		return `il y a ${Math.round(hours / 24)}j`;
	}
	if (diffMins < 2) return 'maintenant';
	if (diffMins < 60) return `dans ${diffMins} min`;
	return `dans ${Math.round(diffMins / 60)}h`;
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
