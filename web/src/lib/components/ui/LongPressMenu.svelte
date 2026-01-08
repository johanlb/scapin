<script lang="ts">
	import type { Snippet } from 'svelte';
	import { haptic } from '$lib/utils/haptics';

	export interface MenuItem {
		id: string;
		label: string;
		icon?: string;
		variant?: 'default' | 'danger' | 'warning';
		disabled?: boolean;
		handler: () => void | Promise<void>;
	}

	interface Props {
		items: MenuItem[];
		longPressDuration?: number;
		children?: Snippet;
	}

	let { items, longPressDuration = 500, children }: Props = $props();

	let isOpen = $state(false);
	let pressTimer: ReturnType<typeof setTimeout> | null = $state(null);
	let menuPosition = $state({ x: 0, y: 0 });
	let containerRef: HTMLDivElement | null = $state(null);

	function handleTouchStart(e: TouchEvent) {
		const touch = e.touches[0];
		menuPosition = { x: touch.clientX, y: touch.clientY };

		pressTimer = setTimeout(() => {
			haptic('medium');
			isOpen = true;
		}, longPressDuration);
	}

	function handleTouchMove() {
		// Cancel long press if user moves finger
		if (pressTimer) {
			clearTimeout(pressTimer);
			pressTimer = null;
		}
	}

	function handleTouchEnd() {
		if (pressTimer) {
			clearTimeout(pressTimer);
			pressTimer = null;
		}
	}

	function handleContextMenu(e: MouseEvent) {
		// Also support right-click on desktop
		e.preventDefault();
		menuPosition = { x: e.clientX, y: e.clientY };
		haptic('light');
		isOpen = true;
	}

	async function handleItemClick(item: MenuItem) {
		if (item.disabled) return;
		haptic('light');
		isOpen = false;
		await item.handler();
	}

	function closeMenu() {
		isOpen = false;
	}

	function getVariantClasses(variant: MenuItem['variant']): string {
		switch (variant) {
			case 'danger':
				return 'text-red-400 hover:bg-red-500/20';
			case 'warning':
				return 'text-orange-400 hover:bg-orange-500/20';
			default:
				return 'text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]';
		}
	}

	// Adjust menu position to stay within viewport
	const adjustedPosition = $derived(() => {
		if (typeof window === 'undefined') return menuPosition;

		const menuWidth = 200;
		const menuHeight = items.length * 44 + 16; // Approximate height
		const padding = 16;

		let x = menuPosition.x;
		let y = menuPosition.y;

		// Adjust horizontal position
		if (x + menuWidth > window.innerWidth - padding) {
			x = window.innerWidth - menuWidth - padding;
		}
		if (x < padding) {
			x = padding;
		}

		// Adjust vertical position
		if (y + menuHeight > window.innerHeight - padding) {
			y = y - menuHeight; // Show above touch point
		}
		if (y < padding) {
			y = padding;
		}

		return { x, y };
	});
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && closeMenu()} />

<div
	bind:this={containerRef}
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
	oncontextmenu={handleContextMenu}
	role="group"
	aria-label="Conteneur avec menu contextuel"
>
	{#if children}{@render children()}{/if}
</div>

{#if isOpen}
	<!-- Backdrop -->
	<button
		type="button"
		class="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
		onclick={closeMenu}
		aria-label="Fermer le menu"
	></button>

	<!-- Menu -->
	<div
		class="fixed z-50 min-w-[200px] py-2 rounded-xl glass-prominent shadow-xl border border-[var(--glass-border-subtle)] animate-in fade-in zoom-in-95 duration-150"
		style="left: {adjustedPosition().x}px; top: {adjustedPosition().y}px;"
		role="menu"
	>
		{#each items as item (item.id)}
			<button
				type="button"
				role="menuitem"
				class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed {getVariantClasses(item.variant)}"
				disabled={item.disabled}
				onclick={() => handleItemClick(item)}
			>
				{#if item.icon}
					<span class="text-lg w-6 text-center shrink-0">{item.icon}</span>
				{/if}
				<span class="flex-1 text-left">{item.label}</span>
			</button>
		{/each}
	</div>
{/if}

<style>
	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes zoom-in-95 {
		from { transform: scale(0.95); }
		to { transform: scale(1); }
	}

	.animate-in {
		animation: fade-in 150ms ease-out, zoom-in-95 150ms ease-out;
	}
</style>
