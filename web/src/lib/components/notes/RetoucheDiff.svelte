<script lang="ts">
	/**
	 * RetoucheDiff Component
	 * Modal showing proposed retouche changes with apply/ignore options
	 */
	import { Modal, Button, Card, Badge } from '$lib/components/ui';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		previewRetouche,
		applyRetouche,
		type RetouchePreview,
		type RetoucheActionPreview
	} from '$lib/api/client';

	interface Props {
		noteId: string;
		open: boolean;
		onApplied?: () => void;
	}

	let { noteId, open = $bindable(false), onApplied }: Props = $props();

	let preview = $state<RetouchePreview | null>(null);
	let loading = $state(false);
	let applying = $state(false);
	let error = $state<string | null>(null);
	let selectedActions = $state<Set<number>>(new Set());

	// Load preview when modal opens
	$effect(() => {
		if (open && noteId) {
			loadPreview();
		} else {
			preview = null;
			selectedActions = new Set();
		}
	});

	async function loadPreview() {
		loading = true;
		error = null;
		try {
			preview = await previewRetouche(noteId);
			// Pre-select auto-apply actions
			selectedActions = new Set(
				preview.actions.map((a, i) => (a.auto_apply ? i : -1)).filter((i) => i >= 0)
			);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
			toastStore.error('Impossible de charger la prévisualisation');
		} finally {
			loading = false;
		}
	}

	async function handleApply() {
		if (!preview) return;

		applying = true;
		try {
			await applyRetouche(noteId, {
				action_indices: Array.from(selectedActions)
			});
			toastStore.success('Retouche appliquée avec succès');
			open = false;
			onApplied?.();
		} catch (e) {
			toastStore.error("Erreur lors de l'application de la retouche");
		} finally {
			applying = false;
		}
	}

	async function handleApplyAll() {
		if (!preview) return;

		applying = true;
		try {
			await applyRetouche(noteId, { apply_all: true });
			toastStore.success('Toutes les retouches appliquées');
			open = false;
			onApplied?.();
		} catch (e) {
			toastStore.error("Erreur lors de l'application des retouches");
		} finally {
			applying = false;
		}
	}

	function toggleAction(index: number) {
		const newSet = new Set(selectedActions);
		if (newSet.has(index)) {
			newSet.delete(index);
		} else {
			newSet.add(index);
		}
		selectedActions = newSet;
	}

	function getActionIcon(actionType: string): string {
		const icons: Record<string, string> = {
			enrich: '✨',
			structure: '📐',
			summarize: '📝',
			score: '📊',
			inject_questions: '❓',
			suggest_links: '🔗',
			cleanup: '🧹',
			profile_insight: '🧠',
			create_omnifocus: '✅'
		};
		return icons[actionType] || '🔧';
	}

	function getActionLabel(actionType: string): string {
		const labels: Record<string, string> = {
			enrich: 'Enrichissement',
			structure: 'Restructuration',
			summarize: 'Résumé',
			score: 'Évaluation',
			inject_questions: 'Questions',
			suggest_links: 'Liens',
			cleanup: 'Nettoyage',
			profile_insight: 'Insights',
			create_omnifocus: 'Tâche OmniFocus'
		};
		return labels[actionType] || actionType;
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.85) return 'text-green-400';
		if (confidence >= 0.7) return 'text-yellow-400';
		return 'text-orange-400';
	}

	const qualityDelta = $derived.by(() => {
		if (!preview || preview.quality_before === null) return null;
		return preview.quality_after - preview.quality_before;
	});
</script>

<Modal
	bind:open
	title="Prévisualisation Retouche"
	size="lg"
	data-testid="retouche-preview-modal"
>
	{#if loading}
		<div class="flex justify-center py-8">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if error}
		<div class="text-center py-8 text-[var(--color-error)]">
			<p>{error}</p>
			<Button variant="ghost" onclick={loadPreview} class="mt-4">Réessayer</Button>
		</div>
	{:else if !preview || preview.actions.length === 0}
		<div class="text-center py-8 text-[var(--color-text-secondary)]">
			<p class="text-4xl mb-4">✨</p>
			<p>Aucune amélioration suggérée</p>
			<p class="text-sm mt-2 text-[var(--color-text-tertiary)]">
				Cette note est déjà de bonne qualité
			</p>
		</div>
	{:else}
		<!-- Quality summary -->
		<div class="flex items-center gap-6 mb-6 p-4 rounded-xl glass-subtle">
			<div class="text-center">
				<div class="text-sm text-[var(--color-text-tertiary)] mb-1">Avant</div>
				<div
					class="text-2xl font-bold"
					class:text-gray-400={preview.quality_before === null}
					class:text-yellow-400={preview.quality_before !== null && preview.quality_before < 60}
					class:text-green-400={preview.quality_before !== null && preview.quality_before >= 60}
				>
					{preview.quality_before ?? '?'}%
				</div>
			</div>
			<div class="text-2xl text-[var(--color-text-tertiary)]">→</div>
			<div class="text-center">
				<div class="text-sm text-[var(--color-text-tertiary)] mb-1">Après</div>
				<div
					class="text-2xl font-bold"
					class:text-yellow-400={preview.quality_after < 60}
					class:text-green-400={preview.quality_after >= 60}
				>
					{preview.quality_after}%
				</div>
			</div>
			{#if qualityDelta !== null}
				<div class="ml-auto">
					<Badge
						class={qualityDelta > 0 ? 'bg-green-500/20 text-green-300' : 'bg-gray-500/20'}
					>
						{qualityDelta > 0 ? '+' : ''}{qualityDelta}%
					</Badge>
				</div>
			{/if}
		</div>

		<!-- Model info -->
		<div class="text-sm text-[var(--color-text-tertiary)] mb-4">
			Analysé par <span class="font-mono text-purple-400">{preview.model_used}</span>
		</div>

		<!-- Actions list -->
		<div class="space-y-3 max-h-[400px] overflow-y-auto pr-2">
			{#each preview.actions as action, index}
				<Card
					variant="glass"
					padding="sm"
					class="cursor-pointer transition-all {selectedActions.has(index)
						? 'ring-2 ring-[var(--color-accent)]'
						: 'opacity-70 hover:opacity-100'}"
					onclick={() => toggleAction(index)}
				>
					<div class="p-3">
						<div class="flex items-center gap-2 mb-2">
							<input
								type="checkbox"
								checked={selectedActions.has(index)}
								class="w-4 h-4 rounded accent-[var(--color-accent)]"
								onclick={(e) => e.stopPropagation()}
								onchange={() => toggleAction(index)}
							/>
							<span class="text-lg">{getActionIcon(action.action_type)}</span>
							<Badge>{getActionLabel(action.action_type)}</Badge>
							<span class={`text-xs font-mono ${getConfidenceColor(action.confidence)}`}>
								{(action.confidence * 100).toFixed(0)}%
							</span>
							{#if action.auto_apply}
								<Badge class="bg-green-500/20 text-green-300 text-xs">Auto</Badge>
							{/if}
						</div>

						<p class="text-sm text-[var(--color-text-secondary)]">
							{action.reasoning || 'Pas de justification'}
						</p>

						{#if action.content}
							<details class="mt-2">
								<summary
									class="text-xs text-[var(--color-accent)] cursor-pointer hover:underline"
								>
									Voir le contenu proposé
								</summary>
								<pre
									class="mt-2 p-2 text-xs bg-black/20 rounded overflow-x-auto whitespace-pre-wrap max-h-32"
								>{action.content}</pre>
							</details>
						{/if}
					</div>
				</Card>
			{/each}
		</div>

		<!-- Reasoning -->
		{#if preview.reasoning}
			<div class="mt-4 p-3 rounded-lg bg-[var(--glass-tint)] text-sm">
				<div class="text-xs text-[var(--color-text-tertiary)] mb-1">Analyse globale</div>
				<p class="text-[var(--color-text-secondary)]">{preview.reasoning}</p>
			</div>
		{/if}
	{/if}

	{#snippet footer()}
		<div class="flex gap-2 w-full">
			<Button variant="ghost" onclick={() => (open = false)} disabled={applying}>
				Ignorer
			</Button>
			<div class="flex-1"></div>
			{#if preview && preview.actions.length > 0}
				<Button
					variant="secondary"
					onclick={handleApplyAll}
					disabled={applying}
				>
					{applying ? 'Application...' : 'Tout appliquer'}
				</Button>
				<Button
					variant="primary"
					onclick={handleApply}
					disabled={applying || selectedActions.size === 0}
				>
					{applying ? 'Application...' : `Appliquer (${selectedActions.size})`}
				</Button>
			{/if}
		</div>
	{/snippet}
</Modal>
