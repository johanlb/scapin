<script lang="ts">
	/**
	 * QuestionsForm Component
	 * Form for answering questions during lecture review
	 */
	import { Card, Button } from '$lib/components/ui';

	interface Props {
		questions: string[];
		onAnswer?: (answers: Record<string, string>) => void;
		disabled?: boolean;
	}

	let { questions, onAnswer, disabled = false }: Props = $props();

	// Track answers for each question
	let answers = $state<Record<string, string>>({});

	function handleSubmit() {
		if (onAnswer) {
			onAnswer(answers);
		}
	}

	function updateAnswer(index: number, value: string) {
		answers = { ...answers, [String(index)]: value };
	}

	const hasAnyAnswer = $derived(
		Object.values(answers).some((a) => a.trim().length > 0)
	);
</script>

{#if questions.length > 0}
	<Card variant="glass" class="border-[var(--color-warning)]/30">
		<div class="space-y-4">
			<div class="flex items-center gap-2">
				<span class="text-lg">❓</span>
				<h3 class="font-medium text-[var(--color-text-primary)]">
					Questions pour toi
				</h3>
				<span class="text-xs px-1.5 py-0.5 rounded-full bg-[var(--color-warning)]/10 text-[var(--color-warning)]">
					{questions.length}
				</span>
			</div>

			<div class="space-y-3">
				{#each questions as question, i}
					<div class="space-y-1.5">
						<label
							for="question-{i}"
							class="block text-sm text-[var(--color-text-secondary)]"
						>
							{question}
						</label>
						<textarea
							id="question-{i}"
							class="w-full px-3 py-2 text-sm bg-[var(--glass-subtle)] border border-[var(--glass-border-subtle)] rounded-xl
								text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)]
								focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50 focus:border-transparent
								resize-none transition-all"
							rows="2"
							placeholder="Ta réponse..."
							{disabled}
							value={answers[String(i)] || ''}
							oninput={(e) => updateAnswer(i, e.currentTarget.value)}
						></textarea>
					</div>
				{/each}
			</div>

			{#if hasAnyAnswer}
				<div class="flex justify-end">
					<button
						type="button"
						onclick={handleSubmit}
						{disabled}
						class="px-4 py-2 text-sm bg-[var(--color-accent)] text-white rounded-xl
							hover:bg-[var(--color-accent)]/90 transition-colors disabled:opacity-50
							liquid-press"
					>
						Enregistrer les réponses
					</button>
				</div>
			{/if}

			<p class="text-xs text-[var(--color-text-tertiary)]">
				Ces questions ont été générées par Scapin pour enrichir cette note.
				Tes réponses seront intégrées automatiquement.
			</p>
		</div>
	</Card>
{/if}
