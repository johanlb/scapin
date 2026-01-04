<script lang="ts">
	import { Card, Button } from '$lib/components/ui';

	interface JournalEntry {
		id: string;
		date: string;
		mood: string;
		highlights: string[];
		accomplishments: number;
		reflection: string;
	}

	const entries: JournalEntry[] = [
		{
			id: '1',
			date: new Date().toISOString(),
			mood: '😊',
			highlights: ['Réunion client réussie', 'Déploiement v2.1 sans accroc'],
			accomplishments: 8,
			reflection: 'Journée productive malgré les interruptions...'
		},
		{
			id: '2',
			date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
			mood: '😐',
			highlights: ['Formation équipe', 'Revue de code'],
			accomplishments: 5,
			reflection: 'Beaucoup de contexte switching aujourd\'hui...'
		},
		{
			id: '3',
			date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
			mood: '🚀',
			highlights: ['Lancement feature majeure', 'Feedback positif utilisateurs'],
			accomplishments: 12,
			reflection: 'Excellente journée ! L\'équipe a vraiment assuré...'
		}
	];

	function formatDate(isoString: string): string {
		return new Date(isoString).toLocaleDateString('fr-FR', {
			weekday: 'long',
			day: 'numeric',
			month: 'long'
		});
	}
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			📖 Journal
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Scapin prend note pour vous, Monsieur
		</p>
	</header>

	<section class="mb-6">
		<Button variant="primary" onclick={() => console.log('New entry')}>
			✏️ Consigner
		</Button>
	</section>

	<section class="space-y-4">
		{#each entries as entry (entry.id)}
			<Card interactive onclick={() => console.log('Open', entry.id)} padding="lg">
				<div class="flex items-start gap-4">
					<div class="text-4xl">{entry.mood}</div>
					<div class="flex-1">
						<div class="flex items-center gap-3 mb-2">
							<h3 class="text-lg font-semibold text-[var(--color-text-primary)]">
								{formatDate(entry.date)}
							</h3>
							<span class="px-2 py-1 text-sm bg-[var(--color-success)]/10 text-[var(--color-success)] rounded-lg">
								{entry.accomplishments} tâches
							</span>
						</div>
						<div class="flex flex-wrap gap-2 mb-2">
							{#each entry.highlights as highlight}
								<span class="px-2 py-1 text-sm bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] rounded-lg">
									{highlight}
								</span>
							{/each}
						</div>
						<p class="text-[var(--color-text-secondary)] line-clamp-2">
							{entry.reflection}
						</p>
					</div>
					<span class="text-xl text-[var(--color-text-tertiary)]">→</span>
				</div>
			</Card>
		{/each}
	</section>
</div>
