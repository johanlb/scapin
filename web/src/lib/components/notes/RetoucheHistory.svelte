<script lang="ts">
	/**
	 * RetoucheHistory Component
	 * Modal showing AI enrichment/retouche history for a note
	 */
	import { Modal, Button, Card, Badge } from '$lib/components/ui';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		getEnrichmentHistory,
		rollbackRetouche,
		type EnrichmentRecord,
		type EnrichmentHistory
	} from '$lib/api/client';

	interface Props {
		noteId: string;
		open: boolean;
		onRollback?: () => void;
	}

	let { noteId, open = $bindable(false), onRollback }: Props = $props();

	let history = $state<EnrichmentHistory | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let rollingBack = $state<number | null>(null);

	// Load history when modal opens
	$effect(() => {
		if (open && noteId) {
			loadHistory();
		} else {
			history = null;
		}
	});

	async function loadHistory() {
		loading = true;
		error = null;
		try {
			history = await getEnrichmentHistory(noteId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
			toastStore.error("Impossible de charger l'historique des retouches");
		} finally {
			loading = false;
		}
	}

	function formatDate(timestamp: string): string {
		return new Date(timestamp).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getActionIcon(actionType: string): string {
		const icons: Record<string, string> = {
			enrich: '✨',
			structure: '📐',
			summarize: '📝',
			score: '📊',
			inject_questions: '❓'
		};
		return icons[actionType] || '🔧';
	}

	function getActionLabel(actionType: string): string {
		const labels: Record<string, string> = {
			enrich: 'Enrichissement',
			structure: 'Restructuration',
			summarize: 'Résumé ajouté',
			score: 'Évaluation qualité',
			inject_questions: 'Questions ajoutées'
		};
		return labels[actionType] || actionType;
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.85) return 'text-green-400';
		if (confidence >= 0.7) return 'text-yellow-400';
		return 'text-orange-400';
	}

	function extractModel(reasoning: string): string | null {
		const match = reasoning.match(/^\[(\w+)\]/);
		return match ? match[1] : null;
	}

	function cleanReasoning(reasoning: string): string {
		return reasoning.replace(/^\[\w+\]\s*/, '');
	}

	// Group records by date
	function groupByDate(records: EnrichmentRecord[]): Map<string, EnrichmentRecord[]> {
		const groups = new Map<string, EnrichmentRecord[]>();
		for (const record of records) {
			const date = new Date(record.timestamp).toLocaleDateString('fr-FR', {
				day: 'numeric',
				month: 'long',
				year: 'numeric'
			});
			if (!groups.has(date)) {
				groups.set(date, []);
			}
			groups.get(date)!.push(record);
		}
		return groups;
	}

	const groupedRecords = $derived(history ? groupByDate(history.records) : new Map());

	async function handleRollback(recordIndex: number, record: EnrichmentRecord) {
		if (!record.applied) {
			toastStore.warning("Cette action n'a pas été appliquée, rien à annuler");
			return;
		}

		rollingBack = recordIndex;
		try {
			const result = await rollbackRetouche(noteId, { record_index: recordIndex });
			if (result.rolled_back) {
				toastStore.success(`Action "${getActionLabel(record.action_type)}" annulée`);
				// Reload history
				await loadHistory();
				onRollback?.();
			} else {
				toastStore.error("Impossible d'annuler cette action");
			}
		} catch (e) {
			toastStore.error(e instanceof Error ? e.message : "Erreur lors de l'annulation");
		} finally {
			rollingBack = null;
		}
	}

	// Check if record can be rolled back (only recent applied actions)
	function canRollback(record: EnrichmentRecord, index: number): boolean {
		if (!record.applied) return false;
		// Only allow rollback of recent actions (within 7 days)
		const sevenDaysAgo = new Date();
		sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
		return new Date(record.timestamp) > sevenDaysAgo && index < 10;
	}
</script>

<Modal bind:open title="Historique des retouches IA" size="lg" data-testid="retouche-history">
	{#if loading}
		<div class="flex justify-center py-8">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
			></div>
		</div>
	{:else if error}
		<div class="text-center py-8 text-[var(--color-error)]">
			<p>{error}</p>
			<Button variant="ghost" onclick={loadHistory} class="mt-4">Réessayer</Button>
		</div>
	{:else if !history || history.records.length === 0}
		<div class="text-center py-8 text-[var(--color-text-secondary)]">
			<p class="text-4xl mb-4">🤖</p>
			<p>Aucune retouche effectuée sur cette note</p>
			<p class="text-sm mt-2 text-[var(--color-text-tertiary)]">
				Les retouches IA apparaîtront ici après analyse de la note
			</p>
		</div>
	{:else}
		<!-- Summary header -->
		<div class="flex items-center gap-4 mb-6 p-4 rounded-xl glass-subtle">
			{#if history.quality_score !== null}
				<div class="text-center">
					<div
						class="text-2xl font-bold"
						class:text-green-400={history.quality_score >= 80}
						class:text-yellow-400={history.quality_score >= 60 && history.quality_score < 80}
						class:text-orange-400={history.quality_score < 60}
					>
						{history.quality_score}%
					</div>
					<div class="text-xs text-[var(--color-text-tertiary)]">Qualité</div>
				</div>
			{/if}
			<div class="text-center">
				<div class="text-2xl font-bold text-[var(--color-accent)]">
					{history.retouche_count}
				</div>
				<div class="text-xs text-[var(--color-text-tertiary)]">Cycles</div>
			</div>
			<div class="text-center">
				<div class="text-2xl font-bold text-[var(--color-text-primary)]">
					{history.total_records}
				</div>
				<div class="text-xs text-[var(--color-text-tertiary)]">Actions</div>
			</div>
		</div>

		<!-- Timeline -->
		<div class="space-y-6 max-h-[400px] overflow-y-auto pr-2">
			{#each groupedRecords as [date, records]}
				<div>
					<h3 class="text-sm font-medium text-[var(--color-text-tertiary)] mb-3 sticky top-0 bg-[var(--glass-bg)] py-1">
						{date}
					</h3>
					<div class="space-y-3 pl-4 border-l-2 border-[var(--glass-border-subtle)]">
						{#each records as record}
							<div class="relative -ml-[9px]">
								<!-- Timeline dot -->
								<div
									class="absolute left-0 w-4 h-4 rounded-full bg-[var(--glass-bg)] border-2 flex items-center justify-center text-xs"
									class:border-green-400={record.confidence >= 0.85}
									class:border-yellow-400={record.confidence >= 0.7 && record.confidence < 0.85}
									class:border-orange-400={record.confidence < 0.7}
								>
									<span class="text-[10px]">{getActionIcon(record.action_type)}</span>
								</div>

								<!-- Content card -->
								<Card variant="glass" padding="sm" class="ml-6">
									<div class="p-2">
										<div class="flex items-center gap-2 mb-1">
											<Badge>{getActionLabel(record.action_type)}</Badge>
											{#if extractModel(record.reasoning)}
												<Badge class="bg-purple-500/20 text-purple-300">
													{extractModel(record.reasoning)}
												</Badge>
											{/if}
											{#if record.applied}
												<Badge class="bg-green-500/20 text-green-300 text-xs">Appliqué</Badge>
											{:else}
												<Badge class="bg-gray-500/20 text-gray-300 text-xs">Non appliqué</Badge>
											{/if}
											<span class={`text-xs font-mono ${getConfidenceColor(record.confidence)}`}>
												{(record.confidence * 100).toFixed(0)}%
											</span>
											<span class="text-xs text-[var(--color-text-tertiary)] ml-auto">
												{new Date(record.timestamp).toLocaleTimeString('fr-FR', {
													hour: '2-digit',
													minute: '2-digit'
												})}
											</span>
										</div>

										{#if cleanReasoning(record.reasoning)}
											<p class="text-sm text-[var(--color-text-secondary)] mt-1">
												{cleanReasoning(record.reasoning)}
											</p>
										{/if}

										{#if record.content}
											<details class="mt-2">
												<summary
													class="text-xs text-[var(--color-accent)] cursor-pointer hover:underline"
												>
													Voir le contenu ajouté
												</summary>
												<pre
													class="mt-2 p-2 text-xs bg-black/20 rounded overflow-x-auto whitespace-pre-wrap">{record.content}</pre>
											</details>
										{/if}

										<!-- Rollback button -->
										{#if record.applied && canRollback(record, history?.records.indexOf(record) ?? -1)}
											{@const recordIndex = history?.records.indexOf(record) ?? -1}
											<div class="mt-2 flex justify-end">
												<Button
													variant="ghost"
													size="sm"
													onclick={() => handleRollback(recordIndex, record)}
													disabled={rollingBack === recordIndex}
													class="text-xs text-orange-400 hover:text-orange-300"
												>
													{rollingBack === recordIndex ? 'Annulation...' : 'Annuler'}
												</Button>
											</div>
										{/if}
									</div>
								</Card>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#snippet footer()}
		<Button variant="ghost" onclick={() => (open = false)}>Fermer</Button>
	{/snippet}
</Modal>
