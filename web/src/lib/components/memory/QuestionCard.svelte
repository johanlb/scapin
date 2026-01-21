<script lang="ts">
	/**
	 * QuestionCard Component
	 * Card for displaying and answering a single pending question
	 */
	import type { PendingQuestion } from '$lib/api/types/memory-cycles';
	import { Card, Badge } from '$lib/components/ui';

	interface Props {
		question: PendingQuestion;
		onAnswer?: (answer: string) => void;
		onSkip?: () => void;
		disabled?: boolean;
	}

	let { question, onAnswer, onSkip, disabled = false }: Props = $props();

	let answer = $state('');
	let isSubmitting = $state(false);

	async function handleSubmit() {
		if (!answer.trim() || !onAnswer) return;

		isSubmitting = true;
		try {
			await onAnswer(answer.trim());
			answer = '';
		} finally {
			isSubmitting = false;
		}
	}

	// Format relative time
	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffHours / 24);

		if (diffDays > 0) {
			return `il y a ${diffDays}j`;
		} else if (diffHours > 0) {
			return `il y a ${diffHours}h`;
		} else {
			return 'récemment';
		}
	}
</script>

<Card variant="glass" class="border-[var(--color-warning)]/20">
	<div class="space-y-3">
		<!-- Header -->
		<div class="flex items-start justify-between gap-2">
			<div class="flex-1 min-w-0">
				<p class="text-sm font-medium text-[var(--color-text-primary)]">
					{question.question_text}
				</p>
				<div class="flex items-center gap-2 mt-1">
					<Badge class="bg-[var(--glass-subtle)] text-[var(--color-text-tertiary)]">
						{question.note_title}
					</Badge>
					<span class="text-xs text-[var(--color-text-tertiary)]">
						{formatRelativeTime(question.created_at)}
					</span>
				</div>
			</div>
			<span class="text-lg flex-shrink-0">❓</span>
		</div>

		<!-- Answer input -->
		{#if !question.answered}
			<div class="space-y-2">
				<textarea
					class="w-full px-3 py-2 text-sm bg-[var(--glass-subtle)] border border-[var(--glass-border-subtle)] rounded-xl
						text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)]
						focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50 focus:border-transparent
						resize-none transition-all"
					rows="2"
					placeholder="Ta réponse..."
					disabled={disabled || isSubmitting}
					bind:value={answer}
				></textarea>

				<div class="flex items-center justify-end gap-2">
					{#if onSkip}
						<button
							type="button"
							onclick={onSkip}
							disabled={disabled || isSubmitting}
							class="px-3 py-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors disabled:opacity-50"
						>
							Passer
						</button>
					{/if}
					<button
						type="button"
						onclick={handleSubmit}
						disabled={disabled || isSubmitting || !answer.trim()}
						class="px-4 py-1.5 text-sm bg-[var(--color-accent)] text-white rounded-xl
							hover:bg-[var(--color-accent)]/90 transition-colors disabled:opacity-50
							liquid-press"
					>
						{#if isSubmitting}
							<span class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
						{:else}
							Répondre
						{/if}
					</button>
				</div>
			</div>
		{:else}
			<!-- Answered state -->
			<div class="p-3 bg-green-500/10 rounded-xl border border-green-500/20">
				<p class="text-sm text-green-600 dark:text-green-400">
					{question.answer}
				</p>
			</div>
		{/if}
	</div>
</Card>
