/**
 * Keyboard Shortcuts Manager
 * Centralized handling of keyboard shortcuts across the application
 */
import { browser } from '$app/environment';
import { haptic } from './haptics';

export interface KeyboardShortcut {
	/** Unique identifier for the shortcut */
	id: string;
	/** Key to trigger (lowercase) */
	key: string;
	/** Description of the action */
	description: string;
	/** Handler function */
	handler: () => void | Promise<void>;
	/** Require ctrl/cmd key */
	ctrl?: boolean;
	/** Require shift key */
	shift?: boolean;
	/** Require alt/option key */
	alt?: boolean;
	/** Context where this shortcut is active (page path prefix) */
	context?: string;
	/** Whether this shortcut is global (works even when inputs are focused) */
	global?: boolean;
}

interface ShortcutsState {
	shortcuts: Map<string, KeyboardShortcut>;
	enabled: boolean;
	helpVisible: boolean;
}

const state: ShortcutsState = {
	shortcuts: new Map(),
	enabled: true,
	helpVisible: false
};

/**
 * Check if an element is an input-like element
 */
function isInputElement(element: Element | null): boolean {
	if (!element) return false;
	const tagName = element.tagName.toLowerCase();
	return (
		tagName === 'input' ||
		tagName === 'textarea' ||
		tagName === 'select' ||
		element.getAttribute('contenteditable') === 'true'
	);
}

/**
 * Generate a unique key for a shortcut based on its modifiers
 */
function getShortcutKey(shortcut: Pick<KeyboardShortcut, 'key' | 'ctrl' | 'shift' | 'alt'>): string {
	const parts = [];
	if (shortcut.ctrl) parts.push('ctrl');
	if (shortcut.shift) parts.push('shift');
	if (shortcut.alt) parts.push('alt');
	parts.push(shortcut.key.toLowerCase());
	return parts.join('+');
}

/**
 * Check if the current event matches a shortcut
 */
function matchesShortcut(event: KeyboardEvent, shortcut: KeyboardShortcut): boolean {
	const ctrlOrMeta = event.ctrlKey || event.metaKey;

	return (
		event.key.toLowerCase() === shortcut.key.toLowerCase() &&
		(shortcut.ctrl ? ctrlOrMeta : !ctrlOrMeta) &&
		(shortcut.shift ? event.shiftKey : !event.shiftKey) &&
		(shortcut.alt ? event.altKey : !event.altKey)
	);
}

/**
 * Handle keydown events
 */
function handleKeydown(event: KeyboardEvent): void {
	if (!state.enabled) return;

	// Check if we're in an input field (unless the shortcut is global)
	const isInput = isInputElement(document.activeElement);

	// Check current path for context filtering
	const currentPath = window.location.pathname;

	for (const shortcut of state.shortcuts.values()) {
		// Skip non-global shortcuts when in input
		if (isInput && !shortcut.global) continue;

		// Check context if specified
		if (shortcut.context && !currentPath.startsWith(shortcut.context)) continue;

		// Check if event matches
		if (matchesShortcut(event, shortcut)) {
			event.preventDefault();
			event.stopPropagation();
			haptic('light');

			// Execute handler
			const result = shortcut.handler();
			if (result instanceof Promise) {
				result.catch((err) => {
					console.error(`[Shortcuts] Error in handler for ${shortcut.id}:`, err);
				});
			}
			return;
		}
	}
}

/**
 * Register a keyboard shortcut
 */
export function registerShortcut(shortcut: KeyboardShortcut): () => void {
	const key = getShortcutKey(shortcut);
	state.shortcuts.set(key, shortcut);

	// Return unregister function
	return () => {
		state.shortcuts.delete(key);
	};
}

/**
 * Register multiple shortcuts at once
 */
export function registerShortcuts(shortcuts: KeyboardShortcut[]): () => void {
	const unregisterFns = shortcuts.map((s) => registerShortcut(s));

	return () => {
		unregisterFns.forEach((fn) => fn());
	};
}

/**
 * Unregister a shortcut by its ID
 */
export function unregisterShortcut(id: string): void {
	for (const [key, shortcut] of state.shortcuts.entries()) {
		if (shortcut.id === id) {
			state.shortcuts.delete(key);
			break;
		}
	}
}

/**
 * Enable/disable shortcuts
 */
export function setShortcutsEnabled(enabled: boolean): void {
	state.enabled = enabled;
}

/**
 * Get all registered shortcuts
 */
export function getShortcuts(): KeyboardShortcut[] {
	return Array.from(state.shortcuts.values());
}

/**
 * Get shortcuts for current context
 */
export function getContextualShortcuts(): KeyboardShortcut[] {
	const currentPath = window.location.pathname;
	return getShortcuts().filter((s) => !s.context || currentPath.startsWith(s.context));
}

/**
 * Show/hide help overlay
 */
export function toggleHelp(): void {
	state.helpVisible = !state.helpVisible;
}

export function isHelpVisible(): boolean {
	return state.helpVisible;
}

export function hideHelp(): void {
	state.helpVisible = false;
}

/**
 * Format a shortcut for display
 */
export function formatShortcut(shortcut: Pick<KeyboardShortcut, 'key' | 'ctrl' | 'shift' | 'alt'>): string {
	const parts = [];
	const isMac = browser && navigator.platform.includes('Mac');

	if (shortcut.ctrl) parts.push(isMac ? '⌘' : 'Ctrl');
	if (shortcut.shift) parts.push(isMac ? '⇧' : 'Shift');
	if (shortcut.alt) parts.push(isMac ? '⌥' : 'Alt');
	parts.push(shortcut.key.toUpperCase());

	return parts.join(isMac ? '' : '+');
}

/**
 * Initialize the keyboard shortcuts system
 */
export function initializeShortcuts(): () => void {
	if (!browser) return () => {};

	// Add event listener
	window.addEventListener('keydown', handleKeydown, { capture: true });

	// Register global shortcuts
	const unregisterHelp = registerShortcut({
		id: 'show-help',
		key: '?',
		shift: true,
		description: "Afficher l'aide des raccourcis",
		handler: toggleHelp,
		global: true
	});

	// Return cleanup function
	return () => {
		window.removeEventListener('keydown', handleKeydown, { capture: true });
		unregisterHelp();
		state.shortcuts.clear();
	};
}

/**
 * Common navigation shortcuts for lists
 */
export function createNavigationShortcuts(
	onPrevious: () => void,
	onNext: () => void,
	context?: string
): KeyboardShortcut[] {
	return [
		{
			id: 'nav-previous',
			key: 'k',
			description: 'Élément précédent',
			handler: onPrevious,
			context
		},
		{
			id: 'nav-next',
			key: 'j',
			description: 'Élément suivant',
			handler: onNext,
			context
		}
	];
}

/**
 * Common action shortcuts for queue items
 */
export function createQueueActionShortcuts(
	onApprove: () => void,
	onReject: () => void,
	onSnooze: () => void,
	onExpand: () => void,
	context?: string
): KeyboardShortcut[] {
	return [
		{
			id: 'action-approve',
			key: 'a',
			description: 'Approuver',
			handler: onApprove,
			context
		},
		{
			id: 'action-reject',
			key: 'r',
			description: 'Rejeter',
			handler: onReject,
			context
		},
		{
			id: 'action-snooze',
			key: 's',
			description: 'Reporter',
			handler: onSnooze,
			context
		},
		{
			id: 'action-expand',
			key: 'e',
			description: 'Développer / Modifier',
			handler: onExpand,
			context
		}
	];
}
