import { writable } from 'svelte/store';

// Global UI state store
export const showCommandPalette = writable(false);

export function openCommandPalette() {
	showCommandPalette.set(true);
}

export function closeCommandPalette() {
	showCommandPalette.set(false);
}
