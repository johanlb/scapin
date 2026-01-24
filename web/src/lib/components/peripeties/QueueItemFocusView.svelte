<script lang="ts">
	import type { QueueItem, ActionOption } from '$lib/api';
	import { Card, Button, Badge } from '$lib/components/ui';
	import { FileAttachment } from '$lib/components/files';
	import { filterNotes, filterTasks } from '$lib/utils/peripeties';
	import ConfidenceSparkline from './ConfidenceSparkline.svelte';
	import PassTimeline from './PassTimeline.svelte';
	import { formatRelativeTime } from '$lib/utils/formatters';

	interface Props {
		item: QueueItem;
		showDetails: boolean;
		onSelectOption: (item: QueueItem, option: ActionOption) => void;
		onDelete: (item: QueueItem) => void;
		onReanalyze: (item: QueueItem) => void;
		onSkip: () => void;
	}

	let { item, showDetails: initialShowDetails, onSelectOption, onDelete, onReanalyze, onSkip }: Props = $props();

	// Local toggle for details mode
	let showLevel3 = $state(initialShowDetails);

	// Toggle for HTML/Text email content
	let showHtmlContent = $state(true);

	const notes = $derived(filterNotes(item.analysis.proposed_notes, showLevel3));
	const tasks = $derived(filterTasks(item.analysis.proposed_tasks, showLevel3));

	// Complexity badges
	const complexityBadges = $derived(() => {
		if (!item.analysis.multi_pass) return { isQuick: false, hasContext: false, isComplex: false, usedOpus: false };
		const mp = item.analysis.multi_pass;
		return {
			isQuick: mp.passes_count === 1 && mp.final_model === 'haiku',
			hasContext: mp.pass_history?.some(p => p.context_searched) ?? false,
			isComplex: mp.passes_count >= 3,
			usedOpus: mp.final_model === 'opus' || mp.models_used?.includes('opus')
		};
	});

	// Avatar initials
	const avatarInitials = $derived(() => {
		const name = item.metadata.from_name || item.metadata.from_address || '?';
		return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || '?';
	});

	// Check if we have retrieved context to show
	const hasRetrievedContext = $derived(
		item.analysis.retrieved_context && item.analysis.retrieved_context.total_results > 0
	);

	// Check if we have entities to show
	const hasEntities = $derived(
		item.analysis.entities && Object.keys(item.analysis.entities).length > 0
	);

	// Check if we have context influence to show
	const hasContextInfluence = $derived(!!item.analysis.context_influence);

	// Check if we have questions raised in pass history
	const hasQuestions = $derived(
		item.analysis.multi_pass?.pass_history?.some(p => p.questions && p.questions.length > 0) ?? false
	);

	function formatDate(dateStr: string | null) {
		if (!dateStr) return 'Inconnue';
		return new Date(dateStr).toLocaleString('fr-FR', {
			weekday: 'long',
			day: 'numeric',
			month: 'long',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Entity color mapping
	function getEntityClass(type: string): string {
		const colors: Record<string, string> = {
			person: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
			project: 'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
			date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
			amount: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
			organization: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300'
		};
		return colors[type] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300';
	}
</script>

<div class="space-y-6">
	<Card
		padding="none"
		class="overflow-hidden border-t-4"
		style="border-top-color: var(--color-accent)"
	>
		<header class="p-6 border-b border-[var(--glass-border-subtle)] bg-[var(--glass-tint)]">
			<!-- Dates and complexity badges -->
			<div class="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-[var(--color-text-tertiary)] mb-4">
				{#if item.metadata.date}
					<span class="flex items-center gap-1.5" title="Date de réception de l'email">
						<span class="text-base">📨</span>
						<span class="font-medium text-[var(--color-text-secondary)]">Reçu</span>
						{formatRelativeTime(item.metadata.date)}
					</span>
				{/if}
				{#if item.timestamps?.analysis_completed_at || item.queued_at}
					<span class="flex items-center gap-1.5" title="Date d'analyse par Scapin">
						<span class="text-base">🧠</span>
						<span class="font-medium text-[var(--color-text-secondary)]">Analysé</span>
						{formatRelativeTime(item.timestamps?.analysis_completed_at || item.queued_at)}
					</span>
				{/if}
				<!-- Complexity badges -->
				{#if item.analysis.multi_pass}
					{@const badges = complexityBadges()}
					<div class="flex items-center gap-1 ml-auto">
						{#if badges.isQuick}
							<span class="text-base" title="Analyse rapide : 1 pass avec Haiku" data-testid="badge-quick">⚡</span>
						{/if}
						{#if badges.hasContext}
							<span class="text-base" title="Contexte personnel utilisé" data-testid="badge-context">🔍</span>
						{/if}
						{#if badges.isComplex}
							<span class="text-base" title="Analyse complexe : {item.analysis.multi_pass.passes_count} passes" data-testid="badge-complex">🧠</span>
						{/if}
						{#if badges.usedOpus}
							<span class="text-base" title="Analyse avec Opus (modèle le plus puissant)" data-testid="badge-opus">🏆</span>
						{/if}
						<!-- v3.2: Canevas status badge -->
						{#if item.analysis.multi_pass.canevas_status}
							{@const cs = item.analysis.multi_pass.canevas_status}
							{#if cs.completeness === 'complete'}
								<span class="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400"
									title="Canevas complet: {cs.files_present} fichiers ({cs.total_chars} chars)">
									📜 Complet
								</span>
							{:else if cs.completeness === 'partial'}
								<span class="text-xs px-2 py-0.5 rounded bg-orange-500/20 text-orange-400"
									title="Fichiers partiels: {cs.files.filter(f => f.status !== 'present').map(f => f.name).join(', ')}">
									⚠️ Partiel ({cs.files_present}/{cs.files.length})
								</span>
							{:else}
								<span class="text-xs px-2 py-0.5 rounded bg-red-500/20 text-red-400"
									title="Fichiers manquants: {cs.files.filter(f => f.status === 'missing').map(f => f.name).join(', ')}">
									❌ Manquant
								</span>
							{/if}
						{/if}
					</div>
				{/if}
			</div>

			<div class="flex justify-between items-start mb-4">
				<!-- Avatar and sender info -->
				<div class="flex items-start gap-4 flex-1 min-w-0">
					<div
						class="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--color-accent)] to-purple-500 flex items-center justify-center text-white font-semibold shrink-0"
					>
						{avatarInitials()}
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-3 mb-2">
							{#if item.analysis.multi_pass?.high_stakes}
								<Badge class="bg-[var(--color-error)]/10 text-[var(--color-error)] animate-pulse"
									>IMPORTANT</Badge
								>
							{/if}
						</div>
						<h2 class="text-2xl font-bold text-[var(--color-text-primary)] leading-tight mb-1">
							{item.metadata.subject || '(Sans objet)'}
						</h2>
						<p class="text-[var(--color-text-secondary)] flex items-center gap-2">
							<span class="font-medium text-[var(--color-text-primary)]"
								>{item.metadata.from_name || item.metadata.from_address}</span
							>
							{#if item.metadata.from_name && item.metadata.from_address}
								<span class="text-xs opacity-30">&lt;{item.metadata.from_address}&gt;</span>
							{/if}
						</p>
					</div>
				</div>
				<div class="flex flex-col items-end gap-3 shrink-0">
					<div class="flex gap-2">
						<Button
							variant={showLevel3 ? 'primary' : 'ghost'}
							size="sm"
							onclick={() => (showLevel3 = !showLevel3)}
							class="glass-interactive"
							title="Afficher les détails"
						>
							{showLevel3 ? '📖' : '📋'}
						</Button>
						<Button variant="secondary" size="sm" onclick={onSkip} class="glass-interactive"
							>Ignorer</Button
						>
						<button
							onclick={() => onDelete(item)}
							class="p-2 rounded-xl glass-interactive hover:bg-red-500/20 text-red-500 transition-colors"
							title="Supprimer"
						>
							🗑️
						</button>
					</div>

					{#if item.analysis.multi_pass}
						<div class="glass-subtle p-2 rounded-xl flex flex-col items-center">
							<ConfidenceSparkline passHistory={item.analysis.multi_pass.pass_history} />
							<div class="text-[9px] font-bold uppercase mt-1 opacity-40">Progression</div>
						</div>
					{/if}
				</div>
			</div>

			{#if item.analysis.multi_pass}
				<div class="mt-4">
					<PassTimeline passHistory={item.analysis.multi_pass.pass_history} />
				</div>
			{/if}
		</header>

		<div class="p-6 space-y-6">
			<!-- Reasoning -->
			<div
				class="prose prose-sm dark:prose-invert max-w-none bg-white/5 p-4 rounded-2xl italic border-l-2 border-[var(--color-accent)]/30"
			>
				<p class="text-[var(--color-text-secondary)] leading-relaxed">
					{item.analysis.reasoning}
				</p>
			</div>

			<!-- SECTION: Retrieved Context (visible by default as collapsible) -->
			{#if hasRetrievedContext && item.analysis.retrieved_context}
				{@const ctx = item.analysis.retrieved_context}
				<details class="rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] overflow-hidden">
					<summary class="px-3 py-2 text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide cursor-pointer hover:bg-[var(--color-bg-tertiary)]">
						📊 Contexte récupéré ({ctx.total_results} résultats)
					</summary>

					<div class="px-3 pb-3 space-y-3">
						<!-- Entities searched -->
						{#if ctx.entities_searched?.length > 0}
							<div>
								<span class="text-xs text-[var(--color-text-tertiary)]">Entités recherchées :</span>
								<div class="flex flex-wrap gap-1 mt-1">
									{#each ctx.entities_searched as entity}
										<span class="text-xs px-2 py-0.5 rounded bg-[var(--glass-tint)] text-[var(--color-text-secondary)]">
											{entity}
										</span>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Notes found -->
						{#if ctx.notes?.length > 0}
							<div>
								<span class="text-xs text-[var(--color-text-tertiary)]">Notes trouvées :</span>
								<div class="mt-1 space-y-1">
									{#each ctx.notes as note}
										<div class="flex items-center gap-2 text-xs">
											<span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
												{note.note_type}
											</span>
											<a href="/memoires/{note.path ? `${note.path}/${note.note_id}` : note.note_id}" class="text-[var(--color-accent)] hover:underline">
												{note.title}
											</a>
											<span class="text-[var(--color-text-tertiary)]">
												({Math.round((note.relevance ?? 0) * 100)}%)
											</span>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Calendar events -->
						{#if ctx.calendar?.length > 0}
							<div>
								<span class="text-xs text-[var(--color-text-tertiary)]">Événements calendrier :</span>
								<div class="mt-1 space-y-1">
									{#each ctx.calendar as event}
										<div class="text-xs text-[var(--color-text-secondary)]">
											📅 {event.date} - {event.title}
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Tasks -->
						{#if ctx.tasks?.length > 0}
							<div>
								<span class="text-xs text-[var(--color-text-tertiary)]">Tâches OmniFocus :</span>
								<div class="mt-1 space-y-1">
									{#each ctx.tasks as task}
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
						{#if ctx.sources_searched?.length > 0}
							<div class="text-xs text-[var(--color-text-tertiary)]">
								Sources : {ctx.sources_searched.join(', ')}
							</div>
						{/if}
					</div>
				</details>
			{/if}

			<!-- SECTION: Entities (Details mode only) -->
			{#if showLevel3 && hasEntities}
				<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)]">
					<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase mb-2">
						Entités extraites
					</p>
					<div class="flex flex-wrap gap-1">
						{#each Object.entries(item.analysis.entities) as [type, entities]}
							{#each entities as entity}
								<span class="px-2 py-0.5 text-xs rounded-full {getEntityClass(type)}"
									>{entity.value}</span
								>
							{/each}
						{/each}
					</div>
				</div>
			{/if}

			<!-- SECTION: Context Used (Details mode only) -->
			{#if showLevel3 && item.analysis.context_used && item.analysis.context_used.length > 0}
				<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)]">
					<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase mb-2">
						Contexte utilisé
					</p>
					<div class="flex flex-wrap gap-1">
						{#each item.analysis.context_used as noteId}
							<a
								href="/memoires/{noteId}"
								class="text-xs px-2 py-0.5 rounded-full bg-[var(--color-event-notes)]/20 text-[var(--color-event-notes)] hover:bg-[var(--color-event-notes)]/30"
							>
								📝 {noteId.slice(0, 15)}...
							</a>
						{/each}
					</div>
				</div>
			{/if}

			<!-- SECTION: Analysis Transparency (Details mode only) -->
			{#if showLevel3 && item.analysis.multi_pass}
				{@const mp = item.analysis.multi_pass}
				<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)] space-y-3">
					<div class="flex items-center justify-between">
						<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">
							Transparence de l'Analyse
						</p>
						<span class="text-xs text-[var(--color-text-tertiary)]">
							{mp.passes_count} pass{mp.passes_count > 1 ? 'es' : ''} • {mp.final_model}
							{#if mp.escalated}
								• <span class="text-amber-500">escaladé</span>
							{/if}
						</span>
					</div>

					<!-- Confidence Sparkline -->
					{#if mp.pass_history && mp.pass_history.length > 0}
						<div>
							<p class="text-xs text-[var(--color-text-tertiary)] mb-1">Évolution de la confiance</p>
							<ConfidenceSparkline passHistory={mp.pass_history} id={item.id} />
						</div>
					{/if}

					<!-- Pass Timeline -->
					{#if mp.pass_history && mp.pass_history.length > 0}
						<div>
							<p class="text-xs text-[var(--color-text-tertiary)] mb-1">Détail des passes</p>
							<PassTimeline passHistory={mp.pass_history} />
						</div>
					{/if}

					<!-- Context Influence -->
					{#if hasContextInfluence && item.analysis.context_influence}
						{@const ci = item.analysis.context_influence}
						<div class="p-2 rounded bg-[var(--color-bg-tertiary)]">
							<p class="text-xs font-medium text-[var(--color-text-secondary)] mb-1">
								💡 Influence du contexte
							</p>
							{#if ci.explanation}
								<p class="text-xs text-[var(--color-text-secondary)]">{ci.explanation}</p>
							{/if}
							{#if ci.confirmations && ci.confirmations.length > 0}
								<div class="mt-1">
									<span class="text-xs text-green-600">✓ Confirmé :</span>
									<span class="text-xs text-[var(--color-text-tertiary)]">
										{ci.confirmations.join(', ')}
									</span>
								</div>
							{/if}
							{#if ci.contradictions && ci.contradictions.length > 0}
								<div class="mt-1">
									<span class="text-xs text-red-600">✗ Contradictions :</span>
									<span class="text-xs text-[var(--color-text-tertiary)]">
										{ci.contradictions.join(', ')}
									</span>
								</div>
							{/if}
							{#if ci.missing_info && ci.missing_info.length > 0}
								<div class="mt-1">
									<span class="text-xs text-[var(--color-text-tertiary)] font-medium">❓ Manquant :</span>
									<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
										{#each ci.missing_info as missing}
											<li>{missing}</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Questions raised -->
					{#if hasQuestions}
						<div class="p-2 rounded bg-blue-50 dark:bg-blue-900/20">
							<p class="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
								💭 Questions soulevées
							</p>
							<ul class="text-xs text-blue-600 dark:text-blue-400 space-y-0.5">
								{#each mp.pass_history as pass}
									{#if pass.questions && pass.questions.length > 0}
										{#each pass.questions as question}
											<li>• {question}</li>
										{/each}
									{/if}
								{/each}
							</ul>
						</div>
					{/if}

					<!-- Stop reason -->
					{#if mp.stop_reason}
						<p class="text-xs text-[var(--color-text-tertiary)]">
							Raison d'arrêt : <span class="font-mono">{mp.stop_reason}</span>
						</p>
					{/if}
				</div>
			{/if}

			<!-- SECTION: Metadata (Details mode only) -->
			{#if showLevel3}
				<div
					class="flex flex-wrap gap-2 text-xs text-[var(--color-text-tertiary)] p-2 rounded-lg bg-[var(--color-bg-secondary)]"
				>
					<span>📧 {item.metadata.from_address}</span>
					<span>📁 {item.metadata.folder || 'INBOX'}</span>
					<span>🕐 {formatRelativeTime(item.timestamps?.analysis_completed_at || item.queued_at)}</span>
				</div>
			{/if}

			<!-- SECTION: Proposed Notes & Tasks -->
			{#if notes.length > 0 || tasks.length > 0}
				<section class="space-y-4 mb-8">
					<h3
						class="text-[10px] font-bold text-[var(--color-text-tertiary)] uppercase tracking-[0.2em]"
					>
						Effets de bord proposés
					</h3>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						{#each notes as note}
							<div
								class="flex items-start gap-3 p-4 rounded-2xl glass-subtle border border-white/5 hover:border-[var(--color-accent)]/30 transition-colors group {note.action === 'create' ? 'ring-1 ring-emerald-500/30' : ''}"
							>
								<span class="text-2xl mt-1 group-hover:scale-110 transition-transform">{note.action === 'create' ? '✨' : '📝'}</span>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<p class="text-sm font-bold text-[var(--color-text-primary)] truncate">
											{note.title}
										</p>
										{#if note.action === 'create'}
											<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 font-medium shrink-0">
												NOUVELLE
											</span>
										{/if}
									</div>
									<p class="text-xs text-[var(--color-text-tertiary)] line-clamp-2">
										{note.content_summary}
									</p>
								</div>
							</div>
						{/each}
						{#each tasks as task}
							<div
								class="flex items-start gap-3 p-4 rounded-2xl glass-subtle border border-white/5 hover:border-[var(--color-success)]/30 transition-colors group"
							>
								<span class="text-2xl mt-1 group-hover:scale-110 transition-transform">✅</span>
								<div class="flex-1 min-w-0">
									<p class="text-sm font-bold text-[var(--color-text-primary)] mb-1 truncate">
										{task.title}
									</p>
									{#if task.due_date}
										<p
											class="text-[10px] text-[var(--color-success)] font-medium uppercase tracking-wider"
										>
											Pour: {formatDate(task.due_date)}
										</p>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<section class="space-y-4">
				<h3
					class="text-[10px] font-bold text-[var(--color-text-tertiary)] uppercase tracking-[0.2em]"
				>
					Décisions possibles
				</h3>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
					{#each item.analysis.options || [] as option}
						<button
							class="w-full text-left p-4 rounded-2xl transition-all duration-300 border liquid-press
								{option.is_recommended
								? 'bg-[var(--color-accent)] text-white border-transparent shadow-lg shadow-[var(--color-accent)]/20'
								: 'glass-subtle text-[var(--color-text-primary)] border-white/5 hover:border-white/20'}"
							onclick={() => onSelectOption(item, option)}
						>
							<div class="flex justify-between items-center mb-2">
								<p class="font-black text-sm uppercase tracking-widest">{option.action}</p>
								{#if option.is_recommended}
									<span class="text-[10px] bg-white/20 px-2 py-0.5 rounded-full font-bold"
										>RECOMMANDÉ</span
									>
								{/if}
							</div>
							<p class="text-xs opacity-80 leading-snug line-clamp-2">{option.reasoning}</p>
						</button>
					{/each}
				</div>
			</section>

			<!-- SECTION: EMAIL CONTENT -->
			<div class="rounded-lg border border-[var(--color-border)] overflow-hidden">
				<div
					class="flex items-center justify-between px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]"
				>
					<span class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase"
						>Email</span
					>
					{#if item.content?.html_body}
						<div class="flex gap-1">
							<button
								class="text-xs px-2 py-0.5 rounded {!showHtmlContent
									? 'bg-[var(--color-accent)] text-white'
									: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
								onclick={() => (showHtmlContent = false)}>Texte</button
							>
							<button
								class="text-xs px-2 py-0.5 rounded {showHtmlContent
									? 'bg-[var(--color-accent)] text-white'
									: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
								onclick={() => (showHtmlContent = true)}>HTML</button
							>
						</div>
					{/if}
				</div>
				{#if showHtmlContent && item.content?.html_body}
					<iframe
						srcdoc={item.content.html_body}
						sandbox=""
						class="w-full h-96 bg-white"
						title="Email HTML"
					></iframe>
				{:else}
					<div
						class="p-3 text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap max-h-96 overflow-y-auto bg-[var(--color-bg-primary)]"
					>
						{item.content?.full_text ||
							item.content?.preview ||
							'Aucun contenu'}
					</div>
				{/if}
			</div>

			<!-- SECTION: ATTACHMENTS -->
			{#if item.metadata.attachments && item.metadata.attachments.length > 0}
				<div class="rounded-lg border border-[var(--color-border)] overflow-hidden">
					<div
						class="px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]"
					>
						<span class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">
							📎 Pièces jointes ({item.metadata.attachments.length})
						</span>
					</div>
					<div class="p-3 space-y-2">
						{#each item.metadata.attachments as attachment (attachment.filename)}
							<FileAttachment {attachment} emailId={item.metadata.id} />
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</Card>

	<div class="flex justify-center">
		<button
			onclick={() => onReanalyze(item)}
			class="px-6 py-3 rounded-2xl glass-prominent hover:glass text-sm font-bold transition-all hover:scale-105 active:scale-95 group"
			data-testid="reanalyze-button"
			title="Réanalyser cet élément avec un modèle plus puissant"
		>
			<span class="mr-2 group-hover:rotate-12 inline-block transition-transform">🧠</span>
			Réanalyser avec Claude 3.5 Opus
		</button>
	</div>
</div>
