<script lang="ts">
	import type { Attachment } from '$lib/api/client';

	interface Props {
		attachment: Attachment;
		emailId?: string;
	}

	let { attachment, emailId }: Props = $props();

	// Format file size for display
	function formatSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
	}

	// Get file extension
	function getExtension(filename: string): string {
		const parts = filename.split('.');
		return parts.length > 1 ? parts.pop()?.toLowerCase() ?? '' : '';
	}

	// Determine file type category
	function getFileCategory(contentType: string, filename: string): 'image' | 'audio' | 'video' | 'pdf' | 'document' | 'archive' | 'other' {
		const ext = getExtension(filename);

		if (contentType.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
			return 'image';
		}
		if (contentType.startsWith('audio/') || ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'].includes(ext)) {
			return 'audio';
		}
		if (contentType.startsWith('video/') || ['mp4', 'webm', 'mov', 'avi', 'mkv'].includes(ext)) {
			return 'video';
		}
		if (contentType === 'application/pdf' || ext === 'pdf') {
			return 'pdf';
		}
		if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'txt', 'rtf', 'csv'].includes(ext)) {
			return 'document';
		}
		if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
			return 'archive';
		}
		return 'other';
	}

	// Get icon for file type
	function getFileIcon(category: 'image' | 'audio' | 'video' | 'pdf' | 'document' | 'archive' | 'other'): string {
		const icons = {
			image: '\u{1f5bc}',    // frame with picture
			audio: '\u{1f3b5}',    // musical note
			video: '\u{1f3ac}',    // clapper board
			pdf: '\u{1f4c4}',      // page facing up
			document: '\u{1f4c3}', // page with curl
			archive: '\u{1f4e6}',  // package
			other: '\u{1f4ce}'     // paperclip
		};
		return icons[category];
	}

	const category = $derived(getFileCategory(attachment.content_type, attachment.filename));
	const icon = $derived(getFileIcon(category));
	const extension = $derived(getExtension(attachment.filename).toUpperCase());
	const size = $derived(formatSize(attachment.size_bytes));
</script>

<div class="attachment">
	<div class="attachment-icon" data-category={category}>
		<span class="icon">{icon}</span>
		{#if extension}
			<span class="extension">{extension}</span>
		{/if}
	</div>

	<div class="attachment-info">
		<span class="filename" title={attachment.filename}>
			{attachment.filename}
		</span>
		<span class="meta">
			{size}
			{#if attachment.content_type !== 'application/octet-stream'}
				<span class="separator">-</span>
				<span class="type">{attachment.content_type}</span>
			{/if}
		</span>
	</div>
</div>

<style>
	.attachment {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		background: var(--color-bg-tertiary);
		border-radius: 0.5rem;
		border: 1px solid var(--color-border);
		transition: background-color 0.15s ease;
	}

	.attachment:hover {
		background: var(--color-bg-secondary);
	}

	.attachment-icon {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		background: var(--color-bg-secondary);
		border-radius: 0.375rem;
		flex-shrink: 0;
	}

	.attachment-icon .icon {
		font-size: 1.25rem;
	}

	.attachment-icon .extension {
		position: absolute;
		bottom: -0.25rem;
		right: -0.25rem;
		font-size: 0.5rem;
		font-weight: 600;
		padding: 0.125rem 0.25rem;
		background: var(--color-accent);
		color: white;
		border-radius: 0.25rem;
		text-transform: uppercase;
	}

	.attachment-icon[data-category="image"] {
		background: rgba(59, 130, 246, 0.1);
	}

	.attachment-icon[data-category="audio"] {
		background: rgba(168, 85, 247, 0.1);
	}

	.attachment-icon[data-category="video"] {
		background: rgba(236, 72, 153, 0.1);
	}

	.attachment-icon[data-category="pdf"] {
		background: rgba(239, 68, 68, 0.1);
	}

	.attachment-icon[data-category="document"] {
		background: rgba(34, 197, 94, 0.1);
	}

	.attachment-icon[data-category="archive"] {
		background: rgba(234, 179, 8, 0.1);
	}

	.attachment-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.filename {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.meta {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.separator {
		opacity: 0.5;
	}

	.type {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 150px;
	}
</style>
