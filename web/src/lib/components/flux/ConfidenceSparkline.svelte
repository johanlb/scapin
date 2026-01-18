<script lang="ts">
	import type { PassHistoryEntry } from '$lib/api/client';

	export let passHistory: PassHistoryEntry[];
	export let width: number = 80;
	export let height: number = 24;

	// Extract confidence values for the sparkline
	// Start with first pass's confidence_before, then all confidence_after values
	$: confidencePoints = [
		passHistory[0]?.confidence_before ?? 0,
		...passHistory.map(p => p.confidence_after)
	];

	// Calculate SVG path
	$: pathData = (() => {
		if (confidencePoints.length < 2) return '';

		const padding = 2;
		const innerWidth = width - padding * 2;
		const innerHeight = height - padding * 2;

		const points = confidencePoints.map((conf, i) => {
			const x = padding + (i / (confidencePoints.length - 1)) * innerWidth;
			const y = padding + (1 - conf) * innerHeight; // Invert Y (SVG 0 is top)
			return `${x},${y}`;
		});

		return `M ${points.join(' L ')}`;
	})();

	// Calculate fill area (for gradient)
	$: fillPath = (() => {
		if (confidencePoints.length < 2) return '';

		const padding = 2;
		const innerWidth = width - padding * 2;
		const innerHeight = height - padding * 2;

		const points = confidencePoints.map((conf, i) => {
			const x = padding + (i / (confidencePoints.length - 1)) * innerWidth;
			const y = padding + (1 - conf) * innerHeight;
			return `${x},${y}`;
		});

		// Close the path to create fill area
		const lastX = padding + innerWidth;
		const firstX = padding;
		const bottomY = height - padding;

		return `M ${firstX},${bottomY} L ${points.join(' L ')} L ${lastX},${bottomY} Z`;
	})();

	// Calculate dot positions
	$: dots = confidencePoints.map((conf, i) => {
		const padding = 2;
		const innerWidth = width - padding * 2;
		const innerHeight = height - padding * 2;

		return {
			x: padding + (i / (confidencePoints.length - 1)) * innerWidth,
			y: padding + (1 - conf) * innerHeight,
			value: conf,
			label: i === 0 ? 'Initial' : `Pass ${i}`
		};
	});

	// Color based on final confidence
	$: finalConfidence = confidencePoints[confidencePoints.length - 1] ?? 0;
	$: strokeColor = finalConfidence >= 0.8 ? '#22c55e' : finalConfidence >= 0.6 ? '#f97316' : '#ef4444';

	// Tooltip text
	$: tooltipText = `Confiance: ${Math.round(confidencePoints[0] * 100)}% → ${Math.round(finalConfidence * 100)}%`;
</script>

<svg
	{width}
	{height}
	viewBox="0 0 {width} {height}"
	class="inline-block align-middle"
	role="img"
	aria-label={tooltipText}
	data-testid="confidence-sparkline"
>
	<title>{tooltipText}</title>

	<!-- Gradient definition -->
	<defs>
		<linearGradient id="sparkline-gradient-{$$restProps.id ?? 'default'}" x1="0" y1="0" x2="0" y2="1">
			<stop offset="0%" stop-color={strokeColor} stop-opacity="0.3" />
			<stop offset="100%" stop-color={strokeColor} stop-opacity="0" />
		</linearGradient>
	</defs>

	<!-- Fill area -->
	{#if fillPath}
		<path
			d={fillPath}
			fill="url(#sparkline-gradient-{$$restProps.id ?? 'default'})"
		/>
	{/if}

	<!-- Line -->
	{#if pathData}
		<path
			d={pathData}
			fill="none"
			stroke={strokeColor}
			stroke-width="1.5"
			stroke-linecap="round"
			stroke-linejoin="round"
		/>
	{/if}

	<!-- Dots at each point -->
	{#each dots as dot}
		<circle
			cx={dot.x}
			cy={dot.y}
			r="2"
			fill={strokeColor}
		>
			<title>{dot.label}: {Math.round(dot.value * 100)}%</title>
		</circle>
	{/each}

	<!-- Start and end value indicators -->
	{#if dots.length >= 2}
		<!-- Start dot (larger) -->
		<circle
			cx={dots[0].x}
			cy={dots[0].y}
			r="3"
			fill="white"
			stroke={strokeColor}
			stroke-width="1"
		>
			<title>Initial: {Math.round(dots[0].value * 100)}%</title>
		</circle>

		<!-- End dot (larger) -->
		<circle
			cx={dots[dots.length - 1].x}
			cy={dots[dots.length - 1].y}
			r="3"
			fill={strokeColor}
		>
			<title>Final: {Math.round(dots[dots.length - 1].value * 100)}%</title>
		</circle>
	{/if}
</svg>
