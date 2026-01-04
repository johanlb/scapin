<script lang="ts">
	import { onMount } from 'svelte';

	interface SearchResult {
		id: string;
		type: 'note' | 'email' | 'event' | 'task' | 'discussion';
		title: string;
		subtitle?: string;
		path?: string;
		icon: string;
	}

	let {
		onclose = () => {},
		onselect = (_result: SearchResult) => {}
	}: {
		onclose?: () => void;
		onselect?: (result: SearchResult) => void;
	} = $props();

	let query = $state('');
	let selectedIndex = $state(0);
	let inputRef: HTMLInputElement;

	// Mock search results - would be replaced by actual search API
	const allItems: SearchResult[] = [
		{ id: '1', type: 'note', title: 'Architecture Scapin v2', subtitle: 'Projets/Scapin/Architecture', icon: '📝' },
		{ id: '2', type: 'note', title: 'Guide déploiement v2.1', subtitle: 'Projets/Scapin/Documentation', icon: '📝' },
		{ id: '3', type: 'email', title: 'RE: Proposition commerciale Q1', subtitle: 'De: Marie Dupont', icon: '📧' },
		{ id: '4', type: 'event', title: 'Réunion équipe produit', subtitle: 'Dans 2h - Salle Voltaire', icon: '📅' },
		{ id: '5', type: 'task', title: 'Préparer présentation Q2', subtitle: 'Due: Vendredi 17h', icon: '✅' },
		{ id: '6', type: 'discussion', title: 'Discussion #projet-alpha', subtitle: 'Teams - Équipe Dev', icon: '💬' },
		{ id: '7', type: 'note', title: 'API Design Guidelines', subtitle: 'Projets/Scapin/Documentation', icon: '📝' },
		{ id: '8', type: 'email', title: 'Newsletter Tech Weekly', subtitle: 'De: Tech Weekly', icon: '📧' },
		{ id: '9', type: 'note', title: 'Contacts Client ABC', subtitle: 'Clients/ABC', icon: '📝' },
		{ id: '10', type: 'task', title: 'Review code PR #42', subtitle: 'Due: Aujourd\'hui', icon: '✅' }
	];

	const results = $derived(
		query.trim() === ''
			? allItems.slice(0, 6) // Show recent items when no query
			: allItems.filter(item =>
					item.title.toLowerCase().includes(query.toLowerCase()) ||
					(item.subtitle?.toLowerCase().includes(query.toLowerCase()) ?? false)
				).slice(0, 8)
	);

	// Reset selection when results change
	$effect(() => {
		if (results) {
			selectedIndex = 0;
		}
	});

	function handleKeydown(event: KeyboardEvent) {
		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
				break;
			case 'ArrowUp':
				event.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, 0);
				break;
			case 'Enter':
				event.preventDefault();
				if (results[selectedIndex]) {
					onselect(results[selectedIndex]);
					onclose();
				}
				break;
			case 'Escape':
				event.preventDefault();
				onclose();
				break;
		}
	}

	function getTypeLabel(type: SearchResult['type']): string {
		const labels: Record<SearchResult['type'], string> = {
			note: 'Carnet',
			email: 'Email',
			event: 'Événement',
			task: 'Tâche',
			discussion: 'Conversation'
		};
		return labels[type];
	}

	function getTypeColor(type: SearchResult['type']): string {
		const colors: Record<SearchResult['type'], string> = {
			note: 'var(--color-event-omnifocus)',
			email: 'var(--color-event-email)',
			event: 'var(--color-event-calendar)',
			task: 'var(--color-event-omnifocus)',
			discussion: 'var(--color-event-teams)'
		};
		return colors[type];
	}

	onMount(() => {
		inputRef?.focus();
	});
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- Backdrop -->
<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-[15vh]"
	onclick={onclose}
>
	<!-- Modal -->
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		class="w-full max-w-xl mx-4 bg-[var(--color-bg-primary)] rounded-2xl shadow-2xl overflow-hidden"
		onclick={(e) => e.stopPropagation()}
	>
		<!-- Search Input -->
		<div class="flex items-center gap-3 p-4 border-b border-[var(--color-border)]">
			<span class="text-xl text-[var(--color-text-tertiary)]">🔍</span>
			<input
				bind:this={inputRef}
				bind:value={query}
				type="text"
				placeholder="Rechercher carnets, emails, événements..."
				class="flex-1 bg-transparent text-lg text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] outline-none"
			/>
			<kbd class="hidden md:inline-flex px-2 py-1 text-xs text-[var(--color-text-tertiary)] bg-[var(--color-bg-secondary)] rounded-md">
				ESC
			</kbd>
		</div>

		<!-- Results -->
		<div class="max-h-[50vh] overflow-y-auto">
			{#if results.length === 0}
				<div class="p-8 text-center">
					<p class="text-[var(--color-text-tertiary)]">Je ne trouve rien de tel dans vos papiers, Monsieur</p>
				</div>
			{:else}
				<div class="p-2">
					{#if query.trim() === ''}
						<p class="px-3 py-2 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wide">
							Récents
						</p>
					{/if}
					{#each results as result, index (result.id)}
						<button
							type="button"
							class="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-colors {index === selectedIndex ? 'bg-[var(--color-accent)]/10' : 'hover:bg-[var(--color-bg-secondary)]'}"
							onclick={() => { onselect(result); onclose(); }}
							onmouseenter={() => selectedIndex = index}
						>
							<span class="text-xl">{result.icon}</span>
							<div class="flex-1 min-w-0">
								<p class="text-[var(--color-text-primary)] font-medium truncate">
									{result.title}
								</p>
								{#if result.subtitle}
									<p class="text-sm text-[var(--color-text-tertiary)] truncate">
										{result.subtitle}
									</p>
								{/if}
							</div>
							<span
								class="px-2 py-0.5 text-xs rounded-md"
								style="background-color: {getTypeColor(result.type)}20; color: {getTypeColor(result.type)}"
							>
								{getTypeLabel(result.type)}
							</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border)] text-xs text-[var(--color-text-tertiary)]">
			<div class="flex items-center gap-4">
				<span class="flex items-center gap-1">
					<kbd class="px-1.5 py-0.5 bg-[var(--color-bg-secondary)] rounded">↑</kbd>
					<kbd class="px-1.5 py-0.5 bg-[var(--color-bg-secondary)] rounded">↓</kbd>
					naviguer
				</span>
				<span class="flex items-center gap-1">
					<kbd class="px-1.5 py-0.5 bg-[var(--color-bg-secondary)] rounded">↵</kbd>
					ouvrir
				</span>
			</div>
			<span class="hidden md:block">
				<kbd class="px-1.5 py-0.5 bg-[var(--color-bg-secondary)] rounded">⌘</kbd>
				<kbd class="px-1.5 py-0.5 bg-[var(--color-bg-secondary)] rounded">K</kbd>
				pour ouvrir
			</span>
		</div>
	</div>
</div>
