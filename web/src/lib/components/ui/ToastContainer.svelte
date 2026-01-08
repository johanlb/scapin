<script lang="ts">
	/**
	 * ToastContainer Component
	 * Renders all active toast notifications in a fixed position
	 * Supports both regular toasts and special Undo toasts with countdown
	 */
	import { toastStore } from '$lib/stores/toast.svelte';
	import Toast from './Toast.svelte';
	import UndoToast from './UndoToast.svelte';

	interface Props {
		position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
	}

	let { position = 'top-right' }: Props = $props();

	const positionClasses = {
		'top-right': 'top-4 right-4',
		'top-left': 'top-4 left-4',
		'bottom-right': 'bottom-4 right-4',
		'bottom-left': 'bottom-4 left-4',
		'top-center': 'top-4 left-1/2 -translate-x-1/2',
		'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2'
	};

	function handleDismiss(id: string) {
		toastStore.dismiss(id);
	}

	function handleUndo(id: string) {
		toastStore.executeUndo(id);
	}
</script>

{#if toastStore.toasts.length > 0}
	<div
		class="fixed z-[100] {positionClasses[position]} flex flex-col gap-2 w-full max-w-sm pointer-events-none"
		style="padding-top: var(--safe-area-top); padding-right: var(--safe-area-right);"
	>
		{#each toastStore.toasts as toast (toast.id)}
			<div class="pointer-events-auto">
				{#if toast.type === 'undo'}
					<UndoToast
						id={toast.id}
						message={toast.message}
						title={toast.title}
						countdownSeconds={toast.countdownSeconds ?? 300}
						onUndo={() => handleUndo(toast.id)}
						onDismiss={() => handleDismiss(toast.id)}
					/>
				{:else}
					<Toast
						id={toast.id}
						type={toast.type}
						message={toast.message}
						title={toast.title}
						dismissible={toast.dismissible}
						ondismiss={handleDismiss}
					/>
				{/if}
			</div>
		{/each}
	</div>
{/if}
