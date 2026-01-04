<script lang="ts">
	import { haptic, type HapticStyle } from '$lib/utils/haptics';
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
		size?: 'sm' | 'md' | 'lg';
		disabled?: boolean;
		loading?: boolean;
		hapticStyle?: HapticStyle;
		onclick?: (e: MouseEvent) => void;
		class?: string;
		type?: 'button' | 'submit' | 'reset';
		children?: Snippet;
	}

	let {
		variant = 'primary',
		size = 'md',
		disabled = false,
		loading = false,
		hapticStyle = 'light',
		onclick,
		class: className = '',
		type = 'button',
		children,
		...restProps
	}: Props = $props();

	const baseClasses =
		'inline-flex items-center justify-center font-medium rounded-xl transition-all touch-target touch-active';

	const variantClasses = {
		primary: 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]',
		secondary:
			'bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]',
		ghost: 'bg-transparent text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]',
		danger: 'bg-[var(--color-error)] text-white hover:opacity-90'
	};

	const sizeClasses = {
		sm: 'px-3 py-1.5 text-sm min-h-[36px]',
		md: 'px-4 py-2 text-base min-h-[44px]',
		lg: 'px-6 py-3 text-lg min-h-[52px]'
	};

	function handleClick(e: MouseEvent) {
		if (!disabled && !loading) {
			haptic(hapticStyle);
			onclick?.(e);
		}
	}
</script>

<button
	{type}
	class="{baseClasses} {variantClasses[variant]} {sizeClasses[size]} {className}"
	disabled={disabled || loading}
	aria-busy={loading ? 'true' : undefined}
	onclick={handleClick}
	{...restProps}
>
	{#if loading}
		<svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
			></circle>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			></path>
		</svg>
	{/if}
	{#if children}{@render children()}{/if}
</button>
