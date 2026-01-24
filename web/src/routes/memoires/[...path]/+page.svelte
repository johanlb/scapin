<script lang="ts">
	import { page } from '$app/stores';
	import { Card, Badge } from '$lib/components/ui';
	import MarkdownEditor from '$lib/components/notes/MarkdownEditor.svelte';
	import MarkdownPreview from '$lib/components/notes/MarkdownPreview.svelte';
	import NoteHistory from '$lib/components/notes/NoteHistory.svelte';
	import RetoucheHistory from '$lib/components/notes/RetoucheHistory.svelte';
	import { noteChatStore, detectNoteType, type NoteContext } from '$lib/stores/note-chat.svelte';
	import { extractWikilinks } from '$lib/utils/markdown';
	import { getNote, updateNote } from '$lib/api/client';

	// Get the note path from route params
	const notePath = $derived($page.params.path);
	const pathParts = $derived(notePath ? notePath.split('/') : []);
	// Extract note_id from the last part of the path
	const noteId = $derived(pathParts.length > 0 ? pathParts[pathParts.length - 1] : '');

	// Note state - loaded from API
	let note = $state<{
		id: string;
		title: string;
		path: string;
		content: string;
		created_at: string;
		updated_at: string;
		tags: string[];
		pinned: boolean;
	} | null>(null);

	let loading = $state(true);
	let error = $state<string | null>(null);
	let editing = $state(false);
	let showHistory = $state(false);
	let showRetoucheHistory = $state(false);

	// Load note when noteId changes
	$effect(() => {
		if (noteId) {
			loadNote(noteId);
		}
	});

	async function loadNote(id: string) {
		loading = true;
		error = null;
		try {
			const apiNote = await getNote(id);
			note = {
				id: apiNote.note_id,
				title: apiNote.title,
				path: apiNote.path,
				content: apiNote.content,
				created_at: apiNote.created_at,
				updated_at: apiNote.updated_at,
				tags: apiNote.tags,
				pinned: apiNote.pinned
			};
		} catch (e) {
			console.error('Failed to load note:', e);
			error = e instanceof Error ? e.message : 'Failed to load note';
			note = null;
		} finally {
			loading = false;
		}
	}

	function goBack() {
		history.back();
	}

	function toggleEdit() {
		editing = !editing;
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'long',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function extractFolder(path: string): string {
		const parts = path.split('/');
		// Remove the filename (last part) to get folder path
		const folder = parts.slice(0, -1).join('/');
		return folder || 'Racine';
	}

	async function handleSave(content: string): Promise<void> {
		if (!note) return;
		try {
			await updateNote(note.id, { content });
			note.content = content;
			note.updated_at = new Date().toISOString();
		} catch (e) {
			console.error('Failed to save note:', e);
		}
	}

	function handleRestore() {
		// Reload note after version restore
		if (noteId) {
			loadNote(noteId);
		}
	}

	function handleOpenChat() {
		if (!note) return;
		// Build note context for chat
		const noteType = detectNoteType({ title: note.title, tags: note.tags });
		const linkedNotes = extractWikilinks(note.content);

		const context: NoteContext = {
			id: note.id,
			title: note.title,
			type: noteType,
			content: note.content,
			tags: note.tags,
			linkedNotes
		};

		noteChatStore.openForNote(context);
	}
</script>

<div class="min-h-screen">
	<!-- Header with back button -->
	<header
		class="sticky top-0 z-20 glass-prominent border-b border-[var(--glass-border-subtle)] px-4 py-3"
	>
		<div class="max-w-4xl mx-auto flex items-center gap-3">
			<button
				onclick={goBack}
				class="p-2 -ml-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
			>
				<span class="text-xl">←</span>
			</button>
			<div class="flex-1 min-w-0">
				<!-- Breadcrumb -->
				<div class="flex items-center gap-1 text-sm text-[var(--color-text-tertiary)]">
					<span>Notes</span>
					{#each pathParts as part, i}
						<span>/</span>
						<span class={i === pathParts.length - 1 ? 'text-[var(--color-text-primary)]' : ''}>
							{part}
						</span>
					{/each}
				</div>
			</div>
			<button
				onclick={handleOpenChat}
				class="p-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
				title="Discuter de cette note"
			>
				<span class="text-xl">💬</span>
			</button>
			<button
				onclick={() => (showRetoucheHistory = true)}
				class="p-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
				title="Historique des retouches IA"
			>
				<span class="text-xl">📜</span>
			</button>
			<button
				onclick={() => (showHistory = true)}
				class="p-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
				title="Historique des versions"
			>
				<span class="text-xl">🕐</span>
			</button>
			<button
				onclick={toggleEdit}
				class="p-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
			>
				<span class="text-xl">{editing ? '✓' : '✏️'}</span>
			</button>
		</div>
	</header>

	{#if loading}
		<div class="flex justify-center py-16">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if note}
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
			<!-- Folder path -->
			<div
				class="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]"
				data-testid="note-folder"
			>
				<span>📁</span>
				<span>{extractFolder(note.path)}</span>
			</div>

			<!-- Meta info -->
			<div class="flex flex-wrap items-center gap-2">
				{#if note.pinned}
					<Badge>📌 Épinglée</Badge>
				{/if}
				{#each note.tags as tag}
					<Badge>{tag}</Badge>
				{/each}
			</div>

			<!-- Title -->
			<h1 class="text-2xl font-bold text-[var(--color-text-primary)]">
				{note.title}
			</h1>

			<!-- Dates -->
			<div class="text-sm text-[var(--color-text-tertiary)] flex flex-wrap gap-4">
				<span>Créée: {formatDate(note.created_at)}</span>
				<span>Modifiée: {formatDate(note.updated_at)}</span>
			</div>

			<!-- Content -->
			{#if editing}
				<div data-testid="note-editor">
					<MarkdownEditor
						bind:content={note.content}
						onSave={handleSave}
						placeholder="Commencez à écrire votre note..."
					/>
				</div>
			{:else}
				<Card variant="glass-subtle">
					<div class="p-4 md:p-6" data-testid="note-preview">
						<MarkdownPreview content={note.content} />
					</div>
				</Card>
			{/if}

			<!-- Related Items -->
			<section>
				<h3
					class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3"
				>
					Éléments liés
				</h3>
				<div class="space-y-2">
					<Card variant="glass" interactive padding="sm">
						<div class="flex items-center gap-3 p-2">
							<span class="text-lg">📧</span>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
									Email: Compte-rendu réunion Alpha
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Il y a 3 jours</p>
							</div>
						</div>
					</Card>
					<Card variant="glass" interactive padding="sm">
						<div class="flex items-center gap-3 p-2">
							<span class="text-lg">📅</span>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
									Prochaine réunion: Lundi 10h
								</p>
								<p class="text-xs text-[var(--color-text-tertiary)]">Dans 3 jours</p>
							</div>
						</div>
					</Card>
				</div>
			</section>
		</main>
	{:else}
		<div class="p-8 text-center">
			{#if error}
				<p class="text-red-400 mb-2">Erreur: {error}</p>
				<button
					onclick={() => noteId && loadNote(noteId)}
					class="text-[var(--color-accent)] hover:underline"
				>
					Réessayer
				</button>
			{:else}
				<p class="text-[var(--color-text-tertiary)]">Note introuvable</p>
			{/if}
		</div>
	{/if}
</div>

<!-- Version history modal -->
{#if note}
	<NoteHistory noteId={note.id} bind:open={showHistory} onRestore={handleRestore} />
	<RetoucheHistory noteId={note.id} bind:open={showRetoucheHistory} />
{/if}
