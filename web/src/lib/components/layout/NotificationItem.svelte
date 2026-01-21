<script lang="ts">
	import type { Notification } from '$lib/api/client';
	import { notificationCenterStore } from '$lib/stores/notification-center.svelte';

	interface Props {
		notification: Notification;
		onmarkread: (id: string) => void;
		onremove: (id: string) => void;
	}

	let { notification, onmarkread, onremove }: Props = $props();
</script>

<li class="relative group" role="listitem">
	<button
		onclick={() => onmarkread(notification.id)}
		class="w-full text-left px-4 py-3 hover:bg-[var(--glass-tint)] transition-colors
			{notification.is_read ? 'opacity-70' : ''}"
	>
		<div class="flex items-start gap-3">
			<span class="text-lg flex-shrink-0 mt-0.5">
				{notificationCenterStore.getTypeIcon(notification.type)}
			</span>

			<div class="flex-1 min-w-0">
				<div class="flex items-start justify-between gap-2">
					<h3
						class="font-medium text-sm text-[var(--color-text-primary)] line-clamp-1
						{!notification.is_read ? 'font-semibold' : ''}"
					>
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
							{notification.priority === 'urgent'
								? '🔴'
								: notification.priority === 'high'
									? '🟠'
									: ''}
						</span>
					{/if}
				</div>
			</div>
		</div>
	</button>

	<!-- Delete button (on hover) -->
	<button
		onclick={(e) => {
			e.stopPropagation();
			onremove(notification.id);
		}}
		class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg
			bg-[var(--glass-tint)] hover:bg-red-500/20 transition-colors
			opacity-0 group-hover:opacity-100"
		title="Supprimer"
		aria-label="Supprimer la notification"
	>
		<span class="text-xs">🗑️</span>
	</button>
</li>
