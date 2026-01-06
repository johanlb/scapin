<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Badge, PullToRefresh, SwipeableCard } from '$lib/components/ui';
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';
	import { PreMeetingModal } from '$lib/components/briefing';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { briefingStore } from '$lib/stores';
	import { notesReviewStore } from '$lib/stores/notes-review.svelte';
	import type { ScapinEvent } from '$lib/types';

	// Mock data for development (fallback when API unavailable)
	const mockEvents: ScapinEvent[] = [
		{
			id: '1',
			source: 'email',
			title: 'RE: Proposition commerciale Q1',
			summary: 'Client ABC demande une révision du budget avant vendredi',
			sender: 'Marie Dupont',
			occurred_at: new Date().toISOString(),
			status: 'pending',
			urgency: 'urgent',
			confidence: 'high',
			suggested_actions: [
				{ id: '1', type: 'reply', label: 'Répondre', confidence: 0.95 },
				{ id: '2', type: 'task', label: 'Créer tâche', confidence: 0.8 }
			]
		},
		{
			id: '2',
			source: 'calendar',
			title: 'Réunion équipe produit',
			summary: "Point hebdomadaire avec l'équipe - salle Voltaire",
			occurred_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'high',
			confidence: 'high',
			suggested_actions: [{ id: '1', type: 'prepare', label: 'Préparer', confidence: 0.9 }]
		},
		{
			id: '3',
			source: 'teams',
			title: 'Message de Pierre Martin',
			summary: 'Question sur le déploiement de la v2.1',
			sender: 'Pierre Martin',
			occurred_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'medium',
			confidence: 'medium',
			suggested_actions: [{ id: '1', type: 'reply', label: 'Répondre', confidence: 0.85 }]
		}
	];

	const mockStats = {
		emails_pending: 12,
		teams_unread: 5,
		meetings_today: 3,
		tasks_due: 7
	};

	// Local state for events (will be populated from API or mock)
	let events = $state<ScapinEvent[]>(mockEvents);
	let stats = $state(mockStats);
	let dataSource = $state<'mock' | 'api' | 'api-empty'>('mock');

	// Pre-meeting briefing modal state
	let showBriefingModal = $state(false);
	let selectedEventId = $state<string | null>(null);
	let selectedEventTitle = $state<string | null>(null);

	function openBriefing(event: ScapinEvent) {
		selectedEventId = event.id;
		selectedEventTitle = event.title;
		showBriefingModal = true;
	}

	function closeBriefing() {
		showBriefingModal = false;
		selectedEventId = null;
		selectedEventTitle = null;
	}

	// Load data on mount
	onMount(async () => {
		await Promise.all([loadBriefingData(), notesReviewStore.fetchStats()]);
	});

	async function loadBriefingData(): Promise<void> {
		await briefingStore.fetchBriefing();

		if (briefingStore.briefing && briefingStore.stats) {
			// Transform API data to ScapinEvent format
			const apiEvents: ScapinEvent[] = [
				...briefingStore.briefing.urgent_items.map(transformBriefingItem),
				...briefingStore.briefing.calendar_today.map(transformBriefingItem),
				...briefingStore.briefing.emails_pending.map(transformBriefingItem),
				...briefingStore.briefing.teams_unread.map(transformBriefingItem)
			];

			if (apiEvents.length > 0) {
				events = apiEvents;
				dataSource = 'api';
			} else {
				// API returned success but no items
				events = [];
				dataSource = 'api-empty';
			}

			stats = {
				emails_pending: briefingStore.briefing.emails_pending.length,
				teams_unread: briefingStore.briefing.teams_unread.length,
				meetings_today: briefingStore.briefing.meetings_today,
				tasks_due: 0
			};
		}
	}

	function transformBriefingItem(item: {
		id?: string;
		event_id?: string;
		type?: string;
		source?: string;
		title: string;
		summary?: string;
		action_summary?: string;
		urgency: string;
		timestamp?: string;
		time_context?: string;
		has_conflicts?: boolean;
		conflicts?: ScapinEvent['conflicts'];
	}): ScapinEvent {
		return {
			id: item.event_id || item.id || '',
			source: (item.source || item.type || 'email') as ScapinEvent['source'],
			title: item.title,
			summary: item.action_summary || item.summary || '',
			occurred_at: item.time_context || item.timestamp || '',
			status: 'pending',
			urgency: item.urgency as ScapinEvent['urgency'],
			confidence: 'high',
			suggested_actions: [],
			has_conflicts: item.has_conflicts,
			conflicts: item.conflicts
		};
	}

	async function handleRefresh(): Promise<void> {
		await loadBriefingData();
	}

	function archiveEvent(eventId: string) {
		events = events.filter((e) => e.id !== eventId);
		console.log('Archived:', eventId);
	}

	function replyToEvent(eventId: string) {
		console.log('Reply to:', eventId);
		// Would navigate to reply view
	}

	function getGreeting(): string {
		const hour = new Date().getHours();
		if (hour < 12) return 'Bonjour Monsieur';
		if (hour < 18) return 'Bon après-midi Monsieur';
		return 'Bonsoir Monsieur';
	}

	const urgentEvents = $derived(
		events.filter((e) => e.urgency === 'urgent' || e.urgency === 'high')
	);
	const otherEvents = $derived(
		events.filter((e) => e.urgency !== 'urgent' && e.urgency !== 'high')
	);
	// Events with calendar conflicts
	const eventsWithConflicts = $derived(events.filter((e) => e.has_conflicts && e.conflicts?.length));
	const conflictsCount = $derived(briefingStore.briefing?.conflicts_count || 0);
</script>

<PullToRefresh onrefresh={handleRefresh}>
	<div class="p-4 md:p-6 max-w-4xl mx-auto overflow-hidden">
		<!-- Header -->
		<header class="mb-6">
			<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
				{getGreeting()}
			</h1>
			<p class="text-[var(--color-text-secondary)] mt-1">
				{#if briefingStore.loading}
					Chargement du briefing...
				{:else}
					Voici l'état des affaires en ce {new Date().toLocaleDateString('fr-FR', {
						weekday: 'long',
						day: 'numeric',
						month: 'long'
					})}
				{/if}
			</p>
			{#if briefingStore.error}
				<p class="text-xs text-[var(--color-urgency-urgent)] mt-1">
					{briefingStore.error}
				</p>
			{/if}
			{#if dataSource === 'mock' && !briefingStore.loading}
				<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
					Données de démonstration (serveur hors ligne)
				</p>
			{/if}
			{#if dataSource === 'api-empty' && !briefingStore.loading}
				<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
					✓ Connecté — aucun élément en attente
				</p>
			{/if}
		</header>

		<!-- Quick Stats -->
		<section class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-email)]">
						{stats.emails_pending}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Emails</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-teams)]">
						{stats.teams_unread}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Teams</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-calendar)]">
						{stats.meetings_today}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Réunions</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-omnifocus)]">
						{stats.tasks_due}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Tâches</p>
				</div>
			</Card>
		</section>

		<!-- Notes Review Widget -->
		{#if notesReviewStore.stats && notesReviewStore.stats.total_due > 0}
			<section class="mb-5">
				<h2
					class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2"
				>
					<span>📝</span> Notes à réviser
				</h2>
				<Card interactive onclick={() => goto('/notes/review')}>
					<div class="flex items-center justify-between p-3">
						<div>
							<p class="text-lg font-semibold text-[var(--color-text-primary)]">
								{notesReviewStore.stats.total_due} notes
							</p>
							<p class="text-xs text-[var(--color-text-tertiary)]">
								{notesReviewStore.stats.reviewed_today} révisées aujourd'hui
							</p>
						</div>
						<div class="flex items-center gap-3">
							<ProgressRing
								percent={notesReviewStore.stats.total_notes > 0
									? Math.round(
											((notesReviewStore.stats.total_notes - notesReviewStore.stats.total_due) /
												notesReviewStore.stats.total_notes) *
												100
										)
									: 100}
								size={48}
								color="primary"
							/>
							<span class="text-[var(--color-text-tertiary)]">→</span>
						</div>
					</div>
				</Card>
			</section>
		{/if}

		<!-- Calendar Conflicts Section -->
		{#if conflictsCount > 0 && eventsWithConflicts.length > 0}
			<section class="mb-5">
				<h2
					class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2"
				>
					<span class="text-orange-500">⚠️</span> Conflits Calendrier
					<span class="text-xs font-normal px-1.5 py-0.5 rounded-full bg-orange-500/10 text-orange-500">
						{conflictsCount}
					</span>
				</h2>
				<Card class="border-orange-500/30 bg-orange-500/5">
					<ul class="divide-y divide-[var(--color-border)]">
						{#each eventsWithConflicts as event (event.id)}
							<li class="p-3">
								<div class="flex items-start gap-2">
									<span class="text-orange-500 text-sm mt-0.5">📅</span>
									<div class="flex-1 min-w-0">
										<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
											{event.title}
										</p>
										<p class="text-xs text-[var(--color-text-tertiary)]">
											{event.occurred_at}
										</p>
										{#if event.conflicts}
											<ul class="mt-1.5 space-y-1">
												{#each event.conflicts as conflict}
													<li class="flex items-start gap-1.5">
														<span
															class="inline-block w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
															class:bg-red-500={conflict.severity === 'high'}
															class:bg-orange-500={conflict.severity === 'medium'}
															class:bg-yellow-500={conflict.severity === 'low'}
														></span>
														<span class="text-xs text-orange-600 dark:text-orange-400">
															{conflict.message}
														</span>
													</li>
												{/each}
											</ul>
										{/if}
									</div>
								</div>
							</li>
						{/each}
					</ul>
				</Card>
			</section>
		{/if}

		<!-- Loading state -->
		{#if briefingStore.loading}
			<div class="flex justify-center py-8">
				<div
					class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
				></div>
			</div>
		{:else if dataSource === 'api-empty'}
			<!-- Empty state when API returns no items -->
			<div class="text-center py-12">
				<p class="text-4xl mb-3">🎉</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
					Tout est en ordre, Monsieur
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">
					Aucune affaire pressante ne requiert votre attention
				</p>
			</div>
		{:else}
			<!-- Urgent Items -->
			{#if urgentEvents.length > 0}
				<section class="mb-5">
					<h2
						class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2"
					>
						<span>🔔</span> Affaires pressantes
					</h2>
					<div class="space-y-2">
						{#each urgentEvents as event (event.id)}
							<SwipeableCard
								leftAction={{
									icon: '📦',
									label: 'Classer',
									color: 'var(--color-text-tertiary)',
									action: () => archiveEvent(event.id)
								}}
								rightAction={{
									icon: '↩️',
									label: 'Répondre',
									color: 'var(--color-accent)',
									action: () => replyToEvent(event.id)
								}}
							>
								<button
									type="button"
									onclick={() => console.log('Navigate to', event.id)}
									class="w-full text-left p-3"
								>
									<div class="flex items-start gap-3">
										<div class="flex-1 min-w-0">
											<div class="flex flex-wrap items-center gap-1.5 mb-1">
												<Badge variant="source" source={event.source} />
												<Badge variant="urgency" urgency={event.urgency} />
												<span class="text-xs text-[var(--color-text-tertiary)]">
													{formatRelativeTime(event.occurred_at)}
												</span>
											</div>
											<h3
												class="text-sm font-semibold text-[var(--color-text-primary)] truncate"
											>
												{event.title}
											</h3>
											<p class="text-sm text-[var(--color-text-secondary)] line-clamp-1">
												{event.summary}
											</p>
											{#if event.sender}
												<p class="text-xs text-[var(--color-text-tertiary)] mt-1 truncate">
													De : {event.sender}
												</p>
											{/if}
											{#if event.has_conflicts && event.conflicts?.length}
												<p
													class="text-xs text-orange-500 mt-1 flex items-center gap-1"
													title={event.conflicts.map((c) => c.message).join(', ')}
												>
													<span>⚠️</span>
													<span>{event.conflicts.length} conflit{event.conflicts.length > 1 ? 's' : ''}</span>
												</p>
											{/if}
										</div>
										<div class="shrink-0 flex items-center gap-2">
											{#if event.source === 'calendar'}
												<!-- svelte-ignore a11y_no_static_element_interactions -->
												<span
													role="button"
													tabindex="0"
													class="p-1.5 rounded-lg text-[var(--color-event-calendar)] hover:bg-[var(--color-event-calendar)] hover:bg-opacity-10 transition-colors cursor-pointer"
													title="Briefing pré-réunion"
													onclick={(e) => {
														e.stopPropagation();
														openBriefing(event);
													}}
													onkeydown={(e) => {
														if (e.key === 'Enter' || e.key === ' ') {
															e.preventDefault();
															e.stopPropagation();
															openBriefing(event);
														}
													}}
												>
													<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
													</svg>
												</span>
											{/if}
											<span class="text-[var(--color-text-tertiary)]">→</span>
										</div>
									</div>
								</button>
							</SwipeableCard>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Other Pending -->
			{#if otherEvents.length > 0}
				<section>
					<h2
						class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2"
					>
						<span>📌</span> À votre attention
					</h2>
					<div class="space-y-2">
						{#each otherEvents as event (event.id)}
							<SwipeableCard
								leftAction={{
									icon: '📦',
									label: 'Classer',
									color: 'var(--color-text-tertiary)',
									action: () => archiveEvent(event.id)
								}}
								rightAction={{
									icon: '↩️',
									label: 'Répondre',
									color: 'var(--color-accent)',
									action: () => replyToEvent(event.id)
								}}
							>
								<button
									type="button"
									onclick={() => console.log('Navigate to', event.id)}
									class="w-full text-left p-3"
								>
									<div class="flex items-start gap-3">
										<div class="flex-1 min-w-0">
											<div class="flex flex-wrap items-center gap-1.5 mb-1">
												<Badge variant="source" source={event.source} />
												<span class="text-xs text-[var(--color-text-tertiary)]">
													{formatRelativeTime(event.occurred_at)}
												</span>
											</div>
											<h3
												class="text-sm font-semibold text-[var(--color-text-primary)] truncate"
											>
												{event.title}
											</h3>
											<p class="text-sm text-[var(--color-text-secondary)] line-clamp-1">
												{event.summary}
											</p>
											{#if event.has_conflicts && event.conflicts?.length}
												<p
													class="text-xs text-orange-500 mt-1 flex items-center gap-1"
													title={event.conflicts.map((c) => c.message).join(', ')}
												>
													<span>⚠️</span>
													<span>{event.conflicts.length} conflit{event.conflicts.length > 1 ? 's' : ''}</span>
												</p>
											{/if}
										</div>
										<div class="shrink-0 flex items-center gap-2">
											{#if event.source === 'calendar'}
												<!-- svelte-ignore a11y_no_static_element_interactions -->
												<span
													role="button"
													tabindex="0"
													class="p-1.5 rounded-lg text-[var(--color-event-calendar)] hover:bg-[var(--color-event-calendar)] hover:bg-opacity-10 transition-colors cursor-pointer"
													title="Briefing pré-réunion"
													onclick={(e) => {
														e.stopPropagation();
														openBriefing(event);
													}}
													onkeydown={(e) => {
														if (e.key === 'Enter' || e.key === ' ') {
															e.preventDefault();
															e.stopPropagation();
															openBriefing(event);
														}
													}}
												>
													<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
													</svg>
												</span>
											{/if}
											<span class="text-[var(--color-text-tertiary)]">→</span>
										</div>
									</div>
								</button>
							</SwipeableCard>
						{/each}
					</div>
				</section>
			{/if}
		{/if}

		<!-- Empty state hint for swipe gestures (mobile only) -->
		<p class="text-xs text-[var(--color-text-tertiary)] text-center mt-6 md:hidden">
			Glissez les cartes pour répondre ou archiver
		</p>
	</div>
</PullToRefresh>

<!-- Pre-meeting briefing modal -->
{#if selectedEventId}
	<PreMeetingModal
		bind:open={showBriefingModal}
		eventId={selectedEventId}
		eventTitle={selectedEventTitle}
		onclose={closeBriefing}
	/>
{/if}
