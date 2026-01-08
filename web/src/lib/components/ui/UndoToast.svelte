<script lang="ts">
	/**
	 * UndoToast Component
	 * Special toast with countdown timer and Undo button
	 * Used for reversible actions (archive, delete, approve, etc.)
	 */
	import { haptic } from '$lib/utils/haptics';

	interface Props {
		id: string;
		message: string;
		title?: string;
		countdownSeconds: number;
		onUndo: () => void;
		onDismiss: () => void;
	}

	let { id, message, title, countdownSeconds, onUndo, onDismiss }: Props = $props();

	// Format countdown as MM:SS
	const formattedTime = $derived.by(() => {
		const mins = Math.floor(countdownSeconds / 60);
		const secs = countdownSeconds % 60;
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	});

	// Progress percentage (0-100)
	const progress = $derived.by(() => {
		// Assume 300 seconds (5 min) as max for visual progress
		const maxSeconds = 300;
		return Math.max(0, Math.min(100, (countdownSeconds / maxSeconds) * 100));
	});

	// Urgency level based on remaining time
	const urgencyClass = $derived.by(() => {
		if (countdownSeconds <= 30) return 'urgent';
		if (countdownSeconds <= 60) return 'warning';
		return 'normal';
	});

	function handleUndo() {
		haptic('medium');
		onUndo();
	}

	function handleDismiss() {
		haptic('light');
		onDismiss();
	}
</script>

<div
	class="undo-toast glass-prominent rounded-2xl shadow-lg animate-toast-in overflow-hidden"
	class:urgent={urgencyClass === 'urgent'}
	class:warning={urgencyClass === 'warning'}
	role="alert"
	aria-live="assertive"
	data-testid="undo-toast-{id}"
>
	<!-- Progress bar at top -->
	<div class="progress-bar-container">
		<div
			class="progress-bar"
			class:urgent={urgencyClass === 'urgent'}
			class:warning={urgencyClass === 'warning'}
			style="width: {progress}%"
		></div>
	</div>

	<div class="flex items-center gap-3 p-4">
		<!-- Undo icon -->
		<div class="flex-shrink-0 text-[var(--color-accent)]">
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
				<path stroke-linecap="round" stroke-linejoin="round" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
			</svg>
		</div>

		<!-- Content -->
		<div class="flex-1 min-w-0">
			{#if title}
				<p class="font-medium text-[var(--color-text-primary)] text-sm">{title}</p>
			{/if}
			<p class="text-sm text-[var(--color-text-secondary)] {title ? 'mt-0.5' : ''}">{message}</p>
		</div>

		<!-- Countdown timer -->
		<div
			class="countdown-timer flex-shrink-0 text-sm font-mono"
			class:urgent={urgencyClass === 'urgent'}
			class:warning={urgencyClass === 'warning'}
		>
			{formattedTime}
		</div>

		<!-- Undo button -->
		<button
			type="button"
			class="undo-button flex-shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
			onclick={handleUndo}
			data-testid="undo-button"
		>
			Annuler
		</button>

		<!-- Dismiss button -->
		<button
			type="button"
			class="flex-shrink-0 p-1.5 -m-1.5 rounded-full text-[var(--color-text-tertiary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--glass-subtle)] transition-colors"
			onclick={handleDismiss}
			aria-label="Fermer"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>
</div>

<style>
	@keyframes toast-in {
		from {
			opacity: 0;
			transform: translateY(-20px) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.animate-toast-in {
		animation: toast-in var(--transition-normal) var(--spring-bouncy);
	}

	.undo-toast {
		background: var(--glass-prominent);
		border: 1px solid var(--color-accent-subtle);
	}

	.undo-toast.warning {
		border-color: var(--color-warning-subtle, rgba(245, 158, 11, 0.3));
	}

	.undo-toast.urgent {
		border-color: var(--color-error-subtle, rgba(239, 68, 68, 0.3));
		animation: toast-in var(--transition-normal) var(--spring-bouncy), pulse 1s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% {
			box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.2);
		}
		50% {
			box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.1);
		}
	}

	.progress-bar-container {
		height: 3px;
		background: var(--glass-subtle);
		width: 100%;
	}

	.progress-bar {
		height: 100%;
		background: var(--color-accent);
		transition: width 1s linear;
	}

	.progress-bar.warning {
		background: var(--color-warning, #f59e0b);
	}

	.progress-bar.urgent {
		background: var(--color-error, #ef4444);
	}

	.countdown-timer {
		color: var(--color-text-secondary);
	}

	.countdown-timer.warning {
		color: var(--color-warning, #f59e0b);
	}

	.countdown-timer.urgent {
		color: var(--color-error, #ef4444);
		font-weight: 600;
	}

	.undo-button {
		background: var(--color-accent);
		color: white;
	}

	.undo-button:hover {
		background: var(--color-accent-hover);
		transform: scale(1.02);
	}

	.undo-button:active {
		transform: scale(0.98);
	}
</style>
