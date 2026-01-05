/**
 * Markdown rendering configuration with wikilinks support
 */
import { marked, type TokenizerExtension, type RendererExtension, type Tokens } from 'marked';

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
		return `<a href="/notes/${noteId}" class="wikilink">${wikilinkToken.text}</a>`;
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
 * @param content - Raw markdown string
 * @returns HTML string
 */
export function renderMarkdown(content: string): string {
	if (!content) return '';
	return marked.parse(content) as string;
}

/**
 * Render markdown content asynchronously
 * Useful for large documents
 * @param content - Raw markdown string
 * @returns Promise resolving to HTML string
 */
export async function renderMarkdownAsync(content: string): Promise<string> {
	if (!content) return '';
	return marked.parse(content);
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
