<script lang="ts">
	/**
	 * Teams Chat Detail Page
	 * Shows full thread with all messages and reply functionality
	 */
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Card, Button, Skeleton } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		listTeamsMessages,
		replyToTeamsMessage,
		flagTeamsMessage,
		markChatAsRead,
		markChatAsUnread
	} from '$lib/api';
	import type { TeamsMessage } from '$lib/api';

	// Get chat ID from route params (always defined in this route)
	const chatId = $derived($page.params.chatId ?? '');

	// AbortController for cleanup on unmount
	let abortController: AbortController | null = null;

	// State
	let messages = $state<TeamsMessage[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let hasMore = $state(false);
	let currentPage = $state(1);
	let loadingMore = $state(false);

	// Reply state
	let replyingTo = $state<TeamsMessage | null>(null);
	let replyContent = $state('');
	let sendingReply = $state(false);

	// Action states
	let markingRead = $state(false);
	let markingUnread = $state(false);
	let flaggingMessage = $state<string | null>(null);

	onMount(async () => {
		if (!chatId) {
			goto('/peripeties');
			return;
		}
		await loadMessages();
	});

	onDestroy(() => {
		// Cancel any pending requests on unmount
		abortController?.abort();
	});

	async function loadMessages() {
		// Cancel any existing request
		abortController?.abort();
		abortController = new AbortController();

		loading = true;
		error = null;

		try {
			const response = await listTeamsMessages(chatId, 1, 50);
			messages = response.data;
			hasMore = response.has_more;
			currentPage = 1;
		} catch (e) {
			// Ignore AbortError (intentional cancellation)
			if (e instanceof Error && e.name === 'AbortError') {
				return;
			}
			console.error('Failed to load messages:', e);
			error = e instanceof Error ? e.message : 'Erreur lors du chargement des messages';
		} finally {
			loading = false;
		}
	}

	async function loadMoreMessages() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;

		try {
			const nextPage = currentPage + 1;
			const response = await listTeamsMessages(chatId, nextPage, 50);
			messages = [...messages, ...response.data];
			hasMore = response.has_more;
			currentPage = nextPage;
		} catch (e) {
			// Ignore AbortError
			if (e instanceof Error && e.name === 'AbortError') {
				return;
			}
			console.error('Failed to load more messages:', e);
			toastStore.error('Erreur lors du chargement');
		} finally {
			loadingMore = false;
		}
	}

	function startReply(message: TeamsMessage) {
		replyingTo = message;
		replyContent = '';
	}

	function cancelReply() {
		replyingTo = null;
		replyContent = '';
	}

	async function sendReply() {
		if (!replyingTo || !replyContent.trim() || sendingReply) return;
		sendingReply = true;

		try {
			await replyToTeamsMessage(chatId, replyingTo.id, replyContent);
			toastStore.success('Réponse envoyée');
			cancelReply();
			// Refresh messages to show the reply
			await loadMessages();
		} catch (e) {
			console.error('Failed to send reply:', e);
			toastStore.error(e instanceof Error ? e.message : 'Erreur lors de l\'envoi');
		} finally {
			sendingReply = false;
		}
	}

	async function handleMarkAsRead() {
		if (markingRead) return;
		markingRead = true;

		try {
			await markChatAsRead(chatId);
			toastStore.success('Conversation marquée comme lue');
			// Update local state
			messages = messages.map((m) => ({ ...m, is_read: true }));
		} catch (e) {
			console.error('Failed to mark as read:', e);
			toastStore.error('Erreur lors du marquage');
		} finally {
			markingRead = false;
		}
	}

	async function handleMarkAsUnread() {
		if (markingUnread) return;
		markingUnread = true;

		try {
			await markChatAsUnread(chatId);
			toastStore.success('Conversation marquée comme non lue');
		} catch (e) {
			console.error('Failed to mark as unread:', e);
			toastStore.error('Erreur lors du marquage');
		} finally {
			markingUnread = false;
		}
	}

	async function handleFlagMessage(message: TeamsMessage) {
		if (flaggingMessage) return;
		flaggingMessage = message.id;

		try {
			await flagTeamsMessage(chatId, message.id, true, 'Flagged from UI');
			toastStore.success('Message signalé');
		} catch (e) {
			console.error('Failed to flag message:', e);
			toastStore.error('Erreur lors du signalement');
		} finally {
			flaggingMessage = null;
		}
	}

	function goBack() {
		goto('/peripeties');
	}

	// Get initials for avatar
	function getInitials(name: string): string {
		if (!name) return '?';
		const parts = name.split(' ').filter(Boolean);
		if (parts.length === 0) return '?';
		if (parts.length === 1) return parts[0][0]?.toUpperCase() || '?';
		return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
	}

	// Get avatar color based on name
	function getAvatarColor(name: string): string {
		const colors = [
			'bg-blue-500',
			'bg-green-500',
			'bg-purple-500',
			'bg-orange-500',
			'bg-pink-500',
			'bg-cyan-500',
			'bg-indigo-500'
		];
		let hash = 0;
		for (let i = 0; i < name.length; i++) {
			hash = name.charCodeAt(i) + ((hash << 5) - hash);
		}
		return colors[Math.abs(hash) % colors.length];
	}

	// Check if message has unread status
	const hasUnread = $derived(messages.some((m) => !m.is_read));
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<!-- Header -->
	<header class="mb-6">
		<div class="flex items-center gap-3 mb-4">
			<button
				type="button"
				class="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] transition-colors"
				onclick={goBack}
				aria-label="Retour"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</button>
			<div>
				<h1 class="text-xl md:text-2xl font-bold text-[var(--color-text-primary)]">
					Conversation Teams
				</h1>
				<p class="text-sm text-[var(--color-text-secondary)]">
					{messages.length} message{messages.length !== 1 ? 's' : ''}
				</p>
			</div>
		</div>

		<!-- Action buttons -->
		<div class="flex flex-wrap gap-2">
			<Button
				variant="secondary"
				size="sm"
				onclick={handleMarkAsRead}
				disabled={markingRead || !hasUnread}
			>
				{#if markingRead}
					<span class="animate-spin mr-1">&#8635;</span>
				{:else}
					<span class="mr-1">&#10003;</span>
				{/if}
				Marquer lu
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={handleMarkAsUnread}
				disabled={markingUnread}
			>
				{#if markingUnread}
					<span class="animate-spin mr-1">&#8635;</span>
				{:else}
					<span class="mr-1">&#9679;</span>
				{/if}
				Marquer non lu
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={loadMessages}
				disabled={loading}
			>
				<span class="mr-1">&#8634;</span>
				Actualiser
			</Button>
		</div>
	</header>

	<!-- Loading state -->
	{#if loading}
		<div class="space-y-4">
			{#each Array(5) as _}
				<Card padding="md">
					<div class="flex gap-3">
						<Skeleton variant="avatar" class="w-10 h-10" />
						<div class="flex-1 space-y-2">
							<Skeleton variant="text" class="w-32" />
							<Skeleton variant="text" class="w-full" />
							<Skeleton variant="text" class="w-3/4" />
						</div>
					</div>
				</Card>
			{/each}
		</div>

	<!-- Error state -->
	{:else if error}
		<Card padding="lg">
			<div class="text-center py-8">
				<p class="text-4xl mb-3">&#9888;</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-2">
					Erreur de chargement
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)] mb-4">{error}</p>
				<Button variant="primary" size="sm" onclick={loadMessages}>
					Réessayer
				</Button>
			</div>
		</Card>

	<!-- Empty state -->
	{:else if messages.length === 0}
		<Card padding="lg">
			<div class="text-center py-8">
				<p class="text-4xl mb-3">&#128172;</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
					Aucun message
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">
					Cette conversation est vide
				</p>
			</div>
		</Card>

	<!-- Messages list -->
	{:else}
		<div class="space-y-4">
			{#each messages as message (message.id)}
				{@const isReplyingToThis = replyingTo?.id === message.id}
				<Card
					padding="md"
					class="transition-all {isReplyingToThis ? 'ring-2 ring-[var(--color-accent)]' : ''}"
				>
					<div class="flex gap-3">
						<!-- Avatar -->
						<div
							class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold {getAvatarColor(message.sender.display_name)}"
						>
							{getInitials(message.sender.display_name)}
						</div>

						<!-- Content -->
						<div class="flex-1 min-w-0">
							<!-- Header -->
							<div class="flex items-center gap-2 mb-1">
								<span class="font-semibold text-[var(--color-text-primary)]">
									{message.sender.display_name}
								</span>
								{#if !message.is_read}
									<span class="w-2 h-2 rounded-full bg-[var(--color-accent)]" title="Non lu"></span>
								{/if}
								{#if message.has_mentions}
									<span
										class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400"
									>
										@mention
									</span>
								{/if}
								{#if message.importance === 'high'}
									<span class="text-xs text-red-400" title="Haute importance">&#9888;</span>
								{/if}
								<span class="text-xs text-[var(--color-text-tertiary)] ml-auto">
									{formatRelativeTime(message.created_at)}
								</span>
							</div>

							<!-- Message content -->
							<div class="text-[var(--color-text-secondary)] whitespace-pre-wrap">
								{message.content}
							</div>

							<!-- Attachments indicator -->
							{#if message.attachments_count > 0}
								<div class="flex items-center gap-1 mt-2 text-xs text-[var(--color-text-tertiary)]">
									<span>&#128206;</span>
									<span>{message.attachments_count} pièce{message.attachments_count > 1 ? 's' : ''} jointe{message.attachments_count > 1 ? 's' : ''}</span>
								</div>
							{/if}

							<!-- Actions -->
							<div class="flex gap-2 mt-3">
								<button
									type="button"
									class="text-xs px-2 py-1 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)] hover:text-white transition-colors"
									onclick={() => startReply(message)}
								>
									&#8617; Répondre
								</button>
								<button
									type="button"
									class="text-xs px-2 py-1 rounded bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:bg-orange-500/20 hover:text-orange-400 transition-colors disabled:opacity-50"
									onclick={() => handleFlagMessage(message)}
									disabled={flaggingMessage === message.id}
								>
									{#if flaggingMessage === message.id}
										<span class="animate-spin">&#8635;</span>
									{:else}
										&#128681; Signaler
									{/if}
								</button>
							</div>

							<!-- Reply form -->
							{#if isReplyingToThis}
								<div class="mt-4 p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
									<p class="text-xs text-[var(--color-text-tertiary)] mb-2">
										Réponse à {message.sender.display_name}
									</p>
									<textarea
										class="w-full p-2 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:border-[var(--color-accent)] focus:outline-none resize-none"
										rows="3"
										placeholder="Votre réponse... (⌘+Entrée pour envoyer)"
										bind:value={replyContent}
									onkeydown={(e) => {
										if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && replyContent.trim() && !sendingReply) {
											e.preventDefault();
											sendReply();
										}
									}}
									></textarea>
									<div class="flex gap-2 mt-2">
										<Button
											variant="primary"
											size="sm"
											onclick={sendReply}
											disabled={sendingReply || !replyContent.trim()}
										>
											{#if sendingReply}
												<span class="animate-spin mr-1">&#8635;</span>
											{/if}
											Envoyer
										</Button>
										<Button
											variant="secondary"
											size="sm"
											onclick={cancelReply}
											disabled={sendingReply}
										>
											Annuler
										</Button>
									</div>
								</div>
							{/if}
						</div>
					</div>
				</Card>
			{/each}

			<!-- Load more button -->
			{#if hasMore}
				<div class="text-center py-4">
					<Button
						variant="secondary"
						size="sm"
						onclick={loadMoreMessages}
						disabled={loadingMore}
					>
						{#if loadingMore}
							<span class="animate-spin mr-1">&#8635;</span>
							Chargement...
						{:else}
							Charger plus de messages
						{/if}
					</Button>
				</div>
			{/if}
		</div>
	{/if}
</div>
