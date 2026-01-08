<script lang="ts">
	import {
		getContextualShortcuts,
		formatShortcut,
		hideHelp,
		type KeyboardShortcut
	} from '$lib/utils/keyboard-shortcuts';
	import { haptic } from '$lib/utils/haptics';

	interface Props {
		visible: boolean;
	}

	let { visible }: Props = $props();

	const shortcuts = $derived(visible ? getContextualShortcuts() : []);

	// Group shortcuts by category (based on ID prefix)
	const groupedShortcuts = $derived(() => {
		const groups: Record<string, KeyboardShortcut[]> = {
			navigation: [],
			actions: [],
			global: []
		};

		for (const s of shortcuts) {
			if (s.id.startsWith('nav-')) {
				groups.navigation.push(s);
			} else if (s.id.startsWith('action-')) {
				groups.actions.push(s);
			} else {
				groups.global.push(s);
			}
		}

		return groups;
	});

	function handleClose() {
		hideHelp();
		haptic('light');
	}

	function handleBackdropClick() {
		handleClose();
	}

	function handleBackdropKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleClose();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			handleClose();
		}
	}
</script>

{#if visible}
	<!-- Backdrop -->
	<div
		role="button"
		tabindex="-1"
		aria-label="Fermer"
		class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
		onclick={handleBackdropClick}
		onkeydown={handleBackdropKeydown}
	></div>

	<!-- Modal -->
	<div
		role="dialog"
		aria-modal="true"
		aria-labelledby="shortcuts-title"
		tabindex="-1"
		class="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[101]
			w-full max-w-lg max-h-[80vh] overflow-y-auto
			glass-prominent rounded-2xl shadow-2xl p-6"
		onkeydown={handleKeydown}
	>
		<!-- Header -->
		<div class="flex items-center justify-between mb-6">
			<h2 id="shortcuts-title" class="text-lg font-semibold text-[var(--color-text-primary)]">
				Raccourcis clavier
			</h2>
			<button
				onclick={handleClose}
				class="p-2 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
				aria-label="Fermer"
			>
				✕
			</button>
		</div>

		<!-- Shortcuts List -->
		<div class="space-y-6">
			{#if groupedShortcuts().navigation.length > 0}
				<div>
					<h3 class="text-sm font-medium text-[var(--color-text-secondary)] mb-3">Navigation</h3>
					<div class="space-y-2">
						{#each groupedShortcuts().navigation as shortcut (shortcut.id)}
							<div class="flex items-center justify-between py-1">
								<span class="text-sm text-[var(--color-text-primary)]">{shortcut.description}</span>
								<kbd class="px-2 py-1 text-xs font-mono rounded glass-subtle text-[var(--color-text-secondary)]">
									{formatShortcut(shortcut)}
								</kbd>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if groupedShortcuts().actions.length > 0}
				<div>
					<h3 class="text-sm font-medium text-[var(--color-text-secondary)] mb-3">Actions</h3>
					<div class="space-y-2">
						{#each groupedShortcuts().actions as shortcut (shortcut.id)}
							<div class="flex items-center justify-between py-1">
								<span class="text-sm text-[var(--color-text-primary)]">{shortcut.description}</span>
								<kbd class="px-2 py-1 text-xs font-mono rounded glass-subtle text-[var(--color-text-secondary)]">
									{formatShortcut(shortcut)}
								</kbd>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if groupedShortcuts().global.length > 0}
				<div>
					<h3 class="text-sm font-medium text-[var(--color-text-secondary)] mb-3">Global</h3>
					<div class="space-y-2">
						{#each groupedShortcuts().global as shortcut (shortcut.id)}
							<div class="flex items-center justify-between py-1">
								<span class="text-sm text-[var(--color-text-primary)]">{shortcut.description}</span>
								<kbd class="px-2 py-1 text-xs font-mono rounded glass-subtle text-[var(--color-text-secondary)]">
									{formatShortcut(shortcut)}
								</kbd>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Always show Cmd+K -->
			<div>
				<h3 class="text-sm font-medium text-[var(--color-text-secondary)] mb-3">Recherche</h3>
				<div class="flex items-center justify-between py-1">
					<span class="text-sm text-[var(--color-text-primary)]">Recherche globale</span>
					<kbd class="px-2 py-1 text-xs font-mono rounded glass-subtle text-[var(--color-text-secondary)]">
						⌘K
					</kbd>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div class="mt-6 pt-4 border-t border-[var(--glass-border-subtle)] text-center">
			<p class="text-xs text-[var(--color-text-tertiary)]">
				Appuyez sur <kbd class="px-1.5 py-0.5 text-xs rounded glass-subtle">?</kbd> pour afficher ce panneau
			</p>
		</div>
	</div>
{/if}
