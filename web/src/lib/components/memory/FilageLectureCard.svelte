<script lang="ts">
	/**
	 * FilageLectureCard Component
	 * Card for displaying a lecture in the filage list
	 */
	import type { FilageLecture } from '$lib/api/types/memory-cycles';
	import { Card, Badge } from '$lib/components/ui';
	import ConfidenceBar from '$lib/components/ui/ConfidenceBar.svelte';

	interface Props {
		lecture: FilageLecture;
		onclick?: () => void;
		selected?: boolean;
	}

	let { lecture, onclick, selected = false }: Props = $props();

	// Note type icons
	const typeIcons: Record<string, string> = {
		personne: '👤',
		organisation: '🏢',
		projet: '📁',
		concept: '💡',
		lieu: '📍',
		evenement: '📅',
		produit: '📦',
		default: '📝'
	};

	// Get quality color based on score
	function getQualityColor(score: number | null): 'primary' | 'success' | 'warning' | 'danger' {
		if (score === null) return 'primary';
		if (score >= 80) return 'success';
		if (score >= 60) return 'warning';
		return 'danger';
	}

	const icon = $derived(typeIcons[lecture.note_type.toLowerCase()] || typeIcons.default);
	const qualityColor = $derived(getQualityColor(lecture.quality_score));
</script>

<Card
	variant={selected ? 'elevated' : 'glass-subtle'}
	interactive
	{onclick}
	class="transition-all duration-200 {selected ? 'ring-2 ring-[var(--color-accent)]' : ''}"
>
	<div class="flex items-start gap-3">
		<!-- Icon -->
		<div class="flex-shrink-0 w-10 h-10 rounded-xl bg-[var(--glass-subtle)] flex items-center justify-center text-xl">
			{icon}
		</div>

		<!-- Content -->
		<div class="flex-1 min-w-0">
			<!-- Title and badges -->
			<div class="flex items-start justify-between gap-2">
				<h3 class="font-medium text-[var(--color-text-primary)] truncate">
					{lecture.note_title}
				</h3>
				{#if lecture.questions_pending}
					<Badge class="flex-shrink-0 bg-red-500/10 text-red-500">
						<span class="flex items-center gap-1">
							<span>?</span>
							<span class="text-xs">{lecture.questions_count}</span>
						</span>
					</Badge>
				{/if}
			</div>

			<!-- Reason -->
			<p class="text-sm text-[var(--color-text-secondary)] mt-0.5 line-clamp-1">
				{lecture.reason}
			</p>

			<!-- Quality score bar -->
			{#if lecture.quality_score !== null}
				<div class="mt-2 flex items-center gap-2">
					<span class="text-xs text-[var(--color-text-tertiary)]">Q:</span>
					<div class="flex-1 max-w-[100px]">
						<ConfidenceBar value={lecture.quality_score / 100} size="sm" showPercentage={false} />
					</div>
					<span class="text-xs font-medium text-[var(--color-text-secondary)]">
						{lecture.quality_score}%
					</span>
				</div>
			{/if}

			<!-- Type badge -->
			<div class="mt-2 flex items-center gap-2">
				<Badge class="bg-[var(--glass-subtle)] text-[var(--color-text-tertiary)]">
					{lecture.note_type}
				</Badge>
				{#if lecture.related_event_id}
					<Badge class="bg-[var(--color-event-calendar)]/10 text-[var(--color-event-calendar)]">
						Lié
					</Badge>
				{/if}
			</div>
		</div>

		<!-- Arrow indicator -->
		<div class="flex-shrink-0 text-[var(--color-text-tertiary)]">
			<span>→</span>
		</div>
	</div>
</Card>
