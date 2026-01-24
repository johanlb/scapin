<script lang="ts">
	/**
	 * RetoucheQueue Component
	 * Page showing notes with pending retouche actions
	 */
	import { Button, Card, Badge } from '$lib/components/ui';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		getRetoucheQueue,
		applyRetouche,
		type RetoucheQueue,
		type RetoucheQueueItem
	} from '$lib/api/client';
	import RetoucheBadge from './RetoucheBadge.svelte';
	import RetoucheDiff from './RetoucheDiff.svelte';

	interface Props {
		onNavigate?: (noteId: string) => void;
	}

	let { onNavigate }: Props = $props();

	let queue = $state<RetoucheQueue | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let applyingAll = $state(false);
	let selectedNoteId = $state<string | null>(null);
	let showPreview = $state(false);

	// Load queue on mount
	$effect(() => {
		loadQueue();
	});

	async function loadQueue() {
		loading = true;
		error = null;
		try {
			queue = await getRetoucheQueue();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
			toastStore.error('Impossible de charger la queue des retouches');
		} finally {
			loading = false;
		}
	}

	async function handleApplyAllHighConfidence() {
		if (!queue || queue.high_confidence.length === 0) return;

		applyingAll = true;
		let successCount = 0;
		let failCount = 0;

		for (const item of queue.high_confidence) {
			try {
				await applyRetouche(item.note_id, { apply_all: true });
				successCount++;
			} catch {
				failCount++;
			}
		}

		applyingAll = false;

		if (successCount > 0) {
			toastStore.success(`${successCount} notes retouchées avec succès`);
		}
		if (failCount > 0) {
			toastStore.warning(`${failCount} notes ont échoué`);
		}

		// Reload queue
		await loadQueue();
	}

	function handleViewNote(item: RetoucheQueueItem) {
		selectedNoteId = item.note_id;
		showPreview = true;
	}

	function handleNavigateToNote(noteId: string) {
		if (onNavigate) {
			onNavigate(noteId);
		}
	}

	function handlePreviewApplied() {
		showPreview = false;
		selectedNoteId = null;
		loadQueue();
	}

	function formatDate(timestamp: string | null): string {
		if (!timestamp) return 'Jamais';
		return new Date(timestamp).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	const totalPending = $derived(
		queue ? queue.high_confidence.length + queue.pending_review.length : 0
	);
</script>

<div class="retouche-queue" data-testid="retouche-queue">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<div>
			<h2 class="text-xl font-semibold text-[var(--color-text-primary)]">
				Retouches en attente
			</h2>
			<p class="text-sm text-[var(--color-text-tertiary)] mt-1">
				Notes analysées par l'IA avec des améliorations proposées
			</p>
		</div>

		<div class="flex items-center gap-3">
			<Button variant="ghost" onclick={loadQueue} disabled={loading}>
				{loading ? 'Chargement...' : 'Actualiser'}
			</Button>
			{#if queue && queue.high_confidence.length > 0}
				<Button variant="primary" onclick={handleApplyAllHighConfidence} disabled={applyingAll}>
					{applyingAll ? 'Application...' : `Tout valider (${queue.high_confidence.length})`}
				</Button>
			{/if}
		</div>
	</div>

	{#if loading && !queue}
		<div class="flex justify-center py-12">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if error}
		<Card variant="glass" padding="lg" class="text-center">
			<p class="text-[var(--color-error)]">{error}</p>
			<Button variant="ghost" onclick={loadQueue} class="mt-4">Réessayer</Button>
		</Card>
	{:else if !queue || totalPending === 0}
		<Card variant="glass" padding="lg" class="text-center">
			<p class="text-4xl mb-4">✨</p>
			<p class="text-[var(--color-text-secondary)]">Aucune retouche en attente</p>
			<p class="text-sm text-[var(--color-text-tertiary)] mt-2">
				Les notes sont à jour ou n'ont pas encore été analysées
			</p>
		</Card>
	{:else}
		<!-- Stats bar -->
		<div class="grid grid-cols-4 gap-4 mb-6">
			<Card variant="glass" padding="sm" class="text-center">
				<div class="text-2xl font-bold text-[var(--color-accent)]">{queue.stats.total || 0}</div>
				<div class="text-xs text-[var(--color-text-tertiary)]">Total</div>
			</Card>
			<Card variant="glass" padding="sm" class="text-center">
				<div class="text-2xl font-bold text-green-400">{queue.stats.high_confidence || 0}</div>
				<div class="text-xs text-[var(--color-text-tertiary)]">Auto-applicable</div>
			</Card>
			<Card variant="glass" padding="sm" class="text-center">
				<div class="text-2xl font-bold text-yellow-400">{queue.stats.pending_review || 0}</div>
				<div class="text-xs text-[var(--color-text-tertiary)]">A valider</div>
			</Card>
			<Card variant="glass" padding="sm" class="text-center">
				<div class="text-2xl font-bold text-purple-400">
					{queue.stats.auto_applied_today || 0}
				</div>
				<div class="text-xs text-[var(--color-text-tertiary)]">Appliquées aujourd'hui</div>
			</Card>
		</div>

		<!-- High confidence section -->
		{#if queue.high_confidence.length > 0}
			<div class="mb-6">
				<h3 class="text-sm font-medium text-[var(--color-text-tertiary)] mb-3 flex items-center gap-2">
					<span class="w-2 h-2 rounded-full bg-green-400"></span>
					Haute confiance (auto-applicable)
				</h3>
				<div class="space-y-2">
					{#each queue.high_confidence as item}
						<Card
							variant="glass"
							padding="sm"
							class="cursor-pointer hover:ring-1 hover:ring-[var(--color-accent)] transition-all"
							onclick={() => handleViewNote(item)}
						>
							<div class="flex items-center gap-4 p-2">
								<input
									type="checkbox"
									checked={true}
									class="w-4 h-4 rounded accent-[var(--color-accent)]"
									onclick={(e) => e.stopPropagation()}
								/>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-medium text-[var(--color-text-primary)] truncate">
											{item.note_title}
										</span>
										{#if item.note_path}
											<span class="text-xs text-[var(--color-text-tertiary)]">
												{item.note_path}
											</span>
										{/if}
									</div>
									<div class="text-xs text-[var(--color-text-tertiary)] mt-1">
										{item.action_count} action{item.action_count > 1 ? 's' : ''} · Dernière: {formatDate(
											item.last_retouche
										)}
									</div>
								</div>
								<RetoucheBadge
									qualityScore={item.quality_score}
									retoucheCount={item.action_count}
									size="sm"
								/>
								<Badge class="bg-green-500/20 text-green-300">
									{(item.avg_confidence * 100).toFixed(0)}%
								</Badge>
								<Button
									variant="ghost"
									size="sm"
									onclick={(e: MouseEvent) => {
										e.stopPropagation();
										handleNavigateToNote(item.note_id);
									}}
								>
									Voir
								</Button>
							</div>
						</Card>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Pending review section -->
		{#if queue.pending_review.length > 0}
			<div>
				<h3 class="text-sm font-medium text-[var(--color-text-tertiary)] mb-3 flex items-center gap-2">
					<span class="w-2 h-2 rounded-full bg-yellow-400"></span>
					Validation requise
				</h3>
				<div class="space-y-2">
					{#each queue.pending_review as item}
						<Card
							variant="glass"
							padding="sm"
							class="cursor-pointer hover:ring-1 hover:ring-[var(--color-accent)] transition-all"
							onclick={() => handleViewNote(item)}
						>
							<div class="flex items-center gap-4 p-2">
								<input
									type="checkbox"
									checked={false}
									class="w-4 h-4 rounded accent-[var(--color-accent)]"
									onclick={(e) => e.stopPropagation()}
								/>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-medium text-[var(--color-text-primary)] truncate">
											{item.note_title}
										</span>
										{#if item.note_path}
											<span class="text-xs text-[var(--color-text-tertiary)]">
												{item.note_path}
											</span>
										{/if}
									</div>
									<div class="text-xs text-[var(--color-text-tertiary)] mt-1">
										{item.action_count} action{item.action_count > 1 ? 's' : ''} · Dernière: {formatDate(
											item.last_retouche
										)}
									</div>
								</div>
								<RetoucheBadge
									qualityScore={item.quality_score}
									retoucheCount={item.action_count}
									size="sm"
								/>
								<Badge class="bg-yellow-500/20 text-yellow-300">
									{(item.avg_confidence * 100).toFixed(0)}%
								</Badge>
								<Button
									variant="ghost"
									size="sm"
									onclick={(e: MouseEvent) => {
										e.stopPropagation();
										handleNavigateToNote(item.note_id);
									}}
								>
									Voir
								</Button>
							</div>
						</Card>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>

<!-- Preview modal -->
{#if selectedNoteId}
	<RetoucheDiff noteId={selectedNoteId} bind:open={showPreview} onApplied={handlePreviewApplied} />
{/if}

<style>
	.retouche-queue {
		max-width: 1000px;
		margin: 0 auto;
	}
</style>
