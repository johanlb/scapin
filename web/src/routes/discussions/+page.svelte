<script lang="ts">
	import { Card, Badge } from '$lib/components/ui';

	interface Discussion {
		id: string;
		title: string;
		lastMessage: string;
		participants: string[];
		source: 'teams' | 'email';
		unread: number;
		updated_at: string;
	}

	const discussions: Discussion[] = [
		{
			id: '1',
			title: '#projet-alpha',
			lastMessage: 'Pierre: Les tests passent maintenant !',
			participants: ['Pierre', 'Marie', 'Jean'],
			source: 'teams',
			unread: 3,
			updated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString()
		},
		{
			id: '2',
			title: 'RE: Budget Q1 - Révision',
			lastMessage: 'Marie: J\'ai mis à jour le fichier Excel...',
			participants: ['Marie Dupont', 'Vous'],
			source: 'email',
			unread: 1,
			updated_at: new Date(Date.now() - 30 * 60 * 1000).toISOString()
		},
		{
			id: '3',
			title: '#general',
			lastMessage: 'Bot: Déploiement v2.0.5 réussi',
			participants: ['Équipe'],
			source: 'teams',
			unread: 0,
			updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
		}
	];

	function formatTime(isoString: string): string {
		const date = new Date(isoString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.round(diffMs / (1000 * 60));

		if (diffMins < 60) return `${diffMins} min`;
		const hours = Math.round(diffMins / 60);
		if (hours < 24) return `${hours}h`;
		return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
	}
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			💬 Discussions
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Vos conversations actives
		</p>
	</header>

	<section class="space-y-4">
		{#each discussions as discussion (discussion.id)}
			<Card interactive onclick={() => console.log('Open', discussion.id)} padding="lg">
				<div class="flex items-center gap-4">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-1">
							<Badge variant="source" source={discussion.source} />
							<span class="text-sm text-[var(--color-text-tertiary)]">
								{formatTime(discussion.updated_at)}
							</span>
							{#if discussion.unread > 0}
								<span class="px-2 py-0.5 text-sm font-bold bg-[var(--color-accent)] text-white rounded-full">
									{discussion.unread}
								</span>
							{/if}
						</div>
						<h3 class="text-lg font-semibold text-[var(--color-text-primary)]">
							{discussion.title}
						</h3>
						<p class="text-[var(--color-text-secondary)] truncate">
							{discussion.lastMessage}
						</p>
					</div>
					<span class="text-xl text-[var(--color-text-tertiary)]">→</span>
				</div>
			</Card>
		{/each}
	</section>
</div>
