<script lang="ts">
	import type { Snippet } from 'svelte';
	import { haptic } from '$lib/utils/haptics';

	interface Props {
		onrefresh?: () => Promise<void>;
		threshold?: number;
		children?: Snippet;
	}

	let {
		onrefresh,
		threshold = 80,
		children
	}: Props = $props();

	let pullDistance = $state(0);
	let isRefreshing = $state(false);
	let startY = $state(0);
	let isPulling = $state(false);

	const progress = $derived(Math.min(pullDistance / threshold, 1));
	const canRefresh = $derived(pullDistance >= threshold);

	function handleTouchStart(e: TouchEvent) {
		// Only activate if at the top of the scroll container
		const target = e.currentTarget as HTMLElement;
		if (target.scrollTop === 0 && !isRefreshing) {
			startY = e.touches[0].clientY;
			isPulling = true;
		}
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isPulling || isRefreshing) return;

		const currentY = e.touches[0].clientY;
		const diff = currentY - startY;

		if (diff > 0) {
			// Add resistance to the pull
			pullDistance = Math.min(diff * 0.5, threshold * 1.5);

			// Haptic feedback when threshold is crossed
			if (pullDistance >= threshold && !canRefresh) {
				haptic('light');
			}
		}
	}

	async function handleTouchEnd() {
		if (!isPulling) return;
		isPulling = false;

		if (canRefresh && onrefresh) {
			isRefreshing = true;
			haptic('medium');

			try {
				await onrefresh();
			} finally {
				isRefreshing = false;
				pullDistance = 0;
			}
		} else {
			pullDistance = 0;
		}
	}
</script>

<div
	class="relative overflow-auto"
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
>
	<!-- Pull indicator -->
	<div
		class="absolute left-0 right-0 flex justify-center items-center transition-transform duration-200 pointer-events-none z-10"
		style="transform: translateY({Math.max(pullDistance - 40, -40)}px); opacity: {progress}"
	>
		<div
			class="w-8 h-8 flex items-center justify-center rounded-full bg-[var(--color-bg-secondary)] border border-[var(--color-border-light)] shadow-sm"
		>
			{#if isRefreshing}
				<span class="animate-spin text-sm">↻</span>
			{:else if canRefresh}
				<span class="text-sm text-[var(--color-accent)]">↓</span>
			{:else}
				<span
					class="text-sm text-[var(--color-text-tertiary)] transition-transform"
					style="transform: rotate({progress * 180}deg)"
				>↓</span>
			{/if}
		</div>
	</div>

	<!-- Content with pull offset -->
	<div
		class="transition-transform duration-200"
		style="transform: translateY({isPulling || isRefreshing ? pullDistance : 0}px)"
	>
		{#if children}{@render children()}{/if}
	</div>
</div>
