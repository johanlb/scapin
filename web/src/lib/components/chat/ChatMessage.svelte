<script lang="ts">
	interface Props {
		role: 'user' | 'assistant';
		content: string;
		timestamp: string;
	}

	let { role, content, timestamp }: Props = $props();

	function formatTime(ts: string): string {
		return new Date(ts).toLocaleTimeString('fr-FR', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<div class="flex {role === 'user' ? 'justify-end' : 'justify-start'}">
	<div
		class="max-w-[85%] rounded-2xl px-3 py-2 {role === 'user'
			? 'bg-[var(--color-accent)] text-white'
			: 'glass-subtle text-[var(--color-text-primary)]'}"
	>
		<p class="text-sm whitespace-pre-wrap">{content}</p>
		<p
			class="text-xs mt-1 {role === 'user' ? 'text-white/70' : 'text-[var(--color-text-tertiary)]'}"
		>
			{formatTime(timestamp)}
		</p>
	</div>
</div>
