<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui';
	import { queueStore, notificationCenterStore } from '$lib/stores';
	import { approveQueueItem, rejectQueueItem, snoozeQueueItem } from '$lib/api';
	import type { QueueItem, ActionOption, SnoozeOption } from '$lib/api';

	// Focus mode filters
	type FocusFilter = 'all' | 'high-priority' | 'urgent';
	let activeFilter: FocusFilter = $state('all');
	let showFilterMenu: boolean = $state(false);

	let currentIndex: number = $state(0);
	let isProcessing: boolean = $state(false);
	let showLevel3: boolean = $state(false);
	let processedCount: number = $state(0);
	let sessionStartTime: Date = $state(new Date());
	let showExitConfirm: boolean = $state(false);
	let showSnoozeMenu: boolean = $state(false);
	let isSnoozing: boolean = $state(false);

	// Snooze options
	const snoozeOptions: { value: SnoozeOption; label: string }[] = [
		{ value: 'in_30_min', label: '30 minutes' },
		{ value: 'in_2_hours', label: '2 heures' },
		{ value: 'tomorrow', label: 'Demain matin' },
		{ value: 'next_week', label: 'Semaine prochaine' }
	];

	// Filter items based on priority/urgency
	const filteredItems = $derived(() => {
		const items = queueStore.items;
		if (activeFilter === 'all') return items;

		return items.filter((item) => {
			const confidence = item.analysis.confidence;
			const category = item.analysis.category?.toLowerCase() || '';

			if (activeFilter === 'high-priority') {
				// High priority: low confidence (needs attention) or work category
				return confidence < 70 || category === 'work';
			}

			if (activeFilter === 'urgent') {
				// Urgent: very low confidence or has deadline entities
				const hasDateEntity = item.analysis.entities?.date?.length > 0;
				return confidence < 50 || hasDateEntity;
			}

			return true;
		});
	});

	// Track if notifications were paused by us
	let notificationsPausedByUs = false;

	// Load queue on mount
	onMount(async () => {
		await queueStore.fetchQueue('pending');
		await queueStore.fetchStats();
		document.addEventListener('keydown', handleKeyboard);
		// Hide layout elements
		document.body.classList.add('focus-mode-active');
		// Pause notifications in focus mode
		if (!notificationCenterStore.isPaused) {
			notificationCenterStore.pauseNotifications();
			notificationsPausedByUs = true;
		}
	});

	onDestroy(() => {
		document.removeEventListener('keydown', handleKeyboard);
		document.body.classList.remove('focus-mode-active');
		// Resume notifications if we paused them
		if (notificationsPausedByUs) {
			notificationCenterStore.resumeNotifications();
		}
	});

	// Use filtered items for current item
	const items = $derived(filteredItems());
	const currentItem = $derived(
		items.length > 0 ? items[currentIndex] || null : null
	);

	const sessionDuration = $derived(() => {
		const now = new Date();
		const diff = now.getTime() - sessionStartTime.getTime();
		const minutes = Math.floor(diff / 60000);
		const seconds = Math.floor((diff % 60000) / 1000);
		return `${minutes}:${seconds.toString().padStart(2, '0')}`;
	});

	const progress = $derived(
		items.length > 0
			? Math.round((processedCount / (processedCount + items.length)) * 100)
			: 100
	);

	const filterLabel = $derived({
		'all': 'Tous',
		'high-priority': 'Prioritaires',
		'urgent': 'Urgents'
	}[activeFilter]);

	function handleKeyboard(e: KeyboardEvent) {
		// Don't handle if processing or in exit confirm
		if (isProcessing || showExitConfirm) {
			if (e.key === 'Escape' && showExitConfirm) {
				showExitConfirm = false;
			}
			return;
		}

		// Close menus on Escape
		if (e.key === 'Escape') {
			if (showSnoozeMenu) {
				showSnoozeMenu = false;
				return;
			}
			if (showFilterMenu) {
				showFilterMenu = false;
				return;
			}
			showExitConfirm = true;
			return;
		}

		if (!currentItem) return;

		const options = currentItem.analysis.options || [];

		switch (e.key) {
			case '1':
				if (options[0]) handleSelectOption(currentItem, options[0]);
				break;
			case '2':
				if (options[1]) handleSelectOption(currentItem, options[1]);
				break;
			case '3':
				if (options[2]) handleSelectOption(currentItem, options[2]);
				break;
			case 'n':
			case 'N':
				// N for Next (skip)
				handleSkip();
				break;
			case 'z':
			case 'Z':
				// Z for snooZe
				showSnoozeMenu = !showSnoozeMenu;
				break;
			case 'd':
			case 'D':
				handleDelete(currentItem);
				break;
			case 'r':
			case 'R':
				handleReject(currentItem);
				break;
			case 'v':
			case 'V':
				showLevel3 = !showLevel3;
				break;
			case 'f':
			case 'F':
				// F for Filter
				showFilterMenu = !showFilterMenu;
				break;
		}
	}

	async function handleSelectOption(item: QueueItem, option: ActionOption) {
		if (isProcessing) return;
		isProcessing = true;

		try {
			await approveQueueItem(item.id, option.action, item.analysis.category || undefined, option.destination);
			queueStore.removeFromList(item.id);
			processedCount++;

			// Move to next or reset (using items.length for filtered view)
			if (currentIndex >= items.length - 1) {
				currentIndex = Math.max(0, items.length - 2);
			}
		} finally {
			isProcessing = false;
		}
	}

	async function handleReject(item: QueueItem) {
		if (isProcessing) return;
		isProcessing = true;

		try {
			await rejectQueueItem(item.id);
			queueStore.removeFromList(item.id);
			processedCount++;

			if (currentIndex >= items.length - 1) {
				currentIndex = Math.max(0, items.length - 2);
			}
		} finally {
			isProcessing = false;
		}
	}

	async function handleDelete(item: QueueItem) {
		if (isProcessing) return;
		isProcessing = true;

		try {
			await approveQueueItem(item.id, 'delete', item.analysis.category || undefined);
			queueStore.removeFromList(item.id);
			processedCount++;

			if (currentIndex >= items.length - 1) {
				currentIndex = Math.max(0, items.length - 2);
			}
		} finally {
			isProcessing = false;
		}
	}

	async function handleSnooze(option: SnoozeOption) {
		if (!currentItem || isSnoozing) return;
		isSnoozing = true;
		showSnoozeMenu = false;

		try {
			await snoozeQueueItem(currentItem.id, option);
			queueStore.removeFromList(currentItem.id);
			processedCount++;

			if (currentIndex >= items.length - 1) {
				currentIndex = Math.max(0, items.length - 2);
			}
		} catch (e) {
			console.error('Snooze failed:', e);
		} finally {
			isSnoozing = false;
		}
	}

	function handleSkip() {
		if (currentIndex < items.length - 1) {
			currentIndex++;
		} else {
			currentIndex = 0;
		}
	}

	function setFilter(filter: FocusFilter) {
		activeFilter = filter;
		currentIndex = 0;
		showFilterMenu = false;
	}

	function exitFocusMode() {
		goto('/peripeties');
	}

	function getActionLabel(action: string): string {
		const labels: Record<string, string> = {
			archive: 'Classer',
			delete: 'Supprimer',
			reply: 'Répondre',
			task: 'Créer tâche',
			defer: 'Reporter'
		};
		return labels[action] || action;
	}

	function getActionIcon(action: string): string {
		const icons: Record<string, string> = {
			archive: '📥',
			delete: '🗑️',
			reply: '✉️',
			task: '✅',
			defer: '⏰'
		};
		return icons[action] || '❓';
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 90) return 'var(--color-success)';
		if (confidence >= 70) return 'var(--color-warning)';
		return 'var(--color-urgency-urgent)';
	}
</script>

<svelte:head>
	<title>Mode Focus — Scapin</title>
</svelte:head>

<!-- Exit confirmation overlay -->
{#if showExitConfirm}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
		role="dialog"
		aria-modal="true"
		aria-labelledby="exit-dialog-title"
	>
		<div class="bg-[var(--color-bg-primary)] p-6 rounded-2xl max-w-md text-center">
			<h2 id="exit-dialog-title" class="text-xl font-bold text-[var(--color-text-primary)] mb-2">
				Quitter le mode Focus ?
			</h2>
			<p class="text-[var(--color-text-secondary)] mb-4">
				Vous avez traité {processedCount} pli{processedCount !== 1 ? 's' : ''} en {sessionDuration()}.
				{#if queueStore.items.length > 0}
					Il reste {queueStore.items.length} pli{queueStore.items.length !== 1 ? 's' : ''} à traiter.
				{/if}
			</p>
			<div class="flex gap-3 justify-center">
				<Button variant="secondary" onclick={() => showExitConfirm = false}>
					Continuer
				</Button>
				<Button variant="primary" onclick={exitFocusMode}>
					Quitter
				</Button>
			</div>
		</div>
	</div>
{/if}

<div class="fixed inset-0 bg-[var(--color-bg-primary)] flex flex-col z-40">
	<!-- Minimal header -->
	<header class="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)]">
		<div class="flex items-center gap-4">
			<span class="text-2xl">🎭</span>
			<div>
				<h1 class="font-bold text-[var(--color-text-primary)]">Mode Focus</h1>
				<p class="text-xs text-[var(--color-text-tertiary)]">
					{processedCount} traité{processedCount !== 1 ? 's' : ''} • {sessionDuration()}
				</p>
			</div>
		</div>

		<!-- Filter dropdown + Progress -->
		<div class="flex items-center gap-4">
			<!-- Filter dropdown -->
			<div class="relative">
				<button
					type="button"
					class="px-3 py-1.5 rounded-lg text-sm font-medium bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-colors flex items-center gap-2"
					onclick={() => showFilterMenu = !showFilterMenu}
					aria-haspopup="true"
					aria-expanded={showFilterMenu}
				>
					<span class="text-[var(--color-text-secondary)]">Filtre:</span>
					<span class="text-[var(--color-text-primary)]">{filterLabel}</span>
					<span class="text-xs opacity-60">▼</span>
				</button>

				{#if showFilterMenu}
					<div class="absolute right-0 mt-2 w-48 py-1 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] shadow-xl z-50">
						<button
							type="button"
							class="w-full px-4 py-2 text-left text-sm hover:bg-[var(--color-bg-tertiary)] transition-colors {activeFilter === 'all' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-primary)]'}"
							onclick={() => setFilter('all')}
						>
							Toutes les péripéties
						</button>
						<button
							type="button"
							class="w-full px-4 py-2 text-left text-sm hover:bg-[var(--color-bg-tertiary)] transition-colors {activeFilter === 'high-priority' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-primary)]'}"
							onclick={() => setFilter('high-priority')}
						>
							⚡ Prioritaires
						</button>
						<button
							type="button"
							class="w-full px-4 py-2 text-left text-sm hover:bg-[var(--color-bg-tertiary)] transition-colors {activeFilter === 'urgent' ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-primary)]'}"
							onclick={() => setFilter('urgent')}
						>
							🔴 Urgents
						</button>
					</div>
				{/if}
			</div>

			<div class="text-right">
				<p class="text-sm font-medium text-[var(--color-text-primary)]">
					{items.length} restant{items.length !== 1 ? 's' : ''}
					{#if activeFilter !== 'all'}
						<span class="text-[var(--color-text-tertiary)]">({queueStore.items.length} total)</span>
					{/if}
				</p>
				<div class="w-32 h-2 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
					<div
						class="h-full bg-[var(--color-success)] transition-all duration-300"
						style="width: {progress}%"
					></div>
				</div>
			</div>

			<Button variant="secondary" size="sm" onclick={() => showExitConfirm = true}>
				<span class="mr-1">✕</span> Quitter
				<span class="ml-1 text-xs opacity-60 font-mono">Esc</span>
			</Button>
		</div>
	</header>

	<!-- Main content -->
	<main class="flex-1 overflow-y-auto p-6 lg:p-12">
		{#if queueStore.loading && queueStore.items.length === 0}
			<!-- Loading state -->
			<div class="h-full flex items-center justify-center">
				<div class="text-center">
					<div class="w-12 h-12 border-3 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
					<p class="text-[var(--color-text-secondary)]">Chargement des péripéties...</p>
				</div>
			</div>

		{:else if queueStore.items.length === 0}
			<!-- Empty state - All done! -->
			<div class="h-full flex items-center justify-center">
				<div class="text-center max-w-md">
					<span class="text-6xl block mb-6">🎉</span>
					<h2 class="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
						Félicitations !
					</h2>
					<p class="text-[var(--color-text-secondary)] mb-2">
						Toutes les péripéties ont été traitées.
					</p>
					<p class="text-sm text-[var(--color-text-tertiary)] mb-6">
						{processedCount} péripétie{processedCount !== 1 ? 's' : ''} traitée{processedCount !== 1 ? 's' : ''} en {sessionDuration()}
					</p>
					<Button variant="primary" onclick={exitFocusMode}>
						Retourner au tableau de bord
					</Button>
				</div>
			</div>

		{:else if currentItem}
			{@const options = currentItem.analysis.options || []}

			<div class="max-w-3xl mx-auto space-y-6">
				<!-- Email header - Large and prominent -->
				<div class="text-center">
					<h2 class="text-2xl lg:text-3xl font-bold text-[var(--color-text-primary)] mb-3">
						{currentItem.metadata.subject}
					</h2>
					<p class="text-[var(--color-text-secondary)]">
						De <span class="font-medium">{currentItem.metadata.from_name || currentItem.metadata.from_address}</span>
					</p>
				</div>

				<!-- AI Summary - Prominent -->
				{#if currentItem.analysis.summary}
					<div class="p-6 rounded-2xl bg-[var(--color-bg-secondary)] border-l-4 border-[var(--color-accent)]">
						<p class="text-lg text-[var(--color-text-primary)]">
							{currentItem.analysis.summary}
						</p>
					</div>
				{/if}

				<!-- Entities - Compact badges -->
				{#if currentItem.analysis.entities && Object.keys(currentItem.analysis.entities).length > 0}
					<div class="flex flex-wrap gap-2 justify-center">
						{#each Object.entries(currentItem.analysis.entities) as [type, entities]}
							{#each entities as entity}
								{@const entityClass = {
									person: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
									project: 'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
									date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
									amount: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
									organization: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300',
									discovered: 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300'
								}[type] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'}
								<span class="px-3 py-1 text-sm rounded-full {entityClass}">
									{entity.value}
								</span>
							{/each}
						{/each}
					</div>
				{/if}

				<!-- Email content (toggle with V) -->
				{#if showLevel3 && (currentItem.content?.preview || currentItem.content?.full_text)}
					{@const contentText = currentItem.content?.full_text || currentItem.content?.preview || ''}
					<div class="p-4 rounded-xl bg-[var(--color-bg-tertiary)] text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap max-h-60 overflow-y-auto">
						{contentText}
					</div>
				{/if}

				<!-- Action options - BIG buttons for focus mode -->
				{#if options.length > 0}
					<div
						class="grid gap-4"
						class:lg:grid-cols-2={options.length === 2}
						class:lg:grid-cols-3={options.length >= 3}
					>
						{#each options as option, idx}
							<button
								class="p-6 rounded-2xl border-2 transition-all duration-200 text-left
									{option.is_recommended
										? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10'
										: 'border-[var(--color-border)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)]'}
									disabled:opacity-50"
								disabled={isProcessing}
								onclick={() => handleSelectOption(currentItem, option)}
							>
								<div class="flex items-center gap-4">
									<!-- Keyboard shortcut - Large -->
									<div class="w-14 h-14 rounded-xl bg-[var(--color-bg-tertiary)] flex items-center justify-center text-2xl font-mono font-bold text-[var(--color-accent)]">
										{idx + 1}
									</div>

									<div class="flex-1">
										<div class="flex items-center gap-2 mb-1">
											<span class="text-2xl">{getActionIcon(option.action)}</span>
											<span class="text-xl font-bold text-[var(--color-text-primary)]">
												{getActionLabel(option.action)}
											</span>
											{#if option.is_recommended}
												<span class="text-xs px-2 py-0.5 rounded bg-[var(--color-accent)] text-white">
													Recommandé
												</span>
											{/if}
										</div>
										<p class="text-sm text-[var(--color-text-secondary)]">
											{option.reasoning}
										</p>
										{#if option.destination}
											<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
												→ {option.destination}
											</p>
										{/if}
									</div>

									<div class="text-right">
										<span
											class="text-lg font-bold"
											style="color: {getConfidenceColor(option.confidence)}"
										>
											{option.confidence}%
										</span>
									</div>
								</div>
							</button>
						{/each}
					</div>
				{/if}

				<!-- Quick actions bar -->
				<div class="flex justify-center gap-3 pt-4">
					<Button
						variant="secondary"
						size="sm"
						onclick={handleSkip}
						disabled={isProcessing || items.length <= 1}
					>
						<span class="mr-1">⏭️</span> Passer
						<span class="ml-1 text-xs opacity-60 font-mono">N</span>
					</Button>

					<!-- Snooze button with dropdown -->
					<div class="relative">
						<Button
							variant="secondary"
							size="sm"
							onclick={() => showSnoozeMenu = !showSnoozeMenu}
							disabled={isProcessing || isSnoozing}
						>
							<span class="mr-1">⏰</span> Reporter
							<span class="ml-1 text-xs opacity-60 font-mono">Z</span>
						</Button>

						{#if showSnoozeMenu}
							<div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 py-1 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)] shadow-xl z-50">
								{#each snoozeOptions as option}
									<button
										type="button"
										class="w-full px-4 py-2 text-left text-sm hover:bg-[var(--color-bg-tertiary)] transition-colors text-[var(--color-text-primary)]"
										onclick={() => handleSnooze(option.value)}
									>
										{option.label}
									</button>
								{/each}
							</div>
						{/if}
					</div>

					<Button
						variant="secondary"
						size="sm"
						onclick={() => handleDelete(currentItem)}
						disabled={isProcessing}
					>
						<span class="mr-1">🗑️</span> Supprimer
						<span class="ml-1 text-xs opacity-60 font-mono">D</span>
					</Button>
					<Button
						variant={showLevel3 ? 'primary' : 'secondary'}
						size="sm"
						onclick={() => showLevel3 = !showLevel3}
					>
						<span class="mr-1">{showLevel3 ? '📖' : '📋'}</span>
						{showLevel3 ? 'Masquer détails' : 'Voir détails'}
						<span class="ml-1 text-xs opacity-60 font-mono">V</span>
					</Button>
					<Button
						variant="secondary"
						size="sm"
						onclick={() => handleReject(currentItem)}
						disabled={isProcessing}
					>
						<span class="mr-1">🚫</span> Ignorer
						<span class="ml-1 text-xs opacity-60 font-mono">R</span>
					</Button>
				</div>
			</div>
		{/if}
	</main>

	<!-- Footer with keyboard hints -->
	<footer class="px-6 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]">
		<div class="flex justify-center flex-wrap gap-x-6 gap-y-2 text-xs text-[var(--color-text-tertiary)]">
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">1</span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded ml-1">2</span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded ml-1">3</span>
				<span class="ml-1">action</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">N</span>
				<span class="ml-1">suivant</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">Z</span>
				<span class="ml-1">reporter</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">D</span>
				<span class="ml-1">supprimer</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">V</span>
				<span class="ml-1">détails</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">R</span>
				<span class="ml-1">ignorer</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">F</span>
				<span class="ml-1">filtrer</span>
			</span>
			<span>
				<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">Esc</span>
				<span class="ml-1">quitter</span>
			</span>
		</div>
	</footer>
</div>

