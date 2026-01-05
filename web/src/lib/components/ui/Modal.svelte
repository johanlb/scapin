<script lang="ts">
	/**
	 * Modal Component
	 * Confirmation dialogs, forms, and general-purpose modals
	 * Uses Liquid Glass design with spring animations
	 */
	import { haptic } from '$lib/utils/haptics';
	import type { Snippet } from 'svelte';

	interface Props {
		open: boolean;
		title?: string;
		size?: 'sm' | 'md' | 'lg' | 'full';
		closable?: boolean;
		closeOnBackdrop?: boolean;
		closeOnEscape?: boolean;
		onclose?: () => void;
		children?: Snippet;
		footer?: Snippet;
	}

	let {
		open = $bindable(false),
		title,
		size = 'md',
		closable = true,
		closeOnBackdrop = true,
		closeOnEscape = true,
		onclose,
		children,
		footer
	}: Props = $props();

	let modalRef = $state<HTMLDivElement | null>(null);

	const sizeClasses = {
		sm: 'max-w-sm',
		md: 'max-w-md',
		lg: 'max-w-2xl',
		full: 'max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]'
	};

	function handleClose() {
		if (closable) {
			haptic('light');
			open = false;
			onclose?.();
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if (closeOnBackdrop && e.target === e.currentTarget) {
			handleClose();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (closeOnEscape && e.key === 'Escape') {
			e.preventDefault();
			handleClose();
		}
	}

	// Focus trap and scroll lock
	$effect(() => {
		if (open) {
			// Prevent body scroll
			document.body.style.overflow = 'hidden';
			// Focus the modal
			modalRef?.focus();
		} else {
			document.body.style.overflow = '';
		}

		return () => {
			document.body.style.overflow = '';
		};
	});
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		role="dialog"
		aria-modal="true"
		aria-labelledby={title ? 'modal-title' : undefined}
		tabindex="-1"
		onkeydown={handleKeydown}
	>
		<!-- Backdrop -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
			onclick={handleBackdropClick}
			role="button"
			tabindex="-1"
			aria-label="Fermer le modal"
		></div>

		<!-- Modal -->
		<div
			bind:this={modalRef}
			class="relative w-full {sizeClasses[size]} glass-prominent rounded-2xl shadow-lg animate-modal-in overflow-hidden"
			tabindex="-1"
		>
			<!-- Header -->
			{#if title || closable}
				<div class="flex items-center justify-between px-5 py-4 border-b border-[var(--glass-border-subtle)]">
					{#if title}
						<h2 id="modal-title" class="text-lg font-semibold text-[var(--color-text-primary)]">
							{title}
						</h2>
					{:else}
						<div></div>
					{/if}

					{#if closable}
						<button
							type="button"
							class="p-2 -m-2 rounded-full text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--glass-subtle)] transition-colors touch-target"
							onclick={handleClose}
							aria-label="Fermer"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					{/if}
				</div>
			{/if}

			<!-- Content -->
			<div class="px-5 py-4 overflow-y-auto max-h-[60vh]">
				{#if children}{@render children()}{/if}
			</div>

			<!-- Footer -->
			{#if footer}
				<div class="flex items-center justify-end gap-3 px-5 py-4 border-t border-[var(--glass-border-subtle)] bg-[var(--glass-tint)]">
					{@render footer()}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes modal-in {
		from {
			opacity: 0;
			transform: scale(0.95) translateY(10px);
		}
		to {
			opacity: 1;
			transform: scale(1) translateY(0);
		}
	}

	.animate-fade-in {
		animation: fade-in var(--transition-fast) var(--spring-responsive);
	}

	.animate-modal-in {
		animation: modal-in var(--transition-normal) var(--spring-bouncy);
	}
</style>
