/**
 * Toast Notification Store
 * Manages toast notifications with auto-dismiss and stacking
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
	id: string;
	type: ToastType;
	message: string;
	title?: string;
	duration?: number;
	dismissible?: boolean;
}

interface ToastOptions {
	title?: string;
	duration?: number;
	dismissible?: boolean;
}

const DEFAULT_DURATION = 4000;
const MAX_TOASTS = 5;

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
		toasts = toasts.filter((t) => t.id !== id);
	}

	function clear() {
		// Clear all timeouts
		timeouts.forEach((timeoutId) => clearTimeout(timeoutId));
		timeouts.clear();
		toasts = [];
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
		info
	};
}

export const toastStore = createToastStore();
