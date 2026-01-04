<script lang="ts">
	import { Card, Badge, PullToRefresh, SwipeableCard } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import type { ScapinEvent } from '$lib/types';

	// Mock data for development
	let mockEvents = $state<ScapinEvent[]>([
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
			summary: 'Point hebdomadaire avec l\'équipe - salle Voltaire',
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
	]);

	const stats = {
		emails_pending: 12,
		teams_unread: 5,
		meetings_today: 3,
		tasks_due: 7
	};

	async function handleRefresh(): Promise<void> {
		// Simulate API call
		await new Promise(resolve => setTimeout(resolve, 1000));
		console.log('Refreshed!');
	}

	function archiveEvent(eventId: string) {
		mockEvents = mockEvents.filter(e => e.id !== eventId);
		console.log('Archived:', eventId);
	}

	function replyToEvent(eventId: string) {
		console.log('Reply to:', eventId);
		// Would navigate to reply view
	}

	function getGreeting(): string {
		const hour = new Date().getHours();
		if (hour < 12) return 'Bonjour';
		if (hour < 18) return 'Bon après-midi';
		return 'Bonsoir';
	}

	const urgentEvents = $derived(mockEvents.filter(e => e.urgency === 'urgent' || e.urgency === 'high'));
	const otherEvents = $derived(mockEvents.filter(e => e.urgency !== 'urgent' && e.urgency !== 'high'));
</script>

<PullToRefresh onrefresh={handleRefresh}>
	<div class="p-4 md:p-6 max-w-4xl mx-auto overflow-hidden">
		<!-- Header -->
		<header class="mb-6">
			<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
				{getGreeting()} 👋
			</h1>
			<p class="text-[var(--color-text-secondary)] mt-1">
				Voici votre briefing du {new Date().toLocaleDateString('fr-FR', {
					weekday: 'long',
					day: 'numeric',
					month: 'long'
				})}
			</p>
		</header>

		<!-- Quick Stats -->
		<section class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-email)]">{stats.emails_pending}</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Emails</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-teams)]">{stats.teams_unread}</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Teams</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-calendar)]">{stats.meetings_today}</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Réunions</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl md:text-2xl font-bold text-[var(--color-event-omnifocus)]">{stats.tasks_due}</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Tâches</p>
				</div>
			</Card>
		</section>

		<!-- Urgent Items -->
		{#if urgentEvents.length > 0}
			<section class="mb-5">
				<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
					<span>🔴</span> Actions urgentes
				</h2>
				<div class="space-y-2">
					{#each urgentEvents as event (event.id)}
						<SwipeableCard
							leftAction={{
								icon: '📦',
								label: 'Archiver',
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
										<h3 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">{event.title}</h3>
										<p class="text-sm text-[var(--color-text-secondary)] line-clamp-1">{event.summary}</p>
										{#if event.sender}
											<p class="text-xs text-[var(--color-text-tertiary)] mt-1 truncate">De : {event.sender}</p>
										{/if}
									</div>
									<span class="text-[var(--color-text-tertiary)] shrink-0">→</span>
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
				<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
					<span>📋</span> À traiter
				</h2>
				<div class="space-y-2">
					{#each otherEvents as event (event.id)}
						<SwipeableCard
							leftAction={{
								icon: '📦',
								label: 'Archiver',
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
										<h3 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">{event.title}</h3>
										<p class="text-sm text-[var(--color-text-secondary)] line-clamp-1">{event.summary}</p>
									</div>
									<span class="text-[var(--color-text-tertiary)] shrink-0">→</span>
								</div>
							</button>
						</SwipeableCard>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Empty state hint for swipe gestures (mobile only) -->
		<p class="text-xs text-[var(--color-text-tertiary)] text-center mt-6 md:hidden">
			Glissez les cartes pour répondre ou archiver
		</p>
	</div>
</PullToRefresh>
