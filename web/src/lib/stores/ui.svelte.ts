// Global UI state using Svelte 5 runes

interface UiState {
	showCommandPalette: boolean;
}

let state = $state<UiState>({
	showCommandPalette: false
});

export const uiState = {
	get showCommandPalette() {
		return state.showCommandPalette;
	},
	set showCommandPalette(value: boolean) {
		state.showCommandPalette = value;
	}
};

export function openCommandPalette() {
	state.showCommandPalette = true;
}

export function closeCommandPalette() {
	state.showCommandPalette = false;
}
