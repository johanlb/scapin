<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Badge, Skeleton } from '$lib/components/ui';
	import { valetsStore } from '$lib/stores/valets.svelte';
	import { haptic } from '$lib/utils/haptics';

	let refreshInterval: number | null = null;

	onMount(() => {
		valetsStore.initialize();

		// Auto-refresh every 30 seconds
		refreshInterval = window.setInterval(() => {
			valetsStore.refresh();
		}, 30000);

		return () => {
			if (refreshInterval) {
				window.clearInterval(refreshInterval);
			}
		};
	});

	function handleRefresh() {
		haptic('light');
		valetsStore.refresh();
	}

	function handlePeriodChange(period: 'today' | '7d' | '30d') {
		haptic('light');
		valetsStore.fetchMetrics(period);
	}
</script>

<svelte:head>
	<title>Valets - Scapin</title>
</svelte:head>

<div class="p-4 md:p-6 max-w-6xl mx-auto space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-[var(--color-text-primary)]">Équipe des Valets</h1>
			<p class="text-sm text-[var(--color-text-secondary)] mt-1">
				Surveillance des agents cognitifs
			</p>
		</div>

		<div class="flex items-center gap-3">
			{#if valetsStore.lastUpdated}
				<span class="text-xs text-[var(--color-text-tertiary)]">
					Mis à jour {valetsStore.formatRelativeTime(valetsStore.lastUpdated.toISOString())}
				</span>
			{/if}
			<button
				onclick={handleRefresh}
				class="p-2 rounded-xl glass-subtle hover:glass transition-colors"
				disabled={valetsStore.loading}
				aria-label="Actualiser"
			>
				<span class={valetsStore.loading ? 'animate-spin' : ''}>🔄</span>
			</button>
		</div>
	</div>

	<!-- System Status Banner -->
	{#if valetsStore.loading && !valetsStore.dashboard}
		<Skeleton variant="rectangular" class="h-20 rounded-xl" />
	{:else if valetsStore.dashboard}
		<Card class="p-4">
			<div class="flex items-center justify-between flex-wrap gap-4">
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-2">
						<span class={`w-3 h-3 rounded-full ${
							valetsStore.systemStatus === 'healthy' ? 'bg-green-500' :
							valetsStore.systemStatus === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
						} ${valetsStore.systemStatus === 'healthy' ? 'animate-pulse' : ''}`}></span>
						<span class={`font-semibold ${valetsStore.getSystemStatusColor(valetsStore.systemStatus)}`}>
							{valetsStore.systemStatus === 'healthy' ? 'Système opérationnel' :
							 valetsStore.systemStatus === 'degraded' ? 'Système dégradé' : 'Système en erreur'}
						</span>
					</div>
				</div>

				<div class="flex items-center gap-6 text-sm">
					<div class="text-center">
						<p class="text-2xl font-bold text-[var(--color-text-primary)]">{valetsStore.activeWorkers}</p>
						<p class="text-xs text-[var(--color-text-tertiary)]">Actifs</p>
					</div>
					<div class="text-center">
						<p class="text-2xl font-bold text-[var(--color-text-primary)]">{valetsStore.totalTasksToday}</p>
						<p class="text-xs text-[var(--color-text-tertiary)]">Tâches aujourd'hui</p>
					</div>
					<div class="text-center">
						<p class="text-2xl font-bold text-[var(--color-text-primary)]">{Math.round(valetsStore.avgConfidence * 100)}%</p>
						<p class="text-xs text-[var(--color-text-tertiary)]">Confiance moy.</p>
					</div>
				</div>
			</div>
		</Card>
	{/if}

	<!-- Error State -->
	{#if valetsStore.error}
		<Card class="p-4 border-red-500/30 bg-red-500/10">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<span class="text-2xl">⚠️</span>
					<div>
						<p class="font-medium text-red-400">Erreur de chargement</p>
						<p class="text-sm text-red-400/70">{valetsStore.error}</p>
					</div>
				</div>
				<button
					onclick={handleRefresh}
					class="text-sm text-[var(--color-accent)] hover:underline"
				>
					Réessayer
				</button>
			</div>
		</Card>
	{/if}

	<!-- Valets Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
		{#if valetsStore.loading && !valetsStore.dashboard}
			{#each Array(7) as _}
				<Card class="p-4">
					<Skeleton variant="rectangular" class="h-32 rounded-lg" />
				</Card>
			{/each}
		{:else}
			{#each valetsStore.valets as valet (valet.name)}
				<Card class="p-4 hover:shadow-lg transition-shadow">
					<!-- Header -->
					<div class="flex items-start justify-between mb-3">
						<div class="flex items-center gap-2">
							<span class="text-2xl">{valetsStore.getValetIcon(valet.name)}</span>
							<div>
								<h3 class="font-semibold text-[var(--color-text-primary)]">{valet.display_name}</h3>
								<p class="text-xs text-[var(--color-text-tertiary)]">{valet.description}</p>
							</div>
						</div>
						<span class={`px-2 py-0.5 text-xs rounded-full ${valetsStore.getStatusBgColor(valet.status)} ${valetsStore.getStatusColor(valet.status)}`}>
							{valetsStore.getStatusLabel(valet.status)}
						</span>
					</div>

					<!-- Current Task -->
					{#if valet.current_task}
						<div class="mb-3 p-2 rounded-lg glass-subtle">
							<p class="text-xs text-[var(--color-text-tertiary)] mb-1">Tâche en cours</p>
							<p class="text-sm text-[var(--color-text-primary)] line-clamp-2">{valet.current_task}</p>
						</div>
					{/if}

					<!-- Stats -->
					<div class="grid grid-cols-2 gap-2 text-center">
						<div class="p-2 rounded-lg glass-subtle">
							<p class="text-lg font-semibold text-[var(--color-text-primary)]">{valet.tasks_completed_today}</p>
							<p class="text-xs text-[var(--color-text-tertiary)]">Tâches</p>
						</div>
						<div class="p-2 rounded-lg glass-subtle">
							<p class="text-lg font-semibold {valet.error_count_today > 0 ? 'text-red-400' : 'text-[var(--color-text-primary)]'}">
								{valet.error_count_today}
							</p>
							<p class="text-xs text-[var(--color-text-tertiary)]">Erreurs</p>
						</div>
					</div>

					<!-- Last Activity -->
					{#if valet.last_activity}
						<p class="mt-3 text-xs text-[var(--color-text-tertiary)]">
							Dernière activité : {valetsStore.formatRelativeTime(valet.last_activity)}
						</p>
					{/if}
				</Card>
			{/each}
		{/if}
	</div>

	<!-- Metrics Section -->
	{#if valetsStore.metrics}
		<Card class="p-4">
			<div class="flex items-center justify-between mb-4">
				<h2 class="font-semibold text-[var(--color-text-primary)]">Métriques détaillées</h2>

				<!-- Period Selector -->
				<div class="flex gap-1">
					{#each ['today', '7d', '30d'] as period}
						<button
							onclick={() => handlePeriodChange(period as 'today' | '7d' | '30d')}
							class="px-3 py-1.5 text-sm rounded-lg transition-colors
								{valetsStore.selectedPeriod === period
									? 'glass text-[var(--color-accent)]'
									: 'glass-subtle text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}"
						>
							{period === 'today' ? "Aujourd'hui" : period}
						</button>
					{/each}
				</div>
			</div>

			<!-- Metrics Table -->
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead>
						<tr class="text-left text-[var(--color-text-tertiary)] border-b border-[var(--glass-border-subtle)]">
							<th class="py-2 pr-4">Valet</th>
							<th class="py-2 pr-4 text-right">Complétées</th>
							<th class="py-2 pr-4 text-right">Échouées</th>
							<th class="py-2 pr-4 text-right">Temps moy.</th>
							<th class="py-2 pr-4 text-right">P95</th>
							<th class="py-2 pr-4 text-right">Succès</th>
							<th class="py-2 pr-4 text-right">Tokens</th>
						</tr>
					</thead>
					<tbody>
						{#each valetsStore.metrics.metrics as metric (metric.name)}
							<tr class="border-b border-[var(--glass-border-subtle)] last:border-0">
								<td class="py-3 pr-4">
									<div class="flex items-center gap-2">
										<span>{valetsStore.getValetIcon(metric.name)}</span>
										<span class="capitalize">{metric.name}</span>
									</div>
								</td>
								<td class="py-3 pr-4 text-right font-medium">{metric.tasks_completed}</td>
								<td class="py-3 pr-4 text-right {metric.tasks_failed > 0 ? 'text-red-400' : ''}">{metric.tasks_failed}</td>
								<td class="py-3 pr-4 text-right">{metric.avg_duration_ms}ms</td>
								<td class="py-3 pr-4 text-right">{metric.p95_duration_ms}ms</td>
								<td class="py-3 pr-4 text-right">
									<span class={metric.success_rate >= 0.95 ? 'text-green-400' : metric.success_rate >= 0.8 ? 'text-yellow-400' : 'text-red-400'}>
										{Math.round(metric.success_rate * 100)}%
									</span>
								</td>
								<td class="py-3 pr-4 text-right text-[var(--color-text-tertiary)]">
									{metric.tokens_used > 0 ? metric.tokens_used.toLocaleString() : '-'}
								</td>
							</tr>
						{/each}
					</tbody>
					<tfoot>
						<tr class="font-semibold text-[var(--color-text-primary)]">
							<td class="py-3 pr-4">Total</td>
							<td class="py-3 pr-4 text-right">{valetsStore.metrics.total_tasks}</td>
							<td class="py-3 pr-4 text-right">-</td>
							<td class="py-3 pr-4 text-right">-</td>
							<td class="py-3 pr-4 text-right">-</td>
							<td class="py-3 pr-4 text-right">-</td>
							<td class="py-3 pr-4 text-right">{valetsStore.metrics.total_tokens.toLocaleString()}</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</Card>
	{/if}
</div>
