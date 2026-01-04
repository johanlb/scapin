<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Card, Button } from '$lib/components/ui';
	import { onMount } from 'svelte';

	// Get shared data from URL params
	const title = $derived($page.url.searchParams.get('title') || '');
	const text = $derived($page.url.searchParams.get('text') || '');
	const url = $derived($page.url.searchParams.get('url') || '');

	let processing = $state(false);
	let success = $state(false);
	let error = $state<string | null>(null);

	// Combine shared content
	const sharedContent = $derived(
		[title, text, url].filter(Boolean).join('\n\n')
	);

	async function saveToNotes() {
		processing = true;
		error = null;

		try {
			// TODO: Call API to save to notes
			// For now, just simulate success
			await new Promise(resolve => setTimeout(resolve, 500));
			success = true;

			// Redirect to notes after a brief delay
			setTimeout(() => goto('/notes'), 1500);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Erreur inconnue';
		} finally {
			processing = false;
		}
	}

	async function sendToScapin() {
		processing = true;
		error = null;

		try {
			// TODO: Call API to process with Scapin
			await new Promise(resolve => setTimeout(resolve, 500));
			success = true;

			// Redirect to briefing
			setTimeout(() => goto('/'), 1500);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Erreur inconnue';
		} finally {
			processing = false;
		}
	}

	function cancel() {
		// Close the share sheet / go back
		if (window.history.length > 1) {
			window.history.back();
		} else {
			goto('/');
		}
	}

	// Auto-redirect if no content
	onMount(() => {
		if (!sharedContent) {
			goto('/');
		}
	});
</script>

<div class="min-h-screen bg-[var(--color-bg-primary)] p-4 flex items-center justify-center">
	<div class="w-full max-w-md">
		<Card padding="lg">
			{#if success}
				<div class="text-center py-8">
					<div class="text-4xl mb-4">
						{success ? '✅' : ''}
					</div>
					<h2 class="text-xl font-bold text-[var(--color-text-primary)] mb-2">
						Enregistre !
					</h2>
					<p class="text-[var(--color-text-secondary)]">
						Redirection en cours...
					</p>
				</div>
			{:else}
				<header class="mb-4">
					<h1 class="text-xl font-bold text-[var(--color-text-primary)]">
						Partage vers Scapin
					</h1>
					<p class="text-sm text-[var(--color-text-secondary)]">
						Que souhaitez-vous faire ?
					</p>
				</header>

				<!-- Preview shared content -->
				<div class="mb-6 p-3 rounded-xl bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]">
					<p class="text-sm text-[var(--color-text-secondary)] mb-1">Contenu partage :</p>
					<p class="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap line-clamp-4">
						{sharedContent || 'Aucun contenu'}
					</p>
				</div>

				{#if error}
					<div class="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm">
						{error}
					</div>
				{/if}

				<div class="space-y-3">
					<Button
						variant="primary"
						size="lg"
						onclick={saveToNotes}
						disabled={processing || !sharedContent}
						class="w-full justify-center"
					>
						{#if processing}
							Enregistrement...
						{:else}
							📝 Sauvegarder dans Notes
						{/if}
					</Button>

					<Button
						variant="secondary"
						size="lg"
						onclick={sendToScapin}
						disabled={processing || !sharedContent}
						class="w-full justify-center"
					>
						{#if processing}
							Traitement...
						{:else}
							🎭 Demander a Scapin
						{/if}
					</Button>

					<Button
						variant="ghost"
						size="lg"
						onclick={cancel}
						disabled={processing}
						class="w-full justify-center"
					>
						Annuler
					</Button>
				</div>
			{/if}
		</Card>
	</div>
</div>
