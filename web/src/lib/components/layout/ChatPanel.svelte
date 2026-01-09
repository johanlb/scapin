<script lang="ts">
	import { page } from '$app/stores';
	import { Button, Input } from '$lib/components/ui';
	import { haptic } from '$lib/utils/haptics';
	import { noteChatStore, type ChatMessage } from '$lib/stores/note-chat.svelte';
	import { quickChat, type QuickChatResponse } from '$lib/api/client';

	let message = $state('');
	let isOpen = $state(false);

	// General chat state (when not in note mode)
	interface GeneralMessage {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: string;
	}
	let generalMessages = $state<GeneralMessage[]>([]);
	let generalSuggestions = $state<string[]>([]);
	let isSendingGeneral = $state(false);
	let generalError = $state<string | null>(null);
	let panelRef: HTMLDivElement | null = $state(null);
	let mobileInputRef: HTMLInputElement | null = $state(null);
	let messagesEndRef: HTMLDivElement | null = $state(null);

	// Check if we're in note chat mode
	const isNoteChatMode = $derived(noteChatStore.noteContext !== null);
	const noteContext = $derived(noteChatStore.noteContext);

	// Sync panel open state with note chat store
	$effect(() => {
		if (noteChatStore.isOpen && !isOpen) {
			isOpen = true;
			requestAnimationFrame(() => {
				mobileInputRef?.focus();
				scrollToBottom();
			});
		}
	});

	// Scroll to bottom when messages change
	$effect(() => {
		if (noteChatStore.messages.length > 0) {
			scrollToBottom();
		}
	});

	function scrollToBottom() {
		requestAnimationFrame(() => {
			messagesEndRef?.scrollIntoView({ behavior: 'smooth' });
		});
	}

	// Contextual suggestions based on current page (normal mode)
	interface Suggestion {
		label: string;
		query: string;
		icon: string;
	}

	const pageSuggestions: Record<string, Suggestion[]> = {
		'/': [
			{ label: 'Résumez ma journée', query: 'Faites-moi un résumé de ma journée', icon: '📋' },
			{ label: 'Préparez ma réunion', query: 'Préparez ma prochaine réunion', icon: '🎯' },
			{ label: 'Affaires pressantes', query: 'Quelles affaires requièrent mon attention ?', icon: '⚡' }
		],
		'/flux': [
			{ label: 'Affaires pressantes', query: 'Montrez-moi uniquement les affaires pressantes', icon: '🔴' },
			{ label: 'Classer les traités', query: 'Classez les éléments que j\'ai traités', icon: '📦' },
			{ label: 'Résumer les nouvelles', query: 'Résumez les messages non lus', icon: '📨' }
		],
		'/notes': [
			{ label: 'Chercher un carnet', query: 'Cherchez dans mes carnets...', icon: '🔍' },
			{ label: 'Nouveau carnet', query: 'Créez un nouveau carnet sur...', icon: '✏️' },
			{ label: 'Résumer un projet', query: 'Résumez les carnets du projet...', icon: '📑' }
		],
		'/settings': [
			{ label: 'État des connexions', query: 'Vérifiez l\'état de mes intégrations', icon: '🔗' },
			{ label: 'Optimiser', query: 'Comment optimiser mes réglages ?', icon: '⚙️' }
		]
	};

	const defaultSuggestions: Suggestion[] = [
		{ label: 'Que savez-vous faire ?', query: 'Que pouvez-vous faire pour moi ?', icon: '❓' },
		{ label: 'Faites le point', query: 'Donnez-moi un résumé de la situation', icon: '📊' }
	];

	// In note chat mode, use contextual suggestions; otherwise use page suggestions
	const suggestions = $derived(() => {
		if (isNoteChatMode) {
			return noteChatStore.contextualSuggestions.map((s) => ({
				label: s.label,
				query: s.query,
				icon: '💬'
			}));
		}
		return pageSuggestions[$page.url.pathname] || defaultSuggestions;
	});

	function togglePanel() {
		if (isNoteChatMode) {
			// In note chat mode, toggle via store
			if (isOpen) {
				noteChatStore.close();
				isOpen = false;
			} else {
				isOpen = true;
			}
		} else {
			isOpen = !isOpen;
		}
		haptic('light');

		if (isOpen) {
			requestAnimationFrame(() => {
				mobileInputRef?.focus();
			});
		}
	}

	function closePanel() {
		isOpen = false;
		if (isNoteChatMode) {
			noteChatStore.close();
		}
		haptic('light');
	}

	async function handleSubmit() {
		if (!message.trim()) return;

		haptic('medium');
		const messageToSend = message;
		message = '';

		if (isNoteChatMode) {
			await noteChatStore.sendMessage(messageToSend);
		} else {
			// Send to general chat API
			await sendGeneralMessage(messageToSend);
		}
	}

	async function sendGeneralMessage(content: string) {
		// Add user message to the list
		const userMessage: GeneralMessage = {
			id: crypto.randomUUID(),
			role: 'user',
			content,
			timestamp: new Date().toISOString()
		};
		generalMessages = [...generalMessages, userMessage];
		generalError = null;
		isSendingGeneral = true;

		try {
			const response = await quickChat({
				message: content,
				include_suggestions: true
			});

			// Add assistant response
			const assistantMessage: GeneralMessage = {
				id: crypto.randomUUID(),
				role: 'assistant',
				content: response.response,
				timestamp: new Date().toISOString()
			};
			generalMessages = [...generalMessages, assistantMessage];
			generalSuggestions = response.suggestions.map(s => s.content);
			scrollToBottom();
		} catch (error) {
			console.error('Failed to send message:', error);
			generalError = error instanceof Error ? error.message : 'Erreur de connexion';
		} finally {
			isSendingGeneral = false;
		}
	}

	function clearGeneralChat() {
		generalMessages = [];
		generalSuggestions = [];
		generalError = null;
	}

	function handleSuggestionClick(query: string) {
		haptic('light');
		message = query;
		// Auto-submit for complete queries (not ending with ...)
		if (!query.endsWith('...')) {
			handleSubmit();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}

	function handlePanelKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			closePanel();
		}

		if (e.key === 'Tab' && panelRef) {
			const focusableElements = panelRef.querySelectorAll<HTMLElement>(
				'button, input, [tabindex]:not([tabindex="-1"])'
			);
			const firstElement = focusableElements[0];
			const lastElement = focusableElements[focusableElements.length - 1];

			if (e.shiftKey && document.activeElement === firstElement) {
				e.preventDefault();
				lastElement?.focus();
			} else if (!e.shiftKey && document.activeElement === lastElement) {
				e.preventDefault();
				firstElement?.focus();
			}
		}
	}

	async function handleSaveAsDiscussion() {
		haptic('medium');
		const result = await noteChatStore.saveAsDiscussion();
		if (result) {
			// Could show a toast or navigate to the discussion
			console.log('Discussion saved:', result.id);
		}
	}

	function handleClearConversation() {
		haptic('light');
		noteChatStore.clearConversation();
	}

	function formatTime(timestamp: string): string {
		return new Date(timestamp).toLocaleTimeString('fr-FR', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<!-- Desktop: Fixed right panel -->
<aside
	class="fixed right-0 top-0 h-full w-72 glass-prominent hidden lg:flex flex-col z-40"
	aria-label="Scapin"
	data-testid="chat-panel"
>
	<!-- Header -->
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
					onclick={handleSaveAsDiscussion}
					class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
					title="Sauvegarder comme discussion"
					disabled={noteChatStore.saving}
				>
					<span class="text-sm">{noteChatStore.saving ? '⏳' : '💾'}</span>
				</button>
			{/if}
			{#if noteChatStore.hasMessages}
				<button
					onclick={handleClearConversation}
					class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
					title="Nouvelle conversation"
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
			<!-- General mode buttons -->
			{#if generalMessages.length > 0}
				<button
					onclick={clearGeneralChat}
					class="p-1.5 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
					title="Nouvelle conversation"
				>
					<span class="text-sm">🗑️</span>
				</button>
			{/if}
			<span class="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse" title="À l'écoute"></span>
		{/if}
	</div>

	<!-- Messages area -->
	<div class="flex-1 p-3 overflow-y-auto" role="log" aria-live="polite">
		{#if isNoteChatMode && noteChatStore.hasMessages}
			<!-- Note chat messages -->
			<div class="space-y-3">
				{#each noteChatStore.messages as msg (msg.id)}
					<div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
						<div
							class={`max-w-[85%] rounded-2xl px-3 py-2 ${
								msg.role === 'user'
									? 'bg-[var(--color-accent)] text-white'
									: 'glass-subtle text-[var(--color-text-primary)]'
							}`}
						>
							<p class="text-sm whitespace-pre-wrap">{msg.content}</p>
							<p class={`text-xs mt-1 ${msg.role === 'user' ? 'text-white/70' : 'text-[var(--color-text-tertiary)]'}`}>
								{formatTime(msg.timestamp)}
							</p>
						</div>
					</div>
				{/each}

				{#if noteChatStore.sending}
					<div class="flex justify-start">
						<div class="glass-subtle rounded-2xl px-3 py-2">
							<div class="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
								<span class="animate-pulse">●</span>
								<span class="animate-pulse delay-75">●</span>
								<span class="animate-pulse delay-150">●</span>
							</div>
						</div>
					</div>
				{/if}

				<div bind:this={messagesEndRef}></div>
			</div>

			<!-- AI Suggestions after messages -->
			{#if noteChatStore.suggestions.length > 0}
				<div class="mt-4 pt-3 border-t border-[var(--glass-border-subtle)]">
					<p class="text-xs text-[var(--color-text-tertiary)] mb-2">Suggestions :</p>
					<div class="flex flex-wrap gap-1">
						{#each noteChatStore.suggestions as sug, i (sug.content)}
							<button
								onclick={() => handleSuggestionClick(sug.content)}
								class="px-2 py-1 text-xs rounded-full glass-subtle hover:glass transition-colors"
							>
								{sug.content}
							</button>
						{/each}
					</div>
				</div>
			{/if}
		{:else if !isNoteChatMode && generalMessages.length > 0}
			<!-- General chat messages -->
			<div class="space-y-3">
				{#each generalMessages as msg (msg.id)}
					<div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
						<div
							class={`max-w-[85%] rounded-2xl px-3 py-2 ${
								msg.role === 'user'
									? 'bg-[var(--color-accent)] text-white'
									: 'glass-subtle text-[var(--color-text-primary)]'
							}`}
						>
							<p class="text-sm whitespace-pre-wrap">{msg.content}</p>
							<p class={`text-xs mt-1 ${msg.role === 'user' ? 'text-white/70' : 'text-[var(--color-text-tertiary)]'}`}>
								{formatTime(msg.timestamp)}
							</p>
						</div>
					</div>
				{/each}

				{#if isSendingGeneral}
					<div class="flex justify-start">
						<div class="glass-subtle rounded-2xl px-3 py-2">
							<div class="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
								<span class="animate-pulse">●</span>
								<span class="animate-pulse delay-75">●</span>
								<span class="animate-pulse delay-150">●</span>
							</div>
						</div>
					</div>
				{/if}

				<div bind:this={messagesEndRef}></div>
			</div>

			<!-- General chat suggestions -->
			{#if generalSuggestions.length > 0}
				<div class="mt-4 pt-3 border-t border-[var(--glass-border-subtle)]">
					<p class="text-xs text-[var(--color-text-tertiary)] mb-2">Suggestions :</p>
					<div class="flex flex-wrap gap-1">
						{#each generalSuggestions as sug, i (sug)}
							<button
								onclick={() => handleSuggestionClick(sug)}
								class="px-2 py-1 text-xs rounded-full glass-subtle hover:glass transition-colors"
							>
								{sug}
							</button>
						{/each}
					</div>
				</div>
			{/if}

			<!-- General error display -->
			{#if generalError}
				<div class="mt-3 p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
					{generalError}
					<button onclick={() => generalError = null} class="ml-2 underline">Fermer</button>
				</div>
			{/if}
		{:else}
			<div class="text-center text-[var(--color-text-tertiary)] text-xs py-4">
				{#if isNoteChatMode && noteContext}
					<p class="mb-3">Discutons de <strong>{noteContext.title}</strong></p>
				{:else}
					<p class="mb-3">À votre service, Monsieur. Que puis-je faire ?</p>
				{/if}
			</div>

			<!-- Contextual suggestions -->
			<div class="space-y-1.5">
				<p class="text-xs text-[var(--color-text-tertiary)] mb-2">Suggestions :</p>
				{#each suggestions() as suggestion}
					<button
						type="button"
						onclick={() => handleSuggestionClick(suggestion.query)}
						class="w-full text-left px-3 py-2 rounded-xl
							glass-subtle hover:glass
							transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
							text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
							flex items-center gap-2 liquid-press"
					>
						<span>{suggestion.icon}</span>
						<span>{suggestion.label}</span>
					</button>
				{/each}
			</div>
		{/if}

		<!-- Error display -->
		{#if noteChatStore.error}
			<div class="mt-3 p-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
				{noteChatStore.error}
				<button onclick={() => noteChatStore.clearError()} class="ml-2 underline">Fermer</button>
			</div>
		{/if}

		<!-- Saved indicator -->
		{#if noteChatStore.discussionId}
			<div class="mt-3 p-2 rounded-lg glass-subtle text-xs text-[var(--color-text-tertiary)] flex items-center gap-2">
				<span>✓</span>
				<span>Conversation sauvegardée</span>
			</div>
		{/if}
	</div>

	<!-- Input area -->
	<div class="p-2 border-t border-[var(--glass-border-subtle)]">
		<div class="flex gap-1.5">
			<Input
				type="text"
				placeholder={isNoteChatMode ? 'Votre question...' : 'Vos instructions...'}
				bind:value={message}
				onkeydown={handleKeydown}
				class="flex-1 text-sm"
				name="chat-message"
				autocomplete="off"
				disabled={noteChatStore.sending || isSendingGeneral}
			/>
			<Button
				variant="primary"
				size="sm"
				onclick={handleSubmit}
				disabled={!message.trim() || noteChatStore.sending || isSendingGeneral}
			>
				<span aria-hidden="true">{noteChatStore.sending || isSendingGeneral ? '...' : '↑'}</span>
				<span class="sr-only">Envoyer</span>
			</Button>
		</div>
	</div>
</aside>

<!-- Mobile: Floating button + slide-up panel -->
<div class="lg:hidden">
	<!-- FAB -->
	{#if !isOpen}
		<button
			onclick={togglePanel}
			class="fixed right-4 z-50 w-14 h-14 rounded-full bg-[var(--color-accent)] text-white
				shadow-[0_4px_20px_rgba(0,122,255,0.4),inset_0_1px_0_rgba(255,255,255,0.2)]
				flex items-center justify-center text-xl liquid-press
				hover:shadow-[0_6px_28px_rgba(0,122,255,0.5)] hover:scale-105
				transition-all duration-[var(--transition-fast)] ease-[var(--spring-bouncy)]"
			style="bottom: calc(80px + var(--safe-area-bottom));"
			aria-label={isNoteChatMode ? 'Continuer la discussion' : 'Appeler Scapin'}
			aria-expanded={isOpen}
			aria-controls="mobile-chat-panel"
		>
			{#if isNoteChatMode}
				💬
			{:else}
				🎭
			{/if}
		</button>
	{/if}

	<!-- Slide-up panel -->
	{#if isOpen}
		<!-- Backdrop -->
		<button
			type="button"
			class="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
			onclick={closePanel}
			aria-label="Fermer le chat"
			tabindex="-1"
		></button>

		<!-- Panel -->
		<div
			bind:this={panelRef}
			id="mobile-chat-panel"
			role="dialog"
			aria-modal="true"
			aria-labelledby="chat-panel-title"
			tabindex="-1"
			class="fixed bottom-0 left-0 right-0 glass-prominent rounded-t-3xl z-50 max-h-[80vh] flex flex-col"
			style="padding-bottom: var(--safe-area-bottom);"
			onkeydown={handlePanelKeydown}
		>
			<!-- Handle -->
			<div class="flex justify-center py-3" aria-hidden="true">
				<div class="w-10 h-1 bg-[var(--color-border)] rounded-full"></div>
			</div>

			<!-- Header -->
			<div class="px-4 pb-3 flex items-center justify-between">
				<div class="flex items-center gap-2 flex-1 min-w-0">
					{#if isNoteChatMode && noteContext}
						<h2 id="chat-panel-title" class="font-semibold truncate">{noteContext.title}</h2>
					{:else}
						<h2 id="chat-panel-title" class="font-semibold">Scapin</h2>
						<span class="w-2 h-2 rounded-full bg-[var(--color-success)]" title="À l'écoute"></span>
					{/if}
				</div>
				<div class="flex items-center gap-1">
					{#if isNoteChatMode}
						{#if noteChatStore.canSaveAsDiscussion}
							<button
								onclick={handleSaveAsDiscussion}
								class="p-2 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
								title="Sauvegarder"
								disabled={noteChatStore.saving}
							>
								{noteChatStore.saving ? '⏳' : '💾'}
							</button>
						{/if}
						{#if noteChatStore.hasMessages}
							<button
								onclick={handleClearConversation}
								class="p-2 rounded-lg hover:bg-[var(--glass-tint)] transition-colors"
								title="Effacer"
							>
								🗑️
							</button>
						{/if}
					{/if}
					<button
						type="button"
						onclick={closePanel}
						class="text-[var(--color-text-tertiary)] touch-target flex items-center justify-center"
						aria-label="Fermer"
					>
						✕
					</button>
				</div>
			</div>

			<!-- Messages + Suggestions -->
			<div class="flex-1 p-4 overflow-y-auto min-h-[200px]" role="log" aria-live="polite">
				{#if isNoteChatMode && noteChatStore.hasMessages}
					<!-- Chat messages -->
					<div class="space-y-3">
						{#each noteChatStore.messages as msg (msg.id)}
							<div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
								<div
									class={`max-w-[85%] rounded-2xl px-4 py-2 ${
										msg.role === 'user'
											? 'bg-[var(--color-accent)] text-white'
											: 'glass text-[var(--color-text-primary)]'
									}`}
								>
									<p class="text-sm whitespace-pre-wrap">{msg.content}</p>
									<p class={`text-xs mt-1 ${msg.role === 'user' ? 'text-white/70' : 'text-[var(--color-text-tertiary)]'}`}>
										{formatTime(msg.timestamp)}
									</p>
								</div>
							</div>
						{/each}

						{#if noteChatStore.sending}
							<div class="flex justify-start">
								<div class="glass rounded-2xl px-4 py-2">
									<div class="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
										<span class="animate-pulse">●</span>
										<span class="animate-pulse delay-75">●</span>
										<span class="animate-pulse delay-150">●</span>
									</div>
								</div>
							</div>
						{/if}

						<div bind:this={messagesEndRef}></div>
					</div>

					<!-- AI Suggestions -->
					{#if noteChatStore.suggestions.length > 0}
						<div class="mt-4 pt-3 border-t border-[var(--glass-border-subtle)]">
							<div class="flex flex-wrap gap-2">
								{#each noteChatStore.suggestions as sug, i (sug.content)}
									<button
										onclick={() => handleSuggestionClick(sug.content)}
										class="px-3 py-1.5 text-sm rounded-full glass hover:glass-prominent transition-colors"
									>
										{sug.content}
									</button>
								{/each}
							</div>
						</div>
					{/if}
				{:else}
					<div class="text-center text-[var(--color-text-tertiary)] text-sm mb-4">
						{#if isNoteChatMode && noteContext}
							<p>Discutons de <strong>{noteContext.title}</strong></p>
						{:else}
							<p>À votre service, Monsieur. Que puis-je faire ?</p>
						{/if}
					</div>

					<!-- Contextual suggestions -->
					<div class="space-y-2">
						{#each suggestions() as suggestion}
							<button
								type="button"
								onclick={() => handleSuggestionClick(suggestion.query)}
								class="w-full text-left px-4 py-3 rounded-xl
									glass hover:glass-prominent
									transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
									text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
									flex items-center gap-3 liquid-press"
							>
								<span class="text-lg">{suggestion.icon}</span>
								<span>{suggestion.label}</span>
							</button>
						{/each}
					</div>
				{/if}

				<!-- Error display -->
				{#if noteChatStore.error}
					<div class="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
						{noteChatStore.error}
						<button onclick={() => noteChatStore.clearError()} class="ml-2 underline">Fermer</button>
					</div>
				{/if}

				<!-- Saved indicator -->
				{#if noteChatStore.discussionId}
					<div class="mt-3 p-3 rounded-lg glass text-sm text-[var(--color-text-tertiary)] flex items-center gap-2">
						<span>✓</span>
						<span>Conversation sauvegardée</span>
					</div>
				{/if}
			</div>

			<!-- Input -->
			<div class="p-4 border-t border-[var(--glass-border-subtle)]">
				<div class="flex gap-2">
					<Input
						type="text"
						placeholder={isNoteChatMode ? 'Votre question...' : 'Vos instructions...'}
						bind:value={message}
						bind:inputRef={mobileInputRef}
						onkeydown={handleKeydown}
						class="flex-1"
						name="chat-message-mobile"
						autocomplete="off"
						disabled={noteChatStore.sending || isSendingGeneral}
					/>
					<Button
						variant="primary"
						onclick={handleSubmit}
						disabled={!message.trim() || noteChatStore.sending || isSendingGeneral}
					>
						<span aria-hidden="true">{noteChatStore.sending || isSendingGeneral ? '...' : '↑'}</span>
						<span class="sr-only">Envoyer</span>
					</Button>
				</div>
			</div>
		</div>
	{/if}
</div>
