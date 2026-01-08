<script lang="ts">
	/**
	 * Toast Component
	 * Individual toast notification with icon, message, and dismiss button
	 */
	import { haptic } from '$lib/utils/haptics';
	import type { ToastType } from '$lib/stores/toast.svelte';

	interface Props {
		id: string;
		type: ToastType;
		message: string;
		title?: string;
		dismissible?: boolean;
		ondismiss?: (id: string) => void;
	}

	let { id, type, message, title, dismissible = true, ondismiss }: Props = $props();

	const typeConfig: Record<ToastType, { bg: string; border: string; icon: string; iconPath: string }> = {
		success: {
			bg: 'bg-[var(--color-success)]/10',
			border: 'border-[var(--color-success)]/30',
			icon: 'text-[var(--color-success)]',
			iconPath: 'M5 13l4 4L19 7'
		},
		error: {
			bg: 'bg-[var(--color-error)]/10',
			border: 'border-[var(--color-error)]/30',
			icon: 'text-[var(--color-error)]',
			iconPath: 'M6 18L18 6M6 6l12 12'
		},
		warning: {
			bg: 'bg-[var(--color-warning)]/10',
			border: 'border-[var(--color-warning)]/30',
			icon: 'text-[var(--color-warning)]',
			iconPath: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'
		},
		info: {
			bg: 'bg-[var(--color-accent)]/10',
			border: 'border-[var(--color-accent)]/30',
			icon: 'text-[var(--color-accent)]',
			iconPath: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
		},
		undo: {
			bg: 'bg-[var(--color-accent)]/10',
			border: 'border-[var(--color-accent)]/30',
			icon: 'text-[var(--color-accent)]',
			iconPath: 'M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6'
		}
	};

	const config = $derived(typeConfig[type]);

	function handleDismiss() {
		haptic('light');
		ondismiss?.(id);
	}
</script>

<div
	class="flex items-start gap-3 p-4 rounded-2xl glass-prominent {config.bg} border {config.border} shadow-lg animate-toast-in"
	role="alert"
	aria-live="polite"
>
	<!-- Icon -->
	<div class="flex-shrink-0 {config.icon}">
		<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
			<path stroke-linecap="round" stroke-linejoin="round" d={config.iconPath} />
		</svg>
	</div>

	<!-- Content -->
	<div class="flex-1 min-w-0">
		{#if title}
			<p class="font-medium text-[var(--color-text-primary)]">{title}</p>
		{/if}
		<p class="text-sm text-[var(--color-text-secondary)] {title ? 'mt-0.5' : ''}">{message}</p>
	</div>

	<!-- Dismiss button -->
	{#if dismissible}
		<button
			type="button"
			class="flex-shrink-0 p-1.5 -m-1.5 rounded-full text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--glass-subtle)] transition-colors"
			onclick={handleDismiss}
			aria-label="Fermer"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	{/if}
</div>

<style>
	@keyframes toast-in {
		from {
			opacity: 0;
			transform: translateY(-20px) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.animate-toast-in {
		animation: toast-in var(--transition-normal) var(--spring-bouncy);
	}
</style>
