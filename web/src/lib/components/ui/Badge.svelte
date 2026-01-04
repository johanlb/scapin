<script lang="ts">
	import type { EventSource, UrgencyLevel } from '$lib/types';
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'default' | 'source' | 'urgency';
		source?: EventSource;
		urgency?: UrgencyLevel;
		class?: string;
		children?: Snippet;
	}

	let { variant = 'default', source, urgency, class: className = '', children }: Props = $props();

	const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium backdrop-blur-sm';

	const sourceColors: Record<EventSource, string> = {
		email: 'bg-[var(--color-event-email)]/10 text-[var(--color-event-email)]',
		teams: 'bg-[var(--color-event-teams)]/10 text-[var(--color-event-teams)]',
		calendar: 'bg-[var(--color-event-calendar)]/10 text-[var(--color-event-calendar)]',
		omnifocus: 'bg-[var(--color-event-omnifocus)]/10 text-[var(--color-event-omnifocus)]'
	};

	const sourceLabels: Record<EventSource, string> = {
		email: 'Email',
		teams: 'Teams',
		calendar: 'Calendrier',
		omnifocus: 'OmniFocus'
	};

	const urgencyColors: Record<UrgencyLevel, string> = {
		urgent: 'bg-[var(--color-error)]/10 text-[var(--color-error)]',
		high: 'bg-[var(--color-warning)]/10 text-[var(--color-warning)]',
		medium: 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]',
		low: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
	};

	const urgencyLabels: Record<UrgencyLevel, string> = {
		urgent: 'Pressant',
		high: 'Important',
		medium: 'Courant',
		low: 'À loisir'
	};

	const classes = $derived.by(() => {
		if (variant === 'source' && source) {
			return `${baseClasses} ${sourceColors[source]} ${className}`;
		}
		if (variant === 'urgency' && urgency) {
			return `${baseClasses} ${urgencyColors[urgency]} ${className}`;
		}
		return `${baseClasses} bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] ${className}`;
	});

	const label = $derived.by(() => {
		if (variant === 'source' && source) {
			return sourceLabels[source];
		}
		if (variant === 'urgency' && urgency) {
			return urgencyLabels[urgency];
		}
		return '';
	});
</script>

<span class={classes}>
	{#if variant === 'default'}
		{#if children}{@render children()}{/if}
	{:else}
		{label}
	{/if}
</span>
