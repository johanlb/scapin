/**
 * Markdown rendering configuration with wikilinks support
 */
import { marked, type TokenizerExtension, type RendererExtension, type Tokens } from 'marked';
import DOMPurify from 'isomorphic-dompurify';

/**
 * Escape HTML special characters to prevent XSS
 */
function escapeHtml(text: string): string {
	return text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}

// Custom token type for wikilinks
interface WikilinkToken extends Tokens.Generic {
	type: 'wikilink';
	raw: string;
	text: string;
}

// Extension for wikilinks [[Note Title]]
const wikilinkExtension: TokenizerExtension & RendererExtension = {
	name: 'wikilink',
	level: 'inline',

	start(src: string): number | undefined {
		const index = src.indexOf('[[');
		return index !== -1 ? index : undefined;
	},

	tokenizer(src: string): WikilinkToken | undefined {
		const match = /^\[\[([^\]]+)\]\]/.exec(src);
		if (match) {
			return {
				type: 'wikilink',
				raw: match[0],
				text: match[1]
			};
		}
		return undefined;
	},

	renderer(token: Tokens.Generic): string {
		const wikilinkToken = token as WikilinkToken;
		const noteId = encodeURIComponent(wikilinkToken.text);
		// Escape HTML to prevent XSS attacks via wikilink text
		const safeText = escapeHtml(wikilinkToken.text);
		return `<a href="/notes/${noteId}" class="wikilink">${safeText}</a>`;
	}
};

// Configure marked with extensions
marked.use({
	extensions: [wikilinkExtension],
	gfm: true,
	breaks: true
});

/**
 * Render markdown content to HTML
 * Sanitizes output with DOMPurify to prevent XSS attacks
 * @param content - Raw markdown string
 * @returns Sanitized HTML string
 */
export function renderMarkdown(content: string): string {
	if (!content) return '';
	const rawHtml = marked.parse(content) as string;
	// Sanitize HTML output to prevent XSS attacks
	return DOMPurify.sanitize(rawHtml, {
		ADD_ATTR: ['class', 'href', 'target'],
		ADD_TAGS: ['a']
	});
}

/**
 * Render markdown content asynchronously
 * Useful for large documents. Sanitizes output with DOMPurify.
 * @param content - Raw markdown string
 * @returns Promise resolving to sanitized HTML string
 */
export async function renderMarkdownAsync(content: string): Promise<string> {
	if (!content) return '';
	const rawHtml = await marked.parse(content);
	// Sanitize HTML output to prevent XSS attacks
	return DOMPurify.sanitize(rawHtml, {
		ADD_ATTR: ['class', 'href', 'target'],
		ADD_TAGS: ['a']
	});
}

/**
 * Extract wikilinks from markdown content
 * @param content - Raw markdown string
 * @returns Array of wikilink targets
 */
export function extractWikilinks(content: string): string[] {
	const wikilinks: string[] = [];
	const regex = /\[\[([^\]]+)\]\]/g;
	let match;
	while ((match = regex.exec(content)) !== null) {
		wikilinks.push(match[1]);
	}
	return wikilinks;
}
