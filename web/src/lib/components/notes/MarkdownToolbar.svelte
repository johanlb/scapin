<script lang="ts">
	/**
	 * MarkdownToolbar Component
	 * Formatting buttons and mode toggle for the markdown editor
	 */

	type EditorMode = 'edit' | 'preview' | 'split';
	type FormatType = 'bold' | 'italic' | 'code' | 'heading' | 'list' | 'link' | 'wikilink';
	type SaveStatus = 'idle' | 'saving' | 'saved' | 'error' | 'unsaved';

	interface Props {
		mode: EditorMode;
		onFormat: (type: FormatType) => void;
		onModeChange: (mode: EditorMode) => void;
		onSave?: () => void;
		saveStatus?: SaveStatus;
		disabled?: boolean;
	}

	let { mode, onFormat, onModeChange, onSave, saveStatus = 'idle', disabled = false }: Props = $props();

	// Format buttons configuration
	const formatButtons: Array<{ type: FormatType; icon: string; label: string; shortcut: string }> = [
		{ type: 'bold', icon: 'B', label: 'Gras', shortcut: 'Cmd+B' },
		{ type: 'italic', icon: 'I', label: 'Italique', shortcut: 'Cmd+I' },
		{ type: 'code', icon: '</>', label: 'Code', shortcut: 'Cmd+E' },
		{ type: 'heading', icon: 'H', label: 'Titre', shortcut: 'Cmd+H' },
		{ type: 'list', icon: '•', label: 'Liste', shortcut: '' },
		{ type: 'link', icon: '🔗', label: 'Lien', shortcut: 'Cmd+K' },
		{ type: 'wikilink', icon: '📝', label: 'Wikilink', shortcut: 'Cmd+W' }
	];

	// Mode buttons configuration
	const modeButtons: Array<{ mode: EditorMode; label: string }> = [
		{ mode: 'edit', label: 'Écrire' },
		{ mode: 'preview', label: 'Aperçu' },
		{ mode: 'split', label: 'Split' }
	];
</script>

<div class="toolbar flex items-center gap-1 p-2 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
	<!-- Format buttons -->
	<div class="format-buttons flex items-center gap-0.5">
		{#each formatButtons as button}
			<button
				type="button"
				onclick={() => onFormat(button.type)}
				{disabled}
				title="{button.label}{button.shortcut ? ` (${button.shortcut})` : ''}"
				class="format-btn px-2 py-1.5 rounded text-sm font-medium
					text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
					hover:bg-[var(--color-bg-tertiary)]
					disabled:opacity-50 disabled:cursor-not-allowed
					transition-colors"
				class:font-bold={button.type === 'bold'}
				class:italic={button.type === 'italic'}
				class:font-mono={button.type === 'code'}
			>
				{button.icon}
			</button>
		{/each}
	</div>

	<!-- Separator -->
	<div class="separator w-px h-5 bg-[var(--color-border)] mx-2 hidden sm:block"></div>

	<!-- Save button -->
	{#if onSave}
		<button
			type="button"
			onclick={onSave}
			disabled={disabled || saveStatus === 'saving' || saveStatus === 'saved'}
			title="Enregistrer (Cmd+S)"
			class="save-btn px-3 py-1.5 rounded text-sm font-medium flex items-center gap-1.5
				transition-colors
				{saveStatus === 'unsaved'
				? 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]'
				: saveStatus === 'saving'
					? 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'
					: saveStatus === 'saved'
						? 'bg-green-500/20 text-green-600 dark:text-green-400'
						: saveStatus === 'error'
							? 'bg-red-500/20 text-red-600 dark:text-red-400'
							: 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}"
		>
			{#if saveStatus === 'saving'}
				<span class="animate-spin">⟳</span>
				Enregistrement...
			{:else if saveStatus === 'saved'}
				<span>✓</span>
				Enregistré
			{:else if saveStatus === 'error'}
				<span>✗</span>
				Erreur
			{:else if saveStatus === 'unsaved'}
				<span>💾</span>
				Enregistrer
			{:else}
				<span>💾</span>
				Enregistrer
			{/if}
		</button>
	{/if}

	<!-- Mode toggle -->
	<div class="mode-toggle flex items-center gap-0.5 ml-auto">
		{#each modeButtons as button}
			<button
				type="button"
				onclick={() => onModeChange(button.mode)}
				class="mode-btn px-3 py-1.5 rounded text-sm
					transition-colors
					{mode === button.mode
					? 'bg-[var(--color-accent)] text-white'
					: 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-tertiary)]'}"
			>
				{button.label}
			</button>
		{/each}
	</div>
</div>

<style>
	.toolbar {
		flex-wrap: wrap;
		gap: 0.25rem;
	}

	@media (max-width: 480px) {
		.format-buttons {
			flex-wrap: wrap;
		}

		.mode-toggle {
			width: 100%;
			justify-content: center;
			margin-top: 0.5rem;
		}
	}

	.format-btn:active {
		transform: scale(0.95);
	}

	.mode-btn {
		min-width: 4rem;
		text-align: center;
	}
</style>
