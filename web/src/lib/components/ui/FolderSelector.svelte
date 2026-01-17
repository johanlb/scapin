<script lang="ts">
	import { onMount } from 'svelte';
	import { getFolderTree, getFolderSuggestions, createFolder } from '$lib/api';
	import type { FolderTreeNode, FolderSuggestion, FolderSuggestions } from '$lib/api';
	import Button from './Button.svelte';
	import Input from './Input.svelte';

	interface Props {
		senderEmail?: string;
		subject?: string;
		onSelect: (folder: string) => void;
		onCancel: () => void;
	}

	let { senderEmail, subject, onSelect, onCancel }: Props = $props();

	// State
	let suggestions: FolderSuggestion[] = $state([]);
	let recentFolders: string[] = $state([]);
	let popularFolders: string[] = $state([]);
	let folderTree: FolderTreeNode[] = $state([]);
	let searchQuery = $state('');
	let newFolderPath = $state('');
	let showCreateFolder = $state(false);
	let isCreatingFolder = $state(false);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let expandedFolders = $state<Set<string>>(new Set());

	// Filtered folders based on search
	const filteredTree = $derived(
		searchQuery.trim()
			? filterTree(folderTree, searchQuery.toLowerCase())
			: folderTree
	);

	// Flatten tree for search
	function filterTree(nodes: FolderTreeNode[], query: string): FolderTreeNode[] {
		const result: FolderTreeNode[] = [];
		for (const node of nodes) {
			const matches = node.name.toLowerCase().includes(query) ||
				node.path.toLowerCase().includes(query);
			const filteredChildren = filterTree(node.children || [], query);

			if (matches || filteredChildren.length > 0) {
				result.push({
					...node,
					children: filteredChildren
				});
			}
		}
		return result;
	}

	// Get all folder paths from tree (flattened)
	function getAllFolderPaths(nodes: FolderTreeNode[]): string[] {
		const paths: string[] = [];
		for (const node of nodes) {
			paths.push(node.path);
			if (node.children?.length) {
				paths.push(...getAllFolderPaths(node.children));
			}
		}
		return paths;
	}

	// Expand all folders containing search matches
	$effect(() => {
		if (searchQuery.trim()) {
			const allPaths = getAllFolderPaths(filteredTree);
			expandedFolders = new Set(allPaths);
		}
	});

	onMount(async () => {
		await loadData();
	});

	async function loadData() {
		isLoading = true;
		error = null;

		try {
			// Load suggestions and tree in parallel
			const [suggestionsData, treeData] = await Promise.all([
				getFolderSuggestions(senderEmail, subject, 5),
				getFolderTree()
			]);

			suggestions = suggestionsData.suggestions;
			recentFolders = suggestionsData.recent_folders;
			popularFolders = suggestionsData.popular_folders;
			folderTree = treeData;

			// Auto-expand first level
			for (const node of folderTree) {
				if (node.children?.length) {
					expandedFolders.add(node.path);
				}
			}
			expandedFolders = new Set(expandedFolders);
		} catch (e) {
			console.error('Failed to load folders:', e);
			error = 'Impossible de charger les dossiers';
		} finally {
			isLoading = false;
		}
	}

	function handleSelectFolder(path: string) {
		onSelect(path);
	}

	function toggleFolder(path: string) {
		if (expandedFolders.has(path)) {
			expandedFolders.delete(path);
		} else {
			expandedFolders.add(path);
		}
		expandedFolders = new Set(expandedFolders);
	}

	async function handleCreateFolder() {
		if (!newFolderPath.trim() || isCreatingFolder) return;

		isCreatingFolder = true;
		try {
			await createFolder(newFolderPath.trim());
			// Select the newly created folder
			onSelect(newFolderPath.trim());
		} catch (e) {
			console.error('Failed to create folder:', e);
			error = 'Impossible de créer le dossier';
		} finally {
			isCreatingFolder = false;
		}
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.8) return 'var(--color-success)';
		if (confidence >= 0.5) return 'var(--color-accent)';
		return 'var(--color-text-secondary)';
	}

	function getConfidenceLabel(confidence: number): string {
		if (confidence >= 0.8) return 'Très probable';
		if (confidence >= 0.5) return 'Probable';
		return 'Suggestion';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onCancel();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="folder-selector-overlay"
	onclick={onCancel}
	onkeydown={(e) => e.key === 'Escape' && onCancel()}
	role="dialog"
	aria-modal="true"
	tabindex="-1"
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="folder-selector" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} data-testid="folder-selector">
		<header class="selector-header">
			<h2>Choisir un dossier</h2>
			<button class="close-btn" onclick={onCancel} aria-label="Fermer">×</button>
		</header>

		{#if isLoading}
			<div class="loading-state">
				<span class="spinner"></span>
				<span>Chargement des dossiers...</span>
			</div>
		{:else if error}
			<div class="error-state">
				<span class="error-icon">⚠️</span>
				<span>{error}</span>
				<Button variant="ghost" size="sm" onclick={loadData}>Réessayer</Button>
			</div>
		{:else}
			<!-- AI Suggestions -->
			{#if suggestions.length > 0}
				<section class="suggestions-section">
					<h3>
						<span class="section-icon">✨</span>
						Suggestions intelligentes
					</h3>
					<div class="suggestions-list">
						{#each suggestions as suggestion}
							<button
								class="suggestion-item"
								onclick={() => handleSelectFolder(suggestion.folder)}
								data-testid="folder-suggestion"
							>
								<div class="suggestion-main">
									<span class="folder-icon">📁</span>
									<span class="folder-path">{suggestion.folder}</span>
								</div>
								<div class="suggestion-meta">
									<span
										class="confidence-badge"
										style="--confidence-color: {getConfidenceColor(suggestion.confidence)}"
									>
										{getConfidenceLabel(suggestion.confidence)}
									</span>
									<span class="suggestion-reason">{suggestion.reason}</span>
								</div>
							</button>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Recent Folders -->
			{#if recentFolders.length > 0}
				<section class="recent-section">
					<h3>
						<span class="section-icon">🕐</span>
						Dossiers récents
					</h3>
					<div class="folder-chips">
						{#each recentFolders.slice(0, 5) as folder}
							<button
								class="folder-chip"
								onclick={() => handleSelectFolder(folder)}
								title={folder}
							>
								{folder}
							</button>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Search -->
			<div class="search-section" data-testid="folder-search">
				<Input
					type="text"
					placeholder="Rechercher un dossier..."
					bind:value={searchQuery}
				/>
			</div>

			<!-- Folder Tree -->
			<section class="tree-section">
				<div class="tree-container">
					{#if filteredTree.length === 0}
						<div class="empty-state">
							{#if searchQuery.trim()}
								Aucun dossier trouvé pour "{searchQuery}"
							{:else}
								Aucun dossier disponible
							{/if}
						</div>
					{:else}
						{#each filteredTree as node}
							{@render FolderNode(node, 0)}
						{/each}
					{/if}
				</div>
			</section>

			<!-- Create New Folder -->
			<section class="create-section">
				{#if showCreateFolder}
					<div class="create-form" data-testid="new-folder-input">
						<Input
							type="text"
							placeholder="Archive/Nouveau/Dossier"
							bind:value={newFolderPath}
						/>
						<Button
							variant="primary"
							size="sm"
							onclick={handleCreateFolder}
							disabled={!newFolderPath.trim() || isCreatingFolder}
						>
							{isCreatingFolder ? 'Création...' : 'Créer'}
						</Button>
						<Button
							variant="ghost"
							size="sm"
							onclick={() => { showCreateFolder = false; newFolderPath = ''; }}
						>
							Annuler
						</Button>
					</div>
				{:else}
					<Button
						variant="ghost"
						size="sm"
						onclick={() => showCreateFolder = true}
						data-testid="create-folder-btn"
					>
						<span class="btn-icon">+</span>
						Créer un nouveau dossier
					</Button>
				{/if}
			</section>
		{/if}
	</div>
</div>

{#snippet FolderNode(node: FolderTreeNode, depth: number)}
	<div class="tree-node" style="--depth: {depth}">
		<div class="node-row">
			<button
				class="node-toggle"
				onclick={() => toggleFolder(node.path)}
				aria-label={node.children?.length ? (expandedFolders.has(node.path) ? 'Réduire' : 'Développer') : 'Dossier vide'}
			>
				{#if node.children?.length}
					<span class="expand-icon" class:expanded={expandedFolders.has(node.path)}>
						▶
					</span>
				{:else}
					<span class="expand-spacer"></span>
				{/if}
				<span class="folder-icon">📁</span>
				<span class="node-name" title={node.path}>{node.name}</span>
			</button>
			<button
				class="node-select-btn"
				onclick={() => handleSelectFolder(node.path)}
				aria-label="Sélectionner ce dossier"
			>
				Sélectionner
			</button>
		</div>

		{#if node.children?.length && expandedFolders.has(node.path)}
			<div class="node-children">
				{#each node.children as child}
					{@render FolderNode(child, depth + 1)}
				{/each}
			</div>
		{/if}
	</div>
{/snippet}

<style>
	.folder-selector-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: rgba(0, 0, 0, 0.85);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 9999;
		padding: 1rem;
	}

	.folder-selector {
		background-color: #1c1c1e;
		border: 1px solid #3a3a3c;
		border-radius: 16px;
		width: 100%;
		max-width: 480px;
		max-height: 85vh;
		display: flex;
		flex-direction: column;
		box-shadow: 0 25px 50px rgba(0, 0, 0, 0.8);
		overflow: hidden;
	}

	.selector-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-bottom: 1px solid #3a3a3c;
		background-color: #2c2c2e;
	}

	.selector-header h2 {
		font-size: 1.1rem;
		font-weight: 600;
		margin: 0;
		color: #ffffff;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 1.5rem;
		color: #8e8e93;
		cursor: pointer;
		padding: 0.25rem;
		line-height: 1;
	}

	.close-btn:hover {
		color: #ffffff;
	}

	.loading-state,
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 3rem 1rem;
		color: #8e8e93;
	}

	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid #3a3a3c;
		border-top-color: #0a84ff;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-icon {
		font-size: 1.5rem;
	}

	section {
		padding: 0.75rem 1.25rem;
	}

	section h3 {
		font-size: 0.8rem;
		font-weight: 600;
		color: #8e8e93;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin: 0 0 0.5rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.section-icon {
		font-size: 1rem;
	}

	.suggestions-section {
		border-bottom: 1px solid #3a3a3c;
	}

	.suggestions-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.suggestion-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.75rem;
		background-color: #2c2c2e;
		border: 1px solid #3a3a3c;
		border-radius: 8px;
		cursor: pointer;
		text-align: left;
		width: 100%;
		transition: all 0.15s ease;
		color: #ffffff;
	}

	.suggestion-item:hover {
		border-color: #0a84ff;
		background-color: #3a3a3c;
	}

	.suggestion-main {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 500;
	}

	.folder-path {
		font-family: var(--font-mono);
		font-size: 0.9rem;
	}

	.suggestion-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8rem;
		color: #8e8e93;
		padding-left: 1.5rem;
	}

	.confidence-badge {
		background: color-mix(in srgb, var(--confidence-color) 15%, transparent);
		color: var(--confidence-color);
		padding: 0.125rem 0.5rem;
		border-radius: 4px;
		font-weight: 500;
		font-size: 0.75rem;
	}

	.recent-section {
		border-bottom: 1px solid #3a3a3c;
	}

	.folder-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.folder-chip {
		background-color: #2c2c2e;
		border: 1px solid #3a3a3c;
		border-radius: 16px;
		padding: 0.375rem 0.75rem;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.15s ease;
		color: #ffffff;
	}

	.folder-chip:hover {
		border-color: #0a84ff;
		background-color: #3a3a3c;
	}

	.search-section {
		padding: 0.75rem 1.25rem;
		border-bottom: 1px solid #3a3a3c;
	}

	.tree-section {
		flex: 1;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		min-height: 200px;
		max-height: 300px;
	}

	.tree-container {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem 0;
	}

	.empty-state {
		text-align: center;
		padding: 2rem 1rem;
		color: #8e8e93;
	}

	.tree-node {
		user-select: none;
	}

	.node-row {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		width: 100%;
		padding: 0.25rem 0.5rem;
		padding-left: calc(0.5rem + var(--depth) * 1.25rem);
		padding-right: 0.5rem;
		transition: background 0.1s ease;
	}

	.node-row:hover {
		background-color: #3a3a3c;
	}

	.node-row:hover .node-select-btn {
		opacity: 1;
	}

	.node-toggle {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		flex: 1;
		background: none;
		border: none;
		text-align: left;
		cursor: pointer;
		font-size: 0.9rem;
		padding: 0.25rem 0;
		color: inherit;
	}

	.node-select-btn {
		opacity: 0;
		background-color: #0a84ff;
		color: white;
		border: none;
		border-radius: 4px;
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.15s ease, background-color 0.1s ease;
		white-space: nowrap;
	}

	.node-select-btn:hover {
		background-color: #0077ed;
	}

	.node-select-btn:focus {
		opacity: 1;
		outline: 2px solid #0a84ff;
		outline-offset: 2px;
	}

	.expand-icon {
		font-size: 0.6rem;
		color: #8e8e93;
		transition: transform 0.15s ease;
		width: 1rem;
		text-align: center;
	}

	.expand-icon.expanded {
		transform: rotate(90deg);
	}

	.expand-spacer {
		width: 1rem;
	}

	.folder-icon {
		font-size: 1rem;
	}

	.node-name {
		flex: 1;
		color: #ffffff;
	}

	.node-children {
		margin-left: 0;
	}

	.create-section {
		border-top: 1px solid #3a3a3c;
		padding: 1rem 1.25rem;
	}

	.create-form {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.create-form :global(input) {
		flex: 1;
	}

	.btn-icon {
		font-size: 1.1rem;
		font-weight: 600;
	}
</style>
