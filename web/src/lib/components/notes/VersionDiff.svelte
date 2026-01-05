<script lang="ts">
	/**
	 * VersionDiff Component
	 * Displays a unified diff between two versions with colored additions/deletions
	 */
	import type { NoteDiff } from '$lib/api/client';

	interface Props {
		diff: NoteDiff;
		fromLabel?: string;
		toLabel?: string;
		class?: string;
	}

	let { diff, fromLabel, toLabel, class: className = '' }: Props = $props();

	// Parse diff text into lines with types
	interface DiffLine {
		type: 'addition' | 'deletion' | 'context' | 'header';
		content: string;
	}

	const parsedLines = $derived.by(() => {
		const lines: DiffLine[] = [];
		const diffLines = diff.diff_text.split('\n');

		for (const line of diffLines) {
			if (line.startsWith('+++') || line.startsWith('---')) {
				// Skip file headers
				continue;
			} else if (line.startsWith('@@')) {
				lines.push({ type: 'header', content: line });
			} else if (line.startsWith('+')) {
				lines.push({ type: 'addition', content: line.slice(1) });
			} else if (line.startsWith('-')) {
				lines.push({ type: 'deletion', content: line.slice(1) });
			} else if (line.startsWith(' ') || line === '') {
				lines.push({ type: 'context', content: line.slice(1) || '' });
			}
		}

		return lines;
	});
</script>

<div class="version-diff {className}">
	<!-- Stats header -->
	<div class="flex items-center gap-4 px-3 py-2 bg-[var(--glass-tint)] rounded-t-lg border-b border-[var(--glass-border-subtle)]">
		<span class="text-sm font-medium text-[var(--color-text-secondary)]">
			{#if fromLabel && toLabel}
				{fromLabel} → {toLabel}
			{:else}
				{diff.from_version} → {diff.to_version}
			{/if}
		</span>
		<div class="flex items-center gap-3 ml-auto text-sm">
			<span class="text-green-500 font-mono">+{diff.additions}</span>
			<span class="text-red-500 font-mono">-{diff.deletions}</span>
		</div>
	</div>

	<!-- Diff content -->
	<div class="diff-content overflow-x-auto bg-[var(--color-bg-secondary)] rounded-b-lg border border-t-0 border-[var(--glass-border-subtle)]">
		<pre class="p-3 text-sm font-mono leading-relaxed">{#each parsedLines as line}<span
			class="diff-line block"
			class:diff-addition={line.type === 'addition'}
			class:diff-deletion={line.type === 'deletion'}
			class:diff-header={line.type === 'header'}
			class:diff-context={line.type === 'context'}
		>{#if line.type === 'addition'}+{:else if line.type === 'deletion'}-{:else if line.type === 'header'}@{:else}{' '}{/if}{line.content}</span>{/each}</pre>
	</div>
</div>

<style>
	.diff-line {
		white-space: pre-wrap;
		word-break: break-all;
	}

	.diff-addition {
		background-color: rgba(34, 197, 94, 0.15);
		color: rgb(34, 197, 94);
	}

	.diff-deletion {
		background-color: rgba(239, 68, 68, 0.15);
		color: rgb(239, 68, 68);
	}

	.diff-header {
		color: var(--color-accent);
		font-weight: 500;
		padding-top: 0.5rem;
		padding-bottom: 0.25rem;
	}

	.diff-context {
		color: var(--color-text-secondary);
	}

	/* Dark mode adjustments */
	@media (prefers-color-scheme: dark) {
		.diff-addition {
			background-color: rgba(34, 197, 94, 0.2);
		}

		.diff-deletion {
			background-color: rgba(239, 68, 68, 0.2);
		}
	}
</style>
