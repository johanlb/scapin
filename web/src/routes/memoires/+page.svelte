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
		listNoteFolders,
		getNote,
		updateNote,
		deleteNote,
		moveNote,
		createNote,
		getNoteReviewMetadata,
		triggerReview,
		getNotesDue,
		getDeletedNotes,
		searchNotes,
		addToFilage,
		triggerRetouche,
		getLowQualityNotes,
		getObsoleteNotes,
		getMergePendingNotes,
		runNoteHygiene,
		enrichNote,
		type Note,
		type FolderNode,
		type NotesTree,
		type NoteSyncStatus,
		type NoteReviewMetadata,
		type NoteSearchResult,
		type HygieneResult,
		type EnrichmentResult
	} from '$lib/api/client';
	import { memoryCyclesStore } from '$lib/stores/memory-cycles.svelte';
	import { orphanQuestionsStore } from '$lib/stores/orphan-questions.svelte';
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
	let deletedNotesCount = $state(0);

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
	let isAddingToFilage = $state(false);
	let isRunningRetouche = $state(false);

	// Notes due for review (for indicators)
	let notesDueForReview = $state<Set<string>>(new Set());

	// Content editing state
	let isEditing = $state(false);
	let editContent = $state('');
	let isSaving = $state(false);
	let showDeleteModal = $state(false);
	let isDeleting = $state(false);

	// Move modal state
	let showMoveModal = $state(false);
	let isMoving = $state(false);
	let availableFolders = $state<string[]>([]);
	let targetMoveFolder = $state('');

	// Create note modal state
	let showCreateNoteModal = $state(false);
	let isCreatingNote = $state(false);
	let newNoteTitle = $state('');

	// Title editing state
	let isEditingTitle = $state(false);
	let editedTitle = $state('');
	let titleInputRef = $state<HTMLInputElement | null>(null);

	// Hygiene review state (types imported from client.ts)
	let isRunningHygiene = $state(false);
	let hygieneResult = $state<HygieneResult | null>(null);
	let showHygienePanel = $state(false);

	// Enrichment state
	let isEnriching = $state(false);
	let enrichmentResult = $state<EnrichmentResult | null>(null);
	let showEnrichmentPanel = $state(false);

	// Expanded folders tracking
	let expandedFolders = $state<Set<string>>(new Set());

	// Search state
	let searchQuery = $state('');
	let searchResults = $state<NoteSearchResult[]>([]);
	let isSearching = $state(false);
	let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
	let searchInputRef: HTMLInputElement | null = null;

	// Virtual folder paths
	const ALL_NOTES_PATH = '__all__';
	const DELETED_NOTES_PATH = '__deleted__';

	// Filter paths (lifecycle filters)
	const FILTER_LOW_QUALITY = '__filter_low_quality__';
	const FILTER_OBSOLETE = '__filter_obsolete__';
	const FILTER_MERGE_PENDING = '__filter_merge_pending__';

	// Active filter state
	let activeFilter = $state<string | null>(null);
	let filteredMetadata = $state<NoteReviewMetadata[]>([]);

	// Sort folders with Canevas/Briefing first, then alphabetically
	function sortFoldersWithCanevasFirst(foldersToSort: FolderNode[]): FolderNode[] {
		return [...foldersToSort]
			.sort((a, b) => {
				const aIsCanevas = a.name === 'Canevas' || a.name === 'Briefing';
				const bIsCanevas = b.name === 'Canevas' || b.name === 'Briefing';
				if (aIsCanevas && !bIsCanevas) return -1;
				if (!aIsCanevas && bIsCanevas) return 1;
				return a.name.localeCompare(b.name);
			})
			.map(f => ({
				...f,
				children: sortFoldersWithCanevasFirst(f.children)
			}));
	}

	async function loadTree() {
		isLoading = true;
		loadError = null;
		try {
			// Critical: Load tree structure first (fast with metadata index)
			notesData = await getNotesTree(10);
			// Sort folders: Canevas/Briefing first, then alphabetically
			folders = sortFoldersWithCanevasFirst(notesData.folders);

			// Auto-select "All Notes" immediately so UI renders
			if (!selectedFolderPath) {
				// Don't await - let folder selection happen in parallel
				selectFolder(ALL_NOTES_PATH);
			}

			// Non-critical: Load these in parallel, fire-and-forget style
			// They update the UI when ready but don't block initial render
			getNotesDue(100)
				.then((dueResponse) => {
					notesDueForReview = new Set(dueResponse.notes.map((n) => n.note_id));
				})
				.catch(() => {
					/* ignore */
				});

			getNoteSyncStatus()
				.then((status) => {
					syncStatus = status;
				})
				.catch(() => {
					/* ignore */
				});

			// SLOW: getDeletedNotes uses AppleScript (180s timeout!)
			// Load lazily only when user clicks "Deleted Notes" folder
			// deletedNotesCount will be loaded on-demand in selectFolder()
		} catch (error) {
			loadError = error instanceof Error ? error.message : 'Erreur de chargement';
		} finally {
			isLoading = false;
		}
	}

	async function selectFilter(filterType: string) {
		if (activeFilter === filterType) return;

		activeFilter = filterType;
		selectedFolderPath = filterType;
		selectedNote = null;
		noteReviewMetadata = null;
		folderNotes = [];
		filteredMetadata = [];
		isLoadingNotes = true;

		try {
			let notes: NoteReviewMetadata[] = [];
			if (filterType === FILTER_LOW_QUALITY) {
				notes = await getLowQualityNotes(50, 100);
			} else if (filterType === FILTER_OBSOLETE) {
				notes = await getObsoleteNotes(100);
			} else if (filterType === FILTER_MERGE_PENDING) {
				notes = await getMergePendingNotes(100);
			}

			filteredMetadata = notes;
			// Load first note if available
			if (filteredMetadata.length > 0) {
				const firstNote = await getNote(filteredMetadata[0].note_id);
				await selectNote(firstNote);
			}
		} catch (error) {
			console.error('Failed to load filtered notes:', error);
			filteredMetadata = [];
		} finally {
			isLoadingNotes = false;
		}
	}

	async function selectFolder(path: string) {
		if (selectedFolderPath === path && !activeFilter) return;

		// Clear filter when selecting a folder
		activeFilter = null;
		filteredMetadata = [];

		selectedFolderPath = path;
		selectedNote = null;
		noteReviewMetadata = null;
		isLoadingNotes = true;

		try {
			if (path === ALL_NOTES_PATH) {
				// Load all notes (no folder filter) - increased to 1000 to display all notes
				const response = await listNotes(1, 1000);
				folderNotes = response.data ?? [];
			} else if (path === DELETED_NOTES_PATH) {
				// Load deleted notes from Apple Notes "Recently Deleted" folder
				folderNotes = await getDeletedNotes();
				deletedNotesCount = folderNotes.length;
			} else {
				const response = await listNotes(1, 1000, path);
				folderNotes = response.data ?? [];
			}
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

		// Cancel any ongoing edits
		if (isEditing) {
			isEditing = false;
			editContent = '';
		}
		if (isEditingTitle) {
			isEditingTitle = false;
			editedTitle = '';
		}

		// Reset hygiene state
		hygieneResult = null;
		showHygienePanel = false;

		// Reset enrichment state
		enrichmentResult = null;
		showEnrichmentPanel = false;

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

	function startEditingTitle() {
		if (!selectedNote) return;
		editedTitle = selectedNote.title;
		isEditingTitle = true;
		// Focus the input after the DOM updates
		setTimeout(() => titleInputRef?.focus(), 0);
	}

	function cancelEditingTitle() {
		isEditingTitle = false;
		editedTitle = '';
	}

	async function saveTitle() {
		if (!selectedNote || !editedTitle.trim()) {
			cancelEditingTitle();
			return;
		}

		const newTitle = editedTitle.trim();
		if (newTitle === selectedNote.title) {
			cancelEditingTitle();
			return;
		}

		isSaving = true;
		try {
			const updated = await updateNote(selectedNote.note_id, { title: newTitle });
			selectedNote = updated;
			// Update the note in the list
			folderNotes = folderNotes.map(n =>
				n.note_id === selectedNote!.note_id ? { ...n, title: newTitle } : n
			);
			toastStore.success('Titre mis à jour');
		} catch (error) {
			console.error('Failed to update title:', error);
			toastStore.error('Échec de la mise à jour du titre');
		} finally {
			isEditingTitle = false;
			editedTitle = '';
			isSaving = false;
		}
	}

	function handleTitleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			saveTitle();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelEditingTitle();
		}
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

	async function openMoveModal() {
		if (!selectedNote) return;

		// Load available folders
		try {
			const response = await listNoteFolders();
			availableFolders = response.folders;
			// Pre-select current folder if any
			targetMoveFolder = selectedNote.path || '';
			showMoveModal = true;
		} catch (error) {
			console.error('Failed to load folders:', error);
			toastStore.error('Échec du chargement des dossiers');
		}
	}

	async function confirmMove() {
		if (!selectedNote) return;

		// Don't move if already in target folder
		if (targetMoveFolder === (selectedNote.path || '')) {
			showMoveModal = false;
			return;
		}

		isMoving = true;
		try {
			const result = await moveNote(selectedNote.note_id, targetMoveFolder);
			if (result.moved) {
				// Update the selected note's path
				selectedNote = { ...selectedNote, path: targetMoveFolder };
				// Update in the folder notes list
				folderNotes = folderNotes.map((n) =>
					n.note_id === selectedNote!.note_id ? { ...n, path: targetMoveFolder } : n
				);
				// Reload tree to update folder counts
				await loadTree();
				toastStore.success(`Note déplacée vers "${targetMoveFolder || 'Racine'}"`);
			}
			showMoveModal = false;
		} catch (error) {
			console.error('Failed to move note:', error);
			toastStore.error('Échec du déplacement de la note');
		} finally {
			isMoving = false;
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

	async function handleAddToFilage() {
		if (!selectedNote || isAddingToFilage) return;

		isAddingToFilage = true;
		try {
			const result = await addToFilage(selectedNote.note_id);
			if (result.success) {
				toastStore.success(`"${selectedNote.title}" ajoutée au filage du jour`);
				// Add to due set for visual indicator
				notesDueForReview = new Set([...notesDueForReview, selectedNote.note_id]);
			} else {
				toastStore.error(result.message);
			}
		} catch (error) {
			console.error('Failed to add to filage:', error);
			toastStore.error('Échec de l\'ajout au filage');
		} finally {
			isAddingToFilage = false;
		}
	}

	async function handleTriggerRetouche() {
		if (!selectedNote || isRunningRetouche) return;

		isRunningRetouche = true;
		toastStore.info('Lancement de la retouche IA...');
		try {
			const result = await triggerRetouche(selectedNote.note_id);
			if (result.success) {
				const message = result.improvements_count > 0
					? `Retouche terminée : ${result.improvements_count} amélioration(s)`
					: 'Retouche terminée : aucune amélioration nécessaire';
				toastStore.success(message);
				// Reload the note to see improvements
				await selectNote(selectedNote);
			} else {
				toastStore.error(result.message);
			}
		} catch (error) {
			console.error('Failed to trigger retouche:', error);
			toastStore.error('Échec de la retouche IA');
		} finally {
			isRunningRetouche = false;
		}
	}

	async function runHygieneReview() {
		if (!selectedNote || isRunningHygiene) return;

		isRunningHygiene = true;
		hygieneResult = null;

		try {
			// Call the hygiene API
			hygieneResult = await runNoteHygiene(selectedNote.note_id);

			showHygienePanel = true;

			if (hygieneResult.issues.length === 0) {
				toastStore.success('Aucun problème détecté');
			} else {
				toastStore.success(`Analyse terminée: ${hygieneResult.issues.length} problème(s)`);
			}
		} catch (error) {
			toastStore.error('Échec de l\'analyse hygiène');
		} finally {
			isRunningHygiene = false;
		}
	}

	function dismissHygieneIssue(index: number) {
		if (!hygieneResult) return;
		hygieneResult = {
			...hygieneResult,
			issues: hygieneResult.issues.filter((_, i) => i !== index),
			summary: {
				...hygieneResult.summary,
				pending_review: Math.max(0, hygieneResult.summary.pending_review - 1)
			}
		};
	}

	function getIssueSeverityIcon(severity: string): string {
		switch (severity) {
			case 'error': return '❌';
			case 'warning': return '⚠️';
			case 'info': return 'ℹ️';
			default: return '•';
		}
	}

	async function runEnrichment() {
		if (!selectedNote || isEnriching) return;

		isEnriching = true;
		enrichmentResult = null;

		try {
			// Determine which sources to use based on metadata
			const sources = ['cross_reference'];
			if (noteReviewMetadata?.auto_enrich) {
				sources.push('ai_analysis');
			}
			if (noteReviewMetadata?.web_search_enabled) {
				sources.push('web_search');
			}

			enrichmentResult = await enrichNote(selectedNote.note_id, sources);
			showEnrichmentPanel = true;

			if (enrichmentResult.enrichments.length === 0) {
				toastStore.info('Aucun enrichissement trouvé');
			} else {
				toastStore.success(`${enrichmentResult.enrichments.length} enrichissement(s) suggéré(s)`);
			}
		} catch (error) {
			toastStore.error('Échec de l\'enrichissement');
		} finally {
			isEnriching = false;
		}
	}

	function dismissEnrichment(index: number) {
		if (!enrichmentResult) return;
		enrichmentResult = {
			...enrichmentResult,
			enrichments: enrichmentResult.enrichments.filter((_, i) => i !== index)
		};
	}

	function getIssueTypeLabel(type: string): string {
		switch (type) {
			case 'broken_link': return 'Lien cassé';
			case 'potential_duplicate': return 'Doublon potentiel';
			case 'missing_field': return 'Champ manquant';
			case 'outdated_info': return 'Info obsolète';
			case 'inconsistency': return 'Incohérence';
			case 'orphan_note': return 'Note orpheline';
			case 'suggested_link': return 'Lien suggéré';
			default: return type;
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

	async function handleCreateNote() {
		if (!newNoteTitle.trim()) return;

		isCreatingNote = true;
		try {
			// Use selected folder or root
			const folder = selectedFolderPath || '';
			const content = `# ${newNoteTitle}\n\n`;

			const note = await createNote(newNoteTitle, content, folder);

			// Close modal and reset
			showCreateNoteModal = false;
			newNoteTitle = '';

			// Reload tree and select the new note
			await loadTree();

			// Select the new note
			if (selectedFolderPath) {
				await selectFolder(selectedFolderPath);
			}
			selectedNote = note;

			toastStore.success('Note créée');
		} catch (error) {
			toastStore.error('Erreur lors de la création');
		} finally {
			isCreatingNote = false;
		}
	}

	function openInNewWindow() {
		if (!selectedNote) return;
		// Build the full path: folder/note_id
		// The [...path] route extracts noteId from the last segment
		const fullPath = selectedNote.path
			? `${selectedNote.path}/${selectedNote.note_id}`
			: selectedNote.note_id;
		const url = `/memoires/${fullPath}`;
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

	// Search functions
	async function performSearch(query: string) {
		if (!query.trim()) {
			searchResults = [];
			return;
		}

		isSearching = true;
		try {
			const response = await searchNotes(query, undefined, 50);
			searchResults = response.results;
		} catch (error) {
			console.error('Search failed:', error);
			searchResults = [];
		} finally {
			isSearching = false;
		}
	}

	function handleSearchInput(event: Event) {
		const input = event.target as HTMLInputElement;
		searchQuery = input.value;

		// Debounce search
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}

		if (searchQuery.trim()) {
			searchDebounceTimer = setTimeout(() => {
				performSearch(searchQuery);
			}, 300);
		} else {
			searchResults = [];
		}
	}

	function clearSearch() {
		searchQuery = '';
		searchResults = [];
		if (searchDebounceTimer) {
			clearTimeout(searchDebounceTimer);
		}
	}

	function handleSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			clearSearch();
			searchInputRef?.blur();
		}
	}

	function handleGlobalKeydown(event: KeyboardEvent) {
		// Cmd+K or Ctrl+K to focus search
		if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
			event.preventDefault();
			searchInputRef?.focus();
		}
	}

	async function selectSearchResult(result: NoteSearchResult) {
		// Clear search and select the note
		clearSearch();
		await selectNote(result.note);
	}

	onMount(() => {
		loadTree();

		// Load Memory Cycles data for navigation badges
		memoryCyclesStore.fetchFilage(20).catch(() => {/* ignore */});
		memoryCyclesStore.fetchPendingQuestions(100).catch(() => {/* ignore */});
		orphanQuestionsStore.fetchQuestions(false).catch(() => {/* ignore */});

		// Global keyboard listener
		window.addEventListener('keydown', handleGlobalKeydown);
		return () => {
			window.removeEventListener('keydown', handleGlobalKeydown);
			if (searchDebounceTimer) {
				clearTimeout(searchDebounceTimer);
			}
		};
	});

	const groupedNotes = $derived(groupNotesByDate(folderNotes));
	const totalNotes = $derived(notesData?.total_notes ?? 0);
	const selectedFolderName = $derived(() => {
		if (selectedFolderPath === ALL_NOTES_PATH) return 'Toutes les notes';
		if (selectedFolderPath === DELETED_NOTES_PATH) return 'Supprimées récemment';
		return selectedFolderPath ?? 'Notes';
	});
	const isSearchMode = $derived(searchQuery.trim().length > 0);
</script>

<div class="h-[calc(100vh-4rem)] flex bg-[var(--color-bg-primary)]">
	<!-- Column 1: Folder Tree -->
	<aside class="w-56 flex-shrink-0 border-r border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50 flex flex-col">
		<!-- Sync Button with Progress -->
		<div class="p-3 border-b border-[var(--color-border)]">
			<div class="flex gap-2">
				<button
					type="button"
					onclick={syncWithAppleNotes}
					disabled={isSyncing}
					class="flex-1 px-3 py-1.5 text-sm rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-tertiary)]/80 transition-colors disabled:opacity-50"
				>
					{#if isSyncing}
						<span class="inline-block animate-spin mr-1">⟳</span>
						{#if syncProgress}
							Synchro...
						{:else}
							Synchro...
						{/if}
					{:else}
						⟳ Sync
					{/if}
				</button>
				<button
					type="button"
					onclick={() => (showCreateNoteModal = true)}
					class="px-3 py-1.5 text-sm rounded-lg bg-[var(--color-accent)]/10 hover:bg-[var(--color-accent)]/20 text-[var(--color-accent)] transition-colors"
					title="Créer une nouvelle note"
					data-testid="create-note-button"
				>
					➕
				</button>
			</div>
			{#if syncStatus?.last_sync}
				<p class="text-[10px] text-[var(--color-text-tertiary)] mt-1 text-center">
					Dernière sync: {formatNoteDate(syncStatus.last_sync)}
				</p>
			{/if}
		</div>

		<!-- Memory Cycles Quick Access -->
		<div class="p-2 border-b border-[var(--color-border)]">
			<div class="flex flex-col gap-1">
				<div class="flex gap-1">
					<button
						type="button"
						onclick={() => goto('/memoires/filage')}
						class="flex-1 px-2 py-1.5 text-xs rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-300 transition-colors flex items-center justify-center gap-1"
						title="Filage du jour"
					>
						<span>📋</span>
						<span>Filage</span>
						{#if memoryCyclesStore.totalLectures > 0}
							<span class="px-1 py-0.5 text-[10px] bg-amber-500/20 rounded-full">{memoryCyclesStore.totalLectures}</span>
						{/if}
					</button>
					<button
						type="button"
						onclick={() => goto('/memoires/questions')}
						class="flex-1 px-2 py-1.5 text-xs rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-700 dark:text-purple-300 transition-colors flex items-center justify-center gap-1"
						title="Questions en attente"
					>
						<span>❓</span>
						<span>Questions</span>
						{#if memoryCyclesStore.pendingQuestionsCount > 0}
							<span class="px-1 py-0.5 text-[10px] bg-purple-500/20 rounded-full">{memoryCyclesStore.pendingQuestionsCount}</span>
						{/if}
					</button>
				</div>
				<button
					type="button"
					onclick={() => goto('/memoires/orphan-questions')}
					class="w-full px-2 py-1.5 text-xs rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-700 dark:text-red-300 transition-colors flex items-center justify-center gap-1"
					title="Questions orphelines (sans note cible)"
				>
					<span>🎯</span>
					<span>Questions orphelines</span>
					{#if orphanQuestionsStore.pendingCount > 0}
						<span class="px-1 py-0.5 text-[10px] bg-red-500/20 rounded-full">{orphanQuestionsStore.pendingCount}</span>
					{/if}
				</button>
			</div>
		</div>

		<!-- Quality Filters -->
		<div class="p-2 border-b border-[var(--color-border)]">
			<p class="text-[10px] text-[var(--color-text-tertiary)] uppercase tracking-wide mb-1 px-1">Filtres qualité</p>
			<div class="flex flex-col gap-1">
				<button
					type="button"
					onclick={() => selectFilter(FILTER_LOW_QUALITY)}
					class="w-full px-2 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1
						{activeFilter === FILTER_LOW_QUALITY
							? 'bg-orange-500/20 text-orange-700 dark:text-orange-300'
							: 'hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
					title="Notes à améliorer (score < 50)"
				>
					<span>📉</span>
					<span>Faible qualité</span>
				</button>
				<button
					type="button"
					onclick={() => selectFilter(FILTER_OBSOLETE)}
					class="w-full px-2 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1
						{activeFilter === FILTER_OBSOLETE
							? 'bg-gray-500/20 text-gray-700 dark:text-gray-300'
							: 'hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
					title="Notes marquées obsolètes"
				>
					<span>🗑️</span>
					<span>Obsolètes</span>
				</button>
				<button
					type="button"
					onclick={() => selectFilter(FILTER_MERGE_PENDING)}
					class="w-full px-2 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1
						{activeFilter === FILTER_MERGE_PENDING
							? 'bg-blue-500/20 text-blue-700 dark:text-blue-300'
							: 'hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
					title="Notes en attente de fusion"
				>
					<span>🔀</span>
					<span>Fusion en attente</span>
				</button>
			</div>
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
						<span class="text-xs text-[var(--color-text-tertiary)] tabular-nums">{deletedNotesCount}</span>
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
		<!-- Search Bar -->
		<div class="px-3 py-2 border-b border-[var(--color-border)]">
			<div class="relative">
				<input
					type="text"
					bind:this={searchInputRef}
					value={searchQuery}
					oninput={handleSearchInput}
					onkeydown={handleSearchKeydown}
					placeholder="Rechercher..."
					class="w-full pl-8 pr-8 py-1.5 text-sm rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)]"
				/>
				<span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]">
					{#if isSearching}
						<span class="inline-block animate-spin">⟳</span>
					{:else}
						🔍
					{/if}
				</span>
				{#if searchQuery}
					<button
						type="button"
						onclick={clearSearch}
						class="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] p-0.5"
						title="Effacer (Esc)"
					>
						✕
					</button>
				{:else}
					<span class="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] text-[var(--color-text-tertiary)] bg-[var(--color-bg-tertiary)] px-1 rounded">
						⌘K
					</span>
				{/if}
			</div>
		</div>

		<!-- Header -->
		<header class="px-4 py-2 border-b border-[var(--color-border)]">
			{#if isSearchMode}
				<h2 class="font-semibold text-[var(--color-text-primary)]">
					Résultats
				</h2>
				<p class="text-xs text-[var(--color-text-tertiary)]">
					{searchResults.length} résultat{searchResults.length !== 1 ? 's' : ''} pour "{searchQuery}"
				</p>
			{:else if activeFilter}
				<div class="flex items-center gap-2">
					<h2 class="font-semibold text-[var(--color-text-primary)]">
						{activeFilter === FILTER_LOW_QUALITY ? 'Faible qualité' :
						 activeFilter === FILTER_OBSOLETE ? 'Obsolètes' :
						 activeFilter === FILTER_MERGE_PENDING ? 'Fusion en attente' : 'Filtre'}
					</h2>
					<button
						type="button"
						onclick={() => selectFolder(ALL_NOTES_PATH)}
						class="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)]"
						title="Effacer le filtre"
					>
						✕
					</button>
				</div>
				<p class="text-xs text-[var(--color-text-tertiary)]">
					{filteredMetadata.length} note{filteredMetadata.length !== 1 ? 's' : ''}
				</p>
			{:else}
				<h2 class="font-semibold text-[var(--color-text-primary)]">
					{selectedFolderName()}
				</h2>
				<p class="text-xs text-[var(--color-text-tertiary)]">
					{folderNotes.length} note{folderNotes.length !== 1 ? 's' : ''}
				</p>
			{/if}
		</header>

		<!-- Notes List / Search Results -->
		<div class="flex-1 overflow-y-auto">
			{#if isSearchMode}
				<!-- Search Results -->
				{#if isSearching}
					<div class="p-4 text-center text-[var(--color-text-tertiary)] text-sm">
						Recherche...
					</div>
				{:else if searchResults.length === 0}
					<div class="p-4 text-center text-[var(--color-text-tertiary)] text-sm">
						Aucun résultat
					</div>
				{:else}
					<div class="px-3 py-2 space-y-1">
						{#each searchResults as result}
							{@render searchResultRow(result)}
						{/each}
					</div>
				{/if}
			{:else if activeFilter}
				<!-- Filtered Notes List -->
				{#if isLoadingNotes}
					<div class="p-4 text-center text-[var(--color-text-tertiary)] text-sm">
						Chargement...
					</div>
				{:else if filteredMetadata.length === 0}
					<div class="p-8 text-center">
						{#if activeFilter === FILTER_LOW_QUALITY}
							<p class="text-4xl mb-3">✨</p>
							<p class="text-[var(--color-text-primary)] font-medium mb-1">Toutes les notes sont de bonne qualité !</p>
							<p class="text-sm text-[var(--color-text-tertiary)]">Aucune note n'a un score inférieur à 50.</p>
						{:else if activeFilter === FILTER_OBSOLETE}
							<p class="text-4xl mb-3">📚</p>
							<p class="text-[var(--color-text-primary)] font-medium mb-1">Aucune note obsolète</p>
							<p class="text-sm text-[var(--color-text-tertiary)]">Toutes vos notes sont à jour.</p>
						{:else if activeFilter === FILTER_MERGE_PENDING}
							<p class="text-4xl mb-3">🔗</p>
							<p class="text-[var(--color-text-primary)] font-medium mb-1">Aucune fusion en attente</p>
							<p class="text-sm text-[var(--color-text-tertiary)]">Pas de doublons détectés.</p>
						{/if}
					</div>
				{:else}
					<div class="px-3 py-2 space-y-1">
						{#each filteredMetadata as meta}
							{@render filteredNoteRow(meta)}
						{/each}
					</div>
				{/if}
			{:else}
				<!-- Normal Notes List -->
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
					{#if isEditingTitle}
						<div class="flex items-center gap-2 flex-1">
							<input
								type="text"
								bind:this={titleInputRef}
								bind:value={editedTitle}
								onkeydown={handleTitleKeydown}
								onblur={saveTitle}
								class="text-2xl font-bold bg-transparent border-b-2 border-amber-500 outline-none flex-1 text-[var(--color-text-primary)]"
								disabled={isSaving}
							/>
							<button
								type="button"
								onclick={saveTitle}
								disabled={isSaving}
								class="p-1.5 rounded-lg text-green-600 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
								title="Sauvegarder"
							>
								{#if isSaving}
									<span class="inline-block animate-spin">⟳</span>
								{:else}
									✓
								{/if}
							</button>
							<button
								type="button"
								onclick={cancelEditingTitle}
								disabled={isSaving}
								class="p-1.5 rounded-lg text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
								title="Annuler"
							>
								✕
							</button>
						</div>
					{:else}
						<h1
							class="text-2xl font-bold text-[var(--color-text-primary)] flex-1 cursor-pointer hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
							ondblclick={startEditingTitle}
							title="Double-clic pour modifier le titre"
						>
							{selectedNote.title}
						</h1>
					{/if}
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
						<!-- Move Button -->
						<button
							type="button"
							onclick={openMoveModal}
							class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
							title="Déplacer vers un dossier"
						>
							📁
						</button>
						<!-- Delete Button -->
						<button
							type="button"
							onclick={() => showDeleteModal = true}
							class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors text-[var(--color-text-secondary)] hover:text-red-600"
							title="Supprimer la note"
						>
							🗑️
						</button>
						<!-- Hygiene Review Button -->
						<button
							type="button"
							onclick={runHygieneReview}
							disabled={isRunningHygiene}
							class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] relative"
							title="Analyser l'hygiène de la note"
						>
							{#if isRunningHygiene}
								<span class="inline-block animate-spin">⟳</span>
							{:else if hygieneResult && hygieneResult.summary.pending_review > 0}
								🧹
								<span class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center">
									{hygieneResult.summary.pending_review}
								</span>
							{:else if hygieneResult && hygieneResult.summary.health_score >= 0.9}
								✨
							{:else}
								🧹
							{/if}
						</button>
						<!-- Enrich Button -->
						<button
							type="button"
							onclick={runEnrichment}
							disabled={isEnriching}
							class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] relative"
							title="Enrichir la note (recherche web si activée)"
						>
							{#if isEnriching}
								<span class="inline-block animate-spin">⟳</span>
							{:else if enrichmentResult && enrichmentResult.enrichments.length > 0}
								🌐
								<span class="absolute -top-1 -right-1 w-4 h-4 bg-blue-500 text-white text-[10px] rounded-full flex items-center justify-center">
									{enrichmentResult.enrichments.length}
								</span>
							{:else}
								🌐
							{/if}
						</button>
						<!-- Trigger Review Button -->
						<button
							type="button"
							onclick={handleTriggerReview}
							disabled={isTriggering}
							class="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
							title="Déclencher une revue SM-2"
						>
							{#if isTriggering}
								<span class="inline-block animate-spin">⟳</span>
							{:else}
								🔄
							{/if}
						</button>
						<!-- Add to Filage Button -->
						<button
							type="button"
							onclick={handleAddToFilage}
							disabled={isAddingToFilage}
							class="p-2 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors text-[var(--color-text-secondary)] hover:text-amber-600"
							title="Ajouter au filage du jour"
						>
							{#if isAddingToFilage}
								<span class="inline-block animate-spin">⟳</span>
							{:else}
								📋
							{/if}
						</button>
						<!-- AI Retouche Button -->
						<button
							type="button"
							onclick={handleTriggerRetouche}
							disabled={isRunningRetouche}
							class="p-2 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors text-[var(--color-text-secondary)] hover:text-purple-600"
							title="Demander une revue IA (retouche)"
						>
							{#if isRunningRetouche}
								<span class="inline-block animate-spin">⟳</span>
							{:else}
								🤖
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

				<!-- Hygiene Review Panel -->
				{#if hygieneResult && showHygienePanel}
					<div class="mt-6 pt-4 border-t border-[var(--color-border)]">
						<div class="bg-[var(--color-bg-secondary)] rounded-lg border border-[var(--color-border)]">
							<!-- Header -->
							<div class="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
								<div class="flex items-center gap-2">
									<span>🧹</span>
									<span class="font-semibold text-[var(--color-text-primary)]">Revue Hygiène</span>
								</div>
								<div class="flex items-center gap-3">
									<span class="text-sm">
										Score:
										<span class="font-bold {hygieneResult.summary.health_score >= 0.9 ? 'text-green-600 dark:text-green-400' : hygieneResult.summary.health_score >= 0.7 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}">
											{Math.round(hygieneResult.summary.health_score * 100)}%
										</span>
									</span>
									<button
										type="button"
										onclick={() => showHygienePanel = false}
										class="p-1 rounded hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-tertiary)]"
										title="Fermer"
									>
										✕
									</button>
								</div>
							</div>

							<!-- Issues List -->
							<div class="p-4 space-y-3">
								{#if hygieneResult.issues.length === 0}
									<div class="text-center py-4 text-[var(--color-text-tertiary)]">
										<span class="text-2xl">✨</span>
										<p class="mt-2">Note en parfait état !</p>
									</div>
								{:else}
									{#each hygieneResult.issues as issue, index}
										<div class="flex items-start gap-3 p-3 rounded-lg bg-[var(--color-bg-primary)] border border-[var(--color-border)]">
											<span class="text-lg flex-shrink-0">
												{#if issue.auto_applied}
													✅
												{:else}
													{getIssueSeverityIcon(issue.severity)}
												{/if}
											</span>
											<div class="flex-1 min-w-0">
												<div class="flex items-center gap-2 mb-1">
													<span class="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]">
														{getIssueTypeLabel(issue.type)}
													</span>
													<span class="text-xs text-[var(--color-text-tertiary)]">
														{Math.round(issue.confidence * 100)}% confiance
													</span>
													{#if issue.auto_applied}
														<span class="text-xs px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
															Corrigé
														</span>
													{/if}
												</div>
												<p class="text-sm text-[var(--color-text-primary)]">{issue.detail}</p>
												{#if issue.suggestion}
													<p class="text-sm text-[var(--color-text-secondary)] mt-1">
														💡 {issue.suggestion}
													</p>
												{/if}
												{#if !issue.auto_applied}
													<div class="flex items-center gap-2 mt-2">
														<button
															type="button"
															class="text-xs px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-900/50"
														>
															Appliquer
														</button>
														<button
															type="button"
															onclick={() => dismissHygieneIssue(index)}
															class="text-xs px-2 py-1 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]/80"
														>
															Ignorer
														</button>
														{#if issue.related_note_id}
															<button
																type="button"
																class="text-xs px-2 py-1 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]/80"
															>
																Voir note
															</button>
														{/if}
													</div>
												{/if}
											</div>
										</div>
									{/each}
								{/if}

								<!-- Summary -->
								<div class="flex items-center justify-between text-xs text-[var(--color-text-tertiary)] pt-2 border-t border-[var(--color-border)]">
									<span>
										Analysé en {hygieneResult.duration_ms}ms avec {hygieneResult.model_used}
									</span>
									<span>
										{hygieneResult.context_notes_count} notes contextuelles
									</span>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Enrichment Panel -->
				{#if enrichmentResult && showEnrichmentPanel}
					<div class="mt-6 pt-4 border-t border-[var(--color-border)]">
						<div class="bg-[var(--color-bg-secondary)] rounded-lg border border-[var(--color-border)]">
							<!-- Header -->
							<div class="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
								<div class="flex items-center gap-2">
									<span>🌐</span>
									<span class="font-semibold text-[var(--color-text-primary)]">Enrichissement</span>
								</div>
								<div class="flex items-center gap-3">
									<span class="text-xs text-[var(--color-text-tertiary)]">
										Sources: {enrichmentResult.sources_used.join(', ')}
									</span>
									<button
										type="button"
										onclick={() => showEnrichmentPanel = false}
										class="p-1 rounded hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-tertiary)]"
										title="Fermer"
									>
										✕
									</button>
								</div>
							</div>

							<!-- Content -->
							<div class="p-4 space-y-3">
								{#if enrichmentResult.enrichments.length === 0}
									<div class="text-center py-4 text-[var(--color-text-tertiary)]">
										<span class="text-2xl">🔍</span>
										<p class="mt-2">Aucun enrichissement trouvé</p>
										{#if enrichmentResult.gaps_identified.length > 0}
											<div class="mt-3 text-left">
												<p class="text-sm font-medium text-[var(--color-text-secondary)] mb-2">Lacunes identifiées :</p>
												<ul class="text-sm text-[var(--color-text-tertiary)] space-y-1">
													{#each enrichmentResult.gaps_identified as gap}
														<li>• {gap}</li>
													{/each}
												</ul>
											</div>
										{/if}
									</div>
								{:else}
									{#each enrichmentResult.enrichments as enrichment, index}
										<div class="p-3 rounded-lg bg-[var(--color-bg-primary)] border border-[var(--color-border)]">
											<div class="flex items-center justify-between mb-2">
												<div class="flex items-center gap-2">
													<span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
														{enrichment.source}
													</span>
													<span class="text-xs px-2 py-0.5 rounded-full bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]">
														→ {enrichment.section}
													</span>
													<span class="text-xs text-[var(--color-text-tertiary)]">
														{Math.round(enrichment.confidence * 100)}%
													</span>
												</div>
												<button
													type="button"
													onclick={() => dismissEnrichment(index)}
													class="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]"
												>
													✕
												</button>
											</div>
											<p class="text-sm text-[var(--color-text-primary)] mb-2">{enrichment.content}</p>
											<p class="text-xs text-[var(--color-text-tertiary)] italic">{enrichment.reasoning}</p>
											<div class="flex items-center gap-2 mt-2">
												<button
													type="button"
													class="text-xs px-2 py-1 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50"
												>
													Appliquer
												</button>
												<button
													type="button"
													onclick={() => dismissEnrichment(index)}
													class="text-xs px-2 py-1 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]/80"
												>
													Ignorer
												</button>
											</div>
										</div>
									{/each}
								{/if}

								<!-- Summary -->
								<div class="text-xs text-[var(--color-text-tertiary)] pt-2 border-t border-[var(--color-border)]">
									<p>{enrichmentResult.analysis_summary}</p>
								</div>
							</div>
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
						{#if noteReviewMetadata.last_synced_at}
							<div class="mt-2 text-sm text-[var(--color-text-tertiary)]">
								🔄 Sync Apple Notes : {formatRelativeTime(noteReviewMetadata.last_synced_at)}
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
	{@const isCanevas = folder.name === 'Canevas' || folder.name === 'Briefing'}
	{@const folderIcon = isCanevas ? '📜' : (isSelected ? '📂' : '📁')}

	<div>
		<div
			class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-left transition-colors text-sm cursor-pointer
				{isCanevas && !isSelected ? 'bg-amber-500/10 border border-amber-500/20' : ''}
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
			<span class="text-sm">{folderIcon}</span>
			<span class="flex-1 truncate">{folder.name}</span>
			{#if isCanevas}
				<span class="text-[10px] px-1 rounded bg-amber-500/20 text-amber-600 dark:text-amber-400">Contexte</span>
			{/if}
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

{#snippet filteredNoteRow(meta: NoteReviewMetadata)}
	{@const isSelected = selectedNote?.note_id === meta.note_id}
	{@const qualityScore = meta.quality_score ?? 0}
	{@const qualityColor = qualityScore >= 70 ? 'text-green-600 dark:text-green-400' :
						   qualityScore >= 40 ? 'text-amber-600 dark:text-amber-400' :
						   'text-red-600 dark:text-red-400'}

	<button
		type="button"
		onclick={async () => {
			const note = await getNote(meta.note_id);
			selectNote(note);
		}}
		class="w-full text-left p-2 rounded-lg transition-colors relative
			{isSelected
				? 'bg-amber-100 dark:bg-amber-900/30'
				: 'hover:bg-[var(--color-bg-secondary)]'}"
	>
		<div class="flex items-baseline gap-2 mb-0.5">
			<span class="font-medium text-sm text-[var(--color-text-primary)] truncate flex-1">
				{meta.note_id.split('/').pop() || meta.note_id}
			</span>
			{#if activeFilter === FILTER_LOW_QUALITY}
				<span class="text-xs font-medium tabular-nums {qualityColor}" title="Score qualité">
					{qualityScore}%
				</span>
			{:else if activeFilter === FILTER_OBSOLETE}
				<span class="text-xs px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
					Obsolète
				</span>
			{:else if activeFilter === FILTER_MERGE_PENDING}
				<span class="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
					🔀 Fusion
				</span>
			{/if}
		</div>
		<div class="flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
			<span>{meta.note_type}</span>
			<span>•</span>
			<span>{meta.importance}</span>
			{#if meta.review_count > 0}
				<span>•</span>
				<span>{meta.review_count} revue{meta.review_count > 1 ? 's' : ''}</span>
			{/if}
		</div>
	</button>
{/snippet}

{#snippet searchResultRow(result: NoteSearchResult)}
	{@const isSelected = selectedNote?.note_id === result.note.note_id}
	{@const scorePercent = Math.round(result.score * 100)}
	{@const folderPath = result.note.path.split('/').slice(0, -1).join('/')}

	<button
		type="button"
		onclick={() => selectSearchResult(result)}
		class="w-full text-left p-2 rounded-lg transition-colors relative
			{isSelected
				? 'bg-amber-100 dark:bg-amber-900/30'
				: 'hover:bg-[var(--color-bg-secondary)]'}"
	>
		<div class="flex items-baseline gap-2 mb-0.5">
			<span class="font-medium text-sm text-[var(--color-text-primary)] truncate flex-1">
				{result.note.title}
			</span>
			<span
				class="text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0
					{scorePercent >= 80 ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' :
					 scorePercent >= 50 ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' :
					 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
				title="Score de pertinence"
			>
				{scorePercent}%
			</span>
		</div>
		<div class="text-xs text-[var(--color-text-tertiary)]">
			{#if result.highlights.length > 0}
				<span class="line-clamp-2">{@html result.highlights[0]}</span>
			{:else}
				<span class="truncate">{result.note.excerpt?.slice(0, 80) || ''}</span>
			{/if}
		</div>
		{#if folderPath}
			<div class="text-[10px] text-[var(--color-text-tertiary)] mt-1 flex items-center gap-1">
				<span>📁</span>
				<span>{folderPath}</span>
			</div>
		{/if}
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

<!-- Move Note Modal -->
<Modal bind:open={showMoveModal} title="Déplacer la note" size="sm">
	<p class="text-[var(--color-text-secondary)] mb-4">
		Déplacer <strong>"{selectedNote?.title}"</strong> vers un autre dossier :
	</p>
	<div class="space-y-2 max-h-64 overflow-y-auto mb-6">
		<!-- Root folder option -->
		<button
			type="button"
			onclick={() => targetMoveFolder = ''}
			class="w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center gap-2
				{targetMoveFolder === ''
					? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
					: 'hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
		>
			<span>📁</span>
			<span>Racine</span>
			{#if selectedNote?.path === ''}
				<span class="text-xs text-[var(--color-text-tertiary)] ml-auto">(actuel)</span>
			{/if}
		</button>
		<!-- Available folders -->
		{#each availableFolders as folder}
			<button
				type="button"
				onclick={() => targetMoveFolder = folder}
				class="w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center gap-2
					{targetMoveFolder === folder
						? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
						: 'hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
			>
				<span>📁</span>
				<span>{folder}</span>
				{#if selectedNote?.path === folder}
					<span class="text-xs text-[var(--color-text-tertiary)] ml-auto">(actuel)</span>
				{/if}
			</button>
		{/each}
	</div>
	<div class="flex justify-end gap-3">
		<button
			type="button"
			onclick={() => showMoveModal = false}
			class="px-4 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors text-[var(--color-text-primary)]"
		>
			Annuler
		</button>
		<button
			type="button"
			onclick={confirmMove}
			disabled={isMoving || targetMoveFolder === (selectedNote?.path || '')}
			class="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white transition-colors disabled:opacity-50"
		>
			{#if isMoving}
				Déplacement...
			{:else}
				Déplacer
			{/if}
		</button>
	</div>
</Modal>

<!-- Create Note Modal -->
<Modal bind:open={showCreateNoteModal} title="Nouvelle note">
	<form onsubmit={(e) => { e.preventDefault(); handleCreateNote(); }}>
		<div class="mb-4">
			<label for="note-title" class="block text-sm font-medium text-[var(--color-text-secondary)] mb-2">
				Titre de la note
			</label>
			<input
				id="note-title"
				type="text"
				bind:value={newNoteTitle}
				placeholder="Entrez le titre..."
				class="w-full px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]
					focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50
					text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)]"
				data-testid="create-note-title-input"
			/>
			{#if selectedFolderPath}
				<p class="text-xs text-[var(--color-text-tertiary)] mt-2">
					📁 Dossier : {selectedFolderPath}
				</p>
			{:else}
				<p class="text-xs text-[var(--color-text-tertiary)] mt-2">
					📁 Dossier : Racine
				</p>
			{/if}
		</div>
		<div class="flex justify-end gap-3">
			<button
				type="button"
				onclick={() => { showCreateNoteModal = false; newNoteTitle = ''; }}
				class="px-4 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors text-[var(--color-text-primary)]"
			>
				Annuler
			</button>
			<button
				type="submit"
				disabled={isCreatingNote || !newNoteTitle.trim()}
				class="px-4 py-2 rounded-lg bg-[var(--color-accent)] hover:bg-[var(--color-accent)]/80 text-white transition-colors disabled:opacity-50"
				data-testid="create-note-submit"
			>
				{#if isCreatingNote}
					Création...
				{:else}
					Créer
				{/if}
			</button>
		</div>
	</form>
</Modal>
