<script lang="ts">
	/**
	 * Simple SVG Line Chart Component
	 * Renders trend data as a multi-line chart
	 */
	import type { SourceTrend } from '$lib/api/client';

	interface Props {
		trends: SourceTrend[];
		height?: number;
		showLegend?: boolean;
		showTooltip?: boolean;
	}

	let { trends, height = 200, showLegend = true, showTooltip = true }: Props = $props();

	// Chart dimensions
	const padding = { top: 20, right: 20, bottom: 30, left: 40 };

	// Maximum data points before downsampling (for performance)
	const MAX_DATA_POINTS = 100;

	/**
	 * Downsample data points for performance
	 * Uses LTTB (Largest Triangle Three Buckets) simplification
	 */
	function downsampleData<T extends { value: number }>(data: T[], targetPoints: number): T[] {
		if (data.length <= targetPoints) return data;

		const sampled: T[] = [];
		const bucketSize = (data.length - 2) / (targetPoints - 2);

		// Always keep first point
		sampled.push(data[0]);

		for (let i = 0; i < targetPoints - 2; i++) {
			const bucketStart = Math.floor((i + 0) * bucketSize) + 1;
			const bucketEnd = Math.floor((i + 1) * bucketSize) + 1;

			// Find point with largest triangle area in bucket
			let maxArea = -1;
			let maxIndex = bucketStart;

			const prevPoint = sampled[sampled.length - 1];

			for (let j = bucketStart; j < bucketEnd && j < data.length - 1; j++) {
				// Calculate triangle area
				const area = Math.abs(
					(prevPoint.value - data[j].value) * (j - sampled.length) -
					(prevPoint.value - data[data.length - 1].value) * (j - sampled.length)
				);
				if (area > maxArea) {
					maxArea = area;
					maxIndex = j;
				}
			}

			sampled.push(data[maxIndex]);
		}

		// Always keep last point
		sampled.push(data[data.length - 1]);

		return sampled;
	}

	// Calculate chart bounds from data (with downsampling)
	const chartData = $derived.by(() => {
		if (!trends.length || !trends[0].data.length) {
			return {
				maxValue: 100,
				minValue: 0,
				dates: [] as string[],
				width: 400,
				sampledTrends: [] as typeof trends
			};
		}

		// Downsample trends if needed for performance
		const sampledTrends = trends.map(trend => ({
			...trend,
			data: downsampleData(trend.data, MAX_DATA_POINTS)
		}));

		const allValues = sampledTrends.flatMap(t => t.data.map(d => d.value));
		const maxValue = Math.max(...allValues, 10); // Minimum 10 for scale
		const minValue = Math.min(...allValues, 0);
		const dates = sampledTrends[0].data.map(d => d.date);

		return {
			maxValue,
			minValue,
			dates,
			width: Math.max(400, dates.length * 30),
			sampledTrends
		};
	});

	// Calculate point positions for a trend line (using sampled data)
	function getPoints(trend: (typeof chartData.sampledTrends)[number], width: number): string {
		const { maxValue, dates } = chartData;
		if (!dates.length) return '';

		const chartWidth = width - padding.left - padding.right;
		const chartHeight = height - padding.top - padding.bottom;

		return trend.data.map((point, i) => {
			const x = padding.left + (i / (dates.length - 1 || 1)) * chartWidth;
			const y = padding.top + chartHeight - (point.value / maxValue) * chartHeight;
			return `${x},${y}`;
		}).join(' ');
	}

	// Format date for display
	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
	}

	// Format value for y-axis
	function formatValue(value: number): string {
		if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
		return String(Math.round(value));
	}

	// Get Y-axis ticks
	const yTicks = $derived.by(() => {
		const { maxValue } = chartData;
		const step = Math.ceil(maxValue / 4);
		return [0, step, step * 2, step * 3, maxValue].filter(v => v <= maxValue);
	});

	// Tooltip state
	let hoveredPoint = $state<{ x: number; y: number; value: number; label: string; date: string } | null>(null);
	let containerRef: HTMLDivElement | null = $state(null);
</script>

<div class="line-chart" bind:this={containerRef}>
	{#if showLegend}
		<div class="flex flex-wrap gap-4 mb-4 px-2">
			{#each trends as trend}
				<div class="flex items-center gap-2">
					<span
						class="w-3 h-3 rounded-full"
						style="background-color: {trend.color}"
					></span>
					<span class="text-sm text-[var(--color-text-secondary)]">
						{trend.label}
						<span class="text-[var(--color-text-tertiary)]">({trend.total})</span>
					</span>
				</div>
			{/each}
		</div>
	{/if}

	<div class="relative overflow-x-auto">
		<svg
			width="100%"
			height={height}
			viewBox="0 0 {chartData.width} {height}"
			preserveAspectRatio="xMidYMid meet"
			class="overflow-visible"
		>
			<!-- Y-axis grid lines -->
			{#each yTicks as tick}
				{@const y = padding.top + (height - padding.top - padding.bottom) * (1 - tick / chartData.maxValue)}
				<line
					x1={padding.left}
					y1={y}
					x2={chartData.width - padding.right}
					y2={y}
					stroke="var(--color-border)"
					stroke-dasharray="2,2"
					opacity="0.5"
				/>
				<text
					x={padding.left - 8}
					y={y + 4}
					text-anchor="end"
					class="text-xs fill-[var(--color-text-tertiary)]"
				>
					{formatValue(tick)}
				</text>
			{/each}

			<!-- X-axis date labels (show a subset) -->
			{#each chartData.dates as date, i}
				{#if i % Math.ceil(chartData.dates.length / 7) === 0 || i === chartData.dates.length - 1}
					{@const x = padding.left + (i / (chartData.dates.length - 1 || 1)) * (chartData.width - padding.left - padding.right)}
					<text
						x={x}
						y={height - 8}
						text-anchor="middle"
						class="text-xs fill-[var(--color-text-tertiary)]"
					>
						{formatDate(date)}
					</text>
				{/if}
			{/each}

			<!-- Trend lines (using sampled data for performance) -->
			{#each chartData.sampledTrends as trend}
				<polyline
					points={getPoints(trend, chartData.width)}
					fill="none"
					stroke={trend.color}
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="transition-opacity"
					opacity={hoveredPoint && hoveredPoint.label !== trend.label ? 0.3 : 1}
				/>

				<!-- Area fill under line -->
				<polygon
					points="{padding.left},{height - padding.bottom} {getPoints(trend, chartData.width)} {chartData.width - padding.right},{height - padding.bottom}"
					fill={trend.color}
					opacity="0.1"
				/>

				<!-- Data points -->
				{#each trend.data as point, i}
					{@const x = padding.left + (i / (chartData.dates.length - 1 || 1)) * (chartData.width - padding.left - padding.right)}
					{@const y = padding.top + (height - padding.top - padding.bottom) * (1 - point.value / chartData.maxValue)}
					<circle
						cx={x}
						cy={y}
						r="4"
						fill={trend.color}
						role="img"
						aria-label="{trend.label}: {point.value} le {point.date}"
						class="cursor-pointer transition-all hover:r-6"
						onmouseenter={() => {
							if (showTooltip) {
								hoveredPoint = { x, y, value: point.value, label: trend.label, date: point.date };
							}
						}}
						onmouseleave={() => { hoveredPoint = null; }}
					/>
				{/each}
			{/each}

			<!-- Tooltip -->
			{#if hoveredPoint}
				<g transform="translate({hoveredPoint.x}, {hoveredPoint.y - 40})">
					<rect
						x="-40"
						y="0"
						width="80"
						height="32"
						rx="4"
						class="fill-[var(--color-bg-primary)]"
						stroke="var(--color-border)"
					/>
					<text
						x="0"
						y="14"
						text-anchor="middle"
						class="text-xs font-medium fill-[var(--color-text-primary)]"
					>
						{hoveredPoint.value}
					</text>
					<text
						x="0"
						y="26"
						text-anchor="middle"
						class="text-xs fill-[var(--color-text-tertiary)]"
					>
						{formatDate(hoveredPoint.date)}
					</text>
				</g>
			{/if}
		</svg>
	</div>
</div>

<style>
	.line-chart {
		width: 100%;
	}

	circle:hover {
		r: 6;
	}
</style>
