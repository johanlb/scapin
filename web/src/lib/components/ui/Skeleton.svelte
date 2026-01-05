<script lang="ts">
	/**
	 * Skeleton Component
	 * Loading placeholder with shimmer animation
	 * Supports various shapes: text, avatar, card, rectangular
	 */

	interface Props {
		variant?: 'text' | 'avatar' | 'card' | 'rectangular' | 'circular';
		width?: string;
		height?: string;
		lines?: number; // For text variant, number of lines
		animated?: boolean;
		class?: string;
	}

	let {
		variant = 'rectangular',
		width,
		height,
		lines = 1,
		animated = true,
		class: className = ''
	}: Props = $props();

	// Default dimensions based on variant
	const defaultDimensions = {
		text: { width: '100%', height: '1em' },
		avatar: { width: '40px', height: '40px' },
		card: { width: '100%', height: '120px' },
		rectangular: { width: '100%', height: '20px' },
		circular: { width: '40px', height: '40px' }
	};

	const variantClasses = {
		text: 'rounded',
		avatar: 'rounded-full',
		card: 'rounded-2xl',
		rectangular: 'rounded-lg',
		circular: 'rounded-full'
	};

	const finalWidth = $derived(width ?? defaultDimensions[variant].width);
	const finalHeight = $derived(height ?? defaultDimensions[variant].height);
</script>

{#if variant === 'text' && lines > 1}
	<div class="flex flex-col gap-2 {className}">
		{#each Array(lines) as _, i}
			<div
				class="skeleton {variantClasses[variant]} {animated ? 'animate-shimmer' : ''}"
				style="width: {i === lines - 1 ? '70%' : finalWidth}; height: {finalHeight};"
				aria-hidden="true"
			></div>
		{/each}
	</div>
{:else}
	<div
		class="skeleton {variantClasses[variant]} {animated ? 'animate-shimmer' : ''} {className}"
		style="width: {finalWidth}; height: {finalHeight};"
		aria-hidden="true"
	></div>
{/if}

<style>
	.skeleton {
		background: linear-gradient(
			90deg,
			var(--color-bg-tertiary) 0%,
			var(--color-bg-secondary) 50%,
			var(--color-bg-tertiary) 100%
		);
		background-size: 200% 100%;
	}

	.animate-shimmer {
		animation: shimmer 1.5s ease-in-out infinite;
	}

	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	/* Respect reduced motion preference */
	@media (prefers-reduced-motion: reduce) {
		.animate-shimmer {
			animation: none;
			background: var(--color-bg-tertiary);
		}
	}
</style>
