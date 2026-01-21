<script lang="ts">
	import { notificationCenterStore } from '$lib/stores/notification-center.svelte';
	import { haptic } from '$lib/utils/haptics';
	import { onMount } from 'svelte';
	import { Sheet } from '$lib/components/ui';
	import NotificationHeader from './NotificationHeader.svelte';
	import NotificationItem from './NotificationItem.svelte';

	let listRef: HTMLDivElement | null = $state(null);

	onMount(() => {
		notificationCenterStore.initialize();
	});

	function handleClose() {
		notificationCenterStore.close();
		haptic('light');
	}
	function handleRefresh() {
		notificationCenterStore.refresh();
		haptic('light');
	}
	function handleMarkAllRead() {
		notificationCenterStore.markAllAsRead();
		haptic('medium');
	}

	function handleScroll(e: Event) {
		const { scrollTop, scrollHeight, clientHeight } = e.target as HTMLDivElement;
		if (scrollHeight - scrollTop - clientHeight < 100) notificationCenterStore.loadMore();
	}
</script>

<Sheet bind:open={notificationCenterStore.isOpen} onclose={handleClose} width="w-full sm:w-96">
	{#snippet header()}
		<NotificationHeader onclose={handleClose} onrefresh={handleRefresh} />
		{#if notificationCenterStore.hasUnread}
			<div class="px-4 py-2 border-b border-[var(--glass-border-subtle)] bg-[var(--glass-tint)]">
				<button
					onclick={handleMarkAllRead}
					class="text-xs text-[var(--color-accent)] hover:underline font-medium"
				>
					Tout marquer comme lu
				</button>
			</div>
		{/if}
	{/snippet}

	<div bind:this={listRef} class="h-full flex flex-col" onscroll={handleScroll} role="list">
		{#if notificationCenterStore.loading && notificationCenterStore.notifications.length === 0}
			<div class="p-4 space-y-4">
				{#each Array(5) as _}
					<div class="h-20 bg-[var(--glass-tint)] rounded-2xl animate-pulse"></div>
				{/each}
			</div>
		{:else if notificationCenterStore.isEmpty}
			<div class="flex-1 flex flex-col items-center justify-center p-8 text-center opacity-30">
				<span class="text-5xl mb-6">🔕</span>
				<h3 class="text-lg font-bold">Aucune notification</h3>
				<p class="text-sm">Vous êtes à jour !</p>
			</div>
		{:else}
			<ul class="divide-y divide-[var(--glass-border-subtle)]">
				{#each notificationCenterStore.notifications as notification (notification.id)}
					<NotificationItem
						{notification}
						onmarkread={(id) => notificationCenterStore.markAsRead(id)}
						onremove={(id) => notificationCenterStore.remove(id)}
					/>
				{/each}
			</ul>
		{/if}
	</div>

	{#snippet footer()}
		{#if notificationCenterStore.stats}
			<div
				class="flex justify-between items-center text-[10px] text-[var(--color-text-tertiary)] uppercase tracking-widest font-mono"
			>
				<span>{notificationCenterStore.stats.total} TOTAL</span>
				<span>{notificationCenterStore.stats.unread} NON LUES</span>
			</div>
		{/if}
	{/snippet}
</Sheet>

<!-- Trigger button -->
<button
	onclick={() => {
		notificationCenterStore.toggle();
		haptic('light');
	}}
	class="fixed top-3 right-3 sm:right-[300px] z-50 p-2.5 rounded-xl glass-prominent hover:glass transition-all shadow-lg overflow-visible group"
	aria-label="Notifications"
>
	<span class="text-lg group-hover:scale-110 transition-transform inline-block">🔔</span>
	{#if notificationCenterStore.hasUnread}
		<span
			class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[var(--color-accent)] text-white text-[10px] font-bold flex items-center justify-center shadow-md animate-in zoom-in"
		>
			{notificationCenterStore.unreadCount > 9 ? '9+' : notificationCenterStore.unreadCount}
		</span>
	{/if}
</button>
