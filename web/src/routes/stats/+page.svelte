<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Skeleton } from '$lib/components/ui';
	import { getStatsOverview, getStatsBySource } from '$lib/api/client';
	import type { StatsOverview, StatsBySource } from '$lib/api/client';

	let loading = $state(true);
	let error = $state<string | null>(null);
	let overview = $state<StatsOverview | null>(null);
	let bySource = $state<StatsBySource | null>(null);

	// Derived stats for display
	let uptimeDisplay = $derived(() => {
		if (!overview) return '—';
		const hours = Math.floor(overview.uptime_seconds / 3600);
		const minutes = Math.floor((overview.uptime_seconds % 3600) / 60);
		if (hours > 0) return `${hours}h ${minutes}m`;
		return `${minutes}m`;
	});

	let lastActivityDisplay = $derived(() => {
		if (!overview?.last_activity) return 'Aucune';
		const date = new Date(overview.last_activity);
		return date.toLocaleString('fr-FR', {
			day: 'numeric',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	});

	async function fetchStats() {
		loading = true;
		error = null;
		try {
			const [overviewData, bySourceData] = await Promise.all([
				getStatsOverview(),
				getStatsBySource()
			]);
			overview = overviewData;
			bySource = bySourceData;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors du chargement des statistiques';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchStats();
	});
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			Vos Registres
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Ce que j'ai observé, Monsieur
		</p>
	</header>

	{#if error}
		<!-- Error State -->
		<Card padding="lg">
			<div class="text-center py-8">
				<span class="text-4xl mb-4 block">⚠️</span>
				<h3 class="font-semibold text-[var(--color-text-primary)] mb-2">
					Impossible de charger les statistiques
				</h3>
				<p class="text-[var(--color-text-secondary)] mb-4">{error}</p>
				<button
					class="px-4 py-2 bg-[var(--color-accent)] text-white rounded-lg hover:opacity-90 transition-opacity"
					onclick={() => fetchStats()}
				>
					Réessayer
				</button>
			</div>
		</Card>
	{:else if loading}
		<!-- Loading State -->
		<section class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
			{#each Array(6) as _}
				<Card padding="lg">
					<div class="text-center">
						<Skeleton variant="text" class="h-10 w-16 mx-auto mb-2" />
						<Skeleton variant="text" class="h-4 w-24 mx-auto" />
					</div>
				</Card>
			{/each}
		</section>
	{:else if overview}
		<!-- Overview Stats -->
		<section class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
			<Card padding="lg">
				<div class="text-center">
					<p class="text-4xl font-bold text-[var(--color-event-email)]">
						{overview.email_processed}
					</p>
					<p class="text-sm text-[var(--color-text-secondary)] mt-1">Emails traités</p>
					{#if overview.email_queued > 0}
						<p class="text-sm text-[var(--color-warning)] mt-1">
							{overview.email_queued} en attente
						</p>
					{/if}
				</div>
			</Card>
			<Card padding="lg">
				<div class="text-center">
					<p class="text-4xl font-bold text-[var(--color-event-teams)]">
						{overview.teams_messages}
					</p>
					<p class="text-sm text-[var(--color-text-secondary)] mt-1">Messages Teams</p>
					{#if overview.teams_unread > 0}
						<p class="text-sm text-[var(--color-warning)] mt-1">
							{overview.teams_unread} non lus
						</p>
					{/if}
				</div>
			</Card>
			<Card padding="lg">
				<div class="text-center">
					<p class="text-4xl font-bold text-[var(--color-event-calendar)]">
						{overview.calendar_events_today}
					</p>
					<p class="text-sm text-[var(--color-text-secondary)] mt-1">Événements aujourd'hui</p>
					<p class="text-sm text-[var(--color-text-tertiary)] mt-1">
						{overview.calendar_events_week} cette semaine
					</p>
				</div>
			</Card>
			<Card padding="lg">
				<div class="text-center">
					<p class="text-4xl font-bold text-[var(--color-event-omnifocus)]">
						{overview.notes_reviewed_today}
					</p>
					<p class="text-sm text-[var(--color-text-secondary)] mt-1">Notes révisées</p>
					{#if overview.notes_due > 0}
						<p class="text-sm text-[var(--color-warning)] mt-1">
							{overview.notes_due} à revoir
						</p>
					{/if}
				</div>
			</Card>
			<Card padding="lg">
				<div class="text-center">
					<p class="text-4xl font-bold text-[var(--color-success)]">
						{overview.total_processed}
					</p>
					<p class="text-sm text-[var(--color-text-secondary)] mt-1">Total traités</p>
					{#if overview.total_pending > 0}
						<p class="text-sm text-[var(--color-warning)] mt-1">
							{overview.total_pending} en attente
						</p>
					{/if}
				</div>
			</Card>
			<Card padding="lg">
				<div class="text-center">
					<p class="text-4xl font-bold text-[var(--color-accent)]">
						{overview.sources_active}
					</p>
					<p class="text-sm text-[var(--color-text-secondary)] mt-1">Sources actives</p>
					<p class="text-sm text-[var(--color-text-tertiary)] mt-1">
						Uptime: {uptimeDisplay()}
					</p>
				</div>
			</Card>
		</section>

		<!-- Details by Source -->
		{#if bySource}
			<section>
				<h2 class="text-xl font-semibold text-[var(--color-text-primary)] mb-4">
					Détails par source
				</h2>
				<div class="space-y-4">
					<!-- Email Stats -->
					{#if bySource.email}
						<Card padding="lg">
							<div class="flex items-start gap-3">
								<span class="text-2xl">📧</span>
								<div class="flex-1">
									<h3 class="font-semibold text-[var(--color-text-primary)]">Email</h3>
									<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-sm">
										<div>
											<span class="text-[var(--color-text-tertiary)]">Traités:</span>
											<span class="ml-1">{bySource.email.emails_processed}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Archivés:</span>
											<span class="ml-1">{bySource.email.emails_archived}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Supprimés:</span>
											<span class="ml-1">{bySource.email.emails_deleted}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Tâches:</span>
											<span class="ml-1">{bySource.email.tasks_created}</span>
										</div>
									</div>
									{#if bySource.email.average_confidence > 0}
										<p class="text-xs text-[var(--color-text-tertiary)] mt-2">
											Confiance moyenne: {Math.round(bySource.email.average_confidence * 100)}%
										</p>
									{/if}
								</div>
							</div>
						</Card>
					{/if}

					<!-- Teams Stats -->
					{#if bySource.teams}
						<Card padding="lg">
							<div class="flex items-start gap-3">
								<span class="text-2xl">💬</span>
								<div class="flex-1">
									<h3 class="font-semibold text-[var(--color-text-primary)]">Teams</h3>
									<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-sm">
										<div>
											<span class="text-[var(--color-text-tertiary)]">Chats:</span>
											<span class="ml-1">{bySource.teams.total_chats}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Non lus:</span>
											<span class="ml-1">{bySource.teams.unread_chats}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Traités:</span>
											<span class="ml-1">{bySource.teams.messages_processed}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Flagués:</span>
											<span class="ml-1">{bySource.teams.messages_flagged}</span>
										</div>
									</div>
								</div>
							</div>
						</Card>
					{/if}

					<!-- Calendar Stats -->
					{#if bySource.calendar}
						<Card padding="lg">
							<div class="flex items-start gap-3">
								<span class="text-2xl">📅</span>
								<div class="flex-1">
									<h3 class="font-semibold text-[var(--color-text-primary)]">Calendrier</h3>
									<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-sm">
										<div>
											<span class="text-[var(--color-text-tertiary)]">Aujourd'hui:</span>
											<span class="ml-1">{bySource.calendar.events_today}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Semaine:</span>
											<span class="ml-1">{bySource.calendar.events_week}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">En ligne:</span>
											<span class="ml-1">{bySource.calendar.meetings_online}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Présentiel:</span>
											<span class="ml-1">{bySource.calendar.meetings_in_person}</span>
										</div>
									</div>
								</div>
							</div>
						</Card>
					{/if}

					<!-- Queue Stats -->
					{#if bySource.queue}
						<Card padding="lg">
							<div class="flex items-start gap-3">
								<span class="text-2xl">📥</span>
								<div class="flex-1">
									<h3 class="font-semibold text-[var(--color-text-primary)]">File d'attente</h3>
									<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-sm">
										<div>
											<span class="text-[var(--color-text-tertiary)]">Total:</span>
											<span class="ml-1">{bySource.queue.total}</span>
										</div>
										{#each Object.entries(bySource.queue.by_status) as [status, count]}
											<div>
												<span class="text-[var(--color-text-tertiary)] capitalize">{status}:</span>
												<span class="ml-1">{count}</span>
											</div>
										{/each}
									</div>
								</div>
							</div>
						</Card>
					{/if}

					<!-- Notes Stats -->
					{#if bySource.notes}
						<Card padding="lg">
							<div class="flex items-start gap-3">
								<span class="text-2xl">📝</span>
								<div class="flex-1">
									<h3 class="font-semibold text-[var(--color-text-primary)]">Notes</h3>
									<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2 text-sm">
										<div>
											<span class="text-[var(--color-text-tertiary)]">Total:</span>
											<span class="ml-1">{bySource.notes.total_notes}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">À revoir:</span>
											<span class="ml-1">{bySource.notes.total_due}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Révisées:</span>
											<span class="ml-1">{bySource.notes.reviewed_today}</span>
										</div>
										<div>
											<span class="text-[var(--color-text-tertiary)]">Facteur EF:</span>
											<span class="ml-1">{bySource.notes.avg_easiness_factor.toFixed(2)}</span>
										</div>
									</div>
									{#if Object.keys(bySource.notes.by_type).length > 0}
										<div class="mt-2 text-xs text-[var(--color-text-tertiary)]">
											Par type: {Object.entries(bySource.notes.by_type).map(([t, c]) => `${t}: ${c}`).join(', ')}
										</div>
									{/if}
								</div>
							</div>
						</Card>
					{/if}
				</div>
			</section>
		{/if}

		<!-- System Info -->
		<section class="mt-8">
			<Card padding="md" class="bg-[var(--color-surface-secondary)]">
				<div class="flex justify-between items-center text-sm text-[var(--color-text-tertiary)]">
					<span>Dernière activité: {lastActivityDisplay()}</span>
					<button
						class="text-[var(--color-accent)] hover:underline"
						onclick={() => fetchStats()}
					>
						Actualiser
					</button>
				</div>
			</Card>
		</section>
	{/if}
</div>
