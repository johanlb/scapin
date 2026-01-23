<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { orphanQuestionsStore } from '$lib/stores/orphan-questions.svelte';
	import type { OrphanQuestion } from '$lib/stores/orphan-questions.svelte';
	import { Card, PullToRefresh, Modal } from '$lib/components/ui';
	import { toastStore } from '$lib/stores/toast.svelte';

	// Tab state
	let activeTab = $state<'pending' | 'resolved' | 'by_category'>('pending');

	// Modal state
	let showResolveModal = $state(false);
	let showDeleteModal = $state(false);
	let selectedQuestion = $state<OrphanQuestion | null>(null);
	let resolutionText = $state('');
	let isResolving = $state(false);
	let isDeleting = $state(false);

	// Filtered questions based on tab
	const filteredQuestions = $derived.by(() => {
		switch (activeTab) {
			case 'resolved':
				return orphanQuestionsStore.resolvedQuestions;
			case 'by_category':
			case 'pending':
			default:
				return orphanQuestionsStore.pendingQuestions;
		}
	});

	const groupByCategory = $derived(activeTab === 'by_category');

	onMount(async () => {
		await orphanQuestionsStore.fetchQuestions(true);
	});

	async function handleRefresh() {
		await orphanQuestionsStore.fetchQuestions(true);
	}

	function openResolveModal(question: OrphanQuestion) {
		selectedQuestion = question;
		resolutionText = '';
		showResolveModal = true;
	}

	function openDeleteModal(question: OrphanQuestion) {
		selectedQuestion = question;
		showDeleteModal = true;
	}

	async function handleResolve() {
		if (!selectedQuestion) return;

		isResolving = true;
		const success = await orphanQuestionsStore.resolveQuestion(
			selectedQuestion.question_id,
			resolutionText
		);

		if (success) {
			toastStore.success('Question marquee comme resolue');
			showResolveModal = false;
			selectedQuestion = null;
			resolutionText = '';
		} else {
			toastStore.error('Echec de la resolution');
		}
		isResolving = false;
	}

	async function handleDelete() {
		if (!selectedQuestion) return;

		isDeleting = true;
		const success = await orphanQuestionsStore.deleteQuestion(selectedQuestion.question_id);

		if (success) {
			toastStore.success('Question supprimee');
			showDeleteModal = false;
			selectedQuestion = null;
		} else {
			toastStore.error('Echec de la suppression');
		}
		isDeleting = false;
	}

	// Category info
	function getCategoryInfo(category: string): { icon: string; label: string; color: string } {
		switch (category) {
			case 'decision':
				return { icon: '🎯', label: 'Decision', color: 'text-red-600 dark:text-red-400' };
			case 'processus':
				return { icon: '⚙️', label: 'Processus', color: 'text-blue-600 dark:text-blue-400' };
			case 'organisation':
				return { icon: '📋', label: 'Organisation', color: 'text-amber-600 dark:text-amber-400' };
			case 'structure_pkm':
				return { icon: '🗂️', label: 'Structure PKM', color: 'text-purple-600 dark:text-purple-400' };
			default:
				return { icon: '❓', label: category, color: 'text-gray-600 dark:text-gray-400' };
		}
	}

	// Format relative time
	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / (1000 * 60));
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffMins < 1) return "A l'instant";
		if (diffMins < 60) return `Il y a ${diffMins} min`;
		if (diffHours < 24) return `Il y a ${diffHours}h`;
		if (diffDays === 1) return 'Hier';
		if (diffDays < 7) return `Il y a ${diffDays} jours`;
		return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
	}

	// Tab definitions
	const tabDefs = [
		{ id: 'pending' as const, label: 'En attente' },
		{ id: 'resolved' as const, label: 'Resolues' },
		{ id: 'by_category' as const, label: 'Par categorie' }
	];

	// Grouped questions by category
	const groupedQuestions = $derived.by(() => {
		if (!groupByCategory) return [];

		const categories = orphanQuestionsStore.byCategory;
		const result: { category: string; info: ReturnType<typeof getCategoryInfo>; questions: OrphanQuestion[] }[] = [];

		for (const [category, questions] of Object.entries(categories)) {
			const pending = questions.filter((q) => !q.resolved);
			if (pending.length > 0) {
				result.push({
					category,
					info: getCategoryInfo(category),
					questions: pending
				});
			}
		}

		// Sort by number of questions (most first)
		return result.sort((a, b) => b.questions.length - a.questions.length);
	});
</script>

<svelte:head>
	<title>Questions Orphelines - Scapin</title>
</svelte:head>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<!-- Header -->
	<header
		class="sticky top-0 z-10 bg-[var(--color-bg-primary)]/80 backdrop-blur-md border-b border-[var(--glass-border-subtle)]"
	>
		<div class="max-w-2xl mx-auto px-4 py-3">
			<div class="flex items-center justify-between mb-3">
				<button
					type="button"
					onclick={() => goto('/memoires')}
					class="flex items-center gap-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors liquid-press"
				>
					<span>←</span>
					<span class="text-sm">Retour</span>
				</button>

				<h1 class="text-base font-semibold text-[var(--color-text-primary)]">
					Questions Orphelines
				</h1>

				<button
					type="button"
					onclick={handleRefresh}
					disabled={orphanQuestionsStore.loading}
					class="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors liquid-press disabled:opacity-50"
					aria-label="Rafraichir"
				>
					<span class={orphanQuestionsStore.loading ? 'animate-spin inline-block' : ''}>⟳</span>
				</button>
			</div>

			<!-- Tabs -->
			<div class="flex gap-1 p-1 bg-[var(--glass-subtle)] rounded-xl">
				{#each tabDefs as tab}
					{@const count =
						tab.id === 'resolved'
							? orphanQuestionsStore.resolvedQuestions.length
							: tab.id === 'pending'
								? orphanQuestionsStore.pendingCount
								: orphanQuestionsStore.pendingCount}
					<button
						type="button"
						onclick={() => (activeTab = tab.id)}
						class="flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all
							{activeTab === tab.id
							? 'bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] shadow-sm'
							: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}"
					>
						{tab.label}
						{#if count > 0}
							<span
								class="ml-1 text-xs px-1.5 py-0.5 rounded-full
								{activeTab === tab.id
									? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]'
									: 'bg-[var(--glass-subtle)] text-[var(--color-text-tertiary)]'}"
							>
								{count}
							</span>
						{/if}
					</button>
				{/each}
			</div>
		</div>
	</header>

	<PullToRefresh onrefresh={handleRefresh}>
		<main class="max-w-2xl mx-auto px-4 py-6">
			<!-- Loading State -->
			{#if orphanQuestionsStore.loading && orphanQuestionsStore.questions.length === 0}
				<div class="flex flex-col items-center justify-center py-20">
					<div
						class="w-10 h-10 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mb-4"
					></div>
					<p class="text-[var(--color-text-secondary)]">Chargement des questions...</p>
				</div>

				<!-- Error State -->
			{:else if orphanQuestionsStore.error}
				<Card variant="glass-subtle" class="mb-4" padding="md">
					<div class="flex items-center gap-3 text-red-600 dark:text-red-400">
						<span class="text-lg">⚠️</span>
						<span class="text-sm">{orphanQuestionsStore.error}</span>
					</div>
				</Card>

				<!-- Empty State -->
			{:else if orphanQuestionsStore.isEmpty}
				<div class="flex flex-col items-center justify-center py-20">
					<span class="text-4xl mb-4">✨</span>
					<p class="text-[var(--color-text-secondary)]">Aucune question orpheline</p>
					<p class="text-sm text-[var(--color-text-tertiary)] mt-1">
						Les questions strategiques ont toutes une note cible
					</p>
				</div>

				<!-- Summary Stats -->
			{:else if orphanQuestionsStore.pendingCount > 0 && activeTab !== 'resolved'}
				<Card variant="glass-subtle" class="mb-4" padding="sm">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-2">
							<span class="text-lg">🎯</span>
							<span class="text-sm text-[var(--color-text-secondary)]">
								{orphanQuestionsStore.pendingCount} question{orphanQuestionsStore.pendingCount > 1
									? 's'
									: ''} en attente
							</span>
						</div>
						<span class="text-xs text-[var(--color-text-tertiary)]">
							Questions sans note cible
						</span>
					</div>
				</Card>
			{/if}

			<!-- Questions List -->
			{#if !orphanQuestionsStore.loading || orphanQuestionsStore.questions.length > 0}
				{#if groupByCategory && groupedQuestions.length > 0}
					<!-- Grouped by category -->
					{#each groupedQuestions as group}
						<div class="mb-6">
							<h3
								class="flex items-center gap-2 text-sm font-semibold text-[var(--color-text-secondary)] mb-3"
							>
								<span>{group.info.icon}</span>
								<span class={group.info.color}>{group.info.label}</span>
								<span class="text-xs text-[var(--color-text-tertiary)]">
									({group.questions.length})
								</span>
							</h3>
							<div class="space-y-3">
								{#each group.questions as question}
									{@render questionCard(question)}
								{/each}
							</div>
						</div>
					{/each}
				{:else if filteredQuestions.length > 0}
					<!-- Flat list -->
					<div class="space-y-3">
						{#each filteredQuestions as question}
							{@render questionCard(question)}
						{/each}
					</div>
				{:else if activeTab === 'resolved' && orphanQuestionsStore.resolvedQuestions.length === 0}
					<div class="flex flex-col items-center justify-center py-12">
						<span class="text-3xl mb-3">📭</span>
						<p class="text-[var(--color-text-tertiary)]">Aucune question resolue</p>
					</div>
				{:else if activeTab === 'pending' && orphanQuestionsStore.pendingCount === 0}
					<div class="flex flex-col items-center justify-center py-12">
						<span class="text-3xl mb-3">✨</span>
						<p class="text-[var(--color-text-tertiary)]">Toutes les questions sont resolues</p>
					</div>
				{/if}
			{/if}
		</main>
	</PullToRefresh>
</div>

<!-- Question Card Snippet -->
{#snippet questionCard(question: OrphanQuestion)}
	{@const categoryInfo = getCategoryInfo(question.category)}

	<Card variant="glass" padding="md" class="relative">
		<!-- Category Badge -->
		<div class="flex items-center gap-2 mb-2">
			<span
				class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-[var(--glass-subtle)] {categoryInfo.color}"
			>
				<span>{categoryInfo.icon}</span>
				<span>{categoryInfo.label}</span>
			</span>
			{#if question.resolved}
				<span
					class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
				>
					✓ Resolue
				</span>
			{/if}
		</div>

		<!-- Question Text -->
		<p class="text-[var(--color-text-primary)] font-medium mb-2">
			{question.question}
		</p>

		<!-- Context (collapsible if long) -->
		{#if question.context}
			<details class="mb-3">
				<summary
					class="text-sm text-[var(--color-text-secondary)] cursor-pointer hover:text-[var(--color-text-primary)]"
				>
					Contexte
				</summary>
				<p class="text-sm text-[var(--color-text-tertiary)] mt-1 pl-4 border-l-2 border-[var(--glass-border-subtle)]">
					{question.context}
				</p>
			</details>
		{/if}

		<!-- Metadata -->
		<div class="flex flex-wrap items-center gap-3 text-xs text-[var(--color-text-tertiary)] mb-3">
			<span class="flex items-center gap-1">
				<span>📧</span>
				<span class="truncate max-w-[200px]">{question.source_email_subject}</span>
			</span>
			{#if question.intended_target}
				<span class="flex items-center gap-1">
					<span>📁</span>
					<span>Cible: {question.intended_target}</span>
				</span>
			{/if}
			<span class="flex items-center gap-1">
				<span>⏰</span>
				<span>{formatRelativeTime(question.created_at)}</span>
			</span>
		</div>

		<!-- Resolution (if resolved) -->
		{#if question.resolved && question.resolution}
			<div
				class="mb-3 p-2 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
			>
				<p class="text-sm text-green-700 dark:text-green-300">
					<strong>Resolution:</strong> {question.resolution}
				</p>
			</div>
		{/if}

		<!-- Actions -->
		<div class="flex items-center justify-end gap-2">
			{#if !question.resolved}
				<button
					type="button"
					onclick={() => openResolveModal(question)}
					class="px-3 py-1.5 text-sm rounded-lg bg-[var(--color-accent)]/10 text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 transition-colors"
				>
					✓ Resoudre
				</button>
			{/if}
			<button
				type="button"
				onclick={() => openDeleteModal(question)}
				class="px-3 py-1.5 text-sm rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
			>
				Supprimer
			</button>
		</div>
	</Card>
{/snippet}

<!-- Resolve Modal -->
<Modal bind:open={showResolveModal} title="Resoudre la question" size="sm">
	{#if selectedQuestion}
		<p class="text-[var(--color-text-secondary)] mb-4">
			<strong>Question:</strong> {selectedQuestion.question}
		</p>
		<div class="mb-6">
			<label for="resolution" class="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
				Resolution (optionnel)
			</label>
			<textarea
				id="resolution"
				bind:value={resolutionText}
				placeholder="Comment avez-vous resolu cette question ?"
				rows="3"
				class="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50 resize-none"
			></textarea>
		</div>
		<div class="flex justify-end gap-3">
			<button
				type="button"
				onclick={() => (showResolveModal = false)}
				class="px-4 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors text-[var(--color-text-primary)]"
			>
				Annuler
			</button>
			<button
				type="button"
				onclick={handleResolve}
				disabled={isResolving}
				class="px-4 py-2 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent)]/90 text-white transition-colors disabled:opacity-50"
			>
				{#if isResolving}
					Resolution...
				{:else}
					Confirmer
				{/if}
			</button>
		</div>
	{/if}
</Modal>

<!-- Delete Modal -->
<Modal bind:open={showDeleteModal} title="Supprimer la question" size="sm">
	{#if selectedQuestion}
		<p class="text-[var(--color-text-secondary)] mb-6">
			Etes-vous sur de vouloir supprimer cette question ? Cette action est irreversible.
		</p>
		<div class="flex justify-end gap-3">
			<button
				type="button"
				onclick={() => (showDeleteModal = false)}
				class="px-4 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors text-[var(--color-text-primary)]"
			>
				Annuler
			</button>
			<button
				type="button"
				onclick={handleDelete}
				disabled={isDeleting}
				class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors disabled:opacity-50"
			>
				{#if isDeleting}
					Suppression...
				{:else}
					Supprimer
				{/if}
			</button>
		</div>
	{/if}
</Modal>
