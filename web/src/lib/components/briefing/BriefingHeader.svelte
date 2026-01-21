<script lang="ts">
	interface Props {
		loading: boolean;
		error: string | null;
		isMock: boolean;
		isEmpty: boolean;
	}

	let { loading, error, isMock, isEmpty }: Props = $props();

	function getGreeting(): string {
		const hour = new Date().getHours();
		if (hour < 12) return 'Bonjour Monsieur';
		if (hour < 18) return 'Bon après-midi Monsieur';
		return 'Bonsoir Monsieur';
	}

	const dateStr = new Date().toLocaleDateString('fr-FR', {
		weekday: 'long',
		day: 'numeric',
		month: 'long'
	});
</script>

<header class="mb-6">
	<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
		{getGreeting()}
	</h1>
	<p class="text-[var(--color-text-secondary)] mt-1">
		{#if loading}
			Chargement du briefing...
		{:else}
			Voici l'état des affaires en ce {dateStr}
		{/if}
	</p>
	{#if error}
		<p class="text-xs text-[var(--color-urgency-urgent)] mt-1">
			{error}
		</p>
	{/if}
	{#if isMock && !loading}
		<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
			Données de démonstration (serveur hors ligne)
		</p>
	{/if}
	{#if isEmpty && !loading}
		<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
			✓ Connecté — aucun élément en attente
		</p>
	{/if}
</header>
