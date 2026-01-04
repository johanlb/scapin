<script lang="ts">
	import { Card, Badge, Button } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import type { ScapinEvent } from '$lib/types';

	// Mock data - Timeline of all events
	const allEvents: ScapinEvent[] = [
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
			suggested_actions: []
		},
		{
			id: '2',
			source: 'teams',
			title: 'Nouveau message dans #projet-alpha',
			summary: 'Discussion sur les specs techniques du module authentification',
			sender: 'Équipe Dev',
			occurred_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'medium',
			confidence: 'high',
			suggested_actions: []
		},
		{
			id: '3',
			source: 'calendar',
			title: 'Réunion équipe produit',
			summary: 'Point hebdomadaire avec l\'équipe - salle Voltaire',
			occurred_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'high',
			confidence: 'high',
			suggested_actions: []
		},
		{
			id: '4',
			source: 'email',
			title: 'Newsletter Tech Weekly',
			summary: 'Les dernières actualités du monde tech cette semaine',
			sender: 'Tech Weekly',
			occurred_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'low',
			confidence: 'high',
			suggested_actions: []
		},
		{
			id: '5',
			source: 'omnifocus',
			title: 'Préparer présentation Q2',
			summary: 'Deadline: Vendredi 17h - Slides pour le comité de direction',
			occurred_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'high',
			confidence: 'medium',
			suggested_actions: []
		},
		{
			id: '6',
			source: 'teams',
			title: 'Message de Pierre Martin',
			summary: 'Question sur le déploiement de la v2.1',
			sender: 'Pierre Martin',
			occurred_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
			status: 'pending',
			urgency: 'medium',
			confidence: 'medium',
			suggested_actions: []
		}
	];

	type FilterSource = 'all' | 'email' | 'teams' | 'calendar' | 'omnifocus';
	let activeFilter: FilterSource = $state('all');

	const filteredEvents = $derived(
		activeFilter === 'all'
			? allEvents
			: allEvents.filter(e => e.source === activeFilter)
	);

	function getSourceIcon(source: string): string {
		const icons: Record<string, string> = {
			email: '📧',
			teams: '💬',
			calendar: '📅',
			omnifocus: '✅'
		};
		return icons[source] || '📄';
	}
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<!-- Header -->
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			📥 Flux d'événements
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Tous vos messages et notifications en un seul endroit
		</p>
	</header>

	<!-- Filters -->
	<section class="mb-6 flex flex-wrap gap-2">
		<Button
			variant={activeFilter === 'all' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => activeFilter = 'all'}
		>
			Tout ({allEvents.length})
		</Button>
		<Button
			variant={activeFilter === 'email' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => activeFilter = 'email'}
		>
			📧 Emails ({allEvents.filter(e => e.source === 'email').length})
		</Button>
		<Button
			variant={activeFilter === 'teams' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => activeFilter = 'teams'}
		>
			💬 Teams ({allEvents.filter(e => e.source === 'teams').length})
		</Button>
		<Button
			variant={activeFilter === 'calendar' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => activeFilter = 'calendar'}
		>
			📅 Calendrier ({allEvents.filter(e => e.source === 'calendar').length})
		</Button>
		<Button
			variant={activeFilter === 'omnifocus' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => activeFilter = 'omnifocus'}
		>
			✅ Tâches ({allEvents.filter(e => e.source === 'omnifocus').length})
		</Button>
	</section>

	<!-- Events Timeline -->
	<section class="space-y-4">
		{#each filteredEvents as event (event.id)}
			<Card interactive onclick={() => console.log('Open event', event.id)} padding="lg">
				<div class="flex items-start gap-4">
					<!-- Source Icon -->
					<div class="text-2xl flex-shrink-0">
						{getSourceIcon(event.source)}
					</div>

					<!-- Content -->
					<div class="flex-1 min-w-0">
						<div class="flex flex-wrap items-center gap-2 mb-2">
							<Badge variant="source" source={event.source} />
							{#if event.urgency === 'urgent' || event.urgency === 'high'}
								<Badge variant="urgency" urgency={event.urgency} />
							{/if}
							<span class="text-sm text-[var(--color-text-tertiary)]">
								{formatRelativeTime(event.occurred_at)}
							</span>
						</div>
						<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
							{event.title}
						</h3>
						<p class="text-[var(--color-text-secondary)]">{event.summary}</p>
						{#if event.sender}
							<p class="text-sm text-[var(--color-text-tertiary)] mt-2">
								De : {event.sender}
							</p>
						{/if}
					</div>

					<!-- Arrow -->
					<span class="text-xl text-[var(--color-text-tertiary)] flex-shrink-0">→</span>
				</div>
			</Card>
		{/each}

		{#if filteredEvents.length === 0}
			<Card padding="lg">
				<div class="text-center py-8">
					<p class="text-2xl mb-2">🎉</p>
					<p class="text-lg text-[var(--color-text-secondary)]">
						Aucun événement dans cette catégorie
					</p>
				</div>
			</Card>
		{/if}
	</section>
</div>
