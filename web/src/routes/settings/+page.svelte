<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Button } from '$lib/components/ui';
	import { notificationStore, configStore } from '$lib/stores';
	import type { IntegrationStatus } from '$lib/stores';

	let darkMode = $state('auto');
	let language = $state('fr');
	let requestingPermission = $state(false);

	// Load config on mount
	onMount(async () => {
		await configStore.fetchConfig();
	});

	async function toggleNotifications() {
		if (notificationStore.isGranted) {
			// Can't programmatically revoke permissions - user must do it in browser settings
			return;
		}
		if (notificationStore.canRequestPermission) {
			requestingPermission = true;
			await notificationStore.requestPermission();
			requestingPermission = false;
		}
	}

	function getStatusColor(status: IntegrationStatus['status']): string {
		switch (status) {
			case 'connected':
				return 'bg-[var(--color-success)]';
			case 'syncing':
				return 'bg-[var(--color-warning)] animate-pulse';
			case 'error':
				return 'bg-[var(--color-error)]';
			default:
				return 'bg-[var(--color-text-tertiary)]';
		}
	}

	function getStatusLabel(status: IntegrationStatus['status']): string {
		switch (status) {
			case 'connected':
				return 'Connecté';
			case 'syncing':
				return 'Synchronisation...';
			case 'error':
				return 'Erreur';
			default:
				return 'Non connecté';
		}
	}

	function handleIntegration(integration: IntegrationStatus) {
		if (integration.status === 'disconnected') {
			// TODO: Implement OAuth flow for each integration
			alert(
				`Configuration de ${integration.name} à venir.\n\nCette fonctionnalité nécessite une configuration OAuth dans les paramètres backend.`
			);
		} else {
			// TODO: Open settings modal for connected integrations
			alert(
				`Paramètres de ${integration.name}\n\nStatut: ${getStatusLabel(integration.status)}\nDernière sync: ${integration.last_sync || 'N/A'}`
			);
		}
	}
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto overflow-hidden">
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			⚙️ Réglages
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Personnalisez votre expérience Scapin
		</p>
	</header>

	<div class="space-y-6">
		<!-- Appearance -->
		<section>
			<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
				🎨 Apparence
			</h2>
			<Card padding="lg">
				<div class="space-y-4">
					<div class="flex items-center justify-between gap-4">
						<div class="min-w-0">
							<h3 class="font-semibold text-[var(--color-text-primary)]">Thème</h3>
							<p class="text-sm text-[var(--color-text-secondary)]">
								Choisissez le mode d'affichage
							</p>
						</div>
						<select
							bind:value={darkMode}
							class="px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm shrink-0"
						>
							<option value="auto">Automatique</option>
							<option value="light">Clair</option>
							<option value="dark">Sombre</option>
						</select>
					</div>
					<div class="flex items-center justify-between gap-4">
						<div class="min-w-0">
							<h3 class="font-semibold text-[var(--color-text-primary)]">Langue</h3>
							<p class="text-sm text-[var(--color-text-secondary)]">
								Langue de l'interface
							</p>
						</div>
						<select
							bind:value={language}
							class="px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm shrink-0"
						>
							<option value="fr">Français</option>
							<option value="en">English</option>
						</select>
					</div>
				</div>
			</Card>
		</section>

		<!-- Notifications -->
		<section>
			<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
				🔔 Notifications
			</h2>
			<Card padding="lg">
				<div class="flex items-center justify-between gap-4">
					<div class="min-w-0">
						<h3 class="font-semibold text-[var(--color-text-primary)]">Notifications push</h3>
						<p class="text-sm text-[var(--color-text-secondary)]">
							{#if !notificationStore.isSupported}
								Non supportées par ce navigateur
							{:else if notificationStore.isDenied}
								Refusées - modifiez les paramètres du navigateur
							{:else if notificationStore.isGranted}
								Actives pour les éléments urgents
							{:else}
								Recevoir des alertes pour les éléments urgents
							{/if}
						</p>
					</div>
					{#if notificationStore.isSupported && !notificationStore.isDenied}
						<button
							type="button"
							onclick={toggleNotifications}
							disabled={requestingPermission || notificationStore.isGranted}
							aria-label={notificationStore.isGranted ? 'Notifications activées' : 'Activer les notifications'}
							aria-pressed={notificationStore.isGranted}
							class="w-14 h-8 rounded-full transition-colors shrink-0 disabled:opacity-50 {notificationStore.isGranted ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
						>
							<span
								class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {notificationStore.isGranted ? 'translate-x-7' : 'translate-x-1'}"
							></span>
						</button>
					{:else}
						<span class="text-sm text-[var(--color-text-tertiary)]">
							{notificationStore.isDenied ? '🚫' : '⚠️'}
						</span>
					{/if}
				</div>
			</Card>
		</section>

		<!-- Integrations -->
		<section>
			<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
				🔗 Intégrations
			</h2>
			{#if configStore.loading}
				<div class="flex justify-center py-4">
					<div
						class="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
					></div>
				</div>
			{:else if configStore.error}
				<Card padding="md">
					<p class="text-sm text-[var(--color-urgency-urgent)]">{configStore.error}</p>
				</Card>
			{:else}
				<div class="space-y-2">
					{#each configStore.integrations as integration}
					<Card padding="md">
						<div class="flex items-center justify-between gap-3">
							<div class="flex items-center gap-3 min-w-0">
								<span class="text-xl shrink-0">{integration.icon}</span>
								<div class="min-w-0">
									<div class="flex items-center gap-2">
										<h3 class="font-semibold text-[var(--color-text-primary)] text-sm">{integration.name}</h3>
										<span
											class="w-2 h-2 rounded-full shrink-0 {getStatusColor(integration.status)}"
											title={getStatusLabel(integration.status)}
										></span>
									</div>
									<p class="text-xs text-[var(--color-text-tertiary)] truncate">
										{#if integration.status === 'connected' && integration.last_sync}
											Sync {integration.last_sync}
										{:else}
											{getStatusLabel(integration.status)}
										{/if}
									</p>
								</div>
							</div>
							{#if integration.status === 'disconnected'}
								<Button variant="primary" size="sm" onclick={() => handleIntegration(integration)}>Établir</Button>
							{:else}
								<Button variant="secondary" size="sm" onclick={() => handleIntegration(integration)}>Ajuster</Button>
							{/if}
						</div>
					</Card>
				{/each}
				</div>
			{/if}
		</section>

		<!-- About -->
		<section>
			<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
				ℹ️ À propos
			</h2>
			<Card padding="lg">
				<div class="text-center">
					<h3 class="text-xl font-bold text-[var(--color-text-primary)] mb-1">🎭 Scapin</h3>
					<p class="text-sm text-[var(--color-text-secondary)] mb-1">Votre valet de l'esprit</p>
					<p class="text-xs text-[var(--color-text-tertiary)]">Version 0.9.0</p>
				</div>
			</Card>
		</section>
	</div>
</div>
