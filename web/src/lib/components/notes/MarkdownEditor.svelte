<script lang="ts">
	import MarkdownToolbar from './MarkdownToolbar.svelte';
	import MarkdownPreview from './MarkdownPreview.svelte';
	import EditorTextarea from './EditorTextarea.svelte';

	/**
	 * MarkdownEditor Component
	 * Full-featured markdown editor with toolbar, preview, and auto-save
	 */

	type EditorMode = 'edit' | 'preview' | 'split';
	type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

	interface Props {
		content: string;
		onSave?: (content: string) => Promise<void> | void;
		autosaveDelay?: number;
		placeholder?: string;
		class?: string;
	}

	let {
		content = $bindable(),
		onSave,
		autosaveDelay = 1000,
		placeholder = 'Commencez \u00e0 \u00e9crire...',
		class: className = ''
	}: Props = $props();

	let mode = $state<EditorMode>('edit');
	let editorRef = $state<EditorTextarea | null>(null);
	let saveStatus = $state<SaveStatus>('idle');
	let saveTimeout: ReturnType<typeof setTimeout>;
	let lastSavedContent = $state(content);
	let isSaving = $state(false);

	// Auto-save with debounce
	$effect(() => {
		if (onSave && content !== lastSavedContent && !isSaving) {
			clearTimeout(saveTimeout);
			saveStatus = 'idle';

			// Capture content at this moment to avoid race conditions
			const contentToSave = content;

			saveTimeout = setTimeout(async () => {
				// Check if content is still the same (user didn't type more)
				if (content !== contentToSave) return;

				try {
					isSaving = true;
					saveStatus = 'saving';
					await onSave(contentToSave);
					lastSavedContent = contentToSave;
					saveStatus = 'saved';

					// Reset status after 2 seconds
					setTimeout(() => {
						if (saveStatus === 'saved') {
							saveStatus = 'idle';
						}
					}, 2000);
				} catch {
					saveStatus = 'error';
				} finally {
					isSaving = false;
				}
			}, autosaveDelay);
		}

		return () => clearTimeout(saveTimeout);
	});

	// Handle format actions
	function handleFormat(type: string): void {
		if (!editorRef) return;

		switch (type) {
			case 'bold':
				editorRef.wrapSelection('**', '**');
				break;
			case 'italic':
				editorRef.wrapSelection('*', '*');
				break;
			case 'code':
				editorRef.wrapSelection('`', '`');
				break;
			case 'heading':
				editorRef.insertText('## ');
				break;
			case 'list':
				editorRef.insertText('- ');
				break;
			case 'link':
				editorRef.wrapSelection('[', '](url)');
				break;
			case 'wikilink':
				editorRef.wrapSelection('[[', ']]');
				break;
		}
	}

	// Keyboard shortcuts
	function handleKeydown(e: KeyboardEvent): void {
		if (e.metaKey || e.ctrlKey) {
			switch (e.key.toLowerCase()) {
				case 'b':
					e.preventDefault();
					handleFormat('bold');
					break;
				case 'i':
					e.preventDefault();
					handleFormat('italic');
					break;
				case 'e':
					e.preventDefault();
					handleFormat('code');
					break;
				case 'k':
					e.preventDefault();
					handleFormat('link');
					break;
				case 'w':
					e.preventDefault();
					handleFormat('wikilink');
					break;
				case 's':
					e.preventDefault();
					// Trigger immediate save
					if (onSave && content !== lastSavedContent && !isSaving) {
						clearTimeout(saveTimeout);
						const contentToSave = content;
						isSaving = true;
						saveStatus = 'saving';
						Promise.resolve(onSave(contentToSave))
							.then(() => {
								lastSavedContent = contentToSave;
								saveStatus = 'saved';
							})
							.catch(() => {
								saveStatus = 'error';
							})
							.finally(() => {
								isSaving = false;
							});
					}
					break;
			}
		}
	}

	// Get save status text
	function getSaveStatusText(): string {
		switch (saveStatus) {
			case 'saving':
				return 'Enregistrement...';
			case 'saved':
				return 'Enregistré';
			case 'error':
				return 'Erreur';
			default:
				return '';
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="editor-container rounded-lg border border-[var(--color-border)] overflow-hidden {className}"
	onkeydown={handleKeydown}
>
	<MarkdownToolbar
		{mode}
		onFormat={handleFormat}
		onModeChange={(m) => (mode = m)}
		disabled={mode === 'preview'}
	/>

	<div class="editor-content bg-[var(--color-bg-primary)]" class:split={mode === 'split'}>
		{#if mode !== 'preview'}
			<div class="editor-pane" class:half={mode === 'split'}>
				<EditorTextarea bind:this={editorRef} bind:content {placeholder} />
			</div>
		{/if}

		{#if mode !== 'edit'}
			<div
				class="preview-pane p-4 overflow-auto"
				class:half={mode === 'split'}
				class:border-l={mode === 'split'}
			>
				<MarkdownPreview {content} />
			</div>
		{/if}
	</div>

	<!-- Status bar -->
	<div
		class="status-bar flex items-center justify-between px-3 py-1.5 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] text-xs text-[var(--color-text-tertiary)]"
	>
		<span>
			{#if content}
				{content.length} caractères
			{:else}
				Aucun contenu
			{/if}
		</span>

		{#if saveStatus !== 'idle'}
			<span
				class="save-status flex items-center gap-1"
				class:text-[var(--color-accent)]={saveStatus === 'saving'}
				class:text-green-500={saveStatus === 'saved'}
				class:text-red-500={saveStatus === 'error'}
			>
				{#if saveStatus === 'saving'}
					<span class="animate-spin">⟳</span>
				{:else if saveStatus === 'saved'}
					<span>✓</span>
				{:else if saveStatus === 'error'}
					<span>✗</span>
				{/if}
				{getSaveStatusText()}
			</span>
		{/if}
	</div>
</div>

<style>
	.editor-container {
		display: flex;
		flex-direction: column;
		min-height: 400px;
	}

	.editor-content {
		flex: 1;
		display: flex;
		min-height: 300px;
	}

	.editor-content.split {
		flex-direction: row;
	}

	.editor-pane,
	.preview-pane {
		flex: 1;
		overflow: auto;
	}

	.editor-pane.half,
	.preview-pane.half {
		width: 50%;
	}

	.preview-pane.border-l {
		border-left: 1px solid var(--color-border);
	}

	/* Mobile: stack vertically in split mode */
	@media (max-width: 768px) {
		.editor-content.split {
			flex-direction: column;
		}

		.editor-pane.half,
		.preview-pane.half {
			width: 100%;
			height: 50%;
		}

		.preview-pane.border-l {
			border-left: none;
			border-top: 1px solid var(--color-border);
		}
	}

	.status-bar {
		font-size: 0.75rem;
	}

	.save-status {
		transition: color 0.2s ease;
	}
</style>
