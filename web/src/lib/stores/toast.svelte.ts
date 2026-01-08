/**
 * Toast Notification Store
 * Manages toast notifications with auto-dismiss and stacking
 * Supports special Undo toasts with countdown and action callback
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'undo';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
	title?: string;
	duration?: number;
	dismissible?: boolean;
	// Undo-specific properties
	onUndo?: () => Promise<void> | void;
	countdownSeconds?: number;
	itemId?: string;
}

interface ToastOptions {
	title?: string;
	duration?: number;
	dismissible?: boolean;
}

interface UndoToastOptions {
	title?: string;
	itemId?: string;
	countdownSeconds?: number; // Default 300 (5 minutes)
}

const DEFAULT_DURATION = 4000;
const DEFAULT_UNDO_COUNTDOWN = 300; // 5 minutes in seconds
const MAX_TOASTS = 5;

// Map to track countdown intervals
const countdownIntervals = new Map<string, ReturnType<typeof setInterval>>();

function createToastStore() {
	let toasts = $state<Toast[]>([]);
	let counter = 0;
	const timeouts = new Map<string, ReturnType<typeof setTimeout>>();

	function add(type: ToastType, message: string, options: ToastOptions = {}) {
		const id = `toast-${++counter}`;
		const toast: Toast = {
			id,
			type,
			message,
			title: options.title,
			duration: options.duration ?? DEFAULT_DURATION,
			dismissible: options.dismissible ?? true
		};

		// Add toast (limit to MAX_TOASTS)
		toasts = [toast, ...toasts].slice(0, MAX_TOASTS);

		// Auto-dismiss if duration > 0
		if (toast.duration && toast.duration > 0) {
			const timeoutId = setTimeout(() => {
				dismiss(id);
			}, toast.duration);
			timeouts.set(id, timeoutId);
		}

		return id;
	}

	function dismiss(id: string) {
		// Clear timeout if exists
		const timeoutId = timeouts.get(id);
		if (timeoutId) {
			clearTimeout(timeoutId);
			timeouts.delete(id);
		}

		// Clear countdown interval if exists
		const intervalId = countdownIntervals.get(id);
		if (intervalId) {
			clearInterval(intervalId);
			countdownIntervals.delete(id);
		}

		toasts = toasts.filter((t) => t.id !== id);
	}

	function clear() {
		// Clear all timeouts
		timeouts.forEach((timeoutId) => clearTimeout(timeoutId));
		timeouts.clear();

		// Clear all countdown intervals
		countdownIntervals.forEach((intervalId) => clearInterval(intervalId));
		countdownIntervals.clear();

		toasts = [];
	}

	/**
	 * Show an Undo toast with countdown timer
	 * @param message - Message to display (e.g., "Email archivé")
	 * @param onUndo - Callback when user clicks Undo
	 * @param options - Additional options (title, itemId, countdownSeconds)
	 * @returns Toast ID
	 */
	function undo(
		message: string,
		onUndo: () => Promise<void> | void,
		options: UndoToastOptions = {}
	): string {
		const id = `toast-${++counter}`;
		const countdownSeconds = options.countdownSeconds ?? DEFAULT_UNDO_COUNTDOWN;

		const toast: Toast = {
			id,
			type: 'undo',
			message,
			title: options.title,
			dismissible: true,
			onUndo,
			countdownSeconds,
			itemId: options.itemId
		};

		// Add toast at the start
		toasts = [toast, ...toasts].slice(0, MAX_TOASTS);

		// Start countdown interval (updates every second)
		const intervalId = setInterval(() => {
			toasts = toasts.map((t) => {
				if (t.id === id && t.countdownSeconds !== undefined && t.countdownSeconds > 0) {
					return { ...t, countdownSeconds: t.countdownSeconds - 1 };
				}
				return t;
			});

			// Check if countdown reached 0
			const currentToast = toasts.find((t) => t.id === id);
			if (currentToast && currentToast.countdownSeconds !== undefined && currentToast.countdownSeconds <= 0) {
				dismiss(id);
			}
		}, 1000);

		countdownIntervals.set(id, intervalId);

		return id;
	}

	/**
	 * Execute undo action for a toast and dismiss it
	 */
	async function executeUndo(id: string): Promise<boolean> {
		const toast = toasts.find((t) => t.id === id);
		if (!toast || toast.type !== 'undo' || !toast.onUndo) {
			return false;
		}

		try {
			await toast.onUndo();
			dismiss(id);
			// Show success feedback
			success('Action annulée');
			return true;
		} catch (err) {
			console.error('Undo failed:', err);
			error('Échec de l\'annulation');
			return false;
		}
	}

	/**
	 * Find undo toast by item ID
	 */
	function findUndoByItemId(itemId: string): Toast | undefined {
		return toasts.find((t) => t.type === 'undo' && t.itemId === itemId);
	}

	// Convenience methods
	function success(message: string, options?: ToastOptions) {
		return add('success', message, options);
	}

	function error(message: string, options?: ToastOptions) {
		return add('error', message, { duration: 6000, ...options });
	}

	function warning(message: string, options?: ToastOptions) {
		return add('warning', message, options);
	}

	function info(message: string, options?: ToastOptions) {
		return add('info', message, options);
	}

	return {
		get toasts() {
			return toasts;
		},
		add,
		dismiss,
		clear,
		success,
		error,
		warning,
		info,
		undo,
		executeUndo,
		findUndoByItemId
	};
}

export const toastStore = createToastStore();
