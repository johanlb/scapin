<script lang="ts">
	/**
	 * FilageSection Component
	 * Grouped section with title, icon and count
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		icon: string;
		count: number;
		collapsed?: boolean;
		children?: Snippet;
	}

	let { title, icon, count, collapsed = false, children }: Props = $props();

	let isCollapsed = $state<boolean>(false);

	// Initialize state from prop
	$effect(() => {
		isCollapsed = collapsed;
	});

	function toggleCollapse() {
		isCollapsed = !isCollapsed;
	}
</script>

<section class="mb-4">
	<!-- Section header -->
	<button
		type="button"
		onclick={toggleCollapse}
		class="w-full flex items-center justify-between px-2 py-2 rounded-lg hover:bg-[var(--glass-subtle)] transition-colors"
	>
		<div class="flex items-center gap-2">
			<span class="text-lg">{icon}</span>
			<h2 class="text-sm font-semibold text-[var(--color-text-primary)]">
				{title}
			</h2>
			<span class="text-xs px-1.5 py-0.5 rounded-full bg-[var(--glass-subtle)] text-[var(--color-text-secondary)]">
				{count}
			</span>
		</div>
		<span
			class="text-[var(--color-text-tertiary)] transition-transform duration-200"
			class:rotate-180={!isCollapsed}
		>
			▼
		</span>
	</button>

	<!-- Section content -->
	{#if !isCollapsed}
		<div class="mt-2 space-y-2 animate-fade-in">
			{#if children}{@render children()}{/if}
		</div>
	{/if}
</section>

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-fade-in {
		animation: fade-in 0.2s ease-out;
	}
</style>
