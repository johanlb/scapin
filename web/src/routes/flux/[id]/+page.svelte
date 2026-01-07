<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Badge, Button, Skeleton } from '$lib/components/ui';
	import { ConfidenceBar } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { getQueueItem, approveQueueItem, rejectQueueItem, snoozeQueueItem, undoQueueItem, canUndoQueueItem } from '$lib/api';
	import type { QueueItem, SnoozeOption } from '$lib/api';

	// Get the item ID from route params
	const itemId = $derived($page.params.id ?? '');

	// State
	let item = $state<QueueItem | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showHtml = $state(true);
	let isProcessing = $state(false);

	// Draft reply state
	let draftContent = $state('');
	let isEditingDraft = $state(false);
	let isSendingReply = $state(false);

	// Snooze state
	let showSnoozeMenu = $state(false);
	let isSnoozing = $state(false);
	let snoozeSuccess = $state<string | null>(null);

	// Undo state
	let canUndo = $state(false);
	let isUndoing = $state(false);
	let undoSuccess = $state<string | null>(null);

	// Computed values
	const isApproved = $derived(item?.status === 'approved');
	const hasHtmlBody = $derived(!!item?.content?.html_body);
	const hasFullText = $derived(!!item?.content?.full_text);
	const contentToShow = $derived(
		showHtml && hasHtmlBody ? item?.content?.html_body : item?.content?.full_text || item?.content?.preview || ''
	);

	// Check if this is a REPLY action with a draft
	const hasDraftReply = $derived(
		item?.analysis?.action?.toLowerCase() === 'reply' && !!item?.analysis?.draft_reply
	);

	onMount(async () => {
		if (itemId) {
			await loadItem();
		}
	});

	async function loadItem() {
		loading = true;
		error = null;
		canUndo = false;

		try {
			item = await getQueueItem(itemId);
			// Initialize draft content if available
			if (item?.analysis?.draft_reply) {
				draftContent = item.analysis.draft_reply;
			}
			// Check if undo is available for approved items
			if (item?.status === 'approved') {
				try {
					const undoCheck = await canUndoQueueItem(itemId);
					canUndo = undoCheck.can_undo;
				} catch {
					// Undo check failed, just disable undo
					canUndo = false;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
		} finally {
			loading = false;
		}
	}

	function startEditingDraft() {
		isEditingDraft = true;
	}

	function cancelEditingDraft() {
		if (item?.analysis?.draft_reply) {
			draftContent = item.analysis.draft_reply;
		}
		isEditingDraft = false;
	}

	// Info message state (for non-error notifications)
	let infoMessage = $state<string | null>(null);

	async function handleSendReply() {
		if (!item || isSendingReply || !draftContent.trim()) return;
		isSendingReply = true;
		error = null;

		try {
			// TODO: Implement actual email sending via SMTP
			// For now, save draft locally and show info message
			localStorage.setItem(`draft_${itemId}`, draftContent);
			infoMessage = 'Brouillon enregistré. L\'envoi d\'emails sera bientôt disponible.';
			isEditingDraft = false;
			// Clear info after 5 seconds
			setTimeout(() => {
				infoMessage = null;
			}, 5000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors de l\'enregistrement';
		} finally {
			isSendingReply = false;
		}
	}

	async function handleApprove(action: string, destination?: string | null) {
		if (!item || isProcessing) return;
		isProcessing = true;

		try {
			await approveQueueItem(item.id, action, destination ?? undefined);
			// Go back to flux list
			goto('/flux');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors de l\'approbation';
		} finally {
			isProcessing = false;
		}
	}

	async function handleReject() {
		if (!item || isProcessing) return;
		isProcessing = true;

		try {
			await rejectQueueItem(item.id, 'Rejeté par l\'utilisateur');
			goto('/flux');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors du rejet';
		} finally {
			isProcessing = false;
		}
	}

	async function handleSnooze(option: SnoozeOption) {
		if (!item || isSnoozing) return;
		isSnoozing = true;
		showSnoozeMenu = false;
		error = null;

		try {
			const result = await snoozeQueueItem(item.id, option);
			// Show success message with snooze time
			const snoozeUntil = new Date(result.snooze_until);
			const snoozeLabel = getSnoozeLabel(option);
			snoozeSuccess = `Snooze jusqu'à ${snoozeUntil.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}`;

			// Go back to list after a short delay
			setTimeout(() => goto('/flux'), 1500);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors du snooze';
		} finally {
			isSnoozing = false;
		}
	}

	function getSnoozeLabel(option: SnoozeOption): string {
		const labels: Record<SnoozeOption, string> = {
			later_today: 'Plus tard (3h)',
			tomorrow: 'Demain matin',
			this_weekend: 'Ce weekend',
			next_week: 'Semaine prochaine',
			custom: 'Personnalisé'
		};
		return labels[option] || option;
	}

	async function handleUndo() {
		if (!item || isUndoing || !canUndo) return;
		isUndoing = true;
		error = null;

		try {
			const updatedItem = await undoQueueItem(item.id);
			item = updatedItem;
			canUndo = false;
			undoSuccess = 'Action annulée — l\'email a été remis dans sa boîte d\'origine';

			// Clear success message after a delay
			setTimeout(() => {
				undoSuccess = null;
			}, 3000);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors de l\'annulation';
		} finally {
			isUndoing = false;
		}
	}

	function toggleSnoozeMenu() {
		showSnoozeMenu = !showSnoozeMenu;
	}

	function goBack() {
		history.back();
	}

	function getInitials(name: string): string {
		if (!name || name.trim() === '') return '?';
		return name
			.split(' ')
			.map((n) => n[0])
			.join('')
			.toUpperCase()
			.slice(0, 2);
	}

	function getConfidenceLevel(confidence: number): number {
		// Convert 0-100 to 0-5 dots
		return Math.round((confidence / 100) * 5);
	}
</script>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<!-- Header with back button -->
	<header
		class="sticky top-0 z-20 glass-prominent border-b border-[var(--glass-border-subtle)] px-4 py-3"
	>
		<div class="max-w-4xl mx-auto flex items-center gap-3">
			<button
				onclick={goBack}
				class="p-2 -ml-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
				aria-label="Retour"
			>
				<span class="text-xl">&#8592;</span>
			</button>
			<div class="flex-1 min-w-0">
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)] truncate">
					{item?.metadata?.subject || 'Chargement...'}
				</h1>
				{#if item?.metadata?.from_name}
					<p class="text-sm text-[var(--color-text-tertiary)]">
						de {item.metadata.from_name}
					</p>
				{/if}
			</div>
		</div>
	</header>

	{#if loading}
		<!-- Loading state -->
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4" role="status" aria-busy="true" aria-label="Chargement du message">
			<span class="sr-only">Chargement du message en cours...</span>
			<div class="flex flex-wrap items-center gap-2">
				<Skeleton variant="rectangular" class="w-16 h-6 rounded-full" />
				<Skeleton variant="rectangular" class="w-20 h-6 rounded-full" />
			</div>
			<Card variant="glass-subtle">
				<div class="p-4 space-y-3">
					<div class="flex items-center gap-3">
						<Skeleton variant="avatar" />
						<div class="flex-1 space-y-2">
							<Skeleton variant="text" class="w-1/3" />
							<Skeleton variant="text" class="w-1/4" />
						</div>
					</div>
				</div>
			</Card>
			<Card variant="glass-subtle">
				<div class="p-4">
					<Skeleton variant="text" lines={8} />
				</div>
			</Card>
		</main>
	{:else if error}
		<!-- Error state -->
		<main class="p-8 text-center">
			<div class="text-red-400 mb-4">{error}</div>
			<Button variant="glass" onclick={loadItem}>Réessayer</Button>
		</main>
	{:else if item}
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
			<!-- Info/Error notifications -->
			{#if infoMessage}
				<div class="flex items-center gap-2 p-3 rounded-lg bg-blue-500/20 text-blue-400 text-sm">
					<span>ℹ️</span>
					<span>{infoMessage}</span>
				</div>
			{/if}
			<!-- Meta info -->
			<div class="flex flex-wrap items-center gap-2">
				<Badge variant="source" source="email" />
				{#if item.metadata.has_attachments}
					<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]">
						&#128206; Pièces jointes
					</span>
				{/if}
				{#if item.metadata.folder}
					<span class="text-sm text-[var(--color-text-tertiary)]">
						&#128193; {item.metadata.folder}
					</span>
				{/if}
				{#if item.metadata.date}
					<span class="text-sm text-[var(--color-text-tertiary)]">
						{formatRelativeTime(item.metadata.date)}
					</span>
				{/if}
			</div>

			<!-- Sender info -->
			<div class="flex items-center gap-3">
				<div
					class="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--color-accent)] to-purple-500 flex items-center justify-center text-white font-semibold shrink-0"
				>
					{getInitials(item.metadata.from_name)}
				</div>
				<div class="min-w-0">
					<p class="font-medium text-[var(--color-text-primary)]">
						{item.metadata.from_name || 'Expéditeur inconnu'}
					</p>
					<p class="text-sm text-[var(--color-text-tertiary)] truncate">
						{item.metadata.from_address}
					</p>
				</div>
			</div>

			<!-- Email Content -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<!-- Content type toggle -->
					{#if hasHtmlBody && hasFullText}
						<div class="flex items-center gap-2 mb-4 pb-4 border-b border-[var(--glass-border-subtle)]">
							<span class="text-sm text-[var(--color-text-tertiary)]">Affichage:</span>
							<button
								class="px-3 py-1 text-sm rounded-full transition-colors {showHtml ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--glass-tint)] text-[var(--color-text-secondary)]'}"
								onclick={() => showHtml = true}
							>
								HTML
							</button>
							<button
								class="px-3 py-1 text-sm rounded-full transition-colors {!showHtml ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--glass-tint)] text-[var(--color-text-secondary)]'}"
								onclick={() => showHtml = false}
							>
								Texte brut
							</button>
						</div>
					{/if}

					<!-- Content display -->
					{#if showHtml && hasHtmlBody}
						<div class="email-content prose prose-invert max-w-none">
							{@html item.content.html_body}
						</div>
					{:else}
						<div class="text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed font-mono text-sm">
							{contentToShow}
						</div>
					{/if}
				</div>
			</Card>

			<!-- AI Analysis -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<h3 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3">
						Analyse de Scapin
					</h3>

					<!-- Summary -->
					{#if item.analysis.summary}
						<p class="text-[var(--color-text-secondary)] mb-4">
							{item.analysis.summary}
						</p>
					{/if}

					<!-- Reasoning -->
					<p class="text-sm text-[var(--color-text-secondary)] mb-4">
						{item.analysis.reasoning}
					</p>

					<!-- Category & Action -->
					<div class="flex flex-wrap items-center gap-3 mb-4">
						{#if item.analysis.category}
							<span class="text-xs px-2 py-1 rounded bg-[var(--glass-tint)] text-[var(--color-text-secondary)]">
								{item.analysis.category}
							</span>
						{/if}
						<span class="text-xs px-2 py-1 rounded bg-[var(--color-accent)]/20 text-[var(--color-accent)]">
							{item.analysis.action}
						</span>
					</div>

					<!-- Confidence -->
					<div class="flex items-center gap-2">
						<span class="text-xs text-[var(--color-text-tertiary)]">Confiance:</span>
						<ConfidenceBar value={item.analysis.confidence / 100} showPercentage={false} size="sm" />
						<span class="text-xs text-[var(--color-text-tertiary)]">
							{item.analysis.confidence}%
						</span>
					</div>

					<!-- Entities (Sprint 2) -->
					{#if item.analysis.entities && Object.keys(item.analysis.entities).length > 0}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
								Entités détectées
							</h4>
							<div class="flex flex-wrap gap-1">
								{#each Object.entries(item.analysis.entities) as [type, entities]}
									{#each entities as entity}
										<span class="px-2 py-0.5 text-xs rounded-full
											{type === 'person' ? 'bg-blue-500/20 text-blue-300' : ''}
											{type === 'project' ? 'bg-purple-500/20 text-purple-300' : ''}
											{type === 'date' ? 'bg-orange-500/20 text-orange-300' : ''}
											{type === 'amount' ? 'bg-green-500/20 text-green-300' : ''}
											{type === 'organization' ? 'bg-cyan-500/20 text-cyan-300' : ''}
										">
											{entity.value}
										</span>
									{/each}
								{/each}
							</div>
						</div>
					{/if}

					<!-- Proposed Notes (Sprint 2) -->
					{#if item.analysis.proposed_notes && item.analysis.proposed_notes.length > 0}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
								Notes proposées
							</h4>
							{#each item.analysis.proposed_notes as note}
								<div class="flex items-center justify-between text-sm py-1">
									<span class="flex items-center gap-2">
										<span class="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300">
											{note.action === 'create' ? '+' : '~'} {note.note_type}
										</span>
										{note.title}
									</span>
									<span class="text-xs text-[var(--color-text-tertiary)]">
										{Math.round(note.confidence * 100)}%
										{#if note.auto_applied}
											<span class="ml-1 text-green-400">Auto</span>
										{/if}
									</span>
								</div>
							{/each}
						</div>
					{/if}

					<!-- Context Used -->
					{#if item.analysis.context_used && item.analysis.context_used.length > 0}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
								Contexte utilisé
							</h4>
							<div class="flex flex-wrap gap-1">
								{#each item.analysis.context_used as noteId}
									<a
										href="/notes/{noteId}"
										class="text-xs px-2 py-1 rounded bg-[var(--glass-tint)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 transition-colors"
									>
										{noteId}
									</a>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</Card>

			<!-- Draft Reply Section -->
			{#if hasDraftReply}
				<Card variant="glass">
					<div class="p-4">
						<div class="flex items-center justify-between mb-3">
							<h3 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide">
								&#9993; Brouillon de réponse
							</h3>
							{#if !isEditingDraft}
								<button
									onclick={startEditingDraft}
									class="text-xs px-2 py-1 rounded bg-[var(--glass-tint)] text-[var(--color-accent)] hover:bg-[var(--color-accent)]/20 transition-colors"
								>
									&#9998; Modifier
								</button>
							{/if}
						</div>

						{#if isEditingDraft}
							<!-- Editing mode -->
							<div class="space-y-3">
								<div class="text-xs text-[var(--color-text-tertiary)] mb-2">
									À: {item.metadata.from_address}
								</div>
								<textarea
									bind:value={draftContent}
									class="w-full h-48 p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--glass-border-subtle)] text-[var(--color-text-primary)] text-sm font-mono resize-y focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]/50"
									placeholder="Écrivez votre réponse..."
								></textarea>
								<div class="flex items-center justify-end gap-2">
									<Button
										variant="ghost"
										size="sm"
										onclick={cancelEditingDraft}
									>
										Annuler
									</Button>
									<Button
										variant="primary"
										size="sm"
										onclick={handleSendReply}
										disabled={isSendingReply || !draftContent.trim()}
									>
										{#if isSendingReply}
											<span class="animate-pulse">Envoi...</span>
										{:else}
											&#9993; Envoyer
										{/if}
									</Button>
								</div>
							</div>
						{:else}
							<!-- Preview mode -->
							<div class="text-xs text-[var(--color-text-tertiary)] mb-2">
								À: {item.metadata.from_address}
							</div>
							<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--glass-border-subtle)]">
								<pre class="text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap font-mono">{draftContent}</pre>
							</div>
							<div class="mt-3 flex items-center justify-end gap-2">
								<Button
									variant="primary"
									size="sm"
									onclick={startEditingDraft}
								>
									&#9998; Modifier et envoyer
								</Button>
							</div>
						{/if}
					</div>
				</Card>
			{/if}

			<!-- Suggested Actions -->
			{#if item.analysis.options && item.analysis.options.length > 0}
				<section>
					<h3 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3">
						Actions suggérées
					</h3>
					<div class="space-y-2">
						{#each item.analysis.options as option, i}
							<Card variant={option.is_recommended ? 'glass' : 'glass-subtle'}>
								<button
									class="w-full p-4 text-left hover:bg-[var(--glass-tint)]/50 transition-colors disabled:opacity-50"
									onclick={() => handleApprove(option.action, option.destination)}
									disabled={isProcessing}
								>
									<div class="flex items-start justify-between gap-3">
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2">
												<span class="font-medium text-[var(--color-text-primary)]">
													{i + 1}. {option.action}
												</span>
												{#if option.is_recommended}
													<span class="text-xs px-1.5 py-0.5 rounded bg-[var(--color-accent)]/20 text-[var(--color-accent)]">
														Recommandé
													</span>
												{/if}
											</div>
											{#if option.destination}
												<p class="text-sm text-[var(--color-text-tertiary)] mt-1">
													&#8594; {option.destination}
												</p>
											{/if}
											<p class="text-sm text-[var(--color-text-secondary)] mt-2">
												{option.reasoning}
											</p>
										</div>
										<div class="text-right shrink-0">
											<span class="text-sm font-medium text-[var(--color-text-primary)]">
												{option.confidence}%
											</span>
										</div>
									</div>
								</button>
							</Card>
						{/each}
					</div>

					<!-- Snooze and Reject buttons -->
					<div class="mt-4 flex items-center gap-3 flex-wrap">
						<!-- Snooze Button with Dropdown -->
						<div class="relative">
							<Button
								variant="glass"
								onclick={toggleSnoozeMenu}
								disabled={isProcessing || isSnoozing}
								class="text-amber-400 hover:text-amber-300"
							>
								{#if isSnoozing}
									<span class="animate-pulse">&#9203; Snooze...</span>
								{:else}
									&#9203; Snooze
								{/if}
							</Button>

							{#if showSnoozeMenu}
								<!-- Snooze dropdown menu -->
								<div class="absolute bottom-full left-0 mb-2 w-48 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--glass-border-subtle)] shadow-xl z-50">
									<div class="py-1">
										<button
											class="w-full px-4 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint)] transition-colors"
											onclick={() => handleSnooze('later_today')}
										>
											&#9203; Plus tard (3h)
										</button>
										<button
											class="w-full px-4 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint)] transition-colors"
											onclick={() => handleSnooze('tomorrow')}
										>
											&#127749; Demain matin
										</button>
										<button
											class="w-full px-4 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint)] transition-colors"
											onclick={() => handleSnooze('this_weekend')}
										>
											&#127774; Ce weekend
										</button>
										<button
											class="w-full px-4 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint)] transition-colors"
											onclick={() => handleSnooze('next_week')}
										>
											&#128197; Semaine prochaine
										</button>
									</div>
								</div>
								<!-- Backdrop to close menu -->
								<button
									class="fixed inset-0 z-40"
									onclick={() => showSnoozeMenu = false}
									aria-label="Fermer le menu"
								></button>
							{/if}
						</div>

						<!-- Reject button -->
						<Button
							variant="ghost"
							onclick={handleReject}
							disabled={isProcessing}
							class="text-red-400 hover:text-red-300"
						>
							&#10005; Rejeter
						</Button>
					</div>

					<!-- Snooze success message -->
					{#if snoozeSuccess}
						<div class="mt-4 p-3 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 text-sm">
							&#9989; {snoozeSuccess}
						</div>
					{/if}
				</section>
			{/if}

			<!-- Approved Item Actions (Undo) -->
			{#if isApproved}
				<section class="mt-6">
					<Card variant="glass">
						<div class="p-4">
							<div class="flex items-center justify-between">
								<div>
									<div class="flex items-center gap-2">
										<span class="text-green-400 text-xl">&#10003;</span>
										<h3 class="font-medium text-[var(--color-text-primary)]">
											Action approuvée
										</h3>
									</div>
									<p class="text-sm text-[var(--color-text-tertiary)] mt-1">
										{#if item?.review_decision === 'approve'}
											L'email a été traité selon la suggestion de Scapin.
										{:else if item?.review_decision === 'modify'}
											L'email a été traité avec une action modifiée.
										{:else}
											L'email a été traité.
										{/if}
									</p>
								</div>
								{#if canUndo}
									<Button
										variant="glass"
										onclick={handleUndo}
										disabled={isUndoing}
										class="text-orange-400 hover:text-orange-300"
									>
										{#if isUndoing}
											<span class="animate-pulse">&#8634; Annulation...</span>
										{:else}
											&#8634; Annuler
										{/if}
									</Button>
								{/if}
							</div>

							<!-- Undo success message -->
							{#if undoSuccess}
								<div class="mt-4 p-3 rounded-lg bg-green-500/20 border border-green-500/30 text-green-300 text-sm">
									&#9989; {undoSuccess}
								</div>
							{/if}
						</div>
					</Card>
				</section>
			{/if}
		</main>
	{:else}
		<div class="p-8 text-center">
			<p class="text-[var(--color-text-tertiary)]">Élément introuvable</p>
			<Button variant="glass" onclick={goBack} class="mt-4">Retour</Button>
		</div>
	{/if}
</div>

<style>
	/* Email HTML content styles */
	:global(.email-content) {
		color: var(--color-text-secondary);
	}

	:global(.email-content a) {
		color: var(--color-accent);
		text-decoration: underline;
	}

	:global(.email-content img) {
		max-width: 100%;
		height: auto;
		border-radius: 0.5rem;
	}

	:global(.email-content table) {
		border-collapse: collapse;
		width: 100%;
		margin: 1rem 0;
	}

	:global(.email-content td, .email-content th) {
		border: 1px solid var(--glass-border-subtle);
		padding: 0.5rem;
	}

	:global(.email-content blockquote) {
		border-left: 3px solid var(--color-accent);
		padding-left: 1rem;
		margin-left: 0;
		color: var(--color-text-tertiary);
		font-style: italic;
	}
</style>
