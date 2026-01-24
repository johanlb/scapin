<script lang="ts">
	/**
	 * ReviewCard Component
	 * Displays a note for review with SM-2 metadata
	 *
	 * v3.1: Updated with Liquid Glass design and QualityScoreDisplay
	 */
	import type { NoteReviewMetadata } from '$lib/api';
	import { Card, Badge } from '$lib/components/ui';
	import QualityScoreDisplay from '$lib/components/memory/QualityScoreDisplay.svelte';

	interface Props {
		note: NoteReviewMetadata;
		recentlyImproved?: boolean;
		questionsCount?: number;
		onViewNote?: () => void;
	}

	let { note, recentlyImproved = false, questionsCount = 0, onViewNote }: Props = $props();

	// Note type icons
	const typeIcons: Record<string, string> = {
		personne: '👤',
		projet: '📁',
		concept: '💡',
		lieu: '📍',
		organisation: '🏢',
		evenement: '📅',
		produit: '📦',
		souvenir: '🎯',
		autre: '📝'
	};

	// Importance badges
	const importanceBadges: Record<string, { bg: string; text: string }> = {
		high: { bg: 'bg-red-500/10', text: 'text-red-500' },
		normal: { bg: 'bg-[var(--glass-subtle)]', text: 'text-[var(--color-text-secondary)]' },
		low: { bg: 'bg-green-500/10', text: 'text-green-500' }
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

	function getNextReviewClass(dateStr: string | null): string {
		if (!dateStr) return 'text-[var(--color-text-tertiary)]';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = date.getTime() - now.getTime();
		const diffHours = diffMs / (1000 * 60 * 60);

		if (diffHours < 0) {
			return 'text-red-500';
		} else if (diffHours < 24) {
			return 'text-[var(--color-warning)]';
		}
		return 'text-[var(--color-accent)]';
	}

	const icon = $derived(typeIcons[note.note_type] ?? '📝');
	const badge = $derived(importanceBadges[note.importance] ?? importanceBadges.normal);

	// Convert quality_score from note if available (assuming it might be added to the type)
	const qualityScore = $derived((note as any).quality_score ?? null);
</script>

<Card variant="glass">
	<!-- Header -->
	<div class="flex items-start justify-between gap-3 mb-4">
		<div class="flex items-center gap-3">
			<div class="w-12 h-12 rounded-xl bg-[var(--glass-subtle)] flex items-center justify-center text-2xl">
				{icon}
			</div>
			<div>
				<h3 class="font-semibold text-[var(--color-text-primary)] text-lg">
					{note.note_id}
				</h3>
				<div class="flex items-center gap-2 mt-1">
					<span class="text-sm text-[var(--color-text-secondary)] capitalize">{note.note_type}</span>
					{#if recentlyImproved}
						<Badge class="bg-purple-500/10 text-purple-500">
							<span class="flex items-center gap-1">
								<span>✨</span>
								<span>Améliorée</span>
							</span>
						</Badge>
					{/if}
					{#if questionsCount > 0}
						<Badge class="bg-[var(--color-warning)]/10 text-[var(--color-warning)]">
							<span class="flex items-center gap-1">
								<span>❓</span>
								<span>{questionsCount}</span>
							</span>
						</Badge>
					{/if}
				</div>
			</div>
		</div>

		<!-- Quality score or importance badge -->
		{#if qualityScore !== null}
			<QualityScoreDisplay score={qualityScore} size={56} />
		{:else}
			<span class="px-2 py-1 rounded-lg text-xs font-medium {badge.bg} {badge.text}">
				{note.importance}
			</span>
		{/if}
	</div>

	<!-- SM-2 Metadata - Compact grid -->
	<div class="p-3 bg-[var(--glass-subtle)] rounded-xl mb-4">
		<div class="grid grid-cols-4 gap-2 text-center">
			<div
				title="Facteur de facilité SM-2 (1.3=difficile, 2.5=facile). Influence l'intervalle entre les révisions."
				class="cursor-help"
			>
				<p class="text-xs text-[var(--color-text-tertiary)]">EF</p>
				<p class="font-medium text-[var(--color-text-primary)]">
					{(note.easiness_factor ?? 2.5).toFixed(1)}
				</p>
			</div>
			<div>
				<p class="text-xs text-[var(--color-text-tertiary)]">Rep</p>
				<p class="font-medium text-[var(--color-text-primary)]">{note.repetition_number ?? 0}</p>
			</div>
			<div>
				<p class="text-xs text-[var(--color-text-tertiary)]">Intervalle</p>
				<p class="font-medium text-[var(--color-text-primary)]">
					{formatInterval(note.interval_hours ?? 0)}
				</p>
			</div>
			<div>
				<p class="text-xs text-[var(--color-text-tertiary)]">Revisions</p>
				<p class="font-medium text-[var(--color-text-primary)]">{note.review_count ?? 0}</p>
			</div>
		</div>
	</div>

	<!-- Last Quality & Next Review -->
	<div class="flex items-center justify-between text-sm mb-4">
		{#if note.last_quality != null && note.last_quality >= 0 && note.last_quality <= 5}
			<div class="flex items-center gap-2">
				<span class="text-[var(--color-text-tertiary)]">Dernière:</span>
				<span class="font-medium text-[var(--color-text-primary)]">
					{note.last_quality} ({qualityLabels[note.last_quality] ?? 'Inconnu'})
				</span>
			</div>
		{:else}
			<div></div>
		{/if}
		<div class="flex items-center gap-2">
			<span class="text-[var(--color-text-tertiary)]">Prochaine:</span>
			<span class="font-medium {getNextReviewClass(note.next_review)}">
				{formatNextReview(note.next_review)}
			</span>
		</div>
	</div>

	<!-- Action Button -->
	{#if onViewNote}
		<button
			type="button"
			onclick={onViewNote}
			class="w-full px-4 py-2 text-sm font-medium text-[var(--color-accent)]
				bg-[var(--color-accent)]/10 rounded-xl
				hover:bg-[var(--color-accent)]/20
				transition-colors liquid-press"
		>
			Voir la note complète →
		</button>
	{/if}
</Card>
