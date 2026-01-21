<script lang="ts">
	import { notificationCenterStore } from '$lib/stores/notification-center.svelte';

	interface Props {
		onclose: () => void;
		onrefresh: () => void;
	}

	let { onclose, onrefresh }: Props = $props();
</script>

<div class="px-4 py-3 border-b border-[var(--glass-border-subtle)] flex items-center gap-3">
	<span class="text-lg">🔔</span>
	<h2 class="flex-1 font-semibold text-[var(--color-text-primary)]">Notifications</h2>

	{#if notificationCenterStore.hasUnread}
		<span
			class="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)]"
		>
			{notificationCenterStore.unreadCount}
		</span>
	{/if}

	<button
		onclick={onrefresh}
		class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
		title="Actualiser"
		disabled={notificationCenterStore.loading}
	>
		<span class={notificationCenterStore.loading ? 'animate-spin' : ''}>🔄</span>
	</button>

	<button
		onclick={onclose}
		class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
		aria-label="Fermer"
	>
		✕
	</button>
</div>
