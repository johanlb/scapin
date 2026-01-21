<script lang="ts">
	/**
	 * FilageProgressHeader Component
	 * Sticky header with progress bar for filage page
	 */
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';

	interface Props {
		title: string;
		current: number;
		total: number;
		onBack?: () => void;
		onRefresh?: () => void;
		loading?: boolean;
	}

	let { title, current, total, onBack, onRefresh, loading = false }: Props = $props();

	const percent = $derived(total > 0 ? Math.round((current / total) * 100) : 0);
</script>

<header
	class="sticky top-0 z-10 bg-[var(--color-bg-primary)]/80 backdrop-blur-md border-b border-[var(--glass-border-subtle)]"
>
	<div class="max-w-2xl mx-auto px-4 py-3">
		<!-- Top row: navigation and actions -->
		<div class="flex items-center justify-between mb-2">
			{#if onBack}
				<button
					type="button"
					onclick={onBack}
					class="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors liquid-press"
				>
					<span>←</span>
					<span class="text-sm">Retour</span>
				</button>
			{:else}
				<div></div>
			{/if}

			<h1 class="text-base font-semibold text-[var(--color-text-primary)]">
				{title}
			</h1>

			{#if onRefresh}
				<button
					type="button"
					onclick={onRefresh}
					disabled={loading}
					class="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors liquid-press disabled:opacity-50"
					aria-label="Rafraîchir"
				>
					<span class={loading ? 'animate-spin inline-block' : ''}>⟳</span>
				</button>
			{:else}
				<div class="w-8"></div>
			{/if}
		</div>

		<!-- Progress bar -->
		<div class="flex items-center gap-3">
			<div class="flex-1 h-2 bg-[var(--glass-subtle)] rounded-full overflow-hidden">
				<div
					class="h-full bg-[var(--color-accent)] transition-all duration-300 ease-out rounded-full"
					style="width: {percent}%"
				></div>
			</div>
			<div class="flex items-center gap-2">
				<span class="text-sm text-[var(--color-text-secondary)]">
					{current}/{total}
				</span>
				<ProgressRing
					{percent}
					size={28}
					strokeWidth={3}
					showLabel={false}
					color="primary"
				/>
			</div>
		</div>
	</div>
</header>
