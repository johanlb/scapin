<script lang="ts">
	/**
	 * MarkdownPreview Component
	 * Renders markdown content as HTML with wikilinks support
	 */
	import { renderMarkdown } from '$lib/utils/markdown';

	interface Props {
		content: string;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	const html = $derived(renderMarkdown(content));
</script>

<div class="markdown-preview prose dark:prose-invert max-w-none {className}">
	{@html html}
</div>

<style>
	.markdown-preview {
		/* Typography */
		font-size: 1rem;
		line-height: 1.75;
	}

	/* Wikilinks styling */
	.markdown-preview :global(.wikilink) {
		color: var(--color-accent);
		text-decoration: none;
		border-bottom: 1px dashed var(--color-accent);
		transition: border-color 0.2s ease;
	}

	.markdown-preview :global(.wikilink:hover) {
		border-bottom-style: solid;
	}

	/* Code blocks */
	.markdown-preview :global(pre) {
		background: var(--color-bg-secondary);
		border-radius: 0.5rem;
		padding: 1rem;
		overflow-x: auto;
	}

	.markdown-preview :global(code) {
		font-family: 'SF Mono', 'Menlo', 'Monaco', monospace;
		font-size: 0.875em;
	}

	.markdown-preview :global(:not(pre) > code) {
		background: var(--color-bg-secondary);
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
	}

	/* Blockquotes */
	.markdown-preview :global(blockquote) {
		border-left: 3px solid var(--color-accent);
		margin-left: 0;
		padding-left: 1rem;
		color: var(--color-text-secondary);
		font-style: italic;
	}

	/* Links */
	.markdown-preview :global(a:not(.wikilink)) {
		color: var(--color-accent);
		text-decoration: underline;
	}

	/* Lists */
	.markdown-preview :global(ul),
	.markdown-preview :global(ol) {
		padding-left: 1.5rem;
	}

	.markdown-preview :global(li) {
		margin-bottom: 0.25rem;
	}

	/* Headings */
	.markdown-preview :global(h1),
	.markdown-preview :global(h2),
	.markdown-preview :global(h3),
	.markdown-preview :global(h4) {
		color: var(--color-text-primary);
		margin-top: 1.5rem;
		margin-bottom: 0.75rem;
		font-weight: 600;
	}

	.markdown-preview :global(h1) {
		font-size: 1.75rem;
	}

	.markdown-preview :global(h2) {
		font-size: 1.5rem;
	}

	.markdown-preview :global(h3) {
		font-size: 1.25rem;
	}

	/* Tables */
	.markdown-preview :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin: 1rem 0;
	}

	.markdown-preview :global(th),
	.markdown-preview :global(td) {
		border: 1px solid var(--color-border);
		padding: 0.5rem;
		text-align: left;
	}

	.markdown-preview :global(th) {
		background: var(--color-bg-secondary);
		font-weight: 600;
	}

	/* Horizontal rule */
	.markdown-preview :global(hr) {
		border: none;
		border-top: 1px solid var(--color-border);
		margin: 2rem 0;
	}

	/* Images */
	.markdown-preview :global(img) {
		max-width: 100%;
		border-radius: 0.5rem;
	}

	/* Apple Notes media images */
	.markdown-preview :global(img.apple-media-image) {
		max-width: 100%;
		height: auto;
		border-radius: 0.5rem;
		margin: 1rem 0;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	/* Audio elements */
	.markdown-preview :global(audio) {
		width: 100%;
		margin: 1rem 0;
	}

	/* Video elements */
	.markdown-preview :global(video) {
		max-width: 100%;
		border-radius: 0.5rem;
		margin: 1rem 0;
	}

	/* PDF iframes */
	.markdown-preview :global(iframe) {
		width: 100%;
		min-height: 400px;
		border: 1px solid var(--color-border);
		border-radius: 0.5rem;
		margin: 1rem 0;
	}
</style>
