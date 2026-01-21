<script lang="ts">
	interface Suggestion {
		label: string;
		query: string;
		icon: string;
	}

	interface Props {
		suggestions: Suggestion[];
		onsuggestion: (query: string) => void;
	}

	let { suggestions, onsuggestion }: Props = $props();
</script>

<div class="space-y-1.5">
	<p class="text-xs text-[var(--color-text-tertiary)] mb-2">Suggestions :</p>
	{#each suggestions as suggestion}
		<button
			type="button"
			onclick={() => onsuggestion(suggestion.query)}
			class="w-full text-left px-3 py-2 rounded-xl
				glass-subtle hover:glass
				transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
				text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
				flex items-center gap-2 liquid-press"
		>
			<span>{suggestion.icon}</span>
			<span>{suggestion.label}</span>
		</button>
	{/each}
</div>
