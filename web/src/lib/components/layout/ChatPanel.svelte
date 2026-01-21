<script lang="ts">
	import { page } from '$app/stores';
	import { Button, Input } from '$lib/components/ui';
	import { haptic } from '$lib/utils/haptics';
	import { noteChatStore } from '$lib/stores/note-chat.svelte';
	import { quickChat } from '$lib/api/client';
	import ChatHeader from '$lib/components/chat/ChatHeader.svelte';
	import ChatMessage from '$lib/components/chat/ChatMessage.svelte';
	import ChatSuggestions from '$lib/components/chat/ChatSuggestions.svelte';
	import { browser } from '$app/environment';

	let message = $state('');
	let isOpen = $state(false);

	// General chat state
	interface GeneralMessage {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: string;
	}
	let generalMessages = $state<GeneralMessage[]>([]);
	let generalSuggestions = $state<{ label: string; query: string; icon: string }[]>([]);
	let isSendingGeneral = $state(false);
	let generalError = $state<string | null>(null);
	let mobileInputRef = $state<HTMLInputElement | null>(null);
	let messagesEndRef: HTMLDivElement | null = $state(null);

	const isNoteChatMode = $derived(noteChatStore.noteContext !== null);

	// Scroll to bottom
	const scrollToBottom = () =>
		requestAnimationFrame(() => messagesEndRef?.scrollIntoView({ behavior: 'smooth' }));

	$effect(() => {
		if (noteChatStore.isOpen && !isOpen) {
			isOpen = true;
			requestAnimationFrame(() => {
				mobileInputRef?.focus();
				scrollToBottom();
			});
		}
	});

	$effect(() => {
		if (noteChatStore.messages.length > 0 || generalMessages.length > 0) scrollToBottom();
	});

	const pageSuggestions: Record<string, { label: string; query: string; icon: string }[]> = {
		'/': [
			{ label: 'Résumez ma journée', query: 'Faites-moi un résumé de ma journée', icon: '📋' },
			{ label: 'Préparez ma réunion', query: 'Préparez ma prochaine réunion', icon: '🎯' }
		],
		'/peripeties': [
			{
				label: 'Affaires pressantes',
				query: 'Montrez-moi uniquement les affaires pressantes',
				icon: '🔴'
			}
		]
	};

	const suggestions = $derived(() => {
		if (isNoteChatMode)
			return noteChatStore.contextualSuggestions.map((s) => ({
				label: s.label,
				query: s.query,
				icon: '💬'
			}));
		if (generalSuggestions.length > 0) return generalSuggestions;
		return (
			pageSuggestions[$page.url.pathname] || [
				{ label: "Besoin d'aide ?", query: 'Que pouvez-vous faire ?', icon: '❓' }
			]
		);
	});

	async function handleSubmit() {
		if (!message.trim()) return;
		haptic('medium');
		const msg = message;
		message = '';

		if (isNoteChatMode) {
			await noteChatStore.sendMessage(msg);
		} else {
			generalMessages = [
				...generalMessages,
				{ id: crypto.randomUUID(), role: 'user', content: msg, timestamp: new Date().toISOString() }
			];
			isSendingGeneral = true;
			try {
				const res = await quickChat({ message: msg, include_suggestions: true });
				generalMessages = [
					...generalMessages,
					{
						id: crypto.randomUUID(),
						role: 'assistant',
						content: res.response,
						timestamp: new Date().toISOString()
					}
				];
				generalSuggestions = res.suggestions.map((s) => ({
					label: s.content,
					query: s.content,
					icon: '✨'
				}));
			} catch (e) {
				generalError = 'Erreur de connexion';
			} finally {
				isSendingGeneral = false;
			}
		}
	}

	function handleSuggestion(query: string) {
		message = query;
		if (!query.endsWith('...')) handleSubmit();
	}
</script>

<aside
	class="fixed right-0 top-0 h-full w-72 glass-prominent hidden lg:flex flex-col z-40"
	data-testid="chat-panel"
>
	<ChatHeader
		{isNoteChatMode}
		onclose={() => (isOpen = false)}
		onSaveAsDiscussion={() => noteChatStore.saveAsDiscussion()}
		onClearConversation={() => noteChatStore.clearConversation()}
	/>

	<div class="flex-1 p-3 overflow-y-auto">
		<div class="space-y-3">
			{#if isNoteChatMode}
				{#each noteChatStore.messages as msg (msg.id)}
					<ChatMessage role={msg.role} content={msg.content} timestamp={msg.timestamp} />
				{/each}
			{:else}
				{#each generalMessages as msg (msg.id)}
					<ChatMessage role={msg.role} content={msg.content} timestamp={msg.timestamp} />
				{/each}
			{/if}
			<div bind:this={messagesEndRef}></div>
		</div>

		{#if !noteChatStore.sending && !isSendingGeneral}
			<div class="mt-4">
				<ChatSuggestions suggestions={suggestions()} onsuggestion={handleSuggestion} />
			</div>
		{/if}
	</div>

	<div class="p-2 border-t border-[var(--glass-border-subtle)]">
		<div class="flex gap-1.5">
			<Input
				bind:value={message}
				placeholder="Scapin..."
				onkeydown={(e) => e.key === 'Enter' && handleSubmit()}
			/>
			<Button variant="primary" size="sm" onclick={handleSubmit} disabled={!message.trim()}
				>↑</Button
			>
		</div>
	</div>
</aside>
