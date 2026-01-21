<script lang="ts">
	/**
	 * FilageWidget Component
	 * Compact card for dashboard showing daily filage summary
	 */
	import { goto } from '$app/navigation';
	import { Card } from '$lib/components/ui';
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';

	interface Props {
		totalLectures: number;
		completedToday: number;
		questionsCount: number;
		loading?: boolean;
	}

	let { totalLectures, completedToday, questionsCount, loading = false }: Props = $props();

	const remaining = $derived(Math.max(0, totalLectures - completedToday));
	const percent = $derived(totalLectures > 0 ? Math.round((completedToday / totalLectures) * 100) : 100);
	const hasUrgent = $derived(questionsCount > 0);
</script>

<section class="mb-5" data-testid="filage-widget">
	<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
		<span>📋</span> Filage du jour
		{#if hasUrgent}
			<span class="relative flex h-2 w-2">
				<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
				<span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
			</span>
		{/if}
	</h2>

	<Card interactive onclick={() => goto('/memoires/filage')} class={hasUrgent ? 'ring-1 ring-[var(--color-warning)]/30' : ''}>
		<div class="flex items-center justify-between p-3">
			<div class="space-y-1">
				<div class="flex items-baseline gap-2">
					<span class="text-2xl font-bold text-[var(--color-text-primary)]">
						{remaining}
					</span>
					<span class="text-sm text-[var(--color-text-tertiary)]">
						{remaining === 1 ? 'note à revoir' : 'notes à revoir'}
					</span>
				</div>

				{#if questionsCount > 0}
					<p class="text-xs text-[var(--color-warning)] flex items-center gap-1">
						<span>❓</span>
						<span>{questionsCount} question{questionsCount > 1 ? 's' : ''} en attente</span>
					</p>
				{:else if completedToday > 0}
					<p class="text-xs text-[var(--color-text-tertiary)]">
						{completedToday} terminée{completedToday > 1 ? 's' : ''} aujourd'hui
					</p>
				{/if}
			</div>

			<div class="flex items-center gap-3">
				{#if loading}
					<div class="w-12 h-12 flex items-center justify-center">
						<div class="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
					</div>
				{:else}
					<ProgressRing
						{percent}
						size={48}
						color={percent === 100 ? 'success' : 'primary'}
					/>
				{/if}
				<span class="text-[var(--color-text-tertiary)]">→</span>
			</div>
		</div>
	</Card>
</section>
