<script lang="ts">
	/**
	 * ConfidenceBar Component
	 * Displays AI confidence level with animated fill and color gradient
	 */

	interface Props {
		value: number; // 0-1 range
		showLabel?: boolean;
		showPercentage?: boolean;
		size?: 'sm' | 'md' | 'lg';
		animated?: boolean;
		class?: string;
	}

	let {
		value,
		showLabel = false,
		showPercentage = true,
		size = 'md',
		animated = true,
		class: className = ''
	}: Props = $props();

	// Clamp value between 0 and 1
	const normalizedValue = $derived(Math.max(0, Math.min(1, value)));
	const percentage = $derived(Math.round(normalizedValue * 100));

	// Color based on confidence level
	const color = $derived.by(() => {
		if (normalizedValue >= 0.8) return 'var(--color-success)';
		if (normalizedValue >= 0.6) return 'var(--color-accent)';
		if (normalizedValue >= 0.4) return 'var(--color-warning)';
		return 'var(--color-error)';
	});

	// Label based on confidence level (French)
	const label = $derived.by(() => {
		if (normalizedValue >= 0.9) return 'Confiance';
		if (normalizedValue >= 0.7) return 'Probable';
		if (normalizedValue >= 0.5) return 'Possible';
		if (normalizedValue >= 0.3) return 'Incertain';
		return 'Faible';
	});

	const sizeClasses = {
		sm: { bar: 'h-1', text: 'text-xs' },
		md: { bar: 'h-1.5', text: 'text-sm' },
		lg: { bar: 'h-2', text: 'text-base' }
	};
</script>

<div class="confidence-bar {className}">
	{#if showLabel || showPercentage}
		<div class="flex items-center justify-between mb-1 {sizeClasses[size].text}">
			{#if showLabel}
				<span class="text-[var(--color-text-secondary)] font-medium">{label}</span>
			{/if}
			{#if showPercentage}
				<span class="text-[var(--color-text-tertiary)] tabular-nums {showLabel ? '' : 'ml-auto'}">{percentage}%</span>
			{/if}
		</div>
	{/if}

	<div
		class="w-full {sizeClasses[size].bar} rounded-full bg-[var(--color-bg-tertiary)] overflow-hidden"
		role="progressbar"
		aria-valuenow={percentage}
		aria-valuemin={0}
		aria-valuemax={100}
		aria-label="Confiance IA: {percentage}%"
	>
		<div
			class="h-full rounded-full {animated ? 'transition-all duration-500 ease-out' : ''}"
			style="width: {percentage}%; background-color: {color};"
		></div>
	</div>
</div>
