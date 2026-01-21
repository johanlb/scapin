<script lang="ts">
	/**
	 * MemoryCyclesNotificationHandler Component
	 * Handles WebSocket events for Memory Cycles and shows toast notifications
	 */
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { toastStore } from '$lib/stores/toast.svelte';

	// Memory Cycles event types
	interface MemoryCyclesEvent {
		event_type: 'retouche_done' | 'filage_ready' | 'questions_added' | 'lecture_completed';
		note_id?: string;
		note_title?: string;
		count?: number;
		quality_score?: number;
		model_used?: string;
		timestamp: string;
	}

	// Handle incoming events
	function handleEvent(event: CustomEvent<MemoryCyclesEvent>) {
		const data = event.detail;

		switch (data.event_type) {
			case 'retouche_done':
				toastStore.success(
					`✨ ${data.note_title || 'Note'} a été améliorée par ${data.model_used || 'Scapin'}`,
					{ title: 'Note améliorée', duration: 5000 }
				);
				break;

			case 'filage_ready':
				toastStore.info(
					`📋 Votre filage est prêt avec ${data.count || 0} note${(data.count || 0) > 1 ? 's' : ''} à revoir`,
					{ title: 'Briefing prêt', duration: 5000 }
				);
				break;

			case 'questions_added':
				toastStore.warning(
					`❓ ${data.count || 0} nouvelle${(data.count || 0) > 1 ? 's' : ''} question${(data.count || 0) > 1 ? 's' : ''} pour vous`,
					{ title: 'Nouvelles questions', duration: 5000 }
				);
				break;

			case 'lecture_completed':
				if (data.quality_score !== undefined) {
					toastStore.success(
						`📚 ${data.note_title || 'Note'} - Score: ${data.quality_score}%`,
						{ title: 'Lecture terminée', duration: 3000 }
					);
				}
				break;
		}
	}

	// Listen for Scapin events from WebSocket
	function handleScapinEvent(event: CustomEvent) {
		const data = event.detail;

		// Check if it's a memory cycles event
		if (
			data.event_type === 'retouche_done' ||
			data.event_type === 'filage_ready' ||
			data.event_type === 'questions_added' ||
			data.event_type === 'lecture_completed'
		) {
			handleEvent(new CustomEvent('memory-cycles', { detail: data }));
		}
	}

	onMount(() => {
		if (!browser) return;

		// Listen for Scapin WebSocket events
		window.addEventListener('scapin:event', handleScapinEvent as EventListener);
	});

	onDestroy(() => {
		if (!browser) return;
		window.removeEventListener('scapin:event', handleScapinEvent as EventListener);
	});
</script>

<!-- This component doesn't render anything visible -->
