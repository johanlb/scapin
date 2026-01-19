<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Badge, Skeleton } from '$lib/components/ui';
	import {
		getValetDetails,
		type ValetDetailsResponse,
		type ValetType
	} from '$lib/api/client';
	import { haptic } from '$lib/utils/haptics';
	import ActivityTimeline from '$lib/components/valets/ActivityTimeline.svelte';
	import PerformanceChart from '$lib/components/valets/PerformanceChart.svelte';
	import ModelUsageBreakdown from '$lib/components/valets/ModelUsageBreakdown.svelte';

	let details: ValetDetailsResponse | null = $state(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activityFilter = $state<'all' | 'success' | 'error'>('all');

	const valetName = $derived($page.params.name as ValetType);

	const valetIcons: Record<string, string> = {
		trivelin: '👁️',
		sancho: '🧠',
		passepartout: '📚',
		planchet: '📋',
		figaro: '⚡',
		sganarelle: '🎓',
		frontin: '🎭'
	};

	onMount(async () => {
		await fetchDetails();
	});

	async function fetchDetails() {
		loading = true;
		error = null;

		try {
			details = await getValetDetails(valetName);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Erreur de chargement';
			console.error('[ValetDetails] Fetch error:', err);
		} finally {
			loading = false;
		}
	}

	function handleRefresh() {
		haptic('light');
		fetchDetails();
	}

	function handleBack() {
		haptic('light');
		goto('/valets');
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'running':
				return 'text-green-400';
			case 'idle':
				return 'text-[var(--color-text-tertiary)]';
			case 'paused':
				return 'text-yellow-400';
			case 'error':
				return 'text-red-400';
			default:
				return 'text-[var(--color-text-secondary)]';
		}
	}

	function getStatusBgColor(status: string): string {
		switch (status) {
			case 'running':
				return 'bg-green-500/20';
			case 'idle':
				return 'bg-[var(--glass-tint)]';
			case 'paused':
				return 'bg-yellow-500/20';
			case 'error':
				return 'bg-red-500/20';
			default:
				return 'bg-[var(--glass-tint)]';
		}
	}

	function getStatusLabel(status: string): string {
		switch (status) {
			case 'running':
				return 'Actif';
			case 'idle':
				return 'En attente';
			case 'paused':
				return 'En pause';
			case 'error':
				return 'Erreur';
			default:
				return status;
		}
	}

	function formatNumber(n: number): string {
		if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
		return n.toString();
	}
</script>

<svelte:head>
	<title>{details?.display_name ?? 'Valet'} - Scapin</title>
</svelte:head>

<div class="p-4 md:p-6 max-w-5xl mx-auto space-y-6">
	<!-- Header with back button -->
	<div class="flex items-center gap-4">
		<button
			onclick={handleBack}
			class="p-2 rounded-xl glass-subtle hover:glass transition-colors"
			aria-label="Retour"
		>
			<span class="text-lg">←</span>
		</button>

		{#if loading && !details}
			<Skeleton variant="text" class="h-8 w-48" />
		{:else if details}
			<div class="flex-1 flex items-center justify-between">
				<div class="flex items-center gap-3">
					<span class="text-3xl">{valetIcons[valetName] ?? '🤖'}</span>
					<div>
						<h1 class="text-2xl font-bold text-[var(--color-text-primary)]">
							{details.display_name}
						</h1>
						<p class="text-sm text-[var(--color-text-secondary)]">
							{details.description}
						</p>
					</div>
				</div>

				<div class="flex items-center gap-3">
					<span
						class="px-3 py-1 text-sm rounded-full {getStatusBgColor(details.status)} {getStatusColor(details.status)}"
					>
						{getStatusLabel(details.status)}
					</span>
					<button
						onclick={handleRefresh}
						class="p-2 rounded-xl glass-subtle hover:glass transition-colors"
						disabled={loading}
						aria-label="Actualiser"
					>
						<span class={loading ? 'animate-spin' : ''}>🔄</span>
					</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- Error State -->
	{#if error}
		<Card class="p-4 border-red-500/30 bg-red-500/10">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<span class="text-2xl">⚠️</span>
					<div>
						<p class="font-medium text-red-400">Erreur de chargement</p>
						<p class="text-sm text-red-400/70">{error}</p>
					</div>
				</div>
				<button onclick={handleRefresh} class="text-sm text-[var(--color-accent)] hover:underline">
					Réessayer
				</button>
			</div>
		</Card>
	{/if}

	{#if loading && !details}
		<!-- Loading skeleton -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			{#each Array(4) as _}
				<Skeleton variant="rectangular" class="h-24 rounded-xl" />
			{/each}
		</div>
		<Skeleton variant="rectangular" class="h-64 rounded-xl" />
	{:else if details}
		<!-- Key Metrics -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<Card class="p-4 text-center">
				<p class="text-3xl font-bold text-[var(--color-text-primary)]">
					{formatNumber(details.tasks_completed_today)}
				</p>
				<p class="text-sm text-[var(--color-text-tertiary)]">Tâches aujourd'hui</p>
			</Card>

			<Card class="p-4 text-center">
				<p
					class="text-3xl font-bold {details.error_count_today > 0 ? 'text-red-400' : 'text-[var(--color-text-primary)]'}"
				>
					{details.error_count_today}
				</p>
				<p class="text-sm text-[var(--color-text-tertiary)]">Erreurs</p>
			</Card>

			<Card class="p-4 text-center">
				<p class="text-3xl font-bold text-[var(--color-text-primary)]">
					{details.avg_duration_ms_today > 0 ? `${details.avg_duration_ms_today}ms` : '-'}
				</p>
				<p class="text-sm text-[var(--color-text-tertiary)]">Temps moyen</p>
			</Card>

			<Card class="p-4 text-center">
				<p class="text-3xl font-bold text-[var(--color-text-primary)]">
					{formatNumber(details.tokens_used_today)}
				</p>
				<p class="text-sm text-[var(--color-text-tertiary)]">Tokens</p>
			</Card>
		</div>

		<!-- Current Task -->
		{#if details.current_task}
			<Card class="p-4">
				<div class="flex items-center gap-2 mb-2">
					<span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
					<span class="text-sm font-medium text-[var(--color-text-secondary)]">Tâche en cours</span>
				</div>
				<p class="text-[var(--color-text-primary)]">{details.current_task}</p>
			</Card>
		{/if}

		<!-- Performance & Model Usage -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
			<!-- Performance Charts -->
			<div class="lg:col-span-2 space-y-4">
				<Card class="p-4">
					<h2 class="font-semibold text-[var(--color-text-primary)] mb-4">Performance (7 jours)</h2>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
						<PerformanceChart data={details.performance_7d} metric="tasks" />
						<PerformanceChart data={details.performance_7d} metric="errors" />
						<PerformanceChart data={details.performance_7d} metric="duration" />
					</div>
				</Card>
			</div>

			<!-- Model Usage (Sancho only) -->
			{#if details.model_usage}
				<div>
					<Card class="p-4">
						<h2 class="font-semibold text-[var(--color-text-primary)] mb-4">Modèles utilisés</h2>
						<ModelUsageBreakdown stats={details.model_usage} />
					</Card>
				</div>
			{:else}
				<div>
					<Card class="p-4">
						<h2 class="font-semibold text-[var(--color-text-primary)] mb-4">Détails</h2>
						<div class="space-y-2">
							{#each Object.entries(details.details) as [key, value]}
								<div class="flex justify-between text-sm">
									<span class="text-[var(--color-text-secondary)]">{key}</span>
									<span class="text-[var(--color-text-primary)] font-mono">
										{typeof value === 'number' ? formatNumber(value) : String(value)}
									</span>
								</div>
							{/each}
						</div>
					</Card>
				</div>
			{/if}
		</div>

		<!-- Activities -->
		<Card class="p-4">
			<div class="flex items-center justify-between mb-4">
				<h2 class="font-semibold text-[var(--color-text-primary)]">Activités récentes</h2>

				<!-- Filter -->
				<div class="flex gap-1">
					{#each ['all', 'success', 'error'] as filter}
						<button
							onclick={() => {
								haptic('light');
								activityFilter = filter as 'all' | 'success' | 'error';
							}}
							class="px-3 py-1.5 text-sm rounded-lg transition-colors
								{activityFilter === filter
								? 'glass text-[var(--color-accent)]'
								: 'glass-subtle text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}"
						>
							{filter === 'all' ? 'Tous' : filter === 'success' ? 'Succès' : 'Erreurs'}
						</button>
					{/each}
				</div>
			</div>

			<ActivityTimeline activities={details.activities} filter={activityFilter} maxItems={50} />
		</Card>
	{/if}
</div>
