<script lang="ts">
	import type { QueueItem } from '$lib/api';
	import { Badge } from '$lib/components/ui';

	interface Props {
		items: QueueItem[];
		onSelectItem: (item: QueueItem) => void;
	}

	let { items, onSelectItem }: Props = $props();

	function formatDate(dateStr: string | null) {
		if (!dateStr) return 'Date inconnue';
		return new Date(dateStr).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusColor(status: string) {
		switch (status) {
			case 'completed':
				return 'var(--color-success)';
			case 'rejected':
				return 'var(--color-error)';
			case 'processing':
				return 'var(--color-accent)';
			case 'snoozed':
				return 'var(--color-warning)';
			default:
				return 'var(--color-text-tertiary)';
		}
	}

	function getStatusLabel(status: string) {
		switch (status) {
			case 'completed':
				return 'Terminé';
			case 'rejected':
				return 'Rejeté';
			case 'processing':
				return 'En cours';
			case 'snoozed':
				return 'Attente';
			case 'pending':
				return 'À traiter';
			default:
				return status;
		}
	}
</script>

<div class="space-y-3">
	{#each items as item (item.id)}
		<button
			class="w-full text-left p-4 rounded-2xl glass hover:bg-white/5 transition-all duration-200 border border-transparent hover:border-white/10 group"
			onclick={() => onSelectItem(item)}
			data-testid="peripeties-item-{item.id}"
		>
			<div class="flex justify-between items-start gap-4">
				<div class="flex-1 min-w-0">
					<div class="flex items-center gap-2 mb-1.5">
						<span class="text-[10px] font-mono opacity-50 uppercase tracking-wider"
							>{formatDate(item.metadata.date)}</span
						>
						{#if item.status !== 'pending'}
							<div
								class="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-tighter rounded"
								style="background: color-mix(in srgb, {getStatusColor(
									item.status
								)} 20%, transparent); color: {getStatusColor(item.status)}"
							>
								{getStatusLabel(item.status)}
							</div>
						{/if}
						{#if item.metadata.has_attachments}
							<span class="text-xs opacity-40">📎</span>
						{/if}
					</div>
					<h3
						class="font-bold text-sm md:text-base truncate group-hover:text-[var(--color-accent)] transition-colors"
					>
						{item.metadata.subject || '(Sans objet)'}
					</h3>
					<p class="text-xs opacity-50 truncate mt-0.5">
						{item.metadata.from_name || item.metadata.from_address}
					</p>
				</div>

				<div class="flex flex-col items-end shrink-0">
					<div
						class="text-xs font-bold"
						style="color: {item.analysis.confidence > 0.8
							? 'var(--color-success)'
							: item.analysis.confidence > 0.5
								? 'var(--color-accent)'
								: 'var(--color-text-tertiary)'}"
					>
						{Math.round(item.analysis.confidence * 100)}%
					</div>
					<div class="text-[9px] uppercase tracking-tighter opacity-30 font-semibold">
						Confiance
					</div>

					{#if item.analysis.proposed_notes.length > 0 || item.analysis.proposed_tasks.length > 0}
						<div class="flex gap-1 mt-2">
							{#if item.analysis.proposed_notes.length > 0}
								<span class="text-[10px] opacity-40" title="Notes"
									>📝 {item.analysis.proposed_notes.length}</span
								>
							{/if}
							{#if item.analysis.proposed_tasks.length > 0}
								<span class="text-[10px] opacity-40" title="Tâches"
									>✅ {item.analysis.proposed_tasks.length}</span
								>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			{#if item.analysis.reasoning && items.length < 10}
				<p class="text-xs opacity-40 mt-3 line-clamp-2 italic border-l-2 border-white/5 pl-3">
					"{item.analysis.reasoning}"
				</p>
			{/if}
		</button>
	{/each}
</div>
