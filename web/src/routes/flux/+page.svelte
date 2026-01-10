<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { Card, Button, Input, VirtualList, SwipeableCard, LongPressMenu } from '$lib/components/ui';
	import type { MenuItem } from '$lib/components/ui/LongPressMenu.svelte';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { queueStore } from '$lib/stores';
	import { toastStore } from '$lib/stores/toast.svelte';
	import { approveQueueItem, rejectQueueItem, undoQueueItem, canUndoQueueItem, snoozeQueueItem, processInbox } from '$lib/api';
	import type { QueueItem, ActionOption, SnoozeOption } from '$lib/api';
	import { registerShortcuts, createNavigationShortcuts, createQueueActionShortcuts } from '$lib/utils/keyboard-shortcuts';

	// Detect touch device
	const isTouchDevice = $derived(browser && ('ontouchstart' in window || navigator.maxTouchPoints > 0));

	// Track undo state per item
	let undoableItems = $state<Set<string>>(new Set());
	let undoingItems = $state<Set<string>>(new Set());

	// Snooze state
	let showSnoozeMenu = $state(false);
	let isSnoozing = $state(false);
	let snoozeSuccess = $state<string | null>(null);
	let snoozeError = $state<string | null>(null);

	// Fetch emails state
	let isFetchingEmails = $state(false);
	let fetchError = $state<string | null>(null);

	// Timeout IDs for cleanup
	let undoErrorTimeout: ReturnType<typeof setTimeout> | null = null;
	let snoozeSuccessTimeout: ReturnType<typeof setTimeout> | null = null;
	let snoozeErrorTimeout: ReturnType<typeof setTimeout> | null = null;

	const snoozeOptions: { value: SnoozeOption; label: string }[] = [
		{ value: 'in_30_min', label: '30 minutes' },
		{ value: 'in_2_hours', label: '2 heures' },
		{ value: 'tomorrow', label: 'Demain matin' },
		{ value: 'next_week', label: 'Semaine prochaine' }
	];

	function enterFocusMode() {
		goto('/flux/focus');
	}

	// Cleanup function for keyboard shortcuts
	let unregisterShortcuts: (() => void) | null = null;

	// Load queue on mount
	onMount(async () => {
		await queueStore.fetchQueue('pending');
		await queueStore.fetchStats();
		document.addEventListener('keydown', handleKeyboard);

		// Register context-specific keyboard shortcuts
		const navigationShortcuts = createNavigationShortcuts(
			() => navigatePrevious(),
			() => navigateNext(),
			'/flux'
		);

		const actionShortcuts = createQueueActionShortcuts(
			() => handleApproveRecommended(),
			() => currentItem && handleReject(currentItem),
			() => toggleSnoozeMenu(),
			() => { showLevel3 = !showLevel3; },
			'/flux'
		);

		unregisterShortcuts = registerShortcuts([...navigationShortcuts, ...actionShortcuts]);
	});

	onDestroy(() => {
		document.removeEventListener('keydown', handleKeyboard);
		unregisterShortcuts?.();
		// Clear all pending timeouts
		if (undoErrorTimeout) clearTimeout(undoErrorTimeout);
		if (snoozeSuccessTimeout) clearTimeout(snoozeSuccessTimeout);
		if (snoozeErrorTimeout) clearTimeout(snoozeErrorTimeout);
	});

	type StatusFilter = 'pending' | 'approved' | 'rejected';
	let activeFilter: StatusFilter = $state('pending');
	let currentIndex: number = $state(0);
	let customInstruction: string = $state('');
	let isProcessing: boolean = $state(false);
	let showCustomInput: boolean = $state(false);
	let showLevel3: boolean = $state(false);
	let showHtmlContent: boolean = $state(false);

	// Current item in single-item view
	const currentItem = $derived(
		activeFilter === 'pending' && queueStore.items.length > 0
			? queueStore.items[currentIndex] || null
			: null
	);

	async function changeFilter(filter: StatusFilter) {
		activeFilter = filter;
		currentIndex = 0;
		customInstruction = '';
		showCustomInput = false;
		await queueStore.fetchQueue(filter);

		// Check which approved items can be undone
		if (filter === 'approved') {
			await checkUndoableItems();
		}
	}

	async function checkUndoableItems() {
		const newUndoable = new Set<string>();
		// Check first 20 items for undo availability
		const itemsToCheck = queueStore.items.slice(0, 20);
		await Promise.all(
			itemsToCheck.map(async (item) => {
				try {
					const result = await canUndoQueueItem(item.id);
					if (result.can_undo) {
						newUndoable.add(item.id);
					}
				} catch {
					// Ignore errors, item just won't be undoable
				}
			})
		);
		undoableItems = newUndoable;
	}

	async function handleFetchEmails() {
		if (isFetchingEmails) return;

		isFetchingEmails = true;
		fetchError = null;

		// Inform user that processing has started (can take 1-2 minutes)
		toastStore.info(
			'Analyse des emails en cours... Cela peut prendre quelques minutes.',
			{ title: 'Traitement démarré' }
		);

		try {
			const result = await processInbox(20, false, undefined, true);
			toastStore.success(
				`${result.total_processed} email${result.total_processed > 1 ? 's' : ''} analysé${result.total_processed > 1 ? 's' : ''}`,
				{ title: 'Courrier récupéré' }
			);

			// Refresh the queue
			await queueStore.fetchQueue('pending');
			await queueStore.fetchStats();
		} catch (err) {
			fetchError = err instanceof Error ? err.message : 'Erreur de connexion';
			toastStore.error(
				'Impossible de récupérer le courrier. Vérifiez la connexion au serveur.',
				{ title: 'Erreur' }
			);
		} finally {
			isFetchingEmails = false;
		}
	}

	// Undo error state
	let undoError = $state<string | null>(null);

	async function handleUndoItem(item: QueueItem) {
		// Double-check to prevent race conditions
		if (undoingItems.has(item.id)) return;
		if (!undoableItems.has(item.id)) return;

		// Atomically mark as in-progress
		undoingItems = new Set([...undoingItems, item.id]);
		undoError = null;

		try {
			await undoQueueItem(item.id);
			// Remove from undoable set
			const newUndoable = new Set(undoableItems);
			newUndoable.delete(item.id);
			undoableItems = newUndoable;
			// Refresh the list
			await queueStore.fetchQueue('approved');
			await queueStore.fetchStats();
		} catch (e) {
			console.error('Undo failed:', e);
			undoError = e instanceof Error ? e.message : 'Erreur lors de l\'annulation';
			// Clear error after 5 seconds
			if (undoErrorTimeout) clearTimeout(undoErrorTimeout);
			undoErrorTimeout = setTimeout(() => {
				undoError = null;
			}, 5000);
		} finally {
			const newUndoing = new Set(undoingItems);
			newUndoing.delete(item.id);
			undoingItems = newUndoing;
		}
	}

	function handleKeyboard(e: KeyboardEvent) {
		// Only handle in pending single-item view
		if (activeFilter !== 'pending' || !currentItem || isProcessing) return;

		// Don't handle if user is typing in input
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

		const options = currentItem.analysis.options || [];

		// Note: j, k, a, r, s, e are handled by centralized keyboard-shortcuts system
		// This handler only handles numeric keys, d, i, v, and Escape
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
			case 'd':
			case 'D':
				handleDelete(currentItem);
				break;
			case 'i':
			case 'I':
				showCustomInput = !showCustomInput;
				break;
			case 'v':
			case 'V':
				// v for details (legacy shortcut, e also works via centralized system)
				showLevel3 = !showLevel3;
				break;
			case 'Escape':
				showCustomInput = false;
				showLevel3 = false;
				showSnoozeMenu = false;
				customInstruction = '';
				break;
		}
	}

	async function handleSelectOption(item: QueueItem, option: ActionOption) {
		if (isProcessing) return;
		isProcessing = true;

		// Save item info for undo and potential restore
		const itemId = item.id;
		const itemSubject = item.metadata.subject;
		const actionLabel = getActionLabel(option.action);
		const savedItem = { ...item }; // Deep copy for restore on error

		// Bug #53 fix: Optimistic update - immediately update UI
		queueStore.removeFromList(item.id);

		// Move to next or reset
		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}
		customInstruction = '';
		showCustomInput = false;

		// Show undo toast immediately
		toastStore.undo(
			`${actionLabel} : ${itemSubject.slice(0, 40)}${itemSubject.length > 40 ? '...' : ''}`,
			async () => {
				await undoQueueItem(itemId);
				await queueStore.fetchQueue('pending');
				await queueStore.fetchStats();
			},
			{ itemId, title: 'Action effectuée' }
		);

		// Allow next action immediately (unlock UI)
		isProcessing = false;

		// Bug #53 fix: Execute API call in background (non-blocking)
		try {
			await approveQueueItem(item.id, option.action, item.analysis.category || undefined, option.destination);
			// Update stats in background (no await needed)
			queueStore.fetchStats();
		} catch (e) {
			// Bug #52 fix: Restore item if action failed
			console.error('Action failed:', e);
			// Dismiss the undo toast since action failed
			const undoToast = toastStore.findUndoByItemId(itemId);
			if (undoToast) toastStore.dismiss(undoToast.id);
			// Restore item to queue
			queueStore.restoreItem(savedItem);
			toastStore.error(
				`Échec de l'action "${actionLabel}". L'email a été restauré.`,
				{ title: 'Erreur IMAP' }
			);
		}
	}

	async function handleCustomInstruction(item: QueueItem) {
		if (isProcessing || !customInstruction.trim()) return;
		isProcessing = true;

		// Save item info for undo and potential restore
		const itemId = item.id;
		const itemSubject = item.metadata.subject;
		const savedItem = { ...item };
		const savedInstruction = customInstruction.trim();

		// Bug #53 fix: Optimistic update - immediately update UI
		queueStore.removeFromList(item.id);

		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}
		customInstruction = '';
		showCustomInput = false;

		// Show undo toast immediately
		toastStore.undo(
			`Instruction personnalisée : ${itemSubject.slice(0, 30)}${itemSubject.length > 30 ? '...' : ''}`,
			async () => {
				await undoQueueItem(itemId);
				await queueStore.fetchQueue('pending');
				await queueStore.fetchStats();
			},
			{ itemId, title: 'Action effectuée' }
		);

		// Allow next action immediately
		isProcessing = false;

		// Execute API call in background
		try {
			await approveQueueItem(item.id, 'custom', item.analysis.category || undefined);
			queueStore.fetchStats();
		} catch (e) {
			console.error('Custom instruction failed:', e);
			const undoToast = toastStore.findUndoByItemId(itemId);
			if (undoToast) toastStore.dismiss(undoToast.id);
			queueStore.restoreItem(savedItem);
			customInstruction = savedInstruction; // Restore the instruction
			toastStore.error(
				`Échec de l'instruction. L'email a été restauré.`,
				{ title: 'Erreur' }
			);
		}
	}

	async function handleReject(item: QueueItem) {
		if (isProcessing) return;
		isProcessing = true;

		// Save for potential restore
		const savedItem = { ...item };

		// Bug #53 fix: Optimistic update
		queueStore.removeFromList(item.id);

		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}
		customInstruction = '';
		showCustomInput = false;

		// Allow next action immediately
		isProcessing = false;

		// Execute in background
		try {
			await rejectQueueItem(item.id);
			queueStore.fetchStats();
		} catch (e) {
			console.error('Reject failed:', e);
			queueStore.restoreItem(savedItem);
			toastStore.error(
				`Échec du rejet. L'email a été restauré.`,
				{ title: 'Erreur' }
			);
		}
	}

	async function handleDelete(item: QueueItem) {
		if (isProcessing) return;
		isProcessing = true;

		// Save item info for undo and potential restore
		const itemId = item.id;
		const itemSubject = item.metadata.subject;
		const savedItem = { ...item };

		// Bug #53 fix: Optimistic update
		queueStore.removeFromList(item.id);

		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}
		customInstruction = '';
		showCustomInput = false;

		// Show undo toast immediately
		toastStore.undo(
			`Supprimé : ${itemSubject.slice(0, 40)}${itemSubject.length > 40 ? '...' : ''}`,
			async () => {
				await undoQueueItem(itemId);
				await queueStore.fetchQueue('pending');
				await queueStore.fetchStats();
			},
			{ itemId, title: 'Email déplacé vers la corbeille' }
		);

		// Allow next action immediately
		isProcessing = false;

		// Execute in background
		try {
			await approveQueueItem(item.id, 'delete', item.analysis.category || undefined);
			queueStore.fetchStats();
		} catch (e) {
			console.error('Delete failed:', e);
			const undoToast = toastStore.findUndoByItemId(itemId);
			if (undoToast) toastStore.dismiss(undoToast.id);
			queueStore.restoreItem(savedItem);
			toastStore.error(
				`Échec de la suppression. L'email a été restauré.`,
				{ title: 'Erreur IMAP' }
			);
		}
	}

	function handleSkip() {
		// Move to next item without action
		if (currentIndex < queueStore.items.length - 1) {
			currentIndex++;
		} else {
			currentIndex = 0; // Loop back to start
		}
		customInstruction = '';
		showCustomInput = false;
		showLevel3 = false;
	}

	// Navigation helpers for keyboard shortcuts
	function navigatePrevious() {
		if (activeFilter === 'pending' && queueStore.items.length > 0) {
			if (currentIndex > 0) {
				currentIndex--;
			} else {
				currentIndex = queueStore.items.length - 1; // Loop to end
			}
		}
	}

	function navigateNext() {
		if (activeFilter === 'pending' && queueStore.items.length > 0) {
			if (currentIndex < queueStore.items.length - 1) {
				currentIndex++;
			} else {
				currentIndex = 0; // Loop to start
			}
		}
	}

	// Approve recommended option (for 'a' shortcut)
	function handleApproveRecommended() {
		if (!currentItem || isProcessing) return;

		const options = currentItem.analysis.options || [];
		// Find recommended option, or use first option as fallback
		const recommended = options.find((o) => o.is_recommended) || options[0];

		if (recommended) {
			handleSelectOption(currentItem, recommended);
		} else {
			// Fallback: approve with current analysis action
			handleSelectOption(currentItem, {
				action: currentItem.analysis.action,
				confidence: currentItem.analysis.confidence,
				reasoning: currentItem.analysis.reasoning,
				reasoning_detailed: null,
				destination: null,
				is_recommended: true
			});
		}
	}

	function toggleSnoozeMenu() {
		showSnoozeMenu = !showSnoozeMenu;
	}

	async function handleSnoozeOption(option: SnoozeOption) {
		if (!currentItem || isSnoozing) return;
		isSnoozing = true;
		showSnoozeMenu = false;
		snoozeError = null;

		try {
			const result = await snoozeQueueItem(currentItem.id, option);
			const snoozeUntil = new Date(result.snooze_until);
			snoozeSuccess = `Snoozé jusqu'à ${snoozeUntil.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}`;

			// Refresh queue and stats
			await queueStore.fetchQueue('pending');
			await queueStore.fetchStats();

			// Clear success message after delay
			if (snoozeSuccessTimeout) clearTimeout(snoozeSuccessTimeout);
			snoozeSuccessTimeout = setTimeout(() => {
				snoozeSuccess = null;
			}, 3000);

			// Reset index if needed
			if (currentIndex >= queueStore.items.length) {
				currentIndex = Math.max(0, queueStore.items.length - 1);
			}
		} catch (e) {
			console.error('Snooze failed:', e);
			snoozeError = e instanceof Error ? e.message : 'Erreur lors du report';
			// Clear error after 5 seconds
			if (snoozeErrorTimeout) clearTimeout(snoozeErrorTimeout);
			snoozeErrorTimeout = setTimeout(() => {
				snoozeError = null;
			}, 5000);
		} finally {
			isSnoozing = false;
		}
	}

	// Bug #55: Defer custom instruction (snooze with instruction saved)
	async function handleDeferCustomInstruction(item: QueueItem) {
		if (!item || isSnoozing) return;
		isSnoozing = true;
		showCustomInput = false;
		snoozeError = null;

		try {
			// Snooze with the custom instruction as reason
			const reason = customInstruction.trim() || undefined;
			const result = await snoozeQueueItem(item.id, 'in_2_hours', { reason });
			const snoozeUntil = new Date(result.snooze_until);
			snoozeSuccess = `Reporté à ${snoozeUntil.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}`;
			if (reason) {
				snoozeSuccess += ` (${reason.slice(0, 30)}${reason.length > 30 ? '...' : ''})`;
			}

			// Refresh queue and stats
			await queueStore.fetchQueue('pending');
			await queueStore.fetchStats();

			// Clear success message after delay
			if (snoozeSuccessTimeout) clearTimeout(snoozeSuccessTimeout);
			snoozeSuccessTimeout = setTimeout(() => {
				snoozeSuccess = null;
			}, 3000);

			// Reset state
			customInstruction = '';
			if (currentIndex >= queueStore.items.length) {
				currentIndex = Math.max(0, queueStore.items.length - 1);
			}
		} catch (e) {
			console.error('Defer custom instruction failed:', e);
			snoozeError = e instanceof Error ? e.message : 'Erreur lors du report';
			if (snoozeErrorTimeout) clearTimeout(snoozeErrorTimeout);
			snoozeErrorTimeout = setTimeout(() => {
				snoozeError = null;
			}, 5000);
		} finally {
			isSnoozing = false;
		}
	}

	function handleSkipToNext() {
		// Skip to next item without API call (local only)
		if (queueStore.items.length > 1) {
			const item = queueStore.items[currentIndex];
			queueStore.moveToEnd(item.id);
		}
		customInstruction = '';
		showCustomInput = false;
		showLevel3 = false;
	}

	function getActionLabel(action: string): string {
		const labels: Record<string, string> = {
			archive: 'Classer',
			delete: 'Supprimer',
			reply: 'Répondre',
			forward: 'Transférer',
			flag: 'Signaler',
			task: 'Créer tâche',
			defer: 'Reporter',
			ignore: 'Ignorer',
			queue: 'À décider',
			review: 'À revoir',
			pending: 'En attente'
		};
		return labels[action] || action;
	}

	function getActionIcon(action: string): string {
		const icons: Record<string, string> = {
			archive: '📥',
			delete: '🗑️',
			reply: '✉️',
			forward: '⬆️',
			flag: '🚩',
			task: '✅',
			defer: '⏰',
			ignore: '🚫',
			queue: '❓',
			review: '👁️'
		};
		return icons[action] || '❓';
	}

	function getActionColor(action: string): string {
		const colors: Record<string, string> = {
			archive: 'var(--color-success)',
			delete: 'var(--color-urgency-urgent)',
			reply: 'var(--color-accent)',
			task: 'var(--color-event-omnifocus)',
			queue: 'var(--color-warning)',
			review: 'var(--color-warning)',
			pending: 'var(--color-warning)'
		};
		return colors[action] || 'var(--color-text-secondary)';
	}

	function getCategoryLabel(category: string | null): string {
		if (!category) return '';
		const labels: Record<string, string> = {
			work: 'Travail',
			personal: 'Personnel',
			finance: 'Finances',
			shopping: 'Achats',
			newsletter: 'Newsletter',
			social: 'Social',
			spam: 'Indésirable'
		};
		return labels[category.toLowerCase()] || category;
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 90) return 'var(--color-success)';
		if (confidence >= 70) return 'var(--color-warning)';
		return 'var(--color-urgency-urgent)';
	}

	function getConfidenceExplanation(confidence: number): string {
		if (confidence >= 90) return 'Scapin est très confiant mais préfère votre aval';
		if (confidence >= 70) return 'Scapin hésite entre plusieurs options';
		return 'Scapin manque d\'éléments pour décider seul';
	}

	// Mobile context menu items
	const getMobileMenuItems = $derived((item: QueueItem): MenuItem[] => {
		const options = item.analysis.options || [];
		const recommended = options.find((o) => o.is_recommended) || options[0];
		const menuItems: MenuItem[] = [];

		// Add action options
		options.forEach((option, idx) => {
			menuItems.push({
				id: `action-${idx}`,
				label: `${getActionIcon(option.action)} ${getActionLabel(option.action)}${option.is_recommended ? ' (Recommandé)' : ''}`,
				handler: () => handleSelectOption(item, option)
			});
		});

		// Separator - snooze
		menuItems.push({
			id: 'snooze',
			label: 'Reporter...',
			icon: '⏰',
			handler: () => { showSnoozeMenu = true; }
		});

		// Reject
		menuItems.push({
			id: 'reject',
			label: 'Rejeter',
			icon: '🚫',
			variant: 'danger',
			handler: () => handleReject(item)
		});

		// View details
		menuItems.push({
			id: 'details',
			label: 'Voir l\'email complet',
			icon: '📧',
			handler: () => goto(`/flux/${item.id}`)
		});

		return menuItems;
	});

	// Swipe actions for mobile
	const swipeRightAction = $derived(currentItem ? {
		icon: '✓',
		label: 'Approuver',
		color: 'var(--color-success)',
		action: () => handleApproveRecommended()
	} : undefined);

	const swipeLeftAction = $derived(currentItem ? {
		icon: '✕',
		label: 'Rejeter',
		color: 'var(--color-urgency-urgent)',
		action: () => currentItem && handleReject(currentItem)
	} : undefined);

	const stats = $derived(queueStore.stats);
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<!-- Header with Scapin tone -->
	<header class="mb-6">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
					Le Courrier, Monsieur
				</h1>
				<p class="text-[var(--color-text-secondary)] mt-1" aria-live="polite" aria-atomic="true">
					{#if queueStore.loading}
						Je consulte vos plis...
					{:else if activeFilter === 'pending' && queueStore.total > 0}
						{queueStore.total} pli{queueStore.total > 1 ? 's' : ''} requièrent votre attention
					{:else if activeFilter === 'pending'}
						Point de pli en attente, Monsieur
					{:else if activeFilter === 'approved'}
						Voici les plis que vous avez traités
					{:else}
						Voici les plis que vous avez écartés
					{/if}
				</p>
			</div>

			<!-- Action buttons -->
			<div class="flex items-center gap-2 shrink-0">
				<!-- Fetch emails button -->
				<Button
					variant="secondary"
					size="sm"
					onclick={handleFetchEmails}
					disabled={isFetchingEmails}
				>
					{#if isFetchingEmails}
						<span class="mr-1.5 animate-spin">⏳</span>
						Récupération...
					{:else}
						<span class="mr-1.5">📥</span>
						Récupérer
					{/if}
				</Button>

				<!-- Focus mode button -->
				{#if activeFilter === 'pending' && queueStore.items.length > 0}
					<Button
						variant="primary"
						size="sm"
						onclick={enterFocusMode}
					>
						<span class="mr-1.5">🎯</span>
						Mode Focus
					</Button>
				{/if}
			</div>
		</div>
	</header>

	<!-- Stats as clickable filters -->
	<section class="grid grid-cols-3 gap-2 mb-6">
		<button
			class="rounded-xl p-3 text-center transition-all border-2"
			class:border-[var(--color-accent)]={activeFilter === 'pending'}
			class:bg-[var(--color-bg-secondary)]={activeFilter === 'pending'}
			class:border-transparent={activeFilter !== 'pending'}
			class:hover:border-[var(--color-border)]={activeFilter !== 'pending'}
			onclick={() => changeFilter('pending')}
		>
			<p class="text-xl font-bold text-[var(--color-warning)]">
				{stats?.by_status?.pending ?? 0}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">À votre attention</p>
		</button>

		<button
			class="rounded-xl p-3 text-center transition-all border-2"
			class:border-[var(--color-accent)]={activeFilter === 'approved'}
			class:bg-[var(--color-bg-secondary)]={activeFilter === 'approved'}
			class:border-transparent={activeFilter !== 'approved'}
			class:hover:border-[var(--color-border)]={activeFilter !== 'approved'}
			onclick={() => changeFilter('approved')}
		>
			<p class="text-xl font-bold text-[var(--color-success)]">
				{stats?.by_status?.approved ?? 0}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">Traités</p>
		</button>

		<button
			class="rounded-xl p-3 text-center transition-all border-2"
			class:border-[var(--color-accent)]={activeFilter === 'rejected'}
			class:bg-[var(--color-bg-secondary)]={activeFilter === 'rejected'}
			class:border-transparent={activeFilter !== 'rejected'}
			class:hover:border-[var(--color-border)]={activeFilter !== 'rejected'}
			onclick={() => changeFilter('rejected')}
		>
			<p class="text-xl font-bold text-[var(--color-urgency-urgent)]">
				{stats?.by_status?.rejected ?? 0}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">Écartés</p>
		</button>
	</section>

	<!-- Loading state -->
	{#if queueStore.loading && queueStore.items.length === 0}
		<div class="flex justify-center py-12" role="status" aria-busy="true" aria-label="Chargement en cours">
			<div
				class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
				aria-hidden="true"
			></div>
			<span class="sr-only">Chargement de la file d'attente...</span>
		</div>

	<!-- Empty state -->
	{:else if queueStore.items.length === 0}
		<Card padding="lg">
			<div class="text-center py-8">
				<p class="text-4xl mb-3">
					{#if activeFilter === 'pending'}🎉
					{:else if activeFilter === 'approved'}✅
					{:else}🚫
					{/if}
				</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
					{#if activeFilter === 'pending'}
						Tout est en ordre, Monsieur
					{:else if activeFilter === 'approved'}
						Aucun pli traité pour l'instant
					{:else}
						Aucun pli écarté
					{/if}
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">
					{#if activeFilter === 'pending'}
						Aucun courrier ne requiert votre décision
					{:else}
						Lancez le traitement des emails pour alimenter la file
					{/if}
				</p>
			</div>
		</Card>

	<!-- SINGLE ITEM VIEW for pending items -->
	{:else if activeFilter === 'pending' && currentItem}
		{@const options = currentItem.analysis.options || []}
		{@const hasOptions = options.length > 0}

		<!-- Mobile hint for swipe gestures (shown only on touch devices) -->
		<div class="text-xs text-center text-[var(--color-text-tertiary)] py-2 mb-2 md:hidden">
			<span class="opacity-70">← Glisser pour rejeter</span>
			<span class="mx-3">•</span>
			<span class="font-medium">Appui long = menu</span>
			<span class="mx-3">•</span>
			<span class="opacity-70">Approuver →</span>
		</div>

		<!-- SwipeableCard wraps for mobile swipe gestures (no-op on desktop) -->
		<SwipeableCard
			rightAction={swipeRightAction}
			leftAction={swipeLeftAction}
			threshold={100}
		>
			<!-- LongPressMenu for mobile context menu (right-click on desktop) -->
			<LongPressMenu items={getMobileMenuItems(currentItem)}>
				<Card padding="lg">
					<div class="space-y-5">
						<!-- Progress indicator -->
						<div class="flex items-center justify-between text-xs text-[var(--color-text-tertiary)]">
							<span>Pli {currentIndex + 1} sur {queueStore.items.length}</span>
							<div class="flex gap-1">
								{#each queueStore.items as _, idx}
									<div
										class="w-2 h-2 rounded-full transition-colors"
										class:bg-[var(--color-accent)]={idx === currentIndex}
										class:bg-[var(--color-border)]={idx !== currentIndex}
									></div>
								{/each}
							</div>
						</div>

				<!-- Snooze feedback -->
				{#if snoozeSuccess}
					<div class="flex items-center gap-2 p-2 rounded-lg bg-green-500/20 text-green-400 text-sm animate-pulse">
						<span>💤</span>
						<span>{snoozeSuccess}</span>
					</div>
				{:else if snoozeError}
					<div class="flex items-center gap-2 p-2 rounded-lg bg-red-500/20 text-red-400 text-sm">
						<span>⚠️</span>
						<span>{snoozeError}</span>
					</div>
				{/if}

				<!-- Why in queue - Scapin explanation -->
				<div class="flex items-center gap-2 p-2 rounded-lg bg-[var(--color-bg-tertiary)]">
					<span class="text-lg">🎭</span>
					<p class="text-xs text-[var(--color-text-secondary)] italic">
						{getConfidenceExplanation(currentItem.analysis.confidence)}
						<span class="font-medium" style="color: {getConfidenceColor(currentItem.analysis.confidence)}">
							({currentItem.analysis.confidence}% de confiance)
						</span>
					</p>
				</div>

				<!-- Email header -->
				<div>
					<h2 class="text-xl font-bold text-[var(--color-text-primary)] mb-2">
						{currentItem.metadata.subject}
					</h2>
					<div class="flex flex-wrap items-center gap-2 text-sm text-[var(--color-text-secondary)]">
						<span>{currentItem.metadata.from_name || currentItem.metadata.from_address}</span>
						<span class="text-[var(--color-text-tertiary)]">•</span>
						<span class="text-[var(--color-text-tertiary)]">
							{#if currentItem.metadata.date}
								{formatRelativeTime(currentItem.metadata.date)}
							{:else}
								{formatRelativeTime(currentItem.queued_at)}
							{/if}
						</span>
						{#if currentItem.analysis.category}
							<span class="px-2 py-0.5 rounded-full text-xs bg-[var(--color-bg-tertiary)]">
								{getCategoryLabel(currentItem.analysis.category)}
							</span>
						{/if}
					</div>
				</div>

				<!-- AI Summary -->
				{#if currentItem.analysis.summary}
					<div class="p-4 rounded-lg bg-[var(--color-bg-secondary)] border-l-4 border-[var(--color-accent)]">
						<p class="text-[var(--color-text-primary)]">
							{currentItem.analysis.summary}
						</p>
					</div>
				{/if}

				<!-- Extracted Entities -->
				{#if currentItem.analysis.entities && Object.keys(currentItem.analysis.entities).length > 0}
					<div class="flex flex-wrap gap-1.5">
						{#each Object.entries(currentItem.analysis.entities) as [type, entities]}
							{#each entities as entity}
								{@const entityClass = {
									person: 'bg-blue-500/20 text-blue-300',
									project: 'bg-purple-500/20 text-purple-300',
									date: 'bg-orange-500/20 text-orange-300',
									amount: 'bg-green-500/20 text-green-300',
									organization: 'bg-cyan-500/20 text-cyan-300',
									phone: 'bg-pink-500/20 text-pink-300',
									url: 'bg-indigo-500/20 text-indigo-300'
								}[type] ?? 'bg-gray-500/20 text-gray-300'}
								<span
									class="px-2 py-0.5 text-xs rounded-full {entityClass}"
									title="{type}: {entity.value} ({Math.round(entity.confidence * 100)}%)"
								>
									{entity.value}
								</span>
							{/each}
						{/each}
					</div>
				{/if}

				<!-- Proposed Notes (Sprint 2) -->
				{#if currentItem.analysis.proposed_notes && currentItem.analysis.proposed_notes.length > 0}
					<div class="p-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]">
						<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
							Notes proposées
						</h4>
						<div class="space-y-2">
							{#each currentItem.analysis.proposed_notes as note}
								{@const noteActionClass = note.action === 'create' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}
								<div class="flex items-center justify-between text-sm">
									<span class="flex items-center gap-2">
										<span class="text-xs px-1.5 py-0.5 rounded {noteActionClass}">
											{note.action === 'create' ? '+ Créer' : '~ Enrichir'} {note.note_type}
										</span>
										<span class="text-[var(--color-text-primary)]">{note.title}</span>
										{#if note.auto_applied}
											<span class="text-xs px-1.5 py-0.5 rounded" style="background: rgba(var(--color-success-rgb, 34, 197, 94), 0.2); color: var(--color-success)">
												Auto
											</span>
										{/if}
									</span>
									<span
										class="text-xs"
										style="color: {note.confidence >= 0.9 ? 'var(--color-success)' : note.confidence >= 0.7 ? 'var(--color-warning)' : 'var(--color-text-tertiary)'}"
									>
										{Math.round(note.confidence * 100)}%
									</span>
								</div>
								{#if showLevel3 && note.reasoning}
									<p class="text-xs text-[var(--color-text-tertiary)] ml-4 pl-2 border-l border-[var(--color-border)]">
										{note.reasoning}
									</p>
								{/if}
							{/each}
						</div>
					</div>
				{/if}

				<!-- Proposed Tasks (Sprint 2) -->
				{#if currentItem.analysis.proposed_tasks && currentItem.analysis.proposed_tasks.length > 0}
					<div class="p-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]">
						<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
							Tâches proposées
						</h4>
						<div class="space-y-2">
							{#each currentItem.analysis.proposed_tasks as task}
								<div class="flex items-center justify-between text-sm">
									<span class="flex items-center gap-2">
										<span class="text-[var(--color-event-omnifocus)]">✓</span>
										<span class="text-[var(--color-text-primary)]">{task.title}</span>
										{#if task.project}
											<span class="text-xs text-[var(--color-text-tertiary)]">
												→ {task.project}
											</span>
										{/if}
										{#if task.due_date}
											<span class="text-xs text-[var(--color-warning)]">
												📅 {task.due_date}
											</span>
										{/if}
										{#if task.auto_applied}
											<span class="text-xs px-1.5 py-0.5 rounded" style="background: rgba(var(--color-success-rgb, 34, 197, 94), 0.2); color: var(--color-success)">
												Auto
											</span>
										{/if}
									</span>
									<span
										class="text-xs"
										style="color: {task.confidence >= 0.9 ? 'var(--color-success)' : task.confidence >= 0.7 ? 'var(--color-warning)' : 'var(--color-text-tertiary)'}"
									>
										{Math.round(task.confidence * 100)}%
									</span>
								</div>
								{#if showLevel3 && task.reasoning}
									<p class="text-xs text-[var(--color-text-tertiary)] ml-4 pl-2 border-l border-[var(--color-border)]">
										{task.reasoning}
									</p>
								{/if}
							{/each}
						</div>
					</div>
				{/if}

				<!-- Context Used (Sprint 2 - Notes that enriched the analysis) -->
				{#if currentItem.analysis.context_used && currentItem.analysis.context_used.length > 0}
					<div class="p-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]">
						<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
							Contexte utilisé
						</h4>
						<div class="flex flex-wrap gap-1.5">
							{#each currentItem.analysis.context_used as noteId}
								<a
									href="/notes/{noteId}"
									class="text-xs px-2 py-1 rounded-full bg-[var(--color-event-notes)]/20 text-[var(--color-event-notes)] hover:bg-[var(--color-event-notes)]/30 transition-colors"
								>
									📝 {noteId.slice(0, 20)}...
								</a>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Email content preview (always visible) -->
				{#if currentItem.content?.preview || currentItem.content?.full_text}
					{@const contentText = currentItem.content?.full_text || currentItem.content?.preview || ''}
					{@const previewLines = contentText.split('\n').slice(0, 5).join('\n')}
					{@const hasMore = contentText.split('\n').length > 5 || contentText.length > 300}

					{#if showLevel3}
						<!-- Détails mode: Full content with HTML toggle -->
						<div class="space-y-2">
							{#if currentItem.content?.html_body}
								<div class="flex gap-2">
									<button
										class="text-xs px-2 py-1 rounded transition-colors {!showHtmlContent ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}"
										onclick={() => showHtmlContent = false}
									>
										📝 Texte
									</button>
									<button
										class="text-xs px-2 py-1 rounded transition-colors {showHtmlContent ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}"
										onclick={() => showHtmlContent = true}
									>
										🌐 HTML
									</button>
								</div>
							{/if}

							{#if showHtmlContent && currentItem.content?.html_body}
								<!-- Note: sandbox without allow-same-origin for security (prevents script access to parent) -->
								<iframe
									srcdoc={currentItem.content.html_body}
									sandbox=""
									class="w-full h-96 rounded-lg border border-[var(--color-border)] bg-white"
									title="Contenu HTML de l'email"
								></iframe>
							{:else}
								<div class="p-3 rounded-lg bg-[var(--color-bg-tertiary)] text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap max-h-80 overflow-y-auto border border-[var(--color-border)]">
									{contentText}
								</div>
							{/if}
						</div>
					{:else}
						<!-- Normal mode: Short preview (5 lines) -->
						<div class="p-3 rounded-lg bg-[var(--color-bg-tertiary)] text-sm text-[var(--color-text-secondary)]">
							<p class="whitespace-pre-wrap line-clamp-5">
								{previewLines.length > 300 ? previewLines.slice(0, 300) + '...' : previewLines}
							</p>
							{#if hasMore}
								<p class="text-xs text-[var(--color-accent)] mt-2">
									Appuyer sur V (Détails) pour voir le contenu complet
									{#if currentItem.content?.html_body}
										<span class="text-[var(--color-text-tertiary)]">• HTML disponible</span>
									{/if}
								</p>
							{/if}
						</div>
					{/if}
				{/if}

				<!-- Metadata enrichment when showLevel3 -->
				{#if showLevel3}
					<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--color-text-tertiary)] p-2 rounded-lg bg-[var(--color-bg-secondary)]">
						<span>📧 {currentItem.metadata.from_address}</span>
						<span>📁 {currentItem.metadata.folder || 'INBOX'}</span>
						{#if currentItem.metadata.has_attachments}
							<span>📎 Pièces jointes</span>
						{/if}
						<span>🕐 Analysé {formatRelativeTime(currentItem.queued_at)}</span>
					</div>
				{/if}

				<!-- Action options - CLICK TO VALIDATE -->
				{#if hasOptions}
					<div class="space-y-3">
						<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide">
							Choisissez une action <span class="font-normal">(clic = validation immédiate)</span>
						</p>

						<div class="grid gap-2">
							{#each options as option, idx}
								<button
									class="w-full text-left p-4 rounded-xl border-2 border-[var(--color-border)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)] transition-all group disabled:opacity-50"
									disabled={isProcessing}
									onclick={() => handleSelectOption(currentItem, option)}
								>
									<div class="flex items-center gap-3">
										<!-- Keyboard shortcut -->
										<div class="w-8 h-8 rounded-lg bg-[var(--color-bg-tertiary)] group-hover:bg-[var(--color-accent)] group-hover:text-white flex items-center justify-center text-sm font-mono font-bold transition-colors">
											{idx + 1}
										</div>

										<!-- Action icon -->
										<div
											class="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
											style="background-color: color-mix(in srgb, {getActionColor(option.action)} 20%, transparent)"
										>
											{getActionIcon(option.action)}
										</div>

										<!-- Option content - enriched when showLevel3 -->
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2">
												<span
													class="font-semibold"
													style="color: {getActionColor(option.action)}"
												>
													{getActionLabel(option.action)}
												</span>
												{#if option.is_recommended}
													<span class="text-xs px-1.5 py-0.5 rounded bg-[var(--color-accent)] text-white">
														Recommandé
													</span>
												{/if}
												<span
													class="text-xs ml-auto"
													style="color: {getConfidenceColor(option.confidence)}"
												>
													{option.confidence}%
												</span>
											</div>
											<!-- Show detailed reasoning when Level 3, otherwise short -->
											<p class="text-xs text-[var(--color-text-secondary)] mt-0.5" class:text-sm={showLevel3 && option.reasoning_detailed}>
												{#if showLevel3 && option.reasoning_detailed}
													{option.reasoning_detailed}
												{:else}
													{option.reasoning}
												{/if}
											</p>
											{#if option.destination && option.action !== 'delete'}
												<p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
													→ {option.destination}
												</p>
											{/if}
										</div>
									</div>
								</button>
							{/each}
						</div>
					</div>
				{:else}
					<!-- Fallback for items without options -->
					<div class="p-4 rounded-lg bg-[var(--color-bg-tertiary)]">
						<div class="flex items-center gap-2 mb-2">
							<span class="text-xl">{getActionIcon(currentItem.analysis.action)}</span>
							<span class="font-semibold" style="color: {getActionColor(currentItem.analysis.action)}">
								{getActionLabel(currentItem.analysis.action)}
							</span>
							<span class="text-xs" style="color: {getConfidenceColor(currentItem.analysis.confidence)}">
								{currentItem.analysis.confidence}%
							</span>
						</div>
						{#if currentItem.analysis.reasoning}
							<p class="text-sm text-[var(--color-text-secondary)]">
								{currentItem.analysis.reasoning}
							</p>
						{/if}
						<Button
							variant="primary"
							size="sm"
							class="mt-3"
							onclick={() => handleSelectOption(currentItem, {
								action: currentItem.analysis.action,
								confidence: currentItem.analysis.confidence,
								reasoning: currentItem.analysis.reasoning,
								reasoning_detailed: null,
								destination: null,
								is_recommended: true
							})}
							disabled={isProcessing}
						>
							Valider cette action
						</Button>
					</div>
				{/if}

				<!-- Custom instruction toggle (Bug #55: two buttons) -->
				{#if showCustomInput}
					<div class="space-y-2 p-3 rounded-lg border border-[var(--color-border)]">
						<label for="custom-instruction" class="text-xs font-medium text-[var(--color-text-secondary)]">
							Votre instruction, Monsieur :
						</label>
						<Input
							id="custom-instruction"
							placeholder="Ex: Classer dans Travail/Projets/2026"
							bind:value={customInstruction}
						/>
						<div class="flex gap-2 flex-wrap">
							<Button
								variant="primary"
								size="sm"
								onclick={() => handleCustomInstruction(currentItem)}
								disabled={isProcessing || !customInstruction.trim()}
							>
								<span class="mr-1">⚡</span> Exécuter maintenant
							</Button>
							<Button
								variant="secondary"
								size="sm"
								onclick={() => handleDeferCustomInstruction(currentItem)}
								disabled={isProcessing || isSnoozing}
							>
								<span class="mr-1">⏰</span> Plus tard
							</Button>
							<Button
								variant="secondary"
								size="sm"
								onclick={() => { showCustomInput = false; customInstruction = ''; }}
							>
								Annuler
							</Button>
						</div>
					</div>
				{/if}

				<!-- Bottom actions - Always available -->
				<div class="pt-4 border-t border-[var(--color-border)] space-y-3">
					<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide">
						Actions rapides
					</p>
					<div class="flex flex-wrap gap-2">
						<Button
							variant="primary"
							size="sm"
							onclick={handleApproveRecommended}
							disabled={isProcessing}
							data-testid="approve-button"
						>
							<span class="mr-1">✅</span> Approuver
							<span class="ml-1 text-xs opacity-60 font-mono">A</span>
						</Button>
						<Button
							variant="secondary"
							size="sm"
							onclick={() => handleReject(currentItem)}
							disabled={isProcessing}
							data-testid="reject-button"
						>
							<span class="mr-1">🚫</span> Rejeter
							<span class="ml-1 text-xs opacity-60 font-mono">R</span>
						</Button>
						<div class="relative">
							<Button
								variant="secondary"
								size="sm"
								onclick={toggleSnoozeMenu}
								disabled={isProcessing}
								data-testid="snooze-button"
							>
								<span class="mr-1">💤</span> Reporter
								<span class="ml-1 text-xs opacity-60 font-mono">S</span>
							</Button>

							<!-- Snooze dropdown menu -->
							{#if showSnoozeMenu}
								<!-- Backdrop to close menu -->
								<button
									type="button"
									class="fixed inset-0 z-40"
									onclick={() => showSnoozeMenu = false}
									aria-label="Fermer le menu"
								></button>

								<div class="absolute bottom-full left-0 mb-2 z-50 min-w-[180px] py-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] shadow-lg">
									{#each snoozeOptions as option}
										<button
											type="button"
											class="w-full text-left px-3 py-2 text-sm text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)] transition-colors disabled:opacity-50"
											onclick={() => handleSnoozeOption(option.value)}
											disabled={isSnoozing}
										>
											{option.label}
										</button>
									{/each}
								</div>
							{/if}
						</div>
						<Button
							variant={showLevel3 ? 'primary' : 'secondary'}
							size="sm"
							onclick={() => showLevel3 = !showLevel3}
						>
							<span class="mr-1">{showLevel3 ? '📖' : '📋'}</span>
							{showLevel3 ? 'Vue simple' : 'Détails'}
							<span class="ml-1 text-xs opacity-60 font-mono">E</span>
						</Button>
						<Button
							variant="secondary"
							size="sm"
							onclick={() => handleDelete(currentItem)}
							disabled={isProcessing}
						>
							<span class="mr-1">🗑️</span> Supprimer
							<span class="ml-1 text-xs opacity-60 font-mono">D</span>
						</Button>
						{#if !showCustomInput}
							<Button
								variant="secondary"
								size="sm"
								onclick={() => showCustomInput = true}
								disabled={isProcessing}
							>
								<span class="mr-1">✏️</span> Autre
								<span class="ml-1 text-xs opacity-60 font-mono">I</span>
							</Button>
						{/if}
					</div>
				</div>

				<!-- Keyboard shortcuts help -->
				<div class="text-xs text-center text-[var(--color-text-tertiary)] pt-3 flex flex-wrap justify-center gap-x-3 gap-y-1">
					<span>
						<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">J</span>
						<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded ml-0.5">K</span>
						<span class="ml-1">naviguer</span>
					</span>
					<span>
						<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">1</span>
						<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded ml-0.5">2</span>
						<span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded ml-0.5">3</span>
						<span class="ml-1">options</span>
					</span>
					<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">A</span> approuver</span>
					<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">R</span> rejeter</span>
					<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">S</span> reporter</span>
					<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">E</span> détails</span>
					<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">D</span> supprimer</span>
					<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">I</span> autre</span>
				</div>
			</div>
				</Card>
			</LongPressMenu>
		</SwipeableCard>

	<!-- LIST VIEW for other filters (approved, rejected, auto) -->
	{:else}
		<section class="list-view-container" data-testid="flux-list">
			<!-- Undo error feedback -->
			{#if undoError}
				<div class="flex items-center gap-2 p-3 mb-4 rounded-lg bg-red-500/20 text-red-400 text-sm">
					<span>⚠️</span>
					<span>{undoError}</span>
				</div>
			{/if}
			<VirtualList
				items={queueStore.items}
				estimatedItemHeight={120}
				onLoadMore={() => queueStore.loadMore()}
				hasMore={queueStore.hasMore}
				loading={queueStore.loading}
				height="calc(100vh - 280px)"
				getKey={(item) => item.id}
			>
				{#snippet item(item, _index)}
					<div class="pb-3" data-testid="flux-item-{item.id}">
						<Card padding="md" class="hover:border-[var(--color-accent)] transition-colors">
							<div class="flex items-start gap-3">
							<a href="/flux/{item.id}" class="flex items-start gap-3 flex-1 min-w-0 no-underline text-inherit">
								<!-- Action icon -->
								<div
									class="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-lg"
									style="background-color: color-mix(in srgb, {getActionColor(item.analysis.action)} 20%, transparent)"
								>
									{getActionIcon(item.analysis.action)}
								</div>

								<div class="flex-1 min-w-0">
									<!-- Subject -->
									<h3 class="font-medium text-[var(--color-text-primary)] truncate">
										{item.metadata.subject}
									</h3>

									<!-- Sender and date -->
									<p class="text-xs text-[var(--color-text-secondary)]">
										{item.metadata.from_name || item.metadata.from_address}
										<span class="text-[var(--color-text-tertiary)]">
											• {item.metadata.date ? formatRelativeTime(item.metadata.date) : formatRelativeTime(item.queued_at)}
										</span>
									</p>

									<!-- Summary -->
									{#if item.analysis.summary}
										<p class="text-xs text-[var(--color-text-tertiary)] mt-1 line-clamp-2">
											{item.analysis.summary}
										</p>
									{/if}

									<!-- Entities (compact view for list) -->
									{#if item.analysis.entities && Object.keys(item.analysis.entities).length > 0}
										{@const totalEntities = Object.values(item.analysis.entities).flat().length}
										<div class="flex flex-wrap gap-1 mt-1.5">
											{#each Object.entries(item.analysis.entities).slice(0, 3) as [type, entityList]}
												{#each entityList.slice(0, 2) as entity}
													{@const entityClass = {
														person: 'bg-blue-500/20 text-blue-300',
														project: 'bg-purple-500/20 text-purple-300',
														date: 'bg-orange-500/20 text-orange-300',
														amount: 'bg-green-500/20 text-green-300',
														organization: 'bg-cyan-500/20 text-cyan-300'
													}[type] ?? 'bg-gray-500/20 text-gray-300'}
													<span class="px-1.5 py-0.5 text-xs rounded {entityClass}">
														{entity.value}
													</span>
												{/each}
											{/each}
											{#if totalEntities > 6}
												<span class="text-xs text-[var(--color-text-tertiary)]">
													+{totalEntities - 6}
												</span>
											{/if}
										</div>
									{/if}
								</div>
							</a>

							<!-- Status indicator and actions (outside link) -->
							<div class="shrink-0 text-right flex flex-col items-end gap-2 ml-auto">
								<span
									class="text-xs px-2 py-1 rounded-full"
									class:bg-green-100={item.status === 'approved'}
									class:text-green-700={item.status === 'approved'}
									class:bg-red-100={item.status === 'rejected'}
									class:text-red-700={item.status === 'rejected'}
								>
									{getActionLabel(item.analysis.action)}
								</span>
								{#if item.reviewed_at}
									<p class="text-xs text-[var(--color-text-tertiary)]">
										{formatRelativeTime(item.reviewed_at)}
									</p>
								{/if}
								<!-- Undo button for approved items -->
								{#if item.status === 'approved' && undoableItems.has(item.id)}
									<button
										class="text-xs px-2 py-1 rounded bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors disabled:opacity-50"
										onclick={(e) => { e.stopPropagation(); handleUndoItem(item); }}
										disabled={undoingItems.has(item.id)}
									>
										{#if undoingItems.has(item.id)}
											⟳ Annulation...
										{:else}
											↩ Annuler
										{/if}
									</button>
								{/if}
							</div>
							</div>
						</Card>
					</div>
				{/snippet}

				{#snippet empty()}
					<Card padding="lg">
						<div class="text-center py-8">
							<p class="text-4xl mb-3">
								{#if activeFilter === 'approved'}✅
								{:else}🚫
								{/if}
							</p>
							<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
								{#if activeFilter === 'approved'}
									Aucun pli traité pour l'instant
								{:else}
									Aucun pli écarté
								{/if}
							</h3>
							<p class="text-sm text-[var(--color-text-secondary)]">
								Lancez le traitement des emails pour alimenter la file
							</p>
						</div>
					</Card>
				{/snippet}
			</VirtualList>
		</section>
	{/if}
</div>
