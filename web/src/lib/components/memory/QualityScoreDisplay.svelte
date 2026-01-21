<script lang="ts">
	/**
	 * QualityScoreDisplay Component
	 * Displays quality score with ProgressRing and label
	 */
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';

	interface Props {
		score: number | null;
		size?: number;
		showLabel?: boolean;
	}

	let { score, size = 64, showLabel = true }: Props = $props();

	// Determine color based on score
	function getColor(s: number | null): 'success' | 'warning' | 'danger' | 'primary' {
		if (s === null) return 'primary';
		if (s >= 80) return 'success';
		if (s >= 60) return 'warning';
		return 'danger';
	}

	// Get label text
	function getLabel(s: number | null): string {
		if (s === null) return 'Non évaluée';
		if (s >= 80) return 'Excellente';
		if (s >= 60) return 'Bonne';
		if (s >= 40) return 'Moyenne';
		return 'À améliorer';
	}

	const color = $derived(getColor(score));
	const label = $derived(getLabel(score));
	const displayScore = $derived(score ?? 0);
</script>

<div class="flex flex-col items-center gap-2">
	<ProgressRing
		percent={displayScore}
		{size}
		strokeWidth={size > 48 ? 6 : 4}
		{color}
	/>
	{#if showLabel}
		<div class="text-center">
			<p class="text-xs font-medium text-[var(--color-text-secondary)]">
				{label}
			</p>
			{#if score !== null}
				<p class="text-[10px] text-[var(--color-text-tertiary)]">
					Score de qualité
				</p>
			{/if}
		</div>
	{/if}
</div>
