<script lang="ts">
	/**
	 * ProgressRing Component
	 * Circular progress indicator with animated SVG
	 */

	interface Props {
		percent: number;
		size?: number;
		strokeWidth?: number;
		showLabel?: boolean;
		color?: 'primary' | 'success' | 'warning' | 'danger';
	}

	let { percent, size = 48, strokeWidth = 4, showLabel = true, color = 'primary' }: Props =
		$props();

	const radius = $derived((size - strokeWidth) / 2);
	const circumference = $derived(2 * Math.PI * radius);
	const offset = $derived(circumference - (percent / 100) * circumference);

	const colorClasses: Record<string, string> = {
		primary: 'stroke-blue-500',
		success: 'stroke-green-500',
		warning: 'stroke-amber-500',
		danger: 'stroke-red-500'
	};

	const trackColor = 'stroke-gray-200 dark:stroke-gray-700';
</script>

<div class="relative inline-flex items-center justify-center" style="width: {size}px; height: {size}px;">
	<svg
		class="transform -rotate-90"
		width={size}
		height={size}
		viewBox="0 0 {size} {size}"
		fill="none"
	>
		<!-- Track -->
		<circle
			class={trackColor}
			cx={size / 2}
			cy={size / 2}
			r={radius}
			stroke-width={strokeWidth}
			fill="none"
		/>
		<!-- Progress -->
		<circle
			class="{colorClasses[color]} transition-all duration-300 ease-out"
			cx={size / 2}
			cy={size / 2}
			r={radius}
			stroke-width={strokeWidth}
			fill="none"
			stroke-linecap="round"
			stroke-dasharray={circumference}
			stroke-dashoffset={offset}
		/>
	</svg>
	{#if showLabel}
		<span
			class="absolute text-xs font-medium text-gray-700 dark:text-gray-300"
			style="font-size: {size * 0.25}px"
		>
			{Math.round(percent)}%
		</span>
	{/if}
</div>
