<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { Card, Button, Tabs } from '$lib/components/ui';
	import { notificationStore, configStore } from '$lib/stores';
	import type { IntegrationStatus } from '$lib/stores';

	// Appearance settings
	let darkMode = $state('auto');
	let language = $state('fr');
	let requestingPermission = $state(false);

	// IA settings
	let aiModel = $state('claude-3-5-haiku-20241022');
	let aiTemperature = $state(0.7);
	let autoApplyThreshold = $state(90);

	// Processing settings
	let processingBatchSize = $state(20);
	let enableCognitive = $state(true);
	let enableAutoApply = $state(true);

	// Notification settings
	let notifyOnUrgent = $state(true);
	let notifyOnQueue = $state(true);
	let notifyOnComplete = $state(false);
	let quietHoursEnabled = $state(false);
	let quietHoursStart = $state('22:00');
	let quietHoursEnd = $state('08:00');

	// Dev settings
	let logLevel = $state('INFO');
	let showDebugInfo = $state(false);
	let enableMockData = $state(false);

	// Load config on mount
	onMount(async () => {
		await configStore.fetchConfig();

		// Load persisted theme preference
		if (browser) {
			const savedTheme = localStorage.getItem('scapin-theme');
			if (savedTheme) darkMode = savedTheme;
		}
	});

	// Persist theme changes
	$effect(() => {
		if (browser) {
			localStorage.setItem('scapin-theme', darkMode);
			// Apply theme to document
			if (darkMode === 'dark') {
				document.documentElement.classList.add('dark');
			} else if (darkMode === 'light') {
				document.documentElement.classList.remove('dark');
			} else {
				// Auto mode - follow system preference
				const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
				document.documentElement.classList.toggle('dark', prefersDark);
			}
		}
	});

	// Settings tabs
	const settingsTabs = [
		{ id: 'general', label: 'Général' },
		{ id: 'integrations', label: 'Connexions' },
		{ id: 'ai', label: 'Intelligence' },
		{ id: 'notifications', label: 'Alertes' },
		{ id: 'dev', label: 'Avancé' }
	];
	let activeTab = $state('general');

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

	<!-- Tab Navigation -->
	<div class="mb-6">
		<Tabs
			tabs={settingsTabs}
			bind:activeTab={activeTab}
			variant="underline"
		/>
	</div>

	<div class="space-y-6">
		<!-- GENERAL TAB -->
		{#if activeTab === 'general'}
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

		<!-- INTEGRATIONS TAB -->
		{:else if activeTab === 'integrations'}
			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					🔗 Connexions aux services
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

		<!-- AI TAB -->
		{:else if activeTab === 'ai'}
			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					🧠 Intelligence Artificielle
				</h2>
				<Card padding="lg">
					<div class="space-y-5">
						<!-- Model selection -->
						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Modèle IA</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Modèle utilisé pour l'analyse
								</p>
							</div>
							<select
								bind:value={aiModel}
								class="px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm shrink-0"
							>
								<option value="claude-3-5-haiku-20241022">Haiku (Rapide)</option>
								<option value="claude-3-5-sonnet-20241022">Sonnet (Équilibré)</option>
								<option value="claude-3-opus-20240229">Opus (Puissant)</option>
							</select>
						</div>

						<!-- Auto-apply threshold -->
						<div>
							<div class="flex items-center justify-between gap-4 mb-2">
								<div class="min-w-0">
									<h3 class="font-semibold text-[var(--color-text-primary)]">Seuil d'auto-approbation</h3>
									<p class="text-sm text-[var(--color-text-secondary)]">
										Confiance minimale pour appliquer automatiquement
									</p>
								</div>
								<span class="text-sm font-mono text-[var(--color-accent)] shrink-0">{autoApplyThreshold}%</span>
							</div>
							<input
								type="range"
								min="50"
								max="100"
								step="5"
								bind:value={autoApplyThreshold}
								class="w-full accent-[var(--color-accent)]"
							/>
							<div class="flex justify-between text-xs text-[var(--color-text-tertiary)] mt-1">
								<span>Plus permissif</span>
								<span>Plus strict</span>
							</div>
						</div>

						<!-- Processing toggles -->
						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Pipeline cognitif</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Raisonnement multi-passes pour de meilleures décisions
								</p>
							</div>
							<button
								type="button"
								aria-label="Activer le pipeline cognitif"
								onclick={() => enableCognitive = !enableCognitive}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {enableCognitive ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {enableCognitive ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>

						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Auto-application</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Appliquer automatiquement les décisions à haute confiance
								</p>
							</div>
							<button
								type="button"
								aria-label="Activer l'auto-application"
								onclick={() => enableAutoApply = !enableAutoApply}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {enableAutoApply ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {enableAutoApply ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>
					</div>
				</Card>
			</section>

			<!-- Processing limits -->
			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					⚙️ Traitement
				</h2>
				<Card padding="lg">
					<div class="flex items-center justify-between gap-4">
						<div class="min-w-0">
							<h3 class="font-semibold text-[var(--color-text-primary)]">Taille de batch</h3>
							<p class="text-sm text-[var(--color-text-secondary)]">
								Nombre max d'emails traités par session
							</p>
						</div>
						<select
							bind:value={processingBatchSize}
							class="px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm shrink-0"
						>
							<option value={10}>10 emails</option>
							<option value={20}>20 emails</option>
							<option value={50}>50 emails</option>
							<option value={100}>100 emails</option>
						</select>
					</div>
				</Card>
			</section>

		<!-- NOTIFICATIONS TAB -->
		{:else if activeTab === 'notifications'}
			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					🔔 Notifications push
				</h2>
				<Card padding="lg">
					<div class="flex items-center justify-between gap-4">
						<div class="min-w-0">
							<h3 class="font-semibold text-[var(--color-text-primary)]">Activer les notifications</h3>
							<p class="text-sm text-[var(--color-text-secondary)]">
								{#if !notificationStore.isSupported}
									Non supportées par ce navigateur
								{:else if notificationStore.isDenied}
									Refusées - modifiez les paramètres du navigateur
								{:else if notificationStore.isGranted}
									Actives
								{:else}
									Recevoir des alertes
								{/if}
							</p>
						</div>
						{#if notificationStore.isSupported && !notificationStore.isDenied}
							<button
								type="button"
								aria-label="Activer les notifications"
								onclick={toggleNotifications}
								disabled={requestingPermission || notificationStore.isGranted}
								class="w-14 h-8 rounded-full transition-colors shrink-0 disabled:opacity-50 {notificationStore.isGranted ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {notificationStore.isGranted ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						{:else}
							<span class="text-sm text-[var(--color-text-tertiary)]">
								{notificationStore.isDenied ? '🚫' : '⚠️'}
							</span>
						{/if}
					</div>
				</Card>
			</section>

			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					📋 Types de notifications
				</h2>
				<Card padding="lg">
					<div class="space-y-4">
						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Éléments urgents</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Emails et tâches à traiter en priorité
								</p>
							</div>
							<button
								type="button"
								aria-label="Notifier pour les éléments urgents"
								onclick={() => notifyOnUrgent = !notifyOnUrgent}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {notifyOnUrgent ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {notifyOnUrgent ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>

						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">File d'attente</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Nouveaux éléments en attente de validation
								</p>
							</div>
							<button
								type="button"
								aria-label="Notifier pour la file d'attente"
								onclick={() => notifyOnQueue = !notifyOnQueue}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {notifyOnQueue ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {notifyOnQueue ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>

						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Traitements terminés</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Confirmation quand un batch est terminé
								</p>
							</div>
							<button
								type="button"
								aria-label="Notifier à la fin des traitements"
								onclick={() => notifyOnComplete = !notifyOnComplete}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {notifyOnComplete ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {notifyOnComplete ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>
					</div>
				</Card>
			</section>

			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					🌙 Heures calmes
				</h2>
				<Card padding="lg">
					<div class="space-y-4">
						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Activer les heures calmes</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Suspendre les notifications pendant certaines heures
								</p>
							</div>
							<button
								type="button"
								aria-label="Activer les heures calmes"
								onclick={() => quietHoursEnabled = !quietHoursEnabled}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {quietHoursEnabled ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {quietHoursEnabled ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>

						{#if quietHoursEnabled}
							<div class="flex items-center gap-4 pt-2">
								<div class="flex-1">
									<label for="quiet-hours-start" class="text-sm text-[var(--color-text-secondary)] mb-1 block">De</label>
									<input
										id="quiet-hours-start"
										type="time"
										bind:value={quietHoursStart}
										class="w-full px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm"
									/>
								</div>
								<div class="flex-1">
									<label for="quiet-hours-end" class="text-sm text-[var(--color-text-secondary)] mb-1 block">À</label>
									<input
										id="quiet-hours-end"
										type="time"
										bind:value={quietHoursEnd}
										class="w-full px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm"
									/>
								</div>
							</div>
						{/if}
					</div>
				</Card>
			</section>

		<!-- DEV TAB -->
		{:else if activeTab === 'dev'}
			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					🔧 Paramètres avancés
				</h2>
				<Card padding="lg">
					<div class="space-y-4">
						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Niveau de log</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Verbosité des logs système
								</p>
							</div>
							<select
								bind:value={logLevel}
								class="px-3 py-2 rounded-xl bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] border border-[var(--color-border)] text-sm shrink-0"
							>
								<option value="DEBUG">Debug</option>
								<option value="INFO">Info</option>
								<option value="WARNING">Warning</option>
								<option value="ERROR">Error</option>
							</select>
						</div>

						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Infos de debug</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Afficher les informations techniques dans l'interface
								</p>
							</div>
							<button
								type="button"
								aria-label="Afficher les infos de debug"
								onclick={() => showDebugInfo = !showDebugInfo}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {showDebugInfo ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {showDebugInfo ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>

						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Données simulées</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Utiliser des données de test au lieu de l'API
								</p>
							</div>
							<button
								type="button"
								aria-label="Activer les données simulées"
								onclick={() => enableMockData = !enableMockData}
								class="w-14 h-8 rounded-full transition-colors shrink-0 {enableMockData ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'}"
							>
								<span class="block w-6 h-6 rounded-full bg-white shadow-md transform transition-transform {enableMockData ? 'translate-x-7' : 'translate-x-1'}"></span>
							</button>
						</div>
					</div>
				</Card>
			</section>

			<section>
				<h2 class="text-lg font-semibold text-[var(--color-text-primary)] mb-3">
					🗄️ Données
				</h2>
				<Card padding="lg">
					<div class="space-y-4">
						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)]">Vider le cache local</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Supprimer les données en cache (préférences conservées)
								</p>
							</div>
							<Button variant="secondary" size="sm" onclick={() => {
								if (browser) {
									sessionStorage.clear();
									alert('Cache vidé');
								}
							}}>Vider</Button>
						</div>

						<div class="flex items-center justify-between gap-4">
							<div class="min-w-0">
								<h3 class="font-semibold text-[var(--color-text-primary)] text-[var(--color-urgency-urgent)]">Réinitialiser tout</h3>
								<p class="text-sm text-[var(--color-text-secondary)]">
									Supprimer toutes les données locales et préférences
								</p>
							</div>
							<Button variant="secondary" size="sm" onclick={() => {
								if (browser && confirm('Êtes-vous sûr de vouloir réinitialiser toutes les données locales ?')) {
									localStorage.clear();
									sessionStorage.clear();
									location.reload();
								}
							}}>Réinitialiser</Button>
						</div>
					</div>
				</Card>
			</section>
		{/if}
	</div>
</div>
