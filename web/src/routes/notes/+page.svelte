<script lang="ts">
	import { Card, Button } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { onMount } from 'svelte';
	import {
		getNotesTree,
		syncAppleNotes,
		type Note,
		type FolderNode,
		type NotesTree
	} from '$lib/api/client';

	// Loading and error states
	let isLoading = $state(true);
	let loadError = $state<string | null>(null);

	// Sync state
	let isSyncing = $state(false);
	let lastSyncTime = $state<string | null>(null);

	// Data
	let notesData = $state<NotesTree | null>(null);
	let folderTree = $state<Record<string, FolderNodeWithExpanded>>({});

	// Extended folder type for UI state
	interface FolderNodeWithExpanded extends FolderNode {
		expanded: boolean;
		children: FolderNodeWithExpanded[];
	}

	async function loadNotes() {
		isLoading = true;
		loadError = null;
		try {
			notesData = await getNotesTree(10);
			folderTree = buildFolderTreeWithExpanded(notesData.folders);
		} catch (error) {
			loadError = error instanceof Error ? error.message : 'Erreur de chargement';
			console.error('Failed to load notes:', error);
		} finally {
			isLoading = false;
		}
	}

	function buildFolderTreeWithExpanded(folders: FolderNode[]): Record<string, FolderNodeWithExpanded> {
		const tree: Record<string, FolderNodeWithExpanded> = {};
		for (const folder of folders) {
			tree[folder.name] = {
				...folder,
				expanded: true, // Expand first level by default
				children: folder.children.map(child => convertToExpandable(child, false))
			};
		}
		return tree;
	}

	function convertToExpandable(folder: FolderNode, expanded: boolean): FolderNodeWithExpanded {
		return {
			...folder,
			expanded,
			children: folder.children.map(child => convertToExpandable(child, false))
		};
	}

	async function syncWithAppleNotes() {
		isSyncing = true;
		try {
			const status = await syncAppleNotes();
			if (status.errors.length > 0) {
				console.error('Sync errors:', status.errors);
			} else {
				lastSyncTime = new Date().toISOString();
				// Reload notes after sync
				await loadNotes();
			}
		} catch (error) {
			console.error('Sync failed:', error);
		} finally {
			isSyncing = false;
		}
	}

	onMount(() => {
		loadNotes();
	});

	const pinnedNotes = $derived(notesData?.pinned ?? []);
	const recentNotes = $derived(notesData?.recent ?? []);

	function toggleFolder(path: string) {
		const parts = path.split('/');
		let current = folderTree;

		for (let i = 0; i < parts.length - 1; i++) {
			const folder = current[parts[i]];
			if (folder) {
				const childIndex = folder.children.findIndex(c => c.name === parts[i + 1]);
				if (childIndex >= 0) {
					current = { [parts[i + 1]]: folder.children[childIndex] } as Record<string, FolderNodeWithExpanded>;
				}
			}
		}

		const finalPart = parts[parts.length - 1];
		if (parts.length === 1 && folderTree[finalPart]) {
			folderTree[finalPart].expanded = !folderTree[finalPart].expanded;
			folderTree = { ...folderTree }; // Trigger reactivity
		}
	}

	let activeView: 'tree' | 'recent' = $state('tree');
</script>

<div class="p-4 md:p-6 max-w-6xl mx-auto">
	<!-- Header -->
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			Carnets
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Vos notes et documents classés
		</p>
	</header>

	<!-- Quick Actions -->
	<section class="mb-6 flex flex-wrap gap-3">
		<Button variant="primary" onclick={() => console.log('New note')}>
			Rédiger
		</Button>
		<Button variant="secondary" onclick={() => console.log('Import')}>
			Recevoir
		</Button>
		<Button
			variant="secondary"
			onclick={syncWithAppleNotes}
			disabled={isSyncing}
		>
			{#if isSyncing}
				<span class="inline-block animate-spin mr-1">⟳</span> Synchro...
			{:else}
				Sync Apple Notes
			{/if}
		</Button>
		{#if lastSyncTime}
			<span class="self-center text-xs text-[var(--color-text-tertiary)]">
				Dernière synchro : {formatRelativeTime(lastSyncTime)}
			</span>
		{/if}
		<div class="flex-1"></div>
		<div class="flex gap-1 bg-[var(--color-bg-secondary)] rounded-xl p-1">
			<button
				type="button"
				class="px-3 py-1.5 rounded-lg text-sm transition-colors {activeView === 'tree' ? 'bg-[var(--color-accent)] text-white' : 'text-[var(--color-text-secondary)]'}"
				onclick={() => activeView = 'tree'}
			>
				Dossiers
			</button>
			<button
				type="button"
				class="px-3 py-1.5 rounded-lg text-sm transition-colors {activeView === 'recent' ? 'bg-[var(--color-accent)] text-white' : 'text-[var(--color-text-secondary)]'}"
				onclick={() => activeView = 'recent'}
			>
				Récents
			</button>
		</div>
	</section>

	<!-- Loading State -->
	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<div class="text-[var(--color-text-tertiary)]">
				<span class="inline-block animate-spin mr-2">⟳</span>
				Chargement des notes...
			</div>
		</div>
	{:else if loadError}
		<div class="py-12">
			<Card padding="lg">
				<div class="text-center">
					<p class="text-[var(--color-text-secondary)] mb-4">{loadError}</p>
					<Button variant="secondary" onclick={loadNotes}>Réessayer</Button>
				</div>
			</Card>
		</div>
	{:else if notesData && notesData.total_notes === 0}
		<div class="py-12">
			<Card padding="lg">
				<div class="text-center">
					<p class="text-[var(--color-text-secondary)] mb-2">Aucune note pour l'instant</p>
					<p class="text-sm text-[var(--color-text-tertiary)] mb-4">
						Créez votre première note ou synchronisez avec Apple Notes
					</p>
					<div class="flex gap-3 justify-center">
						<Button variant="primary" onclick={() => console.log('New note')}>
							Rédiger
						</Button>
						<Button variant="secondary" onclick={syncWithAppleNotes}>
							Sync Apple Notes
						</Button>
					</div>
				</div>
			</Card>
		</div>
	{:else}
		<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
			<!-- Sidebar: Folder Tree (desktop) -->
			<aside class="hidden lg:block">
				<!-- Pinned Notes -->
				{#if pinnedNotes.length > 0}
					<div class="mb-6">
						<h2 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3 flex items-center gap-2">
							<span>📌</span> Épinglées
						</h2>
						<div class="space-y-1">
							{#each pinnedNotes as note (note.note_id)}
								<button
									type="button"
									onclick={() => console.log('Open note', note.note_id)}
									class="w-full text-left px-3 py-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors"
								>
									<p class="text-sm text-[var(--color-text-primary)] truncate">{note.title}</p>
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Folder Tree -->
				<h2 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3">
					Dossiers
				</h2>
				<div class="space-y-0.5" data-testid="notes-tree">
					{#each Object.entries(folderTree) as [name, folder]}
						{@render folderItem(folder, 0)}
					{/each}
				</div>
			</aside>

			<!-- Main Content -->
			<main class="lg:col-span-3">
				{#if activeView === 'tree'}
					<!-- Mobile: Show pinned notes -->
					{#if pinnedNotes.length > 0}
						<section class="mb-6 lg:hidden">
							<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
								<span>📌</span> Notes épinglées
							</h2>
							<div class="space-y-2">
								{#each pinnedNotes as note (note.note_id)}
									<Card interactive onclick={() => console.log('Open note', note.note_id)} padding="md">
										<h3 class="font-semibold text-[var(--color-text-primary)]">{note.title}</h3>
										<p class="text-sm text-[var(--color-text-tertiary)] mt-1">{note.path}</p>
									</Card>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Folder Contents -->
					{#each Object.entries(folderTree) as [name, folder]}
						{@render folderContents(folder)}
					{/each}
				{:else}
					<!-- Recent Notes View -->
					<section>
						<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
							<span>🕐</span> Notes récentes
						</h2>
						<div class="space-y-3">
							{#each recentNotes as note (note.note_id)}
								{@render noteCard(note)}
							{/each}
						</div>
					</section>
				{/if}
			</main>
		</div>
	{/if}
</div>

{#snippet folderItem(folder: FolderNodeWithExpanded, depth: number)}
	<div style="padding-left: {depth * 12}px">
		<button
			type="button"
			onclick={() => toggleFolder(folder.path)}
			class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors text-left"
		>
			<span class="text-sm transition-transform {folder.expanded ? 'rotate-90' : ''}">▶</span>
			<span class="text-sm">📁</span>
			<span class="text-sm text-[var(--color-text-primary)] flex-1 truncate">{folder.name}</span>
			<span class="text-xs text-[var(--color-text-tertiary)]">{folder.note_count}</span>
		</button>

		{#if folder.expanded}
			{#each folder.children as childFolder}
				{@render folderItem(childFolder, depth + 1)}
			{/each}
		{/if}
	</div>
{/snippet}

{#snippet folderContents(folder: FolderNodeWithExpanded)}
	{#if folder.note_count > 0}
		<section class="mb-6">
			<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
				<span>📁</span> {folder.path}
				<span class="text-sm font-normal text-[var(--color-text-tertiary)]">
					({folder.note_count})
				</span>
			</h2>
			<!-- Notes would be loaded here via separate API call -->
			<p class="text-sm text-[var(--color-text-tertiary)]">
				{folder.note_count} note(s) dans ce dossier
			</p>
		</section>
	{/if}

	{#each folder.children as childFolder}
		{@render folderContents(childFolder)}
	{/each}
{/snippet}

{#snippet noteCard(note: Note)}
	<Card interactive onclick={() => console.log('Open note', note.note_id)} padding="md">
		<div class="flex items-start gap-4">
			<div class="flex-1 min-w-0">
				<div class="flex flex-wrap items-center gap-2 mb-1">
					{#if note.pinned}
						<span class="text-sm" title="Épinglée">📌</span>
					{/if}
					<span class="text-xs text-[var(--color-text-tertiary)]">
						{note.path || 'Sans dossier'}
					</span>
					<span class="text-[var(--color-text-tertiary)]">•</span>
					<span class="text-xs text-[var(--color-text-tertiary)]">
						{formatRelativeTime(note.updated_at)}
					</span>
				</div>
				<h3 class="font-semibold text-[var(--color-text-primary)] mb-1">
					{note.title}
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)] line-clamp-2">
					{note.excerpt}
				</p>
				{#if note.tags.length > 0}
					<div class="flex flex-wrap gap-1.5 mt-2">
						{#each note.tags as tag}
							<span class="px-2 py-0.5 text-xs bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] rounded-md">
								#{tag}
							</span>
						{/each}
					</div>
				{/if}
			</div>
			<span class="text-[var(--color-text-tertiary)] shrink-0">→</span>
		</div>
	</Card>
{/snippet}
