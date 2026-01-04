<script lang="ts">
	// Common autocomplete values - extend as needed
	type AutocompleteValue =
		| 'off'
		| 'on'
		| 'name'
		| 'email'
		| 'username'
		| 'new-password'
		| 'current-password'
		| 'tel'
		| 'url'
		| 'street-address'
		| 'postal-code'
		| 'country';

	interface Props {
		type?: 'text' | 'email' | 'password' | 'search' | 'url' | 'number' | 'tel';
		placeholder?: string;
		value?: string;
		disabled?: boolean;
		error?: string;
		class?: string;
		id?: string;
		name?: string;
		required?: boolean;
		autocomplete?: AutocompleteValue;
		oninput?: (e: Event) => void;
		onkeydown?: (e: KeyboardEvent) => void;
		inputRef?: HTMLInputElement | null;
	}

	let {
		type = 'text',
		placeholder = '',
		value = $bindable(''),
		disabled = false,
		error = '',
		class: className = '',
		id,
		name,
		required = false,
		autocomplete,
		oninput,
		onkeydown,
		inputRef = $bindable(null),
		...restProps
	}: Props = $props();

	// Generate a unique ID for accessibility if not provided
	// Use $derived to handle dynamic id prop changes
	const generatedId = `input-${Math.random().toString(36).slice(2, 9)}`;
	const inputId = $derived(id ?? generatedId);
	const errorId = $derived(`${inputId}-error`);

	const baseClasses = `
		w-full px-4 py-3 rounded-xl
		bg-[var(--color-bg-secondary)]
		border border-[var(--color-border-light)]
		text-[var(--color-text-primary)]
		placeholder:text-[var(--color-text-tertiary)]
		focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] focus:border-transparent
		transition-all duration-200
		touch-target
	`;

	const errorClasses = $derived(
		error ? 'border-[var(--color-error)] focus:ring-[var(--color-error)]' : ''
	);
	const disabledClasses = $derived(disabled ? 'opacity-50 cursor-not-allowed' : '');
</script>

<div class="w-full">
	<input
		{type}
		{placeholder}
		{disabled}
		{required}
		{autocomplete}
		id={inputId}
		{name}
		bind:value
		bind:this={inputRef}
		{oninput}
		{onkeydown}
		class="{baseClasses} {errorClasses} {disabledClasses} {className}"
		aria-invalid={error ? 'true' : undefined}
		aria-describedby={error ? errorId : undefined}
		{...restProps}
	/>
	{#if error}
		<p id={errorId} class="mt-1 text-sm text-[var(--color-error)]" role="alert">
			{error}
		</p>
	{/if}
</div>
