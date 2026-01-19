<script lang="ts">
	import type { DailyMetrics } from '$lib/api/client';

	interface Props {
		data: DailyMetrics[];
		metric?: 'tasks' | 'errors' | 'duration';
	}

	let { data, metric = 'tasks' }: Props = $props();

	// Chart dimensions
	const width = 300;
	const height = 120;
	const padding = { top: 10, right: 10, bottom: 25, left: 35 };
	const chartWidth = width - padding.left - padding.right;
	const chartHeight = height - padding.top - padding.bottom;

	// Compute chart data
	const chartData = $derived(() => {
		if (!data || data.length === 0) return { points: '', maxY: 0, values: [] };

		const values = data.map((d) => {
			switch (metric) {
				case 'tasks':
					return d.tasks_completed;
				case 'errors':
					return d.tasks_failed;
				case 'duration':
					return d.avg_duration_ms;
				default:
					return d.tasks_completed;
			}
		});

		const maxY = Math.max(...values, 1);
		const stepX = chartWidth / Math.max(values.length - 1, 1);

		const points = values
			.map((v, i) => {
				const x = padding.left + i * stepX;
				const y = padding.top + chartHeight - (v / maxY) * chartHeight;
				return `${x},${y}`;
			})
			.join(' ');

		return { points, maxY, values };
	});

	// Format day labels
	function formatDay(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('fr-FR', { weekday: 'short' }).slice(0, 2);
	}

	// Y-axis labels
	const yLabels = $derived(() => {
		const { maxY } = chartData();
		return [0, Math.round(maxY / 2), Math.round(maxY)];
	});

	const metricLabel = $derived(() => {
		switch (metric) {
			case 'tasks':
				return 'Tâches';
			case 'errors':
				return 'Erreurs';
			case 'duration':
				return 'Durée (ms)';
			default:
				return '';
		}
	});

	const lineColor = $derived(() => {
		switch (metric) {
			case 'tasks':
				return 'rgb(59, 130, 246)'; // blue
			case 'errors':
				return 'rgb(239, 68, 68)'; // red
			case 'duration':
				return 'rgb(168, 85, 247)'; // purple
			default:
				return 'rgb(59, 130, 246)';
		}
	});
</script>

<div class="performance-chart">
	<div class="chart-header">
		<span class="chart-title">{metricLabel()}</span>
	</div>

	<svg viewBox="0 0 {width} {height}" class="chart-svg">
		<!-- Grid lines -->
		{#each yLabels() as label, i}
			{@const y = padding.top + chartHeight - (label / chartData().maxY) * chartHeight}
			<line
				x1={padding.left}
				y1={y}
				x2={width - padding.right}
				y2={y}
				stroke="var(--glass-border-subtle)"
				stroke-dasharray="2,2"
			/>
			<text x={padding.left - 5} y={y + 3} class="axis-label" text-anchor="end">
				{label}
			</text>
		{/each}

		<!-- X-axis labels -->
		{#each data as d, i}
			{@const x = padding.left + (i * chartWidth) / Math.max(data.length - 1, 1)}
			<text x={x} y={height - 5} class="axis-label" text-anchor="middle">
				{formatDay(d.date)}
			</text>
		{/each}

		<!-- Data line -->
		{#if chartData().points}
			<polyline
				points={chartData().points}
				fill="none"
				stroke={lineColor()}
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>

			<!-- Data points -->
			{#each chartData().values as v, i}
				{@const x = padding.left + (i * chartWidth) / Math.max(data.length - 1, 1)}
				{@const y = padding.top + chartHeight - (v / chartData().maxY) * chartHeight}
				<circle cx={x} cy={y} r="3" fill={lineColor()} />
			{/each}
		{/if}
	</svg>
</div>

<style>
	.performance-chart {
		background: var(--glass-tint);
		border-radius: 0.5rem;
		padding: 0.75rem;
	}

	.chart-header {
		margin-bottom: 0.5rem;
	}

	.chart-title {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		font-weight: 500;
	}

	.chart-svg {
		width: 100%;
		height: auto;
	}

	.axis-label {
		font-size: 9px;
		fill: var(--color-text-tertiary);
	}
</style>
