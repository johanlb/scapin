<script lang="ts">
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		getNotesTree,
		syncAppleNotes,
		getNoteSyncStatus,
		listNotes,
		getNote,
		updateNote,
		deleteNote,
		getNoteReviewMetadata,
		triggerReview,
		getNotesDue,
		type Note,
		type FolderNode,
		type NotesTree,
		type NoteSyncStatus,
		type NoteReviewMetadata
	} from '$lib/api/client';
	import MarkdownEditor from '$lib/components/notes/MarkdownEditor.svelte';
	import MarkdownPreview from '$lib/components/notes/MarkdownPreview.svelte';
	import { Modal } from '$lib/components/ui';

	// Loading states
	let isLoading = $state(true);
	let loadError = $state<string | null>(null);
	let isSyncing = $state(false);

	// Sync progress
	let syncStatus = $state<NoteSyncStatus | null>(null);
	let syncProgress = $state<{ current: number; total: number } | null>(null);

	// Data
	let notesData = $state<NotesTree | null>(null);
	let folders = $state<FolderNode[]>([]);

	// Selection state
	let selectedFolderPath = $state<string | null>(null);
	let folderNotes = $state<Note[]>([]);
	let isLoadingNotes = $state(false);
	let selectedNote = $state<Note | null>(null);
	let isLoadingNote = $state(false);

	// Review metadata for selected note
	let noteReviewMetadata = $state<NoteReviewMetadata | null>(null);
	let isLoadingReviewMetadata = $state(false);
	let isTriggering = $state(false);

	// Notes due for review (for indicators)
	let notesDueForReview = $state<Set<string>>(new Set());

	// Editing state
	let isEditing = $state(false);
	let editContent = $state('');
	let isSaving = $state(false);
	let showDeleteModal = $state(false);
	let isDeleting = $state(false);

	// Expanded folders tracking
	let expandedFolders = $state<Set<string>>(new Set());

	// Virtual folder paths
	const ALL_NOTES_PATH = '__all__';
	const DELETED_NOTES_PATH = '__deleted__';

	async function loadTree() {
		isLoading = true;
		loadError = null;
		try {
			notesData = await getNotesTree(10);
			folders = notesData.folders;

			// Load notes due for review
			try {
				const dueResponse = await getNotesDue(100);
				notesDueForReview = new Set(dueResponse.notes.map(n => n.note_id));
			} catch {
				// Ignore errors loading due notes
			}

			// Load sync status
			try {
				syncStatus = await getNoteSyncStatus();
			} catch {
				// Ignore errors
			}

			// Auto-select "All Notes" by default
			if (!selectedFolderPath) {
				await selectFolder(ALL_NOTES_PATH);
			}
		} catch (error) {
			loadError = error instanceof Error ? error.message : 'Erreur de chargement';
		} finally {
			isLoading = false;
		}
	}

	async function selectFolder(path: string) {
		if (selectedFolderPath === path) return;

		selectedFolderPath = path;
		selectedNote = null;
		noteReviewMetadata = null;
		isLoadingNotes = true;

		try {
			let response;
			if (path === ALL_NOTES_PATH) {
				// Load all notes (no folder filter) - increased to 1000 to display all notes
				response = await listNotes(1, 1000);
			} else if (path === DELETED_NOTES_PATH) {
				// For now, deleted notes folder is empty (feature not implemented)
				response = { data: [], total: 0, page: 1, per_page: 1000, pages: 0 };
			} else {
				response = await listNotes(1, 1000, path);
			}
			folderNotes = response.data ?? [];
			// Auto-select first note
			if (folderNotes.length > 0) {
				await selectNote(folderNotes[0]);
			}
		} catch (error) {
			console.error('Failed to load notes:', error);
			folderNotes = [];
		} finally {
			isLoadingNotes = false;
		}
	}

	async function selectNote(note: Note) {
		if (selectedNote?.note_id === note.note_id) return;

		// Cancel any ongoing edit
		if (isEditing) {
			isEditing = false;
			editContent = '';
		}

		isLoadingNote = true;
		noteReviewMetadata = null;

		try {
			selectedNote = await getNote(note.note_id);
			// Load review metadata
			loadReviewMetadata(note.note_id);
		} catch (error) {
			console.error('Failed to load note:', error);
			selectedNote = note; // Fallback to list data
		} finally {
			isLoadingNote = false;
		}
	}

	async function loadReviewMetadata(noteId: string) {
		isLoadingReviewMetadata = true;
		try {
			noteReviewMetadata = await getNoteReviewMetadata(noteId);
		} catch (error) {
			console.error('Failed to load review metadata:', error);
			noteReviewMetadata = null;
		} finally {
			isLoadingReviewMetadata = false;
		}
	}

	function startEditing() {
		if (!selectedNote) return;
		editContent = selectedNote.content;
		isEditing = true;
	}

	function cancelEditing() {
		isEditing = false;
		editContent = '';
	}

	async function saveNote(content: string) {
		if (!selectedNote) return;

		isSaving = true;
		try {
			const updated = await updateNote(selectedNote.note_id, {
				content
			});
			selectedNote = updated;
			isEditing = false;
			editContent = '';
		} catch (error) {
			console.error('Failed to save note:', error);
			throw error;
		} finally {
			isSaving = false;
		}
	}

	async function confirmDelete() {
		if (!selectedNote) return;

		const noteTitle = selectedNote.title;
		isDeleting = true;
		try {
			await deleteNote(selectedNote.note_id);
			// Remove from list
			folderNotes = folderNotes.filter(n => n.note_id !== selectedNote!.note_id);
			selectedNote = null;
			showDeleteModal = false;
			// Show success toast
			toastStore.success(`Note "${noteTitle}" supprimée`);
			// Select next note if available
			if (folderNotes.length > 0) {
				await selectNote(folderNotes[0]);
			}
		} catch (error) {
			console.error('Failed to delete note:', error);
			toastStore.error(`Échec de la suppression de la note`);
		} finally {
			isDeleting = false;
		}
	}

	async function handleTriggerReview() {
		if (!selectedNote || isTriggering) return;

		isTriggering = true;
		try {
			await triggerReview(selectedNote.note_id);
			// Reload metadata
			await loadReviewMetadata(selectedNote.note_id);
			// Add to due set for visual indicator
			notesDueForReview = new Set([...notesDueForReview, selectedNote.note_id]);
		} catch (error) {
			console.error('Failed to trigger review:', error);
		} finally {
			isTriggering = false;
		}
	}

	function toggleFolder(path: string) {
		if (expandedFolders.has(path)) {
			expandedFolders.delete(path);
		} else {
			expandedFolders.add(path);
		}
		expandedFolders = new Set(expandedFolders);
	}

	async function syncWithAppleNotes() {
		isSyncing = true;
		syncProgress = { current: 0, total: 0 };

		try {
			// Show syncing status
			syncStatus = { ...syncStatus, syncing: true } as NoteSyncStatus;

			const result = await syncAppleNotes();
			syncStatus = result;
			syncProgress = { current: result.notes_synced, total: result.notes_synced };

			// Reload tree after sync
			await loadTree();
		} catch (error) {
			console.error('Sync failed:', error);
		} finally {
			isSyncing = false;
			syncProgress = null;
		}
	}

	function openInNewWindow() {
		if (!selectedNote) return;
		// Open the note in a new window/tab
		const url = `/notes/${encodeURIComponent(selectedNote.note_id)}`;
		window.open(url, '_blank', 'width=800,height=600');
	}

	function formatNoteDate(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffDays === 0) {
			return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
		} else if (diffDays < 7) {
			return date.toLocaleDateString('fr-FR', { weekday: 'long' });
		} else {
			return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
		}
	}

	function formatReviewDate(dateStr: string | null): string {
		if (!dateStr) return 'Jamais';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = date.getTime() - now.getTime();
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffMs < 0) {
			// Past due
			const absDays = Math.abs(diffDays);
			if (absDays === 0) return "Aujourd'hui";
			if (absDays === 1) return 'Hier';
			return `Il y a ${absDays} jours`;
		} else {
			// Future
			if (diffHours < 1) return 'Dans moins d\'une heure';
			if (diffHours < 24) return `Dans ${diffHours}h`;
			if (diffDays === 1) return 'Demain';
			return `Dans ${diffDays} jours`;
		}
	}

	function groupNotesByDate(notes: Note[]): { label: string; notes: Note[] }[] {
		const now = new Date();
		const today: Note[] = [];
		const last7Days: Note[] = [];
		const last30Days: Note[] = [];
		const older: Note[] = [];

		for (const note of notes) {
			const date = new Date(note.updated_at);
			const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

			if (diffDays === 0) {
				today.push(note);
			} else if (diffDays < 7) {
				last7Days.push(note);
			} else if (diffDays < 30) {
				last30Days.push(note);
			} else {
				older.push(note);
			}
		}

		const groups: { label: string; notes: Note[] }[] = [];
		if (today.length > 0) groups.push({ label: "Aujourd'hui", notes: today });
		if (last7Days.length > 0) groups.push({ label: '7 jours précédents', notes: last7Days });
		if (last30Days.length > 0) groups.push({ label: '30 jours précédents', notes: last30Days });
		if (older.length > 0) groups.push({ label: 'Plus ancien', notes: older });

		return groups;
	}

	onMount(() => {
		loadTree();
	});

	const groupedNotes = $derived(groupNotesByDate(folderNotes));
	const totalNotes = $derived(notesData?.total_notes ?? 0);
	const selectedFolderName = $derived(() => {
		if (selectedFolderPath === ALL_NOTES_PATH) return 'Toutes les notes';
		if (selectedFolderPath === DELETED_NOTES_PATH) return 'Supprimées récemment';
		return selectedFolderPath ?? 'Notes';
	});
</script>

<div class="h-[calc(100vh-4rem)] flex bg-[var(--color-bg-primary)]">
	<!-- Column 1: Folder Tree -->
	<aside class="w-56 flex-shrink-0 border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50 flex flex-col">
		<!-- Sync Button with Progress -->
		<div class="p-3 border-b border-[var(--color-border)]">
			<button
				type="button"
				onclick={syncWithAppleNotes}
				disabled={isSyncing}
				class="w-full px-3 py-1.5 text-sm rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-tertiary)]/80 transition-colors disabled:opacity-50"
			>
				{#if isSyncing}
					<span class="inline-block animate-spin mr-1">⟳</span>
					{#if syncProgress}
						Synchro... ({syncProgress.current})
					{:else}
						Synchro...
					{/if}
				{:else}
					⟳ Sync Apple Notes
				{/if}
			</button>
			{#if syncStatus?.last_sync}
				<p class="text-[10px] text-[var(--color-text-tertiary)] mt-1 text-center">
					Dernière sync: {formatNoteDate(syncStatus.last_sync)}
				</p>
			{/if}
		</div>

		<!-- Folders -->
		<nav class="flex-1 overflow-y-auto p-2">
			{#if isLoading}
				<div class="p-4 text-center text-[var(--color-text-tertiary)] text-sm">
					Chargement...
				</div>
			{:else if loadError}
				<div class="p-4 text-center text-red-500 text-sm">
					{loadError}
				</div>
			{:else}
				<div class="space-y-0.5">
					<!-- Virtual: All Notes -->
					<div
						class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-left transition-colors text-sm cursor-pointer
							{selectedFolderPath === ALL_NOTES_PATH
								? 'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-100'
								: 'hover:bg-[var(--color-bg-tertiary)]'}"
						role="button"
						tabindex="0"
						onclick={() => selectFolder(ALL_NOTES_PATH)}
						onkeydown={(e) => e.key === 'Enter' && selectFolder(ALL_NOTES_PATH)}
					>
						<span class="w-4"></span>
						<span class="text-sm">📋</span>
						<span class="flex-1 truncate font-medium">Toutes les notes</span>
						<span class="text-xs text-[var(--color-text-tertiary)] tabular-nums">{totalNotes}</span>
					</div>

					<!-- Regular Folders -->
					{#each folders as folder}
						{@render folderRow(folder, 0)}
					{/each}

					<!-- Separator -->
					<div class="my-2 border-t border-[var(--color-border)]"></div>

					<!-- Virtual: Deleted Notes -->
					<div
						class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-left transition-colors text-sm cursor-pointer
							{selectedFolderPath === DELETED_NOTES_PATH
								? 'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-100'
								: 'hover:bg-[var(--color-bg-tertiary)]'}"
						role="button"
						tabindex="0"
						onclick={() => selectFolder(DELETED_NOTES_PATH)}
						onkeydown={(e) => e.key === 'Enter' && selectFolder(DELETED_NOTES_PATH)}
					>
						<span class="w-4"></span>
						<span class="text-sm">🗑️</span>
						<span class="flex-1 truncate">Supprimées récemment</span>
						<span class="text-xs text-[var(--color-text-tertiary)] tabular-nums">0</span>
					</div>
				</div>
			{/if}
		</nav>

		<!-- Footer: Total Notes -->
		<div class="p-2 border-t border-[var(--color-border)] text-center">
			<span class="text-xs text-[var(--color-text-tertiary)]">
				{totalNotes} note{totalNotes !== 1 ? 's' : ''} au total
			</span>
		</div>
	</aside>

	<!-- Column 2: Notes List -->
	<div class="w-72 flex-shrink-0 border-r border-[var(--color-border)] bg-[var(--color-bg-primary)] flex flex-col">
		<!-- Header -->
		<header class="px-4 py-3 border-b border-[var(--color-border)]">
			<h2 class="font-semibold text-[var(--color-text-primary)]">
				{selectedFolderName()}
			</h2>
			<p class="text-xs text-[var(--color-text-tertiary)]">
				{folderNotes.length} note{folderNotes.length !== 1 ? 's' : ''}
			</p>
		</header>

		<!-- Notes List -->
		<div class="flex-1 overflow-y-auto">
			{#if isLoadingNotes}
				<div class="p-4 text-center text-[var(--color-text-tertiary)] text-sm">
					Chargement...
				</div>
			{:else if folderNotes.length === 0}
				<div class="p-4 text-center text-[var(--color-text-tertiary)] text-sm">
					{#if selectedFolderPath === DELETED_NOTES_PATH}
						Aucune note supprimée
					{:else}
						Aucune note
					{/if}
				</div>
			{:else}
				{#each groupedNotes as group}
					<div class="px-4 py-2">
						<h3 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
							{group.label}
						</h3>
						<div class="space-y-1">
							{#each group.notes as note}
								{@render noteRow(note)}
							{/each}
						</div>
					</div>
				{/each}
			{/if}
		</div>
	</div>

	<!-- Column 3: Note Content -->
	<main class="flex-1 overflow-y-auto bg-[var(--color-bg-primary)]">
		{#if isLoadingNote}
			<div class="p-8 text-center text-[var(--color-text-tertiary)]">
				Chargement...
			</div>
		{:else if selectedNote}
			<article class="max-w-3xl mx-auto p-6">
				<!-- Note Header with Actions -->
				<div class="flex items-start justify-between mb-4">
					<h1 class="text-2xl font-bold text-[var(--color-text-primary)] flex-1">
						{selectedNote.title}
					</h1>
					<div class="flex items-center gap-2 ml-4">
						<!-- Edit Button -->
						{#if !isEditing}
							<button
								type="button"
								onclick={startEditing}
								class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
								title="Modifier la note"
							>
								✏️
							</button>
						{:else}
							<button
								type="button"
								onclick={cancelEditing}
								class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
								title="Annuler les modifications"
							>
								✕
							</button>
						{/if}
						<!-- Delete Button -->
						<button
							type="button"
							onclick={() => showDeleteModal = true}
							class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors text-[var(--color-text-secondary)] hover:text-red-600"
							title="Supprimer la note"
						>
							🗑️
						</button>
						<!-- Trigger Review Button -->
						<button
							type="button"
							onclick={handleTriggerReview}
							disabled={isTriggering}
							class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
							title="Déclencher une revue"
						>
							{#if isTriggering}
								<span class="inline-block animate-spin">⟳</span>
							{:else}
								🔄
							{/if}
						</button>
						<!-- Open in New Window Button -->
						<button
							type="button"
							onclick={openInNewWindow}
							class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
							title="Ouvrir dans une nouvelle fenêtre"
						>
							↗️
						</button>
					</div>
				</div>

				<!-- Note Content -->
				{#if isEditing}
					<div class="mt-4">
						<MarkdownEditor
							bind:content={editContent}
							onSave={saveNote}
							placeholder="Contenu de la note..."
						/>
					</div>
				{:else}
					<div class="prose prose-sm dark:prose-invert max-w-none mt-4">
						<MarkdownPreview content={selectedNote.content} />
					</div>
				{/if}

				<!-- Tags -->
				{#if selectedNote.tags.length > 0}
					<div class="mt-6 pt-4 border-t border-[var(--color-border)]">
						<div class="flex flex-wrap gap-2">
							{#each selectedNote.tags as tag}
								<span class="px-2 py-1 text-xs bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] rounded-md">
									#{tag}
								</span>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Review Metadata Section -->
				<div class="mt-6 pt-4 border-t border-[var(--color-border)]">
					<h3 class="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
						📊 Métadonnées de revue
						{#if notesDueForReview.has(selectedNote.note_id)}
							<span class="px-2 py-0.5 text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full">
								Revue due
							</span>
						{/if}
					</h3>

					{#if isLoadingReviewMetadata}
						<div class="text-sm text-[var(--color-text-tertiary)]">Chargement...</div>
					{:else if noteReviewMetadata}
						<div class="grid grid-cols-2 gap-3 text-sm">
							<div class="bg-[var(--color-bg-secondary)] rounded-lg p-3">
								<div class="text-[var(--color-text-tertiary)] text-xs mb-1">Prochaine revue</div>
								<div class="font-medium text-[var(--color-text-primary)]">
									{formatReviewDate(noteReviewMetadata.next_review)}
								</div>
							</div>
							<div class="bg-[var(--color-bg-secondary)] rounded-lg p-3">
								<div class="text-[var(--color-text-tertiary)] text-xs mb-1">Nombre de revues</div>
								<div class="font-medium text-[var(--color-text-primary)]">
									{noteReviewMetadata.review_count}
								</div>
							</div>
							<div class="bg-[var(--color-bg-secondary)] rounded-lg p-3">
								<div class="text-[var(--color-text-tertiary)] text-xs mb-1">Facteur de facilité</div>
								<div class="font-medium text-[var(--color-text-primary)]">
									{noteReviewMetadata.easiness_factor.toFixed(2)}
								</div>
							</div>
							<div class="bg-[var(--color-bg-secondary)] rounded-lg p-3">
								<div class="text-[var(--color-text-tertiary)] text-xs mb-1">Intervalle actuel</div>
								<div class="font-medium text-[var(--color-text-primary)]">
									{#if noteReviewMetadata.interval_hours < 24}
										{noteReviewMetadata.interval_hours}h
									{:else}
										{Math.round(noteReviewMetadata.interval_hours / 24)}j
									{/if}
								</div>
							</div>
							<div class="bg-[var(--color-bg-secondary)] rounded-lg p-3">
								<div class="text-[var(--color-text-tertiary)] text-xs mb-1">Type de note</div>
								<div class="font-medium text-[var(--color-text-primary)]">
									{noteReviewMetadata.note_type}
								</div>
							</div>
							<div class="bg-[var(--color-bg-secondary)] rounded-lg p-3">
								<div class="text-[var(--color-text-tertiary)] text-xs mb-1">Importance</div>
								<div class="font-medium text-[var(--color-text-primary)]">
									{noteReviewMetadata.importance}
								</div>
							</div>
						</div>
						{#if noteReviewMetadata.last_quality !== null}
							<div class="mt-3 text-sm text-[var(--color-text-tertiary)]">
								Dernière évaluation : {noteReviewMetadata.last_quality}/5
							</div>
						{/if}
					{:else}
						<div class="text-sm text-[var(--color-text-tertiary)]">
							Aucune donnée de revue disponible
						</div>
					{/if}
				</div>
			</article>
		{:else}
			<div class="h-full flex items-center justify-center text-[var(--color-text-tertiary)]">
				<div class="text-center">
					<p class="text-4xl mb-2">📝</p>
					<p>Sélectionnez une note</p>
				</div>
			</div>
		{/if}
	</main>
</div>

{#snippet folderRow(folder: FolderNode, depth: number)}
	{@const hasChildren = folder.children.length > 0}
	{@const isExpanded = expandedFolders.has(folder.path)}
	{@const isSelected = selectedFolderPath === folder.path}

	<div>
		<div
			class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-left transition-colors text-sm cursor-pointer
				{isSelected
					? 'bg-amber-100 dark:bg-amber-900/30 text-amber-900 dark:text-amber-100'
					: 'hover:bg-[var(--color-bg-tertiary)]'}"
			style="padding-left: {8 + depth * 16}px"
			role="button"
			tabindex="0"
			onclick={() => selectFolder(folder.path)}
			onkeydown={(e) => e.key === 'Enter' && selectFolder(folder.path)}
		>
			{#if hasChildren}
				<span
					role="button"
					tabindex="0"
					onclick={(e) => { e.stopPropagation(); toggleFolder(folder.path); }}
					onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); toggleFolder(folder.path); } }}
					class="w-4 h-4 flex items-center justify-center text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] cursor-pointer"
				>
					<span class="text-xs transition-transform {isExpanded ? 'rotate-90' : ''}">▶</span>
				</span>
			{:else}
				<span class="w-4"></span>
			{/if}
			<span class="text-sm">{isSelected ? '📂' : '📁'}</span>
			<span class="flex-1 truncate">{folder.name}</span>
			<span class="text-xs text-[var(--color-text-tertiary)] tabular-nums">{folder.note_count}</span>
		</div>

		{#if hasChildren && isExpanded}
			{#each folder.children as child}
				{@render folderRow(child, depth + 1)}
			{/each}
		{/if}
	</div>
{/snippet}

{#snippet noteRow(note: Note)}
	{@const isSelected = selectedNote?.note_id === note.note_id}
	{@const isDue = notesDueForReview.has(note.note_id)}

	<button
		type="button"
		onclick={() => selectNote(note)}
		class="w-full text-left p-2 rounded-lg transition-colors relative
			{isSelected
				? 'bg-amber-100 dark:bg-amber-900/30'
				: 'hover:bg-[var(--color-bg-secondary)]'}"
	>
		<div class="flex items-baseline gap-2 mb-0.5">
			<span class="font-medium text-sm text-[var(--color-text-primary)] truncate flex-1">
				{note.title}
			</span>
			{#if isDue}
				<span class="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0" title="Revue due"></span>
			{/if}
		</div>
		<div class="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
			<span class="shrink-0">{formatNoteDate(note.updated_at)}</span>
			<span class="truncate">{note.excerpt?.slice(0, 50) || ''}</span>
		</div>
	</button>
{/snippet}

<!-- Delete Confirmation Modal -->
<Modal bind:open={showDeleteModal} title="Supprimer la note" size="sm">
	<p class="text-[var(--color-text-secondary)] mb-6">
		Êtes-vous sûr de vouloir supprimer la note <strong>"{selectedNote?.title}"</strong> ? Cette action est irréversible.
	</p>
	<div class="flex justify-end gap-3">
		<button
			type="button"
			onclick={() => showDeleteModal = false}
			class="px-4 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors text-[var(--color-text-primary)]"
		>
			Annuler
		</button>
		<button
			type="button"
			onclick={confirmDelete}
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
</Modal>
