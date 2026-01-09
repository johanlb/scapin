<script lang="ts">
	import { notificationCenterStore } from '$lib/stores/notification-center.svelte';
	import { haptic } from '$lib/utils/haptics';
	import { onMount } from 'svelte';

	let panelRef: HTMLDivElement | null = $state(null);
	let listRef: HTMLDivElement | null = $state(null);

	onMount(() => {
		// Initialize on mount
		notificationCenterStore.initialize();
	});

	function handleClose() {
		notificationCenterStore.close();
		haptic('light');
	}

	function handleMarkAllRead() {
		notificationCenterStore.markAllAsRead();
		haptic('medium');
	}

	function handleMarkAsRead(notificationId: string) {
		notificationCenterStore.markAsRead(notificationId);
		haptic('light');
	}

	function handleDelete(notificationId: string) {
		notificationCenterStore.remove(notificationId);
		haptic('medium');
	}

	function handleRefresh() {
		notificationCenterStore.refresh();
		haptic('light');
	}

	function handleScroll(e: Event) {
		const target = e.target as HTMLDivElement;
		const { scrollTop, scrollHeight, clientHeight } = target;

		// Load more when 100px from bottom
		if (scrollHeight - scrollTop - clientHeight < 100) {
			notificationCenterStore.loadMore();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			handleClose();
		}
	}

	function handleBackdropClick() {
		handleClose();
	}

	function handleBackdropKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleClose();
		}
	}
</script>

<!-- Desktop Panel (slide from right) -->
{#if notificationCenterStore.isOpen}
	<!-- Backdrop (desktop) -->
	<div
		role="button"
		tabindex="-1"
		aria-label="Fermer les notifications"
		class="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 hidden lg:block"
		onclick={handleBackdropClick}
		onkeydown={handleBackdropKeydown}
	></div>

	<!-- Panel -->
	<div
		bind:this={panelRef}
		role="dialog"
		aria-modal="true"
		aria-labelledby="notifications-title"
		tabindex="-1"
		class="fixed right-0 top-0 h-full w-80 glass-prominent flex flex-col z-50 shadow-2xl
			animate-in slide-in-from-right duration-300 ease-out"
		onkeydown={handleKeydown}
		data-testid="notifications-panel"
	>
		<!-- Header -->
		<div class="px-4 py-3 border-b border-[var(--glass-border-subtle)] flex items-center gap-3">
			<span class="text-lg">🔔</span>
			<h2 id="notifications-title" class="flex-1 font-semibold text-[var(--color-text-primary)]">
				Notifications
			</h2>

			{#if notificationCenterStore.hasUnread}
				<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)]">
					{notificationCenterStore.unreadCount}
				</span>
			{/if}

			<button
				onclick={handleRefresh}
				class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
				title="Actualiser"
				disabled={notificationCenterStore.loading}
			>
				<span class={notificationCenterStore.loading ? 'animate-spin' : ''}>🔄</span>
			</button>

			<button
				onclick={handleClose}
				class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
				aria-label="Fermer"
			>
				✕
			</button>
		</div>

		<!-- Actions bar -->
		{#if notificationCenterStore.hasUnread}
			<div class="px-4 py-2 border-b border-[var(--glass-border-subtle)]">
				<button
					onclick={handleMarkAllRead}
					class="text-xs text-[var(--color-accent)] hover:underline"
				>
					Tout marquer comme lu
				</button>
			</div>
		{/if}

		<!-- Notifications list -->
		<div
			bind:this={listRef}
			class="flex-1 overflow-y-auto"
			onscroll={handleScroll}
			role="list"
			aria-label="Liste des notifications"
		>
			{#if notificationCenterStore.loading && notificationCenterStore.notifications.length === 0}
				<!-- Loading skeleton -->
				<div class="p-4 space-y-3">
					{#each Array(5) as _}
						<div class="animate-pulse">
							<div class="flex items-start gap-3">
								<div class="w-8 h-8 rounded-full bg-[var(--glass-tint)]"></div>
								<div class="flex-1 space-y-2">
									<div class="h-4 bg-[var(--glass-tint)] rounded w-3/4"></div>
									<div class="h-3 bg-[var(--glass-tint)] rounded w-1/2"></div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else if notificationCenterStore.isEmpty}
				<!-- Empty state -->
				<div class="flex flex-col items-center justify-center h-full p-8 text-center">
					<span class="text-4xl mb-4 opacity-50">🔕</span>
					<p class="text-[var(--color-text-secondary)] text-sm">
						Aucune notification
					</p>
					<p class="text-[var(--color-text-tertiary)] text-xs mt-1">
						Vous serez notifié des événements importants
					</p>
				</div>
			{:else if notificationCenterStore.error}
				<!-- Error state -->
				<div class="flex flex-col items-center justify-center h-full p-8 text-center">
					<span class="text-4xl mb-4">⚠️</span>
					<p class="text-red-400 text-sm mb-2">{notificationCenterStore.error}</p>
					<button
						onclick={handleRefresh}
						class="text-xs text-[var(--color-accent)] hover:underline"
					>
						Réessayer
					</button>
				</div>
			{:else}
				<!-- Notification items -->
				<ul class="divide-y divide-[var(--glass-border-subtle)]">
					{#each notificationCenterStore.notifications as notification (notification.id)}
						<li
							class="relative group"
							role="listitem"
						>
							<button
								onclick={() => handleMarkAsRead(notification.id)}
								class="w-full text-left px-4 py-3 hover:bg-[var(--glass-tint)] transition-colors
									{notification.is_read ? 'opacity-70' : ''}"
							>
								<div class="flex items-start gap-3">
									<!-- Icon -->
									<span class="text-lg flex-shrink-0 mt-0.5">
										{notificationCenterStore.getTypeIcon(notification.type)}
									</span>

									<!-- Content -->
									<div class="flex-1 min-w-0">
										<div class="flex items-start justify-between gap-2">
											<h3 class="font-medium text-sm text-[var(--color-text-primary)] line-clamp-1
												{!notification.is_read ? 'font-semibold' : ''}">
												{notification.title}
											</h3>

											{#if !notification.is_read}
												<span class="flex-shrink-0 w-2 h-2 rounded-full bg-[var(--color-accent)] mt-1.5"></span>
											{/if}
										</div>

										{#if notification.message}
											<p class="text-xs text-[var(--color-text-secondary)] mt-0.5 line-clamp-2">
												{notification.message}
											</p>
										{/if}

										<div class="flex items-center gap-2 mt-1">
											<span class="text-xs text-[var(--color-text-tertiary)]">
												{notificationCenterStore.formatTimestamp(notification.created_at)}
											</span>

											{#if notification.priority !== 'normal'}
												<span class="text-xs {notificationCenterStore.getPriorityColor(notification.priority)}">
													{notification.priority === 'urgent' ? '🔴' : notification.priority === 'high' ? '🟠' : ''}
												</span>
											{/if}
										</div>
									</div>
								</div>
							</button>

							<!-- Delete button (on hover) -->
							<button
								onclick={() => handleDelete(notification.id)}
								class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg
									bg-[var(--glass-tint)] hover:bg-red-500/20 transition-colors
									opacity-0 group-hover:opacity-100"
								title="Supprimer"
								aria-label="Supprimer la notification"
							>
								<span class="text-xs">🗑️</span>
							</button>
						</li>
					{/each}
				</ul>

				<!-- Load more indicator -->
				{#if notificationCenterStore.loading && notificationCenterStore.notifications.length > 0}
					<div class="p-4 text-center">
						<span class="text-sm text-[var(--color-text-tertiary)]">Chargement...</span>
					</div>
				{/if}

				{#if !notificationCenterStore.hasMore && notificationCenterStore.notifications.length > 0}
					<div class="p-4 text-center">
						<span class="text-xs text-[var(--color-text-tertiary)]">Fin des notifications</span>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Footer with stats -->
		{#if notificationCenterStore.stats}
			<div class="px-4 py-2 border-t border-[var(--glass-border-subtle)] text-xs text-[var(--color-text-tertiary)]">
				{notificationCenterStore.stats.total} notifications
				{#if notificationCenterStore.stats.unread > 0}
					• {notificationCenterStore.stats.unread} non lues
				{/if}
			</div>
		{/if}
	</div>
{/if}

<!-- Desktop trigger button (fixed top right, next to chat panel) -->
<button
	onclick={() => { notificationCenterStore.toggle(); haptic('light'); }}
	class="fixed top-3 z-50 p-2.5 rounded-xl glass-prominent hover:glass transition-all
		shadow-lg hover:shadow-xl hidden md:flex items-center justify-center"
	style="right: calc(288px + 12px);"
	aria-label="Notifications"
	aria-expanded={notificationCenterStore.isOpen}
>
	<span class="text-lg">🔔</span>

	{#if notificationCenterStore.hasUnread}
		<span class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[var(--color-accent)] text-white text-[10px] font-bold flex items-center justify-center shadow-md" data-testid="notification-badge">
			{notificationCenterStore.unreadCount > 9 ? '9+' : notificationCenterStore.unreadCount}
		</span>
	{/if}
</button>

<!-- Mobile trigger button (fixed top right) -->
<button
	onclick={() => { notificationCenterStore.toggle(); haptic('light'); }}
	class="fixed top-3 right-3 z-50 p-2.5 rounded-xl glass-prominent hover:glass transition-all
		shadow-lg md:hidden flex items-center justify-center"
	aria-label="Notifications"
	aria-expanded={notificationCenterStore.isOpen}
>
	<span class="text-lg">🔔</span>

	{#if notificationCenterStore.hasUnread}
		<span class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[var(--color-accent)] text-white text-[10px] font-bold flex items-center justify-center shadow-md">
			{notificationCenterStore.unreadCount > 9 ? '9+' : notificationCenterStore.unreadCount}
		</span>
	{/if}
</button>

<!-- Mobile Panel (slide up) -->
{#if notificationCenterStore.isOpen}
	<div class="lg:hidden">
		<!-- Backdrop -->
		<button
			type="button"
			class="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
			onclick={handleBackdropClick}
			aria-label="Fermer les notifications"
			tabindex="-1"
		></button>

		<!-- Panel -->
		<div
			role="dialog"
			aria-modal="true"
			aria-labelledby="notifications-mobile-title"
			tabindex="-1"
			class="fixed bottom-0 left-0 right-0 glass-prominent rounded-t-3xl z-50 max-h-[85vh] flex flex-col
				animate-in slide-in-from-bottom duration-300 ease-out"
			style="padding-bottom: var(--safe-area-bottom);"
			onkeydown={handleKeydown}
		>
			<!-- Handle -->
			<div class="flex justify-center py-3" aria-hidden="true">
				<div class="w-10 h-1 bg-[var(--color-border)] rounded-full"></div>
			</div>

			<!-- Header -->
			<div class="px-4 pb-3 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<h2 id="notifications-mobile-title" class="font-semibold">Notifications</h2>
					{#if notificationCenterStore.hasUnread}
						<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)]">
							{notificationCenterStore.unreadCount}
						</span>
					{/if}
				</div>

				<div class="flex items-center gap-2">
					{#if notificationCenterStore.hasUnread}
						<button
							onclick={handleMarkAllRead}
							class="text-xs text-[var(--color-accent)]"
						>
							Tout lire
						</button>
					{/if}
					<button
						onclick={handleClose}
						class="p-2 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
						aria-label="Fermer"
					>
						✕
					</button>
				</div>
			</div>

			<!-- Notifications list (mobile) -->
			<div
				class="flex-1 overflow-y-auto px-4 pb-4 min-h-[200px] max-h-[60vh]"
				onscroll={handleScroll}
			>
				{#if notificationCenterStore.loading && notificationCenterStore.notifications.length === 0}
					<div class="space-y-3">
						{#each Array(3) as _}
							<div class="animate-pulse flex items-start gap-3 p-3 rounded-xl glass-subtle">
								<div class="w-10 h-10 rounded-full bg-[var(--glass-tint)]"></div>
								<div class="flex-1 space-y-2">
									<div class="h-4 bg-[var(--glass-tint)] rounded w-3/4"></div>
									<div class="h-3 bg-[var(--glass-tint)] rounded w-1/2"></div>
								</div>
							</div>
						{/each}
					</div>
				{:else if notificationCenterStore.isEmpty}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<span class="text-5xl mb-4 opacity-50">🔕</span>
						<p class="text-[var(--color-text-secondary)]">Aucune notification</p>
					</div>
				{:else}
					<div class="space-y-2">
						{#each notificationCenterStore.notifications as notification (notification.id)}
							<button
								onclick={() => handleMarkAsRead(notification.id)}
								class="w-full text-left p-3 rounded-xl glass-subtle hover:glass transition-colors
									{notification.is_read ? 'opacity-70' : ''}"
							>
								<div class="flex items-start gap-3">
									<span class="text-xl">
										{notificationCenterStore.getTypeIcon(notification.type)}
									</span>

									<div class="flex-1 min-w-0">
										<div class="flex items-start justify-between gap-2">
											<h3 class="font-medium text-sm {!notification.is_read ? 'font-semibold' : ''}">
												{notification.title}
											</h3>
											{#if !notification.is_read}
												<span class="w-2 h-2 rounded-full bg-[var(--color-accent)] flex-shrink-0 mt-1.5"></span>
											{/if}
										</div>

										{#if notification.message}
											<p class="text-sm text-[var(--color-text-secondary)] mt-1 line-clamp-2">
												{notification.message}
											</p>
										{/if}

										<span class="text-xs text-[var(--color-text-tertiary)] mt-1 block">
											{notificationCenterStore.formatTimestamp(notification.created_at)}
										</span>
									</div>
								</div>
							</button>
						{/each}
					</div>

					{#if notificationCenterStore.loading}
						<div class="py-4 text-center">
							<span class="text-sm text-[var(--color-text-tertiary)]">Chargement...</span>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes slide-in-from-right {
		from {
			transform: translateX(100%);
		}
		to {
			transform: translateX(0);
		}
	}

	@keyframes slide-in-from-bottom {
		from {
			transform: translateY(100%);
		}
		to {
			transform: translateY(0);
		}
	}

	.animate-in {
		animation-fill-mode: both;
	}

	.slide-in-from-right {
		animation-name: slide-in-from-right;
	}

	.slide-in-from-bottom {
		animation-name: slide-in-from-bottom;
	}
</style>
