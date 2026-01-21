<script lang="ts">
	import type { SearchResult } from '$lib/types';

	interface Props {
		result: SearchResult;
		active: boolean;
		onclick: () => void;
		onmouseenter: () => void;
	}

	let { result, active, onclick, onmouseenter }: Props = $props();

	function getTypeLabel(type: SearchResult['type']): string {
		const labels: Record<SearchResult['type'], string> = {
			note: 'Carnet',
			email: 'Email',
			event: 'Événement',
			task: 'Tâche',
			discussion: 'Conversation'
		};
		return labels[type];
	}

	function getTypeColor(type: SearchResult['type']): string {
		const colors: Record<SearchResult['type'], string> = {
			note: 'var(--color-event-omnifocus)',
			email: 'var(--color-event-email)',
			event: 'var(--color-event-calendar)',
			task: 'var(--color-event-omnifocus)',
			discussion: 'var(--color-event-teams)'
		};
		return colors[type];
	}
</script>

<button
	type="button"
	class="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left
		transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
		liquid-press
		{active
		? 'glass-subtle shadow-[inset_0_0_0_1px_var(--color-accent)]/20'
		: 'hover:bg-[var(--glass-tint)]'}"
	{onclick}
	{onmouseenter}
>
	<span class="text-xl">{result.icon}</span>
	<div class="flex-1 min-w-0">
		<p class="text-[var(--color-text-primary)] font-medium truncate">
			{result.title}
		</p>
		{#if result.subtitle}
			<p class="text-sm text-[var(--color-text-tertiary)] truncate">
				{result.subtitle}
			</p>
		{/if}
	</div>
	<span
		class="px-2 py-0.5 text-xs rounded-md"
		style="background-color: {getTypeColor(result.type)}20; color: {getTypeColor(result.type)}"
	>
		{getTypeLabel(result.type)}
	</span>
</button>
