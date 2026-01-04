<script lang="ts">
	import { page } from '$app/stores';
	import { Card, Badge, Button } from '$lib/components/ui';

	// Get the note path from route params
	const notePath = $derived($page.params.path);
	const pathParts = $derived(notePath ? notePath.split('/') : []);

	// Mock note data (will be fetched from API)
	let note = $state({
		title: 'Réunion Projet Alpha',
		path: '',
		content: `# Réunion Projet Alpha

## Participants
- Jean-Pierre (Chef de projet)
- Marie (Designer)
- Thomas (Développeur)

## Points discutés

### 1. Avancement du sprint
Le sprint actuel avance bien. 80% des tâches sont terminées.

### 2. Blocages identifiés
- Attente de validation du design
- Dépendance sur l'API externe

### 3. Prochaines étapes
1. Finaliser les maquettes
2. Intégrer le module de paiement
3. Tests utilisateurs

## Actions à suivre
- [ ] Marie: Livrer les maquettes finales (vendredi)
- [ ] Thomas: Documenter l'API (lundi)
- [ ] Jean-Pierre: Planifier les tests utilisateurs`,
		folder: 'Projets/Alpha',
		created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
		updated_at: new Date().toISOString(),
		tags: ['projet', 'réunion', 'alpha'],
		pinned: true
	});

	let loading = $state(false);
	let editing = $state(false);

	function goBack() {
		history.back();
	}

	function toggleEdit() {
		editing = !editing;
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'long',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
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
				<!-- Breadcrumb -->
				<div class="flex items-center gap-1 text-sm text-[var(--color-text-tertiary)]">
					<span>Notes</span>
					{#each pathParts as part, i}
						<span>/</span>
						<span class={i === pathParts.length - 1 ? 'text-[var(--color-text-primary)]' : ''}>
							{part}
						</span>
					{/each}
				</div>
			</div>
			<button
				onclick={toggleEdit}
				class="p-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
			>
				<span class="text-xl">{editing ? '✓' : '✏️'}</span>
			</button>
		</div>
	</header>

	{#if loading}
		<div class="flex justify-center py-16">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if note}
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
			<!-- Meta info -->
			<div class="flex flex-wrap items-center gap-2">
				{#if note.pinned}
					<Badge>📌 Épinglée</Badge>
				{/if}
				{#each note.tags as tag}
					<Badge>{tag}</Badge>
				{/each}
			</div>

			<!-- Title -->
			<h1 class="text-2xl font-bold text-[var(--color-text-primary)]">
				{note.title}
			</h1>

			<!-- Dates -->
			<div class="text-sm text-[var(--color-text-tertiary)] flex flex-wrap gap-4">
				<span>Créée: {formatDate(note.created_at)}</span>
				<span>Modifiée: {formatDate(note.updated_at)}</span>
			</div>

			<!-- Content -->
			<Card variant="glass-subtle">
				<div class="p-4 md:p-6">
					{#if editing}
						<textarea
							bind:value={note.content}
							class="w-full min-h-[400px] bg-transparent text-[var(--color-text-primary)]
								font-mono text-sm leading-relaxed resize-y outline-none"
						></textarea>
					{:else}
						<div class="prose prose-invert max-w-none">
							<!-- Simple markdown rendering - would use a proper markdown parser -->
							{#each note.content.split('\n') as line}
								{#if line.startsWith('# ')}
									<h1 class="text-xl font-bold text-[var(--color-text-primary)] mt-4 mb-2">
										{line.slice(2)}
									</h1>
								{:else if line.startsWith('## ')}
									<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mt-4 mb-2">
										{line.slice(3)}
									</h2>
								{:else if line.startsWith('### ')}
									<h3 class="text-base font-semibold text-[var(--color-text-primary)] mt-3 mb-1">
										{line.slice(4)}
									</h3>
								{:else if line.startsWith('- [ ]')}
									<div class="flex items-center gap-2 py-0.5">
										<input type="checkbox" disabled class="w-4 h-4 rounded" />
										<span class="text-[var(--color-text-secondary)]">{line.slice(6)}</span>
									</div>
								{:else if line.startsWith('- [x]')}
									<div class="flex items-center gap-2 py-0.5">
										<input type="checkbox" checked disabled class="w-4 h-4 rounded" />
										<span class="text-[var(--color-text-secondary)] line-through"
											>{line.slice(6)}</span
										>
									</div>
								{:else if line.startsWith('- ')}
									<div class="flex items-start gap-2 py-0.5">
										<span class="text-[var(--color-text-tertiary)]">•</span>
										<span class="text-[var(--color-text-secondary)]">{line.slice(2)}</span>
									</div>
								{:else if line.match(/^\d+\. /)}
									<div class="flex items-start gap-2 py-0.5">
										<span class="text-[var(--color-text-tertiary)] font-mono text-sm"
											>{line.match(/^\d+/)?.[0]}.</span
										>
										<span class="text-[var(--color-text-secondary)]"
											>{line.replace(/^\d+\. /, '')}</span
										>
									</div>
								{:else if line.trim() === ''}
									<div class="h-2"></div>
								{:else}
									<p class="text-[var(--color-text-secondary)] py-0.5">{line}</p>
								{/if}
							{/each}
						</div>
					{/if}
				</div>
			</Card>

			<!-- Related Items -->
			<section>
				<h3
					class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3"
				>
					Éléments liés
				</h3>
				<div class="space-y-2">
					<Card variant="glass" interactive padding="sm">
						<div class="flex items-center gap-3 p-2">
							<span class="text-lg">📧</span>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
									Email: Compte-rendu réunion Alpha
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Il y a 3 jours</p>
							</div>
						</div>
					</Card>
					<Card variant="glass" interactive padding="sm">
						<div class="flex items-center gap-3 p-2">
							<span class="text-lg">📅</span>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
									Prochaine réunion: Lundi 10h
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Dans 3 jours</p>
							</div>
						</div>
					</Card>
				</div>
			</section>
		</main>
	{:else}
		<div class="p-8 text-center">
			<p class="text-[var(--color-text-tertiary)]">Note introuvable</p>
		</div>
	{/if}
</div>
