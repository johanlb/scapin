<script lang="ts">
	/**
	 * QuestionsGroupedList Component
	 * List of questions grouped by note
	 */
	import type { PendingQuestion } from '$lib/api/types/memory-cycles';
	import QuestionCard from './QuestionCard.svelte';
	import { Card } from '$lib/components/ui';

	interface Props {
		questions: PendingQuestion[];
		onAnswer?: (questionId: string, answer: string) => void;
		onSkip?: (questionId: string) => void;
		groupByNote?: boolean;
		disabled?: boolean;
	}

	let { questions, onAnswer, onSkip, groupByNote = true, disabled = false }: Props = $props();

	// Group questions by note
	const groupedQuestions = $derived.by(() => {
		if (!groupByNote) return { '': questions };

		const groups: Record<string, PendingQuestion[]> = {};
		for (const q of questions) {
			const key = q.note_title;
			if (!groups[key]) {
				groups[key] = [];
			}
			groups[key].push(q);
		}
		return groups;
	});

	const groupKeys = $derived(Object.keys(groupedQuestions).sort());

	function handleAnswer(questionId: string) {
		return (answer: string) => {
			if (onAnswer) {
				onAnswer(questionId, answer);
			}
		};
	}

	function handleSkip(questionId: string) {
		return () => {
			if (onSkip) {
				onSkip(questionId);
			}
		};
	}
</script>

{#if questions.length === 0}
	<div class="flex flex-col items-center justify-center py-12 text-center">
		<span class="text-4xl mb-3">🎉</span>
		<h3 class="text-lg font-medium text-[var(--color-text-primary)] mb-1">
			Aucune question en attente
		</h3>
		<p class="text-sm text-[var(--color-text-secondary)]">
			Toutes les questions ont été répondues
		</p>
	</div>
{:else if groupByNote}
	<div class="space-y-6">
		{#each groupKeys as noteTitle}
			{@const noteQuestions = groupedQuestions[noteTitle]}
			<section>
				<!-- Note group header -->
				<div class="flex items-center gap-2 mb-3">
					<span class="text-lg">📝</span>
					<h3 class="font-medium text-[var(--color-text-primary)]">
						{noteTitle}
					</h3>
					<span class="text-xs px-1.5 py-0.5 rounded-full bg-[var(--color-warning)]/10 text-[var(--color-warning)]">
						{noteQuestions.length}
					</span>
				</div>

				<!-- Questions list -->
				<div class="space-y-3">
					{#each noteQuestions as question (question.question_id)}
						<QuestionCard
							{question}
							onAnswer={handleAnswer(question.question_id)}
							onSkip={handleSkip(question.question_id)}
							{disabled}
						/>
					{/each}
				</div>
			</section>
		{/each}
	</div>
{:else}
	<div class="space-y-3">
		{#each questions as question (question.question_id)}
			<QuestionCard
				{question}
				onAnswer={handleAnswer(question.question_id)}
				onSkip={handleSkip(question.question_id)}
				{disabled}
			/>
		{/each}
	</div>
{/if}
