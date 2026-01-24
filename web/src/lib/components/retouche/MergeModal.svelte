<!--
	MergeModal Component
	Modal for confirming note merge actions.
	Shows source and target notes with reasoning.
-->
<script lang="ts">
	import { Modal, Button, Skeleton } from '$lib/components/ui';
	import { approveRetoucheAction, rejectRetoucheAction, getNote } from '$lib/api';
	import { toastStore } from '$lib/stores/toast.svelte';
	import type { PendingRetoucheAction, Note } from '$lib/api';

	interface Props {
		open: boolean;
		action: PendingRetoucheAction | null;
		onclose?: () => void;
		onapprove?: () => void;
		onreject?: () => void;
	}

	let { open = $bindable(false), action, onclose, onapprove, onreject }: Props = $props();

	// State
	let loading = $state(false);
	let loadingNotes = $state(true);
	let sourceNote = $state<Note | null>(null);
	let targetNote = $state<Note | null>(null);
	let rejectReason = $state('');
	let showRejectForm = $state(false);

	// Fetch notes when modal opens
	$effect(() => {
		if (open && action) {
			fetchNotes();
		} else {
			// Reset state
			loadingNotes = true;
			sourceNote = null;
			targetNote = null;
			rejectReason = '';
			showRejectForm = false;
		}
	});

	async function fetchNotes() {
		loadingNotes = true;
		try {
			const [source, target] = await Promise.all([
				getNote(action!.note_id),
				action!.target_note_id ? getNote(action!.target_note_id) : Promise.resolve(null)
			]);
			sourceNote = source;
			targetNote = target;
		} catch {
			toastStore.error('Erreur lors du chargement des notes');
		} finally {
			loadingNotes = false;
		}
	}

	async function handleApprove() {
		if (!action) return;
		loading = true;
		try {
			const result = await approveRetoucheAction(action.action_id, action.note_id, true);
			if (result.success) {
				toastStore.success(result.message);
				open = false;
				onapprove?.();
			} else {
				toastStore.error(result.message);
			}
		} catch {
			toastStore.error('Erreur lors de la fusion');
		} finally {
			loading = false;
		}
	}

	async function handleReject() {
		if (!action) return;
		loading = true;
		try {
			const result = await rejectRetoucheAction(
				action.action_id,
				action.note_id,
				rejectReason || undefined
			);
			if (result.success) {
				toastStore.info('Fusion annulée');
				open = false;
				onreject?.();
			} else {
				toastStore.error(result.message);
			}
		} catch {
			toastStore.error("Erreur lors de l'annulation");
		} finally {
			loading = false;
		}
	}

	function handleClose() {
		open = false;
		onclose?.();
	}

	function formatConfidence(confidence: number): string {
		return `${Math.round(confidence * 100)}%`;
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.85) return 'var(--color-success)';
		if (confidence >= 0.6) return 'var(--color-warning)';
		return 'var(--color-urgency-urgent)';
	}
</script>

<Modal {open} title="Fusionner les notes" size="lg" onclose={handleClose}>
	{#if loadingNotes}
		<div class="space-y-4" data-testid="merge-loading">
			<Skeleton variant="rectangular" height="80px" />
			<Skeleton variant="rectangular" height="80px" />
			<Skeleton variant="text" lines={2} />
		</div>
	{:else if action}
		<div class="space-y-5" data-testid="merge-content">
			<!-- Confidence indicator -->
			<div class="flex items-center gap-2 text-sm">
				<span class="text-[var(--color-text-secondary)]">Confiance :</span>
				<span
					class="font-semibold"
					style="color: {getConfidenceColor(action.confidence)}"
				>
					{formatConfidence(action.confidence)}
				</span>
			</div>

			<!-- Source note -->
			<section>
				<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
					<span>📤</span> Note source (sera archivée)
				</h4>
				<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
					<div class="flex items-start gap-3">
						<div class="flex-1 min-w-0">
							<p class="font-medium text-[var(--color-text-primary)]">
								{action.note_title}
							</p>
							{#if action.note_path}
								<p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
									{action.note_path}
								</p>
							{/if}
							{#if sourceNote?.excerpt}
								<p class="text-sm text-[var(--color-text-secondary)] mt-2 line-clamp-3">
									{sourceNote.excerpt}
								</p>
							{/if}
						</div>
					</div>
				</div>
			</section>

			<!-- Arrow -->
			<div class="flex justify-center text-2xl text-[var(--color-text-tertiary)]">
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
				</svg>
			</div>

			<!-- Target note -->
			<section>
				<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
					<span>📥</span> Note cible
				</h4>
				<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border-2 border-[var(--color-accent)]">
					<div class="flex items-start gap-3">
						<div class="flex-1 min-w-0">
							<p class="font-medium text-[var(--color-text-primary)]">
								{action.target_note_title || 'Note non spécifiée'}
							</p>
							{#if targetNote?.path}
								<p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
									{targetNote.path}
								</p>
							{/if}
							{#if targetNote?.excerpt}
								<p class="text-sm text-[var(--color-text-secondary)] mt-2 line-clamp-3">
									{targetNote.excerpt}
								</p>
							{/if}
						</div>
					</div>
				</div>
			</section>

			<!-- Reasoning -->
			{#if action.reasoning}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
						<span>💭</span> Raisonnement
					</h4>
					<div class="p-3 rounded-lg bg-[var(--color-bg-tertiary)] text-sm text-[var(--color-text-secondary)]">
						{action.reasoning}
					</div>
				</section>
			{/if}

			<!-- Reject form -->
			{#if showRejectForm}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2">
						Raison du rejet (optionnel)
					</h4>
					<textarea
						bind:value={rejectReason}
						class="w-full p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-sm resize-none"
						rows="2"
						placeholder="Pourquoi cette fusion ne devrait pas être effectuée..."
					></textarea>
				</section>
			{/if}
		</div>
	{/if}

	{#snippet footer()}
		{#if showRejectForm}
			<Button variant="ghost" onclick={() => (showRejectForm = false)} disabled={loading}>
				Annuler
			</Button>
			<Button variant="danger" onclick={handleReject} {loading}>
				Confirmer le rejet
			</Button>
		{:else}
			<Button variant="ghost" onclick={() => (showRejectForm = true)} disabled={loading}>
				Rejeter
			</Button>
			<Button variant="primary" onclick={handleApprove} {loading}>
				Fusionner
			</Button>
		{/if}
	{/snippet}
</Modal>
