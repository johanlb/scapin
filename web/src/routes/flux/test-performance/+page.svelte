<!--
  Performance Test Page for VirtualList

  This page generates mock data to test virtualization performance.
  Access via: http://localhost:5173/flux/test-performance
-->
<script lang="ts">
	import { VirtualList, Card, Button } from '$lib/components/ui';
	import type { QueueItem } from '$lib/api';

	// Test configuration
	let itemCount = $state(1000);
	let generatedItems: QueueItem[] = $state([]);
	let isGenerating = $state(false);
	let renderTime = $state(0);

	// Generate mock items
	function generateItems(count: number): QueueItem[] {
		const statuses = ['approved', 'rejected'];
		const actions = ['archive', 'delete', 'reply', 'forward', 'flag', 'task'];
		const categories = ['work', 'personal', 'finance', 'newsletter', 'social'];

		const items: QueueItem[] = [];

		for (let i = 0; i < count; i++) {
			const status = statuses[Math.floor(Math.random() * statuses.length)];
			const action = actions[Math.floor(Math.random() * actions.length)];
			const category = categories[Math.floor(Math.random() * categories.length)];

			items.push({
				id: `mock-${i}`,
				account_id: 'test-account',
				status,
				queued_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
				reviewed_at: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
				review_decision: null,
				metadata: {
					id: `email-${i}`,
					subject: `Email de test #${i + 1} - ${generateRandomSubject()}`,
					from_address: `sender${i}@example.com`,
					from_name: `Expéditeur ${i + 1}`,
					date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
					folder: 'INBOX',
					has_attachments: Math.random() > 0.7
				},
				analysis: {
					action,
					category,
					confidence: Math.floor(50 + Math.random() * 50),
					reasoning: `Analyse automatique pour l'email ${i + 1}`,
					summary: generateRandomSummary(),
					options: [],
					// Sprint 2: Entity extraction fields
					entities: i % 5 === 0 ? { person: [{ value: 'Jean Dupont', confidence: 0.9, type: 'person', source: 'extraction', metadata: {} }] } : {},
					proposed_notes: i % 7 === 0 ? [{ action: 'create' as const, note_type: 'personne', title: 'Jean Dupont', content_summary: 'Contact professionnel', confidence: 0.85, reasoning: 'Nouvelle personne détectée', auto_applied: false, target_note_id: null }] : [],
					proposed_tasks: i % 10 === 0 ? [{ title: 'Répondre à Jean', note: 'Email urgent', project: 'Communications', due_date: '2026-01-10', confidence: 0.9, reasoning: 'Action requise', auto_applied: false }] : [],
					context_used: i % 6 === 0 ? ['note-jean-dupont-abc123', 'note-projet-xyz-789'] : [],
					// Sprint 3: Draft replies
					draft_reply: action === 'reply' ? `Bonjour,\n\nMerci pour votre email.\n\nCordialement,\nJohan` : null
				},
				content: {
					preview: `Ceci est le contenu de l'email ${i + 1}...`
				}
			});
		}

		return items;
	}

	function generateRandomSubject(): string {
		const subjects = [
			'Réunion demain à 10h',
			'Facture du mois',
			'Newsletter hebdomadaire',
			'Invitation à un événement',
			'Mise à jour de projet',
			'Question urgente',
			'Confirmation de commande',
			'Rappel: échéance proche',
			'Rapport mensuel disponible',
			'Nouvelle fonctionnalité disponible'
		];
		return subjects[Math.floor(Math.random() * subjects.length)];
	}

	function generateRandomSummary(): string {
		const summaries = [
			'Email concernant une réunion importante la semaine prochaine.',
			'Notification de paiement pour les services du mois dernier.',
			'Résumé des actualités et mises à jour de la semaine.',
			'Demande de confirmation pour un événement à venir.',
			"Mise à jour sur l'avancement du projet en cours.",
			'Question nécessitant une réponse rapide.',
			'Confirmation de votre récente commande en ligne.',
			"Rappel concernant une échéance à ne pas manquer.",
			'Le rapport mensuel est maintenant disponible pour consultation.',
			'Annonce de nouvelles fonctionnalités dans le service.'
		];
		return summaries[Math.floor(Math.random() * summaries.length)];
	}

	async function handleGenerate() {
		isGenerating = true;
		const startTime = performance.now();

		// Use setTimeout to allow UI update before heavy computation
		await new Promise((resolve) => setTimeout(resolve, 50));

		generatedItems = generateItems(itemCount);

		// Measure time to next frame (when rendering is complete)
		requestAnimationFrame(() => {
			renderTime = Math.round(performance.now() - startTime);
			isGenerating = false;
		});
	}

	// Helpers for display
	function getActionIcon(action: string): string {
		const icons: Record<string, string> = {
			archive: '📥',
			delete: '🗑️',
			reply: '✉️',
			forward: '⬆️',
			flag: '🚩',
			task: '✅'
		};
		return icons[action] || '❓';
	}

	function getActionColor(action: string): string {
		const colors: Record<string, string> = {
			archive: 'var(--color-success)',
			delete: 'var(--color-urgency-urgent)',
			reply: 'var(--color-accent)',
			task: 'var(--color-event-omnifocus)'
		};
		return colors[action] || 'var(--color-text-secondary)';
	}

	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const minutes = Math.floor(diff / 60000);
		const hours = Math.floor(minutes / 60);
		const days = Math.floor(hours / 24);

		if (days > 0) return `il y a ${days}j`;
		if (hours > 0) return `il y a ${hours}h`;
		if (minutes > 0) return `il y a ${minutes}m`;
		return "à l'instant";
	}
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<header class="mb-6">
		<h1 class="text-2xl font-bold text-[var(--color-text-primary)]">
			Test de Performance — VirtualList
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Génère des données fictives pour tester la virtualisation et l'infinite scroll.
		</p>
	</header>

	<!-- Configuration -->
	<Card padding="md">
		<div class="flex flex-wrap items-center gap-4">
			<div class="flex items-center gap-2">
				<label for="itemCount" class="text-sm text-[var(--color-text-secondary)]">
					Nombre d'items :
				</label>
				<input
					id="itemCount"
					type="number"
					min="100"
					max="100000"
					step="100"
					bind:value={itemCount}
					class="w-24 px-2 py-1 rounded border border-[var(--color-border)] bg-[var(--color-bg-secondary)]"
				/>
			</div>

			<Button variant="primary" onclick={handleGenerate} disabled={isGenerating}>
				{isGenerating ? 'Génération...' : 'Générer'}
			</Button>

			{#if generatedItems.length > 0}
				<div class="text-sm text-[var(--color-text-tertiary)]">
					{generatedItems.length} items générés en {renderTime}ms
				</div>
			{/if}
		</div>
	</Card>

	<!-- Performance metrics -->
	{#if generatedItems.length > 0}
		<div class="mt-4 grid grid-cols-3 gap-2 text-center">
			<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
				<p class="text-lg font-bold text-[var(--color-text-primary)]">{generatedItems.length}</p>
				<p class="text-xs text-[var(--color-text-tertiary)]">Items</p>
			</div>
			<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
				<p class="text-lg font-bold text-[var(--color-text-primary)]">{renderTime}ms</p>
				<p class="text-xs text-[var(--color-text-tertiary)]">Temps initial</p>
			</div>
			<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
				<p class="text-lg font-bold text-[var(--color-success)]">Fluide</p>
				<p class="text-xs text-[var(--color-text-tertiary)]">Scroll virtualisé</p>
			</div>
		</div>
	{/if}

	<!-- Virtual List -->
	{#if generatedItems.length > 0}
		<section class="mt-4">
			<VirtualList
				items={generatedItems}
				estimatedItemHeight={120}
				height="calc(100vh - 350px)"
				getKey={(item) => item.id}
			>
				{#snippet item(item, _index)}
					<div class="pb-3">
						<Card padding="md">
							<div class="flex items-start gap-3">
								<div
									class="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-lg"
									style="background-color: color-mix(in srgb, {getActionColor(item.analysis.action)} 20%, transparent)"
								>
									{getActionIcon(item.analysis.action)}
								</div>

								<div class="flex-1 min-w-0">
									<h3 class="font-medium text-[var(--color-text-primary)] truncate">
										{item.metadata.subject}
									</h3>
									<p class="text-xs text-[var(--color-text-secondary)]">
										{item.metadata.from_name || item.metadata.from_address}
										{#if item.metadata.date}
											<span class="text-[var(--color-text-tertiary)]">
												• {formatRelativeTime(item.metadata.date)}
											</span>
										{/if}
									</p>
									{#if item.analysis.summary}
										<p class="text-xs text-[var(--color-text-tertiary)] mt-1 line-clamp-2">
											{item.analysis.summary}
										</p>
									{/if}
								</div>

								<div class="shrink-0 text-right">
									<span
										class="text-xs px-2 py-1 rounded-full"
										class:bg-green-100={item.status === 'approved'}
										class:text-green-700={item.status === 'approved'}
										class:bg-red-100={item.status === 'rejected'}
										class:text-red-700={item.status === 'rejected'}
									>
										{item.analysis.action}
									</span>
								</div>
							</div>
						</Card>
					</div>
				{/snippet}

				{#snippet empty()}
					<div class="text-center py-8 text-[var(--color-text-secondary)]">
						Aucun item généré
					</div>
				{/snippet}
			</VirtualList>
		</section>
	{/if}

	<!-- Instructions -->
	{#if generatedItems.length === 0}
		<Card padding="lg">
			<div class="text-center py-8">
				<p class="text-4xl mb-3">🧪</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
					Test de Virtualisation
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)] max-w-md mx-auto">
					Cliquez sur "Générer" pour créer des données fictives et tester les performances de
					VirtualList avec des milliers d'items.
				</p>
				<ul class="text-xs text-[var(--color-text-tertiary)] mt-4 space-y-1">
					<li>• 1 000 items : Test basique</li>
					<li>• 10 000 items : Test réaliste</li>
					<li>• 50 000+ items : Test de stress</li>
				</ul>
			</div>
		</Card>
	{/if}
</div>
