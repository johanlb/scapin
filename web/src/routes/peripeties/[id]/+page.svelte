<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import DOMPurify from 'isomorphic-dompurify';
	import { Card, Badge, Button, Skeleton } from '$lib/components/ui';
	import { ConfidenceBar } from '$lib/components/ui';
	import { FileAttachment } from '$lib/components/files';
	import PassTimeline from '$lib/components/peripeties/PassTimeline.svelte';
	import ConfidenceSparkline from '$lib/components/peripeties/ConfidenceSparkline.svelte';
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

	// Sanitize HTML content with DOMPurify
	// Allows safe HTML rendering while preventing XSS attacks
	const sanitizedHtml = $derived(() => {
		if (!hasHtmlBody || !item?.content?.html_body) return '';

		// Configure DOMPurify to allow safe email content
		const config = {
			ALLOWED_TAGS: [
				'a', 'abbr', 'address', 'article', 'aside', 'b', 'bdi', 'bdo', 'blockquote',
				'br', 'caption', 'cite', 'code', 'col', 'colgroup', 'data', 'dd', 'del', 'dfn',
				'div', 'dl', 'dt', 'em', 'figcaption', 'figure', 'footer', 'h1', 'h2', 'h3',
				'h4', 'h5', 'h6', 'header', 'hr', 'i', 'img', 'ins', 'kbd', 'li', 'main', 'mark',
				'nav', 'ol', 'p', 'pre', 'q', 'rp', 'rt', 'ruby', 's', 'samp', 'section', 'small',
				'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead',
				'time', 'tr', 'u', 'ul', 'var', 'wbr', 'font', 'center'
			],
			ALLOWED_ATTR: [
				'href', 'src', 'alt', 'title', 'class', 'id', 'style', 'target', 'rel',
				'width', 'height', 'colspan', 'rowspan', 'align', 'valign', 'border',
				'cellpadding', 'cellspacing', 'bgcolor', 'color', 'face', 'size', 'dir', 'lang'
			],
			ALLOW_DATA_ATTR: false,
			ADD_ATTR: ['target'], // Allow target on links
			FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button'],
			FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
		};

		// Sanitize the HTML
		const clean = DOMPurify.sanitize(item.content.html_body, config);

		// Add target="_blank" and rel="noopener" to all links for security
		return clean.replace(/<a\s+(?![^>]*target=)/gi, '<a target="_blank" rel="noopener noreferrer" ');
	});

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
			goto('/peripeties');
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
			goto('/peripeties');
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
			setTimeout(() => goto('/peripeties'), 1500);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors du snooze';
		} finally {
			isSnoozing = false;
		}
	}

	function getSnoozeLabel(option: SnoozeOption): string {
		const labels: Record<SnoozeOption, string> = {
			in_30_min: '30 minutes',
			in_2_hours: '2 heures',
			tomorrow: 'Demain matin',
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
			<!-- v2.4: Meta info with dates -->
			<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
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
			</div>

			<!-- v2.4: Enhanced dates section -->
			<div class="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-[var(--color-text-tertiary)]">
				{#if item.metadata.date}
					<span class="flex items-center gap-1.5" title="Date de réception de l'email">
						<span class="text-base">&#x1f4e8;</span>
						<span class="font-medium text-[var(--color-text-secondary)]">Reçu</span>
						{formatRelativeTime(item.metadata.date)}
					</span>
				{/if}
				{#if item.queued_at}
					<span class="flex items-center gap-1.5" title="Date d'analyse par Scapin">
						<span class="text-base">&#x1f9e0;</span>
						<span class="font-medium text-[var(--color-text-secondary)]">Analysé</span>
						{formatRelativeTime(item.queued_at)}
					</span>
				{/if}
				{#if item.reviewed_at}
					<span class="flex items-center gap-1.5" title="Date de décision">
						<span class="text-base">&#x2705;</span>
						<span class="font-medium text-[var(--color-text-secondary)]">Traité</span>
						{formatRelativeTime(item.reviewed_at)}
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
						<!-- Sanitized HTML content with DOMPurify for XSS prevention -->
						<div
							class="email-content prose prose-invert max-w-none p-4 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--glass-border-subtle)] overflow-auto"
						>
							{@html sanitizedHtml()}
						</div>
					{:else}
						<div class="text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed font-mono text-sm">
							{contentToShow}
						</div>
					{/if}
				</div>
			</Card>

			<!-- Attachments Section -->
			{#if item.metadata.attachments && item.metadata.attachments.length > 0}
				<Card variant="glass-subtle">
					<div class="p-4">
						<h3 class="text-sm font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-3">
							Pièces jointes ({item.metadata.attachments.length})
						</h3>
						<div class="grid gap-2">
							{#each item.metadata.attachments as attachment (attachment.filename)}
								<FileAttachment {attachment} emailId={item.metadata.id} />
							{/each}
						</div>
					</div>
				</Card>
			{/if}

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

					<!-- Multi-Pass Analysis Metadata (v2.3) -->
					{#if item.analysis.multi_pass}
						{@const mp = item.analysis.multi_pass}
						{@const modelColors: Record<string, string> = {
							haiku: 'bg-yellow-500/20 text-yellow-400',
							sonnet: 'bg-orange-500/20 text-orange-400',
							opus: 'bg-red-500/20 text-red-400'
						}}
						{@const modelsDisplay = mp.models_used.join(' → ')}
						{@const durationSec = (mp.total_duration_ms / 1000).toFixed(1)}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]" data-testid="multipass-section">
							<h4
								class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2"
								title="Détails du processus d'analyse multi-pass : nombre de passes, modèles utilisés, et temps d'exécution"
							>
								🔬 Analyse
							</h4>

							<!-- Summary line -->
							<div class="flex flex-wrap items-center gap-2 text-sm text-[var(--color-text-secondary)]" data-testid="multipass-summary">
								<span title="Nombre de passes d'analyse effectuées (1 à 5). Plus de passes = email plus complexe" data-testid="multipass-passes-count">{mp.passes_count} {mp.passes_count === 1 ? 'pass' : 'passes'}</span>
								<span class="text-[var(--color-text-tertiary)]">•</span>
								<!-- Confidence Sparkline (v2.3.1) -->
								{#if mp.pass_history && mp.pass_history.length > 0}
									<ConfidenceSparkline passHistory={mp.pass_history} id={item.id} />
									<span class="text-[var(--color-text-tertiary)]">•</span>
								{/if}
								<span class="font-mono text-xs" title="Séquence des modèles IA utilisés : Haiku (rapide), Sonnet (équilibré), Opus (puissant)" data-testid="multipass-models">{modelsDisplay}</span>
								<span class="text-[var(--color-text-tertiary)]">•</span>
								<span title="Temps total d'analyse par l'IA" data-testid="multipass-duration">{durationSec}s</span>
								{#if mp.escalated}
									<span class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400" title="L'IA a escaladé vers un modèle plus puissant car la confiance initiale était insuffisante" data-testid="multipass-escalated">
										↑ Escalade
									</span>
								{/if}
								{#if mp.high_stakes}
									<span class="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-400" title="Email détecté comme important : contient des enjeux financiers, juridiques ou personnels significatifs" data-testid="multipass-high-stakes">
										⚠️ High stakes
									</span>
								{/if}
							</div>

							<!-- Stop reason -->
							{#if mp.stop_reason}
								{@const stopReasonLabels: Record<string, string> = {
									'confidence_sufficient': 'Confiance suffisante',
									'max_passes': 'Maximum de passes atteint',
									'no_changes': 'Pas de changement'
								}}
								{@const stopReasonTooltips: Record<string, string> = {
									'confidence_sufficient': 'L\'analyse s\'est arrêtée car le niveau de confiance requis a été atteint',
									'max_passes': 'L\'analyse a atteint le nombre maximum de passes autorisées (5)',
									'no_changes': 'L\'analyse s\'est arrêtée car la passe supplémentaire n\'a pas amélioré la confiance'
								}}
								<div class="mt-2 text-xs text-[var(--color-text-tertiary)]" title={stopReasonTooltips[mp.stop_reason] ?? 'Raison de l\'arrêt de l\'analyse'} data-testid="multipass-stop-reason">
									Arrêt : {stopReasonLabels[mp.stop_reason] ?? mp.stop_reason}
								</div>
							{/if}

							<!-- Pass Timeline (v2.3.1) -->
							<details class="mt-3" data-testid="multipass-details">
								<summary class="text-xs text-[var(--color-text-tertiary)] cursor-pointer hover:text-[var(--color-text-secondary)]" title="Cliquez pour voir le detail de chaque passe d'analyse avec les questions/doutes de l'IA">
									💬 {mp.total_tokens.toLocaleString()} tokens <span class="opacity-60">(voir timeline)</span>
								</summary>
								<div class="mt-3" data-testid="multipass-pass-history">
									<PassTimeline passHistory={mp.pass_history} />
								</div>
							</details>
						</div>
					{:else}
						<!-- Legacy analysis (no multi_pass data) -->
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]" data-testid="multipass-legacy">
							<span class="text-xs text-[var(--color-text-tertiary)] italic" title="Cet email a été analysé avec une version antérieure du système, les métadonnées détaillées ne sont pas disponibles">
								Analyse legacy
							</span>
						</div>
					{/if}

					<!-- Entities (Sprint 2) -->
					{#if item.analysis.entities && Object.keys(item.analysis.entities).length > 0}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
								Entités détectées
							</h4>
							<div class="flex flex-wrap gap-1">
								{#each Object.entries(item.analysis.entities) as [type, entities]}
									{#each entities as entity}
										{@const entityClass = {
											person: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
											project: 'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
											date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
											amount: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
											organization: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300',
											discovered: 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300'
										}[type] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'}
										<span class="px-2 py-0.5 text-xs rounded-full {entityClass}">
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
								{@const noteActionClass = note.action === 'create' ? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300' : 'bg-amber-100 text-amber-700 dark:bg-yellow-500/20 dark:text-yellow-300'}
								{@const requiredClass = note.required ? 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-500/20 dark:text-gray-400'}
								<div class="flex items-center justify-between text-sm py-1">
									<span class="flex items-center gap-2">
										<span class="text-xs px-1.5 py-0.5 rounded {noteActionClass}">
											{note.action === 'create' ? '+ Créer' : '~ Enrichir'} {note.note_type}
										</span>
										{#if note.required}
											<span class="text-xs px-1.5 py-0.5 rounded {requiredClass}" title="Requis pour archiver en toute sécurité">
												Requis
											</span>
										{/if}
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

					<!-- v2.4: Proposed Tasks -->
					{#if item.analysis.proposed_tasks && item.analysis.proposed_tasks.length > 0}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
								Tâches proposées
							</h4>
							{#each item.analysis.proposed_tasks as task}
								<div class="flex items-center justify-between text-sm py-1">
									<span class="flex items-center gap-2">
										<span class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300">
											⚡ {task.project || 'Tâche'}
										</span>
										{task.title}
										{#if task.due_date}
											<span class="text-xs text-[var(--color-text-tertiary)]">
												📅 {new Date(task.due_date).toLocaleDateString('fr-FR')}
											</span>
										{/if}
									</span>
									<span class="text-xs text-[var(--color-text-tertiary)]">
										{Math.round(task.confidence * 100)}%
									</span>
								</div>
							{/each}
						</div>
					{/if}

					<!-- Context Influence (AI explanation) -->
					{#if item.analysis.context_influence}
						<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
								🧠 Influence du contexte
							</h4>

							<!-- AI Explanation -->
							{#if item.analysis.context_influence.explanation}
								<p class="text-sm text-[var(--color-text-secondary)] mb-3">
									{item.analysis.context_influence.explanation}
								</p>
							{/if}

							<!-- Notes used -->
							{#if item.analysis.context_influence.notes_used?.length > 0}
								<div class="flex flex-wrap gap-1 mb-2">
									{#each item.analysis.context_influence.notes_used as noteName}
										<span class="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400">
											📝 {noteName}
										</span>
									{/each}
								</div>
							{/if}

							<!-- Confirmations -->
							{#if item.analysis.context_influence.confirmations?.length > 0}
								<div class="mb-2">
									<span class="text-xs text-green-400 font-medium">✓ Confirmé :</span>
									<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
										{#each item.analysis.context_influence.confirmations as confirmation}
											<li>{confirmation}</li>
										{/each}
									</ul>
								</div>
							{/if}

							<!-- Contradictions -->
							{#if item.analysis.context_influence.contradictions?.length > 0}
								<div class="mb-2">
									<span class="text-xs text-orange-400 font-medium">⚠ Contradiction :</span>
									<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
										{#each item.analysis.context_influence.contradictions as contradiction}
											<li>{contradiction}</li>
										{/each}
									</ul>
								</div>
							{/if}

							<!-- Missing info -->
							{#if item.analysis.context_influence.missing_info?.length > 0}
								<div class="mb-2">
									<span class="text-xs text-[var(--color-text-tertiary)] font-medium">❓ Manquant :</span>
									<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
										{#each item.analysis.context_influence.missing_info as missing}
											<li>{missing}</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Retrieved Context (raw data, collapsible) -->
					{#if item.analysis.retrieved_context && item.analysis.retrieved_context.total_results > 0}
						<details class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
							<summary class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2 cursor-pointer hover:text-[var(--color-text-secondary)]">
								📊 Contexte brut ({item.analysis.retrieved_context.total_results} résultats)
							</summary>

							<div class="mt-3 space-y-3">
								<!-- Entities searched -->
								{#if item.analysis.retrieved_context.entities_searched?.length > 0}
									<div>
										<span class="text-xs text-[var(--color-text-tertiary)]">Entités recherchées :</span>
										<div class="flex flex-wrap gap-1 mt-1">
											{#each item.analysis.retrieved_context.entities_searched as entity}
												<span class="text-xs px-2 py-0.5 rounded bg-[var(--glass-tint)] text-[var(--color-text-secondary)]">
													{entity}
												</span>
											{/each}
										</div>
									</div>
								{/if}

								<!-- Notes found -->
								{#if item.analysis.retrieved_context.notes?.length > 0}
									<div>
										<span class="text-xs text-[var(--color-text-tertiary)]">Notes trouvées :</span>
										<div class="mt-1 space-y-1">
											{#each item.analysis.retrieved_context.notes as note}
												<div class="flex items-center gap-2 text-xs">
													<span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
														{note.note_type}
													</span>
													<a href="/notes/{note.note_id}" class="text-[var(--color-accent)] hover:underline">
														{note.title}
													</a>
													<span class="text-[var(--color-text-tertiary)]">
														({Math.round(note.relevance * 100)}%)
													</span>
												</div>
											{/each}
										</div>
									</div>
								{/if}

								<!-- Calendar events -->
								{#if item.analysis.retrieved_context.calendar?.length > 0}
									<div>
										<span class="text-xs text-[var(--color-text-tertiary)]">Événements calendrier :</span>
										<div class="mt-1 space-y-1">
											{#each item.analysis.retrieved_context.calendar as event}
												<div class="text-xs text-[var(--color-text-secondary)]">
													📅 {event.date} - {event.title}
												</div>
											{/each}
										</div>
									</div>
								{/if}

								<!-- Tasks -->
								{#if item.analysis.retrieved_context.tasks?.length > 0}
									<div>
										<span class="text-xs text-[var(--color-text-tertiary)]">Tâches OmniFocus :</span>
										<div class="mt-1 space-y-1">
											{#each item.analysis.retrieved_context.tasks as task}
												<div class="text-xs text-[var(--color-text-secondary)]">
													⚡ {task.title}
													{#if task.project}
														<span class="text-[var(--color-text-tertiary)]">[{task.project}]</span>
													{/if}
												</div>
											{/each}
										</div>
									</div>
								{/if}

								<!-- Sources searched -->
								{#if item.analysis.retrieved_context.sources_searched?.length > 0}
									<div class="text-xs text-[var(--color-text-tertiary)]">
										Sources : {item.analysis.retrieved_context.sources_searched.join(', ')}
									</div>
								{/if}
							</div>
						</details>
					{:else if item.analysis.context_used && item.analysis.context_used.length > 0}
						<!-- Fallback: old context_used format -->
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
											<!-- v2.3.1: Why not X? -->
											{#if !option.is_recommended && option.rejection_reason}
												<p class="text-xs text-[var(--color-text-tertiary)] mt-2 italic" title="Raison pour laquelle cette option n'a pas ete recommandee" data-testid="option-rejection-reason">
													💡 {option.rejection_reason}
												</p>
											{/if}
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

					<!-- v2.3.1: Why Not Alternatives Section -->
					{#if item.analysis.options.some(o => !o.is_recommended && o.rejection_reason)}
						<details class="mt-3" data-testid="why-not-section">
							<summary class="text-xs text-[var(--color-text-tertiary)] cursor-pointer hover:text-[var(--color-text-secondary)]" title="Voir pourquoi les autres options n'ont pas ete recommandees">
								🤔 Pourquoi pas les autres options ?
							</summary>
							<div class="mt-2 p-3 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border-subtle)] space-y-2">
								{#each item.analysis.options.filter(o => !o.is_recommended && o.rejection_reason) as option}
									<div class="text-sm" data-testid="why-not-item">
										<span class="font-medium text-[var(--color-text-secondary)]">{option.action}</span>
										<span class="text-[var(--color-text-tertiary)]">:</span>
										<span class="text-[var(--color-text-tertiary)] italic ml-1">{option.rejection_reason}</span>
									</div>
								{/each}
							</div>
						</details>
					{/if}

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
											onclick={() => handleSnooze('in_30_min')}
										>
											&#9203; 30 minutes
										</button>
										<button
											class="w-full px-4 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint)] transition-colors"
											onclick={() => handleSnooze('in_2_hours')}
										>
											&#9203; 2 heures
										</button>
										<button
											class="w-full px-4 py-2 text-left text-sm text-[var(--color-text-secondary)] hover:bg-[var(--glass-tint)] transition-colors"
											onclick={() => handleSnooze('tomorrow')}
										>
											&#127749; Demain matin
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
