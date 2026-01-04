<script lang="ts">
	import { page } from '$app/stores';
	import { Button, Input } from '$lib/components/ui';
	import { haptic } from '$lib/utils/haptics';

	let message = $state('');
	let isOpen = $state(false);
	let panelRef: HTMLDivElement | null = $state(null);
	let mobileInputRef: HTMLInputElement | null = $state(null);

	// Contextual suggestions based on current page
	interface Suggestion {
		label: string;
		query: string;
		icon: string;
	}

	const pageSuggestions: Record<string, Suggestion[]> = {
		'/': [
			{ label: 'Résumer ma journée', query: 'Résume les éléments importants de ma journée', icon: '📋' },
			{ label: 'Préparer réunion', query: 'Aide-moi à préparer ma prochaine réunion', icon: '🎯' },
			{ label: 'Emails urgents', query: 'Quels emails nécessitent une réponse urgente ?', icon: '⚡' }
		],
		'/flux': [
			{ label: 'Filtrer par urgence', query: 'Montre-moi uniquement les éléments urgents', icon: '🔴' },
			{ label: 'Archiver traités', query: 'Archive les éléments que j\'ai traités', icon: '📦' },
			{ label: 'Résumer non lus', query: 'Résume les messages non lus', icon: '📨' }
		],
		'/notes': [
			{ label: 'Chercher note', query: 'Cherche dans mes notes...', icon: '🔍' },
			{ label: 'Créer note', query: 'Crée une nouvelle note sur...', icon: '✏️' },
			{ label: 'Résumer projet', query: 'Résume les notes du projet...', icon: '📑' }
		],
		'/settings': [
			{ label: 'Vérifier connexions', query: 'Vérifie l\'état de mes intégrations', icon: '🔗' },
			{ label: 'Optimiser', query: 'Comment optimiser mes paramètres ?', icon: '⚙️' }
		]
	};

	const defaultSuggestions: Suggestion[] = [
		{ label: 'Aide', query: 'Que peux-tu faire pour m\'aider ?', icon: '❓' },
		{ label: 'Briefing', query: 'Donne-moi un résumé de la situation', icon: '📊' }
	];

	let suggestions = $derived(
		pageSuggestions[$page.url.pathname] || defaultSuggestions
	);

	function togglePanel() {
		isOpen = !isOpen;
		haptic('light');

		if (isOpen) {
			requestAnimationFrame(() => {
				mobileInputRef?.focus();
			});
		}
	}

	function closePanel() {
		isOpen = false;
		haptic('light');
	}

	function handleSubmit() {
		if (message.trim()) {
			haptic('medium');
			// TODO: Send message to API
			console.log('Sending:', message);
			message = '';
		}
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
</script>

<!-- Desktop: Fixed right panel -->
<aside
	class="fixed right-0 top-0 h-full w-72 bg-[var(--color-bg-secondary)] border-l border-[var(--color-border-light)] hidden lg:flex flex-col z-40"
	aria-label="Assistant Scapin"
>
	<!-- Header -->
	<div class="px-3 py-2.5 border-b border-[var(--color-border-light)] flex items-center gap-2">
		<span class="text-lg">🎭</span>
		<div class="flex-1">
			<h2 class="text-sm font-semibold text-[var(--color-text-primary)]">Assistant Scapin</h2>
		</div>
		<span class="w-2 h-2 rounded-full bg-[var(--color-success)]" title="Connecté"></span>
	</div>

	<!-- Messages area -->
	<div class="flex-1 p-3 overflow-y-auto" role="log" aria-live="polite">
		<div class="text-center text-[var(--color-text-tertiary)] text-xs py-4">
			<p class="mb-3">👋 Comment puis-je vous aider ?</p>
		</div>

		<!-- Contextual suggestions -->
		<div class="space-y-1.5">
			<p class="text-xs text-[var(--color-text-tertiary)] mb-2">Suggestions :</p>
			{#each suggestions as suggestion}
				<button
					type="button"
					onclick={() => handleSuggestionClick(suggestion.query)}
					class="w-full text-left px-3 py-2 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-primary)] border border-transparent hover:border-[var(--color-border)] transition-all text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-2"
				>
					<span>{suggestion.icon}</span>
					<span>{suggestion.label}</span>
				</button>
			{/each}
		</div>
	</div>

	<!-- Input area -->
	<div class="p-2 border-t border-[var(--color-border-light)]">
		<div class="flex gap-1.5">
			<Input
				type="text"
				placeholder="Votre message..."
				bind:value={message}
				onkeydown={handleKeydown}
				class="flex-1 text-sm"
				name="chat-message"
				autocomplete="off"
			/>
			<Button variant="primary" size="sm" onclick={handleSubmit} disabled={!message.trim()}>
				<span aria-hidden="true">↑</span>
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
			class="fixed right-4 z-50 w-14 h-14 rounded-full bg-[var(--color-accent)] text-white shadow-lg flex items-center justify-center text-xl touch-active"
			style="bottom: calc(80px + var(--safe-area-bottom));"
			aria-label="Ouvrir le chat"
			aria-expanded={isOpen}
			aria-controls="mobile-chat-panel"
		>
			💬
		</button>
	{/if}

	<!-- Slide-up panel -->
	{#if isOpen}
		<!-- Backdrop -->
		<button
			type="button"
			class="fixed inset-0 bg-black/40 z-40"
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
			class="fixed bottom-0 left-0 right-0 bg-[var(--color-bg-primary)] rounded-t-3xl z-50 max-h-[80vh] flex flex-col"
			style="padding-bottom: var(--safe-area-bottom);"
			onkeydown={handlePanelKeydown}
		>
			<!-- Handle -->
			<div class="flex justify-center py-3" aria-hidden="true">
				<div class="w-10 h-1 bg-[var(--color-border)] rounded-full"></div>
			</div>

			<!-- Header -->
			<div class="px-4 pb-3 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<h2 id="chat-panel-title" class="font-semibold">Assistant Scapin</h2>
					<span class="w-2 h-2 rounded-full bg-[var(--color-success)]" title="Connecté"></span>
				</div>
				<button
					type="button"
					onclick={closePanel}
					class="text-[var(--color-text-tertiary)] touch-target flex items-center justify-center"
					aria-label="Fermer"
				>
					✕
				</button>
			</div>

			<!-- Messages + Suggestions -->
			<div class="flex-1 p-4 overflow-y-auto min-h-[200px]" role="log" aria-live="polite">
				<div class="text-center text-[var(--color-text-tertiary)] text-sm mb-4">
					<p>👋 Comment puis-je vous aider ?</p>
				</div>

				<!-- Contextual suggestions -->
				<div class="space-y-2">
					{#each suggestions as suggestion}
						<button
							type="button"
							onclick={() => handleSuggestionClick(suggestion.query)}
							class="w-full text-left px-4 py-3 rounded-xl bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] border border-[var(--color-border-light)] transition-all text-sm text-[var(--color-text-secondary)] flex items-center gap-3"
						>
							<span class="text-lg">{suggestion.icon}</span>
							<span>{suggestion.label}</span>
						</button>
					{/each}
				</div>
			</div>

			<!-- Input -->
			<div class="p-4 border-t border-[var(--color-border-light)]">
				<div class="flex gap-2">
					<Input
						type="text"
						placeholder="Votre message..."
						bind:value={message}
						bind:inputRef={mobileInputRef}
						onkeydown={handleKeydown}
						class="flex-1"
						name="chat-message-mobile"
						autocomplete="off"
					/>
					<Button variant="primary" onclick={handleSubmit} disabled={!message.trim()}>
						<span aria-hidden="true">↑</span>
						<span class="sr-only">Envoyer</span>
					</Button>
				</div>
			</div>
		</div>
	{/if}
</div>
