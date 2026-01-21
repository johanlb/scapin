<script lang="ts">
	import { noteChatStore } from '$lib/stores/note-chat.svelte';

	interface Props {
		isNoteChatMode: boolean;
		onclose: () => void;
		onSaveAsDiscussion: () => void;
		onClearConversation: () => void;
	}

	let { isNoteChatMode, onclose, onSaveAsDiscussion, onClearConversation }: Props = $props();
	const noteContext = $derived(noteChatStore.noteContext);
</script>

<div class="px-3 py-2.5 border-b border-[var(--glass-border-subtle)] flex items-center gap-2">
	<span class="text-lg">🎭</span>
	<div class="flex-1 min-w-0">
		{#if isNoteChatMode && noteContext}
			<h2 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">
				{noteContext.title}
			</h2>
			<p class="text-xs text-[var(--color-text-tertiary)]">Discussion</p>
		{:else}
			<h2 class="text-sm font-semibold text-[var(--color-text-primary)]">Scapin</h2>
		{/if}
	</div>
	{#if isNoteChatMode}
		{#if noteChatStore.canSaveAsDiscussion}
			<button
				onclick={onSaveAsDiscussion}
				class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
				title="Sauvegarder"
				disabled={noteChatStore.saving}
			>
				<span class="text-sm">{noteChatStore.saving ? '⏳' : '💾'}</span>
			</button>
		{/if}
		{#if noteChatStore.hasMessages}
			<button
				onclick={onClearConversation}
				class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
				title="Effacer"
			>
				<span class="text-sm">🗑️</span>
			</button>
		{/if}
		<button
			onclick={() => noteChatStore.clearContext()}
			class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
			title="Fermer"
		>
			<span class="text-sm">✕</span>
		</button>
	{:else}
		<span class="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse" title="À l'écoute"
		></span>
	{/if}
</div>
