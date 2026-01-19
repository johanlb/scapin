/**
 * Quick Actions Store
 * Provides context-aware quick actions based on the current page and state
 */
import { page } from '$app/stores';
import { goto } from '$app/navigation';
import { openCommandPalette } from '$lib/stores';
import { get } from 'svelte/store';
import type { QuickAction } from '$lib/components/ui/QuickActionsMenu.svelte';

// Action generators for different contexts
type ActionGenerator = () => QuickAction[];

// Registry of page-specific actions
const pageActionsRegistry: Record<string, ActionGenerator> = {
	'/': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'process-peripeties',
			label: 'Traiter les péripéties',
			icon: '🎪',
			handler: () => goto('/peripeties')
		},
		{
			id: 'new-note',
			label: 'Nouvelle mémoire',
			icon: '📝',
			handler: () => goto('/memoires?action=new')
		},
		{
			id: 'start-discussion',
			label: 'Nouvelle discussion',
			icon: '💬',
			handler: () => goto('/discussions?action=new')
		}
	],

	'/peripeties': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'focus-mode',
			label: 'Mode Focus',
			icon: '🎯',
			variant: 'primary',
			handler: () => goto('/peripeties/focus')
		},
		{
			id: 'refresh',
			label: 'Actualiser',
			icon: '🔄',
			handler: () => window.location.reload()
		}
	],

	'/memoires': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'new-note',
			label: 'Nouvelle mémoire',
			icon: '📝',
			variant: 'primary',
			handler: () => goto('/memoires?action=new')
		},
		{
			id: 'review-notes',
			label: 'Réviser les mémoires',
			icon: '🧠',
			handler: () => goto('/memoires/review')
		},
		{
			id: 'sync-apple-notes',
			label: 'Sync Apple Notes',
			icon: '🍎',
			handler: async () => {
				const { syncAppleNotes } = await import('$lib/api');
				await syncAppleNotes();
			}
		}
	],

	'/discussions': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'new-discussion',
			label: 'Nouvelle discussion',
			icon: '💬',
			variant: 'primary',
			handler: () => goto('/discussions?action=new')
		}
	],

	'/confessions': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'today-confession',
			label: "Confession d'aujourd'hui",
			icon: '📖',
			variant: 'primary',
			handler: () => {
				const today = new Date().toISOString().split('T')[0];
				goto(`/confessions?date=${today}`);
			}
		}
	],

	'/valets': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'refresh-valets',
			label: 'Actualiser',
			icon: '🔄',
			handler: () => window.location.reload()
		}
	],

	'/settings': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		}
	],

	'/comptes': () => [
		{
			id: 'search',
			label: 'Rechercher',
			icon: '🔍',
			shortcut: '⌘K',
			handler: () => openCommandPalette()
		},
		{
			id: 'refresh-comptes',
			label: 'Actualiser',
			icon: '🔄',
			handler: () => window.location.reload()
		}
	]
};

// Default actions for unregistered pages
const defaultActions: ActionGenerator = () => [
	{
		id: 'search',
		label: 'Rechercher',
		icon: '🔍',
		shortcut: '⌘K',
		handler: () => openCommandPalette()
	},
	{
		id: 'home',
		label: 'Accueil',
		icon: '🏠',
		handler: () => goto('/')
	}
];

/**
 * Get quick actions for the current page
 */
export function getQuickActions(): QuickAction[] {
	const currentPage = get(page);
	const pathname = currentPage?.url?.pathname || '/';

	// Try exact match first
	if (pageActionsRegistry[pathname]) {
		return pageActionsRegistry[pathname]();
	}

	// Try prefix match for nested routes
	for (const [route, generator] of Object.entries(pageActionsRegistry)) {
		if (pathname.startsWith(route) && route !== '/') {
			return generator();
		}
	}

	// Fall back to default actions
	return defaultActions();
}

/**
 * Create a reactive quick actions state
 */
export function createQuickActionsStore() {
	let actions = $state<QuickAction[]>([]);

	// Update actions when page changes
	$effect(() => {
		const currentPage = get(page);
		if (currentPage) {
			actions = getQuickActions();
		}
	});

	return {
		get actions() {
			return actions;
		}
	};
}

// Singleton instance
let quickActionsInstance: ReturnType<typeof createQuickActionsStore> | null = null;

export function getQuickActionsStore() {
	if (!quickActionsInstance) {
		quickActionsInstance = createQuickActionsStore();
	}
	return quickActionsInstance;
}
