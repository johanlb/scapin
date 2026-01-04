<script lang="ts">
	import { page } from '$app/stores';
	import { Card, Badge, Button } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import type { ScapinEvent } from '$lib/types';

	// Get the event ID from route params
	const eventId = $derived($page.params.id);

	// Mock event data (will be fetched from API)
	let event = $state<ScapinEvent | null>({
		id: '1',
		source: 'email',
		title: 'RE: Proposition commerciale Q1',
		summary:
			"Client ABC demande une révision du budget avant vendredi. Il souhaite également discuter des options de paiement échelonné pour le premier trimestre.",
		sender: 'Marie Dupont',
		occurred_at: new Date().toISOString(),
		status: 'pending',
		urgency: 'urgent',
		confidence: 'high',
		suggested_actions: [
			{ id: '1', type: 'reply', label: 'Répondre', confidence: 0.95 },
			{ id: '2', type: 'task', label: 'Créer tâche OmniFocus', confidence: 0.8 },
			{ id: '3', type: 'archive', label: 'Archiver', confidence: 0.6 }
		]
	});

	let loading = $state(false);

	function handleAction(actionId: string) {
		console.log('Action triggered:', actionId);
		// Would trigger the action via API
	}

	function goBack() {
		history.back();
	}
</script>

<div class="min-h-screen">
	<!-- Header with back button -->
	<header
		class="sticky top-0 z-20 glass-prominent border-b border-[var(--glass-border-subtle)] px-4 py-3"
	>
		<div class="max-w-4xl mx-auto flex items-center gap-3">
			<button
				onclick={goBack}
				class="p-2 -ml-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
			>
				<span class="text-xl">←</span>
			</button>
			<div class="flex-1 min-w-0">
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)] truncate">
					{event?.title || 'Chargement...'}
				</h1>
			</div>
		</div>
	</header>

	{#if loading}
		<div class="flex justify-center py-16">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if event}
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
			<!-- Meta info -->
			<div class="flex flex-wrap items-center gap-2">
				<Badge variant="source" source={event.source} />
				<Badge variant="urgency" urgency={event.urgency} />
				<span class="text-sm text-[var(--color-text-tertiary)]">
					{formatRelativeTime(event.occurred_at)}
				</span>
			</div>

			<!-- Sender -->
			{#if event.sender}
				<div class="flex items-center gap-3">
					<div
						class="w-10 h-10 rounded-full bg-[var(--color-accent)] flex items-center justify-center text-white font-semibold"
					>
						{event.sender.charAt(0)}
					</div>
					<div>
						<p class="font-medium text-[var(--color-text-primary)]">{event.sender}</p>
						<p class="text-sm text-[var(--color-text-tertiary)]">Expéditeur</p>
					</div>
				</div>
			{/if}

			<!-- Content -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<h2 class="font-semibold text-[var(--color-text-primary)] mb-3">{event.title}</h2>
					<p class="text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
						{event.summary}
					</p>
				</div>
			</Card>

			<!-- AI Analysis -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<h3 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3">
						Analyse de Scapin
					</h3>
					<p class="text-sm text-[var(--color-text-secondary)]">
						Ce message requiert votre attention. Je vous suggère de répondre rapidement car le
						client mentionne une échéance pour vendredi. Une tâche pourrait être créée pour
						assurer le suivi.
					</p>
					<div class="mt-3 flex items-center gap-2">
						<span class="text-xs text-[var(--color-text-tertiary)]">Confiance:</span>
						<div class="flex gap-0.5">
							{#each Array(5) as _, i}
								<div
									class="w-2 h-2 rounded-full {i < 4
										? 'bg-[var(--color-accent)]'
										: 'bg-[var(--glass-tint)]'}"
								></div>
							{/each}
						</div>
					</div>
				</div>
			</Card>

			<!-- Suggested Actions -->
			{#if event.suggested_actions && event.suggested_actions.length > 0}
				<section>
					<h3
						class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3"
					>
						Actions suggérées
					</h3>
					<div class="flex flex-wrap gap-2">
						{#each event.suggested_actions as action}
							<Button
								variant={action.type === 'reply' ? 'primary' : 'glass'}
								onclick={() => handleAction(action.id)}
							>
								{action.label}
								<span class="text-xs opacity-70 ml-1">
									({Math.round(action.confidence * 100)}%)
								</span>
							</Button>
						{/each}
					</div>
				</section>
			{/if}
		</main>
	{:else}
		<div class="p-8 text-center">
			<p class="text-[var(--color-text-tertiary)]">Élément introuvable</p>
		</div>
	{/if}
</div>
