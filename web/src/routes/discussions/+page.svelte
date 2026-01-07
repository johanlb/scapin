<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Badge, Button, Skeleton, Modal } from '$lib/components/ui';
	import { discussionsStore } from '$lib/stores/discussions.svelte';
	import type { Discussion, DiscussionType } from '$lib/api';

	// Local state for create modal
	let showCreateModal = $state(false);
	let newDiscussionTitle = $state('');
	let newDiscussionMessage = $state('');
	let newDiscussionType = $state<DiscussionType>('free');

	// Selected discussion for detail view
	let selectedDiscussion = $state<Discussion | null>(null);
	let messageInput = $state('');

	onMount(() => {
		discussionsStore.fetchDiscussions(true);
	});

	function formatTime(isoString: string): string {
		const date = new Date(isoString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.round(diffMs / (1000 * 60));

		if (diffMins < 60) return `${diffMins} min`;
		const hours = Math.round(diffMins / 60);
		if (hours < 24) return `${hours}h`;
		return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
	}

	function getTypeLabel(type: DiscussionType): string {
		const labels: Record<DiscussionType, string> = {
			free: 'Libre',
			note: 'Note',
			email: 'Email',
			task: 'Tâche',
			event: 'Événement'
		};
		return labels[type] || type;
	}

	function getTypeIcon(type: DiscussionType): string {
		const icons: Record<DiscussionType, string> = {
			free: '💬',
			note: '📝',
			email: '📧',
			task: '✅',
			event: '📅'
		};
		return icons[type] || '💬';
	}

	async function handleCreateDiscussion() {
		if (!newDiscussionMessage.trim()) return;

		const result = await discussionsStore.create({
			title: newDiscussionTitle.trim() || undefined,
			discussion_type: newDiscussionType,
			initial_message: newDiscussionMessage.trim()
		});

		if (result) {
			showCreateModal = false;
			newDiscussionTitle = '';
			newDiscussionMessage = '';
			newDiscussionType = 'free';
			// Select the new discussion
			selectedDiscussion = {
				id: result.id,
				title: result.title,
				discussion_type: result.discussion_type,
				attached_to_id: result.attached_to_id,
				attached_to_type: result.attached_to_type,
				created_at: result.created_at,
				updated_at: result.updated_at,
				message_count: result.message_count,
				last_message_preview: result.last_message_preview,
				metadata: result.metadata
			};
		}
	}

	function handleSelectDiscussion(discussion: Discussion) {
		selectedDiscussion = discussion;
		discussionsStore.selectDiscussion(discussion);
	}

	function handleCloseDetail() {
		selectedDiscussion = null;
		discussionsStore.clearCurrent();
	}

	async function handleSendMessage() {
		if (!messageInput.trim() || !selectedDiscussion) return;

		const content = messageInput.trim();
		messageInput = '';
		await discussionsStore.sendMessage(selectedDiscussion.id, content);
	}

	async function handleDeleteDiscussion(discussionId: string) {
		if (confirm('Supprimer cette discussion ?')) {
			const success = await discussionsStore.remove(discussionId);
			if (success && selectedDiscussion?.id === discussionId) {
				selectedDiscussion = null;
			}
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSendMessage();
		}
	}
</script>

<div class="p-4 md:p-6 max-w-6xl mx-auto">
	<header class="mb-6 flex items-center justify-between">
		<div>
			<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
				Conversations
			</h1>
			<p class="text-[var(--color-text-secondary)] mt-1">
				Vos échanges avec Scapin
			</p>
		</div>
		<Button variant="primary" onclick={() => (showCreateModal = true)}>
			+ Nouvelle
		</Button>
	</header>

	{#if discussionsStore.error}
		<div class="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
			<p>{discussionsStore.error}</p>
			<Button
				variant="ghost"
				size="sm"
				onclick={() => {
					discussionsStore.clearError();
					discussionsStore.fetchDiscussions(true);
				}}
			>
				Réessayer
			</Button>
		</div>
	{/if}

	<div class="flex flex-col md:flex-row gap-6">
		<!-- Discussions List -->
		<section class="flex-1 space-y-3">
			{#if discussionsStore.loading && discussionsStore.discussions.length === 0}
				<!-- Loading skeletons -->
				{#each Array(3) as _}
					<Card padding="lg">
						<div class="flex items-center gap-4">
							<div class="flex-1">
								<Skeleton variant="text" class="w-24 mb-2" />
								<Skeleton variant="text" class="w-48 mb-1" />
								<Skeleton variant="text" class="w-64" />
							</div>
						</div>
					</Card>
				{/each}
			{:else if discussionsStore.isEmpty}
				<Card padding="lg" class="text-center">
					<div class="py-8">
						<p class="text-4xl mb-4">💬</p>
						<p class="text-[var(--color-text-secondary)] mb-4">
							Aucune discussion pour le moment
						</p>
						<Button variant="primary" onclick={() => (showCreateModal = true)}>
							Démarrer une conversation
						</Button>
					</div>
				</Card>
			{:else}
				{#each discussionsStore.discussions as discussion (discussion.id)}
					<Card
						interactive
						onclick={() => handleSelectDiscussion(discussion)}
						padding="lg"
						class={selectedDiscussion?.id === discussion.id ? 'ring-2 ring-[var(--color-accent)]' : ''}
					>
						<div class="flex items-center gap-4">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<span class="text-lg">{getTypeIcon(discussion.discussion_type)}</span>
									<span
										class="px-2 py-0.5 text-xs rounded-full bg-[var(--color-surface-elevated)] text-[var(--color-text-secondary)]"
									>
										{getTypeLabel(discussion.discussion_type)}
									</span>
									<span class="text-sm text-[var(--color-text-tertiary)]">
										{formatTime(discussion.updated_at)}
									</span>
								</div>
								<h3 class="text-lg font-semibold text-[var(--color-text-primary)]">
									{discussion.title || 'Discussion sans titre'}
								</h3>
								{#if discussion.last_message_preview}
									<p class="text-[var(--color-text-secondary)] truncate">
										{discussion.last_message_preview}
									</p>
								{/if}
								<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
									{discussion.message_count} message{discussion.message_count !== 1 ? 's' : ''}
								</p>
							</div>
							<span class="text-xl text-[var(--color-text-tertiary)]">→</span>
						</div>
					</Card>
				{/each}

				{#if discussionsStore.hasMore}
					<div class="text-center py-4">
						<Button
							variant="ghost"
							onclick={() => discussionsStore.loadMore()}
							disabled={discussionsStore.loading}
						>
							{discussionsStore.loading ? 'Chargement...' : 'Voir plus'}
						</Button>
					</div>
				{/if}
			{/if}
		</section>

		<!-- Discussion Detail Panel -->
		{#if selectedDiscussion}
			<section
				class="md:w-[400px] lg:w-[500px] flex flex-col bg-[var(--color-surface)] rounded-2xl border border-[var(--color-border)] overflow-hidden max-h-[calc(100vh-200px)]"
			>
				<!-- Header -->
				<div
					class="p-4 border-b border-[var(--color-border)] flex items-center justify-between bg-[var(--color-surface-elevated)]"
				>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<span class="text-lg">{getTypeIcon(selectedDiscussion.discussion_type)}</span>
							<h2 class="font-semibold text-[var(--color-text-primary)] truncate">
								{selectedDiscussion.title || 'Discussion sans titre'}
							</h2>
						</div>
					</div>
					<div class="flex items-center gap-2">
						<button
							onclick={() => handleDeleteDiscussion(selectedDiscussion!.id)}
							class="p-2 text-[var(--color-text-tertiary)] hover:text-red-400 transition-colors"
							title="Supprimer"
						>
							🗑️
						</button>
						<button
							onclick={handleCloseDetail}
							class="p-2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] transition-colors md:hidden"
						>
							✕
						</button>
					</div>
				</div>

				<!-- Messages -->
				<div class="flex-1 overflow-y-auto p-4 space-y-4">
					{#if discussionsStore.loadingDetail}
						<div class="flex justify-center py-8">
							<Skeleton variant="circular" class="w-8 h-8" />
						</div>
					{:else if discussionsStore.currentMessages.length === 0}
						<p class="text-center text-[var(--color-text-tertiary)] py-8">
							Aucun message
						</p>
					{:else}
						{#each discussionsStore.currentMessages as message (message.id)}
							<div
								class={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
							>
								<div
									class={`max-w-[85%] rounded-2xl px-4 py-2 ${
										message.role === 'user'
											? 'bg-[var(--color-accent)] text-white'
											: 'bg-[var(--color-surface-elevated)] text-[var(--color-text-primary)]'
									}`}
								>
									<p class="whitespace-pre-wrap">{message.content}</p>
									<p
										class={`text-xs mt-1 ${
											message.role === 'user'
												? 'text-white/70'
												: 'text-[var(--color-text-tertiary)]'
										}`}
									>
										{formatTime(message.created_at)}
									</p>
								</div>
							</div>
						{/each}
					{/if}
				</div>

				<!-- Suggestions -->
				{#if discussionsStore.currentSuggestions.length > 0}
					<div
						class="px-4 py-2 border-t border-[var(--color-border)] flex flex-wrap gap-2"
					>
						{#each discussionsStore.currentSuggestions as suggestion}
							<button
								onclick={() => {
									messageInput = suggestion.content;
								}}
								class="px-3 py-1 text-sm bg-[var(--color-surface-elevated)] hover:bg-[var(--color-surface)] rounded-full text-[var(--color-text-secondary)] transition-colors"
							>
								{suggestion.content}
							</button>
						{/each}
					</div>
				{/if}

				<!-- Input -->
				<div class="p-4 border-t border-[var(--color-border)]">
					<div class="flex gap-2">
						<textarea
							bind:value={messageInput}
							onkeydown={handleKeydown}
							placeholder="Votre message..."
							rows="2"
							class="flex-1 px-4 py-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-xl text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
						></textarea>
						<Button
							variant="primary"
							onclick={handleSendMessage}
							disabled={!messageInput.trim() || discussionsStore.sending}
						>
							{discussionsStore.sending ? '...' : '↑'}
						</Button>
					</div>
				</div>
			</section>
		{/if}
	</div>
</div>

<!-- Create Discussion Modal -->
<Modal
	open={showCreateModal}
	onclose={() => (showCreateModal = false)}
	title="Nouvelle discussion"
	size="md"
>
	<div class="space-y-4">
		<div>
			<label for="discussion-type" class="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
				Type
			</label>
			<select
				id="discussion-type"
				bind:value={newDiscussionType}
				class="w-full px-4 py-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-xl text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
			>
				<option value="free">Libre</option>
				<option value="note">À propos d'une note</option>
				<option value="email">À propos d'un email</option>
				<option value="task">À propos d'une tâche</option>
				<option value="event">À propos d'un événement</option>
			</select>
		</div>

		<div>
			<label for="discussion-title" class="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
				Titre (optionnel)
			</label>
			<input
				id="discussion-title"
				type="text"
				bind:value={newDiscussionTitle}
				placeholder="Ex: Question sur le projet X"
				class="w-full px-4 py-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-xl text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
			/>
		</div>

		<div>
			<label for="discussion-message" class="block text-sm font-medium text-[var(--color-text-secondary)] mb-1">
				Message
			</label>
			<textarea
				id="discussion-message"
				bind:value={newDiscussionMessage}
				placeholder="Commencez la conversation..."
				rows="4"
				class="w-full px-4 py-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-xl text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
			></textarea>
		</div>

		<div class="flex justify-end gap-2 pt-4">
			<Button variant="ghost" onclick={() => (showCreateModal = false)}>
				Annuler
			</Button>
			<Button
				variant="primary"
				onclick={handleCreateDiscussion}
				disabled={!newDiscussionMessage.trim() || discussionsStore.creating}
			>
				{discussionsStore.creating ? 'Création...' : 'Créer'}
			</Button>
		</div>
	</div>
</Modal>
