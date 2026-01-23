<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import {
		Card,
		Button,
		Input,
		VirtualList,
		SwipeableCard,
		LongPressMenu,
		FolderSelector
	} from '$lib/components/ui';
	import type { MenuItem } from '$lib/components/ui/LongPressMenu.svelte';
	import { formatRelativeTime } from '$lib/utils/formatters';
	// v2.3: Analysis Transparency components
	import PassTimeline from '$lib/components/peripeties/PassTimeline.svelte';
	import ConfidenceSparkline from '$lib/components/peripeties/ConfidenceSparkline.svelte';
	// v2.4: Skeleton loader for improved UX
	import QueueItemSkeleton from '$lib/components/peripeties/QueueItemSkeleton.svelte';
	// v2.5: FileAttachment component for attachments display
	import { FileAttachment } from '$lib/components/files';
	import { queueStore } from '$lib/stores';
	import { queueWsStore } from '$lib/stores/queueWebsocket.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import {
		approveQueueItem,
		undoQueueItem,
		canUndoQueueItem,
		snoozeQueueItem,
		processInbox,
		reanalyzeQueueItem,
		reanalyzeAllPending,
		recordArchive,
		getFolderSuggestions
	} from '$lib/api';
	import type {
		QueueItem,
		ActionOption,
		SnoozeOption,
		FolderSuggestion,
		ProposedNote,
		ProposedTask
	} from '$lib/api';
	import {
		registerShortcuts,
		registerShortcut,
		createNavigationShortcuts,
		createQueueActionShortcuts
	} from '$lib/utils/keyboard-shortcuts.svelte';

	// Constants for filtering - synchronized with backend auto-apply thresholds
	// See src/core/entities.py: AUTO_APPLY_THRESHOLD and AUTO_APPLY_THRESHOLD_REQUIRED
	// Adjusted for geometric mean confidence (4 dimensions)
	const AUTO_APPLY_THRESHOLD_REQUIRED = 0.8; // Required enrichments
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
		return notes.filter((note) => {
			const hasValidTitle =
				note.title && note.title.toLowerCase() !== 'general' && note.title.trim() !== '';
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
		return tasks.filter((task) => {
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
	 * Filter proposed notes to show only ones that will NOT be applied (skipped/rejected).
	 */
	function filterSkippedNotes(notes: ProposedNote[] | undefined): ProposedNote[] {
		if (!notes) return [];
		return notes.filter((note) => {
			const hasValidTitle =
				note.title && note.title.toLowerCase() !== 'general' && note.title.trim() !== '';
			return hasValidTitle && !willNoteBeAutoApplied(note);
		});
	}

	/**
	 * Filter proposed tasks to show only ones that will NOT be applied (skipped/rejected).
	 */
	function filterSkippedTasks(tasks: ProposedTask[] | undefined): ProposedTask[] {
		if (!tasks) return [];
		return tasks.filter((task) => !willTaskBeAutoApplied(task));
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
	const isTouchDevice = $derived(
		browser && ('ontouchstart' in window || navigator.maxTouchPoints > 0)
	);

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
		goto('/peripeties/focus');
	}

	// Cleanup function for keyboard shortcuts
	let unregisterShortcuts: (() => void) | null = null;

	// v2.4: WebSocket event handlers
	function handleQueueItemAdded(event: CustomEvent) {
		// A new item was added - refresh stats and optionally show notification
		queueStore.fetchStats();
		console.log('[Peripeties] New item added:', event.detail?.id);
	}

	function handleQueueItemUpdated(event: CustomEvent) {
		// An item was updated - refresh stats
		queueStore.fetchStats();
		console.log('[Peripeties] Item updated:', event.detail?.item?.id);
	}

	function handleQueueItemRemoved(event: CustomEvent) {
		// Item already removed from store by queueWsStore
		console.log('[Peripeties] Item removed:', event.detail?.itemId);
	}

	function handleQueueStatsUpdated(event: CustomEvent) {
		// Stats were updated - could update UI directly
		console.log('[Peripeties] Stats updated:', event.detail?.total);
	}

	// Load queue on mount
	onMount(async () => {
		await queueStore.fetchQueueByTab('to_process');
		await queueStore.fetchStats();
		document.addEventListener('keydown', handleKeyboard);

		// v2.4: Connect to queue WebSocket for real-time updates
		queueWsStore.connect();

		// v2.4: Listen for queue events
		if (browser) {
			window.addEventListener('scapin:queue:item_added', handleQueueItemAdded as EventListener);
			window.addEventListener('scapin:queue:item_updated', handleQueueItemUpdated as EventListener);
			window.addEventListener('scapin:queue:item_removed', handleQueueItemRemoved as EventListener);
			window.addEventListener('scapin:queue:stats_updated', handleQueueStatsUpdated as EventListener);
		}

		// Bug #49: Check if we need to auto-fetch after initial load
		checkAutoFetch();

		// Register context-specific keyboard shortcuts
		const navigationShortcuts = createNavigationShortcuts(
			() => navigatePrevious(),
			() => navigateNext(),
			'/peripeties'
		);

		const actionShortcuts = createQueueActionShortcuts(
			() => handleApproveRecommended(),
			() => toggleOpusPanel(), // R = Toggle Opus panel
			() => toggleSnoozeMenu(),
			() => {
				showLevel3 = !showLevel3;
			},
			'/peripeties'
		);

		// v2.4: Add Focus Mode shortcut
		const focusModeShortcut = {
			id: 'focus-mode',
			key: 'f',
			description: 'Mode Focus',
			handler: () => {
				if (activeTab === 'to_process' && queueStore.items.length > 0) {
					enterFocusMode();
				}
			},
			context: '/peripeties'
		};

		unregisterShortcuts = registerShortcuts([...navigationShortcuts, ...actionShortcuts, focusModeShortcut]);
	});

	onDestroy(() => {
		document.removeEventListener('keydown', handleKeyboard);
		unregisterShortcuts?.();

		// v2.4: Disconnect from queue WebSocket
		queueWsStore.disconnect();

		// v2.4: Remove queue event listeners
		if (browser) {
			window.removeEventListener('scapin:queue:item_added', handleQueueItemAdded as EventListener);
			window.removeEventListener('scapin:queue:item_updated', handleQueueItemUpdated as EventListener);
			window.removeEventListener('scapin:queue:item_removed', handleQueueItemRemoved as EventListener);
			window.removeEventListener('scapin:queue:stats_updated', handleQueueStatsUpdated as EventListener);
		}

		// Clear all pending timeouts
		if (undoErrorTimeout) clearTimeout(undoErrorTimeout);
		if (snoozeSuccessTimeout) clearTimeout(snoozeSuccessTimeout);
		if (snoozeErrorTimeout) clearTimeout(snoozeErrorTimeout);
	});

	// v2.4: Tab-based filtering (replaces status-based)
	type TabFilter = 'to_process' | 'in_progress' | 'snoozed' | 'history' | 'errors';
	let activeTab: TabFilter = $state('to_process');
	let currentIndex: number = $state(0);
	let customInstruction: string = $state('');
	let isProcessing: boolean = $state(false);
	let showLevel3: boolean = $state(false);
	let showHtmlContent: boolean = $state(true);

	// Current item in single-item view
	const currentItem = $derived(
		activeTab === 'to_process' && queueStore.items.length > 0
			? queueStore.items[currentIndex] || null
			: null
	);

	// v2.4: Tab-based navigation
	async function changeTab(tab: TabFilter) {
		activeTab = tab;
		currentIndex = 0;
		customInstruction = '';
		// Map tabs to API parameters
		await queueStore.fetchQueueByTab(tab);

		// Check which items can be undone in history tab
		if (tab === 'history') {
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
			'Récupération des emails en cours...',
			{ title: 'Traitement', duration: 120000 } // 2 minutes max
		);

		let pollInterval: ReturnType<typeof setInterval> | null = null;

		try {
			// Note: unreadOnly=false to process all emails, not just unread ones
			const result = await processInbox(20, false, undefined, false);

			// Dismiss the processing toast
			toastStore.dismiss(processingToastId);

			// Bug #50 fix: Refresh queue FIRST before showing success toast
			await queueStore.fetchQueueByTab('to_process');
			await queueStore.fetchStats();

			// v2.5: Handle new async analysis flow
			const inProgressCount = result.in_progress || 0;

			if (result.total_processed > 0) {
				if (inProgressCount > 0) {
					// Items are being analyzed in background - start polling
					const analyzeToastId = toastStore.info(
						`Analyse de ${inProgressCount} email${inProgressCount > 1 ? 's' : ''} en cours...`,
						{ title: 'Analyse', duration: 300000 }
					);

					pollInterval = setInterval(async () => {
						await queueStore.fetchStats();

						const currentInProgress = queueStore.stats?.by_tab?.in_progress ?? 0;
						if (currentInProgress === 0 && pollInterval) {
							clearInterval(pollInterval);
							pollInterval = null;
							isFetchingEmails = false;
							toastStore.dismiss(analyzeToastId);

							// Refresh to show completed items
							await queueStore.fetchQueueByTab('to_process');
							const toProcessCount = queueStore.stats?.by_tab?.to_process ?? 0;
							toastStore.success(
								`Analyse terminée. ${toProcessCount} élément${toProcessCount > 1 ? 's' : ''} à traiter.`,
								{ title: 'Analyse terminée' }
							);
						}
					}, 2000);

					// Don't set isFetchingEmails = false yet, wait for analysis to complete
					return;
				} else {
					// Immediate completion (backwards compatibility)
					const queuedCount = result.queued || 0;
					toastStore.success(
						`${result.total_processed} email${result.total_processed > 1 ? 's' : ''} analysé${result.total_processed > 1 ? 's' : ''} et ${queuedCount} ajouté${queuedCount > 1 ? 's' : ''} à la file`,
						{ title: 'Péripéties récupérées' }
					);
				}
			} else {
				toastStore.info('Aucun nouvel email à traiter', { title: 'Boîte de réception à jour' });
			}
		} catch (err) {
			// Dismiss the processing toast
			toastStore.dismiss(processingToastId);
			if (pollInterval) clearInterval(pollInterval);

			fetchError = err instanceof Error ? err.message : 'Erreur de connexion';
			toastStore.error('Impossible de récupérer les péripéties. Vérifiez la connexion au serveur.', {
				title: 'Erreur'
			});
		} finally {
			// Only reset if not waiting for analysis
			if (!pollInterval) {
				isFetchingEmails = false;
			}
		}
	}

	// Re-analyze all pending items
	async function handleReanalyzeAll() {
		if (isReanalyzing) return;

		const pendingCount = queueStore.stats?.by_tab?.to_process ?? queueStore.items.length;
		if (pendingCount === 0) {
			toastStore.info('Aucun élément à réanalyser', { title: 'File vide' });
			return;
		}

		isReanalyzing = true;

		const processingToastId = toastStore.info(
			`Réanalyse de ${pendingCount} élément${pendingCount > 1 ? 's' : ''} en cours...`,
			{ title: 'Réanalyse', duration: 300000 } // 5 minutes max
		);

		let pollInterval: ReturnType<typeof setInterval> | null = null;

		try {
			// Call API - returns immediately after marking all items as in_progress
			await reanalyzeAllPending();

			// Refresh to show items in "En cours"
			await queueStore.fetchStats();
			await queueStore.fetchQueueByTab('to_process');

			// Start polling every 3 seconds to track progress
			pollInterval = setInterval(async () => {
				await queueStore.fetchStats();
				await queueStore.fetchQueueByTab('to_process');

				const inProgressCount = queueStore.stats?.by_tab?.in_progress ?? 0;
				if (inProgressCount === 0 && pollInterval) {
					clearInterval(pollInterval);
					pollInterval = null;
					isReanalyzing = false;
					toastStore.dismiss(processingToastId);
					toastStore.success('Réanalyse terminée', { title: 'Terminé' });
				}
			}, 3000);

		} catch (err) {
			if (pollInterval) clearInterval(pollInterval);
			toastStore.dismiss(processingToastId);
			toastStore.error('Impossible de réanalyser les éléments. Vérifiez la connexion au serveur.', {
				title: 'Erreur'
			});
			isReanalyzing = false;
		}
	}

	// Bug #49: Auto-fetch when queue is low
	async function checkAutoFetch() {
		// Only auto-fetch in to_process view when enabled and not already fetching
		if (!autoFetchEnabled || isFetchingEmails || activeTab !== 'to_process') return;

		// Check cooldown to prevent spamming
		const now = Date.now();
		if (now - lastAutoFetchTime < AUTO_FETCH_COOLDOWN_MS) {
			return; // Still in cooldown period
		}

		// Check if queue is below threshold (to_process + in_progress)
		const toProcessCount = queueStore.stats?.by_tab?.to_process ?? 0;
		const inProgressCount = queueStore.stats?.by_tab?.in_progress ?? 0;
		const totalActiveCount = toProcessCount + inProgressCount;

		if (totalActiveCount < AUTO_FETCH_THRESHOLD) {
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
			await queueStore.fetchQueueByTab('history');
			await queueStore.fetchStats();
		} catch (e) {
			console.error('Undo failed:', e);
			undoError = e instanceof Error ? e.message : "Erreur lors de l'annulation";
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
		// Only handle in to_process single-item view
		if (activeTab !== 'to_process' || !currentItem || isProcessing) return;

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
				await queueStore.fetchQueueByTab('to_process');
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
				toastStore.error(`Échec de l'action "${actionLabel}". L'email a été restauré.`, {
					title: 'Erreur IMAP'
				});
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
				toastStore.error(`La ré-analyse a échoué. Veuillez réessayer.`, { title: 'Erreur' });
			}
		} catch (e) {
			console.error('Reanalysis failed:', e);
			customInstruction = savedInstruction; // Restore instruction on error
			toastStore.error(`Échec de la ré-analyse. Veuillez réessayer.`, { title: 'Erreur' });
		} finally {
			isReanalyzing = false;
		}
	}

	// Reanalyze panel state (v2.5: full panel with model selection)
	// v3.2: Track which specific item is being reanalyzed (null = none)
	let reanalyzingItemId = $state<string | null>(null);
	let isReanalyzingItem = $derived(reanalyzingItemId !== null);
	let showReanalyzePanel = $state(false);
	let reanalyzeInstruction = $state('');
	let reanalyzeModel = $state<'standard' | 'haiku' | 'sonnet' | 'opus'>('standard');
	let reanalyzeProgress = $state(0); // 0-100 for progress bar

	function toggleReanalyzePanel() {
		showReanalyzePanel = !showReanalyzePanel;
		if (!showReanalyzePanel) {
			reanalyzeInstruction = '';
			reanalyzeModel = 'standard';
		}
	}

	// Check if a specific item is being reanalyzed
	function isItemReanalyzing(itemId: string): boolean {
		return reanalyzingItemId === itemId;
	}

	// Legacy aliases for backwards compatibility
	let isReanalyzingOpus = $derived(isReanalyzingItem);
	let showOpusPanel = $derived(showReanalyzePanel);
	let opusInstruction = $derived(reanalyzeInstruction);
	function toggleOpusPanel() { toggleReanalyzePanel(); }

	async function handleReanalyzeItem(
		item: QueueItem,
		mode: 'immediate' | 'background' = 'immediate'
	) {
		// v3.2: Only block if THIS item is already being reanalyzed
		if (reanalyzingItemId === item.id || isProcessing) return;

		reanalyzingItemId = item.id;
		reanalyzeProgress = 0;
		showReanalyzePanel = false;

		const instruction = reanalyzeInstruction.trim();
		const selectedModel = reanalyzeModel;
		reanalyzeInstruction = '';
		reanalyzeModel = 'standard';

		// Map 'standard' to null (let multi-pass decide)
		const forceModel = selectedModel === 'standard' ? null : selectedModel;
		const modelLabel = selectedModel === 'standard' ? 'Multi-pass' : selectedModel.charAt(0).toUpperCase() + selectedModel.slice(1);

		const processingToastId =
			mode === 'immediate'
				? toastStore.info(
						instruction
							? `Réanalyse avec instruction: "${instruction.slice(0, 50)}..."`
							: `Réanalyse en cours (${modelLabel})...`,
						{ title: 'Réanalyse', duration: 120000 }
					)
				: toastStore.info("Réanalyse en file d'attente", { title: 'Réanalyse', duration: 3000 });

		// Optimistic update: remove item from current view (it's now in_progress)
		const savedItem = { ...item };
		queueStore.removeFromList(item.id);
		if (currentIndex >= queueStore.items.length) {
			currentIndex = Math.max(0, queueStore.items.length - 1);
		}

		// v3.2: Refresh stats immediately to show item in "En cours" tab
		await queueStore.fetchStats();

		// v3.2: Simulate progress for immediate mode (actual progress would need SSE/WebSocket)
		let progressInterval: ReturnType<typeof setInterval> | null = null;
		if (mode === 'immediate') {
			progressInterval = setInterval(() => {
				// Slow down as we approach 90% (never reach 100 until complete)
				if (reanalyzeProgress < 90) {
					reanalyzeProgress += Math.random() * 5;
					if (reanalyzeProgress > 90) reanalyzeProgress = 90;
				}
			}, 500);
		}

		try {
			const result = await reanalyzeQueueItem(item.id, instruction, mode, forceModel);

			if (progressInterval) clearInterval(progressInterval);
			reanalyzeProgress = 100;
			toastStore.dismiss(processingToastId);

			if (mode === 'background') {
				toastStore.success("L'analyse sera effectuée en arrière-plan.", {
					title: 'Analyse programmée'
				});
			} else if (result.status === 'complete' && result.new_analysis) {
				// Refresh queue to get updated item
				await queueStore.fetchQueueByTab('to_process');
				await queueStore.fetchStats();

				toastStore.success(
					`Nouvelle analyse terminée. Action: ${result.new_analysis.action} (${result.new_analysis.confidence}%)`,
					{ title: `Analyse ${modelLabel}` }
				);
			} else {
				// Reanalysis didn't produce a result - restore item to list
				queueStore.restoreItem(savedItem);
				toastStore.warning("La réanalyse n'a pas produit de nouveau résultat.", {
					title: 'Réanalyse'
				});
			}
		} catch (e) {
			if (progressInterval) clearInterval(progressInterval);
			toastStore.dismiss(processingToastId);
			console.error('Reanalysis failed:', e);
			// Restore item to list on error
			queueStore.restoreItem(savedItem);
			toastStore.error('Échec de la réanalyse. Veuillez réessayer.', { title: 'Erreur' });
		} finally {
			reanalyzingItemId = null;
			reanalyzeProgress = 0;
		}
	}

	// Legacy alias
	async function handleReanalyzeOpus(item: QueueItem, mode: 'immediate' | 'background' = 'immediate') {
		reanalyzeModel = 'opus';
		await handleReanalyzeItem(item, mode);
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
				await queueStore.fetchQueueByTab('to_process');
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
				toastStore.error(`Échec de la suppression. L'email a été restauré.`, {
					title: 'Erreur IMAP'
				});
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
		if (activeTab === 'to_process' && queueStore.items.length > 0) {
			if (currentIndex > 0) {
				currentIndex--;
			} else {
				currentIndex = queueStore.items.length - 1; // Loop to end
			}
		}
	}

	function navigateNext() {
		if (activeTab === 'to_process' && queueStore.items.length > 0) {
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
			await queueStore.fetchQueueByTab('to_process');
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
			await queueStore.fetchQueueByTab('to_process');
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
		return "Scapin manque d'éléments pour décider seul";
	}

	// v2.4: Analysis progress helpers for "En cours" tab
	interface AnalysisProgress {
		stage: 'grimaud' | 'bazin' | 'planchet' | 'mousqueton' | 'finalizing';
		stageLabel: string;
		stageDescription: string;
		progress: number; // 0-100
		elapsedSeconds: number;
	}

	function getAnalysisProgress(analysisStartedAt: string | null | undefined): AnalysisProgress {
		if (!analysisStartedAt) {
			return {
				stage: 'grimaud',
				stageLabel: 'Démarrage...',
				stageDescription: 'Préparation de l\'analyse',
				progress: 0,
				elapsedSeconds: 0
			};
		}

		const started = new Date(analysisStartedAt);
		const now = new Date();
		const elapsedMs = now.getTime() - started.getTime();
		const elapsedSeconds = Math.floor(elapsedMs / 1000);

		// Estimated timing for each valet (based on typical analysis times)
		// grimaud: 0-8s, bazin: 8-25s, planchet: 25-40s, mousqueton: 40-60s
		if (elapsedSeconds < 8) {
			return {
				stage: 'grimaud',
				stageLabel: 'grimaud',
				stageDescription: 'Extraction silencieuse des faits',
				progress: Math.min(25, (elapsedSeconds / 8) * 25),
				elapsedSeconds
			};
		} else if (elapsedSeconds < 25) {
			return {
				stage: 'bazin',
				stageLabel: 'bazin',
				stageDescription: 'Critique et enrichissement contextuel',
				progress: 25 + ((elapsedSeconds - 8) / 17) * 25,
				elapsedSeconds
			};
		} else if (elapsedSeconds < 40) {
			return {
				stage: 'planchet',
				stageLabel: 'planchet',
				stageDescription: 'Décision et action résolue',
				progress: 50 + ((elapsedSeconds - 25) / 15) * 25,
				elapsedSeconds
			};
		} else if (elapsedSeconds < 60) {
			return {
				stage: 'mousqueton',
				stageLabel: 'mousqueton',
				stageDescription: 'Arbitrage des cas complexes',
				progress: 75 + ((elapsedSeconds - 40) / 20) * 20,
				elapsedSeconds
			};
		} else {
			return {
				stage: 'finalizing',
				stageLabel: 'Finalisation',
				stageDescription: 'Consolidation de l\'analyse',
				progress: 95,
				elapsedSeconds
			};
		}
	}

	function formatElapsedTime(seconds: number): string {
		if (seconds < 60) return `${seconds}s`;
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins}m${secs}s`;
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
			handler: () => {
				showSnoozeMenu = true;
			}
		});

		// Reanalyze panel
		menuItems.push({
			id: 'reanalyze',
			label: 'Réanalyser',
			icon: '🔄',
			handler: () => toggleReanalyzePanel()
		});

		// View details
		menuItems.push({
			id: 'details',
			label: "Voir l'email complet",
			icon: '📧',
			handler: () => goto(`/peripeties/${item.id}`)
		});

		return menuItems;
	});

	// Swipe actions for mobile
	const swipeRightAction = $derived(
		currentItem
			? {
					icon: '✓',
					label: 'Approuver',
					color: 'var(--color-success)',
					action: () => handleApproveRecommended()
				}
			: undefined
	);

	const swipeLeftAction = $derived(
		currentItem
			? {
					icon: '🧠',
					label: 'Opus',
					color: 'var(--color-accent)',
					action: () => toggleOpusPanel()
				}
			: undefined
	);

	const stats = $derived(queueStore.stats);
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<!-- Header with Scapin tone -->
	<header class="mb-6">
		<div class="flex items-start justify-between gap-4">
			<div>
				<div class="flex items-center gap-2">
					<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
						Péripéties
					</h1>
					<!-- v2.4: Real-time connection indicator -->
					<span
						class="inline-flex items-center px-1.5 py-0.5 text-xs rounded-full {queueWsStore.isConnected
							? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
							: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}"
						title={queueWsStore.isConnected ? 'Temps réel actif' : 'Connexion temps réel...'}
					>
						<span
							class="w-1.5 h-1.5 rounded-full mr-1 {queueWsStore.isConnected
								? 'bg-green-500 animate-pulse'
								: 'bg-gray-400'}"
						></span>
						{queueWsStore.isConnected ? 'Live' : '...'}
					</span>
				</div>
				<p class="text-[var(--color-text-secondary)] mt-1" aria-live="polite" aria-atomic="true">
					{#if queueStore.loading}
						Chargement...
					{:else if activeTab === 'to_process' && queueStore.total > 0}
						{queueStore.total} péripétie{queueStore.total > 1 ? 's' : ''} à traiter
					{:else if activeTab === 'to_process'}
						Aucune péripétie en attente
					{:else if activeTab === 'in_progress'}
						Péripéties en cours d'analyse
					{:else if activeTab === 'snoozed'}
						Péripéties reportées
					{:else if activeTab === 'history'}
						Historique des péripéties
					{:else if activeTab === 'errors'}
						Péripéties en erreur
					{:else}
						Péripéties
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
				{#if activeTab === 'to_process' && queueStore.items.length > 0}
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

				<!-- Focus mode button (F shortcut) -->
				{#if activeTab === 'to_process' && queueStore.items.length > 0}
					<Button variant="primary" size="sm" onclick={enterFocusMode} title="Activer le mode focus (F)">
						<span class="mr-1.5">🎯</span>
						Mode Focus
						<kbd class="ml-1.5 px-1 py-0.5 text-xs bg-white/20 rounded">F</kbd>
					</Button>
				{/if}
			</div>
		</div>
	</header>

	<!-- Analysis in progress indicator -->
	{#if (stats?.by_tab?.in_progress ?? 0) > 0}
		<div class="mb-4 px-4 py-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 flex items-center gap-3">
			<div class="flex items-center gap-2">
				<span class="animate-spin text-blue-600 dark:text-blue-400">⏳</span>
				<span class="text-blue-800 dark:text-blue-200 font-medium">
					{stats?.by_tab?.in_progress} analyse{(stats?.by_tab?.in_progress ?? 0) > 1 ? 's' : ''} en cours
				</span>
			</div>
			<div class="flex-1 h-1.5 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden">
				<div class="h-full bg-blue-500 dark:bg-blue-400 rounded-full animate-pulse" style="width: 60%"></div>
			</div>
		</div>
	{/if}

	<!-- v2.4: Tab-based navigation with 5 tabs (scrollable on mobile) -->
	<div class="flex gap-2 mb-4 text-sm overflow-x-auto pb-1 -mx-4 px-4 md:mx-0 md:px-0 md:overflow-visible md:flex-wrap" role="tablist" aria-label="Navigation péripéties">
		<!-- À traiter -->
		<button
			role="tab"
			aria-selected={activeTab === 'to_process'}
			data-testid="peripeties-tab-to-process"
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5 shrink-0"
			class:bg-[var(--color-accent)]={activeTab === 'to_process'}
			class:text-white={activeTab === 'to_process'}
			class:bg-[var(--color-bg-secondary)]={activeTab !== 'to_process'}
			class:text-[var(--color-text-secondary)]={activeTab !== 'to_process'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeTab !== 'to_process'}
			onclick={() => changeTab('to_process')}
		>
			<span
				class="font-bold text-[var(--color-warning)]"
				class:text-white={activeTab === 'to_process'}
				data-testid="to-process-count"
			>
				{stats?.by_tab?.to_process ?? 0}
			</span>
			<span>À traiter</span>
		</button>

		<!-- En cours -->
		<button
			role="tab"
			aria-selected={activeTab === 'in_progress'}
			data-testid="peripeties-tab-in-progress"
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5 shrink-0"
			class:bg-[var(--color-accent)]={activeTab === 'in_progress'}
			class:text-white={activeTab === 'in_progress'}
			class:bg-[var(--color-bg-secondary)]={activeTab !== 'in_progress'}
			class:text-[var(--color-text-secondary)]={activeTab !== 'in_progress'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeTab !== 'in_progress'}
			onclick={() => changeTab('in_progress')}
		>
			<span
				class="font-bold text-[var(--color-accent)]"
				class:text-white={activeTab === 'in_progress'}
				data-testid="in-progress-count"
			>
				{stats?.by_tab?.in_progress ?? 0}
			</span>
			<span>En cours</span>
		</button>

		<!-- Reportées -->
		<button
			role="tab"
			aria-selected={activeTab === 'snoozed'}
			data-testid="peripeties-tab-snoozed"
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5 shrink-0"
			class:bg-[var(--color-accent)]={activeTab === 'snoozed'}
			class:text-white={activeTab === 'snoozed'}
			class:bg-[var(--color-bg-secondary)]={activeTab !== 'snoozed'}
			class:text-[var(--color-text-secondary)]={activeTab !== 'snoozed'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeTab !== 'snoozed'}
			onclick={() => changeTab('snoozed')}
		>
			<span
				class="font-bold text-[var(--color-text-tertiary)]"
				class:text-white={activeTab === 'snoozed'}
				data-testid="snoozed-count"
			>
				{stats?.by_tab?.snoozed ?? 0}
			</span>
			<span>💤 Reportées</span>
		</button>

		<!-- Historique -->
		<button
			role="tab"
			aria-selected={activeTab === 'history'}
			data-testid="peripeties-tab-history"
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5 shrink-0"
			class:bg-[var(--color-accent)]={activeTab === 'history'}
			class:text-white={activeTab === 'history'}
			class:bg-[var(--color-bg-secondary)]={activeTab !== 'history'}
			class:text-[var(--color-text-secondary)]={activeTab !== 'history'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeTab !== 'history'}
			onclick={() => changeTab('history')}
		>
			<span
				class="font-bold text-[var(--color-success)]"
				class:text-white={activeTab === 'history'}
				data-testid="history-count"
			>
				{stats?.by_tab?.history ?? 0}
			</span>
			<span>Historique</span>
		</button>

		<!-- Erreurs -->
		<button
			role="tab"
			aria-selected={activeTab === 'errors'}
			data-testid="peripeties-tab-errors"
			class="px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5 shrink-0"
			class:bg-[var(--color-accent)]={activeTab === 'errors'}
			class:text-white={activeTab === 'errors'}
			class:bg-[var(--color-bg-secondary)]={activeTab !== 'errors'}
			class:text-[var(--color-text-secondary)]={activeTab !== 'errors'}
			class:hover:bg-[var(--color-bg-tertiary)]={activeTab !== 'errors'}
			onclick={() => changeTab('errors')}
		>
			<span
				class="font-bold text-[var(--color-urgency-urgent)]"
				class:text-white={activeTab === 'errors'}
				data-testid="errors-count"
			>
				{stats?.by_tab?.errors ?? 0}
			</span>
			<span>⚠️ Erreurs</span>
		</button>

		<!-- Badges legend (v2.3) -->
		<div class="ml-auto flex items-center gap-1 text-xs text-[var(--color-text-tertiary)]" data-testid="badges-legend">
			<span class="hidden sm:inline" title="Légende des badges de complexité d'analyse">Badges:</span>
			<span title="Analyse rapide : 1 pass avec Haiku">⚡</span>
			<span title="Contexte personnel utilisé">🔍</span>
			<span title="Analyse complexe : 3+ passes">🧠</span>
			<span title="Opus utilisé">🏆</span>
		</div>
	</div>

	<!-- Loading state with skeleton cards (v2.4) -->
	{#if queueStore.loading && queueStore.items.length === 0}
		<div role="status" aria-busy="true" aria-label="Chargement en cours" data-testid="peripeties-loading-state">
			<span class="sr-only">Chargement de la file d'attente...</span>
			{#each { length: 5 } as _}
				<QueueItemSkeleton />
			{/each}
		</div>

		<!-- Error state with retry (v2.4) -->
	{:else if queueStore.error && queueStore.items.length === 0}
		<Card padding="lg" data-testid="peripeties-error-state">
			<div class="text-center py-8">
				<p class="text-4xl mb-3">⚠️</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-2" data-testid="peripeties-error-title">
					Erreur de chargement
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)] mb-4" data-testid="peripeties-error-message">
					{queueStore.error}
				</p>
				<Button
					variant="primary"
					onclick={() => {
						queueStore.clearError();
						queueStore.fetchQueueByTab(activeTab);
					}}
					data-testid="peripeties-error-retry"
				>
					Réessayer
				</Button>
			</div>
		</Card>

		<!-- Empty state -->
	{:else if queueStore.items.length === 0}
		<Card padding="lg" data-testid="peripeties-empty-state">
			<div class="text-center py-8">
				<p class="text-4xl mb-3" data-testid="peripeties-empty-icon">
					{#if activeTab === 'to_process'}🎉
					{:else if activeTab === 'in_progress'}⏳
					{:else if activeTab === 'snoozed'}💤
					{:else if activeTab === 'history'}✅
					{:else if activeTab === 'errors'}⚠️
					{:else}📭
					{/if}
				</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1" data-testid="peripeties-empty-title">
					{#if activeTab === 'to_process'}
						Boîte de réception vide
					{:else if activeTab === 'in_progress'}
						Aucune analyse en cours
					{:else if activeTab === 'snoozed'}
						Aucune péripétie reportée
					{:else if activeTab === 'history'}
						Historique vide
					{:else if activeTab === 'errors'}
						Tout fonctionne !
					{:else}
						Aucune péripétie
					{/if}
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)] max-w-md mx-auto" data-testid="peripeties-empty-description">
					{#if activeTab === 'to_process'}
						Scapin n'a détecté aucun email nécessitant votre attention. Cliquez sur "Récupérer" pour vérifier les nouveaux messages.
					{:else if activeTab === 'in_progress'}
						Sancho n'analyse aucun élément actuellement. Les analyses démarrent automatiquement lors de la récupération des emails.
					{:else if activeTab === 'snoozed'}
						Vous n'avez reporté aucune péripétie. Utilisez le bouton "Snooze" pour reporter le traitement d'un email.
					{:else if activeTab === 'history'}
						Aucune péripétie traitée pour le moment. L'historique apparaîtra ici après vos premières décisions.
					{:else if activeTab === 'errors'}
						Aucune erreur enregistrée. Scapin fonctionne correctement !
					{:else}
						Lancez la récupération pour alimenter la file
					{/if}
				</p>
				<!-- v2.4: Action button for empty to_process state -->
				{#if activeTab === 'to_process'}
					<div class="mt-4">
						<Button
							variant="primary"
							size="sm"
							onclick={handleFetchEmails}
							disabled={isFetchingEmails}
							data-testid="peripeties-fetch-button"
						>
							{#if isFetchingEmails}
								<span class="mr-1.5 animate-spin">⏳</span>
								Récupération...
							{:else}
								<span class="mr-1.5">📥</span>
								Récupérer les emails
							{/if}
						</Button>
					</div>
				{/if}
			</div>
		</Card>

		<!-- SINGLE ITEM VIEW for to_process items - REDESIGNED UI -->
	{:else if activeTab === 'to_process' && currentItem}
		{@const options = currentItem.analysis.options || []}
		{@const hasOptions = options.length > 0}
		{@const recommendedOption = options.find((o) => o.is_recommended) || options[0]}
		{@const otherOptions = options.filter((o) => o !== recommendedOption)}
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
						{@const noteActionClass =
							note.action === 'create'
								? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300'
								: 'bg-amber-100 text-amber-700 dark:bg-yellow-500/20 dark:text-yellow-300'}
						{@const willApply = willNoteBeAutoApplied(note)}
						{@const threshold = note.required
							? AUTO_APPLY_THRESHOLD_REQUIRED
							: AUTO_APPLY_THRESHOLD_OPTIONAL}
						{@const isManuallySet =
							note.manually_approved !== null && note.manually_approved !== undefined}
						{@const isChecked =
							note.manually_approved === true || (note.manually_approved !== false && willApply)}
						<div
							class="rounded-lg border border-[var(--color-border)] p-2 {!isChecked
								? 'opacity-60'
								: ''}"
						>
							<div class="flex items-center justify-between text-sm">
								<span class="flex items-center gap-2">
									<input
										type="checkbox"
										checked={isChecked}
										class="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500 cursor-pointer"
										title={isManuallySet
											? note.manually_approved
												? 'Forcé'
												: 'Rejeté'
											: willApply
												? 'Auto'
												: 'Manuel'}
										onchange={() => queueStore.toggleNoteApproval(currentItem.id, noteIndex)}
									/>
									<span class="text-xs px-1.5 py-0.5 rounded {noteActionClass}">
										{#if note.action === 'create'}
											✨ {note.note_type}
										{:else}
											~ {note.note_type}
										{/if}
									</span>
									{#if note.action === 'create'}
										<span class="text-[10px] px-1 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300 font-medium">
											NOUVELLE
										</span>
									{/if}
									{#if note.required}
										<span
											class="text-xs px-1 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300"
											>!</span
										>
									{/if}
									<span class="text-[var(--color-text-primary)] font-medium"
										>{note.title || 'Sans titre'}</span
									>
								</span>
								<span
									class="text-xs font-medium px-1.5 py-0.5 rounded {isChecked
										? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300'
										: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300'}"
								>
									{Math.round(note.confidence * 100)}%
								</span>
							</div>
							{#if note.content_summary}
								<p
									class="mt-1.5 text-xs text-[var(--color-text-secondary)] pl-6 border-l-2 border-[var(--color-border)] ml-2"
								>
									{note.content_summary}
								</p>
							{/if}
						</div>
					{/each}
					{#each tasks as task, taskIndex}
						{@const willApply = willTaskBeAutoApplied(task)}
						{@const isPastDue = isDateObsolete(task.due_date)}
						{@const isManuallySet =
							task.manually_approved !== null && task.manually_approved !== undefined}
						{@const isChecked =
							task.manually_approved === true ||
							(task.manually_approved !== false && willApply && !isPastDue)}
						<div
							class="rounded-lg border border-[var(--color-border)] p-2 {!isChecked
								? 'opacity-60'
								: ''}"
						>
							<div class="flex items-center justify-between text-sm">
								<span class="flex items-center gap-2">
									<input
										type="checkbox"
										checked={isChecked}
										class="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500 cursor-pointer"
										title={task.manually_approved !== null
											? task.manually_approved
												? 'Forcé'
												: 'Rejeté'
											: willApply
												? 'Auto'
												: 'Manuel'}
										onchange={() => queueStore.toggleTaskApproval(currentItem.id, taskIndex)}
									/>
									<span
										class="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300"
										>📋 OmniFocus</span
									>
									<span class="text-[var(--color-text-primary)] font-medium">{task.title}</span>
								</span>
								<span
									class="text-xs font-medium px-1.5 py-0.5 rounded {isChecked
										? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300'
										: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300'}"
								>
									{Math.round(task.confidence * 100)}%
								</span>
							</div>
							<div
								class="mt-1.5 text-xs text-[var(--color-text-secondary)] pl-6 border-l-2 border-[var(--color-border)] ml-2 space-y-0.5"
							>
								{#if task.note}
									<p>{task.note}</p>
								{/if}
								<p class="flex items-center gap-2">
									{#if task.project}
										<span>📁 {task.project}</span>
									{/if}
									{#if task.due_date}
										<span
											class={isDatePast(task.due_date)
												? 'text-red-500 line-through'
												: 'text-orange-500'}
										>
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

		<!-- v3.1: Strategic questions section -->
		{#snippet strategicQuestionsSection()}
			{@const questions = currentItem.analysis.strategic_questions || []}
			{#if questions.length > 0}
				<div class="space-y-2">
					<div class="flex items-center gap-2 text-sm font-medium text-[var(--color-text-secondary)]">
						<span>❓</span>
						<span>Questions stratégiques ({questions.length})</span>
					</div>
					{#each questions as q}
						<div class="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-3">
							<p class="text-sm text-[var(--color-text-primary)] font-medium">{q.question}</p>
							{#if q.context}
								<p class="mt-1 text-xs text-[var(--color-text-secondary)]">{q.context}</p>
							{/if}
							<div class="mt-2 flex items-center gap-2 text-xs text-[var(--color-text-tertiary)]">
								<span class="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-800/40 text-amber-700 dark:text-amber-300">
									{q.category}
								</span>
								{#if q.target_note}
									<span>→ {q.target_note}</span>
								{/if}
								<span class="ml-auto opacity-60">via {q.source}</span>
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

		<SwipeableCard rightAction={swipeRightAction} leftAction={swipeLeftAction} threshold={100}>
			<LongPressMenu items={getMobileMenuItems(currentItem)}>
				<Card padding="md">
					<div class="space-y-3">
						<!-- SECTION 1: ACTION BAR (fixed at top) -->
						<div
							class="flex flex-wrap items-center gap-2 pb-3 border-b border-[var(--color-border)]"
						>
							<!-- Navigation -->
							<div class="flex items-center gap-1 text-sm text-[var(--color-text-tertiary)]">
								<button
									onclick={navigatePrevious}
									class="hover:text-[var(--color-accent)] p-1 -ml-1">←</button
								>
								<span class="font-medium">{currentIndex + 1}/{queueStore.items.length}</span>
								<button onclick={navigateNext} class="hover:text-[var(--color-accent)] p-1"
									>→</button
								>
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
								✓ <span class="hidden sm:inline">Approuver</span>
								<span class="opacity-60 font-mono text-xs">A</span>
							</Button>
							<Button
								variant={showReanalyzePanel ? 'primary' : 'secondary'}
								size="sm"
								onclick={toggleReanalyzePanel}
								disabled={isProcessing || isItemReanalyzing(currentItem.id)}
								data-testid="reanalyze-button"
							>
								{#if isItemReanalyzing(currentItem.id)}
									⏳
								{:else}
									🔄 <span class="opacity-60 font-mono text-xs">R</span>
								{/if}
							</Button>
							{#if otherOptions.length > 0}
								<Button variant="secondary" size="sm" onclick={() => (showLevel3 = !showLevel3)}>
									+{otherOptions.length}
								</Button>
							{/if}
							<div class="flex-1"></div>
							<!-- Secondary actions -->
							<Button
								variant="ghost"
								size="sm"
								onclick={() => handleArchiveElsewhere(currentItem)}
								disabled={isProcessing}
							>
								📁
							</Button>
							<Button
								variant="ghost"
								size="sm"
								onclick={() => handleDelete(currentItem)}
								disabled={isProcessing}
							>
								🗑️
							</Button>
							<div class="relative">
								<Button
									variant="ghost"
									size="sm"
									onclick={toggleSnoozeMenu}
									disabled={isProcessing}
									data-testid="snooze-button"
								>
									💤
								</Button>
								{#if showSnoozeMenu}
									<button
										type="button"
										class="fixed inset-0 z-40"
										onclick={() => (showSnoozeMenu = false)}
										aria-label="Fermer"
									></button>
									<div
										class="absolute top-full right-0 mt-1 z-50 min-w-[160px] py-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-primary)] shadow-lg"
									>
										{#each snoozeOptions as option}
											<button
												type="button"
												class="w-full text-left px-3 py-2 text-sm hover:bg-[var(--color-bg-secondary)]"
												onclick={() => handleSnoozeOption(option.value)}
												disabled={isSnoozing}>{option.label}</button
											>
										{/each}
									</div>
								{/if}
							</div>
							<Button
								variant={showLevel3 ? 'primary' : 'ghost'}
								size="sm"
								onclick={() => (showLevel3 = !showLevel3)}
							>
								{showLevel3 ? '📖' : '📋'}
							</Button>
						</div>

						<!-- v3.2: Reanalysis progress bar -->
						{#if isItemReanalyzing(currentItem.id)}
							<div class="py-2">
								<div class="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
									<span class="animate-spin">⏳</span>
									<span>Réanalyse en cours...</span>
									<span class="text-xs text-[var(--color-text-tertiary)]">{Math.round(reanalyzeProgress)}%</span>
								</div>
								<div class="mt-1 h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
									<div
										class="h-full bg-[var(--color-accent)] rounded-full transition-all duration-300"
										style="width: {reanalyzeProgress}%"
									></div>
								</div>
							</div>
						{/if}

						<!-- SECTION 2: EMAIL HEADER (modèle historique) -->
						<!-- v2.5: Enhanced dates section (like history page) -->
						<div class="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-[var(--color-text-tertiary)]">
							{#if currentItem.metadata.date}
								<span class="flex items-center gap-1.5" title="Date de réception de l'email">
									<span class="text-base">📨</span>
									<span class="font-medium text-[var(--color-text-secondary)]">Reçu</span>
									{formatRelativeTime(currentItem.metadata.date)}
								</span>
							{/if}
							{#if currentItem.timestamps?.analysis_completed_at || currentItem.queued_at}
								<span class="flex items-center gap-1.5" title="Date d'analyse par Scapin">
									<span class="text-base">🧠</span>
									<span class="font-medium text-[var(--color-text-secondary)]">Analysé</span>
									{formatRelativeTime(currentItem.timestamps?.analysis_completed_at || currentItem.queued_at)}
								</span>
							{/if}
							<!-- Complexity badges (v2.3) -->
							{#if currentItem.analysis.multi_pass}
								{@const mp = currentItem.analysis.multi_pass}
								{@const isQuick = mp.passes_count === 1 && mp.final_model === 'haiku'}
								{@const hasContext = mp.pass_history?.some(p => p.context_searched)}
								{@const isComplex = mp.passes_count >= 3}
								{@const usedOpus = mp.final_model === 'opus' || mp.models_used?.includes('opus')}
								<div class="flex items-center gap-1 ml-auto">
									{#if isQuick}
										<span class="text-base" title="Analyse rapide : 1 pass avec Haiku" data-testid="badge-quick">⚡</span>
									{/if}
									{#if hasContext}
										<span class="text-base" title="Contexte personnel utilisé" data-testid="badge-context">🔍</span>
									{/if}
									{#if isComplex}
										<span class="text-base" title="Analyse complexe : {mp.passes_count} passes" data-testid="badge-complex">🧠</span>
									{/if}
									{#if usedOpus}
										<span class="text-base" title="Analyse avec Opus (modèle le plus puissant)" data-testid="badge-opus">🏆</span>
									{/if}
								</div>
							{/if}
						</div>

						<!-- Sender info with avatar (like history page) -->
						<div class="flex items-center gap-3">
							<div
								class="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--color-accent)] to-purple-500 flex items-center justify-center text-white font-semibold shrink-0"
							>
								{(currentItem.metadata.from_name || currentItem.metadata.from_address || '?')
									.split(' ')
									.map((n) => n[0])
									.join('')
									.toUpperCase()
									.slice(0, 2) || '?'}
							</div>
							<div class="min-w-0 flex-1">
								<h2 class="text-lg font-bold text-[var(--color-text-primary)] leading-tight">
									{currentItem.metadata.subject}
								</h2>
								<p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
									{currentItem.metadata.from_name || 'Expéditeur inconnu'}
									<span class="text-[var(--color-text-tertiary)]">
										&lt;{currentItem.metadata.from_address}&gt;
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
							<div
								class="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-[var(--color-bg-secondary)] to-[var(--color-bg-tertiary)] border border-[var(--color-accent)]/30"
							>
								<div
									class="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0"
									style="background-color: color-mix(in srgb, {getActionColor(
										recommendedOption.action
									)} 25%, transparent)"
								>
									{getActionIcon(recommendedOption.action)}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span
											class="font-bold"
											style="color: {getActionColor(recommendedOption.action)}"
										>
											{getActionLabel(recommendedOption.action)}
										</span>
										<div
											class="flex-1 max-w-[80px] h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden"
										>
											<div
												class="h-full rounded-full"
												style="width: {recommendedOption.confidence}%; background-color: {getConfidenceColor(
													recommendedOption.confidence
												)}"
											></div>
										</div>
										<span
											class="text-xs font-medium"
											style="color: {getConfidenceColor(recommendedOption.confidence)}"
										>
											{recommendedOption.confidence}%
										</span>
										{#if recommendedOption.destination}
											<span class="text-xs text-[var(--color-text-tertiary)]"
												>→ {recommendedOption.destination}</span
											>
										{/if}
									</div>
									<p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
										{recommendedOption.reasoning}
									</p>
								</div>
							</div>
						{:else}
							<!-- Fallback when no options -->
							<div
								class="flex items-center gap-3 p-3 rounded-xl bg-[var(--color-bg-secondary)] border border-[var(--color-border)]"
							>
								<div
									class="w-10 h-10 rounded-lg flex items-center justify-center text-xl flex-shrink-0"
									style="background-color: color-mix(in srgb, {getActionColor(
										currentItem.analysis.action
									)} 25%, transparent)"
								>
									{getActionIcon(currentItem.analysis.action)}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2">
										<span
											class="font-bold"
											style="color: {getActionColor(currentItem.analysis.action)}"
										>
											{getActionLabel(currentItem.analysis.action)}
										</span>
										<div
											class="flex-1 max-w-[80px] h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden"
										>
											<div
												class="h-full rounded-full"
												style="width: {currentItem.analysis
													.confidence}%; background-color: {getConfidenceColor(
													currentItem.analysis.confidence
												)}"
											></div>
										</div>
										<span
											class="text-xs font-medium"
											style="color: {getConfidenceColor(currentItem.analysis.confidence)}"
										>
											{currentItem.analysis.confidence}%
										</span>
									</div>
									{#if currentItem.analysis.reasoning}
										<p class="text-sm text-[var(--color-text-secondary)] mt-0.5">
											{currentItem.analysis.reasoning}
										</p>
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
									{#if filterNotes(currentItem.analysis.proposed_notes, false).some((n) => n.required)}
										<span
											class="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300"
											>requis</span
										>
									{/if}
								</div>
								{@render enrichmentsSection()}
							</div>
						{/if}

						<!-- SECTION 4.1: SKIPPED ENRICHMENTS (Details mode only) -->
						{#if showLevel3}
							{@const skippedNotes = filterSkippedNotes(currentItem.analysis.proposed_notes)}
							{@const skippedTasks = filterSkippedTasks(currentItem.analysis.proposed_tasks)}
							{#if skippedNotes.length > 0 || skippedTasks.length > 0}
								<div class="space-y-2">
									<div class="flex items-center gap-2">
										<span class="text-sm font-medium text-[var(--color-text-tertiary)]">
											🚫 {skippedNotes.length + skippedTasks.length} enrichissement{skippedNotes.length + skippedTasks.length > 1 ? 's' : ''} non appliqué{skippedNotes.length + skippedTasks.length > 1 ? 's' : ''}
										</span>
									</div>
									<div class="space-y-2 opacity-60">
										{#each skippedNotes as note}
											{@const reason = note.manually_approved === false
												? 'Rejeté manuellement'
												: `Confiance insuffisante (${Math.round(note.confidence * 100)}% < ${note.required ? '80' : '85'}%)`}
											<div class="rounded-lg border border-dashed border-[var(--color-border)] p-2 bg-[var(--color-bg-secondary)]/50">
												<div class="flex items-center justify-between text-sm">
													<span class="flex items-center gap-2">
														<span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400">
															{note.action === 'create' ? '✨' : '~'} {note.note_type}
														</span>
														<span class="text-[var(--color-text-secondary)] line-through">{note.title || 'Sans titre'}</span>
													</span>
													<span class="text-xs text-[var(--color-text-tertiary)]" title={reason}>
														{note.manually_approved === false ? '✗ rejeté' : `${Math.round(note.confidence * 100)}%`}
													</span>
												</div>
												{#if note.content_summary}
													<p class="mt-1.5 text-xs text-[var(--color-text-tertiary)] pl-6 border-l-2 border-[var(--color-border)] ml-2 italic">
														{note.content_summary}
													</p>
												{/if}
												<p class="mt-1 text-[10px] text-[var(--color-text-tertiary)]">
													💡 {reason}
												</p>
											</div>
										{/each}
										{#each skippedTasks as task}
											{@const reason = `Confiance insuffisante (${Math.round(task.confidence * 100)}% < 85%)`}
											<div class="rounded-lg border border-dashed border-[var(--color-border)] p-2 bg-[var(--color-bg-secondary)]/50">
												<div class="flex items-center justify-between text-sm">
													<span class="flex items-center gap-2">
														<span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400">
															📋 OmniFocus
														</span>
														<span class="text-[var(--color-text-secondary)] line-through">{task.title}</span>
													</span>
													<span class="text-xs text-[var(--color-text-tertiary)]">
														{Math.round(task.confidence * 100)}%
													</span>
												</div>
												<p class="mt-1 text-[10px] text-[var(--color-text-tertiary)]">
													💡 {reason}
												</p>
											</div>
										{/each}
									</div>
								</div>
							{/if}
						{/if}

						<!-- SECTION 4.2: STRATEGIC QUESTIONS (v3.1) -->
						{@render strategicQuestionsSection()}

						<!-- SECTION 4.5: CONTEXT INFLUENCE (visible by default - like history page) -->
						{#if currentItem.analysis.context_influence}
							{@const ci = currentItem.analysis.context_influence}
							<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]">
								<h4 class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide mb-2">
									🧠 Influence du contexte
								</h4>

								<!-- AI Explanation -->
								{#if ci.explanation}
									<p class="text-sm text-[var(--color-text-secondary)] mb-3">
										{ci.explanation}
									</p>
								{/if}

								<!-- Notes used -->
								{#if ci.notes_used && ci.notes_used.length > 0}
									<div class="flex flex-wrap gap-1 mb-2">
										{#each ci.notes_used as noteName}
											<span class="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400">
												📝 {noteName}
											</span>
										{/each}
									</div>
								{/if}

								<!-- Confirmations -->
								{#if ci.confirmations && ci.confirmations.length > 0}
									<div class="mb-2">
										<span class="text-xs text-green-500 font-medium">✓ Confirmé :</span>
										<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
											{#each ci.confirmations as confirmation}
												<li>{confirmation}</li>
											{/each}
										</ul>
									</div>
								{/if}

								<!-- Contradictions -->
								{#if ci.contradictions && ci.contradictions.length > 0}
									<div class="mb-2">
										<span class="text-xs text-orange-400 font-medium">⚠ Contradiction :</span>
										<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
											{#each ci.contradictions as contradiction}
												<li>{contradiction}</li>
											{/each}
										</ul>
									</div>
								{/if}

								<!-- Missing info -->
								{#if ci.missing_info && ci.missing_info.length > 0}
									<div class="mb-2">
										<span class="text-xs text-[var(--color-text-tertiary)] font-medium">❓ Manquant :</span>
										<ul class="text-xs text-[var(--color-text-tertiary)] ml-4 mt-1">
											{#each ci.missing_info as missing}
												<li>{missing}</li>
											{/each}
										</ul>
									</div>
								{/if}
							</div>
						{/if}

						<!-- SECTION 4.6: RETRIEVED CONTEXT (visible by default - like history page) -->
						{#if currentItem.analysis.retrieved_context && currentItem.analysis.retrieved_context.total_results > 0}
							<details class="rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] overflow-hidden">
								<summary class="px-3 py-2 text-xs font-semibold text-[var(--color-text-tertiary)] uppercase tracking-wide cursor-pointer hover:bg-[var(--color-bg-tertiary)]">
									📊 Contexte récupéré ({currentItem.analysis.retrieved_context.total_results} résultats)
								</summary>

								<div class="px-3 pb-3 space-y-3">
									<!-- Entities searched -->
									{#if currentItem.analysis.retrieved_context.entities_searched?.length > 0}
										<div>
											<span class="text-xs text-[var(--color-text-tertiary)]">Entités recherchées :</span>
											<div class="flex flex-wrap gap-1 mt-1">
												{#each currentItem.analysis.retrieved_context.entities_searched as entity}
													<span class="text-xs px-2 py-0.5 rounded bg-[var(--glass-tint)] text-[var(--color-text-secondary)]">
														{entity}
													</span>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Notes found -->
									{#if currentItem.analysis.retrieved_context.notes?.length > 0}
										<div>
											<span class="text-xs text-[var(--color-text-tertiary)]">Notes trouvées :</span>
											<div class="mt-1 space-y-1">
												{#each currentItem.analysis.retrieved_context.notes as note}
													<div class="flex items-center gap-2 text-xs">
														<span class="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
															{note.note_type}
														</span>
														<a href="/memoires/{note.path ? `${note.path}/${note.note_id}` : note.note_id}" class="text-[var(--color-accent)] hover:underline">
															{note.title}
														</a>
														<span class="text-[var(--color-text-tertiary)]">
															({Math.round((note.relevance ?? 0) * 100)}%)
														</span>
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Calendar events -->
									{#if currentItem.analysis.retrieved_context.calendar?.length > 0}
										<div>
											<span class="text-xs text-[var(--color-text-tertiary)]">Événements calendrier :</span>
											<div class="mt-1 space-y-1">
												{#each currentItem.analysis.retrieved_context.calendar as event}
													<div class="text-xs text-[var(--color-text-secondary)]">
														📅 {event.date} - {event.title}
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Tasks -->
									{#if currentItem.analysis.retrieved_context.tasks?.length > 0}
										<div>
											<span class="text-xs text-[var(--color-text-tertiary)]">Tâches OmniFocus :</span>
											<div class="mt-1 space-y-1">
												{#each currentItem.analysis.retrieved_context.tasks as task}
													<div class="text-xs text-[var(--color-text-secondary)]">
														⚡ {task.title}
														{#if task.project}
															<span class="text-[var(--color-text-tertiary)]">[{task.project}]</span>
														{/if}
													</div>
												{/each}
											</div>
										</div>
									{/if}

									<!-- Sources searched -->
									{#if currentItem.analysis.retrieved_context.sources_searched?.length > 0}
										<div class="text-xs text-[var(--color-text-tertiary)]">
											Sources : {currentItem.analysis.retrieved_context.sources_searched.join(', ')}
										</div>
									{/if}
								</div>
							</details>
						{/if}

						<!-- SECTION 5: REANALYZE PANEL (v2.5: full options) -->
						{#if showReanalyzePanel}
							<div
								class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]"
							>
								<div class="flex items-center gap-2 mb-3">
									<span class="text-lg">🔄</span>
									<span class="text-sm font-medium text-[var(--color-text-primary)]"
										>Réanalyser cette péripétie</span
									>
								</div>

								<!-- Instruction personnalisée -->
								<div class="mb-3">
									<span class="block text-xs font-medium text-[var(--color-text-secondary)] mb-1">
										Instruction personnalisée (optionnel)
									</span>
									<textarea
										bind:value={reanalyzeInstruction}
										placeholder="Ex: Classer dans Archive/2025/Relevés, considérer comme urgent..."
										class="w-full p-2 text-sm rounded border border-[var(--color-border)] bg-[var(--color-bg-primary)] text-[var(--color-text-primary)] resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
										rows="2"
										aria-label="Instruction personnalisée"
									></textarea>
								</div>

								<!-- Sélection du modèle -->
								<div class="mb-3" role="radiogroup" aria-label="Modèle d'analyse">
									<span class="block text-xs font-medium text-[var(--color-text-secondary)] mb-2">
										Modèle d'analyse
									</span>
									<div class="grid grid-cols-2 gap-2">
										<label
											class="flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors {reanalyzeModel === 'standard' ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10' : 'border-[var(--color-border)] hover:border-[var(--color-accent)]/50'}"
										>
											<input type="radio" bind:group={reanalyzeModel} value="standard" class="sr-only" />
											<span class="text-sm">⚡</span>
											<div class="flex-1">
												<div class="text-sm font-medium">Standard</div>
												<div class="text-xs text-[var(--color-text-tertiary)]">Multi-pass adaptatif</div>
											</div>
										</label>
										<label
											class="flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors {reanalyzeModel === 'haiku' ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10' : 'border-[var(--color-border)] hover:border-[var(--color-accent)]/50'}"
										>
											<input type="radio" bind:group={reanalyzeModel} value="haiku" class="sr-only" />
											<span class="text-sm">🌸</span>
											<div class="flex-1">
												<div class="text-sm font-medium">Haiku</div>
												<div class="text-xs text-[var(--color-text-tertiary)]">Rapide, économique</div>
											</div>
										</label>
										<label
											class="flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors {reanalyzeModel === 'sonnet' ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10' : 'border-[var(--color-border)] hover:border-[var(--color-accent)]/50'}"
										>
											<input type="radio" bind:group={reanalyzeModel} value="sonnet" class="sr-only" />
											<span class="text-sm">📝</span>
											<div class="flex-1">
												<div class="text-sm font-medium">Sonnet</div>
												<div class="text-xs text-[var(--color-text-tertiary)]">Équilibré</div>
											</div>
										</label>
										<label
											class="flex items-center gap-2 p-2 rounded border cursor-pointer transition-colors {reanalyzeModel === 'opus' ? 'border-purple-500 bg-purple-500/10' : 'border-[var(--color-border)] hover:border-purple-500/50'}"
										>
											<input type="radio" bind:group={reanalyzeModel} value="opus" class="sr-only" />
											<span class="text-sm">🏆</span>
											<div class="flex-1">
												<div class="text-sm font-medium text-purple-600 dark:text-purple-400">Opus</div>
												<div class="text-xs text-[var(--color-text-tertiary)]">Maximum de précision</div>
											</div>
										</label>
									</div>
								</div>

								<!-- Actions -->
								<div class="flex gap-2">
									<Button
										variant="primary"
										size="sm"
										onclick={() => handleReanalyzeItem(currentItem, 'immediate')}
										disabled={isReanalyzingItem}
									>
										▶️ Maintenant
									</Button>
									<Button
										variant="secondary"
										size="sm"
										onclick={() => handleReanalyzeItem(currentItem, 'background')}
										disabled={isReanalyzingItem}
									>
										📥 Plus tard
									</Button>
									<div class="flex-1"></div>
									<Button variant="ghost" size="sm" onclick={toggleReanalyzePanel}>Annuler</Button>
								</div>
							</div>
						{/if}

						<!-- SECTION 6: Other options (Details mode) -->
						{#if showLevel3 && otherOptions.length > 0}
							<div class="space-y-2">
								<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">
									Autres options
								</p>
								{#each otherOptions as option, idx}
									<button
										class="w-full text-left p-3 rounded-lg border border-[var(--color-border)] hover:border-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)] transition-all"
										disabled={isProcessing}
										onclick={() => handleSelectOption(currentItem, option)}
									>
										<div class="flex items-center gap-2">
											<span
												class="w-6 h-6 rounded bg-[var(--color-bg-tertiary)] flex items-center justify-center text-xs font-mono"
												>{idx + 2}</span
											>
											<span class="text-lg">{getActionIcon(option.action)}</span>
											<span class="font-medium" style="color: {getActionColor(option.action)}"
												>{getActionLabel(option.action)}</span
											>
											<span
												class="text-xs ml-auto"
												style="color: {getConfidenceColor(option.confidence)}"
												>{option.confidence}%</span
											>
										</div>
										<p class="text-xs text-[var(--color-text-secondary)] mt-1 ml-8">
											{option.reasoning}
										</p>
									</button>
								{/each}
							</div>
						{/if}

						<!-- SECTION 7: Entities (Details mode) -->
						{#if showLevel3 && currentItem.analysis.entities && Object.keys(currentItem.analysis.entities).length > 0}
							<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
								<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase mb-2">
									Entités extraites
								</p>
								<div class="flex flex-wrap gap-1">
									{#each Object.entries(currentItem.analysis.entities) as [type, entities]}
										{#each entities as entity}
											{@const entityClass =
												{
													person:
														'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
													project:
														'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
													date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
													amount:
														'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
													organization:
														'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300'
												}[type] ??
												'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'}
											<span class="px-2 py-0.5 text-xs rounded-full {entityClass}"
												>{entity.value}</span
											>
										{/each}
									{/each}
								</div>
							</div>
						{/if}

						<!-- SECTION 8: Context & Metadata (Details mode) -->
						{#if showLevel3}
							{#if currentItem.analysis.context_used && currentItem.analysis.context_used.length > 0}
								<div class="p-2 rounded-lg bg-[var(--color-bg-secondary)]">
									<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase mb-1">
										Contexte utilisé
									</p>
									<div class="flex flex-wrap gap-1">
										{#each currentItem.analysis.context_used as noteId}
											<a
												href="/memoires/{noteId}"
												class="text-xs px-2 py-0.5 rounded-full bg-[var(--color-event-notes)]/20 text-[var(--color-event-notes)] hover:bg-[var(--color-event-notes)]/30"
											>
												📝 {noteId.slice(0, 15)}...
											</a>
										{/each}
									</div>
								</div>
							{/if}
							<div
								class="flex flex-wrap gap-2 text-xs text-[var(--color-text-tertiary)] p-2 rounded-lg bg-[var(--color-bg-secondary)]"
							>
								<span>📧 {currentItem.metadata.from_address}</span>
								<span>📁 {currentItem.metadata.folder || 'INBOX'}</span>
								<span>🕐 {formatRelativeTime(currentItem.timestamps?.analysis_completed_at || currentItem.queued_at)}</span>
							</div>
						{/if}

						<!-- SECTION 8.5: Analysis Transparency (v2.3) -->
						{#if showLevel3 && currentItem.analysis.multi_pass}
							{@const mp = currentItem.analysis.multi_pass}
							<div class="p-3 rounded-lg bg-[var(--color-bg-secondary)] space-y-3">
								<div class="flex items-center justify-between">
									<p class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">
										Transparence de l'Analyse
									</p>
									<span class="text-xs text-[var(--color-text-tertiary)]">
										{mp.passes_count} pass{mp.passes_count > 1 ? 'es' : ''} • {mp.final_model}
										{#if mp.escalated}
											• <span class="text-amber-500">escaladé</span>
										{/if}
									</span>
								</div>

								<!-- Confidence Sparkline -->
								{#if mp.pass_history && mp.pass_history.length > 0}
									<div>
										<p class="text-xs text-[var(--color-text-tertiary)] mb-1">Évolution de la confiance</p>
										<ConfidenceSparkline passHistory={mp.pass_history} id={currentItem.id} />
									</div>
								{/if}

								<!-- Pass Timeline -->
								{#if mp.pass_history && mp.pass_history.length > 0}
									<div>
										<p class="text-xs text-[var(--color-text-tertiary)] mb-1">Détail des passes</p>
										<PassTimeline passHistory={mp.pass_history} />
									</div>
								{/if}

								<!-- Context Influence (v2.2.2) -->
								{#if currentItem.analysis.context_influence}
									{@const ci = currentItem.analysis.context_influence}
									<div class="p-2 rounded bg-[var(--color-bg-tertiary)]">
										<p class="text-xs font-medium text-[var(--color-text-secondary)] mb-1">
											💡 Influence du contexte
										</p>
										{#if ci.explanation}
											<p class="text-xs text-[var(--color-text-secondary)]">{ci.explanation}</p>
										{/if}
										{#if ci.confirmations && ci.confirmations.length > 0}
											<div class="mt-1">
												<span class="text-xs text-green-600">✓ Confirmé :</span>
												<span class="text-xs text-[var(--color-text-tertiary)]">
													{ci.confirmations.join(', ')}
												</span>
											</div>
										{/if}
										{#if ci.contradictions && ci.contradictions.length > 0}
											<div class="mt-1">
												<span class="text-xs text-red-600">✗ Contradictions :</span>
												<span class="text-xs text-[var(--color-text-tertiary)]">
													{ci.contradictions.join(', ')}
												</span>
											</div>
										{/if}
									</div>
								{/if}

								<!-- Thinking Bubbles: Questions between passes -->
								{#if mp.pass_history?.some(p => p.questions && p.questions.length > 0)}
									<div class="p-2 rounded bg-blue-50 dark:bg-blue-900/20">
										<p class="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">
											💭 Questions soulevées
										</p>
										<ul class="text-xs text-blue-600 dark:text-blue-400 space-y-0.5">
											{#each mp.pass_history as pass}
												{#if pass.questions && pass.questions.length > 0}
													{#each pass.questions as question}
														<li>• {question}</li>
													{/each}
												{/if}
											{/each}
										</ul>
									</div>
								{/if}

								<!-- Stop reason -->
								{#if mp.stop_reason}
									<p class="text-xs text-[var(--color-text-tertiary)]">
										Raison d'arrêt : <span class="font-mono">{mp.stop_reason}</span>
									</p>
								{/if}
							</div>
						{/if}

						<!-- SECTION 10: EMAIL (at bottom, larger height) -->
						<div class="rounded-lg border border-[var(--color-border)] overflow-hidden">
							<div
								class="flex items-center justify-between px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]"
							>
								<span class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase"
									>Email</span
								>
								{#if currentItem.content?.html_body}
									<div class="flex gap-1">
										<button
											class="text-xs px-2 py-0.5 rounded {!showHtmlContent
												? 'bg-[var(--color-accent)] text-white'
												: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
											onclick={() => (showHtmlContent = false)}>Texte</button
										>
										<button
											class="text-xs px-2 py-0.5 rounded {showHtmlContent
												? 'bg-[var(--color-accent)] text-white'
												: 'bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)]'}"
											onclick={() => (showHtmlContent = true)}>HTML</button
										>
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
								<div
									class="p-3 text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap max-h-96 overflow-y-auto bg-[var(--color-bg-primary)]"
								>
									{currentItem.content?.full_text ||
										currentItem.content?.preview ||
										'Aucun contenu'}
								</div>
							{/if}
						</div>

						<!-- SECTION 10.5: ATTACHMENTS (like history page) -->
						{#if currentItem.metadata.attachments && currentItem.metadata.attachments.length > 0}
							<div class="rounded-lg border border-[var(--color-border)] overflow-hidden">
								<div
									class="px-3 py-2 bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)]"
								>
									<span class="text-xs font-semibold text-[var(--color-text-tertiary)] uppercase">
										📎 Pièces jointes ({currentItem.metadata.attachments.length})
									</span>
								</div>
								<div class="p-3 space-y-2">
									{#each currentItem.metadata.attachments as attachment (attachment.filename)}
										<FileAttachment {attachment} emailId={currentItem.metadata.id} />
									{/each}
								</div>
							</div>
						{/if}

						<!-- Keyboard help (compact) -->
						<div
							class="text-xs text-center text-[var(--color-text-tertiary)] flex flex-wrap justify-center gap-2"
						>
							<span
								><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">J/K</span> nav</span
							>
							<span
								><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">A</span> approuver</span
							>
							<span
								><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">R</span> opus</span
							>
							<span
								><span class="font-mono bg-[var(--color-bg-tertiary)] px-1 rounded">E</span> détails</span
							>
						</div>

						<!-- Snooze/Error feedback -->
						{#if snoozeSuccess}
							<div
								class="flex items-center gap-2 p-2 rounded-lg bg-green-500/20 text-green-400 text-sm"
							>
								<span>💤</span><span>{snoozeSuccess}</span>
							</div>
						{:else if snoozeError}
							<div
								class="flex items-center gap-2 p-2 rounded-lg bg-red-500/20 text-red-400 text-sm"
							>
								<span>⚠️</span><span>{snoozeError}</span>
							</div>
						{/if}
					</div>
				</Card>
			</LongPressMenu>
		</SwipeableCard>

		<!-- LIST VIEW for other filters (approved, rejected, auto) -->
	{:else}
		<section class="list-view-container" data-testid="peripeties-list">
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
					<div class="pb-3" data-testid="peripeties-item-{item.id}">
						<!-- Special view for items in progress (analyzing) -->
						{#if activeTab === 'in_progress'}
							{@const progress = getAnalysisProgress(item.timestamps?.analysis_started_at)}
							<Card padding="md" class="border-[var(--color-accent)]/30 bg-[var(--color-accent)]/5">
								<div class="space-y-3">
									<!-- Progress header -->
									<div class="flex items-center justify-between">
										<div class="flex items-center gap-2">
											<div class="w-6 h-6 rounded-full bg-[var(--color-accent)]/20 flex items-center justify-center">
												<span class="animate-spin text-sm">⏳</span>
											</div>
											<span class="text-sm font-medium text-[var(--color-accent)]">
												{progress.stageLabel}
											</span>
											<span class="text-xs text-[var(--color-text-tertiary)]">
												{progress.stageDescription}
											</span>
										</div>
										<span class="text-xs font-mono text-[var(--color-text-secondary)]">
											{formatElapsedTime(progress.elapsedSeconds)}
										</span>
									</div>

									<!-- Progress bar with valet stages -->
									<div class="space-y-1">
										<div class="flex items-center gap-1 text-[10px] text-[var(--color-text-tertiary)]">
											<span class:text-[var(--color-accent)]={progress.stage === 'grimaud'} class:font-medium={progress.stage === 'grimaud'}>grimaud</span>
											<span>→</span>
											<span class:text-[var(--color-accent)]={progress.stage === 'bazin'} class:font-medium={progress.stage === 'bazin'}>bazin</span>
											<span>→</span>
											<span class:text-[var(--color-accent)]={progress.stage === 'planchet'} class:font-medium={progress.stage === 'planchet'}>planchet</span>
											<span>→</span>
											<span class:text-[var(--color-accent)]={progress.stage === 'mousqueton' || progress.stage === 'finalizing'} class:font-medium={progress.stage === 'mousqueton' || progress.stage === 'finalizing'}>mousqueton</span>
										</div>
										<div class="h-1.5 bg-[var(--color-bg-tertiary)] rounded-full overflow-hidden">
											<div
												class="h-full bg-[var(--color-accent)] rounded-full transition-all duration-500"
												style="width: {progress.progress}%"
											></div>
										</div>
									</div>

									<!-- Email info -->
									<div class="pt-2 border-t border-[var(--color-border)]">
										<h3 class="font-medium text-[var(--color-text-primary)] truncate">
											{item.metadata.subject || 'Sans sujet'}
										</h3>
										<p class="text-xs text-[var(--color-text-secondary)] mt-0.5">
											{item.metadata.from_name || item.metadata.from_address || 'Expéditeur inconnu'}
											<span class="text-[var(--color-text-tertiary)]">
												• {item.metadata.date
													? formatRelativeTime(item.metadata.date)
													: formatRelativeTime(item.queued_at)}
											</span>
											{#if item.metadata.has_attachments}
												<span class="ml-1" title="Contient des pièces jointes">📎</span>
											{/if}
										</p>
									</div>
								</div>
							</Card>
						{:else}
						<!-- Standard view for other tabs -->
						<Card padding="md" class="hover:border-[var(--color-accent)] transition-colors">
							<div class="flex items-start gap-3">
								<a
									href="/peripeties/{item.id}"
									class="flex items-start gap-3 flex-1 min-w-0 no-underline text-inherit"
								>
									<!-- Action icon -->
									<div
										class="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-lg"
										style="background-color: color-mix(in srgb, {getActionColor(
											item.analysis?.action || 'pending'
										)} 20%, transparent)"
									>
										{getActionIcon(item.analysis?.action || 'pending')}
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
												• {item.metadata.date
													? formatRelativeTime(item.metadata.date)
													: formatRelativeTime(item.queued_at)}
											</span>
											<!-- v2.4: Context indicators -->
											{#if item.metadata.has_attachments}
												<span
													class="ml-1 text-[var(--color-text-tertiary)]"
													title="Contient des pièces jointes"
												>
													📎
												</span>
											{/if}
											{#if item.analysis.context_used && item.analysis.context_used.length > 0}
												<span
													class="ml-1 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[10px] bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300"
													title="L'analyse a utilisé {item.analysis.context_used.length} note{item.analysis.context_used.length > 1 ? 's' : ''} existante{item.analysis.context_used.length > 1 ? 's' : ''}"
												>
													🧠 Contexte
												</span>
											{/if}
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
														{@const entityClass =
															{
																person:
																	'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
																project:
																	'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
																date: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300',
																amount:
																	'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300',
																organization:
																	'bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300',
																discovered:
																	'bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-300'
															}[type] ??
															'bg-gray-100 text-gray-700 dark:bg-gray-500/20 dark:text-gray-300'}
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
									<div class="flex items-center gap-1">
										<!-- Complexity badges (v2.3) -->
										{#if item.analysis.multi_pass}
											{@const mp = item.analysis.multi_pass}
											{@const isQuick = mp.passes_count === 1 && mp.final_model === 'haiku'}
											{@const hasContext = mp.pass_history?.some(p => p.context_searched)}
											{@const isComplex = mp.passes_count >= 3}
											{@const usedOpus = mp.final_model === 'opus' || mp.models_used?.includes('opus')}
											{#if isQuick}
												<span class="text-xs" title="Analyse rapide : 1 pass avec Haiku" data-testid="badge-quick">⚡</span>
											{/if}
											{#if hasContext}
												<span class="text-xs" title="Contexte personnel utilisé" data-testid="badge-context">🔍</span>
											{/if}
											{#if isComplex}
												<span class="text-xs" title="Analyse complexe : {mp.passes_count} passes" data-testid="badge-complex">🧠</span>
											{/if}
											{#if usedOpus}
												<span class="text-xs" title="Analyse avec Opus (modèle le plus puissant)" data-testid="badge-opus">🏆</span>
											{/if}
										{/if}
										<span
											class="text-xs px-2 py-1 rounded-full"
											class:bg-green-100={item.status === 'approved'}
											class:text-green-700={item.status === 'approved'}
											class:bg-red-100={item.status === 'rejected'}
											class:text-red-700={item.status === 'rejected'}
										>
											{getActionLabel(item.analysis.action)}
										</span>
									</div>
									{#if item.reviewed_at}
										<p class="text-xs text-[var(--color-text-tertiary)]">
											{formatRelativeTime(item.reviewed_at)}
										</p>
									{/if}
									<!-- Undo button for approved items -->
									{#if item.status === 'approved' && undoableItems.has(item.id)}
										<button
											class="text-xs px-2 py-1 rounded bg-orange-100 text-orange-700 hover:bg-orange-200 transition-colors disabled:opacity-50"
											onclick={(e) => {
												e.stopPropagation();
												handleUndoItem(item);
											}}
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
						{/if}
					</div>
				{/snippet}

				{#snippet empty()}
					<Card padding="lg">
						<div class="text-center py-8">
							<p class="text-4xl mb-3">
								{#if activeTab === 'history'}✅
								{:else if activeTab === 'errors'}🎉
								{:else if activeTab === 'snoozed'}💤
								{:else if activeTab === 'in_progress'}⏳
								{:else}📭
								{/if}
							</p>
							<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
								{#if activeTab === 'history'}
									Historique vide
								{:else if activeTab === 'errors'}
									Tout fonctionne !
								{:else if activeTab === 'snoozed'}
									Aucune péripétie reportée
								{:else if activeTab === 'in_progress'}
									Aucune analyse en cours
								{:else}
									Boîte de réception vide
								{/if}
							</h3>
							<p class="text-sm text-[var(--color-text-secondary)]">
								{#if activeTab === 'history'}
									Les péripéties traitées apparaîtront ici
								{:else if activeTab === 'errors'}
									Aucun email n'a rencontré de problème
								{:else if activeTab === 'snoozed'}
									Les péripéties reportées apparaîtront ici
								{:else if activeTab === 'in_progress'}
									Les analyses en cours apparaîtront ici
								{:else}
									Lancez la récupération des emails pour alimenter la file
								{/if}
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
