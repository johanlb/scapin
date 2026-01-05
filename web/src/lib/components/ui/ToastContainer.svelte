<script lang="ts">
	/**
	 * ToastContainer Component
	 * Renders all active toast notifications in a fixed position
	 */
	import { toastStore } from '$lib/stores/toast.svelte';
	import Toast from './Toast.svelte';

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
</script>

{#if toastStore.toasts.length > 0}
	<div
		class="fixed z-[100] {positionClasses[position]} flex flex-col gap-2 w-full max-w-sm pointer-events-none"
		style="padding-top: var(--safe-area-top); padding-right: var(--safe-area-right);"
	>
		{#each toastStore.toasts as toast (toast.id)}
			<div class="pointer-events-auto">
				<Toast
					id={toast.id}
					type={toast.type}
					message={toast.message}
					title={toast.title}
					dismissible={toast.dismissible}
					ondismiss={handleDismiss}
				/>
			</div>
		{/each}
	</div>
{/if}
