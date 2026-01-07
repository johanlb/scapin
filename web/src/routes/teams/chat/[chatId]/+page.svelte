<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Badge, Button, Input, Skeleton } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import {
		listTeamsMessages,
		replyToTeamsMessage,
		flagTeamsMessage,
		markChatAsRead
	} from '$lib/api';
	import type { TeamsMessage } from '$lib/api';

	// Get the chat ID from route params
	const chatId = $derived($page.params.chatId ?? '');
	const messageId = $derived($page.url.searchParams.get('message'));

	// State
	let messages = $state<TeamsMessage[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	// Separate reply states to avoid conflict between inline and quick reply
	let inlineReplyContent = $state('');
	let quickReplyContent = $state('');
	let replyingToId = $state<string | null>(null);
	let sendingReply = $state(false);
	let markingAsRead = $state(false);

	// Selected message for detailed view
	const selectedMessage = $derived(
		messageId ? messages.find((m) => m.id === messageId) : messages[0]
	);

	onMount(async () => {
		if (chatId) {
			await loadMessages();
		}
	});

	async function loadMessages() {
		loading = true;
		error = null;

		try {
			const response = await listTeamsMessages(chatId, 1, 50);
			if (response.success && response.data) {
				messages = response.data;
			} else {
				error = 'Impossible de charger les messages';
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
		} finally {
			loading = false;
		}
	}

	async function handleInlineReply(messageId: string) {
		if (!inlineReplyContent.trim()) return;

		sendingReply = true;
		try {
			await replyToTeamsMessage(chatId, messageId, inlineReplyContent);
			inlineReplyContent = '';
			replyingToId = null;
			// Reload messages to see the reply
			await loadMessages();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors de l\'envoi';
		} finally {
			sendingReply = false;
		}
	}

	async function handleQuickReply() {
		if (!quickReplyContent.trim() || messages.length === 0) return;

		sendingReply = true;
		try {
			// Reply to the most recent message
			await replyToTeamsMessage(chatId, messages[0].id, quickReplyContent);
			quickReplyContent = '';
			// Reload messages to see the reply
			await loadMessages();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors de l\'envoi';
		} finally {
			sendingReply = false;
		}
	}

	async function handleFlag(messageId: string, flagged: boolean) {
		try {
			await flagTeamsMessage(chatId, messageId, !flagged);
			await loadMessages();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors du marquage';
		}
	}

	async function handleMarkAsRead() {
		markingAsRead = true;
		try {
			await markChatAsRead(chatId);
			// Optionally refresh or show feedback
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur lors du marquage';
		} finally {
			markingAsRead = false;
		}
	}

	function goBack() {
		// Go back to flux or discussions
		goto('/flux');
	}

	function getInitials(name: string): string {
		if (!name || name.trim() === '') return '?';
		return name
			.split(' ')
			.map((n) => n[0])
			.join('')
			.toUpperCase()
			.slice(0, 2);
	}

	function getImportanceColor(importance: string): string {
		switch (importance.toLowerCase()) {
			case 'high':
				return 'text-red-400';
			case 'urgent':
				return 'text-orange-400';
			default:
				return 'text-[var(--color-text-tertiary)]';
		}
	}
</script>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<!-- Header -->
	<header
		class="sticky top-0 z-20 glass-prominent border-b border-[var(--glass-border-subtle)] px-4 py-3"
	>
		<div class="max-w-4xl mx-auto flex items-center gap-3">
			<button
				onclick={goBack}
				class="p-2 -ml-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
				aria-label="Retour"
			>
				<span class="text-xl">&#8592;</span>
			</button>
			<div class="flex-1 min-w-0">
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)] truncate">
					Conversation Teams
				</h1>
				<p class="text-sm text-[var(--color-text-tertiary)]">
					{messages.length} message{messages.length !== 1 ? 's' : ''}
				</p>
			</div>
			<Button
				variant="glass"
				size="sm"
				onclick={handleMarkAsRead}
				disabled={markingAsRead}
			>
				{#if markingAsRead}
					<span class="animate-pulse">...</span>
				{:else}
					Marquer comme lu
				{/if}
			</Button>
		</div>
	</header>

	{#if loading}
		<!-- Loading state -->
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4" role="status" aria-busy="true" aria-label="Chargement des messages">
			<span class="sr-only">Chargement des messages en cours...</span>
			{#each Array(3) as _}
				<Card variant="glass-subtle">
					<div class="p-4 space-y-3">
						<div class="flex items-center gap-3">
							<Skeleton variant="avatar" />
							<div class="flex-1 space-y-2">
								<Skeleton variant="text" class="w-1/3" />
								<Skeleton variant="text" class="w-1/4" />
							</div>
						</div>
						<Skeleton variant="text" lines={3} />
					</div>
				</Card>
			{/each}
		</main>
	{:else if error}
		<!-- Error state -->
		<main class="p-8 text-center">
			<div class="text-red-400 mb-4">{error}</div>
			<Button variant="glass" onclick={loadMessages}>Réessayer</Button>
		</main>
	{:else if messages.length === 0}
		<!-- Empty state -->
		<main class="p-8 text-center">
			<p class="text-[var(--color-text-tertiary)]">Aucun message dans cette conversation</p>
		</main>
	{:else}
		<main class="p-4 md:p-6 max-w-4xl mx-auto">
			<!-- Messages list -->
			<div class="space-y-4">
				{#each messages as message (message.id)}
					{@const isSelected = selectedMessage?.id === message.id}
					<Card
						variant={isSelected ? 'glass' : 'glass-subtle'}
						class="transition-all {isSelected ? 'ring-2 ring-[var(--color-accent)]' : ''}"
					>
						<div class="p-4">
							<!-- Message header -->
							<div class="flex items-start gap-3 mb-3">
								<div
									class="w-10 h-10 rounded-full bg-gradient-to-br from-[var(--color-accent)] to-purple-500 flex items-center justify-center text-white font-semibold text-sm shrink-0"
								>
									{getInitials(message.sender.display_name)}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 flex-wrap">
										<span class="font-medium text-[var(--color-text-primary)]">
											{message.sender.display_name}
										</span>
										{#if message.importance !== 'normal'}
											<Badge variant="urgency" urgency={message.importance === 'high' ? 'urgent' : 'high'}>
												{message.importance}
											</Badge>
										{/if}
										{#if message.has_mentions}
											<Badge variant="source" source="teams">@mention</Badge>
										{/if}
									</div>
									<div class="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
										{#if message.sender.email}
											<span class="truncate">{message.sender.email}</span>
											<span>&#8226;</span>
										{/if}
										<span>{formatRelativeTime(message.created_at)}</span>
									</div>
								</div>
								<!-- Actions -->
								<div class="flex items-center gap-1">
									<button
										onclick={() => handleFlag(message.id, false)}
										class="p-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
										title="Marquer pour suivi"
									>
										<span class="text-lg">&#9873;</span>
									</button>
								</div>
							</div>

							<!-- Message content -->
							<div class="text-[var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed">
								{message.content || message.content_preview}
							</div>

							<!-- Attachments indicator -->
							{#if message.attachments_count > 0}
								<div class="mt-3 flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
									<span>&#128206;</span>
									<span>{message.attachments_count} pièce{message.attachments_count > 1 ? 's' : ''} jointe{message.attachments_count > 1 ? 's' : ''}</span>
								</div>
							{/if}

							<!-- Reply section -->
							{#if replyingToId === message.id}
								<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
									<div class="flex gap-2">
										<Input
											bind:value={inlineReplyContent}
											placeholder="Votre réponse..."
											class="flex-1"
											onkeydown={(e: KeyboardEvent) => {
												if (e.key === 'Escape') {
													replyingToId = null;
													inlineReplyContent = '';
												} else if (e.key === 'Enter' && !e.shiftKey) {
													handleInlineReply(message.id);
												}
											}}
										/>
										<Button
											variant="primary"
											size="sm"
											onclick={() => handleInlineReply(message.id)}
											disabled={sendingReply || !inlineReplyContent.trim()}
										>
											{#if sendingReply}
												<span class="animate-pulse">...</span>
											{:else}
												Envoyer
											{/if}
										</Button>
										<Button
											variant="ghost"
											size="sm"
											onclick={() => { replyingToId = null; inlineReplyContent = ''; }}
										>
											Annuler
										</Button>
									</div>
								</div>
							{:else}
								<div class="mt-4 pt-4 border-t border-[var(--glass-border-subtle)]">
									<Button
										variant="ghost"
										size="sm"
										onclick={() => replyingToId = message.id}
									>
										&#8617; Répondre
									</Button>
								</div>
							{/if}
						</div>
					</Card>
				{/each}
			</div>

			<!-- Quick reply at bottom -->
			<div class="mt-6 sticky bottom-4">
				<Card variant="glass">
					<div class="p-3 flex gap-2">
						<Input
							bind:value={quickReplyContent}
							placeholder="Répondre à la conversation..."
							class="flex-1"
							onkeydown={(e: KeyboardEvent) => {
								if (e.key === 'Enter' && !e.shiftKey) {
									handleQuickReply();
								}
							}}
						/>
						<Button
							variant="primary"
							onclick={() => handleQuickReply()}
							disabled={sendingReply || !quickReplyContent.trim() || messages.length === 0}
						>
							{#if sendingReply}
								<span class="animate-pulse">...</span>
							{:else}
								Envoyer
							{/if}
						</Button>
					</div>
				</Card>
			</div>
		</main>
	{/if}
</div>
