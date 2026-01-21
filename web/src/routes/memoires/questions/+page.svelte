<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { memoryCyclesStore } from '$lib/stores/memory-cycles.svelte';
	import QuestionsGroupedList from '$lib/components/memory/QuestionsGroupedList.svelte';
	import { Card, PullToRefresh, Tabs } from '$lib/components/ui';

	// Tab state
	let activeTab = $state<'all' | 'by_note' | 'resolved'>('all');

	// Filtered questions based on tab
	const filteredQuestions = $derived.by(() => {
		const questions = memoryCyclesStore.pendingQuestions;

		switch (activeTab) {
			case 'resolved':
				return questions.filter((q) => q.answered);
			case 'by_note':
			case 'all':
			default:
				return questions.filter((q) => !q.answered);
		}
	});

	const groupByNote = $derived(activeTab === 'by_note');

	onMount(async () => {
		await memoryCyclesStore.fetchPendingQuestions(100);
	});

	async function handleRefresh() {
		await memoryCyclesStore.fetchPendingQuestions(100);
	}

	async function handleAnswer(questionId: string, answer: string) {
		await memoryCyclesStore.answerQuestion(questionId, answer);
	}

	function handleSkip(questionId: string) {
		// Skip just moves to next, no API call needed
		console.log('Skipped question:', questionId);
	}

	// Tab definitions - counts are computed dynamically in the template
	const tabDefs = [
		{ id: 'all' as const, label: 'Toutes' },
		{ id: 'by_note' as const, label: 'Par note' },
		{ id: 'resolved' as const, label: 'Résolues' }
	];

	const resolvedCount = $derived(
		memoryCyclesStore.pendingQuestions.filter((q) => q.answered).length
	);

	const pendingCount = $derived(
		memoryCyclesStore.pendingQuestions.filter((q) => !q.answered).length
	);
</script>

<svelte:head>
	<title>Questions - Scapin</title>
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
					Questions
				</h1>

				<button
					type="button"
					onclick={handleRefresh}
					disabled={memoryCyclesStore.questionsLoading}
					class="p-2 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors liquid-press disabled:opacity-50"
					aria-label="Rafraîchir"
				>
					<span class={memoryCyclesStore.questionsLoading ? 'animate-spin inline-block' : ''}>⟳</span>
				</button>
			</div>

			<!-- Tabs -->
			<div class="flex gap-1 p-1 bg-[var(--glass-subtle)] rounded-xl">
				{#each tabDefs as tab}
					{@const count = tab.id === 'resolved' ? resolvedCount : filteredQuestions.length}
					<button
						type="button"
						onclick={() => activeTab = tab.id}
						class="flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-all
							{activeTab === tab.id
								? 'bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] shadow-sm'
								: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'}"
					>
						{tab.label}
						{#if count > 0}
							<span class="ml-1 text-xs px-1.5 py-0.5 rounded-full
								{activeTab === tab.id
									? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]'
									: 'bg-[var(--glass-subtle)] text-[var(--color-text-tertiary)]'}">
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
			{#if memoryCyclesStore.questionsLoading && memoryCyclesStore.pendingQuestions.length === 0}
				<div class="flex flex-col items-center justify-center py-20">
					<div
						class="w-10 h-10 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mb-4"
					></div>
					<p class="text-[var(--color-text-secondary)]">Chargement des questions...</p>
				</div>

			<!-- Summary stats -->
			{:else if pendingCount > 0 && activeTab !== 'resolved'}
				<Card variant="glass-subtle" class="mb-4" padding="sm">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-2">
							<span class="text-lg">❓</span>
							<span class="text-sm text-[var(--color-text-secondary)]">
								{pendingCount} question{pendingCount > 1 ? 's' : ''} en attente
							</span>
						</div>
						<span class="text-xs text-[var(--color-text-tertiary)]">
							Répondez pour enrichir vos notes
						</span>
					</div>
				</Card>
			{/if}

			<!-- Questions list -->
			<QuestionsGroupedList
				questions={filteredQuestions}
				{groupByNote}
				onAnswer={handleAnswer}
				onSkip={handleSkip}
				disabled={memoryCyclesStore.questionsLoading}
			/>
		</main>
	</PullToRefresh>
</div>
