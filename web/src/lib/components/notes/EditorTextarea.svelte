<script lang="ts" module>
	/**
	 * EditorTextarea Component
	 * Enhanced textarea with text manipulation methods for markdown editing
	 */

	export interface EditorTextareaAPI {
		insertText: (text: string) => void;
		wrapSelection: (before: string, after: string) => void;
		focus: () => void;
		getSelection: () => { start: number; end: number; text: string };
	}
</script>

<script lang="ts">
	interface Props {
		content: string;
		placeholder?: string;
		class?: string;
	}

	let { content = $bindable(), placeholder = 'Commencez \u00e0 \u00e9crire...', class: className = '' }: Props = $props();
	let textarea: HTMLTextAreaElement;

	/**
	 * Insert text at current cursor position
	 */
	export function insertText(text: string): void {
		if (!textarea) return;

		const start = textarea.selectionStart;
		const end = textarea.selectionEnd;

		content = content.slice(0, start) + text + content.slice(end);

		// Restore cursor position after the inserted text
		requestAnimationFrame(() => {
			textarea.selectionStart = textarea.selectionEnd = start + text.length;
			textarea.focus();
		});
	}

	/**
	 * Wrap current selection with before/after strings
	 */
	export function wrapSelection(before: string, after: string): void {
		if (!textarea) return;

		const start = textarea.selectionStart;
		const end = textarea.selectionEnd;
		const selected = content.slice(start, end);

		content = content.slice(0, start) + before + selected + after + content.slice(end);

		// Maintain selection of the wrapped text
		requestAnimationFrame(() => {
			textarea.selectionStart = start + before.length;
			textarea.selectionEnd = end + before.length;
			textarea.focus();
		});
	}

	/**
	 * Focus the textarea
	 */
	export function focus(): void {
		textarea?.focus();
	}

	/**
	 * Get current selection info
	 */
	export function getSelection(): { start: number; end: number; text: string } {
		if (!textarea) return { start: 0, end: 0, text: '' };
		return {
			start: textarea.selectionStart,
			end: textarea.selectionEnd,
			text: content.slice(textarea.selectionStart, textarea.selectionEnd)
		};
	}

	// Auto-resize textarea as content grows
	function handleInput(): void {
		if (textarea) {
			textarea.style.height = 'auto';
			textarea.style.height = `${textarea.scrollHeight}px`;
		}
	}

	// Set initial height on mount
	$effect(() => {
		if (textarea && content) {
			requestAnimationFrame(() => {
				textarea.style.height = 'auto';
				textarea.style.height = `${textarea.scrollHeight}px`;
			});
		}
	});
</script>

<textarea
	bind:this={textarea}
	bind:value={content}
	{placeholder}
	oninput={handleInput}
	class="editor-textarea w-full min-h-[300px] p-4 bg-transparent resize-none focus:outline-none {className}"
	spellcheck="true"
></textarea>

<style>
	.editor-textarea {
		font-family: 'SF Mono', 'Menlo', 'Monaco', monospace;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--color-text-primary);
		caret-color: var(--color-accent);
	}

	.editor-textarea::placeholder {
		color: var(--color-text-tertiary);
	}

	/* Scrollbar styling */
	.editor-textarea::-webkit-scrollbar {
		width: 8px;
	}

	.editor-textarea::-webkit-scrollbar-track {
		background: transparent;
	}

	.editor-textarea::-webkit-scrollbar-thumb {
		background: var(--color-border);
		border-radius: 4px;
	}

	.editor-textarea::-webkit-scrollbar-thumb:hover {
		background: var(--color-text-tertiary);
	}
</style>
