<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { memoryCyclesStore } from '$lib/stores/memory-cycles.svelte';
	import FilageProgressHeader from '$lib/components/memory/FilageProgressHeader.svelte';
	import FilageSection from '$lib/components/memory/FilageSection.svelte';
	import FilageLectureCard from '$lib/components/memory/FilageLectureCard.svelte';
	import LectureReviewCard from '$lib/components/memory/LectureReviewCard.svelte';
	import QualityRating from '$lib/components/notes/QualityRating.svelte';
	import { Card, PullToRefresh } from '$lib/components/ui';
	import { REASON_ICONS, REASON_LABELS } from '$lib/api/types/memory-cycles';

	// Session mode: list or review
	let mode = $state<'list' | 'review'>('list');
	let lastResult = $state<{ quality: number; message: string } | null>(null);
	let questionAnswers = $state<Record<string, string>>({});

	onMount(async () => {
		await memoryCyclesStore.fetchFilage(20);
	});

	// Format date for display
	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('fr-FR', {
			weekday: 'long',
			day: 'numeric',
			month: 'long'
		});
	}

	// Get today's date formatted
	const todayFormatted = $derived(
		memoryCyclesStore.filage
			? formatDate(memoryCyclesStore.filage.date)
			: formatDate(new Date().toISOString())
	);

	// Actions
	async function handleRefresh() {
		await memoryCyclesStore.fetchFilage(20);
	}

	async function handleStartSession() {
		const lecture = memoryCyclesStore.currentLecture;
		if (!lecture) return;

		const session = await memoryCyclesStore.startSession(lecture.note_id);
		if (session) {
			mode = 'review';
		}
	}

	async function handleRate(quality: number) {
		const result = await memoryCyclesStore.completeSession(quality, questionAnswers);
		if (result) {
			lastResult = {
				quality: result.quality_rating,
				message: result.success ? 'Lecture terminée' : 'Erreur'
			};
			questionAnswers = {};

			// Return to list mode if done, or show next
			if (memoryCyclesStore.isEmpty) {
				mode = 'list';
			} else if (!memoryCyclesStore.hasNext) {
				mode = 'list';
			}

			// Clear result after 2s
			setTimeout(() => {
				lastResult = null;
			}, 2000);
		}
	}

	function handleSelectLecture(index: number) {
		memoryCyclesStore.goToLecture(index);
	}

	function handleBack() {
		if (mode === 'review') {
			mode = 'list';
		} else {
			goto('/memoires');
		}
	}

	function handleAnswerQuestions(answers: Record<string, string>) {
		questionAnswers = answers;
	}

	// Grouped lectures
	const lecturesByCategory = $derived(memoryCyclesStore.lecturesByCategory);
</script>

<svelte:head>
	<title>Filage - Scapin</title>
</svelte:head>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<FilageProgressHeader
		title="Filage du {todayFormatted}"
		current={memoryCyclesStore.completedToday}
		total={memoryCyclesStore.totalLectures}
		onBack={handleBack}
		onRefresh={handleRefresh}
		loading={memoryCyclesStore.loading}
	/>

	<PullToRefresh onrefresh={handleRefresh}>
		<main class="max-w-2xl mx-auto px-4 py-6">
			<!-- Loading State -->
			{#if memoryCyclesStore.loading && !memoryCyclesStore.filage}
				<div class="flex flex-col items-center justify-center py-20">
					<div
						class="w-10 h-10 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mb-4"
					></div>
					<p class="text-[var(--color-text-secondary)]">Chargement du filage...</p>
				</div>

			<!-- Empty State -->
			{:else if memoryCyclesStore.isEmpty}
				<div class="flex flex-col items-center justify-center py-20 text-center">
					<p class="text-5xl mb-4">🎉</p>
					<h2 class="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
						Aucune lecture aujourd'hui
					</h2>
					<p class="text-[var(--color-text-secondary)] mb-6">
						Votre mémoire est à jour. Revenez demain !
					</p>
					<button
						type="button"
						onclick={() => goto('/memoires')}
						class="px-4 py-2 bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent)]/90 transition-colors liquid-press"
					>
						Retour aux mémoires
					</button>
				</div>

			<!-- Review Mode -->
			{:else if mode === 'review' && memoryCyclesStore.currentSession}
				<div class="space-y-6">
					<!-- Lecture card -->
					<LectureReviewCard
						session={memoryCyclesStore.currentSession}
						recentlyImproved={memoryCyclesStore.currentLecture?.reason.includes('Améliorée')}
						onViewNote={() => goto(`/memoires/${encodeURIComponent(memoryCyclesStore.currentSession?.note_id ?? '')}`)}
						onAnswerQuestions={handleAnswerQuestions}
					/>

					<!-- Success feedback -->
					{#if lastResult}
						<div
							class="p-3 bg-green-500/10 rounded-xl border border-green-500/30 text-center animate-fade-in"
						>
							<p class="text-sm text-green-600 dark:text-green-400">
								{lastResult.message}
							</p>
						</div>
					{/if}

					<!-- Quality Rating -->
					<Card variant="glass">
						<QualityRating onRate={handleRate} disabled={memoryCyclesStore.loading} />
					</Card>

					<!-- Navigation -->
					<div class="flex items-center justify-between">
						<button
							type="button"
							onclick={() => { mode = 'list'; }}
							class="px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
						>
							← Retour à la liste
						</button>

						<div class="flex gap-2">
							{#if memoryCyclesStore.hasPrevious}
								<button
									type="button"
									onclick={() => { memoryCyclesStore.previousLecture(); handleStartSession(); }}
									class="px-3 py-2 text-sm border border-[var(--glass-border-subtle)] rounded-xl hover:bg-[var(--glass-subtle)] transition-colors liquid-press"
								>
									← Précédent
								</button>
							{/if}
							{#if memoryCyclesStore.hasNext}
								<button
									type="button"
									onclick={() => { memoryCyclesStore.skipLecture(); handleStartSession(); }}
									class="px-3 py-2 text-sm border border-[var(--glass-border-subtle)] rounded-xl hover:bg-[var(--glass-subtle)] transition-colors liquid-press"
								>
									Passer →
								</button>
							{/if}
						</div>
					</div>

					<!-- Keyboard shortcuts hint -->
					<p class="text-xs text-[var(--color-text-tertiary)] text-center">
						Raccourcis : 1-6 noter | ← → naviguer | Esc liste
					</p>
				</div>

			<!-- List Mode -->
			{:else if memoryCyclesStore.filage}
				<div class="space-y-4">
					<!-- Summary stats -->
					<div class="grid grid-cols-3 gap-2 mb-4">
						<Card padding="sm">
							<div class="text-center">
								<p class="text-2xl font-bold text-[var(--color-accent)]">
									{memoryCyclesStore.filage.total_lectures}
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Lectures</p>
							</div>
						</Card>
						<Card padding="sm">
							<div class="text-center">
								<p class="text-2xl font-bold text-[var(--color-event-calendar)]">
									{memoryCyclesStore.filage.events_today}
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Événements</p>
							</div>
						</Card>
						<Card padding="sm">
							<div class="text-center">
								<p class="text-2xl font-bold text-[var(--color-warning)]">
									{memoryCyclesStore.filage.notes_with_questions}
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Questions</p>
							</div>
						</Card>
					</div>

					<!-- Sections grouped by category -->
					{#if lecturesByCategory.questions_pending?.length > 0}
						<FilageSection
							title={REASON_LABELS.questions_pending}
							icon={REASON_ICONS.questions_pending}
							count={lecturesByCategory.questions_pending.length}
						>
							{#each lecturesByCategory.questions_pending as lecture, i}
								{@const globalIndex = memoryCyclesStore.filage?.lectures.findIndex(l => l.note_id === lecture.note_id) ?? 0}
								<FilageLectureCard
									{lecture}
									selected={memoryCyclesStore.currentIndex === globalIndex}
									onclick={() => handleSelectLecture(globalIndex)}
								/>
							{/each}
						</FilageSection>
					{/if}

					{#if lecturesByCategory.event_related?.length > 0}
						<FilageSection
							title={REASON_LABELS.event_related}
							icon={REASON_ICONS.event_related}
							count={lecturesByCategory.event_related.length}
						>
							{#each lecturesByCategory.event_related as lecture}
								{@const globalIndex = memoryCyclesStore.filage?.lectures.findIndex(l => l.note_id === lecture.note_id) ?? 0}
								<FilageLectureCard
									{lecture}
									selected={memoryCyclesStore.currentIndex === globalIndex}
									onclick={() => handleSelectLecture(globalIndex)}
								/>
							{/each}
						</FilageSection>
					{/if}

					{#if lecturesByCategory.sm2_due?.length > 0}
						<FilageSection
							title={REASON_LABELS.sm2_due}
							icon={REASON_ICONS.sm2_due}
							count={lecturesByCategory.sm2_due.length}
						>
							{#each lecturesByCategory.sm2_due as lecture}
								{@const globalIndex = memoryCyclesStore.filage?.lectures.findIndex(l => l.note_id === lecture.note_id) ?? 0}
								<FilageLectureCard
									{lecture}
									selected={memoryCyclesStore.currentIndex === globalIndex}
									onclick={() => handleSelectLecture(globalIndex)}
								/>
							{/each}
						</FilageSection>
					{/if}

					{#if lecturesByCategory.recently_improved?.length > 0}
						<FilageSection
							title={REASON_LABELS.recently_improved}
							icon={REASON_ICONS.recently_improved}
							count={lecturesByCategory.recently_improved.length}
						>
							{#each lecturesByCategory.recently_improved as lecture}
								{@const globalIndex = memoryCyclesStore.filage?.lectures.findIndex(l => l.note_id === lecture.note_id) ?? 0}
								<FilageLectureCard
									{lecture}
									selected={memoryCyclesStore.currentIndex === globalIndex}
									onclick={() => handleSelectLecture(globalIndex)}
								/>
							{/each}
						</FilageSection>
					{/if}

					<!-- Start session button -->
					<div class="sticky bottom-4 pt-4">
						<button
							type="button"
							onclick={handleStartSession}
							disabled={memoryCyclesStore.loading || !memoryCyclesStore.currentLecture}
							class="w-full py-3 bg-[var(--color-accent)] text-white rounded-xl font-medium
								hover:bg-[var(--color-accent)]/90 transition-colors disabled:opacity-50
								shadow-lg liquid-press"
						>
							{#if memoryCyclesStore.currentLecture}
								Commencer avec "{memoryCyclesStore.currentLecture.note_title}"
							{:else}
								Sélectionnez une lecture
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<!-- Error State -->
			{#if memoryCyclesStore.error}
				<div class="mt-4 p-4 bg-red-500/10 rounded-xl border border-red-500/30">
					<p class="text-sm text-red-600 dark:text-red-400">{memoryCyclesStore.error}</p>
					<button
						type="button"
						onclick={() => memoryCyclesStore.clearError()}
						class="mt-2 text-xs text-red-500 underline"
					>
						Fermer
					</button>
				</div>
			{/if}
		</main>
	</PullToRefresh>
</div>

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-fade-in {
		animation: fade-in 0.2s ease-out;
	}
</style>
