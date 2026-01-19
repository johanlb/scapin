<script lang="ts">
	import type { ModelUsageStats } from '$lib/api/client';

	interface Props {
		stats: ModelUsageStats | null;
	}

	let { stats }: Props = $props();

	// Calculate percentages
	const breakdown = $derived(() => {
		if (!stats || stats.total_requests === 0) {
			return [
				{ model: 'Haiku', pct: 33, color: '#22c55e', requests: 0, cost: 0 },
				{ model: 'Sonnet', pct: 34, color: '#3b82f6', requests: 0, cost: 0 },
				{ model: 'Opus', pct: 33, color: '#a855f7', requests: 0, cost: 0 }
			];
		}

		const total = stats.total_requests;
		return [
			{
				model: 'Haiku',
				pct: Math.round((stats.haiku_requests / total) * 100),
				color: '#22c55e',
				requests: stats.haiku_requests,
				cost: stats.haiku_cost_usd
			},
			{
				model: 'Sonnet',
				pct: Math.round((stats.sonnet_requests / total) * 100),
				color: '#3b82f6',
				requests: stats.sonnet_requests,
				cost: stats.sonnet_cost_usd
			},
			{
				model: 'Opus',
				pct: Math.round((stats.opus_requests / total) * 100),
				color: '#a855f7',
				requests: stats.opus_requests,
				cost: stats.opus_cost_usd
			}
		];
	});

	// SVG pie chart calculations
	const pieData = $derived(() => {
		const items = breakdown();
		let currentAngle = 0;
		return items.map((item) => {
			const startAngle = currentAngle;
			const angle = (item.pct / 100) * 360;
			currentAngle += angle;

			const startRad = ((startAngle - 90) * Math.PI) / 180;
			const endRad = ((startAngle + angle - 90) * Math.PI) / 180;

			const x1 = 50 + 40 * Math.cos(startRad);
			const y1 = 50 + 40 * Math.sin(startRad);
			const x2 = 50 + 40 * Math.cos(endRad);
			const y2 = 50 + 40 * Math.sin(endRad);

			const largeArc = angle > 180 ? 1 : 0;

			return {
				...item,
				path:
					item.pct === 100
						? `M 50 10 A 40 40 0 1 1 49.99 10`
						: `M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`
			};
		});
	});

	function formatCost(cost: number): string {
		if (cost < 0.01) return '<$0.01';
		return `$${cost.toFixed(2)}`;
	}
</script>

<div class="model-usage">
	<div class="chart-container">
		<svg viewBox="0 0 100 100" class="pie-chart">
			{#each pieData() as slice}
				{#if slice.pct > 0}
					<path d={slice.path} fill={slice.color} opacity="0.8" />
				{/if}
			{/each}
			<!-- Center hole for donut effect -->
			<circle cx="50" cy="50" r="25" fill="var(--glass-bg)" />
			<!-- Center text -->
			<text x="50" y="48" class="center-text" text-anchor="middle">
				{stats?.total_requests ?? 0}
			</text>
			<text x="50" y="58" class="center-label" text-anchor="middle">requêtes</text>
		</svg>
	</div>

	<div class="legend">
		{#each breakdown() as item}
			<div class="legend-item">
				<span class="legend-dot" style="background: {item.color}"></span>
				<span class="legend-model">{item.model}</span>
				<span class="legend-pct">{item.pct}%</span>
				<span class="legend-cost">{formatCost(item.cost)}</span>
			</div>
		{/each}
	</div>

	{#if stats}
		<div class="total-cost">
			<span class="total-label">Coût total</span>
			<span class="total-value">${stats.total_cost_usd.toFixed(2)}</span>
		</div>
	{/if}
</div>

<style>
	.model-usage {
		background: var(--glass-tint);
		border-radius: 0.5rem;
		padding: 1rem;
	}

	.chart-container {
		display: flex;
		justify-content: center;
		margin-bottom: 1rem;
	}

	.pie-chart {
		width: 120px;
		height: 120px;
	}

	.center-text {
		font-size: 14px;
		font-weight: 600;
		fill: var(--color-text-primary);
	}

	.center-label {
		font-size: 8px;
		fill: var(--color-text-tertiary);
	}

	.legend {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.75rem;
	}

	.legend-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.legend-model {
		color: var(--color-text-primary);
		flex: 1;
	}

	.legend-pct {
		color: var(--color-text-secondary);
		font-family: monospace;
		min-width: 2.5rem;
		text-align: right;
	}

	.legend-cost {
		color: var(--color-text-tertiary);
		font-family: monospace;
		min-width: 3.5rem;
		text-align: right;
	}

	.total-cost {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--glass-border-subtle);
	}

	.total-label {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.total-value {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--color-text-primary);
	}
</style>
