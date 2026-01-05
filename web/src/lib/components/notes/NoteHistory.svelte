<script lang="ts">
	/**
	 * NoteHistory Component
	 * Modal showing version history with compare and restore functionality
	 */
	import { Modal, Button, Card } from '$lib/components/ui';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		getNoteVersions,
		diffNoteVersions,
		restoreNoteVersion,
		type NoteVersion,
		type NoteDiff
	} from '$lib/api/client';
	import VersionDiff from './VersionDiff.svelte';

	interface Props {
		noteId: string;
		open: boolean;
		onRestore?: () => void;
	}

	let { noteId, open = $bindable(false), onRestore }: Props = $props();

	let versions = $state<NoteVersion[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Selection for comparison
	let selectedVersions = $state<string[]>([]);
	let diff = $state<NoteDiff | null>(null);
	let loadingDiff = $state(false);
	let showDiff = $state(false);

	// Restore confirmation
	let confirmRestore = $state(false);
	let restoring = $state(false);
	let versionToRestore = $state<string | null>(null);

	// Load versions when modal opens
	$effect(() => {
		if (open && noteId) {
			loadVersions();
		} else {
			// Reset state when closed
			selectedVersions = [];
			diff = null;
			showDiff = false;
			confirmRestore = false;
			versionToRestore = null;
		}
	});

	async function loadVersions() {
		loading = true;
		error = null;
		try {
			const response = await getNoteVersions(noteId);
			versions = response.versions;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
			toastStore.error('Impossible de charger l\'historique');
		} finally {
			loading = false;
		}
	}

	function toggleVersionSelection(versionId: string) {
		if (selectedVersions.includes(versionId)) {
			selectedVersions = selectedVersions.filter((v) => v !== versionId);
		} else if (selectedVersions.length < 2) {
			selectedVersions = [...selectedVersions, versionId];
		} else {
			// Replace the first selection
			selectedVersions = [selectedVersions[1], versionId];
		}
		// Reset diff when selection changes
		diff = null;
		showDiff = false;
	}

	async function compareVersions() {
		if (selectedVersions.length !== 2) return;

		loadingDiff = true;
		try {
			// Sort to ensure older version is first
			const [v1, v2] = selectedVersions.sort((a, b) => {
				const versionA = versions.find((v) => v.version_id === a);
				const versionB = versions.find((v) => v.version_id === b);
				if (!versionA || !versionB) return 0;
				return new Date(versionA.timestamp).getTime() - new Date(versionB.timestamp).getTime();
			});

			diff = await diffNoteVersions(noteId, v1, v2);
			showDiff = true;
		} catch (e) {
			toastStore.error('Impossible de comparer les versions');
		} finally {
			loadingDiff = false;
		}
	}

	function initiateRestore(versionId: string) {
		versionToRestore = versionId;
		confirmRestore = true;
	}

	async function executeRestore() {
		if (!versionToRestore) return;

		restoring = true;
		try {
			await restoreNoteVersion(noteId, versionToRestore);
			toastStore.success('Version restaurée avec succès');
			confirmRestore = false;
			open = false;
			onRestore?.();
		} catch (e) {
			toastStore.error('Impossible de restaurer la version');
		} finally {
			restoring = false;
		}
	}

	function formatDate(timestamp: string): string {
		return new Date(timestamp).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getVersionLabel(versionId: string): string {
		const version = versions.find((v) => v.version_id === versionId);
		return version ? formatDate(version.timestamp) : versionId;
	}
</script>

<Modal bind:open title="Historique des versions" size="lg">
	{#if loading}
		<div class="flex justify-center py-8">
			<div class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
		</div>
	{:else if error}
		<div class="text-center py-8 text-[var(--color-error)]">
			<p>{error}</p>
			<Button variant="ghost" onclick={loadVersions} class="mt-4">Réessayer</Button>
		</div>
	{:else if versions.length === 0}
		<div class="text-center py-8 text-[var(--color-text-secondary)]">
			<p>Aucune version disponible</p>
		</div>
	{:else}
		<!-- Version list -->
		<div class="space-y-2 max-h-[300px] overflow-y-auto">
			{#each versions as version, index (version.version_id)}
				<Card
					variant={selectedVersions.includes(version.version_id) ? 'glass-prominent' : 'glass'}
					interactive
					padding="sm"
					onclick={() => toggleVersionSelection(version.version_id)}
				>
					<div class="flex items-center gap-3 p-2">
						<!-- Selection indicator -->
						<div
							class="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-colors"
							class:border-[var(--color-accent)]={selectedVersions.includes(version.version_id)}
							class:bg-[var(--color-accent)]={selectedVersions.includes(version.version_id)}
							class:border-[var(--color-border)]={!selectedVersions.includes(version.version_id)}
						>
							{#if selectedVersions.includes(version.version_id)}
								<svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
								</svg>
							{/if}
						</div>

						<!-- Version info -->
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<code class="text-xs font-mono text-[var(--color-accent)]">{version.version_id}</code>
								{#if index === 0}
									<span class="text-xs px-1.5 py-0.5 rounded bg-[var(--color-accent)]/10 text-[var(--color-accent)]">
										Actuel
									</span>
								{/if}
							</div>
							<p class="text-sm text-[var(--color-text-primary)] truncate mt-0.5">{version.message}</p>
							<p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
								{formatDate(version.timestamp)} · {version.author}
							</p>
						</div>

						<!-- Restore button -->
						{#if index > 0}
							<Button
								variant="ghost"
								size="sm"
								onclick={(e: MouseEvent) => {
									e.stopPropagation();
									initiateRestore(version.version_id);
								}}
							>
								Restaurer
							</Button>
						{/if}
					</div>
				</Card>
			{/each}
		</div>

		<!-- Compare button -->
		{#if selectedVersions.length === 2}
			<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
				<Button
					variant="secondary"
					onclick={compareVersions}
					loading={loadingDiff}
					class="w-full"
				>
					Comparer les versions sélectionnées
				</Button>
			</div>
		{/if}

		<!-- Diff display -->
		{#if showDiff && diff}
			<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
				<VersionDiff
					{diff}
					fromLabel={getVersionLabel(diff.from_version)}
					toLabel={getVersionLabel(diff.to_version)}
				/>
			</div>
		{/if}
	{/if}

	{#snippet footer()}
		<Button variant="ghost" onclick={() => (open = false)}>Fermer</Button>
	{/snippet}
</Modal>

<!-- Restore confirmation modal -->
<Modal bind:open={confirmRestore} title="Confirmer la restauration" size="sm">
	<p class="text-[var(--color-text-secondary)]">
		Voulez-vous restaurer cette version ? Une nouvelle version sera créée avec le contenu restauré.
	</p>

	{#snippet footer()}
		<Button variant="ghost" onclick={() => (confirmRestore = false)}>Annuler</Button>
		<Button variant="primary" onclick={executeRestore} loading={restoring}>
			Restaurer
		</Button>
	{/snippet}
</Modal>
