<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { globalSearch, type GlobalSearchResponse } from '$lib/api/client';
	import type { SearchResult } from '$lib/types';
	import SearchResultItem from './SearchResultItem.svelte';

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
	let loading = $state(false);
	let error = $state<string | null>(null);
	let searchResults = $state<SearchResult[]>([]);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	// Recent items shown when no query
	const recentItems: SearchResult[] = [
		{
			id: 'recent-1',
			type: 'note',
			title: 'Dernière note consultée',
			subtitle: 'Notes récentes',
			icon: '📝'
		},
		{
			id: 'recent-2',
			type: 'email',
			title: 'Dernier email traité',
			subtitle: 'Péripétie récente',
			icon: '📧'
		}
	];

	// Transform API response to SearchResult format
	function transformApiResults(response: GlobalSearchResponse): SearchResult[] {
		const results: SearchResult[] = [];

		// Notes
		for (const note of response.results.notes) {
			results.push({
				id: note.id,
				type: 'note',
				title: note.title,
				subtitle: note.path || note.excerpt,
				path: note.path,
				icon: '📝'
			});
		}

		// Emails
		for (const email of response.results.emails) {
			results.push({
				id: email.id,
				type: 'email',
				title: email.title,
				subtitle: `De: ${email.from_name || email.from_address}`,
				icon: '📧'
			});
		}

		// Calendar
		for (const event of response.results.calendar) {
			results.push({
				id: event.id,
				type: 'event',
				title: event.title,
				subtitle: event.location || formatEventTime(event.start),
				icon: '📅'
			});
		}

		// Teams
		for (const msg of response.results.teams) {
			results.push({
				id: msg.id,
				type: 'discussion',
				title: msg.title,
				subtitle: `De: ${msg.sender}`,
				path: msg.chat_id,
				icon: '💬'
			});
		}

		// Sort by score (highest first)
		return results
			.sort((a, b) => {
				const scoreA = getScoreFromResponse(response, a.id);
				const scoreB = getScoreFromResponse(response, b.id);
				return scoreB - scoreA;
			})
			.slice(0, 8);
	}

	function getScoreFromResponse(response: GlobalSearchResponse, id: string): number {
		for (const note of response.results.notes) if (note.id === id) return note.score;
		for (const email of response.results.emails) if (email.id === id) return email.score;
		for (const event of response.results.calendar) if (event.id === id) return event.score;
		for (const msg of response.results.teams) if (msg.id === id) return msg.score;
		return 0;
	}

	function formatEventTime(isoString: string): string {
		try {
			const date = new Date(isoString);
			return date.toLocaleString('fr-FR', {
				day: 'numeric',
				month: 'short',
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch {
			return isoString;
		}
	}

	// Debounced search function
	async function performSearch(searchQuery: string) {
		if (searchQuery.length < 2) {
			searchResults = [];
			return;
		}

		loading = true;
		error = null;

		try {
			const response = await globalSearch(searchQuery, { limit: 10 });
			searchResults = transformApiResults(response);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de recherche';
			searchResults = [];
		} finally {
			loading = false;
		}
	}

	// Watch query changes with debounce
	$effect(() => {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}

		if (query.trim().length >= 2) {
			debounceTimer = setTimeout(() => {
				performSearch(query.trim());
			}, 300);
		} else {
			searchResults = [];
			loading = false;
		}

		return () => {
			if (debounceTimer) clearTimeout(debounceTimer);
		};
	});

	// Results to display
	const results = $derived(query.trim() === '' ? recentItems : searchResults);

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
					navigateToResult(results[selectedIndex]);
				}
				break;
			case 'Escape':
				event.preventDefault();
				onclose();
				break;
		}
	}

	// Navigate to the selected result
	function navigateToResult(result: SearchResult) {
		onselect(result);
		onclose();

		// Navigate based on result type
		switch (result.type) {
			case 'note':
				const notePath = result.path ? `${result.path}/${result.id}` : result.id;
				goto(`/memoires/${notePath}`);
				break;
			case 'email':
				goto(`/peripeties/${result.id}`);
				break;
			case 'event':
				goto(`/calendar?event=${result.id}`);
				break;
			case 'discussion':
				if (result.path) {
					goto(`/discussions?chat=${result.path}`);
				} else {
					goto(`/discussions?id=${result.id}`);
				}
				break;
			case 'task':
				goto(`/tasks/${result.id}`);
				break;
		}
	}

	onMount(() => {
		inputRef?.focus();
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Backdrop -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-start justify-center pt-[15vh]"
	role="button"
	tabindex="-1"
	aria-label="Fermer la recherche"
	onclick={onclose}
>
	<!-- Modal -->
	<div
		class="w-full max-w-xl mx-4 glass-prominent rounded-3xl shadow-2xl overflow-hidden
			animate-fluid glass-glow"
		role="dialog"
		tabindex="-1"
		aria-modal="true"
		aria-label="Recherche globale"
		data-testid="command-palette"
		onclick={(e) => e.stopPropagation()}
	>
		<!-- Search Input -->
		<div class="flex items-center gap-3 p-4 border-b border-[var(--glass-border-subtle)]">
			<span class="text-xl text-[var(--color-text-tertiary)]">🔍</span>
			<input
				bind:this={inputRef}
				bind:value={query}
				type="text"
				placeholder="Rechercher carnets, emails, événements..."
				class="flex-1 bg-transparent text-lg text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] outline-none"
				data-testid="search-input"
			/>
			<kbd
				class="hidden md:inline-flex px-2 py-1 text-xs text-[var(--color-text-tertiary)] glass-subtle rounded-lg"
			>
				ESC
			</kbd>
		</div>

		<!-- Results -->
		<div class="max-h-[50vh] overflow-y-auto" data-testid="search-results">
			{#if loading}
				<div class="flex justify-center py-8">
					<div
						class="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
					></div>
				</div>
			{:else if error}
				<div class="p-8 text-center">
					<p class="text-[var(--color-error)] font-medium">{error}</p>
				</div>
			{:else if query.trim().length >= 2 && results.length === 0}
				<div class="p-8 text-center">
					<p class="text-[var(--color-text-tertiary)]">
						Je ne trouve rien de tel dans vos papiers, Monsieur
					</p>
				</div>
			{:else if query.trim().length > 0 && query.trim().length < 2}
				<div class="p-8 text-center text-sm">
					<p class="text-[var(--color-text-tertiary)]">
						Tapez au moins 2 caractères pour rechercher
					</p>
				</div>
			{:else if results.length === 0}
				<div class="p-8 text-center text-sm">
					<p class="text-[var(--color-text-tertiary)]">Commencez à taper pour rechercher</p>
				</div>
			{:else}
				<div class="p-2 space-y-1">
					{#if query.trim() === ''}
						<p
							class="px-3 py-2 text-[10px] font-bold text-[var(--color-text-tertiary)] uppercase tracking-widest font-mono"
						>
							Récents
						</p>
					{/if}
					{#each results as result, index (result.id)}
						<SearchResultItem
							{result}
							active={index === selectedIndex}
							onclick={() => navigateToResult(result)}
							onmouseenter={() => (selectedIndex = index)}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div
			class="flex items-center justify-between px-4 py-3 border-t border-[var(--glass-border-subtle)] text-[10px] text-[var(--color-text-tertiary)] uppercase font-mono tracking-widest"
		>
			<div class="flex items-center gap-4">
				<span class="flex items-center gap-1">
					<kbd class="px-1.5 py-0.5 glass-subtle rounded-md text-[9px]">↑↓</kbd>
					naviguer
				</span>
				<span class="flex items-center gap-1">
					<kbd class="px-1.5 py-0.5 glass-subtle rounded-md text-[9px]">↵</kbd>
					ouvrir
				</span>
			</div>
			<span class="hidden md:block">
				<kbd class="px-1.5 py-0.5 glass-subtle rounded-md text-[9px]">⌘K</kbd>
				RECHERCHE
			</span>
		</div>
	</div>
</div>
