<script lang="ts">
	import { haptic } from '$lib/utils/haptics';

	export interface QuickAction {
		id: string;
		label: string;
		icon: string;
		shortcut?: string;
		variant?: 'default' | 'primary' | 'danger' | 'warning';
		disabled?: boolean;
		handler: () => void | Promise<void>;
	}

	interface Props {
		actions: QuickAction[];
		position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
		trigger?: 'click' | 'hover' | 'always';
		compact?: boolean;
	}

	let { actions, position = 'bottom-right', trigger = 'click', compact = false }: Props = $props();

	// Derive open state from trigger prop
	const isAlwaysOpen = $derived(trigger === 'always');
	let manualOpen = $state(false);
	const isOpen = $derived(isAlwaysOpen || manualOpen);
	let isExecuting = $state(false);

	function toggleMenu() {
		if (trigger === 'always') return;
		manualOpen = !manualOpen;
		if (manualOpen) {
			haptic('light');
		}
	}

	function handleMouseEnter() {
		if (trigger === 'hover') {
			manualOpen = true;
		}
	}

	function handleMouseLeave() {
		if (trigger === 'hover') {
			manualOpen = false;
		}
	}

	async function handleAction(action: QuickAction) {
		if (action.disabled || isExecuting) return;

		isExecuting = true;
		haptic('medium');

		try {
			await action.handler();
		} catch (e) {
			console.error('Quick action failed:', e);
		} finally {
			isExecuting = false;
			if (trigger !== 'always') {
				manualOpen = false;
			}
		}
	}

	function handleBackdropClick() {
		if (trigger === 'click') {
			manualOpen = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			manualOpen = false;
		}
	}

	function getVariantClasses(variant: QuickAction['variant']): string {
		switch (variant) {
			case 'primary':
				return 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent)]/90';
			case 'danger':
				return 'bg-red-500/20 text-red-400 hover:bg-red-500/30';
			case 'warning':
				return 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30';
			default:
				return 'bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]';
		}
	}

	const positionClasses = $derived({
		'bottom-right': 'bottom-4 right-4',
		'bottom-left': 'bottom-4 left-4',
		'top-right': 'top-4 right-4',
		'top-left': 'top-4 left-4'
	}[position]);

	const menuPositionClasses = $derived({
		'bottom-right': 'bottom-full right-0 mb-2',
		'bottom-left': 'bottom-full left-0 mb-2',
		'top-right': 'top-full right-0 mt-2',
		'top-left': 'top-full left-0 mt-2'
	}[position]);
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="fixed z-40 {positionClasses}"
	role="group"
	aria-label="Actions rapides"
	onmouseenter={handleMouseEnter}
	onmouseleave={handleMouseLeave}
>
	<!-- Backdrop when open (click trigger only) -->
	{#if isOpen && trigger === 'click'}
		<button
			type="button"
			class="fixed inset-0 z-30 bg-transparent"
			onclick={handleBackdropClick}
			aria-label="Fermer le menu"
		></button>
	{/if}

	<!-- Actions menu -->
	{#if isOpen}
		<div
			class="absolute z-50 {menuPositionClasses} min-w-[200px] py-2 rounded-xl glass-prominent shadow-xl border border-[var(--glass-border-subtle)]"
			role="menu"
		>
			{#each actions as action (action.id)}
				<button
					type="button"
					role="menuitem"
					class="w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed {getVariantClasses(action.variant)}"
					disabled={action.disabled || isExecuting}
					onclick={() => handleAction(action)}
				>
					<span class="text-lg w-6 text-center shrink-0">{action.icon}</span>
					<span class="flex-1 text-left">{action.label}</span>
					{#if action.shortcut}
						<kbd class="text-xs font-mono opacity-60 px-1.5 py-0.5 rounded bg-black/20">{action.shortcut}</kbd>
					{/if}
				</button>
			{/each}
		</div>
	{/if}

	<!-- Trigger button -->
	{#if trigger !== 'always'}
		<button
			type="button"
			class="w-14 h-14 rounded-full glass-prominent shadow-lg flex items-center justify-center transition-all hover:scale-105 active:scale-95 {compact ? 'w-12 h-12' : ''}"
			class:rotate-45={isOpen}
			onclick={toggleMenu}
			aria-expanded={isOpen}
			aria-haspopup="menu"
			aria-label="Actions rapides"
		>
			<span class="text-2xl transition-transform {isOpen ? 'rotate-45' : ''}">+</span>
		</button>
	{/if}
</div>
