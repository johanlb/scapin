<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { notesReviewStore } from '$lib/stores/notes-review.svelte';
	import { getNote, updateNote, deleteNote, type Note } from '$lib/api/client';
	import ReviewCard from '$lib/components/notes/ReviewCard.svelte';
	import QualityRating from '$lib/components/notes/QualityRating.svelte';
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';
	import MarkdownEditor from '$lib/components/notes/MarkdownEditor.svelte';
	import { Modal } from '$lib/components/ui';

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
						goto('/');
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
			// Navigate to /memoires/{note_id} - the [...path] route extracts noteId from the last segment
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
			// Load full note content
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

			// Check if all done
			if (notesReviewStore.isEmpty) {
				reviewComplete = true;
			}
		} catch (error) {
			console.error('Failed to delete note:', error);
		} finally {
			isDeleting = false;
		}
	}
</script>

<svelte:head>
	<title>Revision des notes - Scapin</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-950">
	<!-- Header -->
	<header
		class="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-800"
	>
		<div class="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
			<button
				type="button"
				onclick={() => goto('/')}
				class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
			>
				<span>←</span>
				<span class="text-sm">Retour</span>
			</button>

			{#if !notesReviewStore.isEmpty && !reviewComplete}
				<div class="flex items-center gap-3">
					<span class="text-sm text-gray-600 dark:text-gray-400">
						{notesReviewStore.progress.current}/{notesReviewStore.progress.total}
					</span>
					<ProgressRing
						percent={notesReviewStore.progress.percent}
						size={32}
						strokeWidth={3}
						showLabel={false}
						color="primary"
					/>
				</div>
			{/if}
		</div>
	</header>

	<main class="max-w-2xl mx-auto px-4 py-6">
		<!-- Loading State -->
		{#if notesReviewStore.loading && notesReviewStore.dueNotes.length === 0}
			<div class="flex flex-col items-center justify-center py-20">
				<div
					class="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"
				></div>
				<p class="text-gray-600 dark:text-gray-400">Chargement des notes...</p>
			</div>

			<!-- Empty State (no notes due) -->
		{:else if notesReviewStore.isEmpty && !reviewComplete}
			<div class="flex flex-col items-center justify-center py-20 text-center">
				<p class="text-5xl mb-4">🎉</p>
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
					Aucune note à réviser
				</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-6">
					Toutes vos notes sont à jour. Revenez plus tard !
				</p>
				<button
					type="button"
					onclick={() => goto('/')}
					class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
				>
					Retour au tableau de bord
				</button>
			</div>

			<!-- Review Complete State -->
		{:else if reviewComplete}
			<div class="flex flex-col items-center justify-center py-20 text-center">
				<p class="text-5xl mb-4">✨</p>
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
					Session terminée !
				</h2>
				<p class="text-gray-600 dark:text-gray-400 mb-2">
					Vous avez révisé {notesReviewStore.reviewedThisSession} notes
				</p>
				{#if notesReviewStore.stats}
					<p class="text-sm text-gray-500 dark:text-gray-500 mb-6">
						Total aujourd'hui : {notesReviewStore.stats.reviewed_today} notes
					</p>
				{/if}
				<div class="flex gap-3">
					<button
						type="button"
						onclick={handleStartNew}
						class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
					>
						Continuer
					</button>
					<button
						type="button"
						onclick={() => goto('/')}
						class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
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
					<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
						<div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
							<h2 class="font-medium text-gray-900 dark:text-white">
								Modifier la note
							</h2>
							<div class="flex gap-2">
								<button
									type="button"
									onclick={handleCancelEdit}
									class="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
								>
									Annuler
								</button>
								<button
									type="button"
									onclick={handleSaveEdit}
									disabled={isSaving}
									class="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
								>
									{#if isSaving}
										Enregistrement...
									{:else}
										Enregistrer
									{/if}
								</button>
							</div>
						</div>
						<div class="p-4">
							<MarkdownEditor
								bind:content={editContent}
								onSave={handleSaveEdit}
							/>
						</div>
					</div>
				{:else}
					<!-- Review Card -->
					<ReviewCard note={notesReviewStore.currentNote} onViewNote={handleViewNote} />
				{/if}

				<!-- Success feedback -->
				{#if lastReviewResult}
					<div
						class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800 text-center"
					>
						<p class="text-sm text-green-700 dark:text-green-400">
							Note enregistrée : {lastReviewResult.assessment}
						</p>
					</div>
				{/if}

				<!-- Quality Rating -->
				<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
					<QualityRating onRate={handleRate} disabled={notesReviewStore.loading} />
				</div>

				<!-- Action Buttons -->
				{#if !isEditing}
					<div class="flex items-center justify-between">
						<div class="flex gap-2">
							<button
								type="button"
								onclick={handlePostpone}
								disabled={notesReviewStore.loading}
								class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors disabled:opacity-50"
							>
								Reporter +24h (s)
							</button>
							<button
								type="button"
								onclick={handleEdit}
								disabled={notesReviewStore.loading}
								class="px-3 py-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors disabled:opacity-50"
								title="Modifier (e)"
							>
								✏️ Modifier
							</button>
							<button
								type="button"
								onclick={handleDeleteClick}
								disabled={notesReviewStore.loading}
								class="px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors disabled:opacity-50"
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
									class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
								>
									← Précédent
								</button>
							{/if}
							{#if notesReviewStore.hasNext}
								<button
									type="button"
									onclick={() => notesReviewStore.skipNote()}
									class="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
								>
									Passer →
								</button>
							{/if}
						</div>
					</div>

					<!-- Keyboard shortcuts hint -->
					<p class="text-xs text-gray-500 dark:text-gray-500 text-center">
						Raccourcis : 1-6 noter | ← → naviguer | s reporter | e modifier | d supprimer | Esc quitter
					</p>
				{/if}
			</div>
		{/if}

		<!-- Error State -->
		{#if notesReviewStore.error}
			<div class="mt-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
				<p class="text-sm text-red-700 dark:text-red-400">{notesReviewStore.error}</p>
				<button
					type="button"
					onclick={() => notesReviewStore.clearError()}
					class="mt-2 text-xs text-red-600 dark:text-red-500 underline"
				>
					Fermer
				</button>
			</div>
		{/if}
	</main>

	<!-- Delete Confirmation Modal -->
	<Modal
		open={showDeleteModal}
		title="Supprimer la note"
		onClose={() => showDeleteModal = false}
	>
		<div class="space-y-4">
			<p class="text-gray-600 dark:text-gray-400">
				Êtes-vous sûr de vouloir supprimer cette note ? Cette action est irréversible.
			</p>
			{#if notesReviewStore.currentNote}
				<div class="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
					<p class="font-medium text-gray-900 dark:text-white text-sm truncate">
						{notesReviewStore.currentNote.note_id}
					</p>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Type: {notesReviewStore.currentNote.note_type}
					</p>
				</div>
			{/if}
			<div class="flex gap-3 justify-end">
				<button
					type="button"
					onclick={() => showDeleteModal = false}
					class="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
				>
					Annuler
				</button>
				<button
					type="button"
					onclick={handleConfirmDelete}
					disabled={isDeleting}
					class="px-4 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
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
