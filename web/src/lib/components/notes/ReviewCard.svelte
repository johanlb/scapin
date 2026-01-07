<script lang="ts">
	/**
	 * ReviewCard Component
	 * Displays a note for review with SM-2 metadata
	 */
	import type { NoteReviewMetadata } from '$lib/api';

	interface Props {
		note: NoteReviewMetadata;
		onViewNote?: () => void;
	}

	let { note, onViewNote }: Props = $props();

	// Note type icons
	const typeIcons: Record<string, string> = {
		personne: '👤',
		projet: '📋',
		concept: '💡',
		lieu: '📍',
		organisation: '🏢',
		souvenir: '🎯',
		autre: '📝'
	};

	// Importance badges
	const importanceBadges: Record<string, { bg: string; text: string }> = {
		high: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-400' },
		normal: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-400' },
		low: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400' }
	};

	// Quality labels
	const qualityLabels = ['Blackout', 'Difficile', 'Moyen', 'Bien', 'Excellent', 'Parfait'];

	function formatInterval(hours: number): string {
		if (hours < 24) {
			return `${Math.round(hours)}h`;
		}
		const days = Math.round(hours / 24);
		return `${days}j`;
	}

	function formatNextReview(dateStr: string | null): string {
		if (!dateStr) return 'Non planifié';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = date.getTime() - now.getTime();
		const diffHours = diffMs / (1000 * 60 * 60);

		if (diffHours < 0) {
			return 'En retard';
		} else if (diffHours < 1) {
			return 'Maintenant';
		} else if (diffHours < 24) {
			return `Dans ${Math.round(diffHours)}h`;
		} else {
			return `Dans ${Math.round(diffHours / 24)}j`;
		}
	}

	const icon = $derived(typeIcons[note.note_type] ?? '📝');
	const badge = $derived(importanceBadges[note.importance] ?? importanceBadges.normal);
</script>

<div
	class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm"
>
	<!-- Header -->
	<div class="flex items-start justify-between gap-3 mb-4">
		<div class="flex items-center gap-3">
			<span class="text-3xl">{icon}</span>
			<div>
				<h3 class="font-semibold text-gray-900 dark:text-white text-lg">
					{note.note_id}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400 capitalize">{note.note_type}</p>
			</div>
		</div>
		<span class="px-2 py-1 rounded text-xs font-medium {badge.bg} {badge.text}">
			{note.importance}
		</span>
	</div>

	<!-- SM-2 Metadata -->
	<div class="grid grid-cols-2 gap-3 mb-4 text-sm">
		<div class="flex items-center gap-2">
			<span class="text-gray-500 dark:text-gray-400">EF:</span>
			<span class="font-medium text-gray-900 dark:text-white">
				{(note.easiness_factor ?? 2.5).toFixed(2)}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<span class="text-gray-500 dark:text-gray-400">Rep:</span>
			<span class="font-medium text-gray-900 dark:text-white">{note.repetition_number ?? 0}</span>
		</div>
		<div class="flex items-center gap-2">
			<span class="text-gray-500 dark:text-gray-400">Intervalle:</span>
			<span class="font-medium text-gray-900 dark:text-white">
				{formatInterval(note.interval_hours ?? 0)}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<span class="text-gray-500 dark:text-gray-400">Revisions:</span>
			<span class="font-medium text-gray-900 dark:text-white">{note.review_count ?? 0}</span>
		</div>
	</div>

	<!-- Last Quality -->
	{#if note.last_quality != null && note.last_quality >= 0 && note.last_quality <= 5}
		<div class="flex items-center gap-2 mb-4 text-sm">
			<span class="text-gray-500 dark:text-gray-400">Dernière note:</span>
			<span class="font-medium text-gray-900 dark:text-white">
				{note.last_quality} ({qualityLabels[note.last_quality] ?? 'Inconnu'})
			</span>
		</div>
	{/if}

	<!-- Next Review -->
	<div class="flex items-center gap-2 mb-4 text-sm">
		<span class="text-gray-500 dark:text-gray-400">Prochaine révision:</span>
		<span class="font-medium text-blue-600 dark:text-blue-400">
			{formatNextReview(note.next_review)}
		</span>
	</div>

	<!-- Action Button -->
	{#if onViewNote}
		<button
			type="button"
			onclick={onViewNote}
			class="w-full mt-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400
				bg-blue-50 dark:bg-blue-900/20 rounded-lg
				hover:bg-blue-100 dark:hover:bg-blue-900/30
				transition-colors"
		>
			Voir la note
		</button>
	{/if}
</div>
