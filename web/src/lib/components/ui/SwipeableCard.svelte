<script lang="ts">
	import type { Snippet } from 'svelte';
	import { haptic } from '$lib/utils/haptics';

	interface SwipeAction {
		icon: string;
		label: string;
		color: string;
		action: () => void;
	}

	interface Props {
		leftAction?: SwipeAction;
		rightAction?: SwipeAction;
		threshold?: number;
		class?: string;
		children?: Snippet;
	}

	let {
		leftAction,
		rightAction,
		threshold = 80,
		class: className = '',
		children
	}: Props = $props();

	let offsetX = $state(0);
	let startX = $state(0);
	let isSwiping = $state(false);
	let cardRef: HTMLDivElement | null = $state(null);

	const leftProgress = $derived(Math.min(Math.max(-offsetX, 0) / threshold, 1));
	const rightProgress = $derived(Math.min(Math.max(offsetX, 0) / threshold, 1));
	const canTriggerLeft = $derived(leftAction && -offsetX >= threshold);
	const canTriggerRight = $derived(rightAction && offsetX >= threshold);

	function handleTouchStart(e: TouchEvent) {
		startX = e.touches[0].clientX;
		isSwiping = true;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isSwiping) return;

		const currentX = e.touches[0].clientX;
		let diff = currentX - startX;

		// Limit swipe based on available actions
		if (diff > 0 && !rightAction) diff = Math.min(diff, 20);
		if (diff < 0 && !leftAction) diff = Math.max(diff, -20);

		// Add resistance past threshold
		if (Math.abs(diff) > threshold) {
			const excess = Math.abs(diff) - threshold;
			diff = Math.sign(diff) * (threshold + excess * 0.3);
		}

		offsetX = diff;

		// Haptic feedback when threshold is crossed
		if ((canTriggerLeft || canTriggerRight) && Math.abs(diff) >= threshold) {
			haptic('light');
		}
	}

	function handleTouchEnd() {
		if (!isSwiping) return;
		isSwiping = false;

		if (canTriggerLeft && leftAction) {
			haptic('medium');
			leftAction.action();
		} else if (canTriggerRight && rightAction) {
			haptic('medium');
			rightAction.action();
		}

		offsetX = 0;
	}
</script>

<div class="relative overflow-hidden rounded-xl {className}">
	<!-- Left action background (swipe right to reveal) -->
	{#if rightAction}
		<div
			class="absolute inset-y-0 left-0 flex items-center justify-start pl-4 transition-opacity"
			style="background-color: {rightAction.color}; width: {Math.max(offsetX, 0)}px; opacity: {rightProgress}"
		>
			{#if rightProgress > 0.3}
				<span class="text-white text-lg">{rightAction.icon}</span>
			{/if}
		</div>
	{/if}

	<!-- Right action background (swipe left to reveal) -->
	{#if leftAction}
		<div
			class="absolute inset-y-0 right-0 flex items-center justify-end pr-4 transition-opacity"
			style="background-color: {leftAction.color}; width: {Math.max(-offsetX, 0)}px; opacity: {leftProgress}"
		>
			{#if leftProgress > 0.3}
				<span class="text-white text-lg">{leftAction.icon}</span>
			{/if}
		</div>
	{/if}

	<!-- Card content -->
	<div
		bind:this={cardRef}
		class="relative bg-[var(--color-bg-secondary)] border border-[var(--color-border-light)] transition-transform"
		style="transform: translateX({offsetX}px)"
		ontouchstart={handleTouchStart}
		ontouchmove={handleTouchMove}
		ontouchend={handleTouchEnd}
	>
		{#if children}{@render children()}{/if}
	</div>
</div>
