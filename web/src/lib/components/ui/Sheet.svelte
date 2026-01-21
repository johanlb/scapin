<script lang="ts">
	/**
	 * Sheet Component
	 * Side-sliding panels (slide from right, or bottom on mobile)
	 * Uses Liquid Glass design system
	 */
	import { haptic } from '$lib/utils/haptics';
	import type { Snippet } from 'svelte';
	import { onDestroy } from 'svelte';

	interface Props {
		open: boolean;
		onclose: () => void;
		title?: string;
		children?: Snippet;
		header?: Snippet;
		footer?: Snippet;
		width?: string; // Default width Tailwind classes
		side?: 'right' | 'left' | 'bottom';
	}

	let {
		open = $bindable(false),
		onclose,
		title,
		children,
		header,
		footer,
		width = 'w-full sm:w-[400px]',
		side = 'right'
	}: Props = $props();

	function handleClose() {
		haptic('light');
		open = false;
		onclose?.();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && open) {
			handleClose();
		}
	}

	// Body scroll lock
	$effect(() => {
		if (open) {
			document.body.style.overflow = 'hidden';
		} else {
			document.body.style.overflow = '';
		}
		return () => {
			document.body.style.overflow = '';
		};
	});

	const sideClasses = {
		right: 'right-0 top-0 h-full animate-slide-in-right',
		left: 'left-0 top-0 h-full animate-slide-in-left',
		bottom: 'bottom-0 left-0 w-full h-[80vh] rounded-t-[2rem] animate-slide-in-bottom'
	};
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="fixed inset-0 z-[100] flex items-end sm:items-stretch"
		role="dialog"
		aria-modal="true"
	>
		<!-- Backdrop -->
		<div
			class="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
			onclick={handleClose}
			role="button"
			tabindex="-1"
			aria-label="Fermer le panneau"
		></div>

		<!-- Panel Content -->
		<div
			class="relative flex flex-col glass-prominent shadow-2xl overflow-hidden {width} {sideClasses[
				side
			]}"
		>
			<!-- Simple Header if title provided and no header snippet -->
			{#if header}
				{@render header()}
			{:else if title}
				<div
					class="flex items-center justify-between px-5 py-4 border-b border-[var(--glass-border-subtle)]"
				>
					<h2
						class="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60"
					>
						{title}
					</h2>
					<button
						onclick={handleClose}
						class="p-2 rounded-full hover:bg-white/10 transition-colors text-white/50 hover:text-white"
						aria-label="Fermer"
					>
						✕
					</button>
				</div>
			{/if}

			<!-- Inner Content -->
			<div class="flex-1 overflow-y-auto custom-scrollbar">
				{#if children}{@render children()}{/if}
			</div>

			<!-- Footer -->
			{#if footer}
				<div class="p-5 border-t border-[var(--glass-border-subtle)] bg-[var(--glass-tint)]">
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

	@keyframes slide-in-right {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	@keyframes slide-in-bottom {
		from {
			transform: translateY(100%);
		}
		to {
			transform: translateY(0);
		}
	}

	.animate-fade-in {
		animation: fade-in 0.3s ease-out;
	}

	.animate-slide-in-right {
		animation: slide-in-right 0.4s var(--spring-responsive);
	}

	.animate-slide-in-bottom {
		animation: slide-in-bottom 0.4s var(--spring-responsive);
	}

	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}

	.custom-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}

	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--glass-border-subtle);
		border-radius: 10px;
	}

	.custom-scrollbar::-webkit-scrollbar-thumb:hover {
		background: var(--color-accent);
	}
</style>
