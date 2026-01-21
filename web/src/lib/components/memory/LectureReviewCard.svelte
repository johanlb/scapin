<script lang="ts">
	/**
	 * LectureReviewCard Component
	 * Enhanced review card for lecture sessions with quality score and questions
	 */
	import type { LectureSession } from '$lib/api/types/memory-cycles';
	import { Card, Badge } from '$lib/components/ui';
	import MarkdownPreview from '$lib/components/notes/MarkdownPreview.svelte';
	import QualityScoreDisplay from './QualityScoreDisplay.svelte';
	import QuestionsForm from './QuestionsForm.svelte';

	interface Props {
		session: LectureSession;
		recentlyImproved?: boolean;
		onViewNote?: () => void;
		onAnswerQuestions?: (answers: Record<string, string>) => void;
	}

	let { session, recentlyImproved = false, onViewNote, onAnswerQuestions }: Props = $props();

	// Note type icons
	const typeIcons: Record<string, string> = {
		personne: '👤',
		organisation: '🏢',
		projet: '📁',
		concept: '💡',
		lieu: '📍',
		evenement: '📅',
		produit: '📦',
		default: '📝'
	};

	// Extract note type from title or use default
	const noteType = $derived('default');
	const icon = $derived(typeIcons[noteType] || typeIcons.default);
</script>

<div class="space-y-4">
	<!-- Main card -->
	<Card variant="glass">
		<!-- Header -->
		<div class="flex items-start justify-between mb-4">
			<div class="flex items-center gap-3">
				<div class="w-12 h-12 rounded-xl bg-[var(--glass-subtle)] flex items-center justify-center text-2xl">
					{icon}
				</div>
				<div>
					<h2 class="font-semibold text-[var(--color-text-primary)] text-lg">
						{session.note_title}
					</h2>
					<div class="flex items-center gap-2 mt-1">
						{#if recentlyImproved}
							<Badge class="bg-purple-500/10 text-purple-500">
								<span class="flex items-center gap-1">
									<span>✨</span>
									<span>Améliorée</span>
								</span>
							</Badge>
						{/if}
						{#if session.questions.length > 0}
							<Badge class="bg-[var(--color-warning)]/10 text-[var(--color-warning)]">
								<span class="flex items-center gap-1">
									<span>❓</span>
									<span>{session.questions.length} questions</span>
								</span>
							</Badge>
						{/if}
					</div>
				</div>
			</div>

			<!-- Quality score -->
			{#if session.quality_score !== null}
				<QualityScoreDisplay score={session.quality_score} size={56} />
			{/if}
		</div>

		<!-- Content preview -->
		<div class="p-4 bg-[var(--glass-subtle)] rounded-xl max-h-[300px] overflow-y-auto">
			<MarkdownPreview content={session.note_content} />
		</div>

		<!-- View full note button -->
		{#if onViewNote}
			<div class="mt-4 flex justify-end">
				<button
					type="button"
					onclick={onViewNote}
					class="text-sm text-[var(--color-accent)] hover:text-[var(--color-accent)]/80 transition-colors"
				>
					Voir la note complète →
				</button>
			</div>
		{/if}
	</Card>

	<!-- Questions section -->
	{#if session.questions.length > 0}
		<QuestionsForm
			questions={session.questions}
			onAnswer={onAnswerQuestions}
		/>
	{/if}
</div>
