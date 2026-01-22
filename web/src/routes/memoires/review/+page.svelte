<script lang="ts">
	/**
	 * Notes Review Page
	 * v3.1: Harmonized with Memory Cycles - Liquid Glass design
	 */
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { notesReviewStore } from '$lib/stores/notes-review.svelte';
	import { getNote, updateNote, deleteNote, type Note } from '$lib/api/client';
	import ReviewCard from '$lib/components/notes/ReviewCard.svelte';
	import QualityRating from '$lib/components/notes/QualityRating.svelte';
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';
	import MarkdownEditor from '$lib/components/notes/MarkdownEditor.svelte';
	import { Card, Modal, PullToRefresh } from '$lib/components/ui';
	import FilageProgressHeader from '$lib/components/memory/FilageProgressHeader.svelte';

	let reviewComplete = $state(false);
	let lastReviewResult = $state<{ quality: number; assessment: string } | null>(null);

	// Edit state
	let isEditing = $state(false);
	let editContent = $state('');
	let isSaving = $state(false);
	let fullNote = $state<Note | null>(null);

	// Delete state
	let showDeleteModal = $state(false);
	let isDeleting = $state(false);

	onMount(async () => {
		await notesReviewStore.fetchAll();
	});

	// Keyboard shortcuts using $effect for proper cleanup
	$effect(() => {
		if (typeof window === 'undefined') return;

		const handleKeydown = (e: KeyboardEvent) => {
			// Ignore if in input/textarea
			if (
				e.target instanceof HTMLInputElement ||
				e.target instanceof HTMLTextAreaElement
			) {
				return;
			}

			switch (e.key) {
				case 'Escape':
					e.preventDefault();
					if (isEditing) {
						handleCancelEdit();
					} else {
						goto('/memoires');
					}
					break;
				case 'ArrowRight':
				case 'n':
					if (!isEditing) {
						e.preventDefault();
						if (notesReviewStore.hasNext) notesReviewStore.skipNote();
					}
					break;
				case 'ArrowLeft':
				case 'p':
					if (!isEditing) {
						e.preventDefault();
						if (notesReviewStore.hasPrevious) notesReviewStore.previousNote();
					}
					break;
				case 's':
					if (!isEditing) {
						e.preventDefault();
						handlePostpone();
					}
					break;
				case 'e':
					if (!isEditing) {
						e.preventDefault();
						handleEdit();
					}
					break;
				case 'd':
					if (!isEditing) {
						e.preventDefault();
						handleDeleteClick();
					}
					break;
			}
		};

		window.addEventListener('keydown', handleKeydown);
		return () => window.removeEventListener('keydown', handleKeydown);
	});

	async function handleRate(quality: number) {
		const result = await notesReviewStore.submitReview(quality);
		if (result) {
			lastReviewResult = {
				quality: result.quality,
				assessment: result.quality_assessment
			};

			// Check if all done
			if (notesReviewStore.isEmpty) {
				reviewComplete = true;
			}

			// Clear result after 2s
			setTimeout(() => {
				lastReviewResult = null;
			}, 2000);
		}
	}

	async function handlePostpone() {
		await notesReviewStore.postponeCurrentNote(24);
		if (notesReviewStore.isEmpty) {
			reviewComplete = true;
		}
	}

	function handleViewNote() {
		const note = notesReviewStore.currentNote;
		if (note) {
			goto(`/memoires/${encodeURIComponent(note.note_id)}`);
		}
	}

	function handleStartNew() {
		notesReviewStore.resetSession();
		notesReviewStore.fetchAll();
		reviewComplete = false;
	}

	async function handleEdit() {
		const note = notesReviewStore.currentNote;
		if (!note) return;

		try {
			fullNote = await getNote(note.note_id);
			editContent = fullNote.content;
			isEditing = true;
		} catch (error) {
			console.error('Failed to load note for editing:', error);
		}
	}

	async function handleSaveEdit() {
		if (!fullNote) return;

		isSaving = true;
		try {
			await updateNote(fullNote.note_id, { content: editContent });
			isEditing = false;
			editContent = '';
			fullNote = null;
		} catch (error) {
			console.error('Failed to save note:', error);
		} finally {
			isSaving = false;
		}
	}

	function handleCancelEdit() {
		isEditing = false;
		editContent = '';
		fullNote = null;
	}

	function handleDeleteClick() {
		showDeleteModal = true;
	}

	async function handleConfirmDelete() {
		const note = notesReviewStore.currentNote;
		if (!note) return;

		isDeleting = true;
		try {
			await deleteNote(note.note_id);
			notesReviewStore.removeNote(note.note_id);
			showDeleteModal = false;

			if (notesReviewStore.isEmpty) {
				reviewComplete = true;
			}
		} catch (error) {
			console.error('Failed to delete note:', error);
		} finally {
			isDeleting = false;
		}
	}

	function handleBack() {
		goto('/memoires');
	}

	async function handleRefresh() {
		await notesReviewStore.fetchAll();
	}
</script>

<svelte:head>
	<title>Revision des notes - Scapin</title>
</svelte:head>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<!-- Header -->
	<FilageProgressHeader
		title="Révision SM-2"
		current={notesReviewStore.reviewedThisSession}
		total={notesReviewStore.totalDue + notesReviewStore.reviewedThisSession}
		onBack={handleBack}
		onRefresh={handleRefresh}
		loading={notesReviewStore.loading}
	/>

	<PullToRefresh onrefresh={handleRefresh}>
		<main class="max-w-2xl mx-auto px-4 py-6">
			<!-- Loading State -->
			{#if notesReviewStore.loading && notesReviewStore.dueNotes.length === 0}
				<div class="flex flex-col items-center justify-center py-20">
					<div
						class="w-10 h-10 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mb-4"
					></div>
					<p class="text-[var(--color-text-secondary)]">Chargement des notes...</p>
				</div>

			<!-- Empty State -->
			{:else if notesReviewStore.isEmpty && !reviewComplete}
				<div class="flex flex-col items-center justify-center py-20 text-center">
					<p class="text-5xl mb-4">🎉</p>
					<h2 class="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
						Aucune note à réviser
					</h2>
					<p class="text-[var(--color-text-secondary)] mb-6">
						Toutes vos notes sont à jour. Revenez plus tard !
					</p>
					<button
						type="button"
						onclick={() => goto('/memoires')}
						class="px-4 py-2 bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent)]/90 transition-colors liquid-press"
					>
						Retour aux mémoires
					</button>
				</div>

			<!-- Review Complete State -->
			{:else if reviewComplete}
				<div class="flex flex-col items-center justify-center py-20 text-center">
					<p class="text-5xl mb-4">✨</p>
					<h2 class="text-xl font-semibold text-[var(--color-text-primary)] mb-2">
						Session terminée !
					</h2>
					<p class="text-[var(--color-text-secondary)] mb-2">
						Vous avez révisé {notesReviewStore.reviewedThisSession} notes
					</p>
					{#if notesReviewStore.stats}
						<p class="text-sm text-[var(--color-text-tertiary)] mb-6">
							Total aujourd'hui : {notesReviewStore.stats.reviewed_today} notes
						</p>
					{/if}
					<div class="flex gap-3">
						<button
							type="button"
							onclick={handleStartNew}
							class="px-4 py-2 bg-[var(--color-accent)] text-white rounded-xl hover:bg-[var(--color-accent)]/90 transition-colors liquid-press"
						>
							Continuer
						</button>
						<button
							type="button"
							onclick={() => goto('/memoires')}
							class="px-4 py-2 border border-[var(--glass-border-subtle)] text-[var(--color-text-secondary)] rounded-xl hover:bg-[var(--glass-subtle)] transition-colors liquid-press"
						>
							Terminer
						</button>
					</div>
				</div>

			<!-- Review Mode -->
			{:else if notesReviewStore.currentNote}
				<div class="space-y-6">
					<!-- Edit Mode -->
					{#if isEditing && fullNote}
						<Card variant="glass">
							<div class="flex items-center justify-between mb-4">
								<h2 class="font-medium text-[var(--color-text-primary)]">
									Modifier la note
								</h2>
								<div class="flex gap-2">
									<button
										type="button"
										onclick={handleCancelEdit}
										class="px-3 py-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
									>
										Annuler
									</button>
									<button
										type="button"
										onclick={handleSaveEdit}
										disabled={isSaving}
										class="px-3 py-1.5 text-sm bg-[var(--color-accent)] text-white rounded-lg hover:bg-[var(--color-accent)]/90 transition-colors disabled:opacity-50"
									>
										{#if isSaving}
											Enregistrement...
										{:else}
											Enregistrer
										{/if}
									</button>
								</div>
							</div>
							<MarkdownEditor
								bind:content={editContent}
								onSave={handleSaveEdit}
							/>
						</Card>
					{:else}
						<!-- Review Card with enrichments -->
						<ReviewCard
							note={notesReviewStore.currentNote}
							onViewNote={handleViewNote}
						/>
					{/if}

					<!-- Success feedback -->
					{#if lastReviewResult}
						<div
							class="p-3 bg-green-500/10 rounded-xl border border-green-500/30 text-center animate-fade-in"
						>
							<p class="text-sm text-green-600 dark:text-green-400">
								Note enregistrée : {lastReviewResult.assessment}
							</p>
						</div>
					{/if}

					<!-- Quality Rating -->
					<Card variant="glass">
						<QualityRating onRate={handleRate} disabled={notesReviewStore.loading} />
					</Card>

					<!-- Action Buttons -->
					{#if !isEditing}
						<div class="flex items-center justify-between">
							<div class="flex gap-2">
								<button
									type="button"
									onclick={handlePostpone}
									disabled={notesReviewStore.loading}
									class="px-3 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors disabled:opacity-50 liquid-press"
								>
									Reporter +24h
								</button>
								<button
									type="button"
									onclick={handleEdit}
									disabled={notesReviewStore.loading}
									class="px-3 py-2 text-sm text-[var(--color-accent)] hover:text-[var(--color-accent)]/80 transition-colors disabled:opacity-50 liquid-press"
									title="Modifier (e)"
								>
									✏️ Modifier
								</button>
								<button
									type="button"
									onclick={handleDeleteClick}
									disabled={notesReviewStore.loading}
									class="px-3 py-2 text-sm text-red-500 hover:text-red-400 transition-colors disabled:opacity-50 liquid-press"
									title="Supprimer (d)"
								>
									🗑️ Supprimer
								</button>
							</div>

							<div class="flex gap-2">
								{#if notesReviewStore.hasPrevious}
									<button
										type="button"
										onclick={() => notesReviewStore.previousNote()}
										class="px-3 py-2 text-sm border border-[var(--glass-border-subtle)] rounded-xl hover:bg-[var(--glass-subtle)] transition-colors liquid-press"
									>
										← Précédent
									</button>
								{/if}
								{#if notesReviewStore.hasNext}
									<button
										type="button"
										onclick={() => notesReviewStore.skipNote()}
										class="px-3 py-2 text-sm border border-[var(--glass-border-subtle)] rounded-xl hover:bg-[var(--glass-subtle)] transition-colors liquid-press"
									>
										Passer →
									</button>
								{/if}
							</div>
						</div>

						<!-- Keyboard shortcuts hint -->
						<p class="text-xs text-[var(--color-text-tertiary)] text-center">
							Raccourcis : 1-6 noter | ← → naviguer | s reporter | e modifier | d supprimer | Esc quitter
						</p>
					{/if}
				</div>
			{/if}

			<!-- Error State -->
			{#if notesReviewStore.error}
				<div class="mt-4 p-4 bg-red-500/10 rounded-xl border border-red-500/30">
					<p class="text-sm text-red-600 dark:text-red-400">{notesReviewStore.error}</p>
					<button
						type="button"
						onclick={() => notesReviewStore.clearError()}
						class="mt-2 text-xs text-red-500 underline"
					>
						Fermer
					</button>
				</div>
			{/if}
		</main>
	</PullToRefresh>

	<!-- Delete Confirmation Modal -->
	<Modal
		open={showDeleteModal}
		title="Supprimer la note"
		onClose={() => showDeleteModal = false}
	>
		<div class="space-y-4">
			<p class="text-[var(--color-text-secondary)]">
				Êtes-vous sûr de vouloir supprimer cette note ? Cette action est irréversible.
			</p>
			{#if notesReviewStore.currentNote}
				<div class="p-3 bg-[var(--glass-subtle)] rounded-xl">
					<p class="font-medium text-[var(--color-text-primary)] text-sm truncate">
						{notesReviewStore.currentNote.note_id}
					</p>
					<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
						Type: {notesReviewStore.currentNote.note_type}
					</p>
				</div>
			{/if}
			<div class="flex gap-3 justify-end">
				<button
					type="button"
					onclick={() => showDeleteModal = false}
					class="px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
				>
					Annuler
				</button>
				<button
					type="button"
					onclick={handleConfirmDelete}
					disabled={isDeleting}
					class="px-4 py-2 text-sm bg-red-500 text-white rounded-xl hover:bg-red-600 transition-colors disabled:opacity-50"
				>
					{#if isDeleting}
						Suppression...
					{:else}
						Supprimer
					{/if}
				</button>
			</div>
		</div>
	</Modal>
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
