<script lang="ts">
	import type { QueueItem, ActionOption } from '$lib/api';
	import { Card, Button, Badge } from '$lib/components/ui';
	import { filterNotes, filterTasks } from '$lib/utils/peripeties';
	import ConfidenceSparkline from './ConfidenceSparkline.svelte';
	import PassTimeline from './PassTimeline.svelte';

	interface Props {
		item: QueueItem;
		showDetails: boolean;
		onSelectOption: (item: QueueItem, option: ActionOption) => void;
		onDelete: (item: QueueItem) => void;
		onReanalyze: (item: QueueItem) => void;
		onSkip: () => void;
	}

	let { item, showDetails, onSelectOption, onDelete, onReanalyze, onSkip }: Props = $props();

	const notes = $derived(filterNotes(item.analysis.proposed_notes, showDetails));
	const tasks = $derived(filterTasks(item.analysis.proposed_tasks, showDetails));

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
</script>

<div class="space-y-6">
	<Card
		padding="none"
		class="overflow-hidden border-t-4"
		style="border-top-color: var(--color-accent)"
	>
		<header class="p-6 border-b border-[var(--glass-border-subtle)] bg-[var(--glass-tint)]">
			<div class="flex justify-between items-start mb-4">
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-3 mb-2">
						{#if item.analysis.multi_pass?.high_stakes}
							<Badge class="bg-[var(--color-error)]/10 text-[var(--color-error)] animate-pulse"
								>IMPORTANT</Badge
							>
						{/if}
						<span class="text-xs font-mono opacity-50 uppercase tracking-widest"
							>{formatDate(item.metadata.date)}</span
						>
					</div>
					<h2 class="text-2xl font-bold text-[var(--color-text-primary)] leading-tight mb-1">
						{item.metadata.subject || '(Sans objet)'}
					</h2>
					<p class="text-[var(--color-text-secondary)] flex items-center gap-2">
						<span class="opacity-50">De:</span>
						<span class="font-medium text-[var(--color-text-primary)]"
							>{item.metadata.from_name || item.metadata.from_address}</span
						>
						{#if item.metadata.from_name && item.metadata.from_address}
							<span class="text-xs opacity-30">&lt;{item.metadata.from_address}&gt;</span>
						{/if}
					</p>
				</div>
				<div class="flex flex-col items-end gap-3 shrink-0">
					<div class="flex gap-2">
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

		<div class="p-6">
			<div
				class="prose prose-sm dark:prose-invert max-w-none mb-8 bg-white/5 p-4 rounded-2xl italic border-l-2 border-[var(--color-accent)]/30"
			>
				<p class="text-[var(--color-text-secondary)] leading-relaxed">
					{item.analysis.reasoning}
				</p>
			</div>

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
								class="flex items-start gap-3 p-4 rounded-2xl glass-subtle border border-white/5 hover:border-[var(--color-accent)]/30 transition-colors group"
							>
								<span class="text-2xl mt-1 group-hover:scale-110 transition-transform">📝</span>
								<div class="flex-1 min-w-0">
									<p class="text-sm font-bold text-[var(--color-text-primary)] mb-1 truncate">
										{note.title}
									</p>
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
