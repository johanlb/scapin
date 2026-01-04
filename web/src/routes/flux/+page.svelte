<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Badge, Button } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { queueStore } from '$lib/stores';
	import type { QueueItem } from '$lib/stores';

	// Load queue on mount
	onMount(async () => {
		await queueStore.fetchQueue('pending');
	});

	type StatusFilter = 'pending' | 'approved' | 'rejected' | 'all';
	let activeFilter: StatusFilter = $state('pending');

	async function changeFilter(filter: StatusFilter) {
		activeFilter = filter;
		await queueStore.fetchQueue(filter === 'all' ? '' : filter);
	}

	async function handleApprove(item: QueueItem) {
		const success = await queueStore.approve(item.id);
		if (success) {
			// Remove from list if viewing pending
			if (activeFilter === 'pending') {
				queueStore.removeFromList(item.id);
			}
		}
	}

	async function handleReject(item: QueueItem) {
		const success = await queueStore.reject(item.id);
		if (success) {
			// Remove from list if viewing pending
			if (activeFilter === 'pending') {
				queueStore.removeFromList(item.id);
			}
		}
	}

	function getActionLabel(action: string): string {
		const labels: Record<string, string> = {
			archive: 'Archiver',
			delete: 'Supprimer',
			reply: 'Répondre',
			forward: 'Transférer',
			flag: 'Signaler',
			task: 'Créer tâche',
			defer: 'Reporter',
			ignore: 'Ignorer'
		};
		return labels[action] || action;
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

	function getConfidenceLabel(confidence: number): string {
		if (confidence >= 0.9) return 'Très sûr';
		if (confidence >= 0.7) return 'Probable';
		if (confidence >= 0.5) return 'Incertain';
		return 'Douteux';
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.9) return 'var(--color-success)';
		if (confidence >= 0.7) return 'var(--color-warning)';
		return 'var(--color-urgency-urgent)';
	}

	const stats = $derived(queueStore.stats);
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<!-- Header -->
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			Le Courrier du jour
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			{#if queueStore.loading}
				Consultation des plis en attente...
			{:else if queueStore.total > 0}
				{queueStore.total} pli{queueStore.total > 1 ? 's' : ''} requièrent votre attention
			{:else}
				Aucun pli en attente de révision
			{/if}
		</p>
		{#if queueStore.error}
			<p class="text-xs text-[var(--color-urgency-urgent)] mt-1">
				{queueStore.error}
			</p>
		{/if}
	</header>

	<!-- Stats bar -->
	{#if stats}
		<section class="grid grid-cols-3 gap-2 mb-5">
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl font-bold text-[var(--color-warning)]">
						{stats.by_status?.pending ?? 0}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">En attente</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl font-bold text-[var(--color-success)]">
						{stats.by_status?.approved ?? 0}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Approuvés</p>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<p class="text-xl font-bold text-[var(--color-urgency-urgent)]">
						{stats.by_status?.rejected ?? 0}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Rejetés</p>
				</div>
			</Card>
		</section>
	{/if}

	<!-- Filters -->
	<section class="mb-6 flex flex-wrap gap-2">
		<Button
			variant={activeFilter === 'pending' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => changeFilter('pending')}
		>
			En attente
		</Button>
		<Button
			variant={activeFilter === 'approved' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => changeFilter('approved')}
		>
			Approuvés
		</Button>
		<Button
			variant={activeFilter === 'rejected' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => changeFilter('rejected')}
		>
			Rejetés
		</Button>
		<Button
			variant={activeFilter === 'all' ? 'primary' : 'secondary'}
			size="sm"
			onclick={() => changeFilter('all')}
		>
			Tous
		</Button>
	</section>

	<!-- Loading state -->
	{#if queueStore.loading && queueStore.items.length === 0}
		<div class="flex justify-center py-12">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if queueStore.items.length === 0}
		<!-- Empty state -->
		<Card padding="lg">
			<div class="text-center py-8">
				<p class="text-4xl mb-3">
					{#if activeFilter === 'pending'}
						<span>&#x1F389;</span>
					{:else if activeFilter === 'approved'}
						<span>&#x2705;</span>
					{:else if activeFilter === 'rejected'}
						<span>&#x274C;</span>
					{:else}
						<span>&#x1F4ED;</span>
					{/if}
				</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
					{#if activeFilter === 'pending'}
						Tout est en ordre, Monsieur
					{:else if activeFilter === 'approved'}
						Aucun pli approuvé
					{:else if activeFilter === 'rejected'}
						Aucun pli rejeté
					{:else}
						La boîte est vide
					{/if}
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">
					{#if activeFilter === 'pending'}
						Aucun courrier ne requiert votre attention
					{:else}
						Lancez le traitement des emails pour alimenter la file
					{/if}
				</p>
			</div>
		</Card>
	{:else}
		<!-- Queue items -->
		<section class="space-y-4">
			{#each queueStore.items as item (item.id)}
				<Card padding="lg">
					<div class="space-y-3">
						<!-- Header row -->
						<div class="flex items-start justify-between gap-3">
							<div class="flex-1 min-w-0">
								<div class="flex flex-wrap items-center gap-2 mb-1">
									<Badge variant="source" source="email" />
									<span
										class="text-xs px-2 py-0.5 rounded-full"
										style="background-color: color-mix(in srgb, {getActionColor(
											item.analysis.action
										)} 20%, transparent); color: {getActionColor(item.analysis.action)}"
									>
										{getActionLabel(item.analysis.action)}
									</span>
									<span class="text-xs text-[var(--color-text-tertiary)]">
										{formatRelativeTime(item.queued_at)}
									</span>
								</div>
								<h3 class="text-lg font-semibold text-[var(--color-text-primary)] truncate">
									{item.metadata.subject}
								</h3>
							</div>
							<!-- Status badge for non-pending -->
							{#if item.status !== 'pending'}
								<span
									class="text-xs px-2 py-1 rounded-full shrink-0"
									class:bg-green-100={item.status === 'approved'}
									class:text-green-700={item.status === 'approved'}
									class:bg-red-100={item.status === 'rejected'}
									class:text-red-700={item.status === 'rejected'}
								>
									{item.status === 'approved' ? 'Approuvé' : 'Rejeté'}
								</span>
							{/if}
						</div>

						<!-- Sender -->
						<p class="text-sm text-[var(--color-text-secondary)]">
							De : <span class="font-medium">{item.metadata.from_name || item.metadata.from_address}</span>
							{#if item.metadata.from_name}
								<span class="text-[var(--color-text-tertiary)]">&lt;{item.metadata.from_address}&gt;</span>
							{/if}
						</p>

						<!-- Preview -->
						{#if item.content?.preview}
							<p class="text-sm text-[var(--color-text-tertiary)] line-clamp-2">
								{item.content.preview}
							</p>
						{/if}

						<!-- Analysis -->
						<div
							class="flex items-center gap-4 text-sm p-2 rounded-lg bg-[var(--color-bg-tertiary)]"
						>
							<div class="flex items-center gap-1">
								<span class="text-[var(--color-text-tertiary)]">Confiance :</span>
								<span style="color: {getConfidenceColor(item.analysis.confidence)}">
									{Math.round(item.analysis.confidence * 100)}%
								</span>
							</div>
							{#if item.analysis.category}
								<div class="flex items-center gap-1">
									<span class="text-[var(--color-text-tertiary)]">Catégorie :</span>
									<span class="text-[var(--color-text-primary)]">{item.analysis.category}</span>
								</div>
							{/if}
						</div>

						<!-- Reasoning -->
						{#if item.analysis.reasoning}
							<p class="text-xs text-[var(--color-text-tertiary)] italic">
								"{item.analysis.reasoning}"
							</p>
						{/if}

						<!-- Actions (only for pending items) -->
						{#if item.status === 'pending'}
							<div class="flex gap-2 pt-2 border-t border-[var(--color-border)]">
								<Button variant="primary" size="sm" onclick={() => handleApprove(item)}>
									Approuver
								</Button>
								<Button variant="secondary" size="sm" onclick={() => handleReject(item)}>
									Rejeter
								</Button>
							</div>
						{/if}
					</div>
				</Card>
			{/each}

			<!-- Load more -->
			{#if queueStore.hasMore}
				<div class="text-center pt-4">
					<Button variant="secondary" onclick={() => queueStore.loadMore()} disabled={queueStore.loading}>
						{#if queueStore.loading}
							Chargement...
						{:else}
							Charger plus
						{/if}
					</Button>
				</div>
			{/if}
		</section>
	{/if}
</div>
