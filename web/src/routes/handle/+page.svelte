<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	// Parse the action from protocol handler
	// Format: web+scapin://action/params
	// URL will be: /handle?action=web%2Bscapin%3A%2F%2Faction%2Fparams
	const rawAction = $derived($page.url.searchParams.get('action') || '');

	interface ParsedAction {
		type: string;
		id?: string;
		params: Record<string, string>;
	}

	function parseAction(action: string): ParsedAction {
		// Remove protocol prefix
		const cleaned = action.replace(/^web\+scapin:\/\//, '');

		// Split path and query
		const [path, query] = cleaned.split('?');
		const segments = path.split('/').filter(Boolean);

		// Parse query params
		const params: Record<string, string> = {};
		if (query) {
			const searchParams = new URLSearchParams(query);
			searchParams.forEach((value, key) => {
				params[key] = value;
			});
		}

		return {
			type: segments[0] || 'home',
			id: segments[1],
			params
		};
	}

	const action = $derived(parseAction(rawAction));

	onMount(() => {
		// Route based on action type
		switch (action.type) {
			case 'email':
			case 'flux':
				if (action.id) {
					goto(`/flux/${action.id}`);
				} else {
					goto('/flux');
				}
				break;

			case 'note':
			case 'notes':
				if (action.id) {
					goto(`/notes/${action.id}`);
				} else {
					goto('/notes');
				}
				break;

			case 'journal':
				goto('/journal');
				break;

			case 'briefing':
			case 'home':
			default:
				goto('/');
				break;
		}
	});
</script>

<div class="min-h-screen bg-[var(--color-bg-primary)] flex items-center justify-center">
	<div class="text-center">
		<div class="spinner mx-auto mb-4"></div>
		<p class="text-[var(--color-text-secondary)]">Redirection...</p>
	</div>
</div>

<style>
	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--color-border);
		border-top-color: var(--color-primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
