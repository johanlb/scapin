<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, Button, Input, Skeleton } from '$lib/components/ui';
	import {
		getDraft,
		updateDraft,
		sendDraft,
		discardDraft,
		deleteDraft,
		type Draft
	} from '$lib/api/client';
	import { formatRelativeTime } from '$lib/utils/formatters';

	// Get the draft ID from route params
	const draftId = $derived($page.params.id ?? '');

	// State
	let draft = $state<Draft | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let sending = $state(false);
	let error = $state<string | null>(null);
	let saveError = $state<string | null>(null);
	let hasChanges = $state(false);

	// Edit state
	let editSubject = $state('');
	let editBody = $state('');
	let editTo = $state('');
	let editCc = $state('');
	let editBcc = $state('');

	onMount(async () => {
		if (draftId) {
			await loadDraft();
		}
	});

	async function loadDraft() {
		loading = true;
		error = null;
		try {
			draft = await getDraft(draftId);
			// Initialize edit fields
			editSubject = draft.subject;
			editBody = draft.body;
			editTo = draft.to_addresses.join(', ');
			editCc = draft.cc_addresses.join(', ');
			editBcc = draft.bcc_addresses.join(', ');
			hasChanges = false;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
		} finally {
			loading = false;
		}
	}

	function markChanged() {
		hasChanges = true;
		saveError = null;
	}

	function parseAddresses(input: string): string[] {
		if (!input.trim()) return [];
		return input
			.split(/[,;]/)
			.map((addr) => addr.trim())
			.filter((addr) => addr.length > 0);
	}

	async function handleSave() {
		if (!draft || draft.status !== 'draft') return;

		saving = true;
		saveError = null;
		try {
			draft = await updateDraft(draftId, {
				subject: editSubject,
				body: editBody,
				to_addresses: parseAddresses(editTo),
				cc_addresses: parseAddresses(editCc),
				bcc_addresses: parseAddresses(editBcc)
			});
			hasChanges = false;
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Erreur de sauvegarde';
		} finally {
			saving = false;
		}
	}

	async function handleSend() {
		if (!draft || draft.status !== 'draft') return;

		// Save first if there are changes
		if (hasChanges) {
			await handleSave();
			if (saveError) return;
		}

		if (!confirm('Envoyer ce brouillon maintenant ?')) return;

		sending = true;
		try {
			draft = await sendDraft(draftId);
			// Redirect back to list after sending
			goto('/drafts');
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Erreur d\'envoi';
		} finally {
			sending = false;
		}
	}

	async function handleDiscard() {
		if (!draft) return;
		if (!confirm('Abandonner ce brouillon ?')) return;

		try {
			await discardDraft(draftId);
			goto('/drafts');
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Erreur';
		}
	}

	async function handleDelete() {
		if (!draft) return;
		if (!confirm('Supprimer définitivement ce brouillon ?')) return;

		try {
			await deleteDraft(draftId);
			goto('/drafts');
		} catch (e) {
			saveError = e instanceof Error ? e.message : 'Erreur de suppression';
		}
	}

	function goBack() {
		if (hasChanges) {
			if (confirm('Vous avez des modifications non sauvegardées. Quitter quand même ?')) {
				goto('/drafts');
			}
		} else {
			goto('/drafts');
		}
	}

	function formatDate(isoString: string): string {
		return new Date(isoString).toLocaleDateString('fr-FR', {
			day: 'numeric',
			month: 'long',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<div class="min-h-screen bg-[var(--color-bg-primary)]">
	<!-- Header -->
	<header
		class="sticky top-0 z-20 glass-prominent border-b border-[var(--glass-border-subtle)] px-4 py-3"
	>
		<div class="max-w-4xl mx-auto flex items-center gap-3">
			<button
				onclick={goBack}
				class="p-2 -ml-2 rounded-full hover:bg-[var(--glass-tint)] transition-colors"
				aria-label="Retour"
			>
				<span class="text-xl">&#8592;</span>
			</button>
			<div class="flex-1 min-w-0">
				<h1 class="text-lg font-semibold text-[var(--color-text-primary)] truncate">
					{#if loading}
						Chargement...
					{:else if draft}
						{draft.status === 'draft' ? 'Modifier le brouillon' : 'Voir le brouillon'}
					{:else}
						Brouillon introuvable
					{/if}
				</h1>
				{#if draft}
					<p class="text-sm text-[var(--color-text-tertiary)]">
						{#if draft.status === 'sent'}
							Envoyé {formatRelativeTime(draft.sent_at ?? draft.updated_at)}
						{:else if draft.status === 'discarded'}
							Abandonné {formatRelativeTime(draft.discarded_at ?? draft.updated_at)}
						{:else}
							Modifié {formatRelativeTime(draft.updated_at)}
						{/if}
					</p>
				{/if}
			</div>
			{#if draft?.status === 'draft'}
				<div class="flex items-center gap-2">
					<Button
						variant="glass"
						size="sm"
						onclick={handleSave}
						disabled={saving || !hasChanges}
					>
						{saving ? 'Sauvegarde...' : hasChanges ? 'Sauvegarder' : 'Sauvegardé'}
					</Button>
					<Button
						variant="primary"
						size="sm"
						onclick={handleSend}
						disabled={sending}
					>
						{sending ? 'Envoi...' : 'Envoyer'}
					</Button>
				</div>
			{/if}
		</div>
	</header>

	{#if loading}
		<!-- Loading state -->
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
			<Card variant="glass-subtle">
				<div class="p-4 space-y-4">
					<Skeleton variant="text" class="w-1/3" />
					<Skeleton variant="text" class="w-full" />
					<Skeleton variant="text" class="w-2/3" />
				</div>
			</Card>
			<Card variant="glass-subtle">
				<div class="p-4">
					<Skeleton variant="rectangular" class="h-64" />
				</div>
			</Card>
		</main>
	{:else if error}
		<!-- Error state -->
		<main class="p-8 text-center">
			<div class="text-red-400 mb-4">{error}</div>
			<Button variant="glass" onclick={loadDraft}>Réessayer</Button>
		</main>
	{:else if draft}
		<main class="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
			<!-- Error message -->
			{#if saveError}
				<div class="p-3 rounded-lg bg-red-500/20 text-red-300 text-sm">
					{saveError}
				</div>
			{/if}

			<!-- Original email context -->
			{#if draft.original_from || draft.original_subject}
				<Card variant="glass-subtle">
					<div class="p-4">
						<div class="text-xs text-[var(--color-text-tertiary)] uppercase tracking-wider mb-2">
							En réponse à
						</div>
						<div class="text-sm text-[var(--color-text-secondary)]">
							{#if draft.original_from}
								<div><strong>De :</strong> {draft.original_from}</div>
							{/if}
							{#if draft.original_subject}
								<div><strong>Objet :</strong> {draft.original_subject}</div>
							{/if}
							{#if draft.original_date}
								<div><strong>Date :</strong> {formatDate(draft.original_date)}</div>
							{/if}
						</div>
					</div>
				</Card>
			{/if}

			<!-- AI info -->
			{#if draft.ai_generated}
				<Card variant="glass-subtle">
					<div class="p-4">
						<div class="flex items-center gap-2 mb-2">
							<span class="px-2 py-0.5 text-xs rounded bg-purple-500/20 text-purple-300">
								Généré par IA
							</span>
							<span class="text-xs text-[var(--color-text-tertiary)]">
								Confiance : {Math.round(draft.ai_confidence * 100)}%
							</span>
						</div>
						{#if draft.ai_reasoning}
							<p class="text-sm text-[var(--color-text-secondary)]">
								{draft.ai_reasoning}
							</p>
						{/if}
					</div>
				</Card>
			{/if}

			<!-- Recipients -->
			<Card variant="glass-subtle">
				<div class="p-4 space-y-4">
					<div>
						<span class="block text-xs text-[var(--color-text-tertiary)] uppercase tracking-wider mb-1">
							À
						</span>
						{#if draft.status === 'draft'}
							<Input
								bind:value={editTo}
								placeholder="destinataire@example.com"
								oninput={markChanged}
							/>
						{:else}
							<div class="text-[var(--color-text-secondary)]">
								{draft.to_addresses.join(', ') || '(Non spécifié)'}
							</div>
						{/if}
					</div>
					<div>
						<span class="block text-xs text-[var(--color-text-tertiary)] uppercase tracking-wider mb-1">
							Cc
						</span>
						{#if draft.status === 'draft'}
							<Input
								bind:value={editCc}
								placeholder="cc@example.com"
								oninput={markChanged}
							/>
						{:else}
							<div class="text-[var(--color-text-secondary)]">
								{draft.cc_addresses.join(', ') || '(Aucun)'}
							</div>
						{/if}
					</div>
					{#if draft.status === 'draft' || draft.bcc_addresses.length > 0}
						<div>
							<span class="block text-xs text-[var(--color-text-tertiary)] uppercase tracking-wider mb-1">
								Cci
							</span>
							{#if draft.status === 'draft'}
								<Input
									bind:value={editBcc}
									placeholder="bcc@example.com"
									oninput={markChanged}
								/>
							{:else}
								<div class="text-[var(--color-text-secondary)]">
									{draft.bcc_addresses.join(', ')}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</Card>

			<!-- Subject -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<span class="block text-xs text-[var(--color-text-tertiary)] uppercase tracking-wider mb-1">
						Objet
					</span>
					{#if draft.status === 'draft'}
						<Input
							bind:value={editSubject}
							placeholder="Objet du message"
							oninput={markChanged}
						/>
					{:else}
						<div class="text-[var(--color-text-primary)] font-medium">
							{draft.subject || '(Sans objet)'}
						</div>
					{/if}
				</div>
			</Card>

			<!-- Body -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<span class="block text-xs text-[var(--color-text-tertiary)] uppercase tracking-wider mb-2">
						Message
					</span>
					{#if draft.status === 'draft'}
						<textarea
							bind:value={editBody}
							oninput={markChanged}
							placeholder="Rédigez votre message..."
							aria-label="Corps du message"
							class="w-full min-h-[300px] p-3 rounded-lg bg-[var(--glass-tint)] border border-[var(--glass-border-subtle)] text-[var(--color-text-primary)] placeholder-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)] resize-y"
						></textarea>
					{:else}
						<div class="whitespace-pre-wrap text-[var(--color-text-secondary)] leading-relaxed">
							{draft.body || '(Contenu vide)'}
						</div>
					{/if}
				</div>
			</Card>

			<!-- Actions for draft status -->
			{#if draft.status === 'draft'}
				<div class="flex items-center justify-between pt-4">
					<Button
						variant="ghost"
						onclick={handleDiscard}
						class="text-yellow-400 hover:text-yellow-300"
					>
						Abandonner
					</Button>
					<Button
						variant="ghost"
						onclick={handleDelete}
						class="text-red-400 hover:text-red-300"
					>
						Supprimer
					</Button>
				</div>
			{/if}

			<!-- Metadata -->
			<Card variant="glass-subtle">
				<div class="p-4">
					<div class="text-xs text-[var(--color-text-tertiary)] space-y-1">
						<div>Créé : {formatDate(draft.created_at)}</div>
						<div>Modifié : {formatDate(draft.updated_at)}</div>
						{#if draft.user_edited}
							<div class="text-purple-400">Édité manuellement</div>
						{/if}
						{#if draft.sent_at}
							<div class="text-green-400">Envoyé : {formatDate(draft.sent_at)}</div>
						{/if}
						{#if draft.discarded_at}
							<div class="text-yellow-400">Abandonné : {formatDate(draft.discarded_at)}</div>
						{/if}
						<div class="opacity-50">ID : {draft.draft_id}</div>
					</div>
				</div>
			</Card>
		</main>
	{/if}
</div>
