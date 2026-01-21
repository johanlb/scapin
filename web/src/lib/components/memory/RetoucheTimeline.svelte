<script lang="ts">
	/**
	 * RetoucheTimeline Component
	 * Timeline showing AI improvement history for a note
	 */
	import type { RetoucheEntry } from '$lib/api/types/memory-cycles';
	import { Card, Badge } from '$lib/components/ui';
	
	interface Props {
		retouches: RetoucheEntry[];
		showChart?: boolean;
	}

	let { retouches, showChart = true }: Props = $props();

	// Model colors
	const modelColors: Record<string, string> = {
		haiku: 'bg-emerald-500',
		sonnet: 'bg-blue-500',
		opus: 'bg-purple-500'
	};

	const modelLabels: Record<string, string> = {
		haiku: 'Haiku',
		sonnet: 'Sonnet',
		opus: 'Opus'
	};

	// Format date
	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Quality delta display
	function formatDelta(before: number | null, after: number | null): string {
		if (before === null || after === null) return '';
		const delta = after - before;
		if (delta > 0) return `+${delta}`;
		if (delta < 0) return `${delta}`;
		return '=';
	}

	function getDeltaColor(before: number | null, after: number | null): string {
		if (before === null || after === null) return 'text-[var(--color-text-tertiary)]';
		const delta = after - before;
		if (delta > 0) return 'text-green-500';
		if (delta < 0) return 'text-red-500';
		return 'text-[var(--color-text-tertiary)]';
	}

	// Chart data
	const chartData = $derived(
		retouches
			.filter((r) => r.quality_after !== null)
			.map((r) => r.quality_after!)
	);
</script>

{#if retouches.length === 0}
	<Card variant="glass-subtle" padding="sm">
		<div class="text-center py-4">
			<span class="text-2xl mb-2 block">✨</span>
			<p class="text-sm text-[var(--color-text-secondary)]">
				Aucune amélioration IA pour cette note
			</p>
		</div>
	</Card>
{:else}
	<div class="space-y-4">
		<!-- Quality trend mini chart -->
		{#if showChart && chartData.length > 1}
			<Card variant="glass-subtle" padding="sm">
				<h4 class="text-xs font-medium text-[var(--color-text-tertiary)] mb-2">
					Évolution de la qualité
				</h4>
				<div class="flex items-end gap-1 h-12">
					{#each chartData as score, i}
						{@const height = Math.max(4, (score / 100) * 48)}
						{@const isLast = i === chartData.length - 1}
						<div
							class="flex-1 rounded-t transition-all {isLast ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-accent)]/40'}"
							style="height: {height}px"
							title="{score}%"
						></div>
					{/each}
				</div>
				<div class="flex justify-between mt-1 text-[10px] text-[var(--color-text-tertiary)]">
					<span>Premier</span>
					<span>Dernier: {chartData[chartData.length - 1]}%</span>
				</div>
			</Card>
		{/if}

		<!-- Timeline -->
		<div class="relative">
			<!-- Vertical line -->
			<div class="absolute left-4 top-0 bottom-0 w-0.5 bg-[var(--glass-border-subtle)]"></div>

			<!-- Timeline entries -->
			<div class="space-y-4">
				{#each retouches as retouche, i (retouche.retouche_id)}
					<div class="relative flex gap-4">
						<!-- Dot -->
						<div class="relative z-10 flex-shrink-0">
							<div class="w-8 h-8 rounded-full {modelColors[retouche.model_used]} flex items-center justify-center">
								<span class="text-xs text-white font-medium">
									{retouche.model_used.charAt(0).toUpperCase()}
								</span>
							</div>
						</div>

						<!-- Content -->
						<Card variant="glass-subtle" class="flex-1" padding="sm">
							<div class="flex items-start justify-between gap-2 mb-2">
								<div>
									<Badge class="bg-[var(--glass-subtle)] text-[var(--color-text-secondary)]">
										{modelLabels[retouche.model_used]}
									</Badge>
									<span class="text-xs text-[var(--color-text-tertiary)] ml-2">
										{formatDate(retouche.timestamp)}
									</span>
								</div>
								{#if retouche.quality_before !== null || retouche.quality_after !== null}
									<span class="text-sm font-medium {getDeltaColor(retouche.quality_before, retouche.quality_after)}">
										{formatDelta(retouche.quality_before, retouche.quality_after)}
									</span>
								{/if}
							</div>

							<p class="text-sm text-[var(--color-text-secondary)]">
								{retouche.changes_summary}
							</p>

							<!-- Quality scores -->
							{#if retouche.quality_before !== null || retouche.quality_after !== null}
								<div class="flex items-center gap-3 mt-2 text-xs">
									{#if retouche.quality_before !== null}
										<span class="text-[var(--color-text-tertiary)]">
											Avant: {retouche.quality_before}%
										</span>
									{/if}
									{#if retouche.quality_after !== null}
										<span class="text-[var(--color-text-primary)] font-medium">
											Après: {retouche.quality_after}%
										</span>
									{/if}
									<span class="text-[var(--color-text-tertiary)]">
										Conf: {Math.round(retouche.confidence * 100)}%
									</span>
								</div>
							{/if}
						</Card>
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
