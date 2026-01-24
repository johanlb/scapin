<!--
	PendingActionCard Component
	Displays a single pending retouche action with approve/reject buttons.
-->
<script lang="ts">
	import { Button } from '$lib/components/ui';
	import type { PendingRetoucheAction } from '$lib/api';

	interface Props {
		action: PendingRetoucheAction;
		loading?: boolean;
		onapprove?: () => void;
		onreject?: () => void;
		onclick?: () => void;
	}

	let { action, loading = false, onapprove, onreject, onclick }: Props = $props();

	function formatConfidence(confidence: number): string {
		return `${Math.round(confidence * 100)}%`;
	}

	function getActionIcon(type: string): string {
		switch (type) {
			case 'flag_obsolete':
				return '🗑️';
			case 'merge_into':
				return '🔀';
			case 'move_to_folder':
				return '📁';
			default:
				return '✨';
		}
	}

	function getActionLabel(type: string): string {
		switch (type) {
			case 'flag_obsolete':
				return 'Obsolète';
			case 'merge_into':
				return 'Fusionner';
			case 'move_to_folder':
				return 'Déplacer';
			default:
				return type;
		}
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 0.85) return 'var(--color-success)';
		if (confidence >= 0.6) return 'var(--color-warning)';
		return 'var(--color-error)';
	}

	function getConfidenceBgColor(confidence: number): string {
		if (confidence >= 0.85) return 'rgba(var(--color-success-rgb, 34, 197, 94), 0.1)';
		if (confidence >= 0.6) return 'rgba(var(--color-warning-rgb, 234, 179, 8), 0.1)';
		return 'rgba(var(--color-error-rgb, 239, 68, 68), 0.1)';
	}

	function handleApprove(e: MouseEvent) {
		e.stopPropagation();
		onapprove?.();
	}

	function handleReject(e: MouseEvent) {
		e.stopPropagation();
		onreject?.();
	}

	function handleClick() {
		onclick?.();
	}
</script>

<button
	type="button"
	class="w-full text-left p-4 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] hover:border-[var(--color-accent)] transition-colors"
	onclick={handleClick}
	data-testid="pending-action-card"
>
	<div class="flex items-start gap-3">
		<!-- Icon -->
		<div class="text-2xl flex-shrink-0" aria-hidden="true">
			{getActionIcon(action.action_type)}
		</div>

		<!-- Content -->
		<div class="flex-1 min-w-0">
			<!-- Header row -->
			<div class="flex items-start justify-between gap-2 mb-1">
				<h3 class="font-medium text-[var(--color-text-primary)] truncate">
					{action.note_title}
				</h3>
				<span
					class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
					style="background: {getConfidenceBgColor(action.confidence)}; color: {getConfidenceColor(action.confidence)}"
				>
					{formatConfidence(action.confidence)}
				</span>
			</div>

			<!-- Action type and path -->
			<div class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] mb-2">
				<span class="font-medium">{getActionLabel(action.action_type)}</span>
				{#if action.note_path}
					<span class="text-[var(--color-text-tertiary)]">•</span>
					<span class="text-[var(--color-text-tertiary)] truncate">{action.note_path}</span>
				{/if}
			</div>

			<!-- Target info for merge/move -->
			{#if action.action_type === 'merge_into' && action.target_note_title}
				<div class="text-sm text-[var(--color-text-secondary)] mb-2">
					→ <span class="font-medium">{action.target_note_title}</span>
				</div>
			{:else if action.action_type === 'move_to_folder' && action.target_folder}
				<div class="text-sm text-[var(--color-text-secondary)] mb-2">
					→ <span class="font-medium">{action.target_folder}</span>
				</div>
			{/if}

			<!-- Reasoning preview -->
			{#if action.reasoning}
				<p class="text-sm text-[var(--color-text-tertiary)] line-clamp-2 mb-3">
					{action.reasoning}
				</p>
			{/if}

			<!-- Actions -->
			<div class="flex items-center gap-2">
				<Button
					variant="ghost"
					size="sm"
					onclick={handleReject}
					disabled={loading}
				>
					Rejeter
				</Button>
				<Button
					variant="primary"
					size="sm"
					onclick={handleApprove}
					{loading}
				>
					Approuver
				</Button>
			</div>
		</div>
	</div>
</button>
