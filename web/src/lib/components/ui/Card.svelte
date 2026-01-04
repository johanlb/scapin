<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'default' | 'glass' | 'elevated';
		padding?: 'none' | 'sm' | 'md' | 'lg';
		interactive?: boolean;
		class?: string;
		onclick?: () => void;
		children?: Snippet;
	}

	let {
		variant = 'default',
		padding = 'md',
		interactive = false,
		class: className = '',
		onclick,
		children,
		...restProps
	}: Props = $props();

	const baseClasses = 'rounded-xl overflow-hidden transition-all duration-200 ease-out';

	const variantClasses = {
		default: 'bg-[var(--color-bg-secondary)] border border-[var(--color-border-light)]',
		glass: 'glass',
		elevated: 'bg-[var(--color-bg-primary)] shadow-[var(--shadow-md)]'
	};

	const paddingClasses = {
		none: '',
		sm: 'p-2.5',
		md: 'p-3',
		lg: 'p-4'
	};

	// Use $derived to react to prop changes
	const interactiveClasses = $derived(
		interactive
			? 'cursor-pointer hover:bg-[var(--color-bg-tertiary)] hover:border-[var(--color-border)] hover:shadow-sm active:scale-[0.99] active:shadow-none'
			: ''
	);
</script>

{#if onclick}
	<button
		type="button"
		class="{baseClasses} {variantClasses[variant]} {paddingClasses[padding]} {interactiveClasses} {className} w-full text-left"
		{onclick}
		{...restProps}
	>
		{#if children}{@render children()}{/if}
	</button>
{:else}
	<div
		class="{baseClasses} {variantClasses[variant]} {paddingClasses[padding]} {interactiveClasses} {className}"
		{...restProps}
	>
		{#if children}{@render children()}{/if}
	</div>
{/if}
