<script lang="ts">
	import type { CostMetricsResponse, ModelCosts } from '$lib/api/client';

	interface Props {
		costs: CostMetricsResponse | null;
	}

	let { costs }: Props = $props();

	// Model colors
	const modelColors = {
		haiku: '#22c55e',
		sonnet: '#3b82f6',
		opus: '#a855f7'
	};

	// Get cost breakdown for visualization
	const breakdown = $derived(() => {
		if (!costs) return [];

		const sanchoCosts = costs.costs_by_valet['sancho'];
		if (!sanchoCosts || sanchoCosts.total_cost_usd === 0) {
			return [
				{ model: 'Haiku', cost: 0, pct: 33, color: modelColors.haiku },
				{ model: 'Sonnet', cost: 0, pct: 34, color: modelColors.sonnet },
				{ model: 'Opus', cost: 0, pct: 33, color: modelColors.opus }
			];
		}

		const total = sanchoCosts.total_cost_usd;
		return [
			{
				model: 'Haiku',
				cost: sanchoCosts.haiku_cost_usd,
				pct: Math.round((sanchoCosts.haiku_cost_usd / total) * 100),
				color: modelColors.haiku
			},
			{
				model: 'Sonnet',
				cost: sanchoCosts.sonnet_cost_usd,
				pct: Math.round((sanchoCosts.sonnet_cost_usd / total) * 100),
				color: modelColors.sonnet
			},
			{
				model: 'Opus',
				cost: sanchoCosts.opus_cost_usd,
				pct: Math.round((sanchoCosts.opus_cost_usd / total) * 100),
				color: modelColors.opus
			}
		];
	});

	function formatCost(cost: number): string {
		if (cost === 0) return '$0.00';
		if (cost < 0.01) return '<$0.01';
		return `$${cost.toFixed(2)}`;
	}
</script>

<div class="cost-breakdown">
	<div class="section-header">
		<span class="section-title">Répartition par modèle</span>
		{#if costs}
			<span class="section-period">{costs.period}</span>
		{/if}
	</div>

	<!-- Stacked bar -->
	<div class="stacked-bar">
		{#each breakdown() as item}
			{#if item.pct > 0}
				<div
					class="bar-segment"
					style="width: {item.pct}%; background: {item.color}"
					title="{item.model}: {formatCost(item.cost)}"
				></div>
			{/if}
		{/each}
	</div>

	<!-- Legend -->
	<div class="cost-legend">
		{#each breakdown() as item}
			<div class="legend-row">
				<div class="legend-left">
					<span class="legend-dot" style="background: {item.color}"></span>
					<span class="legend-model">{item.model}</span>
				</div>
				<div class="legend-right">
					<span class="legend-pct">{item.pct}%</span>
					<span class="legend-cost">{formatCost(item.cost)}</span>
				</div>
			</div>
		{/each}
	</div>

	<!-- Total and projections -->
	{#if costs}
		<div class="cost-metrics">
			<div class="metric-row">
				<span class="metric-label">Total ({costs.period})</span>
				<span class="metric-value">{formatCost(costs.total_cost_usd)}</span>
			</div>
			<div class="metric-row">
				<span class="metric-label">Projection mensuelle</span>
				<span class="metric-value projected">{formatCost(costs.projected_monthly_usd)}</span>
			</div>
			<div class="metric-row">
				<span class="metric-label">Coût/email moyen</span>
				<span class="metric-value">{formatCost(costs.cost_per_email_avg_usd)}</span>
			</div>
			{#if costs.confidence_per_dollar > 0}
				<div class="metric-row">
					<span class="metric-label">Efficacité (conf./$)</span>
					<span class="metric-value">{costs.confidence_per_dollar.toFixed(1)} pts/$</span>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.cost-breakdown {
		background: var(--glass-bg);
		border: 1px solid var(--glass-border-subtle);
		border-radius: 0.75rem;
		padding: 1rem;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.section-title {
		font-weight: 600;
		color: var(--color-text-primary);
	}

	.section-period {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
		padding: 0.125rem 0.5rem;
		background: var(--glass-tint);
		border-radius: 0.25rem;
	}

	.stacked-bar {
		display: flex;
		height: 1.5rem;
		border-radius: 0.375rem;
		overflow: hidden;
		margin-bottom: 1rem;
		background: var(--glass-tint);
	}

	.bar-segment {
		transition: width 0.3s ease;
	}

	.cost-legend {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.legend-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.legend-left {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.legend-dot {
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
	}

	.legend-model {
		font-size: 0.875rem;
		color: var(--color-text-primary);
	}

	.legend-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.legend-pct {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		font-family: monospace;
		min-width: 2.5rem;
		text-align: right;
	}

	.legend-cost {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
		font-family: monospace;
		min-width: 3.5rem;
		text-align: right;
	}

	.cost-metrics {
		border-top: 1px solid var(--glass-border-subtle);
		padding-top: 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.metric-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.metric-label {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	.metric-value {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text-primary);
		font-family: monospace;
	}

	.metric-value.projected {
		color: var(--color-accent);
	}
</style>
