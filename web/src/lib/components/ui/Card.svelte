<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'default' | 'glass' | 'glass-subtle' | 'glass-prominent' | 'elevated';
		padding?: 'none' | 'sm' | 'md' | 'lg';
		interactive?: boolean;
		specular?: boolean;
		class?: string;
		onclick?: () => void;
		children?: Snippet;
		[key: string]: unknown;
	}

	let {
		variant = 'default',
		padding = 'md',
		interactive = false,
		specular = false,
		class: className = '',
		onclick,
		children,
		...restProps
	}: Props = $props();

	const baseClasses = 'rounded-2xl overflow-hidden';

	const variantClasses = {
		default: 'bg-[var(--color-bg-secondary)] border border-[var(--color-border-light)]',
		glass: 'glass',
		'glass-subtle': 'glass-subtle',
		'glass-prominent': 'glass-prominent',
		elevated: 'bg-[var(--color-bg-primary)] shadow-[var(--shadow-md)] glass-glow'
	};

	const paddingClasses = {
		none: '',
		sm: 'p-2.5',
		md: 'p-3',
		lg: 'p-4'
	};

	// Liquid Glass interactive styles
	const interactiveClasses = $derived(
		interactive
			? 'glass-interactive liquid-press cursor-pointer'
			: 'animate-fluid'
	);

	// Specular highlight effect
	const specularClass = $derived(specular ? 'glass-specular' : '');
</script>

{#if onclick}
	<button
		type="button"
		class="{baseClasses} {variantClasses[variant]} {paddingClasses[padding]} {interactiveClasses} {specularClass} {className} w-full text-left"
		{onclick}
		{...restProps}
	>
		{#if children}{@render children()}{/if}
	</button>
{:else}
	<div
		class="{baseClasses} {variantClasses[variant]} {paddingClasses[padding]} {interactiveClasses} {specularClass} {className}"
		{...restProps}
	>
		{#if children}{@render children()}{/if}
	</div>
{/if}
