<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Button, Badge, Skeleton } from '$lib/components/ui';
	import {
		listDrafts,
		listPendingDrafts,
		getDraftStats,
		deleteDraft,
		discardDraft,
		type Draft,
		type DraftStats
	} from '$lib/api/client';
	import { formatRelativeTime } from '$lib/utils/formatters';

	// State
	let drafts = $state<Draft[]>([]);
	let stats = $state<DraftStats | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeFilter = $state<'all' | 'pending' | 'sent' | 'discarded'>('pending');
	let page = $state(1);
	let hasMore = $state(false);
	let actionLoading = $state<string | null>(null);

	// Load drafts on mount
	onMount(async () => {
		await Promise.all([loadDrafts(), loadStats()]);
	});

	// Reload when filter changes
	$effect(() => {
		if (!loading) {
			page = 1;
			loadDrafts();
		}
	});

	async function loadStats() {
		try {
			stats = await getDraftStats();
		} catch (e) {
			console.error('Failed to load stats:', e);
		}
	}

	async function loadDrafts() {
		loading = true;
		error = null;
		try {
			let response;
			if (activeFilter === 'pending') {
				response = await listPendingDrafts(page, 20);
			} else if (activeFilter === 'all') {
				response = await listDrafts(page, 20);
			} else {
				response = await listDrafts(page, 20, activeFilter);
			}
			drafts = response.data;
			hasMore = response.has_more;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
		} finally {
			loading = false;
		}
	}

	async function handleDiscard(draftId: string) {
		actionLoading = draftId;
		try {
			await discardDraft(draftId);
			// Remove from list
			drafts = drafts.filter((d) => d.draft_id !== draftId);
			await loadStats();
		} catch (e) {
			console.error('Failed to discard draft:', e);
		} finally {
			actionLoading = null;
		}
	}

	async function handleDelete(draftId: string) {
		if (!confirm('Supprimer définitivement ce brouillon ?')) return;
		actionLoading = draftId;
		try {
			await deleteDraft(draftId);
			drafts = drafts.filter((d) => d.draft_id !== draftId);
			await loadStats();
		} catch (e) {
			console.error('Failed to delete draft:', e);
		} finally {
			actionLoading = null;
		}
	}

	function openDraft(draftId: string) {
		goto(`/drafts/${draftId}`);
	}

	function getStatusBadge(status: string): { label: string; variant: 'default' | 'success' | 'warning' | 'error' } {
		switch (status) {
			case 'sent':
				return { label: 'Envoyé', variant: 'success' };
			case 'discarded':
				return { label: 'Abandonné', variant: 'warning' };
			case 'failed':
				return { label: 'Échec', variant: 'error' };
			default:
				return { label: 'Brouillon', variant: 'default' };
		}
	}

	function truncate(text: string, maxLength: number): string {
		if (text.length <= maxLength) return text;
		return text.slice(0, maxLength) + '...';
	}
</script>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<!-- Header -->
	<header
		class="sticky top-0 z-20 glass-prominent border-b border-[var(--glass-border-subtle)] px-4 py-3"
	>
		<div class="max-w-4xl mx-auto">
			<div class="flex items-center justify-between mb-4">
				<div>
					<h1 class="text-xl font-semibold text-[var(--color-text-primary)]">Brouillons</h1>
					<p class="text-sm text-[var(--color-text-tertiary)]">
						{#if stats}
							{stats.total} brouillon{stats.total !== 1 ? 's' : ''} au total
						{:else}
							Chargement...
						{/if}
					</p>
				</div>
			</div>

			<!-- Filter tabs -->
			<div class="flex gap-2">
				{#each [
					{ key: 'pending', label: 'En attente', count: stats?.by_status?.draft ?? 0 },
					{ key: 'sent', label: 'Envoyés', count: stats?.by_status?.sent ?? 0 },
					{ key: 'discarded', label: 'Abandonnés', count: stats?.by_status?.discarded ?? 0 },
					{ key: 'all', label: 'Tous', count: stats?.total ?? 0 }
				] as filter}
					<button
						onclick={() => (activeFilter = filter.key as typeof activeFilter)}
						class="px-3 py-1.5 text-sm rounded-full transition-all {activeFilter === filter.key
							? 'bg-[var(--color-accent)] text-white'
							: 'bg-[var(--glass-tint)] text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint-hover)]'}"
					>
						{filter.label}
						<span class="ml-1 opacity-70">({filter.count})</span>
					</button>
				{/each}
			</div>
		</div>
	</header>

	<main class="p-4 md:p-6 max-w-4xl mx-auto">
		{#if loading && drafts.length === 0}
			<!-- Loading state -->
			<div class="space-y-4">
				{#each Array(3) as _}
					<Card variant="glass-subtle">
						<div class="p-4 space-y-3">
							<div class="flex items-center gap-3">
								<Skeleton variant="avatar" />
								<div class="flex-1 space-y-2">
									<Skeleton variant="text" class="w-2/3" />
									<Skeleton variant="text" class="w-1/2" />
								</div>
							</div>
							<Skeleton variant="text" lines={2} />
						</div>
					</Card>
				{/each}
			</div>
		{:else if error}
			<!-- Error state -->
			<Card variant="glass">
				<div class="p-8 text-center">
					<p class="text-red-400 mb-4">{error}</p>
					<Button variant="glass" onclick={loadDrafts}>Réessayer</Button>
				</div>
			</Card>
		{:else if drafts.length === 0}
			<!-- Empty state -->
			<Card variant="glass">
				<div class="p-8 text-center">
					<div class="text-4xl mb-4">📝</div>
					<h3 class="text-lg font-medium text-[var(--color-text-primary)] mb-2">
						Aucun brouillon
					</h3>
					<p class="text-[var(--color-text-tertiary)]">
						{#if activeFilter === 'pending'}
							Tous vos brouillons ont été traités.
						{:else if activeFilter === 'sent'}
							Aucun brouillon envoyé pour l'instant.
						{:else if activeFilter === 'discarded'}
							Aucun brouillon abandonné.
						{:else}
							Vous n'avez aucun brouillon.
						{/if}
					</p>
				</div>
			</Card>
		{:else}
			<!-- Drafts list -->
			<div class="space-y-4">
				{#each drafts as draft (draft.draft_id)}
					{@const statusBadge = getStatusBadge(draft.status)}
					<Card
						variant="glass-subtle"
						class="cursor-pointer hover:bg-[var(--glass-tint)] transition-colors"
					>
						<button
							class="w-full text-left p-4"
							onclick={() => openDraft(draft.draft_id)}
						>
							<!-- Header -->
							<div class="flex items-start justify-between gap-3 mb-2">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-[var(--color-text-primary)] truncate">
											{draft.subject || '(Sans objet)'}
										</span>
										{#if draft.ai_generated}
											<span
												class="px-1.5 py-0.5 text-xs rounded bg-purple-500/20 text-purple-300"
												title="Généré par IA"
											>
												IA
											</span>
										{/if}
									</div>
									<div class="text-sm text-[var(--color-text-tertiary)]">
										À : {draft.to_addresses.join(', ') || 'Non spécifié'}
									</div>
								</div>
								<div class="flex items-center gap-2">
									<span
										class="px-2 py-0.5 text-xs rounded-full
											{statusBadge.variant === 'success' ? 'bg-green-500/20 text-green-300' : ''}
											{statusBadge.variant === 'warning' ? 'bg-yellow-500/20 text-yellow-300' : ''}
											{statusBadge.variant === 'error' ? 'bg-red-500/20 text-red-300' : ''}
											{statusBadge.variant === 'default' ? 'bg-[var(--glass-tint)] text-[var(--color-text-secondary)]' : ''}"
									>
										{statusBadge.label}
									</span>
								</div>
							</div>

							<!-- Preview -->
							<p class="text-sm text-[var(--color-text-secondary)] line-clamp-2 mb-3">
								{truncate(draft.body, 150) || '(Contenu vide)'}
							</p>

							<!-- Meta -->
							<div class="flex items-center justify-between text-xs text-[var(--color-text-tertiary)]">
								<div class="flex items-center gap-3">
									{#if draft.original_from}
										<span>Re: {draft.original_from}</span>
									{/if}
									<span>{formatRelativeTime(draft.updated_at)}</span>
								</div>
								{#if draft.ai_confidence > 0}
									<span title="Confiance IA">
										{Math.round(draft.ai_confidence * 100)}%
									</span>
								{/if}
							</div>
						</button>

						<!-- Actions -->
						{#if draft.status === 'draft'}
							<div class="px-4 pb-4 flex gap-2 border-t border-[var(--glass-border-subtle)] pt-3">
								<Button
									variant="primary"
									size="sm"
									onclick={(e: Event) => {
										e.stopPropagation();
										openDraft(draft.draft_id);
									}}
								>
									Modifier
								</Button>
								<Button
									variant="ghost"
									size="sm"
									onclick={(e: Event) => {
										e.stopPropagation();
										handleDiscard(draft.draft_id);
									}}
									disabled={actionLoading === draft.draft_id}
								>
									{actionLoading === draft.draft_id ? '...' : 'Abandonner'}
								</Button>
								<div class="flex-1"></div>
								<Button
									variant="ghost"
									size="sm"
									onclick={(e: Event) => {
										e.stopPropagation();
										handleDelete(draft.draft_id);
									}}
									disabled={actionLoading === draft.draft_id}
									class="text-red-400 hover:text-red-300"
								>
									Supprimer
								</Button>
							</div>
						{/if}
					</Card>
				{/each}
			</div>

			<!-- Load more -->
			{#if hasMore}
				<div class="mt-6 text-center">
					<Button
						variant="glass"
						onclick={async () => {
							page++;
							await loadDrafts();
						}}
						disabled={loading}
					>
						{loading ? 'Chargement...' : 'Charger plus'}
					</Button>
				</div>
			{/if}
		{/if}
	</main>
</div>
