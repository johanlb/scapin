<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { Card, Button, Input, VirtualList, SwipeableCard, LongPressMenu, FolderSelector } from '$lib/components/ui';
	import type { MenuItem } from '$lib/components/ui/LongPressMenu.svelte';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { queueStore } from '$lib/stores';
	import { toastStore } from '$lib/stores/toast.svelte';
	import { approveQueueItem, undoQueueItem, canUndoQueueItem, snoozeQueueItem, processInbox, reanalyzeQueueItem, reanalyzeAllPending, recordArchive, getFolderSuggestions } from '$lib/api';
	import type { QueueItem, ActionOption, SnoozeOption, FolderSuggestion, ProposedNote, ProposedTask } from '$lib/api';
	import { registerShortcuts, createNavigationShortcuts, createQueueActionShortcuts } from '$lib/utils/keyboard-shortcuts';

	// Constants for filtering - synchronized with backend auto-apply thresholds
	// See src/core/entities.py: AUTO_APPLY_THRESHOLD and AUTO_APPLY_THRESHOLD_REQUIRED
	// Adjusted for geometric mean confidence (4 dimensions)
	const AUTO_APPLY_THRESHOLD_REQUIRED = 0.80; // Required enrichments
	const AUTO_APPLY_THRESHOLD_OPTIONAL = 0.85; // Optional enrichments
	const DAYS_THRESHOLD = 90; // Days after which a past date is considered obsolete

	/**
	 * Check if a note will be applied based on its confidence, required status, and manual override.
	 */
	function willNoteBeAutoApplied(note: ProposedNote): boolean {
		// Manual override takes precedence
		if (note.manually_approved === true) return true;
		if (note.manually_approved === false) return false;
		// Otherwise, use confidence threshold
		const threshold = note.required ? AUTO_APPLY_THRESHOLD_REQUIRED : AUTO_APPLY_THRESHOLD_OPTIONAL;
		return note.confidence >= threshold;
	}

	/**
	 * Check if a task will be auto-applied based on its confidence.
	 * Tasks are never "required", so they always use the optional threshold.
	 */
	function willTaskBeAutoApplied(task: ProposedTask): boolean {
		return task.confidence >= AUTO_APPLY_THRESHOLD_OPTIONAL;
	}

	/**
	 * Filter proposed notes to only show ones that will be auto-applied.
	 * In Details mode (showAll), shows all notes including those that won't be applied.
	 */
	function filterNotes(notes: ProposedNote[] | undefined, showAll: boolean): ProposedNote[] {
		if (!notes) return [];
		return notes.filter(note => {
			const hasValidTitle = note.title && note.title.toLowerCase() !== 'general' && note.title.trim() !== '';
			// In Details mode, show all. Otherwise only show notes that will be auto-applied
			return showAll || (hasValidTitle && willNoteBeAutoApplied(note));
		});
	}

	/**
	 * Filter proposed tasks to only show ones that will be auto-applied.
	 * Also filters out tasks with due dates > 90 days in the past.
	 * In Details mode (showAll), shows all tasks including those that won't be applied.
	 */
	function filterTasks(tasks: ProposedTask[] | undefined, showAll: boolean): ProposedTask[] {
		if (!tasks) return [];
		const ninetyDaysAgo = new Date(Date.now() - DAYS_THRESHOLD * 24 * 60 * 60 * 1000);
		return tasks.filter(task => {
			// Filter out tasks with due dates more than 90 days in the past
			let hasValidDueDate = true;
			if (task.due_date) {
				const dueDate = new Date(task.due_date);
				hasValidDueDate = !isNaN(dueDate.getTime()) && dueDate >= ninetyDaysAgo;
			}
			// In Details mode, show all. Otherwise only show tasks that will be auto-applied
			return showAll || (willTaskBeAutoApplied(task) && hasValidDueDate);
		});
	}

	/**
	 * Check if a date is in the past.
	 */
	function isDatePast(dateStr: string | null | undefined): boolean {
		if (!dateStr) return false;
		const date = new Date(dateStr);
		return !isNaN(date.getTime()) && date < new Date();
	}

	/**
	 * Check if a date is obsolete (> 30 days in the past).
	 */
	function isDateObsolete(dateStr: string | null | undefined): boolean {
		if (!dateStr) return false;
		const date = new Date(dateStr);
		const thirtyDaysAgo = new Date(Date.now() - DAYS_THRESHOLD * 24 * 60 * 60 * 1000);
		return !isNaN(date.getTime()) && date < thirtyDaysAgo;
	}

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

	// Reanalyze state
	let isReanalyzing = $state(false);

	// Folder selector state
	let showFolderSelector = $state(false);
	let pendingArchiveItem = $state<QueueItem | null>(null);
	let pendingArchiveOption = $state<ActionOption | null>(null);
	let folderSuggestion = $state<FolderSuggestion | null>(null);

	// Bug #49: Auto-fetch threshold
	const AUTO_FETCH_THRESHOLD = 20;
	const AUTO_FETCH_COOLDOWN_MS = 60000; // 1 minute cooldown between auto-fetches
	let autoFetchEnabled = $state(true); // Can be disabled by user
	let lastAutoFetchTime = $state(0); // Timestamp of last auto-fetch

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

		// Bug #49: Check if we need to auto-fetch after initial load
		checkAutoFetch();

		// Register context-specific keyboard shortcuts
		const navigationShortcuts = createNavigationShortcuts(
			() => navigatePrevious(),
			() => navigateNext(),
			'/flux'
		);

		const actionShortcuts = createQueueActionShortcuts(
			() => handleApproveRecommended(),
			() => toggleOpusPanel(),  // R = Toggle Opus panel
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
	let showLevel3: boolean = $state(false);
	let showHtmlContent: boolean = $state(true);

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

		// Bug #50 fix: Use a longer-duration toast that stays visible during processing
		const processingToastId = toastStore.info(
			'Récupération et analyse des emails en cours...',
			{ title: 'Traitement', duration: 120000 } // 2 minutes max
		);

		try {
			// Note: unreadOnly=false to process all emails, not just unread ones
			const result = await processInbox(20, false, undefined, false);

			// Dismiss the processing toast
			toastStore.dismiss(processingToastId);

			// Bug #50 fix: Refresh queue FIRST before showing success toast
			// This ensures UI updates immediately
			await queueStore.fetchQueue('pending');
			await queueStore.fetchStats();

			// Show success toast with results
			if (result.total_processed > 0) {
				const queuedCount = result.queued || 0;
				toastStore.success(
					`${result.total_processed} email${result.total_processed > 1 ? 's' : ''} analysé${result.total_processed > 1 ? 's' : ''} et ${queuedCount} ajouté${queuedCount > 1 ? 's' : ''} à la file`,
					{ title: 'Courrier récupéré' }
				);
			} else {
				toastStore.info(
					'Aucun nouvel email à traiter',
					{ title: 'Boîte de réception à jour' }
				);
			}
		} catch (err) {
			// Dismiss the processing toast
			toastStore.dismiss(processingToastId);

			fetchError = err instanceof Error ? err.message : 'Erreur de connexion';
			toastStore.error(
				'Impossible de récupérer le courrier. Vérifiez la connexion au serveur.',
				{ title: 'Erreur' }
			);
		} finally {
			isFetchingEmails = false;
		}
	}

	// Re-analyze all pending items
	async function handleReanalyzeAll() {
		if (isReanalyzing) return;

		const pendingCount = queueStore.stats?.by_status?.pending ?? queueStore.items.length;
		if (pendingCount === 0) {
			toastStore.info('Aucun élément à réanalyser', { title: 'File vide' });
			return;
		}

		isReanalyzing = true;

		const processingToastId = toastStore.info(
			`Réanalyse de ${pendingCount} élément${pendingCount > 1 ? 's' : ''} en cours...`,
			{ title: 'Réanalyse', duration: 300000 } // 5 minutes max
		);

		try {
			const result = await reanalyzeAllPending();

			toastStore.dismiss(processingToastId);

			// Refresh queue
			await queueStore.fetchQueue('pending');
			await queueStore.fetchStats();

			if (result.started > 0) {
				toastStore.success(
					`${result.started}/${result.total_items} élément${result.started > 1 ? 's' : ''} réanalysé${result.started > 1 ? 's' : ''}${result.failed > 0 ? ` (${result.failed} échec${result.failed > 1 ? 's' : ''})` : ''}`,
					{ title: 'Réanalyse terminée' }
				);
			} else {
				toastStore.warning(
					'Aucun élément n\'a pu être réanalysé',
					{ title: 'Réanalyse échouée' }
				);
			}
		} catch (err) {
			toastStore.dismiss(processingToastId);
			toastStore.error(
				'Impossible de réanalyser les éléments. Vérifiez la connexion au serveur.',
				{ title: 'Erreur' }
			);
		} finally {
			isReanalyzing = false;
		}
	}

	// Bug #49: Auto-fetch when queue is low
	async function checkAutoFetch() {
		// Only auto-fetch in pending view when enabled and not already fetching
		if (!autoFetchEnabled || isFetchingEmails || activeFilter !== 'pending') return;

		// Check cooldown to prevent spamming
		const now = Date.now();
		if (now - lastAutoFetchTime < AUTO_FETCH_COOLDOWN_MS) {
			return; // Still in cooldown period
		}

		// Check if queue is below threshold
		const pendingCount = queueStore.stats?.by_status?.pending ?? queueStore.items.length;
		if (pendingCount < AUTO_FETCH_THRESHOLD) {
			// Update cooldown timestamp
			lastAutoFetchTime = now;
			// Show subtle notification
			toastStore.info(
				`Moins de ${AUTO_FETCH_THRESHOLD} emails en attente. Récupération automatique...`,
				{ title: 'Auto-fetch' }
			);
			await handleFetchEmails();
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
			case 'v':
			case 'V':
				// v for details (legacy shortcut, e also works via centralized system)
				showLevel3 = !showLevel3;
				break;
			case 'Escape':
				showLevel3 = false;
				showSnoozeMenu = false;
				customInstruction = '';
				break;
		}
	}

	async function handleSelectOption(item: QueueItem, option: ActionOption) {
		if (isProcessing) return;

		// For archive action: check if we have a destination
		if (option.action === 'archive') {
			const destination = option.destination;

			if (!destination) {
				// No destination - try to get AI suggestion
				try {
					const suggestions = await getFolderSuggestions(
						item.metadata.from_address,
						item.metadata.subject,
						1
					);

					if (suggestions.suggestions.length > 0 && suggestions.suggestions[0].confidence >= 0.8) {
						// High confidence suggestion - use it directly
						await executeArchiveWithFolder(item, option, suggestions.suggestions[0].folder);
						return;
					} else {
						// No high-confidence suggestion - show folder selector
						pendingArchiveItem = item;
						pendingArchiveOption = option;
						folderSuggestion = suggestions.suggestions[0] || null;
						showFolderSelector = true;
						return;
					}
				} catch {
					// On error, show folder selector
					pendingArchiveItem = item;
					pendingArchiveOption = option;
					folderSuggestion = null;
					showFolderSelector = true;
					return;
				}
			}
			// Has destination - use it directly
			await executeArchiveWithFolder(item, option, destination);
			return;
		}

		// Non-archive action - proceed normally
		await executeAction(item, option, option.destination ?? undefined);
	}

	// Open folder selector to choose a different folder
	function handleArchiveElsewhere(item: QueueItem) {
		pendingArchiveItem = item;
		pendingArchiveOption = {
			action: 'archive',
			confidence: 0,
			reasoning: 'Classement manuel',
			reasoning_detailed: null,
			destination: null,
			is_recommended: false
		};
		folderSuggestion = null;
		showFolderSelector = true;
	}

	async function executeArchiveWithFolder(item: QueueItem, option: ActionOption, folder: string) {
		// Record the archive for learning
		try {
			await recordArchive(folder, item.metadata.from_address, item.metadata.subject);
		} catch (e) {
			console.error('Failed to record archive for learning:', e);
			// Continue anyway - recording is not critical
		}

		// Execute the action with the selected folder
		await executeAction(item, option, folder);
	}

	async function executeAction(item: QueueItem, option: ActionOption, destination?: string) {
		// Save item info for undo and potential restore
		const itemId = item.id;
		const itemSubject = item.metadata.subject;
		const actionLabel = getActionLabel(option.action);
		const savedItem = { ...item }; // Deep copy for restore on error

		// Optimistic update - immediately update UI and move to next item
		queueStore.removeFromList(item.id);

		// Move to next or reset
		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}
		customInstruction = '';
		showOpusPanel = false;
		showLevel3 = false;

		// Show immediate feedback toast with undo option
		toastStore.undo(
			`${actionLabel} : ${itemSubject.slice(0, 40)}${itemSubject.length > 40 ? '...' : ''}`,
			async () => {
				await undoQueueItem(itemId);
				await queueStore.fetchQueue('pending');
				await queueStore.fetchStats();
			},
			{ itemId, title: 'Action effectuée' }
		);

		// Execute action in background (fire and forget)
		approveQueueItem(item.id, option.action, item.analysis.category || undefined, destination)
			.then(() => {
				// Update stats in background
				queueStore.fetchStats();
				// Check if we need to auto-fetch
				checkAutoFetch();
			})
			.catch((e) => {
				// Restore item if action failed
				console.error('Action failed:', e);
				queueStore.restoreItem(savedItem);
				toastStore.error(
					`Échec de l'action "${actionLabel}". L'email a été restauré.`,
					{ title: 'Erreur IMAP' }
				);
			});
	}

	function handleFolderSelect(folder: string) {
		if (pendingArchiveItem && pendingArchiveOption) {
			executeArchiveWithFolder(pendingArchiveItem, pendingArchiveOption, folder);
		}
		closeFolderSelector();
	}

	function closeFolderSelector() {
		showFolderSelector = false;
		pendingArchiveItem = null;
		pendingArchiveOption = null;
		folderSuggestion = null;
	}

	async function handleCustomInstruction(item: QueueItem) {
		if (isProcessing || isReanalyzing || !customInstruction.trim()) return;
		isReanalyzing = true;

		const itemId = item.id;
		const savedInstruction = customInstruction.trim();

		// Clear the input but don't close the panel yet - show "Analysing..."
		customInstruction = '';

		try {
			// Bug #55 fix: Call reanalyzeQueueItem to get a new analysis
			const result = await reanalyzeQueueItem(itemId, savedInstruction, 'immediate');

			if (result.status === 'complete' && result.new_analysis) {
				// Update the item in the store with the new analysis
				queueStore.updateItemAnalysis(itemId, result.new_analysis);

								toastStore.success(
					`Nouvelle analyse effectuée pour : ${item.metadata.subject.slice(0, 30)}${item.metadata.subject.length > 30 ? '...' : ''}`,
					{ title: 'Analyse terminée' }
				);
			} else if (result.status === 'failed') {
				customInstruction = savedInstruction; // Restore instruction on failure
				toastStore.error(
					`La ré-analyse a échoué. Veuillez réessayer.`,
					{ title: 'Erreur' }
				);
			}
		} catch (e) {
			console.error('Reanalysis failed:', e);
			customInstruction = savedInstruction; // Restore instruction on error
			toastStore.error(
				`Échec de la ré-analyse. Veuillez réessayer.`,
				{ title: 'Erreur' }
			);
		} finally {
			isReanalyzing = false;
		}
	}

	// Reanalyze with Opus state
	let isReanalyzingOpus = $state(false);
	let showOpusPanel = $state(false);
	let opusInstruction = $state('');

	function toggleOpusPanel() {
		showOpusPanel = !showOpusPanel;
		if (!showOpusPanel) {
			opusInstruction = '';
		}
	}

	async function handleReanalyzeOpus(item: QueueItem, mode: 'immediate' | 'background' = 'immediate') {
		if (isReanalyzingOpus || isProcessing) return;
		isReanalyzingOpus = true;
		showOpusPanel = false;

		const instruction = opusInstruction.trim();
		opusInstruction = '';

		const processingToastId = mode === 'immediate'
			? toastStore.info(
				instruction ? `Réanalyse avec instruction: "${instruction.slice(0, 50)}..."` : 'Réanalyse en cours avec Opus...',
				{ title: 'Analyse approfondie', duration: 120000 }
			)
			: toastStore.info(
				'Réanalyse en file d\'attente',
				{ title: 'Analyse Opus', duration: 3000 }
			);

		try {
			const result = await reanalyzeQueueItem(item.id, instruction, mode, 'opus');

			toastStore.dismiss(processingToastId);

			if (mode === 'background') {
				toastStore.success(
					'L\'analyse sera effectuée en arrière-plan.',
					{ title: 'Analyse programmée' }
				);
			} else if (result.status === 'complete' && result.new_analysis) {
				// Refresh queue to get updated item
				await queueStore.fetchQueue('pending');
				await queueStore.fetchStats();

				toastStore.success(
					`Nouvelle analyse terminée. Action: ${result.new_analysis.action} (${result.new_analysis.confidence}%)`,
					{ title: 'Analyse Opus' }
				);
			} else {
				toastStore.warning(
					'La réanalyse n\'a pas produit de nouveau résultat.',
					{ title: 'Analyse Opus' }
				);
			}
		} catch (e) {
			toastStore.dismiss(processingToastId);
			console.error('Reanalyze with Opus failed:', e);
			toastStore.error(
				'Échec de la réanalyse. Veuillez réessayer.',
				{ title: 'Erreur' }
			);
		} finally {
			isReanalyzingOpus = false;
		}
	}

	function handleDelete(item: QueueItem) {
		// Save item info for undo and potential restore
		const itemId = item.id;
		const itemSubject = item.metadata.subject;
		const savedItem = { ...item };

		// Optimistic update - immediately update UI
		queueStore.removeFromList(item.id);

		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}
		customInstruction = '';
		showOpusPanel = false;
		showLevel3 = false;

		// Show immediate feedback toast with undo option
		toastStore.undo(
			`Supprimé : ${itemSubject.slice(0, 40)}${itemSubject.length > 40 ? '...' : ''}`,
			async () => {
				await undoQueueItem(itemId);
				await queueStore.fetchQueue('pending');
				await queueStore.fetchStats();
			},
			{ itemId, title: 'Email déplacé vers la corbeille' }
		);

		// Execute action in background (fire and forget)
		approveQueueItem(item.id, 'delete', item.analysis.category || undefined)
			.then(() => {
				queueStore.fetchStats();
				checkAutoFetch();
			})
			.catch((e) => {
				console.error('Delete failed:', e);
				queueStore.restoreItem(savedItem);
				toastStore.error(
					`Échec de la suppression. L'email a été restauré.`,
					{ title: 'Erreur IMAP' }
				);
			});
	}

	function handleSkip() {
		// Move to next item without action
		if (currentIndex < queueStore.items.length - 1) {
			currentIndex++;
		} else {
			currentIndex = 0; // Loop back to start
		}
		customInstruction = '';
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

			// Bug #49: Check if we need to auto-fetch
			checkAutoFetch();

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

			// Bug #49: Check if we need to auto-fetch
			checkAutoFetch();

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
			pending: 'En attente',
			rien: 'Aucune action'
		};
		return labels[action.toLowerCase()] || action;
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
			review: '👁️',
			rien: '➖',
			pending: '⏳'
		};
		return icons[action.toLowerCase()] || '📋';
	}

	function getActionColor(action: string): string {
		const colors: Record<string, string> = {
			archive: 'var(--color-success)',
			delete: 'var(--color-urgency-urgent)',
			reply: 'var(--color-accent)',
			flag: 'var(--color-warning)',
			task: 'var(--color-event-omnifocus)',
			queue: 'var(--color-warning)',
			review: 'var(--color-warning)',
			pending: 'var(--color-warning)',
			rien: 'var(--color-text-tertiary)'
		};
		return colors[action.toLowerCase()] || 'var(--color-text-secondary)';
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

		// Reanalyze with Opus
		menuItems.push({
			id: 'reanalyze-opus',
			label: 'Réanalyser (Opus)',
			icon: '🧠',
			handler: () => toggleOpusPanel()
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
		icon: '🧠',
		label: 'Opus',
		color: 'var(--color-accent)',
		action: () => toggleOpusPanel()
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

				<!-- Re-analyze all button -->
				{#if activeFilter === 'pending' && queueStore.items.length > 0}
					<Button
						variant="secondary"
						size="sm"
						onclick={handleReanalyzeAll}
						disabled={isReanalyzing}
					>
						{#if isReanalyzing}
							<span class="mr-1.5 animate-spin">🔄</span>
							Réanalyse...
						{:else}
							<span class="mr-1.5">🔄</span>
							Réanalyser
						{/if}
					</Button>
				{/if}

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

	<!-- Stats as compact clickable filters -->
	<section class="flex gap-2 mb-4 text-sm">
		<button
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5"
			class:bg-[var(--color-accent)]={activeFilter === 'pending'}
			class:text-white={activeFilter === 'pending'}
			class:bg-[var(--color-bg-secondary)]={activeFilter !== 'pending'}
			class:text-[var(--color-text-secondary)]={activeFilter !== 'pending'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeFilter !== 'pending'}
			onclick={() => changeFilter('pending')}
		>
			<span class="font-bold text-[var(--color-warning)]" class:text-white={activeFilter === 'pending'}>
				{stats?.by_status?.pending ?? 0}
			</span>
			<span>en attente</span>
		</button>

		<button
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5"
			class:bg-[var(--color-accent)]={activeFilter === 'approved'}
			class:text-white={activeFilter === 'approved'}
			class:bg-[var(--color-bg-secondary)]={activeFilter !== 'approved'}
			class:text-[var(--color-text-secondary)]={activeFilter !== 'approved'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeFilter !== 'approved'}
			onclick={() => changeFilter('approved')}
		>
			<span class="font-bold text-[var(--color-success)]" class:text-white={activeFilter === 'approved'}>
				{stats?.by_status?.approved ?? 0}
			</span>
			<span>traités</span>
		</button>

		<button
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5"
			class:bg-[var(--color-accent)]={activeFilter === 'rejected'}
			class:text-white={activeFilter === 'rejected'}
			class:bg-[var(--color-bg-secondary)]={activeFilter !== 'rejected'}
			class:text-[var(--color-text-secondary)]={activeFilter !== 'rejected'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeFilter !== 'rejected'}
			onclick={() => changeFilter('rejected')}
		>
			<span class="font-bold text-[var(--color-urgency-urgent)]" class:text-white={activeFilter === 'rejected'}>
				{stats?.by_status?.rejected ?? 0}
			</span>
			<span>écartés</span>
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

	<!-- SINGLE ITEM VIEW for pending items - REDESIGNED UI -->
	{:else if activeFilter === 'pending' && currentItem}
		{@const options = currentItem.analysis.options || []}
		{@const hasOptions = options.length > 0}
		{@const recommendedOption = options.find(o => o.is_recommended) || options[0]}
		{@const otherOptions = options.filter(o => o !== recommendedOption)}
		{@const notesCount = filterNotes(currentItem.analysis.proposed_notes, false).length}
		{@const tasksCount = filterTasks(currentItem.analysis.proposed_tasks, false).length}
		{@const enrichmentsCount = notesCount + tasksCount}

		<!-- Collapsible state for enrichments -->
		{#snippet enrichmentsSection()}
			{@const notes = filterNotes(currentItem.analysis.proposed_notes, showLevel3)}
			{@const tasks = filterTasks(currentItem.analysis.proposed_tasks, showLevel3)}
			{#if notes.length > 0 || tasks.length > 0}
				<div class="space-y-2">
					{#each notes as note, noteIndex}
						{@const noteActionClass = note.action === 'create' ? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300' : 'bg-amber-100 text-amber-700 dark:bg-yellow-500/20 dark:text-yellow-300'}
						{@const willApply = willNoteBeAutoApplied(note)}
						{@const threshold = note.required ? AUTO_APPLY_THRESHOLD_REQUIRED : AUTO_APPLY_THRESHOLD_OPTIONAL}
						{@const isManuallySet = note.manually_approved !== null && note.manually_approved !== undefined}
						{@const isChecked = note.manually_approved === true || (note.manually_approved !== false && willApply)}
						<div class="rounded-lg border border-[var(--color-border)] p-2 {!isChecked ? 'opacity-60' : ''}">
							<div class="flex items-center justify-between text-sm">
								<span class="flex items-center gap-2">
									<input
										type="checkbox"
										checked={isChecked}
										class="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
										title={isManuallySet ? (note.manually_approved ? 'Forcé' : 'Rejeté') : (willApply ? 'Auto' : 'Manuel')}
										onchange={() => queueStore.toggleNoteApproval(currentItem.id, noteIndex)}
									/>
									<span class="text-xs px-1.5 py-0.5 rounded {noteActionClass}">
										{note.action === 'create' ? '+' : '~'} {note.note_type}
									</span>
									{#if note.required}
										<span class="text-xs px-1 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300">!</span>
									{/if}
									<span class="text-[var(--color-text-primary)] font-medium">{note.title || 'Sans titre'}</span>
								</span>
								<span class="text-xs font-medium px-1.5 py-0.5 rounded {isChecked ? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300' : 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300'}">
									{Math.round(note.confidence * 100)}%
								</span>
							</div>
							{#if note.content_summary}
								<p class="mt-1.5 text-xs text-[var(--color-text-secondary)] pl-6 border-l-2 border-[var(--color-border)] ml-2">
									{note.content_summary}
								</p>
							{/if}
						</div>
					{/each}
					{#each tasks as task, taskIndex}
						{@const willApply = willTaskBeAutoApplied(task)}
						{@const isPastDue = isDateObsolete(task.due_date)}
						{@const isManuallySet = task.manually_approved !== null && task.manually_approved !== undefined}
						{@const isChecked = task.manually_approved === true || (task.manually_approved !== false && willApply && !isPastDue)}
						<div class="rounded-lg border border-[var(--color-border)] p-2 {!isChecked ? 'opacity-60' : ''}">
							<div class="flex items-center justify-between text-sm">
								<span class="flex items-center gap-2">
									<input
										type="checkbox"
										checked={isChecked}
										class="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500 cursor-pointer"
										title={task.manually_approved !== null ? (task.manually_approved ? 'Forcé' : 'Rejeté') : (willApply ? 'Auto' : 'Manuel')}
										onchange={() => queueStore.toggleTaskApproval(currentItem.id, taskIndex)}
									/>
									<span class="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300">📋 OmniFocus</span>
									<span class="text-[var(--color-text-primary)] font-medium">{task.title}</span>
								</span>
								<span class="text-xs font-medium px-1.5 py-0.5 rounded {isChecked ? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300' : 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300'}">
									{Math.round(task.confidence * 100)}%
								</span>
							</div>
							<div class="mt-1.5 text-xs text-[var(--color-text-secondary)] pl-6 border-l-2 border-[var(--color-border)] ml-2 space-y-0.5">
								{#if task.note}
									<p>{task.note}</p>
								{/if}
								<p class="flex items-center gap-2">
									{#if task.project}
										<span>📁 {task.project}</span>
									{/if}
									{#if task.due_date}
										<span class="{isDatePast(task.due_date) ? 'text-red-500 line-through' : 'text-orange-500'}">
											📅 {task.due_date}
										</span>
									{/if}
								</p>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		{/snippet}

		<!-- Mobile swipe hint -->
		<div class="text-xs text-center text-[var(--color-text-tertiary)] py-1 mb-2 md:hidden">
			← Opus • Appui long = menu • Approuver →
		</div>

		<SwipeableCard
			rightAction={swipeRightAction}
			leftAction={swipeLeftAction}
			threshold={100}
		>
			<LongPressMenu items={getMobileMenuItems(currentItem)}>
				<Card padding="md">
					<div class="space-y-3">
						<!-- SECTION 1: ACTION BAR (fixed at top) -->
						<div class="flex flex-wrap items-center gap-2 pb-3 border-b border-[var(--color-border)]">
							<!-- Navigation -->
							<div class="flex items-center gap-1 text-sm text-[var(--color-text-tertiary)]">
								<button onclick={navigatePrevious} class="hover:text-[var(--color-accent)] p-1 -ml-1">←</button>
								<span class="font-medium">{currentIndex + 1}/{queueStore.items.length}</span>
								<button onclick={navigateNext} class="hover:text-[var(--color-accent)] p-1">→</button>
							</div>
							<div class="w-px h-5 bg-[var(--color-border)]"></div>
							<!-- Main actions -->
							<Button
								variant="primary"
								size="sm"
								onclick={handleApproveRecommended}
								disabled={isProcessing}
								data-testid="approve-button"
							>
								✓ <span class="hidden sm:inline">Approuver</span> <span class="opacity-60 font-mono text-xs">A</span>
							</Button>
							<Button
								variant={showOpusPanel ? 'primary' : 'secondary'}
								size="sm"
								onclick={toggleOpusPanel}
								disabled={isProcessing || isReanalyzingOpus}
								data-testid="reanalyze-opus-button"
							>
								{#if isReanalyzingOpus}
									⏳
								{:else}
									🧠 <span class="opacity-60 font-mono text-xs">R</span>
								{/if}
							</Button>
							{#if otherOptions.length > 0}
								<Button
									variant="secondary"
									size="sm"
									onclick={() => showLevel3 = !showLevel3}
								>
									+{otherOptions.length}
								</Button>
							{/if}
							<div class="flex-1"></div>
							<!-- Secondary actions -->
							<Button variant="ghost" size="sm" onclick={() => handleArchiveElsewhere(currentItem)} disabled={isProcessing}>
								📁
							</Button>
							<Button variant="ghost" size="sm" onclick={() => handleDelete(currentItem)} disabled={isProcessing}>
								🗑️
							</Button>
							<div class="relative">
								<Button variant="ghost" size="sm" onclick={toggleSnoozeMenu} disabled={isProcessing} data-testid="snooze-button">
									💤
								</Button>
								{#if showSnoozeMenu}
									<button type="button" class="fixed inset-0 z-40" onclick={() => showSnoozeMenu = false} aria-label="Fermer"></button>
									<div class="absolute top-full right-0 mt-1 z-50 min-w-[160px] py-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] shadow-lg">
										{#each snoozeOptions as option}
											<button
												type="button"
												class="w-full text-left px-3 py-2 text-sm hover:bg-[var(--color-bg-secondary)]"
												onclick={() => handleSnoozeOption(option.value)}
												disabled={isSnoozing}
											>{option.label}</button>
										{/each}
									</div>
								{/if}
							</div>
							<Button
								variant={showLevel3 ? 'primary' : 'ghost'}
								size="sm"
								onclick={() => showLevel3 = !showLevel3}
							>
								{showLevel3 ? '📖' : '📋'}
							</Button>
						</div>

						<!-- SECTION 2: EMAIL HEADER -->
						<div class="flex items-start justify-between gap-3">
							<div class="flex-1 min-w-0">
								<h2 class="text-lg font-bold text-[var(--color-text-primary)] leading-tight">
									{currentItem.metadata.subject}
								</h2>
								<p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
									{currentItem.metadata.from_name || currentItem.metadata.from_address}
									<span class="text-[var(--color-text-tertiary)]">•</span>
									<span class="text-[var(--color-text-tertiary)]">
										{currentItem.metadata.date ? formatRelativeTime(currentItem.metadata.date) : formatRelativeTime(currentItem.queued_at)}
									</span>
									{#if currentItem.metadata.has_attachments}
										<span class="text-[var(--color-text-tertiary)]">• 📎</span>
									{/if}
									{#if currentItem.analysis.category}
										<span class="text-[var(--color-text-tertiary)]">•</span>
										<span class="text-xs px-1.5 py-0.5 rounded bg-[var(--color-bg-tertiary)]">
											{getCategoryLabel(currentItem.analysis.category)}
										</span>
									{/if}
								</p>
							</div>
						</div>

						<!-- SECTION 3: RECOMMENDATION -->
						{#if hasOptions && recommendedOption}
							<div class="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-[var(--color-bg-secondary)] to-[var(--color-bg-tertiary)] border border-[var(--color-accent)]/30">
								<div
									class="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0"
									style="background-color: color-mix(in srgb, {getActionColor(recommendedOption.action)} 25%, transparent)"
								>
									{getActionIcon(recommendedOption.action)}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-bold" style="color: {getActionColor(recommendedOption.action)}">
											{getActionLabel(recommendedOption.action)}
										</span>
										<div class="flex-1 max-w-[80px] h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
											<div
												class="h-full rounded-full"
												style="width: {recommendedOption.confidence}%; background-color: {getConfidenceColor(recommendedOption.confidence)}"
											></div>
										</div>
										<span class="text-xs font-medium" style="color: {getConfidenceColor(recommendedOption.confidence)}">
											{recommendedOption.confidence}%
										</span>
										{#if recommendedOption.destination}
											<span class="text-xs text-[var(--color-text-tertiary)]">→ {recommendedOption.destination}</span>
										{/if}
									</div>
									<p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
										{recommendedOption.reasoning}
									</p>
								</div>
							</div>
						{:else}
							<!-- Fallback when no options -->
							<div class="flex items-center gap-3 p-3 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
								<div
									class="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0"
									style="background-color: color-mix(in srgb, {getActionColor(currentItem.analysis.action)} 25%, transparent)"
								>
									{getActionIcon(currentItem.analysis.action)}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span class="font-bold" style="color: {getActionColor(currentItem.analysis.action)}">
											{getActionLabel(currentItem.analysis.action)}
										</span>
										<div class="flex-1 max-w-[80px] h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
											<div
												class="h-full rounded-full"
												style="width: {currentItem.analysis.confidence}%; background-color: {getConfidenceColor(currentItem.analysis.confidence)}"
											></div>
										</div>
										<span class="text-xs font-medium" style="color: {getConfidenceColor(currentItem.analysis.confidence)}">
											{currentItem.analysis.confidence}%
										</span>
									</div>
									{#if currentItem.analysis.reasoning}
										<p class="text-sm text-[var(--color-text-secondary)] mt-0.5">{currentItem.analysis.reasoning}</p>
									{/if}
								</div>
							</div>
						{/if}

						<!-- SECTION 4: ENRICHMENTS (visible by default) -->
						{#if enrichmentsCount > 0}
							<div class="space-y-2">
								<div class="flex items-center gap-2">
									<span class="text-sm font-medium text-[var(--color-text-primary)]">
										📝 {enrichmentsCount} enrichissement{enrichmentsCount > 1 ? 's' : ''}
									</span>
									{#if filterNotes(currentItem.analysis.proposed_notes, false).some(n => n.required)}
										<span class="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300">requis</span>
									{/if}
								</div>
								{@render enrichmentsSection()}
							</div>
						{/if}

						<!-- SECTION 5: OPUS INSTRUCTION PANEL (when visible) -->
						{#if showOpusPanel}
							<div class="p-3 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800">
								<div class="flex items-center gap-2 mb-2">
									<span class="text-lg">🧠</span>
									<span class="text-sm font-medium text-purple-800 dark:text-purple-200">Réanalyse avec Opus</span>
								</div>
								<textarea
									bind:value={opusInstruction}
									placeholder="Instruction personnalisée (optionnel) : ex. Classer dans Archive/2025/Relevés..."
									class="w-full p-2 text-sm rounded border border-purple-200 dark:border-purple-700 bg-white dark:bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
									rows="2"
								></textarea>
								<div class="flex gap-2 mt-2">
									<Button
										variant="primary"
										size="sm"
										onclick={() => handleReanalyzeOpus(currentItem, 'immediate')}
										disabled={isReanalyzingOpus}
									>
										▶️ Maintenant
									</Button>
									<Button
										variant="secondary"
										size="sm"
										onclick={() => handleReanalyzeOpus(currentItem, 'background')}
										disabled={isReanalyzingOpus}
									>
										📥 Plus tard
									</Button>
									<div class="flex-1"></div>
									<Button
										variant="ghost"
										size="sm"
										onclick={toggleOpusPanel}
									>
										Annuler
									</Button>
								</div>
							</div>
						{/if}

						<!-- SECTION 6: Other options (Details mode) -->
						{#if showLevel3 && otherOptions.length > 0}
							<div class="space-y-2">
								<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">Autres options</p>
								{#each otherOptions as option, idx}
									<button
										class="w-full text-left p-3 rounded-lg border border-[var(--color-border)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)] transition-all"
										disabled={isProcessing}
										onclick={() => handleSelectOption(currentItem, option)}
									>
										<div class="flex items-center gap-2">
											<span class="w-6 h-6 rounded bg-[var(--color-bg-tertiary)] flex items-center justify-center text-xs font-mono">{idx + 2}</span>
											<span class="text-lg">{getActionIcon(option.action)}</span>
											<span class="font-medium" style="color: {getActionColor(option.action)}">{getActionLabel(option.action)}</span>
											<span class="text-xs ml-auto" style="color: {getConfidenceColor(option.confidence)}">{option.confidence}%</span>
										</div>
										<p class="text-xs text-[var(--color-text-secondary)] mt-1 ml-8">{option.reasoning}</p>
									</button>
								{/each}
							</div>
						{/if}

						<!-- SECTION 7: Entities (Details mode) -->
						{#if showLevel3 && currentItem.analysis.entities && Object.keys(currentItem.analysis.entities).length > 0}
							<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
								<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase mb-2">Entités extraites</p>
								<div class="flex flex-wrap gap-1">
									{#each Object.entries(currentItem.analysis.entities) as [type, entities]}
										{#each entities as entity}
											{@const entityClass = {
												person: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
												project: 'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
												date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
												amount: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
												organization: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300'
											}[type] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'}
											<span class="px-2 py-0.5 text-xs rounded-full {entityClass}">{entity.value}</span>
										{/each}
									{/each}
								</div>
							</div>
						{/if}

						<!-- SECTION 8: Context & Metadata (Details mode) -->
						{#if showLevel3}
							{#if currentItem.analysis.context_used && currentItem.analysis.context_used.length > 0}
								<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
									<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase mb-1">Contexte utilisé</p>
									<div class="flex flex-wrap gap-1">
										{#each currentItem.analysis.context_used as noteId}
											<a href="/notes/{noteId}" class="text-xs px-2 py-0.5 rounded-full bg-[var(--color-event-notes)]/20 text-[var(--color-event-notes)] hover:bg-[var(--color-event-notes)]/30">
												📝 {noteId.slice(0, 15)}...
											</a>
										{/each}
									</div>
								</div>
							{/if}
							<div class="flex flex-wrap gap-2 text-xs text-[var(--color-text-tertiary)] p-2 rounded-lg bg-[var(--color-bg-secondary)]">
								<span>📧 {currentItem.metadata.from_address}</span>
								<span>📁 {currentItem.metadata.folder || 'INBOX'}</span>
								<span>🕐 {formatRelativeTime(currentItem.queued_at)}</span>
							</div>
						{/if}

						<!-- SECTION 9: Custom instruction (Details mode) -->
						{#if showLevel3}
							<div class="p-3 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50">
								<div class="flex items-center gap-2 mb-2">
									<span>✏️</span>
									<span class="text-sm font-medium text-[var(--color-text-secondary)]">Instruction personnalisée</span>
								</div>
								<Input
									placeholder="Votre instruction..."
									bind:value={customInstruction}
									disabled={isProcessing || isReanalyzing}
								/>
								<div class="flex gap-2 mt-2">
									<Button
										variant="primary"
										size="sm"
										onclick={() => handleCustomInstruction(currentItem)}
										disabled={isProcessing || isReanalyzing || !customInstruction.trim()}
									>
										{isReanalyzing ? '⏳' : '🔄'} Analyser
									</Button>
									<Button
										variant="secondary"
										size="sm"
										onclick={() => handleDeferCustomInstruction(currentItem)}
										disabled={isProcessing || isSnoozing || isReanalyzing || !customInstruction.trim()}
									>
										⏰ Plus tard
									</Button>
								</div>
							</div>
						{/if}

						<!-- SECTION 10: EMAIL (at bottom, larger height) -->
						<div class="rounded-lg border border-[var(--color-border)] overflow-hidden">
							<div class="flex items-center justify-between px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]">
								<span class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">Email</span>
								{#if currentItem.content?.html_body}
									<div class="flex gap-1">
										<button
											class="text-xs px-2 py-0.5 rounded {!showHtmlContent ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
											onclick={() => showHtmlContent = false}
										>Texte</button>
										<button
											class="text-xs px-2 py-0.5 rounded {showHtmlContent ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
											onclick={() => showHtmlContent = true}
										>HTML</button>
									</div>
								{/if}
							</div>
							{#if showHtmlContent && currentItem.content?.html_body}
								<iframe
									srcdoc={currentItem.content.html_body}
									sandbox=""
									class="w-full h-96 bg-white"
									title="Email HTML"
								></iframe>
							{:else}
								<div class="p-3 text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap max-h-96 overflow-y-auto bg-[var(--color-bg-primary)]">
									{currentItem.content?.full_text || currentItem.content?.preview || 'Aucun contenu'}
								</div>
							{/if}
						</div>

						<!-- Keyboard help (compact) -->
						<div class="text-xs text-center text-[var(--color-text-tertiary)] flex flex-wrap justify-center gap-2">
							<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">J/K</span> nav</span>
							<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">A</span> approuver</span>
							<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">R</span> opus</span>
							<span><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">E</span> détails</span>
						</div>

						<!-- Snooze/Error feedback -->
						{#if snoozeSuccess}
							<div class="flex items-center gap-2 p-2 rounded-lg bg-green-500/20 text-green-400 text-sm">
								<span>💤</span><span>{snoozeSuccess}</span>
							</div>
						{:else if snoozeError}
							<div class="flex items-center gap-2 p-2 rounded-lg bg-red-500/20 text-red-400 text-sm">
								<span>⚠️</span><span>{snoozeError}</span>
							</div>
						{/if}
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
														person: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
														project: 'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
														date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
														amount: 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
														organization: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300',
														discovered: 'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300'
													}[type] ?? 'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'}
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

<!-- Folder Selector Modal -->
{#if showFolderSelector && pendingArchiveItem}
	<FolderSelector
		senderEmail={pendingArchiveItem.metadata.from_address}
		subject={pendingArchiveItem.metadata.subject}
		onSelect={handleFolderSelect}
		onCancel={closeFolderSelector}
	/>
{/if}
