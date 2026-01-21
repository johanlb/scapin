// Global UI state using Svelte 5 runes
export const uiState = $state({
	showCommandPalette: false
});

export function openCommandPalette() {
	uiState.showCommandPalette = true;
}

export function closeCommandPalette() {
	uiState.showCommandPalette = false;
}
