<script lang="ts">
	import { Card, Button } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';

	// Sync state
	let isSyncing = $state(false);
	let lastSyncTime = $state<string | null>(null);

	async function syncWithAppleNotes() {
		isSyncing = true;
		try {
			// Simulated API call - would call backend sync endpoint
			await new Promise(resolve => setTimeout(resolve, 2000));
			lastSyncTime = new Date().toISOString();
			console.log('Apple Notes synced successfully');
		} catch (error) {
			console.error('Sync failed:', error);
		} finally {
			isSyncing = false;
		}
	}

	interface Note {
		id: string;
		title: string;
		excerpt: string;
		path: string; // Full path like "Projets/Scapin/Architecture"
		tags: string[];
		updated_at: string;
		pinned?: boolean;
	}

	interface FolderNode {
		name: string;
		path: string;
		notes: Note[];
		children: Record<string, FolderNode>;
		expanded: boolean;
	}

	// Mock notes data with hierarchical paths
	const mockNotes: Note[] = [
		{
			id: '1',
			title: 'Architecture Scapin v2',
			excerpt: 'Notes sur la nouvelle architecture cognitive avec les valets Sancho, Passepartout, Planchet...',
			path: 'Projets/Scapin/Architecture',
			tags: ['architecture', 'design'],
			updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
			pinned: true
		},
		{
			id: '2',
			title: 'Réunion Client ABC - Compte-rendu',
			excerpt: 'Points discutés : budget Q1, roadmap produit, échéances livraison...',
			path: 'Clients/ABC/Réunions',
			tags: ['réunion', 'client'],
			updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
		},
		{
			id: '3',
			title: 'Ideas - Nouvelles fonctionnalités',
			excerpt: 'Brainstorming sur les prochaines features : dark mode, notifications push, sync offline...',
			path: 'Ideas',
			tags: ['brainstorm', 'features'],
			updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
			pinned: true
		},
		{
			id: '4',
			title: 'Guide déploiement v2.1',
			excerpt: 'Procédure de déploiement : 1. Backup DB, 2. Migration, 3. Tests smoke...',
			path: 'Projets/Scapin/Documentation',
			tags: ['devops', 'procédure'],
			updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString()
		},
		{
			id: '5',
			title: 'Weekly Review - Semaine 1',
			excerpt: 'Accomplissements de la semaine, blocages rencontrés, objectifs semaine prochaine...',
			path: 'Journal/2026',
			tags: ['review', 'journal'],
			updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
		},
		{
			id: '6',
			title: 'Contacts Client ABC',
			excerpt: 'Liste des contacts principaux, organigramme, historique des interactions...',
			path: 'Clients/ABC',
			tags: ['contacts', 'client'],
			updated_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString()
		},
		{
			id: '7',
			title: 'API Design Guidelines',
			excerpt: 'Conventions REST, versioning, pagination, error handling...',
			path: 'Projets/Scapin/Documentation',
			tags: ['api', 'guidelines'],
			updated_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString()
		}
	];

	// Build folder tree structure
	let folderTree = $state<Record<string, FolderNode>>({});

	function buildFolderTree(notes: Note[]): Record<string, FolderNode> {
		const tree: Record<string, FolderNode> = {};

		for (const note of notes) {
			const parts = note.path.split('/');
			let current = tree;
			let currentPath = '';

			for (let i = 0; i < parts.length; i++) {
				const part = parts[i];
				currentPath = currentPath ? `${currentPath}/${part}` : part;

				if (!current[part]) {
					current[part] = {
						name: part,
						path: currentPath,
						notes: [],
						children: {},
						expanded: i === 0 // Expand first level by default
					};
				}

				// Add note to the deepest folder
				if (i === parts.length - 1) {
					current[part].notes.push(note);
				}

				current = current[part].children;
			}
		}

		return tree;
	}

	// Initialize folder tree
	$effect(() => {
		folderTree = buildFolderTree(mockNotes);
	});

	const pinnedNotes = $derived(mockNotes.filter(n => n.pinned));
	const recentNotes = $derived(
		[...mockNotes]
			.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
			.slice(0, 5)
	);

	function toggleFolder(path: string) {
		const parts = path.split('/');
		let current = folderTree;

		for (let i = 0; i < parts.length - 1; i++) {
			current = current[parts[i]].children;
		}

		const folder = current[parts[parts.length - 1]];
		if (folder) {
			folder.expanded = !folder.expanded;
			folderTree = { ...folderTree }; // Trigger reactivity
		}
	}

	let activeView: 'tree' | 'recent' = $state('tree');
</script>

<div class="p-4 md:p-6 max-w-6xl mx-auto">
	<!-- Header -->
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			📝 Notes
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Votre base de connaissances personnelle
		</p>
	</header>

	<!-- Quick Actions -->
	<section class="mb-6 flex flex-wrap gap-3">
		<Button variant="primary" onclick={() => console.log('New note')}>
			+ Nouvelle note
		</Button>
		<Button variant="secondary" onclick={() => console.log('Import')}>
			📥 Importer
		</Button>
		<Button
			variant="secondary"
			onclick={syncWithAppleNotes}
			disabled={isSyncing}
		>
			{#if isSyncing}
				<span class="inline-block animate-spin mr-1">⟳</span> Synchro...
			{:else}
				🍎 Sync Apple Notes
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
				📁 Dossiers
			</button>
			<button
				type="button"
				class="px-3 py-1.5 rounded-lg text-sm transition-colors {activeView === 'recent' ? 'bg-[var(--color-accent)] text-white' : 'text-[var(--color-text-secondary)]'}"
				onclick={() => activeView = 'recent'}
			>
				🕐 Récents
			</button>
		</div>
	</section>

	<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
		<!-- Sidebar: Folder Tree (desktop) or hidden (mobile in tree view) -->
		<aside class="hidden lg:block">
			<!-- Pinned Notes -->
			{#if pinnedNotes.length > 0}
				<div class="mb-6">
					<h2 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3 flex items-center gap-2">
						<span>📌</span> Épinglées
					</h2>
					<div class="space-y-1">
						{#each pinnedNotes as note (note.id)}
							<button
								type="button"
								onclick={() => console.log('Open note', note.id)}
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
			<div class="space-y-0.5">
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
							{#each pinnedNotes as note (note.id)}
								<Card interactive onclick={() => console.log('Open note', note.id)} padding="md">
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
						{#each recentNotes as note (note.id)}
							{@render noteCard(note)}
						{/each}
					</div>
				</section>
			{/if}
		</main>
	</div>
</div>

{#snippet folderItem(folder: FolderNode, depth: number)}
	<div style="padding-left: {depth * 12}px">
		<button
			type="button"
			onclick={() => toggleFolder(folder.path)}
			class="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors text-left"
		>
			<span class="text-sm transition-transform {folder.expanded ? 'rotate-90' : ''}">▶</span>
			<span class="text-sm">📁</span>
			<span class="text-sm text-[var(--color-text-primary)] flex-1 truncate">{folder.name}</span>
			<span class="text-xs text-[var(--color-text-tertiary)]">{folder.notes.length}</span>
		</button>

		{#if folder.expanded}
			{#each Object.entries(folder.children) as [childName, childFolder]}
				{@render folderItem(childFolder, depth + 1)}
			{/each}
		{/if}
	</div>
{/snippet}

{#snippet folderContents(folder: FolderNode)}
	{#if folder.notes.length > 0}
		<section class="mb-6">
			<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
				<span>📁</span> {folder.path}
				<span class="text-sm font-normal text-[var(--color-text-tertiary)]">
					({folder.notes.length})
				</span>
			</h2>
			<div class="space-y-3">
				{#each folder.notes as note (note.id)}
					{@render noteCard(note)}
				{/each}
			</div>
		</section>
	{/if}

	{#each Object.values(folder.children) as childFolder}
		{@render folderContents(childFolder)}
	{/each}
{/snippet}

{#snippet noteCard(note: Note)}
	<Card interactive onclick={() => console.log('Open note', note.id)} padding="md">
		<div class="flex items-start gap-4">
			<div class="flex-1 min-w-0">
				<div class="flex flex-wrap items-center gap-2 mb-1">
					{#if note.pinned}
						<span class="text-sm" title="Épinglée">📌</span>
					{/if}
					<span class="text-xs text-[var(--color-text-tertiary)]">
						{note.path}
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
